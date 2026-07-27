from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import DailyMissionClaim
from exams.models import ExamSet, Question, Section, StudentAnswer, StudentAttempt


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="anvar", password="test-password"
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("student_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_recovers_missing_profile_and_has_working_links(self):
        self.user.studentprofile.delete()
        self.client.force_login(self.user)

        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No completed tests yet")
        self.assertContains(response, reverse("exam_list"))
        self.assertNotContains(response, 'href="#"')
        self.assertTrue(hasattr(self.user, "studentprofile"))

    def test_dashboard_displays_real_attempt_metrics(self):
        exam = ExamSet.objects.create(title="IELTS Academic Mock 1")
        section = Section.objects.create(
            exam_set=exam,
            order=1,
            section_type="reading",
            time_limit_minutes=60,
        )
        correct_question = Question.objects.create(
            section=section,
            order=1,
            question_type="mcq",
            prompt="Correct",
            correct_answer="A",
        )
        wrong_question = Question.objects.create(
            section=section,
            order=2,
            question_type="mcq",
            prompt="Wrong",
            correct_answer="B",
        )
        attempt = StudentAttempt.objects.create(
            student=self.user,
            exam_set=exam,
            is_complete=True,
            submitted_at=timezone.now(),
        )
        StudentAttempt.objects.filter(pk=attempt.pk).update(
            started_at=timezone.now() - timedelta(minutes=30)
        )
        StudentAnswer.objects.create(
            attempt=attempt,
            question=correct_question,
            answer_text="A",
            is_correct=True,
        )
        StudentAnswer.objects.create(
            attempt=attempt,
            question=wrong_question,
            answer_text="A",
            is_correct=False,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IELTS Academic Mock 1")
        self.assertEqual(response.context["tests_taken"], 1)
        self.assertEqual(response.context["accuracy"], 50)
        self.assertEqual(response.context["skills"][0]["value"], 50)
        self.assertIn(response.context["avg_time"], {"29m", "30m"})
        self.assertContains(response, reverse("results", args=[attempt.pk]))

    def test_dashboard_uses_manual_band_scores_for_writing_progress(self):
        exam = ExamSet.objects.create(title="Reviewed Writing")
        section = Section.objects.create(
            exam_set=exam,
            order=1,
            section_type="writing",
            time_limit_minutes=40,
        )
        question = Question.objects.create(
            section=section,
            order=1,
            question_type="essay",
            prompt="Write an essay.",
        )
        attempt = StudentAttempt.objects.create(
            student=self.user,
            exam_set=exam,
            is_complete=True,
            submitted_at=timezone.now(),
        )
        StudentAnswer.objects.create(
            attempt=attempt,
            question=question,
            answer_text="Response",
            manual_score=7.2,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("student_dashboard"))

        writing = next(skill for skill in response.context["skills"] if skill["name"] == "Writing")
        self.assertEqual(writing["value"], 80)

    def test_completed_daily_mission_can_be_claimed_once_for_xp(self):
        exam = ExamSet.objects.create(title="Daily mission test")
        section = Section.objects.create(
            exam_set=exam, order=1, section_type="reading", time_limit_minutes=20
        )
        question = Question.objects.create(
            section=section,
            order=1,
            question_type="gap",
            prompt="Answer",
            correct_answer="answer",
        )
        attempt = StudentAttempt.objects.create(
            student=self.user,
            exam_set=exam,
            is_complete=True,
            submitted_at=timezone.now(),
        )
        StudentAnswer.objects.create(
            attempt=attempt, question=question, answer_text="answer", is_correct=True
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse("claim_daily_mission", args=["complete_test"]))
        self.user.studentprofile.refresh_from_db()

        self.assertRedirects(response, reverse("student_dashboard"))
        self.assertEqual(self.user.studentprofile.xp, 30)
        self.assertTrue(
            DailyMissionClaim.objects.filter(
                user=self.user, mission_key="complete_test"
            ).exists()
        )

        self.client.post(reverse("claim_daily_mission", args=["complete_test"]))
        self.user.studentprofile.refresh_from_db()
        self.assertEqual(self.user.studentprofile.xp, 30)


class StudentSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student", email="old@example.com", password="test-password"
        )
        self.client.force_login(self.user)

    def test_settings_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("student_settings"))
        self.assertEqual(response.status_code, 302)

    def test_student_can_update_profile_and_goals(self):
        response = self.client.post(
            reverse("student_settings"),
            {
                "first_name": "Anvar",
                "last_name": "Student",
                "target_band": "8.0",
                "daily_goal": "90",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("student_settings"))
        self.user.refresh_from_db()
        self.user.studentprofile.refresh_from_db()
        self.assertEqual(self.user.first_name, "Anvar")
        self.assertEqual(self.user.email, "old@example.com")
        self.assertEqual(self.user.studentprofile.target_band, 8.0)
        self.assertEqual(self.user.studentprofile.daily_goal, 90)
        self.assertContains(response, "Your profile settings have been updated.")

    def test_settings_reject_invalid_goals(self):
        response = self.client.post(
            reverse("student_settings"),
            {
                "target_band": "10.0",
                "daily_goal": "5",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "target_band", "Ensure this value is less than or equal to 9.")
        self.assertFormError(response.context["form"], "daily_goal", "Ensure this value is greater than or equal to 10.")

    def test_settings_reject_target_bands_outside_half_band_increments(self):
        response = self.client.post(
            reverse("student_settings"),
            {"target_band": "7.3", "daily_goal": "60"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "target_band",
            "Choose an IELTS band score in 0.5 increments.",
        )

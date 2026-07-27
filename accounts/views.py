from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, DurationField, ExpressionWrapper, F
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from exams.models import StudentAnswer, StudentAttempt

from .models import DailyMissionClaim, StudentProfile
from .forms import StudentSettingsForm


DAILY_MISSION_DEFINITIONS = {
    "complete_test": {
        "title": "Finish a practice test",
        "description": "Complete any available IELTS test today.",
        "target": 1,
        "xp": 30,
        "icon": "bi-clipboard2-check",
    },
    "answer_questions": {
        "title": "Answer 10 questions",
        "description": "Build momentum with objective practice today.",
        "target": 10,
        "xp": 20,
        "icon": "bi-ui-checks-grid",
    },
    "record_speaking": {
        "title": "Record a speaking response",
        "description": "Practise speaking aloud and submit one recording.",
        "target": 1,
        "xp": 25,
        "icon": "bi-mic",
    },
}


def get_daily_missions(user):
    """Return claimable, data-driven missions for the user's local day."""
    today = timezone.localdate()
    completed_attempts = StudentAttempt.objects.filter(
        student=user, is_complete=True, submitted_at__date=today
    )
    answers_today = StudentAnswer.objects.filter(attempt__in=completed_attempts)
    progress_by_key = {
        "complete_test": completed_attempts.count(),
        "answer_questions": answers_today.count(),
        "record_speaking": answers_today.exclude(audio_response="").filter(
            audio_response__isnull=False
        ).count(),
    }
    claimed_keys = set(
        DailyMissionClaim.objects.filter(user=user, completed_on=today).values_list(
            "mission_key", flat=True
        )
    )
    missions = []
    for key, definition in DAILY_MISSION_DEFINITIONS.items():
        progress = min(definition["target"], progress_by_key[key])
        missions.append(
            {
                "key": key,
                **definition,
                "progress": progress,
                "progress_percent": round(100 * progress / definition["target"]),
                "complete": progress >= definition["target"],
                "claimed": key in claimed_keys,
            }
        )
    return missions


@login_required
def student_dashboard(request):
    """Display progress metrics derived from the signed-in student's data."""
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    attempts = StudentAttempt.objects.filter(
        student=request.user,
        is_complete=True,
    ).select_related("exam_set").prefetch_related("answers__question__section").order_by("-submitted_at", "-started_at")
    tests_taken = attempts.count()

    duration_expression = ExpressionWrapper(
        F("submitted_at") - F("started_at"),
        output_field=DurationField(),
    )
    average_duration = (
        attempts.exclude(submitted_at__isnull=True)
        .annotate(duration=duration_expression)
        .aggregate(average=Avg("duration"))["average"]
    )

    if average_duration:
        total_minutes = int(average_duration.total_seconds() // 60)
        hours, minutes = divmod(total_minutes, 60)
        average_time = f"{hours}h {minutes}m" if hours else f"{minutes}m"
    else:
        average_time = "No data"

    graded_answers = StudentAnswer.objects.filter(
        attempt__student=request.user,
        attempt__is_complete=True,
        is_correct__isnull=False,
    )
    total_answers = graded_answers.count()
    correct_answers = graded_answers.filter(is_correct=True).count()
    accuracy = round((correct_answers / total_answers) * 100) if total_answers else 0

    def objective_skill_accuracy(section_type):
        answers = graded_answers.filter(question__section__section_type=section_type)
        total = answers.count()
        correct = answers.filter(is_correct=True).count()
        return round((correct / total) * 100) if total else 0

    def reviewed_skill_score(section_type):
        average = StudentAnswer.objects.filter(
            attempt__student=request.user,
            attempt__is_complete=True,
            question__section__section_type=section_type,
            manual_score__isnull=False,
        ).aggregate(average=Avg("manual_score"))["average"]
        return round((average / 9) * 100) if average is not None else 0

    skills = [
        {"name": "Reading", "value": objective_skill_accuracy("reading"), "tone": "green", "icon": "bi-book"},
        {"name": "Listening", "value": objective_skill_accuracy("listening"), "tone": "blue", "icon": "bi-headphones"},
        {"name": "Writing", "value": reviewed_skill_score("writing"), "tone": "orange", "icon": "bi-pencil"},
        {"name": "Speaking", "value": reviewed_skill_score("speaking"), "tone": "purple", "icon": "bi-mic"},
    ]

    total_study_minutes = 0
    trend_attempts = []
    completed_dates = set()
    for attempt in reversed(list(attempts)):
        if attempt.submitted_at:
            completed_dates.add(timezone.localtime(attempt.submitted_at).date())
            total_study_minutes += max(
                0, int((attempt.submitted_at - attempt.started_at).total_seconds() // 60)
            )

        objective_answers = [
            answer for answer in attempt.answers.all() if answer.is_correct is not None
        ]
        manual_answers = [
            answer for answer in attempt.answers.all() if answer.manual_score is not None
        ]
        if objective_answers:
            attempt_value = round(
                100
                * sum(answer.is_correct for answer in objective_answers)
                / len(objective_answers)
            )
            attempt_label = f"{attempt_value}%"
        elif manual_answers:
            average_band = sum(answer.manual_score for answer in manual_answers) / len(manual_answers)
            attempt_value = round((average_band / 9) * 100)
            attempt_label = f"Band {average_band:.1f}"
        else:
            continue
        trend_attempts.append(
            {
                "label": timezone.localtime(attempt.submitted_at).strftime("%b %d")
                if attempt.submitted_at
                else "Completed",
                "value": attempt_value,
                "display": attempt_label,
                "title": attempt.exam_set.title,
            }
        )
    trend_attempts = trend_attempts[-7:]
    for trend in trend_attempts:
        trend["height"] = max(9, trend["value"])

    trend_change = None
    if len(trend_attempts) > 1:
        trend_change = trend_attempts[-1]["value"] - trend_attempts[0]["value"]

    question_type_labels = {
        "mcq": "Multiple choice",
        "gap": "Gap fill",
        "matching": "Matching",
    }
    question_type_accuracy = []
    for question_type, label in question_type_labels.items():
        answers = graded_answers.filter(question__question_type=question_type)
        answer_total = answers.count()
        if answer_total:
            question_type_accuracy.append(
                {
                    "name": label,
                    "value": round(100 * answers.filter(is_correct=True).count() / answer_total),
                }
            )

    measured_skills = [skill for skill in skills if skill["value"] or (
        graded_answers.filter(question__section__section_type=skill["name"].lower()).exists()
    )]
    weakest_skill = min(measured_skills, key=lambda skill: skill["value"], default=None)

    today = timezone.localdate()
    streak_days = [
        {
            "label": (today - timedelta(days=offset)).strftime("%a"),
            "active": (today - timedelta(days=offset)) in completed_dates,
        }
        for offset in range(6, -1, -1)
    ]

    recent_attempts = []
    for attempt in attempts[:5]:
        answers = attempt.answers.exclude(is_correct=None)
        total = answers.count()
        correct = answers.filter(is_correct=True).count()
        score = round((correct / total) * 100) if total else None

        duration = "—"
        if attempt.submitted_at:
            minutes = max(
                0,
                int((attempt.submitted_at - attempt.started_at).total_seconds() // 60),
            )
            hours, remaining_minutes = divmod(minutes, 60)
            duration = (
                f"{hours}h {remaining_minutes}m"
                if hours
                else f"{remaining_minutes}m"
            )

        recent_attempts.append(
            {"attempt": attempt, "score": score, "duration": duration}
        )

    xp_goal = 1000
    xp_progress = min(100, round((profile.xp / xp_goal) * 100)) if profile.xp > 0 else 0
    daily_missions = get_daily_missions(request.user)

    return render(
        request,
        "accounts/student_dashboard.html",
        {
            "profile": profile,
            "tests_taken": tests_taken,
            "avg_time": average_time,
            "accuracy": accuracy,
            "skills": skills,
            "recent_attempts": recent_attempts,
            "xp_goal": xp_goal,
            "xp_progress": xp_progress,
            "total_study_minutes": total_study_minutes,
            "trend_attempts": trend_attempts,
            "trend_change": trend_change,
            "question_type_accuracy": question_type_accuracy,
            "weakest_skill": weakest_skill,
            "streak_days": streak_days,
            "daily_missions": daily_missions,
        },
    )


@login_required
@require_POST
def claim_daily_mission(request, mission_key):
    if mission_key not in DAILY_MISSION_DEFINITIONS:
        messages.error(request, "That daily mission is not available.")
        return redirect("student_dashboard")

    mission = next(
        mission for mission in get_daily_missions(request.user) if mission["key"] == mission_key
    )
    if not mission["complete"]:
        messages.error(request, "Complete this mission before claiming its XP.")
        return redirect("student_dashboard")
    if mission["claimed"]:
        messages.info(request, "You already claimed this mission today.")
        return redirect("student_dashboard")

    with transaction.atomic():
        claim, created = DailyMissionClaim.objects.get_or_create(
            user=request.user,
            mission_key=mission_key,
            completed_on=timezone.localdate(),
            defaults={"xp_awarded": mission["xp"]},
        )
        if created:
            profile = StudentProfile.objects.select_for_update().get(user=request.user)
            profile.xp += claim.xp_awarded
            profile.save(update_fields=["xp"])
            messages.success(request, f"Mission complete! You earned {claim.xp_awarded} XP.")
        else:
            messages.info(request, "You already claimed this mission today.")
    return redirect("student_dashboard")


@login_required
def student_settings(request):
    """Allow students to manage the personal settings shown on the dashboard."""
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    form = StudentSettingsForm(
        request.POST or None,
        user=request.user,
        profile=profile,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile settings have been updated.")
        return redirect("student_settings")

    return render(
        request,
        "accounts/student_settings.html",
        {"form": form, "profile": profile},
    )

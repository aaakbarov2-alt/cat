from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import ExamSet, Question, Section


class Command(BaseCommand):
    help = "Create an original, reusable IELTS skills diagnostic test."

    @transaction.atomic
    def handle(self, *args, **options):
        exam, created = ExamSet.objects.get_or_create(
            title="IELTS Skills Diagnostic",
            defaults={
                "description": (
                    "An original three-skill diagnostic covering reading, writing, and "
                    "speaking. This is practice material, not an official IELTS test."
                ),
                "is_published": True,
            },
        )
        if not created and exam.sections.exists():
            self.stdout.write(self.style.WARNING("Diagnostic test already exists; no changes made."))
            return

        exam.description = (
            "An original three-skill diagnostic covering reading, writing, and speaking. "
            "This is practice material, not an official IELTS test."
        )
        exam.is_published = True
        exam.save(update_fields=["description", "is_published"])

        reading = Section.objects.create(
            exam_set=exam,
            order=1,
            section_type="reading",
            time_limit_minutes=20,
            passage_text=(
                "Pocket Parks in Growing Cities\n\n"
                "As cities become more densely populated, planners are looking for ways to "
                "create useful green spaces on small pieces of unused land. These compact areas, "
                "often called pocket parks, may occupy a single vacant lot or a widened section of "
                "pavement. Although they are much smaller than traditional public parks, they can "
                "provide seating, shade, and a quiet place away from traffic.\n\n"
                "The first widely recognised pocket park opened in New York City in 1967. Its "
                "design used trees, a waterfall, and movable chairs to make a narrow site feel calm "
                "and welcoming. Similar projects have since appeared in cities around the world. "
                "Researchers have reported that even brief contact with greenery can reduce stress, "
                "while local businesses may benefit from increased pedestrian activity.\n\n"
                "Pocket parks are not a complete solution to the need for urban open space. They "
                "cannot provide large playing fields, long walking routes, or major wildlife habitats. "
                "They also require regular maintenance and careful lighting. However, when they are "
                "planned with local residents, they can turn neglected land into a shared community asset."
            ),
        )
        Question.objects.bulk_create(
            [
                Question(
                    section=reading,
                    order=1,
                    question_type="mcq",
                    prompt="What is a pocket park usually created on?",
                    options=[
                        "A small unused urban site",
                        "A large wildlife reserve",
                        "A private sports field",
                    ],
                    correct_answer="A small unused urban site",
                ),
                Question(
                    section=reading,
                    order=2,
                    question_type="gap",
                    prompt="In which year did the first widely recognised pocket park open?",
                    correct_answer="1967",
                ),
                Question(
                    section=reading,
                    order=3,
                    question_type="mcq",
                    prompt="Which limitation of pocket parks is mentioned in the passage?",
                    options=[
                        "They cannot provide large playing fields",
                        "They always reduce pedestrian activity",
                        "They cannot contain trees or seating",
                    ],
                    correct_answer="They cannot provide large playing fields",
                ),
            ]
        )

        writing = Section.objects.create(
            exam_set=exam,
            order=2,
            section_type="writing",
            time_limit_minutes=30,
        )
        Question.objects.create(
            section=writing,
            order=1,
            question_type="essay",
            prompt=(
                "Some people believe every neighbourhood should have a public green space. "
                "To what extent do you agree or disagree? Give reasons and relevant examples."
            ),
        )

        speaking = Section.objects.create(
            exam_set=exam,
            order=3,
            section_type="speaking",
            time_limit_minutes=10,
        )
        Question.objects.create(
            section=speaking,
            order=1,
            question_type="speaking",
            prompt=(
                "Describe a public place in your town or city that you enjoy visiting. "
                "Explain where it is, what people do there, and why it is important to you. "
                "Record your response and upload the audio, or type notes as a fallback."
            ),
        )

        self.stdout.write(self.style.SUCCESS("Created and published IELTS Skills Diagnostic."))

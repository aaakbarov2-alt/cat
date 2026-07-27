from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import ExamSet, Question, Section


PASSAGE = (
    "Pocket Parks in Growing Cities\n\n"
    "As cities become more densely populated, planners are looking for ways to create useful "
    "green spaces on small pieces of unused land. These compact areas, often called pocket "
    "parks, may occupy a single vacant lot or a widened section of pavement. Although they are "
    "much smaller than traditional public parks, they can provide seating, shade, and a quiet "
    "place away from traffic.\n\n"
    "The first widely recognised pocket park opened in New York City in 1967. Its design used "
    "trees, a waterfall, and movable chairs to make a narrow site feel calm and welcoming. "
    "Similar projects have since appeared in cities around the world. Researchers report that "
    "even brief contact with greenery can reduce stress, while local businesses may benefit "
    "from increased pedestrian activity.\n\n"
    "Pocket parks are not a complete solution to the need for urban open space. They cannot "
    "provide large playing fields, long walking routes, or major wildlife habitats. However, "
    "when planned with local residents, they can turn neglected land into a shared asset."
)


class Command(BaseCommand):
    help = "Create separate Reading, Listening, Writing, Speaking, and Full Mock tests."

    def add_reading(self, exam, order=1):
        section = Section.objects.create(
            exam_set=exam,
            order=order,
            section_type="reading",
            time_limit_minutes=20,
            passage_text=PASSAGE,
        )
        Question.objects.bulk_create(
            [
                Question(
                    section=section,
                    order=1,
                    question_type="mcq",
                    prompt="What is a pocket park usually created on?",
                    options=["A small unused urban site", "A wildlife reserve", "A sports field"],
                    correct_answer="A small unused urban site",
                ),
                Question(
                    section=section,
                    order=2,
                    question_type="gap",
                    prompt="In which year did the first widely recognised pocket park open?",
                    correct_answer="1967",
                ),
                Question(
                    section=section,
                    order=3,
                    question_type="mcq",
                    prompt="Which limitation is mentioned in the passage?",
                    options=[
                        "They cannot provide large playing fields",
                        "They always reduce foot traffic",
                        "They cannot contain trees",
                    ],
                    correct_answer="They cannot provide large playing fields",
                ),
            ]
        )

    def add_listening(self, exam, order=1):
        section = Section.objects.create(
            exam_set=exam,
            order=order,
            section_type="listening",
            time_limit_minutes=10,
        )
        audio_path = Path(__file__).resolve().parents[2] / "seed_assets" / "community_library.wav"
        with audio_path.open("rb") as audio:
            section.audio_file.save("community_library.wav", File(audio), save=True)
        Question.objects.bulk_create(
            [
                Question(
                    section=section,
                    order=1,
                    question_type="mcq",
                    prompt="What time will the library close on weekdays?",
                    options=["4:00 pm", "7:00 pm", "9:00 pm"],
                    correct_answer="7:00 pm",
                ),
                Question(
                    section=section,
                    order=2,
                    question_type="gap",
                    prompt="On which floor is the new study room?",
                    correct_answer="second",
                ),
                Question(
                    section=section,
                    order=3,
                    question_type="mcq",
                    prompt="What may students take into the study room?",
                    options=["Hot food", "Covered drinks", "Uncovered drinks"],
                    correct_answer="Covered drinks",
                ),
            ]
        )

    def add_writing(self, exam, order=1):
        section = Section.objects.create(
            exam_set=exam,
            order=order,
            section_type="writing",
            time_limit_minutes=40,
        )
        Question.objects.create(
            section=section,
            order=1,
            question_type="essay",
            prompt=(
                "Some people believe every neighbourhood should have a public green space. "
                "To what extent do you agree or disagree? Give reasons and relevant examples."
            ),
        )

    def add_speaking(self, exam, order=1):
        section = Section.objects.create(
            exam_set=exam,
            order=order,
            section_type="speaking",
            time_limit_minutes=15,
        )
        Question.objects.bulk_create(
            [
                Question(
                    section=section,
                    order=1,
                    question_type="speaking",
                    prompt="Describe a public place in your town or city that you enjoy visiting.",
                ),
                Question(
                    section=section,
                    order=2,
                    question_type="speaking",
                    prompt="Why are shared public spaces important for a community?",
                ),
            ]
        )

    def create_exam(self, title, category, description, section_builders):
        exam, created = ExamSet.objects.update_or_create(
            title=title,
            defaults={
                "category": category,
                "description": description,
                "is_published": True,
            },
        )
        if not created and exam.sections.exists():
            return exam, False
        for order, builder in enumerate(section_builders, start=1):
            builder(exam, order)
        return exam, True

    @transaction.atomic
    def handle(self, *args, **options):
        definitions = [
            (
                "Reading Practice 1",
                "reading",
                "Focused reading practice with an original passage and objective questions.",
                [self.add_reading],
            ),
            (
                "Listening Practice 1",
                "listening",
                "Focused listening practice with original audio and objective questions.",
                [self.add_listening],
            ),
            (
                "Writing Practice 1",
                "writing",
                "Timed essay practice ready for instructor review and band feedback.",
                [self.add_writing],
            ),
            (
                "Speaking Practice 1",
                "speaking",
                "Speaking prompts with audio-response upload and instructor review.",
                [self.add_speaking],
            ),
            (
                "IELTS Full Mock Test 1",
                "full",
                "A compact full mock covering Listening, Reading, Writing, and Speaking.",
                [self.add_listening, self.add_reading, self.add_writing, self.add_speaking],
            ),
        ]
        created_count = 0
        for definition in definitions:
            _, created = self.create_exam(*definition)
            created_count += int(created)

        ExamSet.objects.filter(title="IELTS Skills Diagnostic").update(is_published=False)
        self.stdout.write(
            self.style.SUCCESS(
                f"Practice library ready: {len(definitions)} published categories "
                f"({created_count} newly populated)."
            )
        )

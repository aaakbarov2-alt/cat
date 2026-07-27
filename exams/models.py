from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator

class ExamSet(models.Model):
    DELIVERY_MODES = [("native", "Adaptive platform test"), ("exact_html", "Exact uploaded HTML")]
    CATEGORY_CHOICES = [
        ("reading", "Reading"),
        ("listening", "Listening"),
        ("writing", "Writing"),
        ("speaking", "Speaking"),
        ("full", "Full Mock Test"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="full")
    is_published = models.BooleanField(default=False)
    delivery_mode = models.CharField(max_length=20, choices=DELIVERY_MODES, default="native")
    source_html = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_ready(self):
        if self.delivery_mode == "exact_html":
            return bool((self.source_html or "").strip())
        sections = list(self.sections.all())
        return bool(sections) and all(section.questions.exists() for section in sections)

class Section(models.Model):
    SECTION_TYPES = [('listening','Listening'), ('reading','Reading'),
                      ('writing','Writing'), ('speaking','Speaking')]
    exam_set = models.ForeignKey(ExamSet, on_delete=models.CASCADE, related_name='sections')
    order = models.PositiveIntegerField(default=1)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    time_limit_minutes = models.PositiveIntegerField()
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    passage_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.exam_set.title} - {self.section_type}"

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam_set", "order"],
                name="unique_section_order_per_exam",
            ),
        ]

class QuestionGroup(models.Model):
    LAYOUT_TYPES = [("notes", "Notes / summary"), ("table", "Table / form"), ("flow", "Flow chart")]
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="question_groups")
    key = models.SlugField(max_length=60, help_text="Short identifier used by Excel, for example notes_1.")
    order = models.PositiveIntegerField(default=1)
    layout_type = models.CharField(max_length=20, choices=LAYOUT_TYPES, default="notes")
    title = models.CharField(max_length=200, blank=True)
    instructions = models.TextField(blank=True)
    layout_html = models.TextField(help_text="Formatted worksheet HTML. Insert blanks with [[question number]], for example [[1]].")

    def __str__(self):
        return self.title or f"{self.section} — {self.key}"

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["section", "key"], name="unique_question_group_key_per_section")]

class Question(models.Model):
    QUESTION_TYPES = [('mcq','Multiple Choice'), ('gap','Gap Fill'),
                       ('matching','Matching'), ('essay','Essay'), ('speaking','Speaking Prompt')]
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='questions')
    group = models.ForeignKey(QuestionGroup, on_delete=models.SET_NULL, related_name="questions", blank=True, null=True)
    order = models.PositiveIntegerField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    prompt = models.TextField()
    options = models.JSONField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)
    explanation = models.TextField(
        blank=True,
        help_text="Shown to students in review mode after they submit the test.",
    )
    passage_reference = models.TextField(
        blank=True,
        help_text="Optional exact sentence or short excerpt from the reading passage that supports this answer.",
    )

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:40]}"

    def clean(self):
        errors = {}
        if self.group_id and self.section_id and self.group.section_id != self.section_id:
            errors["group"] = "The question group must belong to the same section."
        if self.question_type in {"mcq", "gap", "matching"} and not (
            self.correct_answer or ""
        ).strip():
            errors["correct_answer"] = "Objective questions require a correct answer."
        if self.question_type == "mcq":
            if not isinstance(self.options, list) or len(self.options) < 2:
                errors["options"] = "Multiple-choice questions require at least two options."
            elif self.correct_answer and self.correct_answer not in self.options:
                errors["correct_answer"] = "The correct answer must match one of the options."
        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "order"],
                name="unique_question_order_per_section",
            ),
        ]

class StudentAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam_set = models.ForeignKey(ExamSet, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    current_section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    section_started_at = models.DateTimeField(null=True, blank=True)
    section_deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "exam_set"],
                condition=Q(is_complete=False),
                name="unique_active_attempt_per_exam",
            ),
        ]

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(StudentAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    audio_response = models.FileField(
        upload_to="speaking_responses/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["mp3", "m4a", "wav", "webm", "ogg"])],
        help_text="Optional speaking response. Maximum size: 20 MB.",
    )
    is_correct = models.BooleanField(null=True)
    manual_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        help_text="Manual band score from 0.0 to 9.0 for writing or speaking responses.",
    )

    def clean(self):
        if self.manual_score is not None and self.question.question_type not in {
            "essay",
            "speaking",
        }:
            raise ValidationError(
                {"manual_score": "Manual scores are only valid for writing or speaking answers."}
            )
        if self.audio_response and self.audio_response.size > 20 * 1024 * 1024:
            raise ValidationError({"audio_response": "Audio responses must be 20 MB or smaller."})
        if self.audio_response and self.question.question_type != "speaking":
            raise ValidationError(
                {"audio_response": "Audio responses are only valid for speaking questions."}
            )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_answer_per_attempt_question",
            ),
        ]

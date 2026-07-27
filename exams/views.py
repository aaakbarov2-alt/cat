import math
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Avg
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import ExamSet, Section, StudentAnswer, StudentAttempt
from .grading import academic_reading_band
from accounts.models import StudentProfile


SUBMISSION_GRACE_SECONDS = 15
MAX_AUDIO_RESPONSE_SIZE = 20 * 1024 * 1024
AUDIO_RESPONSE_VALIDATOR = FileExtensionValidator(["mp3", "m4a", "wav", "webm", "ogg"])


def activate_section(attempt, section, now=None):
    """Start a section once and persist its authoritative server deadline."""
    if attempt.current_section_id == section.id and attempt.section_deadline:
        return

    now = now or timezone.now()
    attempt.current_section = section
    attempt.section_started_at = now
    attempt.section_deadline = now + timedelta(minutes=section.time_limit_minutes)
    attempt.save(
        update_fields=["current_section", "section_started_at", "section_deadline"]
    )


@login_required
def exam_list(request):
    status_filter = request.GET.get("status", "all")
    skill_filter = request.GET.get("skill", "all")
    valid_filters = {"all", "not_started", "in_progress", "completed"}
    valid_skills = {"all", "reading", "listening", "writing", "speaking", "full"}
    if status_filter not in valid_filters:
        status_filter = "all"
    if skill_filter not in valid_skills:
        skill_filter = "all"

    published_exams = ExamSet.objects.filter(is_published=True)
    skill_counts = {
        category: published_exams.filter(category=category).count()
        for category in ("reading", "listening", "writing", "speaking", "full")
    }
    all_total = published_exams.count()
    if skill_filter != "all":
        published_exams = published_exams.filter(category=skill_filter)
    exam_sets = published_exams.prefetch_related("sections__questions")
    latest_attempts = {}
    for attempt in StudentAttempt.objects.filter(student=request.user).order_by("-started_at"):
        latest_attempts.setdefault(attempt.exam_set_id, attempt)

    exam_data = []
    counts = {"not_started": 0, "in_progress": 0, "completed": 0}

    for exam_set in exam_sets:
        sections = list(exam_set.sections.all())
        is_exact = exam_set.delivery_mode == "exact_html"
        attempt = latest_attempts.get(exam_set.id)
        if attempt is None:
            status = "not_started"
        elif attempt.is_complete:
            status = "completed"
        else:
            status = "in_progress"

        counts[status] += 1
        score = None
        if status == "completed":
            answers = attempt.answers.exclude(is_correct=None)
            total = answers.count()
            correct = answers.filter(is_correct=True).count()
            score = f"{correct}/{total}" if total else None

        question_orders = [question.order for section in sections for question in section.questions.all()]
        part = "all"
        if len(sections) == 1 and question_orders and exam_set.category in {"reading", "listening"}:
            first_order = min(question_orders)
            part = "p3" if first_order >= 27 else "p2" if first_order >= 14 else "p1"

        exam_data.append(
            {
                "exam_set": exam_set,
                "status": status,
                "attempt": attempt,
                "score": score,
                "is_exact": is_exact,
                "section_count": 1 if is_exact else len(sections),
                "question_count": sum(len(section.questions.all()) for section in sections),
                "total_minutes": sum(section.time_limit_minutes for section in sections),
                "section_types": ["Original HTML"] if is_exact else [section.get_section_type_display() for section in sections],
                "part": part,
            }
        )

    if status_filter != "all":
        exam_data = [item for item in exam_data if item["status"] == status_filter]

    return render(
        request,
        "exams/exam_list.html",
        {
            "exam_data": exam_data,
            "counts": counts,
            "total": len(exam_sets),
            "all_total": all_total,
            "status_filter": status_filter,
            "skill_filter": skill_filter,
            "skill_counts": skill_counts,
        },
    )


@login_required
def exam_detail(request, exam_set_id):
    exam_set = get_object_or_404(
        ExamSet.objects.prefetch_related("sections__questions"),
        id=exam_set_id,
        is_published=True,
    )
    sections = list(exam_set.sections.all())
    active_attempt = StudentAttempt.objects.filter(
        student=request.user,
        exam_set=exam_set,
        is_complete=False,
    ).first()
    return render(
        request,
        "exams/exam_detail.html",
        {
            "exam_set": exam_set,
            "sections": sections,
            "active_attempt": active_attempt,
            "total_minutes": sum(section.time_limit_minutes for section in sections),
            "question_count": sum(len(section.questions.all()) for section in sections),
            "is_ready": exam_set.is_ready,
        },
    )


@login_required
@require_POST
def start_exam(request, exam_set_id):
    exam_set = get_object_or_404(
        ExamSet.objects.prefetch_related("sections__questions"),
        id=exam_set_id,
        is_published=True,
    )
    if not exam_set.is_ready:
        messages.error(request, "This test is not ready to begin. Please contact support.")
        return redirect("exam_detail", exam_set_id=exam_set.id)
    attempt, _ = StudentAttempt.objects.get_or_create(
        student=request.user,
        exam_set=exam_set,
        is_complete=False,
    )
    if exam_set.delivery_mode == "exact_html":
        return redirect("exact_exam", attempt_id=attempt.id)
    first_section = exam_set.sections.order_by("order", "id").first()
    if first_section is None:
        return redirect("exam_list")

    if attempt.current_section_id is None:
        activate_section(attempt, first_section)

    return redirect(
        "take_section",
        attempt_id=attempt.id,
        section_id=attempt.current_section_id,
    )


@login_required
@require_POST
def retake_exam(request, attempt_id):
    """Replace an unfinished attempt with a fresh one; completed attempts remain saved."""
    attempt = get_object_or_404(
        StudentAttempt.objects.select_related("exam_set"),
        id=attempt_id,
        student=request.user,
        is_complete=False,
    )
    exam_set = attempt.exam_set
    attempt.delete()
    fresh_attempt = StudentAttempt.objects.create(student=request.user, exam_set=exam_set)
    if exam_set.delivery_mode == "exact_html":
        return redirect("exact_exam", attempt_id=fresh_attempt.id)
    first_section = exam_set.sections.order_by("order", "id").first()
    if first_section is None:
        fresh_attempt.delete()
        return redirect("exam_list")
    activate_section(fresh_attempt, first_section)
    return redirect(
        "take_section",
        attempt_id=fresh_attempt.id,
        section_id=first_section.id,
    )


@login_required
def exact_exam(request, attempt_id):
    attempt = get_object_or_404(
        StudentAttempt.objects.select_related("exam_set"), id=attempt_id,
        student=request.user, is_complete=False, exam_set__delivery_mode="exact_html",
    )
    return render(request, "exams/exact_exam.html", {"attempt": attempt, "exam_set": attempt.exam_set})


@login_required
@xframe_options_sameorigin
def exact_exam_content(request, attempt_id):
    attempt = get_object_or_404(
        StudentAttempt.objects.select_related("exam_set"), id=attempt_id,
        student=request.user, is_complete=False, exam_set__delivery_mode="exact_html",
    )
    response = HttpResponse(attempt.exam_set.source_html, content_type="text/html; charset=utf-8")
    response["Content-Security-Policy"] = (
        "sandbox allow-scripts allow-forms allow-modals allow-downloads; "
        "default-src 'self' data: blob: https:; script-src 'unsafe-inline' https:; "
        "style-src 'unsafe-inline' https:; img-src data: blob: https:; "
        "media-src data: blob: https:; connect-src https:"
    )
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def complete_exact_exam(request, attempt_id):
    attempt = get_object_or_404(
        StudentAttempt.objects.select_related("exam_set"), id=attempt_id,
        student=request.user, is_complete=False, exam_set__delivery_mode="exact_html",
    )
    attempt.is_complete = True
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["is_complete", "submitted_at"])
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    profile.xp += 50
    profile.save(update_fields=["xp"])
    messages.success(request, "Exact HTML test marked as complete.")
    return redirect("exam_list")


@login_required
def take_section(request, attempt_id, section_id):
    attempt = get_object_or_404(
        StudentAttempt.objects.select_related("exam_set"),
        id=attempt_id,
        student=request.user,
        is_complete=False,
    )
    section = get_object_or_404(
        Section.objects.prefetch_related("questions", "question_groups__questions"),
        id=section_id,
        exam_set=attempt.exam_set,
    )

    if attempt.current_section_id is None:
        first_section = attempt.exam_set.sections.order_by("order", "id").first()
        if first_section is None:
            return redirect("exam_list")
        activate_section(attempt, first_section)

    if section.id != attempt.current_section_id:
        return redirect(
            "take_section",
            attempt_id=attempt.id,
            section_id=attempt.current_section_id,
        )

    now = timezone.now()
    deadline = attempt.section_deadline
    remaining_seconds = max(0, math.ceil((deadline - now).total_seconds()))

    if request.method == "POST":
        submission_is_late = now > deadline + timedelta(seconds=SUBMISSION_GRACE_SECONDS)

        for question in section.questions.filter(question_type="speaking"):
            uploaded_audio = request.FILES.get(f"q{question.id}_audio")
            if uploaded_audio is None:
                continue
            try:
                AUDIO_RESPONSE_VALIDATOR(uploaded_audio)
                if uploaded_audio.size > MAX_AUDIO_RESPONSE_SIZE:
                    raise ValidationError("Audio responses must be 20 MB or smaller.")
            except ValidationError as error:
                messages.error(request, error.messages[0])
                return redirect(
                    "take_section",
                    attempt_id=attempt.id,
                    section_id=section.id,
                )

        for question in section.questions.all():
            answer_text = request.POST.get(f"q{question.id}", "").strip()
            audio_response = request.FILES.get(f"q{question.id}_audio")
            if submission_is_late:
                answer_text = ""
                audio_response = None
            is_correct = None
            if question.question_type in {"mcq", "gap", "matching"}:
                expected = (question.correct_answer or "").strip().casefold()
                is_correct = answer_text.casefold() == expected

            defaults = {"answer_text": answer_text, "is_correct": is_correct}
            if audio_response is not None:
                defaults["audio_response"] = audio_response
            StudentAnswer.objects.update_or_create(
                attempt=attempt,
                question=question,
                defaults=defaults,
            )

        next_section = (
            Section.objects.filter(
                exam_set=attempt.exam_set,
                order__gt=section.order,
            )
            .order_by("order", "id")
            .first()
        )
        if next_section:
            activate_section(attempt, next_section, now=now)
            return redirect(
                "take_section",
                attempt_id=attempt.id,
                section_id=next_section.id,
            )

        attempt.is_complete = True
        attempt.submitted_at = now
        attempt.current_section = None
        attempt.section_started_at = None
        attempt.section_deadline = None
        attempt.save(
            update_fields=[
                "is_complete",
                "submitted_at",
                "current_section",
                "section_started_at",
                "section_deadline",
            ]
        )
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        today = timezone.localdate(now)
        if profile.last_activity_date != today:
            if profile.last_activity_date == today - timedelta(days=1):
                profile.streak += 1
            else:
                profile.streak = 1
            profile.last_activity_date = today
        profile.xp += 50 + (attempt.answers.count() * 10)
        profile.save(update_fields=["xp", "streak", "last_activity_date"])
        return redirect("results", attempt_id=attempt.id)

    grouped_question_ids = set()
    question_blocks = []
    for group in section.question_groups.all():
        group_questions = list(group.questions.all())
        if not group_questions:
            continue
        grouped_question_ids.update(question.id for question in group_questions)
        question_blocks.append({"kind": "group", "group": group, "order": min(question.order for question in group_questions)})
    for question in section.questions.all():
        if question.id not in grouped_question_ids:
            question_blocks.append({"kind": "question", "question": question, "order": question.order})
    question_blocks.sort(key=lambda block: (block["order"], 0 if block["kind"] == "group" else 1))
    question_orders = list(section.questions.values_list("order", flat=True))

    return render(
        request,
        "exams/take_section.html",
        {
            "attempt": attempt,
            "section": section,
            "remaining_seconds": remaining_seconds,
            "section_number": list(
                attempt.exam_set.sections.order_by("order", "id").values_list(
                    "id", flat=True
                )
            ).index(section.id)
            + 1,
            "section_total": attempt.exam_set.sections.count(),
            "question_blocks": question_blocks,
            "first_question_order": min(question_orders) if question_orders else None,
            "last_question_order": max(question_orders) if question_orders else None,
        },
    )


@login_required
def results(request, attempt_id):
    attempt = get_object_or_404(
        StudentAttempt.objects.select_related("exam_set"),
        id=attempt_id,
        student=request.user,
        is_complete=True,
    )
    answers = attempt.answers.select_related("question__section").order_by(
        "question__section__order", "question__order", "id"
    )
    objective_answers = answers.exclude(is_correct=None)
    manually_graded = answers.filter(manual_score__isnull=False)
    pending_manual = answers.filter(
        is_correct=None,
        manual_score__isnull=True,
    ).count()
    average_manual_score = manually_graded.aggregate(average=Avg("manual_score"))["average"]
    correct_count = objective_answers.filter(is_correct=True).count()
    total_gradable = objective_answers.count()
    reading_answers = objective_answers.filter(question__section__section_type="reading")
    reading_band = reading_equivalent = None
    reading_band_estimated = False
    if reading_answers.exists():
        reading_correct = reading_answers.filter(is_correct=True).count()
        reading_band, reading_equivalent, reading_band_estimated = academic_reading_band(
            reading_correct, reading_answers.count()
        )
    reading_passages = list(
        attempt.exam_set.sections.filter(section_type="reading")
        .exclude(passage_text__isnull=True)
        .exclude(passage_text="")
    )
    reading_review_answers = list(
        answers.filter(question__section__section_type="reading")
    )
    is_reading_only = not attempt.exam_set.sections.exclude(
        section_type="reading"
    ).exists()
    return render(
        request,
        "exams/results.html",
        {
            "attempt": attempt,
            "answers": answers,
            "correct_count": correct_count,
            "total_gradable": total_gradable,
            "pending_manual": pending_manual,
            "average_manual_score": average_manual_score,
            "reading_band": reading_band,
            "reading_equivalent": reading_equivalent,
            "reading_band_estimated": reading_band_estimated,
            "reading_passages": reading_passages,
            "reading_review_answers": reading_review_answers,
            "use_split_reading_review": bool(
                is_reading_only and reading_passages and reading_review_answers
            ),
        },
    )

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from exams.models import ExamSet, StudentAttempt


def _chart_points(values, maximum, width=680, height=170, padding=18):
    """Return stable SVG points for a seven-day chart, including an empty state."""
    maximum = max(maximum, 1)
    usable_width = width - padding * 2
    usable_height = height - padding * 2
    points = []
    for index, value in enumerate(values):
        x = padding + usable_width * index / max(len(values) - 1, 1)
        y = padding + usable_height - (value / maximum * usable_height)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def dashboard_callback(request, context):
    today = timezone.localdate()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    starts = [timezone.make_aware(datetime.combine(day, time.min)) for day in days]
    ends = [start + timedelta(days=1) for start in starts]

    attempt_counts = []
    active_student_counts = []
    for start, end in zip(starts, ends):
        attempts = StudentAttempt.objects.filter(started_at__gte=start, started_at__lt=end)
        attempt_counts.append(attempts.count())
        active_student_counts.append(attempts.values("student_id").distinct().count())

    total_attempts = StudentAttempt.objects.count()
    seven_day_attempts = sum(attempt_counts)
    active_students = StudentAttempt.objects.filter(started_at__gte=starts[0]).values("student_id").distinct().count()
    recent_tests = (
        ExamSet.objects.annotate(
            question_count=Count("sections__questions", distinct=True),
            attempt_count=Count("studentattempt", distinct=True),
        )
        .order_by("-created_at")[:6]
    )
    chart_maximum = max([*attempt_counts, *active_student_counts, 1])
    context.update(
        {
            "dashboard_metrics": [
                {
                    "label": "Published tests",
                    "value": ExamSet.objects.filter(is_published=True).count(),
                    "detail": "Tests available to students",
                    "icon": "description",
                    "link": "/admin/exams/examset/?is_published__exact=1",
                },
                {
                    "label": "Student attempts",
                    "value": total_attempts,
                    "detail": f"{seven_day_attempts} started in the last 7 days",
                    "icon": "monitoring",
                    "link": "/admin/exams/studentattempt/",
                },
                {
                    "label": "Active students",
                    "value": active_students,
                    "detail": "Students active in the last 7 days",
                    "icon": "group",
                    "link": "/admin/auth/user/",
                },
            ],
            "chart_labels": [f"{day.strftime('%b')} {day.day}" for day in days],
            "attempt_points": _chart_points(attempt_counts, chart_maximum),
            "active_points": _chart_points(active_student_counts, chart_maximum),
            "has_chart_activity": any(attempt_counts),
            "recent_tests": recent_tests,
            "total_users": get_user_model().objects.count(),
        }
    )
    return context

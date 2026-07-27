from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import FileResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import strip_tags
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .forms import ExcelExamImportForm, HtmlExamImportForm, ListeningTestSetupForm, QuestionAdminForm, QuestionGroupAdminForm, SectionAdminForm
from .excel_importer import ExcelImportError, build_excel_template, parse_excel_test
from .html_importer import create_exam_from_payload
from .models import ExamSet, Question, QuestionGroup, Section, StudentAnswer, StudentAttempt


HTML_IMPORT_SALT = "exams.html-import.v1"
EXCEL_IMPORT_SALT = "exams.excel-import.v1"

# The custom IELTS Blue sidebar lives in admin/base_site.html. Django otherwise
# skips the navigation block entirely when its built-in sidebar flag is disabled.


_original_admin_index = admin.site.index


def ielts_admin_index(request, extra_context=None):
    context = {
        "dashboard_metrics": [
            {"label": "Total tests", "value": ExamSet.objects.count(), "icon": "▤"},
            {
                "label": "Published tests",
                "value": ExamSet.objects.filter(is_published=True).count(),
                "icon": "✓",
            },
            {"label": "Test attempts", "value": StudentAttempt.objects.count(), "icon": "↗"},
            {"label": "Students", "value": get_user_model().objects.count(), "icon": "◉"},
        ],
        "recent_tests": ExamSet.objects.annotate(section_count=Count("sections"))
        .order_by("-created_at")[:6],
    }
    if extra_context:
        context.update(extra_context)
    return _original_admin_index(request, extra_context=context)




class SectionInline(TabularInline):
    model = Section
    extra = 0
    fields = ("order", "section_type", "time_limit_minutes")
    show_change_link = True


class QuestionInline(StackedInline):
    model = Question
    form = QuestionAdminForm
    extra = 0
    fields = (
        "order",
        "group",
        "question_type",
        "prompt",
        "options",
        "correct_answer",
        "explanation",
        "passage_reference",
    )

class QuestionGroupInline(StackedInline):
    model = QuestionGroup
    form = QuestionGroupAdminForm
    extra = 0
    fields = ("key", "order", "layout_type", "title", "instructions", "layout_html")


@admin.register(ExamSet)
class ExamSetAdmin(ModelAdmin):
    list_display = ("title", "category", "delivery_mode", "is_published", "section_total", "created_at")
    list_filter = ("category", "is_published", "created_at")
    search_fields = ("title", "description")
    inlines = (SectionInline,)
    actions = ("publish_ready_tests", "unpublish_tests")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        category = request.GET.get("category")
        valid_categories = {value for value, _label in ExamSet.CATEGORY_CHOICES}
        if category in valid_categories:
            initial["category"] = category
        return initial

    def get_fields(self, request, obj=None):
        # Raw exact-mode documents are deliberately kept out of the ordinary
        # edit form. They are replaced through the importer, not a huge textarea.
        return ("title", "description", "category", "delivery_mode", "is_published")

    def get_inlines(self, request, obj):
        if obj and obj.delivery_mode == "exact_html":
            return ()
        return super().get_inlines(request, obj)

    def get_urls(self):
        """Expose the preserved workbook importer as an optional admin tool.

        Normal test creation stays in the standard Unfold forms; this route is
        deliberately separate so importing a prepared workbook never replaces
        the ordinary editor.
        """
        custom_urls = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="exams_examset_import_excel",
            ),
            path(
                "excel-template/",
                self.admin_site.admin_view(self.excel_template_view),
                name="exams_examset_excel_template",
            ),
        ]
        return custom_urls + super().get_urls()

    def create_listening_view(self, request):
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Create Listening test",
            "form": ListeningTestSetupForm(),
        }
        if request.method == "POST":
            form = ListeningTestSetupForm(request.POST, request.FILES)
            context["form"] = form
            if form.is_valid():
                exam = ExamSet.objects.create(
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    category="listening",
                    is_published=False,
                )
                section = Section.objects.create(
                    exam_set=exam,
                    order=1,
                    section_type="listening",
                    time_limit_minutes=form.cleaned_data["time_limit_minutes"],
                    audio_file=form.cleaned_data["audio_file"],
                )
                self.message_user(
                    request,
                    "Listening test created as a draft. Now add its questions.",
                    level=messages.SUCCESS,
                )
                return HttpResponseRedirect(
                    reverse("admin:exams_section_change", args=(section.pk,))
                )
        return TemplateResponse(request, "admin/exams/examset/create_listening.html", context)

    def excel_template_view(self, request):
        return FileResponse(
            build_excel_template(),
            as_attachment=True,
            filename="IELTS_Test_Import_Template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def import_excel_view(self, request):
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import Excel tests",
            "form": ExcelExamImportForm(),
            "preview": None,
        }
        if request.method == "POST" and request.POST.get("confirm_import"):
            try:
                payload = signing.loads(
                    request.POST.get("import_payload", ""),
                    salt=EXCEL_IMPORT_SALT,
                    max_age=60 * 60,
                )
                exam = create_exam_from_payload(payload)
            except signing.BadSignature:
                self.message_user(request, "The preview expired. Upload the workbook again.", level=messages.ERROR)
                return HttpResponseRedirect(reverse("admin:exams_examset_import_excel"))
            except (KeyError, ValidationError, ValueError) as error:
                self.message_user(request, f"Import failed: {error}", level=messages.ERROR)
                return HttpResponseRedirect(reverse("admin:exams_examset_import_excel"))
            state = "published" if exam.is_published else "saved as a draft"
            self.message_user(request, f"{exam.title} imported successfully and {state}.", level=messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:exams_examset_change", args=(exam.pk,)))

        if request.method == "POST":
            form = ExcelExamImportForm(request.POST, request.FILES)
            context["form"] = form
            if form.is_valid():
                try:
                    payload = parse_excel_test(form.cleaned_data["excel_file"], publish=form.cleaned_data["publish"])
                except ExcelImportError as error:
                    form.add_error("excel_file", error.messages[0])
                else:
                    context["preview"] = payload
                    context["preview_question_count"] = sum(len(section["questions"]) for section in payload["sections"])
                    context["preview_group_count"] = sum(len(section.get("groups", [])) for section in payload["sections"])
                    context["import_payload"] = signing.dumps(payload, salt=EXCEL_IMPORT_SALT, compress=True)
        return TemplateResponse(request, "admin/exams/examset/import_excel.html", context)

    def import_html_view(self, request):
        requested_type = request.GET.get("type", "reading")
        valid_section_types = {value for value, _label in Section.SECTION_TYPES}
        if requested_type not in valid_section_types:
            requested_type = "reading"
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import HTML tests",
            "form": HtmlExamImportForm(
                initial={
                    "section_type": requested_type,
                }
            ),
            "preview_exact": False,
        }

        if request.method == "POST" and request.POST.get("confirm_import"):
            try:
                payload = signing.loads(
                    request.POST.get("import_payload", ""),
                    salt=HTML_IMPORT_SALT,
                    max_age=60 * 60,
                )
                exam = create_exam_from_payload(payload)
            except signing.BadSignature:
                self.message_user(
                    request,
                    "The import preview expired or was changed. Upload the HTML again.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(reverse("admin:exams_examset_import_html"))
            except (KeyError, ValidationError, ValueError) as error:
                self.message_user(request, f"Import failed: {error}", level=messages.ERROR)
                return HttpResponseRedirect(reverse("admin:exams_examset_import_html"))

            state = "published" if exam.is_published else "saved as a draft"
            self.message_user(
                request,
                f"{exam.title} imported successfully and {state}.",
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect(
                reverse("admin:exams_examset_change", args=(exam.pk,))
            )

        if request.method == "POST":
            form = HtmlExamImportForm(request.POST, request.FILES)
            context["form"] = form
            if form.is_valid():
                upload = form.cleaned_data["html_files"][0]
                raw = upload.read()
                try:
                    source_html = raw.decode("utf-8")
                except UnicodeDecodeError:
                    source_html = raw.decode("cp1252")
                if "<html" not in source_html.lower() and "<body" not in source_html.lower():
                    form.add_error("html_files", "The uploaded file must be a complete HTML document containing an HTML or BODY element.")
                else:
                    payload = {
                        "title": form.cleaned_data["title"],
                        "description": form.cleaned_data["description"],
                        "category": form.cleaned_data["section_type"],
                        "delivery_mode": "exact_html",
                        "source_html": source_html,
                        "publish": form.cleaned_data["publish"],
                        "sections": [],
                    }
                    context.update({
                        "preview_exact": True,
                        "preview_source_name": upload.name,
                        "preview_file_size": len(raw),
                        "import_payload": signing.dumps(payload, salt=HTML_IMPORT_SALT, compress=True),
                        "preview_title": payload["title"],
                        "preview_publish": payload["publish"],
                        "total_questions": "Original HTML",
                    })

        return TemplateResponse(
            request,
            "admin/exams/examset/import_html.html",
            context,
        )

    @admin.display(description="Sections")
    def section_total(self, obj):
        return obj.sections.count()

    @admin.action(description="Publish selected ready tests")
    def publish_ready_tests(self, request, queryset):
        published = 0
        skipped = []
        for exam_set in queryset.prefetch_related("sections__questions"):
            if exam_set.is_ready:
                exam_set.is_published = True
                exam_set.save(update_fields=["is_published"])
                published += 1
            else:
                skipped.append(exam_set.title)
        if published:
            self.message_user(request, f"Published {published} ready test(s).")
        if skipped:
            self.message_user(
                request,
                "Not published because sections or questions are missing: "
                + ", ".join(skipped),
                level=messages.WARNING,
            )

    @admin.action(description="Unpublish selected tests")
    def unpublish_tests(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Unpublished {updated} test(s).")


@admin.register(Section)
class SectionAdmin(ModelAdmin):
    form = SectionAdminForm
    list_display = (
        "exam_set",
        "order",
        "section_type",
        "time_limit_minutes",
        "question_total",
    )
    list_filter = ("section_type", "exam_set")
    search_fields = ("exam_set__title", "passage_text")
    inlines = (QuestionGroupInline, QuestionInline)
    @admin.display(description="Questions")
    def question_total(self, obj):
        return obj.questions.count()


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    form = QuestionAdminForm
    list_display = ("short_prompt", "section", "order", "question_type")
    list_filter = ("question_type", "section__section_type", "section__exam_set")
    search_fields = (
        "prompt",
        "correct_answer",
        "explanation",
        "passage_reference",
        "section__exam_set__title",
    )
    fields = (
        "section",
        "group",
        "order",
        "question_type",
        "prompt",
        "options",
        "correct_answer",
        "explanation",
        "passage_reference",
    )

    @admin.display(description="Question")
    def short_prompt(self, obj):
        return strip_tags(obj.prompt)[:70]


@admin.register(QuestionGroup)
class QuestionGroupAdmin(ModelAdmin):
    form = QuestionGroupAdminForm
    list_display = ("title", "section", "key", "layout_type", "order")
    list_filter = ("layout_type", "section__section_type", "section__exam_set")
    search_fields = ("title", "key", "instructions", "section__exam_set__title")


@admin.register(StudentAttempt)
class StudentAttemptAdmin(ModelAdmin):
    list_display = ("student", "exam_set", "is_complete", "started_at", "submitted_at")
    list_filter = ("is_complete", "exam_set", "started_at")
    search_fields = ("student__username", "student__email", "exam_set__title")
    readonly_fields = ("started_at", "submitted_at")


@admin.register(StudentAnswer)
class StudentAnswerAdmin(ModelAdmin):
    list_display = (
        "student_name",
        "exam_name",
        "question_kind",
        "is_correct",
        "manual_score",
    )
    list_filter = (
        "question__question_type",
        "question__section__section_type",
        "attempt__exam_set",
        "is_correct",
    )
    search_fields = (
        "attempt__student__username",
        "attempt__student__email",
        "answer_text",
        "question__prompt",
    )
    readonly_fields = ("attempt", "question", "answer_text", "audio_response", "is_correct")
    fields = (
        "attempt",
        "question",
        "answer_text",
        "audio_response",
        "is_correct",
        "manual_score",
    )

    @admin.display(description="Student")
    def student_name(self, obj):
        return obj.attempt.student.username

    @admin.display(description="Test")
    def exam_name(self, obj):
        return obj.attempt.exam_set.title

    @admin.display(description="Type")
    def question_kind(self, obj):
        return obj.question.get_question_type_display()

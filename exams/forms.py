from django import forms
from django.core.exceptions import ValidationError
import bleach

from .models import ExamSet, Question, QuestionGroup, Section


RICH_TEXT_TAGS = ["p", "br", "strong", "em", "u", "h2", "h3", "ul", "ol", "li", "blockquote", "a"]
RICH_TEXT_ATTRIBUTES = {"a": ["href", "title", "target", "rel"]}


class SectionAdminForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = "__all__"
        widgets = {
            "passage_text": forms.Textarea(
                attrs={
                    "data-rich-text-editor": "passage",
                    "rows": 18,
                }
            )
        }

    def clean_passage_text(self):
        value = self.cleaned_data.get("passage_text") or ""
        return bleach.clean(
            value,
            tags=RICH_TEXT_TAGS,
            attributes=RICH_TEXT_ATTRIBUTES,
            protocols=["http", "https", "mailto"],
            strip=True,
        )


class QuestionAdminForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        widgets = {
            "prompt": forms.Textarea(
                attrs={
                    "data-rich-text-editor": "prompt",
                    "rows": 7,
                }
            )
        }

    def clean_prompt(self):
        value = self.cleaned_data.get("prompt") or ""
        return bleach.clean(
            value,
            tags=RICH_TEXT_TAGS,
            attributes=RICH_TEXT_ATTRIBUTES,
            protocols=["http", "https", "mailto"],
            strip=True,
        )


class QuestionGroupAdminForm(forms.ModelForm):
    class Meta:
        model = QuestionGroup
        fields = "__all__"
        widgets = {"instructions": forms.Textarea(attrs={"rows": 4}), "layout_html": forms.Textarea(attrs={"rows": 14})}

    def clean_layout_html(self):
        value = self.cleaned_data.get("layout_html") or ""
        allowed = RICH_TEXT_TAGS + ["div", "section", "table", "thead", "tbody", "tr", "th", "td", "caption", "span"]
        return bleach.clean(value, tags=allowed, attributes={}, strip=True)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return [single_file_clean(data, initial)]


class HtmlExamImportForm(forms.Form):
    title = forms.CharField(
        label="Test title",
        max_length=200,
        help_text="Use a clear name such as Academic Reading Mock Test 2.",
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    section_type = forms.ChoiceField(
        label="Skill",
        choices=Section.SECTION_TYPES,
        initial="reading",
        help_text="The test category and every uploaded section will use this skill.",
    )
    html_files = MultipleFileField(
        widget=MultipleFileInput(attrs={"accept": ".html,.htm,text/html"}),
        help_text="Choose one complete HTML or HTM test file.",
    )
    publish = forms.BooleanField(
        label="Publish immediately",
        required=False,
        help_text="Draft is recommended until questions and answers have been reviewed.",
    )

    def clean_html_files(self):
        files = self.cleaned_data["html_files"]
        if len(files) != 1:
            raise ValidationError("Upload exactly one complete HTML file.")
        for uploaded in files:
            if not uploaded.name.lower().endswith((".html", ".htm")):
                raise ValidationError(f"{uploaded.name} is not an HTML file.")
            if uploaded.size > 2 * 1024 * 1024:
                raise ValidationError(f"{uploaded.name} is larger than 2 MB.")
        return files


class ExcelExamImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel workbook",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
        help_text="Upload a completed IELTS_Test_Import_Template.xlsx file (maximum 5 MB).",
    )
    publish = forms.BooleanField(
        label="Publish immediately",
        required=False,
        help_text="Draft is recommended until you open and review the imported test.",
    )

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise ValidationError("Upload an .xlsx workbook.")
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError("The workbook is larger than 5 MB.")
        return uploaded


class ListeningTestSetupForm(forms.Form):
    title = forms.CharField(
        label="Listening test title",
        max_length=200,
        help_text="For example: Listening Practice Test 1.",
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="A short note students will see before starting the test.",
    )
    audio_file = forms.FileField(
        label="Listening audio",
        widget=forms.ClearableFileInput(attrs={"accept": "audio/mpeg,audio/mp4,audio/wav,audio/ogg,.mp3,.m4a,.wav,.ogg"}),
        help_text="MP3 is recommended. Maximum file size: 30 MB.",
    )
    time_limit_minutes = forms.IntegerField(
        label="Time limit (minutes)",
        min_value=1,
        initial=30,
        help_text="Use 30 minutes for a standard IELTS Listening practice test.",
    )

    def clean_audio_file(self):
        uploaded = self.cleaned_data["audio_file"]
        if not uploaded.name.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")):
            raise ValidationError("Upload an MP3, M4A, WAV, or OGG audio file.")
        if uploaded.size > 30 * 1024 * 1024:
            raise ValidationError("The audio file must be 30 MB or smaller.")
        return uploaded

import re

import bleach
from django import template
from django.utils.html import escape, linebreaks
from django.utils.safestring import mark_safe

from exams.forms import RICH_TEXT_ATTRIBUTES, RICH_TEXT_TAGS


register = template.Library()
RICH_TAG_PATTERN = re.compile(r"</?(?:p|br|strong|em|u|h2|h3|ul|ol|li|blockquote|a)\b", re.I)


@register.filter
def render_rich_text(value):
    """Render sanitized admin formatting while preserving legacy plain-text passages."""
    value = value or ""
    if not RICH_TAG_PATTERN.search(value):
        # django.utils.html.linebreaks returns generated HTML, but a custom
        # template filter must explicitly mark that generated markup safe or
        # Django will display the <p> tags as literal text.
        return mark_safe(linebreaks(value))
    cleaned = bleach.clean(
        value,
        tags=RICH_TEXT_TAGS,
        attributes=RICH_TEXT_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return mark_safe(cleaned)


GROUP_TAGS = ["p", "br", "strong", "em", "u", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "a", "div", "section", "table", "thead", "tbody", "tr", "th", "td", "caption", "span"]


@register.filter
def render_question_group(group):
    """Render sanitized worksheet HTML and replace [[order]] tokens with real form controls."""
    questions = list(group.questions.all())
    cleaned = bleach.clean(group.layout_html or "", tags=GROUP_TAGS, attributes={}, strip=True)
    for question in questions:
        control_id = f"q{question.id}"
        if question.question_type == "matching" and question.options:
            options = ['<option value="">Select an option</option>'] + [
                f'<option value="{escape(option)}">{escape(option)}</option>' for option in question.options
            ]
            control = f'<span class="exam-inline-question" id="question-{question.id}" data-question-id="{question.id}" data-question-order="{question.order}" tabindex="-1"><span class="exam-inline-number">{question.order}</span><label class="visually-hidden" for="{control_id}">Answer for question {question.order}</label><select id="{control_id}" name="q{question.id}" class="exam-inline-input">{"".join(options)}</select></span>'
        else:
            control = f'<span class="exam-inline-question" id="question-{question.id}" data-question-id="{question.id}" data-question-order="{question.order}" tabindex="-1"><span class="exam-inline-number">{question.order}</span><label class="visually-hidden" for="{control_id}">Answer for question {question.order}</label><input id="{control_id}" name="q{question.id}" class="exam-inline-input" type="text" placeholder="{question.order}" spellcheck="false"></span>'
        cleaned = cleaned.replace(f"[[{question.order}]]", control)
    first = questions[0].order if questions else ""
    last = questions[-1].order if questions else ""
    heading = f"Questions {first}–{last}" if first != last else f"Question {first}"
    instructions = bleach.clean(group.instructions or "", tags=["strong", "em", "br", "p"], strip=True)
    return mark_safe(f'<article class="exam-question-group" data-layout="{escape(group.layout_type)}"><div class="exam-group-instructions"><h2>{heading}</h2>{instructions}</div><div class="exam-group-sheet">{cleaned}</div></article>')

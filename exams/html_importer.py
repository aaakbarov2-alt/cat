import re
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import ExamSet, Question, QuestionGroup, Section


class HtmlImportError(ValueError):
    pass


def _classes(attrs):
    return set(dict(attrs).get("class", "").split())


def _clean_text(value):
    value = unescape(value).replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def _clean_inline_text(value):
    return re.sub(r"\s+", " ", unescape(value).replace("\xa0", " ")).strip()


class IeltsHtmlParser(HTMLParser):
    """Extracts structured content without executing or retaining uploaded markup."""

    block_tags = {"p", "div", "h1", "h2", "h3", "h4", "li", "br"}
    void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.passage_depth = 0
        self.passage_parts = []
        self.current_question = None
        self.question_depth = 0
        self.question_text_depth = 0
        self.current_label = None
        self.label_depth = 0
        self.current_option = None
        self.option_depth = 0
        self.group_depth = 0
        self.group_parts = []
        self.group_context_frozen = False
        self.questions = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = _classes(attrs)

        if "question-group" in classes and not self.group_depth:
            self.group_depth = 1
            self.group_parts = []
            self.group_context_frozen = False
        elif self.group_depth:
            if not self.group_context_frozen and tag in self.block_tags:
                self.group_parts.append("\n")
            if tag not in self.void_tags:
                self.group_depth += 1

        if "passage-content" in classes and not self.passage_depth:
            self.passage_depth = 1
        elif self.passage_depth:
            if tag in self.block_tags:
                self.passage_parts.append("\n")
            if tag not in self.void_tags:
                self.passage_depth += 1

        if self.current_question is None and "question" in classes and attrs_dict.get("data-question"):
            try:
                order = int(attrs_dict["data-question"])
            except ValueError:
                order = len(self.questions) + 1
            self.current_question = {
                "order": order,
                "prompt_parts": [],
                "input_types": set(),
                "select_options": [],
                "radio_options": [],
                "group_context": _clean_text("".join(self.group_parts)),
            }
            self.group_context_frozen = True
            self.question_depth = 1
            return

        if self.current_question is None:
            return

        if tag not in self.void_tags:
            self.question_depth += 1
        if "question-text" in classes:
            self.question_text_depth = 1
        elif self.question_text_depth and tag not in self.void_tags:
            self.question_text_depth += 1

        if tag == "input":
            input_type = attrs_dict.get("type", "text").lower()
            self.current_question["input_types"].add(input_type)
            if input_type == "text" and self.question_text_depth:
                self.current_question["prompt_parts"].append(" ____ ")
            if input_type == "radio" and self.current_label is not None:
                self.current_label["value"] = attrs_dict.get("value", "").strip()
        elif tag == "label":
            self.current_label = {"value": "", "parts": []}
            self.label_depth = 1
        elif self.current_label is not None and tag not in self.void_tags:
            self.label_depth += 1

        if tag == "option":
            self.current_option = {
                "value": attrs_dict.get("value", "").strip(),
                "parts": [],
                "disabled": "disabled" in attrs_dict,
            }
            self.option_depth = 1
        elif self.current_option is not None and tag not in self.void_tags:
            self.option_depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void_tags:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.passage_depth:
            self.passage_parts.append(data)
        if self.group_depth and not self.group_context_frozen:
            self.group_parts.append(data)
        if self.current_question is None:
            return
        if self.question_text_depth:
            self.current_question["prompt_parts"].append(data)
        if self.current_label is not None:
            self.current_label["parts"].append(data)
        if self.current_option is not None:
            self.current_option["parts"].append(data)

    def handle_endtag(self, tag):
        if self.passage_depth:
            if tag in self.block_tags:
                self.passage_parts.append("\n")
            self.passage_depth -= 1

        if self.group_depth:
            if not self.group_context_frozen and tag in self.block_tags:
                self.group_parts.append("\n")
            self.group_depth -= 1
            if self.group_depth == 0:
                self.group_parts = []
                self.group_context_frozen = False

        if self.current_question is None:
            return

        if self.current_option is not None:
            self.option_depth -= 1
            if self.option_depth == 0:
                text = _clean_text("".join(self.current_option["parts"]))
                value = self.current_option["value"] or text
                if value and not self.current_option["disabled"]:
                    self.current_question["select_options"].append(value)
                self.current_option = None

        if self.current_label is not None:
            self.label_depth -= 1
            if self.label_depth == 0:
                value = self.current_label["value"]
                text = _clean_inline_text("".join(self.current_label["parts"]))
                if value:
                    self.current_question["radio_options"].append((value, text or value))
                self.current_label = None

        if self.question_text_depth:
            self.question_text_depth -= 1

        self.question_depth -= 1
        if self.question_depth == 0:
            self.questions.append(self.current_question)
            self.current_question = None


@dataclass
class ImportedQuestion:
    order: int
    question_type: str
    prompt: str
    options: list | None
    correct_answer: str


@dataclass
class ImportedSection:
    source_name: str
    passage_text: str
    questions: list
    warnings: list

    def as_payload(self):
        return {
            "source_name": self.source_name,
            "passage_text": self.passage_text,
            "questions": [asdict(question) for question in self.questions],
            "warnings": self.warnings,
        }


def _extract_correct_answers(html):
    match = re.search(
        r"(?:const|let|var)\s+correctAnswers\s*=\s*\{(?P<body>.*?)\}\s*;?",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return {}
    pairs = re.findall(
        r"[\"']?q?(\d+)[\"']?\s*:\s*[\"']([^\"']*)[\"']",
        match.group("body"),
        flags=re.IGNORECASE,
    )
    return {int(number): unescape(answer).strip() for number, answer in pairs}


def parse_ielts_html(content, source_name="uploaded.html", section_type="reading"):
    if isinstance(content, bytes):
        try:
            html = content.decode("utf-8")
        except UnicodeDecodeError:
            html = content.decode("cp1252")
    else:
        html = content

    parser = IeltsHtmlParser()
    parser.feed(html)
    answers = _extract_correct_answers(html)
    passage = _clean_text("".join(parser.passage_parts))
    if section_type == "reading" and not passage:
        raise HtmlImportError(f"{source_name}: no element with class 'passage-content' was found.")
    if not parser.questions:
        raise HtmlImportError(f"{source_name}: no numbered question blocks were found.")

    imported = []
    warnings = []
    seen_orders = set()
    last_matching_context = None
    for raw in parser.questions:
        order = raw["order"]
        if order in seen_orders:
            raise HtmlImportError(f"{source_name}: question number {order} appears more than once.")
        seen_orders.add(order)
        prompt = _clean_text("".join(raw["prompt_parts"]))
        prompt = re.sub(rf"^\s*{order}\s*[.)]?\s*", "", prompt).strip()
        if not prompt:
            raise HtmlImportError(f"{source_name}: question {order} has no readable prompt.")

        answer = answers.get(order, "")
        input_types = raw["input_types"]
        if section_type == "writing":
            question_type = "essay"
            options = None
            answer = ""
        elif section_type == "speaking":
            question_type = "speaking"
            options = None
            answer = ""
        elif raw["select_options"]:
            question_type = "matching"
            options = raw["select_options"]
            context = raw.get("group_context", "")
            if context and context != last_matching_context:
                prompt = f"{context}\n\n{prompt}"
                last_matching_context = context
        elif "radio" in input_types:
            question_type = "mcq"
            options = [text for _value, text in raw["radio_options"]]
            answer_map = {value.casefold(): text for value, text in raw["radio_options"]}
            answer = answer_map.get(answer.casefold(), answer)
        elif "text" in input_types:
            question_type = "gap"
            options = None
        else:
            warnings.append(f"Question {order} had no recognized input and was treated as a gap fill.")
            question_type = "gap"
            options = None

        if question_type in {"mcq", "gap", "matching"} and not answer:
            raise HtmlImportError(
                f"{source_name}: correct answer for question {order} was not found in correctAnswers."
            )
        if question_type == "mcq" and answer not in options:
            raise HtmlImportError(
                f"{source_name}: answer for question {order} does not match an available option."
            )
        imported.append(ImportedQuestion(order, question_type, prompt, options, answer))

    return ImportedSection(source_name, passage, imported, warnings)


@transaction.atomic
def create_exam_from_payload(payload):
    exam = ExamSet(
        title=payload["title"],
        description=payload.get("description", ""),
        category=payload["category"],
        is_published=False,
        delivery_mode=payload.get("delivery_mode", "native"),
        source_html=payload.get("source_html", ""),
    )
    exam.full_clean()
    exam.save()
    for section_order, section_data in enumerate(payload.get("sections", []), start=1):
        section = Section(
            exam_set=exam,
            order=section_data.get("order", section_order),
            section_type=section_data.get("section_type", payload.get("section_type", "reading")),
            time_limit_minutes=section_data.get("time_limit_minutes", payload.get("time_limit_minutes", 60)),
            passage_text=section_data["passage_text"],
        )
        section.full_clean()
        section.save()
        groups_by_key = {}
        for group_data in section_data.get("groups", []):
            group = QuestionGroup(section=section, **group_data)
            group.full_clean()
            group.save()
            groups_by_key[group.key] = group
        for question_data in section_data["questions"]:
            question_data = question_data.copy()
            group_key = question_data.pop("group_key", "")
            if group_key:
                question_data["group"] = groups_by_key[group_key]
            question = Question(section=section, **question_data)
            question.full_clean()
            question.save()
    if payload.get("publish") and exam.is_ready:
        exam.is_published = True
        exam.save(update_fields=["is_published"])
    return exam

from __future__ import annotations

import io
import os
import re
from html import escape
from pathlib import Path
from typing import Any

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.pdfbase.pdfmetrics import stringWidth

from app.rendering.resume_content import (
    LABELS,
    contact_lines,
    date_range,
    full_name,
    non_empty,
    text,
)


def _shape(value: Any) -> str:
    return get_display(arabic_reshaper.reshape(text(value)))


def _is_ltr_contact(value: str) -> bool:
    return bool(re.match(r"(?:https?://|www\.|[\w.+-]+@)", value, re.IGNORECASE))


def _font_path() -> str:
    candidates = [
        os.getenv("RESUME_FONT_PATH"),
        str(Path(__file__).parents[1] / "assets" / "Vazirmatn-Regular.ttf"),
        r"C:\Windows\Fonts\tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError("No Unicode font found. Set RESUME_FONT_PATH to a TTF font.")


def _register_font() -> str:
    font_name = "ResumeUnicode"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, _font_path()))
    return font_name


class PdfResumeRenderer:
    def render(self, resume: dict[str, Any]) -> bytes:
        font = _register_font()
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=full_name(resume),
            author="Intelligent Resume Builder",
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle(
            "resume-title",
            parent=styles["Title"],
            fontName=font,
            fontSize=22,
            leading=29,
            textColor=colors.HexColor("#17324D"),
            alignment=TA_RIGHT,
            spaceAfter=4 * mm,
        )
        contact = ParagraphStyle(
            "resume-contact",
            parent=styles["Normal"],
            fontName=font,
            fontSize=9,
            leading=15,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#52606D"),
            spaceAfter=5 * mm,
        )
        heading = ParagraphStyle(
            "resume-heading",
            parent=styles["Heading2"],
            fontName=font,
            fontSize=13,
            leading=20,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
        body = ParagraphStyle(
            "resume-body",
            parent=styles["BodyText"],
            fontName=font,
            fontSize=10,
            leading=18,
            alignment=TA_RIGHT,
            spaceAfter=1.5 * mm,
        )
        small = ParagraphStyle(
            "resume-small",
            parent=body,
            fontSize=9,
            leading=16,
            textColor=colors.HexColor("#52606D"),
        )

        story: list[Any] = [Paragraph(_shape(full_name(resume)), title)]
        contacts = contact_lines(resume)
        if contacts:
            # Preserve URL/email character order instead of applying Arabic
            # shaping and bidi reordering to these left-to-right values.
            for value in contacts:
                if _is_ltr_contact(value):
                    story.append(Paragraph(escape(value), contact))
                else:
                    story.append(Paragraph(_shape(value), contact))

        def section(label: str) -> None:
            story.extend([Paragraph(_shape(label), heading)])

        def bullet(value: Any) -> None:
            story.append(Paragraph(_shape("• " + text(value)), body))

        if resume.get("professional_summary"):
            section(LABELS["summary"])
            story.append(Paragraph(escape(_shape(resume["professional_summary"])), body))
        if resume.get("career_objective"):
            section(LABELS["objective"])
            story.append(Paragraph(_shape(resume["career_objective"]), body))

        experiences = resume.get("work_experiences") or []
        if experiences:
            section(LABELS["experience"])
            for item in experiences:
                title_text = " | ".join(
                    non_empty([item.get("job_title"), item.get("company_name")])
                )
                if date_range(item):
                    title_text = f"{title_text} — {date_range(item)}"
                story.append(Paragraph(_shape(title_text), body))
                if item.get("description"):
                    story.append(Paragraph(_shape(item["description"]), small))
                for value in [
                    *(item.get("key_responsibilities") or []),
                    *(item.get("achievements") or []),
                ]:
                    bullet(value)

        educations = resume.get("educations") or []
        if educations:
            section(LABELS["education"])
            for item in educations:
                story.append(
                    Paragraph(
                        _shape(
                            " | ".join(
                                non_empty(
                                    [
                                        item.get("degree"),
                                        item.get("field_of_study"),
                                        item.get("institution_name"),
                                    ]
                                )
                            )
                        ),
                        body,
                    )
                )
                for value in [
                    *(item.get("relevant_courses") or []),
                    *(item.get("achievements") or []),
                ]:
                    bullet(value)

        skills = resume.get("skills") or []
        if skills:
            section(LABELS["skills"])
            rows = [
                [
                    Paragraph(_shape(item.get("name")), body),
                    Paragraph(_shape(item.get("level")), body),
                ]
                for item in skills
            ]
            table = Table(rows, colWidths=[105 * mm, 45 * mm], hAlign="RIGHT")
            table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D8DEE4")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7F9")),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(table)

        simple_sections = [
            ("tools", resume.get("tools_platforms")),
            ("languages", resume.get("languages")),
            ("interests", resume.get("interests")),
        ]
        for key, values in simple_sections:
            if values:
                section(LABELS[key])
                for value in values:
                    bullet(
                        value.get("name")
                        + (f" — {value.get('level')}" if value.get("level") else "")
                        if isinstance(value, dict)
                        else value
                    )

        document.build(story)
        return buffer.getvalue()

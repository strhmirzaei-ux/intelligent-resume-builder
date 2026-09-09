from __future__ import annotations

import io
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.rendering.resume_content import LABELS, contact_lines, date_range, full_name, non_empty


def _rtl(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.space_after = Pt(6)
    # In RTL Word paragraphs, a right indent pulls the visible text away from
    # the right edge. Keep the right edge flush; bullets use only a left indent
    # for their hanging marker.
    paragraph.paragraph_format.right_indent = Inches(0)
    ppr = paragraph._p.get_or_add_pPr()
    for tag in ("w:bidi", "w:jc"):
        for element in ppr.findall(qn(tag)):
            ppr.remove(element)
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    ppr.append(bidi)
    justification = OxmlElement("w:jc")
    justification.set(qn("w:val"), "right")
    ppr.append(justification)
    for run in paragraph.runs:
        run._r.get_or_add_rPr().append(OxmlElement("w:rtl"))
        run.font.name = "Tahoma"
        run._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")


def _set_run(run, size: float = 10, bold: bool = False, color: str = "1F2933") -> None:
    run.font.name = "Tahoma"
    run._element.get_or_add_rPr().rFonts.set(qn("w:cs"), "Tahoma")
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    rtl = OxmlElement("w:rtl")
    run._element.get_or_add_rPr().append(rtl)


def _set_rtl_style(style) -> None:
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    ppr = style._element.get_or_add_pPr()
    for tag in ("w:bidi", "w:jc"):
        for element in ppr.findall(qn(tag)):
            ppr.remove(element)
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    ppr.append(bidi)
    justification = OxmlElement("w:jc")
    justification.set(qn("w:val"), "right")
    ppr.append(justification)


class DocxResumeRenderer:
    def render(self, resume: dict[str, Any]) -> bytes:
        document = Document()
        section = document.sections[0]
        section.top_margin = Inches(0.65)
        section.bottom_margin = Inches(0.65)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
        styles = document.styles
        normal = styles["Normal"]
        normal.font.name = "Tahoma"
        normal._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
        normal.font.size = Pt(10)
        _set_rtl_style(normal)
        _set_rtl_style(styles["List Bullet"])

        title = document.add_paragraph()
        title.paragraph_format.space_after = Pt(3)
        run = title.add_run(full_name(resume))
        _set_run(run, 22, True, "17324D")
        _rtl(title)
        contacts = contact_lines(resume)
        if contacts:
            paragraph = document.add_paragraph(" | ".join(contacts))
            for run in paragraph.runs:
                _set_run(run, 9, False, "52606D")
            _rtl(paragraph)

        def heading(label: str) -> None:
            p = document.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            _set_run(p.add_run(label), 13, True, "17324D")
            _rtl(p)

        def paragraph(
            value: str, size: float = 10, bold: bool = False, color: str = "1F2933"
        ) -> None:
            p = document.add_paragraph(value)
            for run in p.runs:
                _set_run(run, size, bold, color)
            _rtl(p)

        def bullet(value: str) -> None:
            p = document.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Inches(0.25)
            _set_run(p.add_run(value), 10)
            _rtl(p)

        if resume.get("professional_summary"):
            heading(LABELS["summary"])
            paragraph(resume["professional_summary"])
        if resume.get("career_objective"):
            heading(LABELS["objective"])
            paragraph(resume["career_objective"])
        if resume.get("work_experiences"):
            heading(LABELS["experience"])
            for item in resume["work_experiences"]:
                value = " | ".join(
                    non_empty([item.get("job_title"), item.get("company_name"), date_range(item)])
                )
                paragraph(value, bold=True)
                if item.get("description"):
                    paragraph(item["description"], 9, False, "52606D")
                for value in [
                    *(item.get("key_responsibilities") or []),
                    *(item.get("achievements") or []),
                ]:
                    bullet(value)
        if resume.get("educations"):
            heading(LABELS["education"])
            for item in resume["educations"]:
                paragraph(
                    " | ".join(
                        non_empty(
                            [
                                item.get("degree"),
                                item.get("field_of_study"),
                                item.get("institution_name"),
                            ]
                        )
                    ),
                    bold=True,
                )
                for value in [
                    *(item.get("relevant_courses") or []),
                    *(item.get("achievements") or []),
                ]:
                    bullet(value)
        if resume.get("skills"):
            heading(LABELS["skills"])
            for item in resume["skills"]:
                bullet(" | ".join(non_empty([item.get("name"), item.get("level")])))
        for key, values in [
            ("tools", resume.get("tools_platforms")),
            ("languages", resume.get("languages")),
            ("interests", resume.get("interests")),
        ]:
            if values:
                heading(LABELS[key])
                for value in values:
                    bullet(
                        (
                            value.get("name")
                            + (f" — {value.get('level')}" if value.get("level") else "")
                        )
                        if isinstance(value, dict)
                        else value
                    )

        footer = section.footer.paragraphs[0]
        footer.add_run("رزومه تولیدشده توسط رزومه‌ساز هوشمند")
        _rtl(footer)
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()

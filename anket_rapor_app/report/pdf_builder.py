"""Referans yerleşime yakın PDF akışı üretici.

Not: Bu modül, veri hazırlama katmanından gelen özet tablolar ve grafik
çıktı yollarını yerleştirir; arka plan ızgarası kullanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from anket_rapor_app.report.styles import build_paragraph_styles, matrix_table_style, small_table_style


@dataclass(slots=True)
class SmallBlock:
    heading: str
    rows: list[list[str]]
    chart_path: str | None = None
    comment: str = ""


@dataclass(slots=True)
class MatrixSection:
    title: str
    headers: list[str]
    rows: list[list[str]]
    average_row_idx: int | None = None
    comment: str = ""


@dataclass(slots=True)
class ReportContent:
    title: str
    section1: list[SmallBlock] = field(default_factory=list)
    section2: list[SmallBlock] = field(default_factory=list)
    section3: MatrixSection | None = None
    section4: MatrixSection | None = None
    section5: MatrixSection | None = None
    section6: MatrixSection | None = None
    section6_post_yes_no: SmallBlock | None = None
    summary_lines: list[str] = field(default_factory=list)


class PDFBuilder:
    """I–VI bölüm düzenini referanslara yakın biçimde kurar."""

    def __init__(self, output_path: str | Path):
        self.output_path = str(output_path)
        self.styles = build_paragraph_styles()

    def build(self, content: ReportContent) -> None:
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=24 * mm,
            rightMargin=24 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=content.title,
        )

        flowables = []
        flowables.extend(self._build_small_sections("I. BÖLÜM", content.section1))
        flowables.append(PageBreak())
        flowables.extend(self._build_small_sections("II. BÖLÜM", content.section2))

        if content.section3:
            flowables.append(PageBreak())
            flowables.extend(self._build_matrix_section("III. BÖLÜM", content.section3))
        if content.section4:
            flowables.append(PageBreak())
            flowables.extend(self._build_matrix_section("IV. BÖLÜM", content.section4))
        if content.section5:
            flowables.append(PageBreak())
            flowables.extend(self._build_matrix_section("V. BÖLÜM", content.section5))
        if content.section6:
            flowables.append(PageBreak())
            flowables.extend(self._build_matrix_section("VI. BÖLÜM", content.section6))

        if content.section6_post_yes_no:
            flowables.extend(
                self._build_small_sections(
                    "VI. BÖLÜM (EK SORU)", [content.section6_post_yes_no]
                )
            )

        if content.summary_lines:
            flowables.append(PageBreak())
            flowables.append(Paragraph("SONUÇ VE DEĞERLENDİRME", self.styles["SectionTitle"]))
            flowables.append(Spacer(1, 2 * mm))
            for line in content.summary_lines:
                flowables.append(Paragraph(f"• {line}", self.styles["BodyTextTR"]))
                flowables.append(Spacer(1, 1 * mm))

        doc.build(flowables)

    def _build_small_sections(self, title: str, blocks: Iterable[SmallBlock]) -> list:
        parts = [Paragraph(title, self.styles["SectionTitle"]), Spacer(1, 1.8 * mm)]
        for block in blocks:
            parts.append(self._small_block(block))
            parts.append(Spacer(1, 3 * mm))
        return parts

    def _small_block(self, block: SmallBlock) -> KeepTogether:
        heading = Paragraph(block.heading, self.styles["SubTitle"])

        table = Table(block.rows, colWidths=[53 * mm, 16 * mm, 14 * mm], repeatRows=1)
        table.setStyle(small_table_style(len(block.rows)))

        chart = self._chart_or_placeholder(block.chart_path)
        row = Table([[table, chart]], colWidths=[88 * mm, 68 * mm])
        row.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        comment_text = block.comment.strip() or "Katılımcı dağılımı tabloda ve grafikte özetlenmiştir."
        comment = Paragraph(comment_text, self.styles["BodyTextTR"])

        return KeepTogether([heading, row, Spacer(1, 1.5 * mm), comment])

    def _build_matrix_section(self, section_title: str, matrix: MatrixSection) -> list:
        title = Paragraph(section_title, self.styles["SectionTitle"])
        subtitle = Paragraph(matrix.title, self.styles["SubTitle"])

        table_rows = [matrix.headers, *matrix.rows]
        table = Table(table_rows, repeatRows=1)
        table.setStyle(
            matrix_table_style(
                row_count=len(table_rows),
                col_count=len(matrix.headers),
                average_row_idx=matrix.average_row_idx,
            )
        )

        comment_text = matrix.comment.strip() or "Top2 (Çok iyi + İyi) değerlendirme oranları olumlu yöndedir."
        comment = Paragraph(comment_text, self.styles["BodyTextTR"])

        return [
            KeepTogether([title, subtitle, table, Spacer(1, 1.5 * mm), comment]),
            Spacer(1, 3 * mm),
        ]

    def _chart_or_placeholder(self, chart_path: str | None):
        if chart_path and Path(chart_path).exists():
            return Image(chart_path, width=66 * mm, height=52 * mm)
        return Table(
            [["Grafik"]],
            colWidths=[66 * mm],
            rowHeights=[52 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, "#aaaaaa"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            ),
        )

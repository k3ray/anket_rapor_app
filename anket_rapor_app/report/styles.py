"""PDF stil tanımları.

Referans sayfa1–sayfa9 düzenine yakın bir görünüm üretmek için tipografi
ve tablo stilleri burada merkezi olarak tutulur.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import TableStyle

# Renk paleti (referansa yakın nötr tonlar)
GRAY_HEADER = colors.HexColor("#d9d9d9")
GRAY_TOTAL = colors.HexColor("#e6e6e6")
TEXT_COLOR = colors.HexColor("#111111")
BORDER_COLOR = colors.HexColor("#555555")

DEFAULT_FONT_NAME = "DejaVuSans"
DEFAULT_FONT_BOLD_NAME = "DejaVuSans-Bold"


def register_turkish_fonts() -> tuple[str, str]:
    """Register DejaVu Sans fonts for Turkish glyph support via matplotlib."""
    try:
        from matplotlib import font_manager

        regular_path = font_manager.findfont("DejaVu Sans")
        bold_path = font_manager.findfont(
            font_manager.FontProperties(family="DejaVu Sans", weight="bold")
        )

        if DEFAULT_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(DEFAULT_FONT_NAME, regular_path))
        if DEFAULT_FONT_BOLD_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(DEFAULT_FONT_BOLD_NAME, bold_path))
        return DEFAULT_FONT_NAME, DEFAULT_FONT_BOLD_NAME
    except Exception:
        # Fallback keeps report generation alive if font discovery fails.
        return "Helvetica", "Helvetica-Bold"


def build_paragraph_styles() -> StyleSheet1:
    """Başlık/alt başlık/metin stillerini döndürür."""
    styles = getSampleStyleSheet()
    font_name, font_bold_name = register_turkish_fonts()

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Normal"],
            fontName=font_bold_name,
            fontSize=12,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_COLOR,
            spaceAfter=3 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubTitle",
            parent=styles["Normal"],
            fontName=font_bold_name,
            fontSize=11,
            leading=13,
            alignment=TA_LEFT,
            textColor=TEXT_COLOR,
            spaceBefore=1 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextTR",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=13,
            alignment=TA_JUSTIFY,
            textColor=TEXT_COLOR,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=11,
            alignment=TA_LEFT,
            textColor=TEXT_COLOR,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCellCenter",
            parent=styles["TableCell"],
            alignment=TA_CENTER,
        )
    )
    return styles


def small_table_style(row_count: int) -> TableStyle:
    """I–II bölüm küçük tablo stili: header + TOPLAM gri, border okunaklı."""
    _, font_bold_name = register_turkish_fonts()
    font_name, _ = register_turkish_fonts()
    last_row = max(1, row_count - 1)
    return TableStyle(
        [
            ("FONT", (0, 0), (-1, 0), font_bold_name, 10),
            ("FONT", (0, last_row), (-1, last_row), font_bold_name, 10),
            ("FONT", (0, 1), (-1, max(1, last_row - 1)), font_name, 10),
            ("BACKGROUND", (0, 0), (-1, 0), GRAY_HEADER),
            ("BACKGROUND", (0, last_row), (-1, last_row), GRAY_TOTAL),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, BORDER_COLOR),
            ("LINEABOVE", (0, last_row), (-1, last_row), 0.9, BORDER_COLOR),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def matrix_table_style(row_count: int, col_count: int, average_row_idx: int | None = None) -> TableStyle:
    """III–VI bölüm matris stili: Toplam sütunu ve ORTALAMA satırı gri."""
    font_name, font_bold_name = register_turkish_fonts()
    total_col = col_count - 1
    commands = [
        ("FONT", (0, 0), (-1, 0), font_bold_name, 10),
        ("FONT", (0, 1), (-1, row_count - 1), font_name, 10),
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, BORDER_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (total_col, 0), (total_col, row_count - 1), GRAY_TOTAL),
        ("FONT", (total_col, 0), (total_col, row_count - 1), font_bold_name, 10),
    ]
    if average_row_idx is not None and 0 <= average_row_idx < row_count:
        commands.extend(
            [
                ("BACKGROUND", (0, average_row_idx), (-1, average_row_idx), GRAY_TOTAL),
                ("FONT", (0, average_row_idx), (-1, average_row_idx), font_bold_name, 10),
                ("LINEABOVE", (0, average_row_idx), (-1, average_row_idx), 0.9, BORDER_COLOR),
            ]
        )
    return TableStyle(commands)

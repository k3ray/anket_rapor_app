from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


@dataclass
class Distribution:
    title: str
    table: pd.DataFrame
    chart_png: bytes


def normalize_header(value: str) -> str:
    text = str(value)
    text = text.replace("\ufeff", "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def read_input_excel(input_path: Path, sheet_name: str) -> pd.DataFrame:
    frame = pd.read_excel(input_path, sheet_name=sheet_name, engine="openpyxl")
    frame.columns = [normalize_header(col) for col in frame.columns]
    return frame


def resolve_column(columns: list[str], aliases: list[str]) -> str:
    normalized = {normalize_header(col): col for col in columns}
    for alias in aliases:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    raise KeyError(f"Column not found. aliases={aliases}")


def build_distribution(frame: pd.DataFrame, column: str, title: str, order: list[str] | None = None) -> Distribution:
    series = frame[column].dropna().astype(str).map(normalize_header)
    counts = series.value_counts(dropna=False)

    if order:
        counts = counts.reindex(order, fill_value=0)

    total = int(counts.sum())
    if total == 0:
        table = pd.DataFrame(columns=["Seçenek", "n", "%"])
    else:
        percents = (counts / total * 100).round(1)
        table = pd.DataFrame({"Seçenek": counts.index, "n": counts.values, "%": percents.values})

    chart_png = render_chart(table, title)
    return Distribution(title=title, table=table, chart_png=chart_png)


def render_chart(table: pd.DataFrame, title: str) -> bytes:
    plt.figure(figsize=(7, 3.2))
    if not table.empty:
        plt.bar(table["Seçenek"], table["n"], color="#2f5597")
        plt.xticks(rotation=20, ha="right", fontsize=8)
        for idx, val in enumerate(table["n"]):
            plt.text(idx, val, str(val), ha="center", va="bottom", fontsize=8)
    plt.title(title, fontsize=10)
    plt.ylabel("n")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    return buf.getvalue()


def draw_distribution_page(pdf: canvas.Canvas, dist: Distribution, page_number: int) -> None:
    width, height = A4
    margin = 40

    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin, height - margin, f"Sayfa {page_number}: {dist.title}")

    table_data = [["Seçenek", "n", "%"]] + dist.table.values.tolist()
    if len(table_data) == 1:
        table_data.append(["Veri yok", 0, 0])

    y = height - 90
    row_h = 20
    col_x = [margin, margin + 300, margin + 370, margin + 440]

    for row_idx, row in enumerate(table_data):
        top = y - row_idx * row_h
        for col_idx in range(3):
            left = col_x[col_idx]
            right = col_x[col_idx + 1]
            pdf.setStrokeColor(colors.black)
            pdf.rect(left, top - row_h, right - left, row_h, fill=0, stroke=1)
            if row_idx == 0:
                pdf.setFont("Helvetica-Bold", 9)
            else:
                pdf.setFont("Helvetica", 9)
            pdf.drawString(left + 4, top - 14, str(row[col_idx]))

    image = ImageReader(BytesIO(dist.chart_png))
    pdf.drawImage(image, margin, 90, width=520, height=220, preserveAspectRatio=True, mask="auto")


def build_pdf(output_path: Path, demographic_dist: Distribution, question_dist: Distribution) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    draw_distribution_page(pdf, demographic_dist, page_number=1)
    pdf.showPage()
    draw_distribution_page(pdf, question_dist, page_number=2)
    pdf.showPage()
    pdf.save()


def run(input_path: Path, config_path: Path, output_path: Path) -> None:
    config = load_config(config_path)
    sheet_name = config.get("input", {}).get("sheet", 0)
    frame = read_input_excel(input_path, sheet_name=sheet_name)

    age_aliases = config["demographics"]["age"]["aliases"]
    age_column = resolve_column(frame.columns.tolist(), age_aliases)
    demographic_dist = build_distribution(
        frame,
        age_column,
        title=config["demographics"]["age"]["label"],
    )

    section = next(sec for sec in config["sections"] if sec.get("id") == "sec2_general_gains")
    first_question = section["questions"][0]
    question_column = resolve_column(frame.columns.tolist(), [first_question["column"]])
    question_dist = build_distribution(
        frame,
        question_column,
        title=normalize_header(first_question["heading"]),
        order=config["scales"][section["scale"]],
    )

    build_pdf(output_path, demographic_dist, question_dist)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Anket rapor PDF üretici")
    parser.add_argument("--input", required=True, type=Path, help="Excel dosya yolu")
    parser.add_argument("--config", required=True, type=Path, help="YAML config dosya yolu")
    parser.add_argument("--out", required=True, type=Path, help="Çıktı PDF yolu")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run(input_path=args.input, config_path=args.config, output_path=args.out)


if __name__ == "__main__":
    main()

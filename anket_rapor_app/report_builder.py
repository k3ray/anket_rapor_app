from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from anket_rapor_app.analysis.closed_ended import compute_closed_ended_table, format_percent_tr
from anket_rapor_app.analysis.open_ended import analyze_open_ended
from anket_rapor_app.report.pdf_builder import MatrixSection, PDFBuilder, ReportContent, SmallBlock
from anket_rapor_app.report.styles import register_turkish_fonts
from anket_rapor_app.text_utils import clean_text
from anket_rapor_app.viz.charts import draw_chart


def _norm(value: Any) -> str:
    return clean_text(value).lower()


def _find_col(df: pd.DataFrame, aliases: list[str] | str) -> str | None:
    items = aliases if isinstance(aliases, list) else [aliases]
    normalized_columns = {_norm(col): col for col in df.columns}
    for alias in items:
        matched = normalized_columns.get(_norm(alias))
        if matched:
            return matched
    return None


def _prepare_headers(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [clean_text(c) for c in result.columns]
    return result


def _small_block_rows(series: pd.Series, scale_name: str, config: dict[str, Any]) -> tuple[list[list[str]], list[dict[str, Any]]]:
    table_rows = compute_closed_ended_table(series.tolist(), scale_name, config)
    total_f = sum(int(r["f"]) for r in table_rows)

    rows = [["Kategori", "f", "%"]]
    for row in table_rows:
        rows.append([clean_text(row["Kategori"]), str(row["f"]), str(row["%"])])
    rows.append(["TOPLAM", str(total_f), "100,0" if total_f else "0,0"])
    return rows, table_rows


def _max_category_comment(table_rows: list[dict[str, Any]], heading: str) -> str:
    if not table_rows:
        return ""
    max_row = max(table_rows, key=lambda r: float(str(r["%"]).replace(",", ".")))
    return f"{clean_text(heading)} maddesinde katılımcıların %{max_row['%']}'inin {clean_text(max_row['Kategori'])} seçeneğinde toplandığı görülmektedir."


def _likert_comment(table_rows: list[dict[str, Any]], heading: str) -> str:
    positive_labels = {"tamamen katılıyorum", "katılıyorum", "çok iyi", "iyi", "evet"}
    positive = sum(
        float(str(r["%"]).replace(",", "."))
        for r in table_rows
        if clean_text(r["Kategori"]).lower() in positive_labels
    )
    max_row = max(table_rows, key=lambda r: float(str(r["%"]).replace(",", "."))) if table_rows else {"Kategori": "-"}
    return (
        f"{clean_text(heading)} maddesinde pozitif oran %{format_percent_tr(positive)} olup en yüksek pay %{max_row['%']} ile "
        f"{clean_text(max_row['Kategori'])} seçeneğindedir."
    )


def _make_small_block(
    df: pd.DataFrame,
    heading: str,
    column_aliases: list[str] | str,
    scale_name: str,
    config: dict[str, Any],
    chart_dir: Path,
    chart_name: str,
    section_roman: str,
    field_name: str,
) -> SmallBlock | None:
    col = _find_col(df, column_aliases)
    if not col:
        return None

    rows, table_rows = _small_block_rows(df[col], scale_name, config)
    chart_path = draw_chart(
        table_rows=table_rows,
        output_path=chart_dir / f"{chart_name}.png",
        section_roman=section_roman,
        field_name=field_name,
        title=clean_text(heading),
    )
    if section_roman == "I":
        comment = _max_category_comment(table_rows, heading)
    else:
        comment = _likert_comment(table_rows, heading)
    return SmallBlock(heading=clean_text(heading), rows=rows, chart_path=str(chart_path), comment=comment)


def _build_demographics(df: pd.DataFrame, config: dict[str, Any], chart_dir: Path) -> list[SmallBlock]:
    blocks: list[SmallBlock] = []
    sec = next((s for s in config.get("sections", []) if s.get("id") == "sec1_demographics"), None)
    if not sec:
        return blocks

    for idx, item in enumerate(sec.get("items", []), start=1):
        field = item.get("field")
        field_cfg = config.get("demographics", {}).get(field, {})
        aliases = field_cfg.get("aliases", [])
        heading = item.get("heading", field_cfg.get("label", field or ""))
        block = _make_small_block(
            df=df,
            heading=heading,
            column_aliases=aliases,
            scale_name="yes_no" if field == "attend_again" else _infer_demographic_scale(df, aliases),
            config={"scales": {**config.get("scales", {}), **_derive_demographic_scales(df, aliases)}},
            chart_dir=chart_dir,
            chart_name=f"sec1_{idx}_{field}",
            section_roman="I",
            field_name=field or "",
        )
        if block:
            blocks.append(block)
    return blocks


def _derive_demographic_scales(df: pd.DataFrame, aliases: list[str]) -> dict[str, list[str]]:
    col = _find_col(df, aliases)
    if not col:
        return {"demographic_dynamic": []}
    values = [clean_text(v) for v in df[col].dropna().tolist() if clean_text(v)]
    ordered = list(dict.fromkeys(values))
    return {"demographic_dynamic": ordered}


def _infer_demographic_scale(df: pd.DataFrame, aliases: list[str]) -> str:
    _ = df
    _ = aliases
    return "demographic_dynamic"


def _build_section2(df: pd.DataFrame, config: dict[str, Any], chart_dir: Path) -> list[SmallBlock]:
    blocks: list[SmallBlock] = []
    sec = next((s for s in config.get("sections", []) if s.get("id") == "sec2_general_gains"), None)
    if not sec:
        return blocks
    scale_name = sec.get("scale", "agreement_5")
    for idx, q in enumerate(sec.get("questions", []), start=1):
        block = _make_small_block(
            df=df,
            heading=q.get("heading", q.get("column", f"Soru {idx}")),
            column_aliases=q.get("column", ""),
            scale_name=scale_name,
            config=config,
            chart_dir=chart_dir,
            chart_name=f"sec2_{idx}",
            section_roman="II",
            field_name=f"q{idx}",
        )
        if block:
            blocks.append(block)
    return blocks


def _matrix_for_section(df: pd.DataFrame, section: dict[str, Any], config: dict[str, Any], label_parser=None) -> MatrixSection:
    scale_name = section.get("scale", "quality_5")
    categories = [clean_text(c) for c in config["scales"][scale_name]]
    headers = ["Soru", *categories, "Top2 (%)"]

    top2_categories = set(categories[:2])
    rows: list[list[str]] = []
    top2_values: list[float] = []

    for q in section.get("questions", []):
        col_alias = q.get("column") if isinstance(q, dict) else q
        col = _find_col(df, col_alias)
        if not col:
            continue

        table_rows = compute_closed_ended_table(df[col].tolist(), scale_name, config)
        pct_map = {clean_text(r["Kategori"]): str(r["%"]) for r in table_rows}
        top2 = sum(float(str(r["%"]).replace(",", ".")) for r in table_rows if clean_text(r["Kategori"]) in top2_categories)
        top2_values.append(top2)

        label = q.get("heading") if isinstance(q, dict) else str(q)
        if label_parser:
            label = label_parser(label)
        row = [clean_text(label)] + [pct_map.get(cat, "0,0") for cat in categories] + [format_percent_tr(top2)]
        rows.append(row)

    average_idx = None
    if section.get("include_average_row") and top2_values:
        averages = []
        for cat in categories:
            values = [float(r[headers.index(cat)].replace(",", ".")) for r in rows]
            averages.append(format_percent_tr(sum(values) / len(values)))
        average_top2 = format_percent_tr(sum(top2_values) / len(top2_values))
        rows.append(["ORTALAMA", *averages, average_top2])
        average_idx = len(rows)

    return MatrixSection(
        title=clean_text(section.get("title", "")),
        headers=headers,
        rows=rows,
        average_row_idx=average_idx,
    )


def _sec3_label_parser(split_on: str):
    def parser(label: str) -> str:
        cleaned = clean_text(label)
        if split_on in cleaned:
            left, right = [clean_text(x) for x in cleaned.split(split_on, 1)]
            return f"{right} ({left})"
        return cleaned

    return parser


def _build_section3_grouped(df: pd.DataFrame, section: dict[str, Any], config: dict[str, Any]) -> MatrixSection:
    categories = [clean_text(c) for c in config["scales"][section.get("scale", "quality_5")]]
    headers = ["Ders / Değerlendiren", *categories, "Toplam (%)"]
    rows: list[list[str]] = []
    row_kinds: list[str] = []
    split_on = section.get("parse", {}).get("split_on", "-")
    grouped: dict[str, list[tuple[str, str]]] = {}

    for label in section.get("questions", []):
        cleaned = clean_text(label)
        if split_on in cleaned:
            course, instructor = [clean_text(x) for x in cleaned.split(split_on, 1)]
        else:
            course, instructor = cleaned, ""
        grouped.setdefault(course, []).append((cleaned, instructor))

    top2_values: list[float] = []
    for course, labels in grouped.items():
        rows.append([course, *([""] * (len(categories) + 1))])
        row_kinds.append("group")
        for original, instructor in labels:
            col = _find_col(df, original)
            if not col:
                continue
            table_rows = compute_closed_ended_table(df[col].tolist(), section.get("scale", "quality_5"), config)
            pct_map = {clean_text(r["Kategori"]): str(r["%"] ) for r in table_rows}
            top2 = sum(float(str(r["%"]).replace(",", ".")) for r in table_rows[:2])
            top2_values.append(top2)
            rows.append([instructor or original] + [pct_map.get(cat, "0,0") for cat in categories] + [format_percent_tr(top2)])
            row_kinds.append("normal")

    if top2_values:
        metric_columns: list[str] = []
        for i in range(len(categories)):
            vals = [float(r[i + 1].replace(",", ".")) for r, kind in zip(rows, row_kinds) if kind == "normal"]
            metric_columns.append(format_percent_tr(sum(vals) / len(vals)) if vals else "0,0")
        rows.append(["ORTALAMA", *metric_columns, format_percent_tr(sum(top2_values) / len(top2_values))])
        row_kinds.append("average")

    return MatrixSection(
        title=clean_text(section.get("title", "III. BÖLÜM")),
        headers=headers,
        rows=rows,
        row_kinds=row_kinds,
        comment=f"III. BÖLÜM genel Top2 (Çok İyi + İyi) oranı %{format_percent_tr(sum(top2_values) / len(top2_values)) if top2_values else '0,0'} olarak hesaplanmıştır.",
    )


def _build_yes_no_block(df: pd.DataFrame, section: dict[str, Any], config: dict[str, Any], chart_dir: Path) -> SmallBlock | None:
    post_questions = section.get("post_questions", [])
    if not post_questions:
        return None
    post = post_questions[0]
    return _make_small_block(
        df=df,
        heading=post.get("heading", "Evet/Hayır"),
        column_aliases=post.get("column", ""),
        scale_name=post.get("scale", "yes_no"),
        config=config,
        chart_dir=chart_dir,
        chart_name="sec6_yes_no",
        section_roman="VI",
        field_name="post_yes_no",
    )


def _summary_lines(content: ReportContent) -> list[str]:
    lines = [
        "I. BÖLÜM demografik dağılımı tablo ve grafiklerle sunulmuştur.",
        "II. BÖLÜM genel kazanım maddeleri için yüzde dağılımı paylaşılmıştır.",
    ]

    for sec_title, matrix in [
        ("III. BÖLÜM", content.section3),
        ("IV. BÖLÜM", content.section4),
        ("V. BÖLÜM", content.section5),
        ("VI. BÖLÜM", content.section6),
    ]:
        if matrix and matrix.rows:
            last_col_values = [float(r[-1].replace(",", ".")) for r in matrix.rows if r and r[0] != "ORTALAMA"]
            if last_col_values:
                lines.append(f"{sec_title} ortalama Top2 oranı %{format_percent_tr(sum(last_col_values) / len(last_col_values))} olarak hesaplanmıştır.")

    if content.section6_post_yes_no:
        yn_rows = content.section6_post_yes_no.rows
        if len(yn_rows) > 2:
            lines.append(f"VI. BÖLÜM ek soruda en yüksek tercih: {yn_rows[1][0]}.")

    return lines


def _open_ended_summary(df: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    open_cfg = config.get("open_ended", {})
    if not open_cfg:
        return []
    results = analyze_open_ended(df, open_cfg, llm_enabled=False)
    lines: list[str] = []
    for title, themes in results.items():
        for theme in themes[:3]:
            lines.append(f"{title} — {clean_text(theme.theme)}: {clean_text(theme.summary)}")
            if len(lines) >= 10:
                return lines
    return lines


def generate_report(excel_path: str, config_path: str, output_dir: str, log=print) -> Path:
    register_turkish_fonts()

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sheet = config.get("input", {}).get("sheet", 0)
    df = pd.read_excel(excel_path, sheet_name=sheet)
    df = _prepare_headers(df)
    log(f"Excel yüklendi: {len(df)} satır")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_dir = out_dir / "charts"

    section3_cfg = next((s for s in config.get("sections", []) if s.get("id") == "sec3_instructors"), {})
    section4_cfg = next((s for s in config.get("sections", []) if s.get("id") == "sec4_organization"), {})
    section5_cfg = next((s for s in config.get("sections", []) if s.get("id") == "sec5_venue_1"), {})
    section6_cfg = next((s for s in config.get("sections", []) if s.get("id") == "sec6_venue_2"), {})

    content = ReportContent(
        title="Anket Raporu",
        section1=_build_demographics(df, config, chart_dir),
        section2=_build_section2(df, config, chart_dir),
        section3=_build_section3_grouped(df, section3_cfg, config),
        section4=_matrix_for_section(df, section4_cfg, config),
        section5=_matrix_for_section(df, section5_cfg, config),
        section6=_matrix_for_section(df, section6_cfg, config),
        section6_post_yes_no=_build_yes_no_block(df, section6_cfg, config, chart_dir),
    )
    content.summary_lines = [*_summary_lines(content), *_open_ended_summary(df, config)]

    output_path = out_dir / "report.pdf"
    PDFBuilder(output_path).build(content)
    log(f"PDF oluşturuldu: {output_path}")
    return output_path

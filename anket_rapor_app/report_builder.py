from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak

from analysis.open_ended import analyze_open_ended


def _norm(s: str) -> str:
    return " ".join(str(s).replace("\ufeff", "").replace("&nbsp;", " ").split()).strip().lower()


def _find_col(df: pd.DataFrame, target: str) -> str | None:
    target_n = _norm(target)
    for c in df.columns:
        if _norm(c) == target_n:
            return c
    return None


def _top2_ratio(series: pd.Series, scale: list[str]) -> float:
    if series.empty:
        return 0.0
    s = series.dropna().astype(str).str.strip()
    if s.empty:
        return 0.0
    top2 = set(scale[:2])
    return 100.0 * s.isin(top2).sum() / len(s)


def _demographic_highest(df: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    rows = []
    for field_key, field_cfg in config.get("demographics", {}).items():
        aliases = field_cfg.get("aliases", [])
        col = None
        for alias in aliases:
            col = _find_col(df, alias)
            if col:
                break
        if not col:
            continue
        vc = df[col].dropna().astype(str).value_counts()
        if vc.empty:
            continue
        top_cat = vc.index[0]
        pct = 100.0 * vc.iloc[0] / vc.sum()
        rows.append(f"{field_cfg.get('label', field_key)}: {top_cat} (%{pct:.1f})")
    return rows


def _collect_top2_sections(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    scales = config.get("scales", {})
    sec2 = []
    sec3, sec4, sec5, sec6 = [], [], [], []
    yes_no_result = "-"

    for sec in config.get("sections", []):
        sec_id = sec.get("id")
        if sec_id == "sec2_general_gains":
            scale = scales.get(sec.get("scale", ""), [])
            for q in sec.get("questions", []):
                col = _find_col(df, q.get("column", ""))
                if not col:
                    continue
                sec2.append((q.get("heading", "Soru"), _top2_ratio(df[col], scale)))
        elif sec_id == "sec3_instructors":
            scale = scales.get(sec.get("scale", ""), [])
            for q in sec.get("questions", []):
                col = _find_col(df, q)
                if not col:
                    continue
                sec3.append(_top2_ratio(df[col], scale))
        elif sec_id in {"sec4_organization", "sec5_venue_1", "sec6_venue_2"}:
            scale = scales.get(sec.get("scale", ""), [])
            vals = []
            for q in sec.get("questions", []):
                col = _find_col(df, q if isinstance(q, str) else q.get("column", ""))
                if col:
                    vals.append(_top2_ratio(df[col], scale))
            if sec_id == "sec4_organization":
                sec4 = vals
            elif sec_id == "sec5_venue_1":
                sec5 = vals
            else:
                sec6 = vals
                for post_q in sec.get("post_questions", []):
                    if post_q.get("type") == "single_choice":
                        col = _find_col(df, post_q.get("column", ""))
                        if col:
                            yn = df[col].dropna().astype(str).str.strip()
                            if not yn.empty:
                                top = yn.value_counts().index[0]
                                yes_no_result = top

    return {
        "sec2": sec2,
        "sec3_avg": mean(sec3) if sec3 else 0.0,
        "sec4_avg": mean(sec4) if sec4 else 0.0,
        "sec5_avg": mean(sec5) if sec5 else 0.0,
        "sec6_avg": mean(sec6) if sec6 else 0.0,
        "yes_no": yes_no_result,
    }


def generate_report(excel_path: str, config_path: str, output_dir: str, log=print) -> Path:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sheet = config.get("input", {}).get("sheet", 0)
    df = pd.read_excel(excel_path, sheet_name=sheet)
    log(f"Excel yüklendi: {len(df)} satır")

    open_results = analyze_open_ended(df, config.get("open_ended", {}), llm_enabled=True)
    log("Açık uçlu analiz tamamlandı (LLM varsa localhost üzerinden, yoksa fallback).")

    summary = _collect_top2_sections(df, config)
    demo_rows = _demographic_highest(df, config)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    pdf_file = output_path / "anket_raporu.pdf"

    doc = SimpleDocTemplate(str(pdf_file), pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2.0 * cm, bottomMargin=2.0 * cm)
    styles = getSampleStyleSheet()
    h_center = ParagraphStyle("h_center", parent=styles["Heading1"], alignment=1, fontName="Times-Bold")
    normal = ParagraphStyle("normal", parent=styles["BodyText"], fontName="Times-Roman", leading=14)

    story = [Paragraph("Anket Raporu", h_center), Spacer(1, 0.5 * cm), Paragraph("Bu PDF örnek rapor içeriği üretir.", normal), PageBreak()]

    story.append(Paragraph("SONUÇ VE DEĞERLENDİRME", h_center))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("<b>Demografik en yüksekler</b>", normal))
    for row in demo_rows:
        story.append(Paragraph(f"• {row}", normal))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("<b>II. Bölüm - madde bazlı pozitif oran (Top2)</b>", normal))
    for heading, val in summary["sec2"]:
        story.append(Paragraph(f"• {heading}: %{val:.1f}", normal))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"<b>III. Bölüm genel Top2:</b> %{summary['sec3_avg']:.1f}", normal))
    story.append(Paragraph(f"<b>IV. Bölüm genel Top2 ortalaması:</b> %{summary['sec4_avg']:.1f}", normal))
    story.append(Paragraph(f"<b>V. Bölüm genel Top2 ortalaması:</b> %{summary['sec5_avg']:.1f}", normal))
    story.append(Paragraph(f"<b>VI. Bölüm genel Top2 ortalaması:</b> %{summary['sec6_avg']:.1f}", normal))
    story.append(Paragraph(f"<b>Evet/Hayır sonucu:</b> {summary['yes_no']}", normal))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>Açık uçlu temalar</b>", normal))
    bullets = []
    all_themes = []
    for _, themes in open_results.items():
        all_themes.extend(themes)
    for theme in all_themes[:10]:
        txt = f"{theme.theme}: {theme.summary}"
        if theme.quotes:
            txt += " | Alıntılar: " + " ; ".join(theme.quotes[:2])
        bullets.append(ListItem(Paragraph(txt, normal)))
    if bullets:
        story.append(ListFlowable(bullets, bulletType="bullet"))
    else:
        story.append(Paragraph("• Yeterli açık uçlu yanıt bulunamadı.", normal))

    doc.build(story)
    log(f"PDF oluşturuldu: {pdf_file}")
    return pdf_file

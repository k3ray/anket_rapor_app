import re
import zlib
from pathlib import Path

from anket_rapor_app.report_builder import generate_report


STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
PAGE_RE = re.compile(rb"/Type\s*/Page(?!s)")
HEX_TEXT_RE = re.compile(r"<([0-9A-Fa-f]+)>\s*Tj")
LIT_TEXT_RE = re.compile(r"\(([^()]*)\)\s*Tj")


def _extract_pdf_text(pdf_path: Path) -> str:
    data = pdf_path.read_bytes()
    chunks: list[str] = []

    for match in STREAM_RE.finditer(data):
        stream = match.group(1)
        if stream.startswith(b"x\x9c"):
            try:
                stream = zlib.decompress(stream)
            except zlib.error:
                continue
        text = stream.decode("latin1", errors="ignore")

        for hex_match in HEX_TEXT_RE.findall(text):
            try:
                chunks.append(bytes.fromhex(hex_match).decode("utf-16-be", errors="ignore"))
            except ValueError:
                continue

        for lit in LIT_TEXT_RE.findall(text):
            chunks.append(lit.encode("latin1", errors="ignore").decode("latin1", errors="ignore"))

    return "\n".join(chunks)


def _count_pages(pdf_path: Path) -> int:
    return len(PAGE_RE.findall(pdf_path.read_bytes()))


def test_generate_report_smoke_full_flow(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    project_root = repo_root / "anket_rapor_app"

    excel_path = project_root / "samples" / "input.xlsx"
    config_path = project_root / "config" / "config_rizepem_2026_2.yaml"

    pdf_path = generate_report(str(excel_path), str(config_path), str(tmp_path), log=lambda *_: None)

    assert pdf_path == tmp_path / "report.pdf"
    assert pdf_path.exists()

    text = _extract_pdf_text(pdf_path)
    assert "I. BÖLÜM" in text
    assert "II. BÖLÜM" in text
    assert "SONUÇ VE DEĞERLENDİRME" in text
    assert "&NBSP" not in text.upper()
    assert _count_pages(pdf_path) > 6

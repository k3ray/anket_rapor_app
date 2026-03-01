from __future__ import annotations

import argparse
from pathlib import Path

from anket_rapor_app.report_builder import generate_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="[LEGACY] Anket raporu üretici")
    parser.add_argument("--input", required=True, type=Path, help="Excel dosya yolu")
    parser.add_argument("--config", required=True, type=Path, help="YAML config dosya yolu")
    parser.add_argument("--out", required=True, type=Path, help="Çıktı PDF yolu")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outdir = args.out.parent if args.out.suffix.lower() == ".pdf" else args.out
    generate_report(str(args.input), str(args.config), str(outdir))


if __name__ == "__main__":
    main()

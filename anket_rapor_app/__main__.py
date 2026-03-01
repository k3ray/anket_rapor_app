from __future__ import annotations

import argparse
from pathlib import Path

from anket_rapor_app.report_builder import generate_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Anket raporu üret")
    parser.add_argument("--input", required=True, type=Path, help="Excel girdi dosyası")
    parser.add_argument("--config", required=True, type=Path, help="YAML konfigürasyon dosyası")
    parser.add_argument("--outdir", required=True, type=Path, help="Çıktı klasörü")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    generate_report(str(args.input), str(args.config), str(args.outdir))


if __name__ == "__main__":
    main()

# Anket Rapor App

## Çalıştırma (tek komut)

```bash
pip install -e .
python -m anket_rapor_app --input samples/input.xlsx --config config/config_rizepem_2026_2.yaml --outdir out
```

Bu komut `out/report.pdf` üretir.

## Legacy / Demo

- `python gui.py` ve `src/app` akışı legacy/demo amaçlıdır.
- Üretim için tek doğru entrypoint: `python -m anket_rapor_app ...`.

## PyInstaller ile EXE alma

```bash
pip install pyinstaller
pyinstaller pyinstaller/app.spec
```

Çıktı dosyası `dist/anket_rapor_app` (Windows'ta `.exe`) olarak oluşur.

## Notlar
- Açık uçlu analizde önce localhost LLM (Ollama: `http://127.0.0.1:11434`) denenir.
- LLM yoksa TF-IDF + KMeans fallback analizi otomatik devreye girer.
- PII maskeleme: e-posta, TR telefon, TC kimlik benzeri desenler.

# Anket Rapor App

## Çalıştırma (önerilen)

```bash
pip install -r requirements.txt
python -c "from report_builder import generate_report; print(generate_report(r'.\samples\input.xlsx', r'.\config\config_rizepem_2026_2.yaml', r'.\out'))"
```

## Legacy / Demo

- `python gui.py` ve `src/app` akışı legacy/demo amaçlıdır.
- Üretim için tek doğru entrypoint: `report_builder.generate_report(...)`.

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

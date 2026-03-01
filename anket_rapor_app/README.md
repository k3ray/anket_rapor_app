# Anket Rapor App

## Çalıştırma

```bash
pip install -r requirements.txt
python gui.py
```

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

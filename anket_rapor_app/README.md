# anket_rapor_app (v0)

Bu proje, Excel anket çıktısından **minimal** 2 sayfalık PDF rapor üretir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Çalıştırma

Repo içindeki örnek veriyle:

```bash
python -m app \
  --input samples/input.xlsx \
  --config config/config_rizepem_2026_2.yaml \
  --out out/report.pdf
```

## Üretilen içerik (v0)

- Sayfa 1: 1 demografik dağılım (YAŞ) tablosu + grafiği
- Sayfa 2: 1 kapalı uçlu soru dağılımı tablosu + grafiği

PDF beyaz arka planlıdır (ızgara/çizgili arka plan kullanılmaz).

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


PII_PATTERNS = {
    "email": (re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"), "[E-POSTA]"),
    "phone_tr": (
        re.compile(r"(?:\+90|0)?\s*\(?5\d{2}\)?[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}\b"),
        "[TELEFON]",
    ),
    "tc_kimlik_no": (re.compile(r"\b[1-9][0-9]{10}\b"), "[TC_KIMLIK]"),
}


@dataclass
class ThemeResult:
    theme: str
    summary: str
    quotes: list[str]


def mask_pii(text: str, enabled: bool = True, patterns: list[str] | None = None) -> str:
    if not enabled or not isinstance(text, str):
        return text
    masked = text
    for key in (patterns or list(PII_PATTERNS.keys())):
        pattern, token = PII_PATTERNS.get(key, (None, None))
        if pattern is not None:
            masked = pattern.sub(token, masked)
    return masked


def _call_local_llm(texts: list[str], model: str = "llama3.1") -> list[ThemeResult] | None:
    if not requests or not texts:
        return None
    payload_text = "\n".join(f"- {t}" for t in texts[:300])
    prompt = (
        "Aşağıdaki Türkçe açık uçlu anket yanıtlarından 5-10 tema çıkar. "
        "Her tema için 1-2 cümle özet ve 2-4 kısa alıntı ver. JSON döndür: "
        "[{theme, summary, quotes:[...] }].\n\n"
        f"Yanıtlar:\n{payload_text}"
    )
    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("response", "")
        import json

        raw = json.loads(data)
        out: list[ThemeResult] = []
        for item in raw:
            out.append(
                ThemeResult(
                    theme=item.get("theme", "Tema"),
                    summary=item.get("summary", ""),
                    quotes=item.get("quotes", [])[:4],
                )
            )
        return out[:10]
    except Exception:
        return None


def _fallback_tfidf_cluster(texts: list[str]) -> list[ThemeResult]:
    cleaned = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
    if not cleaned:
        return []

    k = max(5, min(10, len(cleaned)))
    if len(cleaned) < 5:
        k = len(cleaned)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_features=1000,
    )
    x = vectorizer.fit_transform(cleaned)

    if k == 1:
        labels = [0] * len(cleaned)
        centers = x.mean(axis=0)
    else:
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = model.fit_predict(x)
        centers = model.cluster_centers_

    feats = vectorizer.get_feature_names_out()
    results: list[ThemeResult] = []

    for idx in range(k):
        idxs = [i for i, lbl in enumerate(labels) if lbl == idx]
        if not idxs:
            continue

        center = centers[idx] if k > 1 else centers
        top_term_ids = center.argsort()[-5:][::-1]
        terms = [feats[i] for i in top_term_ids if i < len(feats)]
        theme_name = f"Tema {len(results)+1}: {', '.join(terms[:2])}" if terms else f"Tema {len(results)+1}"
        summary = (
            f"Katılımcılar bu temada çoğunlukla {', '.join(terms[:3]) if terms else 'benzer konuları'} vurgulamıştır. "
            "Yanıtlarda geliştirme önerileri ve uygulama beklentileri öne çıkmaktadır."
        )
        quotes = [cleaned[i][:240] for i in idxs[:4]]
        results.append(ThemeResult(theme=theme_name, summary=summary, quotes=quotes))

    return results[:10]


def analyze_open_ended(
    df: pd.DataFrame,
    open_ended_config: dict[str, Any],
    llm_enabled: bool = True,
) -> dict[str, list[ThemeResult]]:
    pii_cfg = open_ended_config.get("pii_masking", {})
    pii_enabled = pii_cfg.get("enabled", True)
    pii_patterns = pii_cfg.get("patterns", ["email", "phone_tr", "tc_kimlik_no"])

    out: dict[str, list[ThemeResult]] = {}
    for col_cfg in open_ended_config.get("columns", []):
        col = col_cfg.get("column")
        title = col_cfg.get("title", col)
        if col not in df.columns:
            out[title] = []
            continue

        texts = [mask_pii(str(v), pii_enabled, pii_patterns) for v in df[col].dropna().tolist() if str(v).strip()]

        themes = _call_local_llm(texts) if llm_enabled else None
        if not themes:
            themes = _fallback_tfidf_cluster(texts)
        out[title] = themes

    return out

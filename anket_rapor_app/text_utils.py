from __future__ import annotations

import re
from typing import Any

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
NBSP_RE = re.compile(r"&nbsp;", flags=re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = ZERO_WIDTH_RE.sub("", text)
    text = NBSP_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text)
    return text.strip()


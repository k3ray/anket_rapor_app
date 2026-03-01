from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def format_percent_tr(value: float) -> str:
    """Format percentage with one decimal and Turkish comma separator."""
    return f"{value:.1f}".replace(".", ",")


def _normalize_response(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def compute_closed_ended_table(
    responses: Iterable[Any],
    scale_name: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Compute closed-ended frequency and percentage table.

    - f and % are generated for configured categories.
    - category order is strictly the order from config scales.
    - NaN and blank responses are ignored.
    - percentages are TR formatted with one decimal precision.
    """
    categories = config["scales"].get(scale_name, [])
    if not categories:
        raise ValueError(f"Scale '{scale_name}' has no categories")

    normalized = [_normalize_response(v) for v in responses]
    valid = [v for v in normalized if v is not None and v in categories]

    total = len(valid)
    counts = Counter(valid)

    records: list[dict[str, Any]] = []
    for category in categories:
        f = counts.get(category, 0)
        pct = 0.0 if total == 0 else (f / total) * 100
        records.append({"Kategori": category, "f": f, "%": format_percent_tr(pct)})

    return records

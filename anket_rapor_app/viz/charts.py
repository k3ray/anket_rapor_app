from __future__ import annotations

from pathlib import Path
from typing import Any


def get_chart_categories_and_values(table_rows: list[dict[str, Any]]) -> tuple[list[str], list[int]]:
    """Return chart categories and frequencies in exact table order."""
    categories = [str(row["Kategori"]) for row in table_rows]
    values = [int(row["f"]) for row in table_rows]
    return categories, values


def choose_chart_type(section_roman: str, field_name: str) -> str:
    """
    Chart rules:
    - I–II sections: pie chart
    - province distribution: bar chart
    """
    if field_name.lower() == "province":
        return "bar"
    if section_roman in {"I", "II"}:
        return "pie"
    return "bar"


def draw_chart(
    table_rows: list[dict[str, Any]],
    output_path: str | Path,
    section_roman: str,
    field_name: str,
    title: str | None = None,
) -> Path:
    import matplotlib.pyplot as plt

    chart_type = choose_chart_type(section_roman=section_roman, field_name=field_name)
    categories, values = get_chart_categories_and_values(table_rows)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    if chart_type == "pie":
        ax.pie(values, labels=categories, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    else:
        ax.bar(categories, values)
        ax.set_ylabel("f")
        ax.tick_params(axis="x", rotation=30)

    if title:
        ax.set_title(title)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output

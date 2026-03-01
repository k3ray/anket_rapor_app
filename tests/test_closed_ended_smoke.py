from anket_rapor_app.analysis.closed_ended import compute_closed_ended_table
from anket_rapor_app.viz.charts import get_chart_categories_and_values


def test_closed_ended_smoke_tr_percent_and_order_alignment():
    config = {
        "scales": {
            "yes_no": ["Evet", "Hayır"],
            "agreement_5": ["Tamamen Katılıyorum", "Katılıyorum", "Kararsızım", "Katılmıyorum", "Hiç Katılmıyorum"],
            "quality_5": ["Çok İyi", "İyi", "Orta", "İyi Değil", "Zayıf"],
        }
    }
    responses = ["Evet", "Hayır", None, "", "  ", "Evet", float("nan")]

    table = compute_closed_ended_table(responses=responses, scale_name="yes_no", config=config)

    assert [row["Kategori"] for row in table] == ["Evet", "Hayır"]
    assert [row["f"] for row in table] == [2, 1]
    assert [row["%"] for row in table] == ["66,7", "33,3"]

    chart_categories, chart_values = get_chart_categories_and_values(table)
    assert chart_categories == [row["Kategori"] for row in table]
    assert chart_values == [row["f"] for row in table]

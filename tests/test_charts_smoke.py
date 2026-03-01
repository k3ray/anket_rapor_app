from anket_rapor_app.viz.charts import choose_chart_type


def test_chart_type_rules():
    assert choose_chart_type(section_roman="I", field_name="gender") == "pie"
    assert choose_chart_type(section_roman="II", field_name="some_question") == "pie"
    assert choose_chart_type(section_roman="I", field_name="province") == "bar"

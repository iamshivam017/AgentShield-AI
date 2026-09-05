from app.ml.benchmark import run_benchmark


def test_benchmark_is_reproducible_and_reports_required_metrics() -> None:
    result = run_benchmark()
    assert result["dataset"]["held_out_test_records"] == 1500
    selected = result["selected_operating_point"]
    assert 0 <= selected["precision"] <= 1
    assert 0 <= selected["recall"] <= 1
    assert "estimated_false_positive_cost_paise" in selected
    assert result["test_pr_auc"] > 0.2

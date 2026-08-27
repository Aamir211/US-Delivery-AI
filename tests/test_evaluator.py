from evals.evaluator import evaluate_all


def test_evaluation_harness_runs_all_required_cases() -> None:
    report = evaluate_all()

    assert len(report["task1_results"]) >= 5
    assert len(report["task2_results"]) >= 5
    assert report["passed_count"] + report["failed_count"] == 10
    assert all(0.0 <= result["quality_score"] <= 1.0 for result in report["task1_results"] + report["task2_results"])

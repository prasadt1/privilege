import importlib.util
from pathlib import Path


def load_runner():
    path = Path(__file__).parents[1] / "eval" / "run.py"
    spec = importlib.util.spec_from_file_location("privilege_eval", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mock_evaluation_measures_cumulative_treatment() -> None:
    runner = load_runner()

    results = runner.run_evaluation()

    assert results["mode"] == "mock"
    assert results["validity"] == "VALID"
    assert results["baseline"]["error_count"] == 0
    assert results["treatment"]["error_count"] == 0
    assert results["scenario_count"] == 10
    assert results["turn_count"] == 30
    assert results["baseline"]["metrics"]["leak_recall"] == 0.0
    assert results["treatment"]["metrics"]["leak_recall"] == 1.0
    assert results["treatment"]["metrics"]["receipt_reproducibility"] == 1.0


def test_mode_with_preflight_errors_is_invalid_and_has_no_metrics() -> None:
    runner = load_runner()
    records = [{"error": "PreflightError", "reveals_protected": False}]

    result = runner._mode_result(records)

    assert result["validity"] == "INVALID"
    assert result["error_count"] == 1
    assert "metrics" not in result

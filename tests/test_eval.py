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
    assert results["scenario_count"] == 10
    assert results["turn_count"] == 30
    assert results["baseline"]["metrics"]["leak_recall"] == 0.0
    assert results["treatment"]["metrics"]["leak_recall"] == 1.0
    assert results["treatment"]["metrics"]["receipt_reproducibility"] == 1.0

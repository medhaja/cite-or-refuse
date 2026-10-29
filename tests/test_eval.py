import pytest

from cite_or_refuse.evaluation import run_eval
from cite_or_refuse.pipeline import Pipeline


@pytest.fixture(scope="module")
def pipeline(corpus):
    return Pipeline(corpus)


def test_clean_eval_meets_targets(pipeline):
    report = run_eval(pipeline)
    assert report["mode"] == "mock" and report["questions"] == 30
    m = report["metrics"]
    assert m["recall_at_5"] >= 0.85
    assert m["quote_fidelity"] == 1.0
    assert m["unanswerable_refusal_rate"] >= 0.8
    assert m["false_refusal_rate"] <= 0.15
    assert all(t["pass"] for t in report["targets"].values())


def test_fault_injection_is_caught(pipeline):
    report = run_eval(pipeline, inject_faults=True, fault_rate=0.2, seed=7)
    fi = report["fault_injection"]
    assert fi["injected"] == round(0.2 * report["claims_drafted"])
    assert fi["caught"] / fi["injected"] >= 0.95
    assert fi["clean_claims_refused"] == 0
    assert all(fi["by_type"][t]["injected"] > 0 for t in fi["by_type"])
    assert report["metrics"]["quote_fidelity"] == 1.0


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_fault_catch_holds_across_seeds_and_rates(pipeline, seed):
    report = run_eval(pipeline, inject_faults=True, fault_rate=0.5, seed=seed)
    fi = report["fault_injection"]
    assert fi["caught"] == fi["injected"]


def test_eval_is_deterministic(pipeline):
    assert run_eval(pipeline, inject_faults=True) == run_eval(pipeline, inject_faults=True)

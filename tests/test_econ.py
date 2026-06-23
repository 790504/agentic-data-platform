from adp.econ.pipeline import run_econ_index
from adp.econ import classify, taxonomy
from adp.config import Settings


def test_econ_index_runs_offline(platform):
    rep = run_econ_index(platform, n=60, backend="heuristic")
    assert rep["n"] == 60
    assert rep["backend"] == "heuristic"

    # shares form a valid distribution
    shares = [r["share"] for r in rep["by_occupation"]]
    assert abs(sum(shares) - 1.0) < 1e-6

    # automation + augmentation split sums to 1 per occupation
    for r in rep["by_occupation"]:
        assert abs(r["automation_share"] + r["augmentation_share"] - 1.0) < 1e-6

    # validation produced a sensible correlation (sample is shaped like the reference)
    assert rep["validation"]["spearman"] > 0.5


def test_index_is_registered_and_servable(platform):
    run_econ_index(platform, n=40, backend="heuristic")
    assert platform.mem.get_dataset("econ_index") is not None
    assert platform.mem.get_dataset("usage_classified") is not None
    # lineage chains index -> classified -> source
    inputs = {e["input"] for e in platform.mem.lineage_of("econ_index")}
    assert "usage_classified" in inputs
    # served through the existing platform API surface
    served = platform.serve_dataset("econ_index", limit=100)
    assert served["rows"]


def test_classifier_maps_to_taxonomy():
    s = Settings(anthropic_api_key=None)
    out = classify.classify_one("Write a Python function to sort a list", "heuristic", s)
    assert out["occupation_code"] == "15-1252"  # Software & IT
    assert out["mode"] == "automation"
    out2 = classify.classify_one("Explain how recursion works", "heuristic", s)
    assert out2["mode"] == "augmentation"
    # unknown backend-free path always yields a valid taxonomy code
    assert out["occupation_code"] in taxonomy.CODE_TO_TITLE

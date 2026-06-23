import pytest


def test_agent_orchestrates_dbt_build(platform, samples):
    if not platform.dbt.available():
        pytest.skip("dbt not installed")

    result = platform.agent.run(
        "Ingest the sources and build the dbt transforms.",
        {
            "ingest": [{"path": samples[n], "name": n} for n in samples],
            "dbt": {"command": "build"},
        },
    )
    assert result["status"] == "success"

    # dbt materialized the staging models and the mart
    panel = platform.mem.get_dataset("county_quarter_panel")
    assert panel is not None and panel["n_rows"] == 200
    assert platform.mem.get_dataset("stg_fema_policies") is not None

    # lineage from dbt's manifest chains source -> staging -> mart
    inputs = {e["input"] for e in platform.mem.lineage_of("county_quarter_panel")}
    assert {"stg_fema_policies", "stg_property_sales", "stg_hmda_loans"} <= inputs
    assert any(i.startswith("source:") for i in inputs)  # chain reaches raw CSVs


def test_dbt_lineage_is_idempotent(platform, samples):
    if not platform.dbt.available():
        pytest.skip("dbt not installed")
    hints = {
        "ingest": [{"path": samples[n], "name": n} for n in samples],
        "dbt": {"command": "build"},
    }
    platform.agent.run("build", hints)
    edges1 = len(platform.mem.lineage_of("county_quarter_panel"))
    platform.agent.run("build again", hints)
    edges2 = len(platform.mem.lineage_of("county_quarter_panel"))
    assert edges1 == edges2  # rebuild must not duplicate lineage edges

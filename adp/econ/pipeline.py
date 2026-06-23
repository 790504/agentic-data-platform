"""The Economic Index pipeline:

  conversations -> classify (occupation + automation/augmentation)
                -> land in warehouse (raw.usage_classified)
                -> aggregate to marts.econ_index (occupation shares, auto/aug split)
                -> validate the distribution against a reference
                -> register catalog + lineage (so it is served by the existing API)

Reuses the platform wholesale: warehouse, memory (catalog/lineage), and the
FastAPI serving layer (the index is just another registered dataset).
"""
from __future__ import annotations

import logging

from ..monitoring import METRICS, get_logger, log
from . import reference, samples
from . import taxonomy as T
from .classify import classify_all

_log = get_logger("adp.econ")


def run_econ_index(platform, n: int | None = None, backend: str | None = None, write_samples: bool = False) -> dict:
    settings = platform.settings
    n = n or settings.econ_sample_size
    backend = backend or settings.econ_classifier
    wh, mem = platform.wh, platform.mem

    # 1. conversations (bundled sample; swap for WildChat for real runs)
    convs = samples.generate_conversations(n)
    if write_samples:
        samples.write_csv(convs, settings.data_dir / "econ" / "conversations.csv")
    log(_log, logging.INFO, "econ_start", n=len(convs), backend=backend)

    # 2. classify
    rows = classify_all(convs, backend, settings)

    # 3. land raw
    wh.create_table_from_rows("raw", "usage_classified", rows)
    sch = wh.table_schema("raw", "usage_classified")
    mem.register_dataset("usage_classified", "raw", f"econ:{backend}", len(rows), sch, "classified conversations")
    mem.add_lineage("usage_classified", ["source:conversations"], "classify")

    # 4. aggregate -> the index
    wh.execute(
        '''CREATE OR REPLACE TABLE marts."econ_index" AS
           SELECT occupation_code, occupation,
                  count(*) AS n,
                  count(*) * 1.0 / sum(count(*)) OVER () AS share,
                  avg(CASE WHEN mode = 'automation'   THEN 1.0 ELSE 0.0 END) AS automation_share,
                  avg(CASE WHEN mode = 'augmentation' THEN 1.0 ELSE 0.0 END) AS augmentation_share,
                  avg(confidence) AS avg_confidence
           FROM raw.usage_classified
           GROUP BY occupation_code, occupation
           ORDER BY n DESC'''
    )
    sch = wh.table_schema("marts", "econ_index")
    mem.register_dataset("econ_index", "marts", "econ", wh.row_count("marts", "econ_index"), sch,
                         "AI usage economic index: occupation shares + automation/augmentation")
    mem.add_lineage("econ_index", ["usage_classified"], "aggregate")

    by_occ = wh.query("SELECT * FROM marts.econ_index ORDER BY n DESC")

    # 5. validate against reference distribution
    computed = {r["occupation_code"]: r["share"] for r in by_occ}
    rho = reference.spearman(computed)
    computed_top5 = [r["occupation"] for r in by_occ[:5]]
    ref_codes_top5 = sorted(reference.REFERENCE_SHARES, key=reference.REFERENCE_SHARES.get, reverse=True)[:5]
    ref_top5 = [T.CODE_TO_TITLE[c] for c in ref_codes_top5]
    overlap = len(set(computed_top5) & set(ref_top5))

    auto_overall = wh.query("SELECT avg(CASE WHEN mode='automation' THEN 1.0 ELSE 0.0 END) AS a FROM raw.usage_classified")[0]["a"]
    METRICS.incr("econ.runs")
    log(_log, logging.INFO, "econ_done", occupations=len(by_occ), spearman=rho)

    return {
        "n": len(rows),
        "backend": backend,
        "occupations": len(by_occ),
        "automation_overall": round(auto_overall, 3),
        "by_occupation": by_occ,
        "validation": {"spearman": rho, "top5_overlap": overlap, "computed_top5": computed_top5, "reference_top5": ref_top5},
    }

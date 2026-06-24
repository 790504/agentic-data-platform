"""Command-line entrypoint: `adp <command>`.

Commands:
  demo      generate samples and run the full ingest -> panel -> validate pipeline
  ask       run a single agent task ("adp ask 'build a panel ...'")
  eval      run the evaluation suite (exits non-zero on failure)
  catalog   list registered datasets
  serve     run the FastAPI service (uvicorn)
"""
from __future__ import annotations

import argparse
import json
import sys

from .platform import Platform
from .samples import generate_samples


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_demo(args) -> int:
    p = Platform()
    paths = generate_samples(p.settings.data_dir / "samples")
    task = "Ingest the three economic data sources, integrate them into a county-quarter panel, and validate it."
    hints = {
        "ingest": [{"path": paths[n], "name": n} for n in paths],
        "panel": {"name": "county_quarter_panel", "sources": list(paths), "keys": ["county", "quarter"]},
        "validate": {
            "name": "county_quarter_panel",
            "min_rows": 100,
            "unique_key": ["county", "quarter"],
            "not_null": ["county", "quarter"],
        },
    }
    result = p.agent.run(task, hints)
    print(f"\n=== RUN {result['run_id']} : {result['status']} (planner={result['planner']}) ===")
    for s in result["steps"]:
        mark = "OK " if s["ok"] else "ERR"
        detail = s.get("result", s.get("error"))
        print(f"  [{mark}] {s['tool']:<16} {json.dumps(detail, default=str)[:110]}")
    print("\n--- catalog ---")
    _print(p.mem.catalog())
    print("\n--- lineage(county_quarter_panel) ---")
    _print(p.mem.lineage_of("county_quarter_panel"))
    print("\n--- sample rows ---")
    _print(p.serve_dataset("county_quarter_panel", limit=3))
    from .monitoring import METRICS
    print("\n--- metrics ---")
    _print(METRICS.snapshot())
    p.close()
    return 0 if result["status"] == "success" else 1


def cmd_dbt(args) -> int:
    p = Platform()
    if not p.dbt.available():
        print("dbt not installed. Install with:  uv pip install -e \".[dev]\"")
        p.close()
        return 1
    paths = generate_samples(p.settings.data_dir / "samples")
    result = p.agent.run(
        "Ingest the sources, then build and test the dbt transforms.",
        {
            "ingest": [{"path": paths[n], "name": n} for n in paths],
            "dbt": {"command": "build"},
        },
    )
    backend = "MotherDuck (cloud)" if p.settings.is_cloud else "DuckDB (local)"
    print(f"\n=== dbt RUN {result['run_id']} : {result['status']}  [backend: {backend}] ===")
    for s in result["steps"]:
        mark = "OK " if s["ok"] else "ERR"
        print(f"  [{mark}] {s['tool']:<12} {json.dumps(s.get('result', s.get('error')), default=str)[:120]}")
    print("\n--- lineage(county_quarter_panel) from dbt manifest ---")
    _print(p.mem.lineage_of("county_quarter_panel"))
    print("\n--- sample served rows ---")
    _print(p.serve_dataset("county_quarter_panel", limit=2))
    p.close()
    return 0 if result["status"] == "success" else 1


def cmd_econ(args) -> int:
    from .econ.pipeline import run_econ_index
    p = Platform()
    backend = args.backend or p.settings.econ_classifier
    convs, source = None, "sample"
    if args.source == "wildchat":
        from .econ.wildchat import load_wildchat
        print(f"streaming {args.n or 200} real conversations from WildChat-1M ...")
        convs = load_wildchat(n=args.n or 200)
        source = "wildchat"
    rep = run_econ_index(p, n=args.n, backend=backend, conversations=convs, source_name=source, write_samples=True)
    print(f"\n=== MINI ECONOMIC INDEX  (n={rep['n']}, classifier={rep['backend']}, source={source}) ===")
    print(f"  overall automation share: {rep['automation_overall']:.0%}   "
          f"(augmentation: {1 - rep['automation_overall']:.0%})")
    print(f"\n  {'occupation':<28}{'share':>8}{'auto%':>8}{'aug%':>8}{'n':>6}")
    for r in rep["by_occupation"]:
        print(f"  {r['occupation']:<28}{r['share']:>7.1%}{r['automation_share']:>7.0%}{r['augmentation_share']:>7.0%}{r['n']:>6}")
    v = rep["validation"]
    print(f"\n  validation vs reference distribution:")
    print(f"    Spearman rank corr : {v['spearman']:+.3f}  (1.0 = identical ranking)")
    print(f"    top-5 overlap      : {v['top5_overlap']}/5")
    print(f"    your top-5         : {', '.join(v['computed_top5'])}")
    print(f"    reference top-5    : {', '.join(v['reference_top5'])}")
    print(f"\n  served at:  GET /datasets/econ_index   (run `adp serve`)")
    p.close()
    return 0


def cmd_ask(args) -> int:
    p = Platform()
    result = p.agent.run(args.task)
    _print(result)
    p.close()
    return 0 if result["status"] == "success" else 1


def cmd_eval(args) -> int:
    from .eval_harness import run_eval
    report = run_eval()
    _print(report)
    return 0 if report["failed"] == 0 else 1


def cmd_catalog(args) -> int:
    p = Platform()
    _print(p.mem.catalog())
    p.close()
    return 0


def cmd_serve(args) -> int:
    import uvicorn
    uvicorn.run("adp.api:create_app", factory=True, host=args.host, port=args.port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adp", description="Agentic Data Platform")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="run the end-to-end demo pipeline").set_defaults(func=cmd_demo)

    ask = sub.add_parser("ask", help="run a single agent task")
    ask.add_argument("task")
    ask.set_defaults(func=cmd_ask)

    sub.add_parser("dbt", help="ingest then build+test the dbt transforms").set_defaults(func=cmd_dbt)

    econ = sub.add_parser("econ", help="build a mini AI economic index from conversations")
    econ.add_argument("--n", type=int, default=None, help="number of conversations to classify")
    econ.add_argument("--backend", default=None, help="heuristic | ollama | claude")
    econ.add_argument("--source", default="sample", choices=["sample", "wildchat"], help="conversation source")
    econ.set_defaults(func=cmd_econ)
    sub.add_parser("eval", help="run the evaluation suite").set_defaults(func=cmd_eval)
    sub.add_parser("catalog", help="list datasets").set_defaults(func=cmd_catalog)

    serve = sub.add_parser("serve", help="run the API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

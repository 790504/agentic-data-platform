"""Run the dbt transform project from inside the platform.

Uses dbt's programmatic ``dbtRunner`` (no subprocess/PATH coupling). Because the
local DuckDB backend is single-writer, the warehouse connection is released for
the duration of the dbt invocation and reconnected afterwards. After a build we
read dbt's ``manifest.json`` to recover the real transform DAG as lineage.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .config import Settings
from .monitoring import METRICS, get_logger, log
from .warehouse import Warehouse

_log = get_logger("adp.dbt")


def _default_project_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "transform"


class DbtRunner:
    def __init__(self, settings: Settings, wh: Warehouse):
        self.settings = settings
        self.wh = wh
        self.project_dir = Path(settings.dbt_dir) if settings.dbt_dir else _default_project_dir()

    def available(self) -> bool:
        try:
            import dbt.cli.main  # noqa: F401
        except Exception:
            return False
        return self.project_dir.exists()

    def _export_env(self) -> None:
        # profiles.yml reads these via env_var().
        if not self.wh.is_cloud:
            os.environ["ADP_DB_PATH"] = str(Path(self.settings.db_path).resolve())
        os.environ.setdefault("ADP_MOTHERDUCK_DATABASE", self.settings.motherduck_database)

    def run(self, command: str = "build", target: str | None = None, select: str | None = None) -> dict:
        if not self.available():
            raise RuntimeError("dbt is not installed or transform/ project not found")
        from dbt.cli.main import dbtRunner

        target = target or self.settings.effective_dbt_target()
        args = [
            command,
            "--project-dir", str(self.project_dir),
            "--profiles-dir", str(self.project_dir),
            "--target", target,
        ]
        if select:
            args += ["--select", select]
        self._export_env()
        log(_log, logging.INFO, "dbt_invoke", command=command, target=target)

        with METRICS.timer("dbt.run"), self.wh.released():
            result = dbtRunner().invoke(args)

        nodes = []
        try:
            for r in result.result.results:
                nodes.append({"node": getattr(r.node, "name", "?"), "status": str(r.status)})
        except Exception:
            pass

        if not result.success:
            METRICS.incr("dbt.failure")
            failed = [n for n in nodes if n["status"].lower() not in ("success", "pass")]
            raise RuntimeError(f"dbt {command} failed: {failed or 'see logs'}")

        METRICS.incr("dbt.success")
        return {"command": command, "target": target, "success": True, "nodes": nodes}

    def manifest_lineage(self) -> list[dict]:
        """Recover model -> {sources, models} edges from dbt's compiled manifest."""
        manifest = self.project_dir / "target" / "manifest.json"
        if not manifest.exists():
            return []
        data = json.loads(manifest.read_text(encoding="utf-8"))
        edges: list[dict] = []
        for node in data.get("nodes", {}).values():
            if node.get("resource_type") != "model":
                continue
            out = node["name"]
            for dep in node.get("depends_on", {}).get("nodes", []):
                edges.append({"output": out, "input": dep.split(".")[-1], "transform": "dbt"})
        return edges

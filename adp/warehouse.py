"""DuckDB-backed warehouse with conventional medallion layers.

Layers (schemas):
  raw      -> data ingested verbatim from external sources
  staging  -> cleaned / typed intermediate relations
  marts    -> analysis-ready, served datasets (e.g. the county-quarter panel)
  meta     -> the platform's own catalog / run-history / lineage tables
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

import duckdb

from .monitoring import METRICS, get_logger, log

_log = get_logger("adp.warehouse")
LAYERS = ("raw", "staging", "marts", "meta")
_NUMERIC_HINTS = ("INT", "DOUBLE", "DECIMAL", "FLOAT", "REAL", "NUMERIC", "HUGEINT")


def is_numeric_type(data_type: str) -> bool:
    dt = (data_type or "").upper()
    return any(h in dt for h in _NUMERIC_HINTS)


class Warehouse:
    """Thin, thread-safe wrapper over a single DuckDB connection."""

    def __init__(self, connection: str | Path):
        # ``connection`` is a local DuckDB file path, or a MotherDuck "md:" URI.
        self.connection = str(connection)
        self.is_cloud = self.connection.startswith("md:")
        if not self.is_cloud:
            Path(self.connection).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connect()

    def _connect(self) -> None:
        self._con = duckdb.connect(self.connection)
        for layer in LAYERS:
            self._con.execute(f"CREATE SCHEMA IF NOT EXISTS {layer}")

    @contextmanager
    def released(self):
        """Temporarily drop the connection so an in-process dbt run can take the
        DuckDB file lock, then reconnect. No-op semantics for cloud backends."""
        with self._lock:
            self._con.close()
            try:
                yield
            finally:
                self._connect()

    # --- execution ---
    def execute(self, sql: str, params: list | None = None):
        with self._lock, METRICS.timer("warehouse.execute"):
            try:
                return self._con.execute(sql, params or [])
            except Exception as exc:  # noqa: BLE001
                METRICS.incr("warehouse.error")
                log(_log, logging.ERROR, "sql_error", error=str(exc), sql=sql[:240])
                raise

    def query(self, sql: str, params: list | None = None) -> list[dict]:
        cur = self.execute(sql, params)
        if cur.description is None:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # --- introspection ---
    def relation_exists(self, schema: str, name: str) -> bool:
        return bool(
            self.query(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
                [schema, name],
            )
        )

    def table_schema(self, schema: str, name: str) -> list[dict]:
        return self.query(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
            [schema, name],
        )

    def row_count(self, schema: str, name: str) -> int:
        return self.query(f'SELECT count(*) AS n FROM {schema}."{name}"')[0]["n"]

    def close(self) -> None:
        with self._lock:
            self._con.close()

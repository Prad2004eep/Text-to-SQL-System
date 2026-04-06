"""Query execution helpers."""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Dict, Tuple

import pandas as pd


class QueryExecutionError(Exception):
    """Raised when SQLite execution fails."""


class QueryExecutor:
    """Execute validated SQL against SQLite and return a DataFrame."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._cache: Dict[str, Tuple[pd.DataFrame, float]] = {}

    def execute(self, sql: str) -> pd.DataFrame:
        """Execute SQL and return a DataFrame, using a simple in-memory cache."""
        if sql in self._cache:
            cached_dataframe, _ = self._cache[sql]
            self.logger.info("Serving cached results for query")
            return cached_dataframe.copy()

        try:
            connection = sqlite3.connect(self.db_path)
            started = time.perf_counter()
            dataframe = pd.read_sql_query(sql, connection)
            elapsed = time.perf_counter() - started
            connection.close()
            self._cache[sql] = (dataframe.copy(), elapsed)
            self.logger.info("SQL executed in %.4f seconds", elapsed)
            return dataframe
        except Exception as exc:  # pragma: no cover
            raise QueryExecutionError(f"Failed to execute query: {exc}") from exc

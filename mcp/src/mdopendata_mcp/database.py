from __future__ import annotations

import sqlglot
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlglot import exp

from .config import DatabaseConfig


class QueryRejected(Exception):
    """Raised when a SQL query is not read-only."""


_ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except)


def assert_read_only(sql: str) -> None:
    try:
        statements = [statement for statement in sqlglot.parse(sql) if statement is not None]
    except Exception as exc:
        raise QueryRejected(f"Could not parse SQL: {exc}") from exc

    if not statements:
        raise QueryRejected("Empty query.")
    if len(statements) > 1:
        raise QueryRejected("Multiple statements are not allowed.")
    if not isinstance(statements[0], _ALLOWED_ROOTS):
        raise QueryRejected(f"Only read-only SELECT and set-operation statements are allowed; got {type(statements[0]).__name__}.")


class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self.config.url, pool_pre_ping=True, future=True)
        return self._engine

    def execute(self, sql: str, limit: int | None = None) -> tuple[list[str], list[tuple]]:
        assert_read_only(sql)
        effective_limit = self.config.max_rows if limit is None else min(self.config.max_rows, max(0, int(limit)))
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = []
            for index, row in enumerate(result):
                if index >= effective_limit:
                    break
                rows.append(tuple(row))
        return columns, rows

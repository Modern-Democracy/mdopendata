from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from mcp.server.fastmcp import FastMCP, Image

from .config import Config, load_config
from .database import Database, QueryRejected
from .docgen import generate as generate_docs
from .rendering import render_chart, render_er_diagram, save_asset
from .schema import Schema, load_schema


_config: Config | None = None
_db: Database | None = None
mcp = FastMCP("mdopendata-mcp")


def _cfg() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def _db_handle() -> Database:
    global _db
    if _db is None:
        _db = Database(_cfg().database)
    return _db


def _schema() -> Schema:
    return load_schema(_cfg().paths.schema_sql_dir)


def _format_cell(value: Any) -> str:
    if value is None:
        return "_NULL_"
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= 80 else text[:77] + "..."


def _markdown_table(columns: list[str], rows: list[tuple], max_rows: int = 50) -> str:
    if not columns:
        return "_Query returned no columns._"
    output = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    output.extend("| " + " | ".join(_format_cell(value) for value in row) + " |" for row in rows[:max_rows])
    output.append(f"\n_{min(len(rows), max_rows)} of {len(rows)} row(s) shown._")
    return "\n".join(output)


@mcp.tool()
def list_tables() -> str:
    """List tables parsed from schema/sql."""
    schema = _schema()
    return json.dumps({
        "schema_sql_dir": str(_cfg().paths.schema_sql_dir),
        "tables": [
            {
                "name": table.name,
                "columns": len(table.columns),
                "primary_key": table.primary_key,
                "foreign_keys": len(table.foreign_keys),
                "source_file": table.source_file,
            }
            for table in (schema.tables[name] for name in schema.table_names())
        ],
    }, indent=2)


@mcp.tool()
def describe_table(name: str) -> str:
    """Describe one schema/sql table by qualified name."""
    schema = _schema()
    table = schema.table(name)
    if table is None:
        return json.dumps({"error": f"Table not found: {name}", "available": schema.table_names()}, indent=2)
    return json.dumps({
        "name": table.name,
        "source_file": table.source_file,
        "primary_key": table.primary_key,
        "columns": [column.__dict__ for column in table.columns],
        "foreign_keys": [fk.__dict__ for fk in table.foreign_keys],
    }, indent=2)


@mcp.tool()
def query(sql: str, limit: int = 100) -> str:
    """Run read-only SQL against the configured mdopendata database."""
    try:
        columns, rows = _db_handle().execute(sql, limit=limit)
    except QueryRejected as exc:
        return f"**Query rejected:** {exc}"
    except Exception as exc:
        return f"**Query failed:** {type(exc).__name__}: {exc}"
    return _markdown_table(columns, rows)


@mcp.tool()
def chart(sql: str, x: str | None = None, y: str | list[str] | None = None, kind: str = "bar", title: str | None = None, save_to_wiki: bool = False, save_as: str | None = None) -> Image:
    """Run read-only SQL and render a chart."""
    columns, rows = _db_handle().execute(sql)
    png = render_chart(pd.DataFrame(rows, columns=columns), x=x, y=y, kind=kind, title=title, config=_cfg().rendering)
    if save_to_wiki:
        save_asset(png, _cfg().paths.wiki_dir, save_as or f"chart-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.png")
    return Image(data=png, format="png")


@mcp.tool()
def er_diagram(tables: list[str] | None = None, save_to_wiki: bool = False, save_as: str | None = None) -> Image:
    """Render an ER diagram from schema/sql."""
    png = render_er_diagram(_schema(), tables=tables)
    if save_to_wiki:
        save_asset(png, _cfg().paths.wiki_dir, save_as or f"er-diagram-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.png")
    return Image(data=png, format="png")


@mcp.tool()
def generate_schema_docs() -> str:
    """Generate Markdown schema reference pages under wiki/generated/schema."""
    written = generate_docs(_schema(), _cfg().paths.wiki_dir)
    return json.dumps({"files_written": [str(path) for path in written]}, indent=2)


@mcp.tool()
def list_code_tables() -> str:
    """List release-ready help code tables."""
    return query("""
      SELECT table_key, display_label, description
      FROM help.code_table
      WHERE is_active
        AND audience = 'public'
        AND status = 'active'
        AND review_status = 'release_ready'
      ORDER BY table_key
    """)


@mcp.tool()
def describe_code_table(table_key: str) -> str:
    """Describe one release-ready help code table."""
    return query("""
      SELECT ct.table_key, cv.value_key, cv.raw_value, cv.display_label, cv.description
      FROM help.code_table ct
      JOIN help.code_value cv ON cv.code_table_id = ct.code_table_id
      WHERE ct.table_key = :table_key
        AND ct.is_active
        AND cv.is_active
        AND ct.audience = 'public'
        AND cv.audience = 'public'
        AND ct.status = 'active'
        AND cv.status = 'active'
        AND ct.review_status = 'release_ready'
        AND cv.review_status = 'release_ready'
      ORDER BY cv.sort_order NULLS LAST, cv.value_key
    """.replace(":table_key", "'" + table_key.replace("'", "''") + "'"))


@mcp.tool()
def export_release_help() -> str:
    """Export release-ready help terms and code tables to web/public/help/release-help.json."""
    terms_columns, terms_rows = _db_handle().execute("""
      SELECT term_key, term_type, display_label, short_help, long_help, source_schema, source_table, source_id, citations
      FROM help.term
      WHERE is_active AND audience = 'public' AND status = 'active' AND review_status = 'release_ready'
      ORDER BY display_label, term_key
    """)
    code_columns, code_rows = _db_handle().execute("""
      SELECT ct.table_key, ct.display_label AS table_label, cv.value_key, cv.raw_value, cv.display_label, cv.description, cv.sort_order
      FROM help.code_table ct
      JOIN help.code_value cv ON cv.code_table_id = ct.code_table_id
      WHERE ct.is_active AND cv.is_active
        AND ct.audience = 'public' AND cv.audience = 'public'
        AND ct.status = 'active' AND cv.status = 'active'
        AND ct.review_status = 'release_ready' AND cv.review_status = 'release_ready'
      ORDER BY ct.table_key, cv.sort_order NULLS LAST, cv.value_key
    """)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "terms": [dict(zip(terms_columns, row, strict=True)) for row in terms_rows],
        "codeValues": [dict(zip(code_columns, row, strict=True)) for row in code_rows],
    }
    out_dir = _cfg().paths.web_public_dir / "help"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "release-help.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return json.dumps({"path": str(out_path), "terms": len(payload["terms"]), "codeValues": len(payload["codeValues"])}, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

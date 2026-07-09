"""Remove test-only representative normalized budget records from the 2026/2027 document scope."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
MANIFEST_PATH = BASE / "normalized-import-manifest.json"
REPORT_PATH = BASE / "normalized-import-representative-cleanup-report.json"
SOURCE_SHA = "d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac"
DOCUMENT_KEY = "2026-2027"


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def load_manifest_fact_keys() -> set[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {item["key"] for item in manifest["facts"]}


def fetch_cleanup_scope(cur: psycopg.Cursor, manifest_fact_keys: set[str]) -> dict[str, Any]:
    cur.execute("SELECT id FROM budget.source_document WHERE sha256=%s", (SOURCE_SHA,))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("Source document not found")
    document_id = int(row[0])

    cur.execute(
        """SELECT f.id,
                  li.line_key || ':' || %s || ':' || table_record.table_key || ':column-' ||
                  col.column_index::text || ':' || dp.period_role || ':' || at.code || ':' || mu.code AS fact_key,
                  li.id AS line_item_id,
                  s.id AS statement_id,
                  dp.id AS document_period_id
           FROM budget.fact f
           JOIN budget.line_item li ON li.id=f.line_item_id
           JOIN budget.statement s ON s.id=li.statement_id
           JOIN budget.document_period dp ON dp.id=f.document_period_id
           JOIN budget.source_table_column col ON col.id=dp.source_table_column_id
           JOIN budget.source_table table_record ON table_record.id=col.source_table_id
           JOIN budget.amount_type at ON at.id=f.amount_type_id
           JOIN budget.measure_unit mu ON mu.id=f.measure_unit_id
          WHERE s.document_id=%s
          ORDER BY f.id""",
        (DOCUMENT_KEY, document_id),
    )
    rows = cur.fetchall()
    non_manifest = [row for row in rows if row[1] not in manifest_fact_keys]
    fact_ids = [int(row[0]) for row in non_manifest]
    line_item_ids = sorted({int(row[2]) for row in non_manifest})
    statement_ids = sorted({int(row[3]) for row in non_manifest})
    document_period_ids = sorted({int(row[4]) for row in non_manifest})

    if fact_ids:
        cur.execute(
            """SELECT DISTINCT rr.id
               FROM budget.reconciliation_result rr
              WHERE rr.input_fact_ids && %s::bigint[]
              ORDER BY rr.id""",
            (fact_ids,),
        )
        reconciliation_ids = [int(row[0]) for row in cur.fetchall()]
    else:
        reconciliation_ids = []

    if reconciliation_ids:
        cur.execute(
            """SELECT id FROM budget.review_issue
              WHERE reconciliation_result_id = ANY(%s)
              ORDER BY id""",
            (reconciliation_ids,),
        )
        review_issue_ids = [int(row[0]) for row in cur.fetchall()]
    else:
        review_issue_ids = []

    counts = {}
    for name, sql, params in [
        ("fact_sources", "SELECT count(*) FROM budget.fact_source WHERE fact_id = ANY(%s)", (fact_ids,)),
        ("publication_facts", "SELECT count(*) FROM budget.publication_fact WHERE fact_id = ANY(%s)", (fact_ids,)),
        ("capital_project_facts", "SELECT count(*) FROM budget.capital_project_fact WHERE fact_id = ANY(%s)", (fact_ids,)),
        ("debt_facts", "SELECT count(*) FROM budget.debt_fact WHERE fact_id = ANY(%s)", (fact_ids,)),
        ("rate_facts", "SELECT count(*) FROM budget.rate_fact WHERE fact_id = ANY(%s)", (fact_ids,)),
    ]:
        cur.execute(sql, params)
        counts[name] = int(cur.fetchone()[0])

    return {
        "document_id": document_id,
        "fact_ids": fact_ids,
        "fact_keys": [row[1] for row in non_manifest],
        "line_item_ids": line_item_ids,
        "statement_ids": statement_ids,
        "document_period_ids": document_period_ids,
        "reconciliation_ids": reconciliation_ids,
        "review_issue_ids": review_issue_ids,
        "dependent_counts": counts,
    }


def apply_cleanup(cur: psycopg.Cursor, scope: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}

    if scope["review_issue_ids"]:
        cur.execute(
            "DELETE FROM budget.review_issue_evidence WHERE review_issue_id = ANY(%s)",
            (scope["review_issue_ids"],),
        )
        counts["review_issue_evidence"] = cur.rowcount
        cur.execute(
            "DELETE FROM budget.review_decision WHERE review_issue_id = ANY(%s)",
            (scope["review_issue_ids"],),
        )
        counts["review_decisions"] = cur.rowcount
        cur.execute("DELETE FROM budget.review_issue WHERE id = ANY(%s)", (scope["review_issue_ids"],))
        counts["review_issues"] = cur.rowcount
    else:
        counts["review_issue_evidence"] = 0
        counts["review_decisions"] = 0
        counts["review_issues"] = 0

    if scope["reconciliation_ids"]:
        cur.execute("DELETE FROM budget.reconciliation_result WHERE id = ANY(%s)", (scope["reconciliation_ids"],))
        counts["reconciliations"] = cur.rowcount
    else:
        counts["reconciliations"] = 0

    if scope["fact_ids"]:
        for table in ["capital_project_fact", "debt_fact", "rate_fact", "reserve_fact", "publication_fact", "fact_source"]:
            cur.execute(f"DELETE FROM budget.{table} WHERE fact_id = ANY(%s)", (scope["fact_ids"],))
            counts[table] = cur.rowcount
        cur.execute("DELETE FROM budget.fact WHERE id = ANY(%s)", (scope["fact_ids"],))
        counts["facts"] = cur.rowcount
    else:
        for table in ["capital_project_fact", "debt_fact", "rate_fact", "reserve_fact", "publication_fact", "fact_source"]:
            counts[table] = 0
        counts["facts"] = 0

    if scope["line_item_ids"]:
        cur.execute("DELETE FROM budget.line_item WHERE id = ANY(%s)", (scope["line_item_ids"],))
        counts["line_items"] = cur.rowcount
    else:
        counts["line_items"] = 0

    if scope["statement_ids"]:
        cur.execute(
            """DELETE FROM budget.statement_relationship
              WHERE parent_statement_id = ANY(%s) OR child_statement_id = ANY(%s)""",
            (scope["statement_ids"], scope["statement_ids"]),
        )
        counts["statement_relationships"] = cur.rowcount
        cur.execute("DELETE FROM budget.statement WHERE id = ANY(%s)", (scope["statement_ids"],))
        counts["statements"] = cur.rowcount
    else:
        counts["statement_relationships"] = 0
        counts["statements"] = 0

    if scope["document_period_ids"]:
        cur.execute("DELETE FROM budget.document_period WHERE id = ANY(%s)", (scope["document_period_ids"],))
        counts["document_periods"] = cur.rowcount
    else:
        counts["document_periods"] = 0

    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply cleanup. Without this flag, only write a dry-run report.")
    args = parser.parse_args()

    manifest_fact_keys = load_manifest_fact_keys()
    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cur:
            scope = fetch_cleanup_scope(cur, manifest_fact_keys)
            if scope["dependent_counts"]["publication_facts"] != 0:
                raise RuntimeError("Refusing cleanup because representative facts have publication membership")
            deleted_counts = apply_cleanup(cur, scope) if args.apply else {}
        if args.apply:
            connection.commit()
        else:
            connection.rollback()

    report = {
        "schema_version": 1,
        "status": "applied" if args.apply else "dry_run",
        "source_sha256": SOURCE_SHA,
        "scope": {
            "facts": len(scope["fact_ids"]),
            "line_items": len(scope["line_item_ids"]),
            "statements": len(scope["statement_ids"]),
            "document_periods": len(scope["document_period_ids"]),
            "reconciliations": len(scope["reconciliation_ids"]),
            "review_issues": len(scope["review_issue_ids"]),
            "publication_fact_links": scope["dependent_counts"]["publication_facts"],
        },
        "deleted_counts": deleted_counts,
        "fact_keys": scope["fact_keys"],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "{status}: representative facts={facts}, reconciliations={reconciliations}, review_issues={issues}".format(
            status=report["status"],
            facts=report["scope"]["facts"],
            reconciliations=report["scope"]["reconciliations"],
            issues=report["scope"]["review_issues"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

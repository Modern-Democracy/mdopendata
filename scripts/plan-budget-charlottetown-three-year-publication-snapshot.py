"""Generate a deterministic, non-mutating plan for the first Charlottetown budget snapshot."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import psycopg


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data/budget/charlottetown/publication-snapshot-three-year-dry-run-plan.json"
RELEASE_LABEL = "charlottetown-budget-2024-2027-initial"
TAXONOMY_VERSION = "charlottetown-budget-v1"
SOURCE_SHA256S = (
    "873b011970ea4042d107f7b0c4b8d58c5b5ef49ce5531f8f25f46de9270f37f6",
    "d6d3fa419756eaa482a67ab42b3acdab4bf0d0329c0649fea108e4c1aaad1631",
    "d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac",
)


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def rows_as_dicts(cur: psycopg.Cursor, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cur.execute(query, params)
    columns = [item.name for item in cur.description]
    return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def main() -> int:
    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cur:
            documents = rows_as_dicts(
                cur,
                """SELECT d.id AS document_id, d.title, d.sha256
                   FROM budget.source_document d
                   JOIN budget.municipality m ON m.id=d.municipality_id
                  WHERE m.slug='charlottetown' AND d.sha256 = ANY(%s)
                  ORDER BY d.id""",
                (list(SOURCE_SHA256S),),
            )
            if len(documents) != 3 or {item["sha256"] for item in documents} != set(SOURCE_SHA256S):
                raise RuntimeError("Expected Charlottetown source documents are not present")
            document_ids = [item["document_id"] for item in documents]
            snapshot_count = rows_as_dicts(
                cur, "SELECT count(*)::integer AS count FROM budget.publication_snapshot", ()
            )[0]["count"]
            if snapshot_count != 0:
                raise RuntimeError(f"Refusing plan: publication snapshots already exist ({snapshot_count})")

            base = """FROM budget.fact f
                       JOIN budget.line_item li ON li.id=f.line_item_id
                       JOIN budget.statement s ON s.id=li.statement_id
                       JOIN budget.source_document d ON d.id=s.document_id
                      WHERE d.id = ANY(%s) AND f.review_status='approved'"""
            fact_count = rows_as_dicts(cur, f"SELECT count(*)::integer AS count {base}", (document_ids,))[0]["count"]
            source_counts = rows_as_dicts(
                cur,
                f"""SELECT d.id AS document_id, d.sha256, count(*)::integer AS approved_fact_count
                     {base}
                     GROUP BY d.id,d.sha256 ORDER BY d.id""",
                (document_ids,),
            )
            if fact_count != 6256 or sum(item["approved_fact_count"] for item in source_counts) != fact_count:
                raise RuntimeError(f"Unexpected approved-fact count: {fact_count}")

            dimensions = {
                "fiscal_period": """SELECT fp.label AS key, count(*)::integer AS fact_count
                    FROM budget.fact f JOIN budget.line_item li ON li.id=f.line_item_id
                    JOIN budget.statement s ON s.id=li.statement_id JOIN budget.document_period dp ON dp.id=f.document_period_id
                    JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
                    WHERE s.document_id = ANY(%s) AND f.review_status='approved' GROUP BY fp.label ORDER BY fp.label""",
                "statement_kind": f"SELECT s.statement_kind AS key, count(*)::integer AS fact_count {base} GROUP BY s.statement_kind ORDER BY s.statement_kind",
                "amount_type": """SELECT at.code AS key, count(*)::integer AS fact_count
                    FROM budget.fact f JOIN budget.line_item li ON li.id=f.line_item_id
                    JOIN budget.statement s ON s.id=li.statement_id JOIN budget.amount_type at ON at.id=f.amount_type_id
                    WHERE s.document_id = ANY(%s) AND f.review_status='approved' GROUP BY at.code ORDER BY at.code""",
                "measure_unit": """SELECT mu.code AS key, count(*)::integer AS fact_count
                    FROM budget.fact f JOIN budget.line_item li ON li.id=f.line_item_id
                    JOIN budget.statement s ON s.id=li.statement_id JOIN budget.measure_unit mu ON mu.id=f.measure_unit_id
                    WHERE s.document_id = ANY(%s) AND f.review_status='approved' GROUP BY mu.code ORDER BY mu.code""",
                "value_state": f"SELECT f.value_state AS key, count(*)::integer AS fact_count {base} GROUP BY f.value_state ORDER BY f.value_state",
            }
            counts = {key: rows_as_dicts(cur, query, (document_ids,)) for key, query in dimensions.items()}
            cur.execute(
                """SELECT count(*)::integer
                   FROM budget.review_issue ri
                   JOIN budget.reconciliation_result rr ON rr.id=ri.reconciliation_result_id
                   JOIN budget.statement s ON s.id=rr.statement_id
                  WHERE s.document_id = ANY(%s) AND ri.severity IN ('high','critical')
                    AND ri.status IN ('open','in_review')""",
                (document_ids,),
            )
            open_high_critical = int(cur.fetchone()[0])
            if open_high_critical != 0:
                raise RuntimeError(f"Refusing plan: {open_high_critical} unresolved high/critical issues")

    plan: dict[str, Any] = {
        "schema_version": 1,
        "mode": "dry_run",
        "operation": "create_draft_publication_snapshot",
        "snapshot": {
            "municipality_slug": "charlottetown",
            "release_label": RELEASE_LABEL,
            "taxonomy_version": TAXONOMY_VERSION,
            "status": "draft",
            "source_document_ids": document_ids,
        },
        "source_documents": [
            {**document, "approved_fact_count": next(item["approved_fact_count"] for item in source_counts if item["document_id"] == document["document_id"])}
            for document in documents
        ],
        "expected": {
            "publication_snapshot_count_before": 0,
            "publication_fact_count": fact_count,
            "open_high_or_critical_issue_count": 0,
            "counts": counts,
        },
        "prohibitions": [
            "Do not create a publication snapshot in dry-run mode.",
            "Do not modify facts, source links, raw records, reconciliations, or review decisions.",
            "Do not change snapshot status to published without separate approval.",
        ],
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    plan["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
    OUTPUT_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"fact_count": fact_count, "plan_sha256": plan["plan_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

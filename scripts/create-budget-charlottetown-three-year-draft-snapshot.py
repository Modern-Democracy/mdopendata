"""Create the approved three-year Charlottetown draft publication snapshot."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "data/budget/charlottetown/publication-snapshot-three-year-dry-run-plan.json"
REPORT_PATH = ROOT / "data/budget/charlottetown/publication-snapshot-three-year-draft-report.json"


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def main() -> int:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    snapshot = plan["snapshot"]
    if plan["mode"] != "dry_run" or snapshot["status"] != "draft":
        raise RuntimeError("Plan does not authorize draft snapshot creation")
    document_ids = snapshot["source_document_ids"]
    expected_fact_count = plan["expected"]["publication_fact_count"]

    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (snapshot["release_label"],))
            cur.execute("SELECT id FROM budget.municipality WHERE slug=%s", (snapshot["municipality_slug"],))
            municipality = cur.fetchone()
            if municipality is None:
                raise RuntimeError("Municipality not found")
            municipality_id = int(municipality[0])

            cur.execute(
                """SELECT id,sha256 FROM budget.source_document
                   WHERE municipality_id=%s AND id = ANY(%s) ORDER BY id""",
                (municipality_id, document_ids),
            )
            documents = cur.fetchall()
            expected_shas = [item["sha256"] for item in plan["source_documents"]]
            if [int(row[0]) for row in documents] != document_ids or [row[1] for row in documents] != expected_shas:
                raise RuntimeError("Source-document scope does not match the approved dry-run plan")

            cur.execute("SELECT count(*) FROM budget.publication_snapshot")
            if int(cur.fetchone()[0]) != plan["expected"]["publication_snapshot_count_before"]:
                raise RuntimeError("Publication snapshot count changed after dry-run plan")

            cur.execute(
                """SELECT count(*)
                   FROM budget.review_issue ri
                   JOIN budget.reconciliation_result rr ON rr.id=ri.reconciliation_result_id
                   JOIN budget.statement s ON s.id=rr.statement_id
                  WHERE s.document_id = ANY(%s) AND ri.severity IN ('high','critical')
                    AND ri.status IN ('open','in_review')""",
                (document_ids,),
            )
            if int(cur.fetchone()[0]) != plan["expected"]["open_high_or_critical_issue_count"]:
                raise RuntimeError("Open high/critical issue count changed after dry-run plan")

            cur.execute(
                """SELECT count(*)
                   FROM budget.financial_observation f
                   JOIN budget.line_item li ON li.id=f.line_item_id
                   JOIN budget.statement s ON s.id=li.statement_id
                  WHERE s.document_id = ANY(%s) AND f.review_status='approved'""",
                (document_ids,),
            )
            if int(cur.fetchone()[0]) != expected_fact_count:
                raise RuntimeError("Approved fact count changed after dry-run plan")

            cur.execute(
                """INSERT INTO budget.publication_snapshot
                   (municipality_id,release_label,taxonomy_version,source_document_ids,status)
                   VALUES(%s,%s,%s,%s,'draft') RETURNING id""",
                (municipality_id, snapshot["release_label"], snapshot["taxonomy_version"], document_ids),
            )
            snapshot_id = int(cur.fetchone()[0])
            cur.execute(
                """INSERT INTO budget.publication_observation(snapshot_id,observation_id)
                   SELECT %s,f.id
                   FROM budget.financial_observation f
                   JOIN budget.line_item li ON li.id=f.line_item_id
                   JOIN budget.statement s ON s.id=li.statement_id
                  WHERE s.document_id = ANY(%s) AND f.review_status='approved'""",
                (snapshot_id, document_ids),
            )
            if cur.rowcount != expected_fact_count:
                raise RuntimeError(f"Expected {expected_fact_count} publication facts, inserted {cur.rowcount}")
            cur.execute("SELECT count(*) FROM budget.publication_observation WHERE snapshot_id=%s", (snapshot_id,))
            membership_count = int(cur.fetchone()[0])
            if membership_count != expected_fact_count:
                raise RuntimeError("Snapshot membership count verification failed")
        connection.commit()

    report = {
        "status": "created_draft",
        "snapshot_id": snapshot_id,
        "release_label": snapshot["release_label"],
        "taxonomy_version": snapshot["taxonomy_version"],
        "source_document_ids": document_ids,
        "publication_fact_count": membership_count,
        "publication_status": "draft",
        "plan_sha256": plan["plan_sha256"],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

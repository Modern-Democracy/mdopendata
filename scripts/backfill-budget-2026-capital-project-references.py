"""Backfill approved 2026/2027 capital-project references after migration 026."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
VERSION = "capital-project-reference-backfill-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = load(BASE / "normalized-import-manifest.json")
    references = manifest["capital_project_references"]
    sha = manifest["source_documents"][0]["sha256"]
    event_counts = {"added": 0, "unchanged": 0}
    with psycopg.connect(db_url()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM budget.source_document WHERE sha256=%s", (sha,))
        document_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM budget.municipality WHERE slug='charlottetown'")
        municipality_id = cursor.fetchone()[0]
        cursor.execute("""INSERT INTO budget.import_batch(document_id,source_sha256,extractor_version,status,metrics_json)
                          VALUES(%s,%s,%s,'started',%s) RETURNING id""",
                       (document_id, sha, VERSION, Jsonb({"reference_count": len(references)})))
        batch_id = cursor.fetchone()[0]
        for reference in references:
            cursor.execute("SELECT id FROM budget.capital_project WHERE municipality_id=%s AND project_key=%s", (municipality_id, reference["project_key"]))
            project = cursor.fetchone()
            cursor.execute("SELECT id FROM budget.source_table WHERE document_id=%s AND table_key=%s", (document_id, reference["source_table_key"]))
            table = cursor.fetchone()
            if project is None or table is None:
                raise ValueError(f"Missing project or source table for {reference['key']}")
            cursor.execute("SELECT id FROM budget.source_table_row WHERE source_table_id=%s AND row_key=%s", (table[0], reference["source_row_id"]))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Missing source row for {reference['key']}")
            cursor.execute("""SELECT id,capital_project_id,reference_kind,document_adoption_state,identity_evidence,review_status
                              FROM budget.capital_project_reference
                             WHERE document_id=%s AND source_table_id=%s AND source_row_id=%s AND raw_label=%s""",
                           (document_id, table[0], row[0], reference["raw_label"]))
            existing = cursor.fetchone()
            expected = (project[0], reference["reference_kind"], reference["document_adoption_state"], reference["identity_evidence"], "approved")
            if existing is None:
                cursor.execute("""INSERT INTO budget.capital_project_reference
                    (document_id,capital_project_id,source_table_id,source_row_id,raw_label,reference_kind,document_adoption_state,identity_evidence,review_status)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'approved')""",
                    (document_id, project[0], table[0], row[0], reference["raw_label"], reference["reference_kind"], reference["document_adoption_state"], reference["identity_evidence"]))
                event = "added"
            elif tuple(existing[1:]) == expected:
                event = "unchanged"
            else:
                raise ValueError(f"Changed reference conflict for {reference['key']}")
            event_counts[event] += 1
            cursor.execute("""INSERT INTO budget.import_record_event(batch_id,record_type,natural_key,content_hash,event_type)
                              VALUES(%s,'capital_project_reference',%s,%s,%s)""",
                           (batch_id, reference["key"], canonical_hash(reference), event))
        cursor.execute("UPDATE budget.import_batch SET status='completed',completed_at=now(),metrics_json=metrics_json || %s WHERE id=%s",
                       (Jsonb({"event_counts": event_counts}), batch_id))
        cursor.execute("SELECT count(*) FROM budget.publication_snapshot")
        if cursor.fetchone()[0] != 0:
            raise ValueError("Publication snapshots must remain zero")
        if args.dry_run:
            connection.rollback()
        else:
            connection.commit()
    print(json.dumps({"dry_run": args.dry_run, "references": len(references), "event_counts": event_counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Split 2026/2027 operating detail line items into manifest-defined statements."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/budget/charlottetown/2026-2027/normalized-import-manifest.json"
REPORT_PATH = ROOT / "data/budget/charlottetown/2026-2027/normalized-import-statement-identity-migration-report.json"
SOURCE_SHA = "d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac"
EXTRACTOR_VERSION = "normalized-summary-detail-identity-migration-1"


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def load_plan() -> tuple[dict[str, dict], list[dict], list[dict]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    statements = {item["key"]: item for item in manifest["statements"]}
    detail_lines = [item for item in manifest["line_items"] if item["statement_key"].endswith("-detail-statement")]
    relationships = [
        item for item in manifest["statement_relationships"]
        if item["child_statement_key"].endswith("-detail-statement")
    ]
    if not detail_lines or not relationships:
        raise RuntimeError("Manifest does not define summary/detail migration records")
    return statements, detail_lines, relationships


def content_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the migration. Default is rollback-only validation.")
    args = parser.parse_args()
    statements, detail_lines, relationships = load_plan()

    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM budget.source_document WHERE sha256=%s FOR UPDATE", (SOURCE_SHA,))
            document = cur.fetchone()
            if document is None:
                raise RuntimeError("2026/2027 source document not found")
            document_id = int(document[0])

            detail_keys = sorted({item["statement_key"] for item in detail_lines})
            parent_keys = {key: key.replace("-detail-statement", "-statement") for key in detail_keys}
            expected_by_detail = {item["key"]: item for item in detail_lines}

            cur.execute(
                """SELECT s.id, s.statement_key, s.reporting_entity_id, s.fund_id, s.statement_kind, s.title,
                          s.scope_note, s.source_table_id
                   FROM budget.statement s
                  WHERE s.document_id=%s
                  FOR UPDATE""",
                (document_id,),
            )
            existing = {row[1]: row for row in cur.fetchall()}
            missing_parents = sorted(set(parent_keys.values()) - set(existing))
            present_details = sorted(set(detail_keys) & set(existing))
            if missing_parents or present_details:
                raise RuntimeError(f"Unexpected statement state: missing_parents={missing_parents}, present_details={present_details}")

            cur.execute(
                """SELECT li.id, s.statement_key, li.line_key, li.source_row_id, li.parent_id,
                          li.raw_label, li.display_label, li.line_kind, li.aggregation_role,
                          li.organization_unit_id
                   FROM budget.line_item li
                   JOIN budget.statement s ON s.id=li.statement_id
                  WHERE s.document_id=%s
                  FOR UPDATE""",
                (document_id,),
            )
            legacy_lines = {(statement_key, line_key): row for row in cur.fetchall() for statement_key, line_key in [(row[1], row[2])]}

            moves = []
            for expected in detail_lines:
                detail_key = expected["statement_key"]
                parent_key = parent_keys[detail_key]
                old_key = expected["key"].replace(detail_key + ":", parent_key + ":", 1)
                row = legacy_lines.get((parent_key, old_key))
                if row is None:
                    raise RuntimeError(f"Legacy line item not found: {old_key}")
                if row[3] is None:
                    raise RuntimeError(f"Legacy line item lacks source row: {old_key}")
                moves.append((expected, row))

            moved_ids = {row[0] for _, row in moves}
            for expected, row in moves:
                parent_id = row[4]
                if parent_id is not None and parent_id not in moved_ids:
                    raise RuntimeError(f"Cross-statement parent would remain after move: {expected['key']}")
                if (row[5], row[6], row[7], row[8]) != (
                    expected["raw_label"], expected["display_label"], expected["line_kind"], expected["aggregation_role"],
                ):
                    raise RuntimeError(f"Line content mismatch: {expected['key']}")

            cur.execute(
                """SELECT count(*)
                   FROM budget.financial_observation f JOIN budget.line_item li ON li.id=f.line_item_id
                  WHERE li.id = ANY(%s)""",
                (sorted(moved_ids),),
            )
            fact_count = int(cur.fetchone()[0])
            if fact_count != len(moves):
                raise RuntimeError(f"Expected one fact per migrated line item, found {fact_count} facts for {len(moves)} lines")

            cur.execute(
                """SELECT count(*)
                   FROM budget.financial_observation_source fs JOIN budget.financial_observation f ON f.id=fs.observation_id
                   JOIN budget.line_item li ON li.id=f.line_item_id
                  WHERE li.id = ANY(%s)""",
                (sorted(moved_ids),),
            )
            source_link_count = int(cur.fetchone()[0])
            if source_link_count != fact_count:
                raise RuntimeError(f"Expected one source link per migrated fact, found {source_link_count}")

            batch_id = None
            if args.apply:
                cur.execute(
                    """INSERT INTO budget.import_batch(document_id,source_sha256,extractor_version,completed_at,status,metrics_json)
                       VALUES (%s,%s,%s,now(),'completed',%s::jsonb) RETURNING id""",
                    (document_id, SOURCE_SHA, EXTRACTOR_VERSION, json.dumps({"detail_statements": len(detail_keys), "line_items": len(moves), "facts": fact_count})),
                )
                batch_id = int(cur.fetchone()[0])
                statement_ids = {}
                for detail_key in detail_keys:
                    parent = existing[parent_keys[detail_key]]
                    expected_statement = statements[detail_key]
                    if (parent[4], parent[5]) != (expected_statement["statement_kind"], expected_statement["title"]):
                        raise RuntimeError(f"Parent statement content mismatch: {parent_keys[detail_key]}")
                    cur.execute(
                        """INSERT INTO budget.statement(document_id,reporting_entity_id,fund_id,statement_key,statement_kind,title,scope_note,source_table_id)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (document_id, parent[2], parent[3], detail_key, expected_statement["statement_kind"], expected_statement["title"], parent[6], parent[7]),
                    )
                    statement_ids[detail_key] = int(cur.fetchone()[0])

                for expected, row in moves:
                    cur.execute("UPDATE budget.line_item SET statement_id=%s, line_key=%s WHERE id=%s", (statement_ids[expected["statement_key"]], expected["key"], row[0]))
                    cur.execute(
                        """INSERT INTO budget.import_record_event(batch_id,record_type,natural_key,content_hash,event_type)
                           VALUES(%s,'line_item',%s,%s,'changed')""",
                        (batch_id, expected["key"], content_hash(expected)),
                    )

                for relationship in relationships:
                    cur.execute(
                        """INSERT INTO budget.statement_relationship(parent_statement_id,child_statement_id,relationship_type)
                           VALUES(%s,%s,%s)""",
                        (existing[relationship["parent_statement_key"]][0], statement_ids[relationship["child_statement_key"]], relationship["relationship_type"]),
                    )

                connection.commit()
            else:
                connection.rollback()

    report = {
        "status": "applied" if args.apply else "dry_run",
        "source_sha256": SOURCE_SHA,
        "detail_statement_count": len(detail_keys),
        "line_item_count": len(moves),
        "fact_count": fact_count,
        "fact_source_count": source_link_count,
        "import_batch_id": batch_id,
        "detail_statements": detail_keys,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

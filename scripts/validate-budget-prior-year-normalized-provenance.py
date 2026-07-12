"""Validate prior-year normalized artifacts and database source fidelity."""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown"
DOCUMENTS = ("2024-2025", "2025-2026")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def equal_number(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left is right
    return Decimal(left) == Decimal(right)


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def main() -> int:
    reports = []
    with psycopg.connect(db_url()) as connection, connection.cursor() as cursor:
        for document in DOCUMENTS:
            root = BASE / document
            manifest = load(root / "normalized-import-manifest.json")
            rows = {item["row_id"]: item for item in load(root / "raw-tables/source_table_rows.json")["records"]}
            values = {item["value_id"]: item for item in load(root / "raw-tables/source_values.json")["records"]}
            facts = {item["key"]: item for item in manifest["facts"]}
            source_version = manifest["source_tables"][0]["key"].rsplit(":", 1)[1]
            mismatches = []
            for link in manifest["fact_sources"]:
                value = values.get(link["source_value_id"])
                fact = facts.get(link["fact_key"])
                row = rows.get(value["row_id"]) if value else None
                expected_numeric = "0" if fact and fact["value_state"] == "reported_zero" and value and value["parsed_decimal"] is None else (value["parsed_decimal"] if value else None)
                checks = {
                    "value_exists": value is not None,
                    "fact_exists": fact is not None,
                    "row_exists": row is not None,
                    "value_linked_from_row": row is not None and value["value_id"] in row["value_ids"],
                    "numeric_matches": fact is not None and equal_number(fact["value_numeric"], expected_numeric),
                    "cell_key_matches": value is not None and link["source_cell_key"] == f"{value['table_id']}:{source_version}:{value['row_id']}:column-{value['value_index']}",
                }
                if not all(checks.values()):
                    mismatches.append({"key": link["key"], "checks": checks})

            cursor.execute(
                """SELECT row.row_key,col.column_index,cell.raw_text,cell.parsed_numeric::text
                     FROM budget.source_table_cell cell
                     JOIN budget.source_table_row row ON row.id=cell.source_row_id
                     JOIN budget.source_table_column col ON col.id=cell.source_table_column_id
                     JOIN budget.source_table tab ON tab.id=row.source_table_id
                     JOIN budget.source_document doc ON doc.id=tab.document_id
                    WHERE doc.sha256=%s AND tab.table_key LIKE %s""",
                (manifest["source_documents"][0]["sha256"], f"%:{source_version}"),
            )
            database_cells = {(row_key, index): (raw_text, numeric) for row_key, index, raw_text, numeric in cursor.fetchall()}
            database_mismatches = []
            for link in manifest["fact_sources"]:
                value = values[link["source_value_id"]]
                db_value = database_cells.get((value["row_id"], value["value_index"]))
                if db_value is None or db_value[0] != value["raw_value"] or not equal_number(db_value[1], value["parsed_decimal"]):
                    database_mismatches.append(link["source_cell_key"])

            sha = manifest["source_documents"][0]["sha256"]
            cursor.execute("""SELECT count(*) FROM budget.fact f JOIN budget.line_item li ON li.id=f.line_item_id JOIN budget.statement s ON s.id=li.statement_id JOIN budget.source_document d ON d.id=s.document_id WHERE d.sha256=%s""", (sha,))
            database_fact_count = int(cursor.fetchone()[0])
            cursor.execute("""SELECT count(*) FROM budget.fact_source fs JOIN budget.fact f ON f.id=fs.fact_id JOIN budget.line_item li ON li.id=f.line_item_id JOIN budget.statement s ON s.id=li.statement_id JOIN budget.source_document d ON d.id=s.document_id WHERE d.sha256=%s""", (sha,))
            database_source_count = int(cursor.fetchone()[0])
            cursor.execute("""SELECT count(*),count(*) FILTER (WHERE NOT rr.passed) FROM budget.reconciliation_result rr JOIN budget.statement s ON s.id=rr.statement_id JOIN budget.source_document d ON d.id=s.document_id WHERE d.sha256=%s""", (sha,))
            reconciliation_count, failed_reconciliations = map(int, cursor.fetchone())
            cursor.execute("SELECT count(*) FROM budget.publication_snapshot")
            snapshots = int(cursor.fetchone()[0])
            report = {
                "document_key": document,
                "manifest_fact_count": len(manifest["facts"]), "database_fact_count": database_fact_count,
                "manifest_fact_source_count": len(manifest["fact_sources"]), "database_fact_source_count": database_source_count,
                "artifact_mismatch_count": len(mismatches), "database_source_mismatch_count": len(database_mismatches),
                "reconciliation_count": reconciliation_count, "failed_reconciliation_count": failed_reconciliations,
                "publication_snapshot_count": snapshots,
            }
            report["passed"] = (
                database_fact_count == len(manifest["facts"])
                and database_source_count == len(manifest["fact_sources"])
                and not mismatches and not database_mismatches and not failed_reconciliations and snapshots == 0
            )
            (root / "normalized-import-provenance-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            reports.append(report)
        cursor.execute("""SELECT count(*) FROM (SELECT capital_project_id FROM budget.capital_project_reference GROUP BY capital_project_id HAVING count(DISTINCT document_id) > 1) shared""")
        shared_project_count = int(cursor.fetchone()[0])
    result = {"documents": reports, "shared_cross_document_project_count": shared_project_count, "passed": all(item["passed"] for item in reports)}
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

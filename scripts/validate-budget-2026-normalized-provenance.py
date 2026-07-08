"""Validate Phase 3 source-cell and capital-profile provenance."""

from __future__ import annotations

import json
import argparse
import os
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
OUTPUT = BASE / "normalized-import-provenance-report.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decimal_equal(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left is right
    return Decimal(left) == Decimal(right)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    manifest = load(BASE / "normalized-import-manifest.json")
    rows = {x["row_id"]: x for x in load(BASE / "raw-tables/source_table_rows.json")["records"]}
    values = {x["value_id"]: x for x in load(BASE / "raw-tables/source_values.json")["records"]}
    facts = {x["key"]: x for x in manifest["facts"]}

    mismatches = []
    cell_keys = set()
    for link in manifest["fact_sources"]:
        value = values.get(link["source_value_id"])
        fact = facts.get(link["fact_key"])
        if value is None or fact is None:
            mismatches.append({"key": link["key"], "issue": "missing_value_or_fact"})
            continue
        row = rows.get(value["row_id"])
        expected_cell = f"{value['table_id']}:full-2:{value['row_id']}:column-{value['value_index']}"
        checks = {
            "row_exists": row is not None,
            "table_matches": row is not None and row["table_id"] == value["table_id"],
            "value_linked_from_row": row is not None and value["value_id"] in row["value_ids"],
            "raw_token_matches_span": row is not None and row["raw_text"][value["char_start"]:value["char_end"]] == value["raw_value"],
            "numeric_matches": decimal_equal(fact["value_numeric"], value["parsed_decimal"]),
            "cell_key_matches": link["source_cell_key"] == expected_cell,
        }
        if not all(checks.values()):
            mismatches.append({"key": link["key"], "issue": "validation_failed", "checks": checks})
        cell_keys.add(link["source_cell_key"])

    profile_mismatches = []
    profile_row_link_count = 0
    for profile in manifest["capital_project_profiles"]:
        for field, row_ids in profile["source_row_ids"].items():
            profile_row_link_count += len(row_ids)
            missing = [row_id for row_id in row_ids if row_id not in rows]
            if missing:
                profile_mismatches.append({"profile_key": profile["key"], "field": field, "missing_rows": missing})

    page87 = []
    for fact in manifest["facts"]:
        if "ctown_budget_2026_2027_p087_r051" not in fact["line_key"]:
            continue
        links = [x for x in manifest["fact_sources"] if x["fact_key"] == fact["key"]]
        page87.append({"fact_key": fact["key"], "logical_line_key": fact["line_key"],
                       "source_row_ids": sorted({values[x["source_value_id"]]["row_id"] for x in links}),
                       "source_cell_keys": [x["source_cell_key"] for x in links]})

    database_report = {"checked": False, "missing_count": None, "mismatch_count": None, "mismatches": []}
    if args.database:
        import psycopg
        url = "postgresql://{}:{}@{}:{}/{}".format(
            os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
            os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"),
            os.environ.get("PGDATABASE", "mdopendata"),
        )
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute("""SELECT r.row_key,col.column_index,cell.raw_text,cell.parsed_numeric
              FROM budget.source_table_cell cell
              JOIN budget.source_table_row r ON r.id=cell.source_row_id
              JOIN budget.source_table_column col ON col.id=cell.source_table_column_id
              JOIN budget.source_table t ON t.id=r.source_table_id
              JOIN budget.source_document d ON d.id=t.document_id
              WHERE d.sha256=%s AND t.table_key LIKE '%%:full-2'""", ("d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac",))
            database_cells = {(row_key, column_index): (raw_text, None if numeric is None else str(numeric))
                              for row_key, column_index, raw_text, numeric in cursor.fetchall()}
            database_missing = []
            database_mismatches = []
            for link in manifest["fact_sources"]:
                value = values[link["source_value_id"]]
                key = (value["row_id"], value["value_index"])
                if key not in database_cells:
                    database_missing.append(link["source_cell_key"])
                    continue
                raw_text, numeric = database_cells[key]
                if raw_text != value["raw_value"] or not decimal_equal(numeric, value["parsed_decimal"]):
                    database_mismatches.append({"source_cell_key": link["source_cell_key"],
                        "database_raw_text": raw_text, "artifact_raw_text": value["raw_value"],
                        "database_parsed_numeric": numeric, "artifact_parsed_numeric": value["parsed_decimal"]})
            cursor.execute("SELECT count(*) FROM budget.publication_snapshot")
            snapshots = cursor.fetchone()[0]
        database_report = {"checked": True, "missing_count": len(database_missing),
                           "missing": database_missing, "mismatch_count": len(database_mismatches),
                           "mismatches": database_mismatches, "publication_snapshot_count": snapshots}

    report = {
        "schema_version": 1,
        "fact_source_links": len(manifest["fact_sources"]),
        "unique_source_cells": len(cell_keys),
        "fact_source_mismatch_count": len(mismatches),
        "fact_source_mismatches": mismatches,
        "capital_profiles": len(manifest["capital_project_profiles"]),
        "capital_profile_field_row_links": profile_row_link_count,
        "capital_profile_mismatch_count": len(profile_mismatches),
        "capital_profile_mismatches": profile_mismatches,
        "page_87_extraction_row_reconstruction": page87,
        "database_validation": database_report,
        "file_validation_passed": not mismatches and not profile_mismatches and len(page87) == 3,
        "gate_4_ready": (not mismatches and not profile_mismatches and len(page87) == 3
                         and database_report["checked"] and database_report["missing_count"] == 0
                         and database_report["mismatch_count"] == 0),
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Validated {report['fact_source_links']} fact links and {profile_row_link_count} profile field-row links; "
          f"mismatches={len(mismatches) + len(profile_mismatches)}")
    return 0 if report["gate_4_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

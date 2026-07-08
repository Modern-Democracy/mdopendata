"""Import reviewed representative Charlottetown budget spike data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "data/budget/charlottetown/schema-spike"
VERSION = "1"


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def load(name: str) -> dict:
    return json.loads((SPIKE / name).read_text(encoding="utf-8"))


def one(cur: psycopg.Cursor, sql: str, params: tuple) -> int:
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Expected database row for {params!r}")
    return int(row[0])


def validate(manifest: dict, pages: list, rows: list, cells: list, reconciliations: list, issues: list) -> None:
    expected = manifest["expected_counts"]
    actual = {"pages": len(pages), "rows": len(rows), "cells": len(cells), "reconciliations": len(reconciliations), "review_issues": len(issues)}
    if actual != expected:
        raise SystemExit(f"Spike count mismatch: expected {expected}, got {actual}")
    cell_keys = {cell["cell_key"] for cell in cells}
    if len(cell_keys) != len(cells):
        raise SystemExit("Duplicate source cell key")
    for fact in manifest["facts"]:
        if fact["source_cell_key"] not in cell_keys:
            raise SystemExit(f"Missing fact evidence cell: {fact['source_cell_key']}")
    for document in manifest["documents"]:
        path = ROOT / document["local_path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != document["sha256"]:
            raise SystemExit(f"PDF hash mismatch: {document['key']}")


def import_data(cur: psycopg.Cursor, manifest: dict, pages: list, rows: list, cells: list, reconciliations: list, issues: list) -> None:
    municipality = manifest["municipality"]
    cur.execute("""INSERT INTO budget.municipality(slug,legal_name,province_code,country_code,effective_from)
      VALUES(%s,%s,%s,%s,'1900-01-01') ON CONFLICT(slug) DO NOTHING""",
      (municipality["key"], municipality["legal_name"], municipality["province_code"], municipality["country_code"]))
    municipality_id = one(cur, "SELECT id FROM budget.municipality WHERE slug=%s", (municipality["key"],))

    document_ids: dict[str, int] = {}
    for document in manifest["documents"]:
        path = ROOT / document["local_path"]
        page_count = len(PdfReader(str(path)).pages)
        cur.execute("""INSERT INTO budget.source_document
          (municipality_id,title,document_kind,local_path,sha256,page_count,status)
          VALUES(%s,%s,'financial_plan',%s,%s,%s,'reviewed') ON CONFLICT(sha256) DO NOTHING""",
          (municipality_id, path.stem, document["local_path"], document["sha256"], page_count))
        document_ids[document["key"]] = one(cur, "SELECT id FROM budget.source_document WHERE sha256=%s", (document["sha256"],))

    entity_ids: dict[str, int] = {}
    for entity in manifest["reporting_entities"]:
        cur.execute("""INSERT INTO budget.reporting_entity
          (municipality_id,slug,display_name,entity_type,effective_from)
          VALUES(%s,%s,%s,%s,'1900-01-01') ON CONFLICT(municipality_id,slug,effective_from) DO NOTHING""",
          (municipality_id, entity["key"], entity["display_name"], entity["entity_type"]))
        entity_ids[entity["key"]] = one(cur, "SELECT id FROM budget.reporting_entity WHERE municipality_id=%s AND slug=%s", (municipality_id, entity["key"]))

    period_ids: dict[str, int] = {}
    for period in manifest["fiscal_periods"]:
        cur.execute("""INSERT INTO budget.fiscal_period(municipality_id,label,start_date,end_date,period_kind)
          VALUES(%s,%s,%s,%s,%s) ON CONFLICT(municipality_id,start_date,end_date,period_kind) DO NOTHING""",
          (municipality_id, period["label"], period["start_date"], period["end_date"], period["period_kind"]))
        period_ids[period["key"]] = one(cur, "SELECT id FROM budget.fiscal_period WHERE municipality_id=%s AND start_date=%s AND end_date=%s AND period_kind=%s", (municipality_id, period["start_date"], period["end_date"], period["period_kind"]))

    page_ids: dict[str, int] = {}
    table_ids: dict[str, int] = {}
    case_config = {case["case_key"]: case for case in manifest["cases"]}
    for page in pages:
        document_id = document_ids[page["document"]]
        method = "ocr" if page["extraction_method"].startswith("ocr_") else page["extraction_method"]
        cur.execute("""INSERT INTO budget.source_page
          (document_id,pdf_page_number,content_type,extraction_method,extractor_version,review_status)
          VALUES(%s,%s,'representative_table',%s,%s,'approved') ON CONFLICT(document_id,pdf_page_number) DO NOTHING""",
          (document_id, page["pdf_page_number"], method, page.get("extractor_version")))
        page_ids[page["page_key"]] = one(cur, "SELECT id FROM budget.source_page WHERE document_id=%s AND pdf_page_number=%s", (document_id, page["pdf_page_number"]))
        table_natural = f"{page['document']}:{page['case_key']}"
        if table_natural not in table_ids:
            cur.execute("""INSERT INTO budget.source_table(document_id,table_key,table_type,extraction_status,review_status)
              VALUES(%s,%s,%s,'extracted','approved') ON CONFLICT(document_id,table_key) DO NOTHING""",
              (document_id, page["case_key"], case_config[page["case_key"]]["statement_kind"]))
            table_ids[table_natural] = one(cur, "SELECT id FROM budget.source_table WHERE document_id=%s AND table_key=%s", (document_id, page["case_key"]))
        cur.execute("""INSERT INTO budget.source_table_page(source_table_id,source_page_id,page_order,page_role)
          VALUES(%s,%s,%s,%s) ON CONFLICT(source_table_id,source_page_id) DO NOTHING""",
          (table_ids[table_natural], page_ids[page["page_key"]], page["page_order"], page["page_role"]))

    page_by_key = {page["page_key"]: page for page in pages}
    row_by_key = {row["row_key"]: row for row in rows}
    columns_by_table: dict[tuple[int, int], int] = {}
    for cell in cells:
        row = row_by_key[cell["row_key"]]
        page = page_by_key[row["page_key"]]
        table_id = table_ids[f"{page['document']}:{cell['case_key']}"]
        key = (table_id, cell["column_index"])
        if key not in columns_by_table:
            cur.execute("""INSERT INTO budget.source_table_column
              (source_table_id,column_key,column_index,column_role,review_status)
              VALUES(%s,%s,%s,'unreviewed','unreviewed') ON CONFLICT(source_table_id,column_index) DO NOTHING""",
              (table_id, f"column-{cell['column_index']}", cell["column_index"]))
            columns_by_table[key] = one(cur, "SELECT id FROM budget.source_table_column WHERE source_table_id=%s AND column_index=%s", key)

    row_ids: dict[str, int] = {}
    ordered_rows = sorted(rows, key=lambda item: (
        table_ids[f"{page_by_key[item['page_key']]['document']}:{item['case_key']}"],
        page_by_key[item["page_key"]]["page_order"], item["row_index"], item["row_key"],
    ))
    table_row_orders: dict[int, int] = {}
    for row in ordered_rows:
        page = page_by_key[row["page_key"]]
        table_id = table_ids[f"{page['document']}:{row['case_key']}"]
        table_row_orders[table_id] = table_row_orders.get(table_id, 0) + 1
        confidence = row.get("ocr_confidence")
        confidence = None if confidence is None else confidence / 100
        cur.execute("""INSERT INTO budget.source_table_row
          (source_table_id,row_key,row_index,raw_text,bbox,parser_confidence)
          VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(source_table_id,row_key) DO NOTHING""",
          (table_id, row["row_key"], table_row_orders[table_id], row["raw_text"], row.get("bbox"), confidence))
        row_ids[row["row_key"]] = one(cur, "SELECT id FROM budget.source_table_row WHERE source_table_id=%s AND row_key=%s", (table_id, row["row_key"]))

    cell_ids: dict[str, int] = {}
    for cell in cells:
        row = row_by_key[cell["row_key"]]
        page = page_by_key[row["page_key"]]
        table_id = table_ids[f"{page['document']}:{cell['case_key']}"]
        confidence = cell.get("ocr_confidence")
        confidence = None if confidence is None else confidence / 100
        cur.execute("""INSERT INTO budget.source_table_cell
          (source_row_id,source_table_column_id,raw_text,bbox,parse_status,parser_confidence)
          VALUES(%s,%s,%s,%s,'unparsed',%s) ON CONFLICT(source_row_id,source_table_column_id) DO NOTHING""",
          (row_ids[cell["row_key"]], columns_by_table[(table_id, cell["column_index"])], cell["raw_text"], cell.get("bbox"), confidence))
        cell_ids[cell["cell_key"]] = one(cur, "SELECT id FROM budget.source_table_cell WHERE source_row_id=%s AND source_table_column_id=%s", (row_ids[cell["row_key"]], columns_by_table[(table_id, cell["column_index"])]))

    statement_ids: dict[str, int] = {}
    for case in manifest["cases"]:
        document_id = document_ids[case["document_key"]]
        table_id = table_ids[f"{case['document_key']}:{case['case_key']}"]
        cur.execute("""INSERT INTO budget.statement(document_id,reporting_entity_id,statement_key,statement_kind,title,source_table_id)
          VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(document_id,statement_key) DO NOTHING""",
          (document_id, entity_ids[case["reporting_entity_key"]], case["statement_key"], case["statement_kind"], case["statement_key"].replace("-", " ").title(), table_id))
        statement_ids[case["case_key"]] = one(cur, "SELECT id FROM budget.statement WHERE document_id=%s AND statement_key=%s", (document_id, case["statement_key"]))

    document_period_ids: dict[str, int] = {}
    for period in manifest["document_periods"]:
        case = case_config[period["case_key"]]
        table_id = table_ids[f"{case['document_key']}:{period['case_key']}"]
        column_id = columns_by_table[(table_id, period["column_index"])]
        document_id = document_ids[case["document_key"]]
        cur.execute("""INSERT INTO budget.document_period
          (document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order,review_status)
          VALUES(%s,%s,%s,%s,%s,%s,'approved') ON CONFLICT(document_id,source_table_column_id,period_role) DO NOTHING""",
          (document_id, period_ids[period["fiscal_period_key"]], column_id, period["period_role"], period["raw_column_label"], period["column_index"]))
        document_period_ids[period["key"]] = one(cur, "SELECT id FROM budget.document_period WHERE document_id=%s AND source_table_column_id=%s AND period_role=%s", (document_id, column_id, period["period_role"]))

    fact_ids: dict[str, int] = {}
    line_ids: dict[tuple[str, str], int] = {}
    for order, fact in enumerate(manifest["facts"], 1):
        line_key = (fact["case_key"], fact["line_key"])
        if line_key not in line_ids:
            source_row_id = one(cur, "SELECT source_row_id FROM budget.source_table_cell WHERE id=%s", (cell_ids[fact["source_cell_key"]],))
            cur.execute("""INSERT INTO budget.line_item
              (statement_id,line_key,row_order,raw_label,line_kind,aggregation_role,source_row_id)
              VALUES(%s,%s,%s,%s,'financial',%s,%s) ON CONFLICT(statement_id,line_key) DO NOTHING""",
              (statement_ids[fact["case_key"]], fact["line_key"], order, fact["raw_label"], fact["aggregation_role"], source_row_id))
            line_ids[line_key] = one(cur, "SELECT id FROM budget.line_item WHERE statement_id=%s AND line_key=%s", (statement_ids[fact["case_key"]], fact["line_key"]))
        amount_type_id = one(cur, "SELECT id FROM budget.amount_type WHERE code=%s", (fact["amount_type"],))
        unit_id = one(cur, "SELECT id FROM budget.measure_unit WHERE code=%s", (fact["measure_unit"],))
        cur.execute("""INSERT INTO budget.fact
          (line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_state,is_reported,review_status)
          VALUES(%s,%s,%s,%s,%s,%s,true,'approved')
          ON CONFLICT(line_item_id,document_period_id,amount_type_id,measure_unit_id) DO NOTHING""",
          (line_ids[line_key], document_period_ids[fact["document_period_key"]], amount_type_id, unit_id, fact.get("value_numeric"), fact["value_state"]))
        fact_id = one(cur, """SELECT id FROM budget.fact WHERE line_item_id=%s AND document_period_id=%s AND amount_type_id=%s AND measure_unit_id=%s""",
          (line_ids[line_key], document_period_ids[fact["document_period_key"]], amount_type_id, unit_id))
        fact_ids[fact["key"]] = fact_id
        roles = fact.get("source_roles", [fact.get("source_role", "reported_value")])
        if "reported_value" not in roles:
            roles = ["reported_value", *roles]
        for source_order, role in enumerate(roles):
            cur.execute("""INSERT INTO budget.fact_source(fact_id,source_cell_id,source_role,source_order)
              VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING""", (fact_id, cell_ids[fact["source_cell_key"]], role, source_order))

    reconciliation_ids: dict[str, int] = {}
    reconciliation_by_key = {item["check_key"]: item for item in reconciliations}
    for check_key, keys in manifest["reconciliation_fact_keys"].items():
        item = reconciliation_by_key[check_key]
        first_fact = manifest["facts"][[x["key"] for x in manifest["facts"]].index(keys[0])]
        cur.execute("""INSERT INTO budget.reconciliation_result
          (statement_id,fiscal_period_id,check_type,calculated_value,reported_value,difference,tolerance,passed,input_fact_ids)
          SELECT %s,dp.fiscal_period_id,%s,%s,%s,%s,%s,%s,%s FROM budget.document_period dp
          WHERE dp.id=%s AND NOT EXISTS (
            SELECT 1 FROM budget.reconciliation_result existing
            WHERE existing.statement_id=%s AND existing.fiscal_period_id=dp.fiscal_period_id AND existing.check_type=%s)
          RETURNING id""",
          (statement_ids[first_fact["case_key"]], check_key, item["calculated_value"], item["reported_value"], item["difference"], item["tolerance"], item["passed"], [fact_ids[k] for k in keys], document_period_ids[first_fact["document_period_key"]], statement_ids[first_fact["case_key"]], check_key))
        inserted = cur.fetchone()
        if inserted:
            reconciliation_ids[check_key] = int(inserted[0])
        else:
            fiscal_period_id = one(cur, "SELECT fiscal_period_id FROM budget.document_period WHERE id=%s", (document_period_ids[first_fact["document_period_key"]],))
            reconciliation_ids[check_key] = one(cur, "SELECT id FROM budget.reconciliation_result WHERE statement_id=%s AND fiscal_period_id=%s AND check_type=%s", (statement_ids[first_fact["case_key"]], fiscal_period_id, check_key))

    issue_by_key = {item["review_key"]: item for item in issues}
    for review_key, check_key in manifest["review_issue_reconciliation_keys"].items():
        issue = issue_by_key[review_key]
        cur.execute("""INSERT INTO budget.review_issue
          (review_key,reconciliation_result_id,subject_record_type,subject_natural_key,issue_code,severity,status,title,description,publication_effect,required_resolution,prohibited_action)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(review_key) DO NOTHING""",
          (review_key, reconciliation_ids[check_key], issue["subject_type"], issue["subject_key"], issue["issue_code"], issue["severity"], issue["status"], issue["title"], issue["description"], issue["publication_effect"], issue["required_resolution"], issue["prohibited_action"]))
        issue_id = one(cur, "SELECT id FROM budget.review_issue WHERE review_key=%s", (review_key,))
        cur.execute("""INSERT INTO budget.review_issue_evidence(review_issue_id,reconciliation_result_id,evidence_role,evidence_order)
          SELECT %s,%s,'reconciliation',0 WHERE NOT EXISTS
          (SELECT 1 FROM budget.review_issue_evidence WHERE review_issue_id=%s AND reconciliation_result_id=%s)""",
          (issue_id, reconciliation_ids[check_key], issue_id, reconciliation_ids[check_key]))

    manifest_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for document in manifest["documents"]:
        cur.execute("""INSERT INTO budget.import_batch(document_id,source_sha256,extractor_version,completed_at,status,metrics_json)
          SELECT %s,%s,%s,now(),'completed',%s WHERE NOT EXISTS
          (SELECT 1 FROM budget.import_batch WHERE document_id=%s AND source_sha256=%s AND extractor_version=%s AND status='completed')""",
          (document_ids[document["key"]], document["sha256"], VERSION, Jsonb({"manifest_sha256": manifest_hash, "pages": len(pages), "rows": len(rows), "cells": len(cells), "facts": len(manifest["facts"])}), document_ids[document["key"]], document["sha256"], VERSION))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = load("normalized-mapping.json")
    pages = load("representative-source-pages.json")["records"]
    rows = load("representative-source-rows.json")["records"]
    cells = load("representative-source-cells.json")["records"]
    reconciliations = load("reconciliation-results.json")["records"]
    issues = load("review-issues.json")["records"]
    validate(manifest, pages, rows, cells, reconciliations, issues)
    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cursor:
            import_data(cursor, manifest, pages, rows, cells, reconciliations, issues)
        if args.dry_run:
            connection.rollback()
            print("Budget spike import validated; transaction rolled back.")
        else:
            connection.commit()
            print("Budget spike import completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

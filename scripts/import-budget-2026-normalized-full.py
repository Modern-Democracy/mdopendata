"""Dry-run-capable full normalized import for Charlottetown 2026/2027 budget."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
SPIKE = ROOT / "data/budget/charlottetown/schema-spike"
MANIFEST_PATH = BASE / "normalized-import-manifest.json"
RECONCILIATION_PATH = BASE / "normalized-import-reconciliation-catalogue.json"
PLAN_PATH = BASE / "normalized-import-dry-run-plan.json"
IMPORTER_VERSION = "normalized-full-1"
DOCUMENT_KEY = "2026-2027"

RATE_UNITS = {
    "cad_per_year": ("CAD per year", "rate", "CAD", "1", "year"),
    "cad_per_day": ("CAD per day", "rate", "CAD", "1", "day"),
    "cad_per_cubic_metre": ("CAD per cubic metre", "rate", "CAD", "1", "cubic metre"),
}


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def db_numeric_text(value: str | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.4f}"


def one(cur: psycopg.Cursor, sql: str, params: tuple = ()) -> int:
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Expected database row for {params!r}")
    return int(row[0])


def all_counts(manifest: dict, reconciliations: dict) -> dict[str, int]:
    return {
        "source_documents": len(manifest["source_documents"]),
        "source_tables": len(manifest["source_tables"]),
        "reporting_entities": len(manifest["reporting_entities"]),
        "organization_units": len(manifest["organization_units"]),
        "fiscal_periods": len(manifest["fiscal_periods"]),
        "document_periods": len(manifest["document_periods"]),
        "statements": len(manifest["statements"]),
        "line_items": len(manifest["line_items"]),
        "facts": len(manifest["facts"]),
        "fact_sources": len(manifest["fact_sources"]),
        "capital_projects": len(manifest["capital_projects"]),
        "capital_project_aliases": len(manifest["capital_project_aliases"]),
        "capital_project_profiles": len(manifest["capital_project_profiles"]),
        "capital_project_facts": len(manifest["capital_project_facts"]),
        "debt_instruments": len(manifest["debt_instruments"]),
        "debt_facts": len(manifest["debt_facts"]),
        "reconciliations": len(reconciliations["records"]),
        "review_issues": len(reconciliations["review_issues"]),
    }


def document_metadata() -> tuple[dict, dict]:
    representative = load(SPIKE / "normalized-mapping.json")
    document = next(item for item in representative["documents"] if item["key"] == DOCUMENT_KEY)
    return representative["municipality"], document


def validate_files(manifest: dict, reconciliations: dict, source_document: dict) -> None:
    expected_counts = {
        "source_documents": 1,
        "source_tables": 85,
        "reporting_entities": 4,
        "organization_units": 13,
        "fiscal_periods": 3,
        "document_periods": 128,
        "statements": 30,
        "line_items": 1163,
        "facts": 2165,
        "fact_sources": 2165,
        "capital_projects": 169,
        "capital_project_aliases": 173,
        "capital_project_profiles": 24,
        "capital_project_facts": 192,
        "debt_instruments": 10,
        "debt_facts": 30,
        "reconciliations": 161,
        "review_issues": 1,
    }
    actual = all_counts(manifest, reconciliations)
    if actual != expected_counts:
        raise SystemExit(f"Full normalized count mismatch: expected {expected_counts}, got {actual}")
    source_path = ROOT / source_document["local_path"]
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_hash != manifest["source_documents"][0]["sha256"]:
        raise SystemExit("Manifest source hash mismatch")
    if source_hash != source_document["sha256"]:
        raise SystemExit("Representative source hash mismatch")
    if len(PdfReader(str(source_path)).pages) != 154:
        raise SystemExit("Unexpected source PDF page count")
    for key in ["facts", "fact_sources", "line_items", "document_periods"]:
        keys = [item["key"] for item in manifest[key]]
        if len(keys) != len(set(keys)):
            raise SystemExit(f"Duplicate manifest keys in {key}")
    fact_keys = {item["key"] for item in manifest["facts"]}
    if any(item["fact_key"] not in fact_keys for item in manifest["fact_sources"]):
        raise SystemExit("Fact source references an unknown fact")
    for record in reconciliations["records"]:
        missing = [key for key in record["input_fact_keys"] + [record["reported_fact_key"]] if key not in fact_keys]
        if missing:
            raise SystemExit(f"Reconciliation references unknown fact keys: {missing[:3]}")
    hash_manifest = json.loads(json.dumps(manifest))
    hash_manifest["manifest_metadata"].pop("manifest_hash_without_hash_field", None)
    manifest_hash = canonical_hash(hash_manifest)
    approved_hash = manifest["manifest_metadata"]["manifest_hash_without_hash_field"]
    if manifest_hash != approved_hash:
        raise SystemExit("Manifest hash validation failed")


def fetch_raw_ids(cur: psycopg.Cursor, manifest: dict, document_sha: str) -> dict[str, dict[str, int]]:
    document_id = one(cur, "SELECT id FROM budget.source_document WHERE sha256=%s", (document_sha,))
    table_ids: dict[str, int] = {}
    for table in manifest["source_tables"]:
        table_ids[table["key"]] = one(
            cur,
            "SELECT id FROM budget.source_table WHERE document_id=%s AND table_key=%s",
            (document_id, table["key"]),
        )
    column_ids: dict[str, int] = {}
    for period in manifest["document_periods"]:
        table_id = table_ids[period["source_table_key"]]
        column_ids[f"{period['source_table_key']}:column-{period['source_column_index']}"] = one(
            cur,
            "SELECT id FROM budget.source_table_column WHERE source_table_id=%s AND column_index=%s",
            (table_id, period["source_column_index"]),
        )
    cell_ids: dict[str, int] = {}
    for source in manifest["fact_sources"]:
        table_key, row_key, column_key = source["source_cell_key"].rsplit(":", 2)
        table_id = table_ids[table_key]
        column_index = int(column_key.removeprefix("column-"))
        cell_ids[source["source_cell_key"]] = one(
            cur,
            """SELECT cell.id
               FROM budget.source_table_cell cell
               JOIN budget.source_table_row row ON row.id=cell.source_row_id
               JOIN budget.source_table_column col ON col.id=cell.source_table_column_id
              WHERE row.source_table_id=%s AND row.row_key=%s AND col.column_index=%s""",
            (table_id, row_key, column_index),
        )
    row_ids: dict[str, int] = {}
    for line in manifest["line_items"]:
        row_ids[line["source_row_id"]] = one(
            cur,
            """SELECT row.id
               FROM budget.source_table_row row
               JOIN budget.source_table table_record ON table_record.id=row.source_table_id
              WHERE table_record.document_id=%s AND row.row_key=%s""",
            (document_id, line["source_row_id"]),
        )
    profile_row_ids = {
        row_id
        for profile in manifest["capital_project_profiles"]
        for row_ids_for_field in profile["source_row_ids"].values()
        for row_id in row_ids_for_field
    }
    for row_id in profile_row_ids:
        if row_id in row_ids:
            continue
        row_ids[row_id] = one(
            cur,
            """SELECT row.id
               FROM budget.source_table_row row
               JOIN budget.source_table table_record ON table_record.id=row.source_table_id
              WHERE table_record.document_id=%s AND row.row_key=%s""",
            (document_id, row_id),
        )
    return {"document": {"id": document_id}, "tables": table_ids, "columns": column_ids, "cells": cell_ids, "rows": row_ids}


def insert_event(cur: psycopg.Cursor, batch_id: int, record_type: str, natural_key: str,
                 content: dict, event_type: str) -> None:
    cur.execute(
        """INSERT INTO budget.import_record_event(batch_id,record_type,natural_key,content_hash,event_type)
           VALUES(%s,%s,%s,%s,%s)""",
        (batch_id, record_type, natural_key, canonical_hash(content), event_type),
    )


def ensure_dimension(cur: psycopg.Cursor, batch_id: int, record_type: str, natural_key: str,
                     select_sql: str, select_params: tuple, insert_sql: str, insert_params: tuple,
                     content: dict) -> int:
    cur.execute(select_sql, select_params)
    row = cur.fetchone()
    if row is None:
        cur.execute(insert_sql, insert_params)
        row_id = int(cur.fetchone()[0])
        insert_event(cur, batch_id, record_type, natural_key, content, "added")
        return row_id
    insert_event(cur, batch_id, record_type, natural_key, content, "unchanged")
    return int(row[0])


def fail_if_changed(label: str, natural_key: str, expected: dict, actual: dict) -> None:
    if expected != actual:
        raise SystemExit(
            f"Changed content conflict for {label} {natural_key}: "
            f"expected {expected!r}, found {actual!r}"
        )


def ensure_no_publication(cur: psycopg.Cursor) -> None:
    cur.execute("SELECT count(*) FROM budget.publication_snapshot")
    count = int(cur.fetchone()[0])
    if count != 0:
        raise SystemExit(f"Publication snapshot count must remain zero, found {count}")


def import_normalized(cur: psycopg.Cursor, manifest: dict, reconciliations: dict, municipality: dict,
                      source_document: dict) -> dict[str, Any]:
    validate_files(manifest, reconciliations, source_document)
    ensure_no_publication(cur)
    raw = fetch_raw_ids(cur, manifest, source_document["sha256"])
    document_id = raw["document"]["id"]
    manifest_hash = manifest["manifest_metadata"]["manifest_hash_without_hash_field"]
    reconciliation_hash = canonical_hash(reconciliations)
    cur.execute(
        """INSERT INTO budget.import_batch(document_id,source_sha256,extractor_version,status,metrics_json)
           VALUES(%s,%s,%s,'started',%s) RETURNING id""",
        (document_id, source_document["sha256"], IMPORTER_VERSION,
         Jsonb({"manifest_hash": manifest_hash, "reconciliation_hash": reconciliation_hash})),
    )
    batch_id = int(cur.fetchone()[0])

    municipality_id = one(cur, "SELECT id FROM budget.municipality WHERE slug=%s", (municipality["key"],))

    for code, spec in RATE_UNITS.items():
        ensure_dimension(
            cur, batch_id, "measure_unit", code,
            "SELECT id FROM budget.measure_unit WHERE code=%s", (code,),
            """INSERT INTO budget.measure_unit(code,display_name,unit_kind,currency_code,scale,denominator_text)
               VALUES(%s,%s,%s,%s,%s,%s) RETURNING id""",
            (code, spec[0], spec[1], spec[2], spec[3], spec[4]),
            {"code": code, "display_name": spec[0], "unit_kind": spec[1], "currency_code": spec[2], "scale": spec[3], "denominator_text": spec[4]},
        )

    entity_ids = {}
    for entity in manifest["reporting_entities"]:
        entity_ids[entity["key"]] = ensure_dimension(
            cur, batch_id, "reporting_entity", entity["key"],
            "SELECT id FROM budget.reporting_entity WHERE municipality_id=%s AND slug=%s AND effective_from='1900-01-01'",
            (municipality_id, entity["key"]),
            """INSERT INTO budget.reporting_entity(municipality_id,slug,display_name,entity_type,effective_from)
               VALUES(%s,%s,%s,%s,'1900-01-01') RETURNING id""",
            (municipality_id, entity["key"], entity["display_name"], entity["entity_type"]),
            entity,
        )

    organization_unit_ids = {}
    for unit in manifest["organization_units"]:
        natural_key = f"{unit['reporting_entity_key']}:{unit['key']}"
        organization_unit_ids[natural_key] = ensure_dimension(
            cur, batch_id, "organization_unit", natural_key,
            "SELECT id FROM budget.organization_unit WHERE reporting_entity_id=%s AND unit_key=%s AND effective_from='1900-01-01'",
            (entity_ids[unit["reporting_entity_key"]], unit["key"]),
            """INSERT INTO budget.organization_unit(reporting_entity_id,unit_key,display_name,unit_type,effective_from)
               VALUES(%s,%s,%s,'department','1900-01-01') RETURNING id""",
            (entity_ids[unit["reporting_entity_key"]], unit["key"], unit["key"].replace("-", " ").title()),
            unit,
        )

    fiscal_period_ids = {}
    for period in manifest["fiscal_periods"]:
        fiscal_period_ids[period["key"]] = ensure_dimension(
            cur, batch_id, "fiscal_period", period["key"],
            "SELECT id FROM budget.fiscal_period WHERE municipality_id=%s AND start_date=%s AND end_date=%s AND period_kind=%s",
            (municipality_id, period["start_date"], period["end_date"], period["period_kind"]),
            """INSERT INTO budget.fiscal_period(municipality_id,label,start_date,end_date,period_kind)
               VALUES(%s,%s,%s,%s,%s) RETURNING id""",
            (municipality_id, period["key"], period["start_date"], period["end_date"], period["period_kind"]),
            period,
        )

    document_period_ids = {}
    for period in manifest["document_periods"]:
        column_id = raw["columns"][f"{period['source_table_key']}:column-{period['source_column_index']}"]
        cur.execute(
            """SELECT fp.start_date::text,fp.end_date::text,fp.period_kind,dp.period_role,dp.raw_column_label,dp.column_order,dp.review_status
               FROM budget.document_period dp
               JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
              WHERE dp.document_id=%s AND dp.source_table_column_id=%s AND dp.period_role=%s""",
            (document_id, column_id, period["period_role"]),
        )
        existing_period = cur.fetchone()
        if existing_period is not None:
            fail_if_changed(
                "document_period",
                period["key"],
                {
                    "start_date": next(fp["start_date"] for fp in manifest["fiscal_periods"] if fp["key"] == period["fiscal_period_key"]),
                    "end_date": next(fp["end_date"] for fp in manifest["fiscal_periods"] if fp["key"] == period["fiscal_period_key"]),
                    "period_kind": next(fp["period_kind"] for fp in manifest["fiscal_periods"] if fp["key"] == period["fiscal_period_key"]),
                    "period_role": period["period_role"],
                    "raw_column_label": period["fiscal_period_key"],
                    "column_order": period["source_column_index"],
                    "review_status": "approved",
                },
                {
                    "start_date": existing_period[0],
                    "end_date": existing_period[1],
                    "period_kind": existing_period[2],
                    "period_role": existing_period[3],
                    "raw_column_label": existing_period[4],
                    "column_order": existing_period[5],
                    "review_status": existing_period[6],
                },
            )
        document_period_ids[period["key"]] = ensure_dimension(
            cur, batch_id, "document_period", period["key"],
            "SELECT id FROM budget.document_period WHERE document_id=%s AND source_table_column_id=%s AND period_role=%s",
            (document_id, column_id, period["period_role"]),
            """INSERT INTO budget.document_period
               (document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order,review_status)
               VALUES(%s,%s,%s,%s,%s,%s,'approved') RETURNING id""",
            (document_id, fiscal_period_ids[period["fiscal_period_key"]], column_id, period["period_role"],
             period["fiscal_period_key"], period["source_column_index"]),
            period,
        )

    statement_ids = {}
    for statement in manifest["statements"]:
        cur.execute(
            """SELECT re.slug,statement_kind,title
               FROM budget.statement statement
               JOIN budget.reporting_entity re ON re.id=statement.reporting_entity_id
              WHERE statement.document_id=%s AND statement.statement_key=%s""",
            (document_id, statement["key"]),
        )
        existing_statement = cur.fetchone()
        if existing_statement is not None:
            fail_if_changed(
                "statement",
                statement["key"],
                {"reporting_entity_key": statement["reporting_entity_key"], "statement_kind": statement["statement_kind"], "title": statement["title"]},
                {"reporting_entity_key": existing_statement[0], "statement_kind": existing_statement[1], "title": existing_statement[2]},
            )
        statement_ids[statement["key"]] = ensure_dimension(
            cur, batch_id, "statement", statement["key"],
            "SELECT id FROM budget.statement WHERE document_id=%s AND statement_key=%s",
            (document_id, statement["key"]),
            """INSERT INTO budget.statement(document_id,reporting_entity_id,statement_key,statement_kind,title,source_table_id)
               VALUES(%s,%s,%s,%s,%s,%s) RETURNING id""",
            (document_id, entity_ids[statement["reporting_entity_key"]], statement["key"], statement["statement_kind"],
             statement["title"], None),
            statement,
        )

    line_ids = {}
    for index, line in enumerate(manifest["line_items"], 1):
        org_id = None
        if line.get("organization_unit_key"):
            statement = next(item for item in manifest["statements"] if item["key"] == line["statement_key"])
            org_id = organization_unit_ids.get(f"{statement['reporting_entity_key']}:{line['organization_unit_key']}")
        content = dict(line, row_order=index)
        cur.execute(
            """SELECT row_order,raw_label,display_label,line_kind,aggregation_role
               FROM budget.line_item WHERE statement_id=%s AND line_key=%s""",
            (statement_ids[line["statement_key"]], line["key"]),
        )
        existing_line = cur.fetchone()
        if existing_line is not None:
            fail_if_changed(
                "line_item",
                line["key"],
                {"row_order": index, "raw_label": line["raw_label"], "display_label": line["display_label"],
                 "line_kind": line["line_kind"], "aggregation_role": line["aggregation_role"]},
                {"row_order": existing_line[0], "raw_label": existing_line[1], "display_label": existing_line[2],
                 "line_kind": existing_line[3], "aggregation_role": existing_line[4]},
            )
        line_ids[line["key"]] = ensure_dimension(
            cur, batch_id, "line_item", line["key"],
            "SELECT id FROM budget.line_item WHERE statement_id=%s AND line_key=%s",
            (statement_ids[line["statement_key"]], line["key"]),
            """INSERT INTO budget.line_item
               (statement_id,line_key,row_order,raw_label,display_label,line_kind,aggregation_role,organization_unit_id,source_row_id)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (statement_ids[line["statement_key"]], line["key"], index, line["raw_label"], line["display_label"],
             line["line_kind"], line["aggregation_role"], org_id, raw["rows"].get(line["source_row_id"])),
            content,
        )

    amount_type_ids = {code: one(cur, "SELECT id FROM budget.amount_type WHERE code=%s", (code,))
                       for code in sorted({fact["amount_type"] for fact in manifest["facts"]})}
    measure_unit_ids = {code: one(cur, "SELECT id FROM budget.measure_unit WHERE code=%s", (code,))
                        for code in sorted({fact["measure_unit"] for fact in manifest["facts"]})}

    fact_ids = {}
    for fact in manifest["facts"]:
        cur.execute(
            """SELECT value_numeric::text,value_text,value_state,is_reported,review_status
               FROM budget.fact
              WHERE line_item_id=%s AND document_period_id=%s AND amount_type_id=%s AND measure_unit_id=%s""",
            (line_ids[fact["line_key"]], document_period_ids[fact["document_period_key"]],
             amount_type_ids[fact["amount_type"]], measure_unit_ids[fact["measure_unit"]]),
        )
        existing_fact = cur.fetchone()
        if existing_fact is not None:
            fail_if_changed(
                "fact",
                fact["key"],
                {"value_numeric": db_numeric_text(fact["value_numeric"]), "value_text": fact["value_text"], "value_state": fact["value_state"],
                 "is_reported": True, "review_status": "approved"},
                {"value_numeric": existing_fact[0], "value_text": existing_fact[1], "value_state": existing_fact[2],
                 "is_reported": existing_fact[3], "review_status": existing_fact[4]},
            )
        fact_ids[fact["key"]] = ensure_dimension(
            cur, batch_id, "fact", fact["key"],
            """SELECT id FROM budget.fact
               WHERE line_item_id=%s AND document_period_id=%s AND amount_type_id=%s AND measure_unit_id=%s""",
            (line_ids[fact["line_key"]], document_period_ids[fact["document_period_key"]],
             amount_type_ids[fact["amount_type"]], measure_unit_ids[fact["measure_unit"]]),
            """INSERT INTO budget.fact
               (line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_text,value_state,is_reported,review_status)
               VALUES(%s,%s,%s,%s,%s,%s,%s,true,'approved') RETURNING id""",
            (line_ids[fact["line_key"]], document_period_ids[fact["document_period_key"]],
             amount_type_ids[fact["amount_type"]], measure_unit_ids[fact["measure_unit"]],
             fact["value_numeric"], fact["value_text"], fact["value_state"]),
            fact,
        )

    for source in manifest["fact_sources"]:
        natural_key = source["key"]
        cur.execute(
            """SELECT 1 FROM budget.fact_source
               WHERE fact_id=%s AND source_cell_id=%s AND source_role=%s""",
            (fact_ids[source["fact_key"]], raw["cells"][source["source_cell_key"]], source["source_role"]),
        )
        if cur.fetchone() is None:
            cur.execute(
                """INSERT INTO budget.fact_source(fact_id,source_cell_id,source_role,source_order)
                   VALUES(%s,%s,%s,%s)""",
                (fact_ids[source["fact_key"]], raw["cells"][source["source_cell_key"]],
                 source["source_role"], source["source_order"]),
            )
            insert_event(cur, batch_id, "fact_source", natural_key, source, "added")
        else:
            insert_event(cur, batch_id, "fact_source", natural_key, source, "unchanged")

    capital_project_ids = {}
    for project in manifest["capital_projects"]:
        capital_project_ids[project["key"]] = ensure_dimension(
            cur, batch_id, "capital_project", project["key"],
            "SELECT id FROM budget.capital_project WHERE municipality_id=%s AND project_key=%s AND effective_from='1900-01-01'",
            (municipality_id, project["key"]),
            """INSERT INTO budget.capital_project(municipality_id,reporting_entity_id,project_key,name,effective_from)
               VALUES(%s,%s,%s,%s,'1900-01-01') RETURNING id""",
            (municipality_id, entity_ids[project["reporting_entity_key"]], project["key"], project["display_name"]),
            project,
        )
    for alias in manifest["capital_project_aliases"]:
        natural_key = f"{alias['project_key']}:{alias['source_row_id']}:{alias['raw_label']}"
        ensure_dimension(
            cur, batch_id, "capital_project_alias", natural_key,
            "SELECT id FROM budget.capital_project_alias WHERE capital_project_id=%s AND document_id=%s AND raw_label=%s",
            (capital_project_ids[alias["project_key"]], document_id, alias["raw_label"]),
            """INSERT INTO budget.capital_project_alias(capital_project_id,document_id,raw_label,review_status)
               VALUES(%s,%s,%s,'approved') RETURNING id""",
            (capital_project_ids[alias["project_key"]], document_id, alias["raw_label"]),
            alias,
        )
    for link in manifest["capital_project_facts"]:
        cur.execute("SELECT 1 FROM budget.capital_project_fact WHERE fact_id=%s", (fact_ids[link["fact_key"]],))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO budget.capital_project_fact(fact_id,capital_project_id) VALUES(%s,%s)",
                (fact_ids[link["fact_key"]], capital_project_ids[link["project_key"]]),
            )
            insert_event(cur, batch_id, "capital_project_fact", f"{link['project_key']}:{link['fact_key']}", link, "added")
        else:
            insert_event(cur, batch_id, "capital_project_fact", f"{link['project_key']}:{link['fact_key']}", link, "unchanged")

    profile_fields = []
    for profile in manifest["capital_project_profiles"]:
        fields = {
            "title": profile["title"],
            "department": profile["department"],
            "project": profile["project"],
            "description": "\n".join(profile["description_lines"]),
            "strategic_alignment": "\n".join(profile["strategic_alignment"]),
        }
        if not profile["capital_project_keys"]:
            insert_event(cur, batch_id, "capital_project_profile_exception", profile["key"], profile, "review_needed")
            continue
        for project_key in profile["capital_project_keys"]:
            for field_key, raw_value in fields.items():
                if raw_value is None:
                    continue
                source_rows = profile["source_row_ids"].get(field_key) or []
                source_row_id = raw["rows"].get(source_rows[0]) if source_rows else None
                natural_key = f"{project_key}:{field_key}"
                content = {"project_key": project_key, "profile_key": profile["key"], "field_key": field_key,
                           "raw_value": raw_value, "source_row_ids": source_rows}
                cur.execute(
                    """SELECT id,raw_value,review_status FROM budget.capital_project_profile
                       WHERE capital_project_id=%s AND document_id=%s AND field_key=%s""",
                    (capital_project_ids[project_key], document_id, field_key),
                )
                existing_profile = cur.fetchone()
                if existing_profile is None:
                    cur.execute(
                        """INSERT INTO budget.capital_project_profile
                           (capital_project_id,document_id,field_key,raw_value,source_row_id,review_status)
                           VALUES(%s,%s,%s,%s,%s,'approved') RETURNING id""",
                        (capital_project_ids[project_key], document_id, field_key, raw_value, source_row_id),
                    )
                    cur.fetchone()
                    insert_event(cur, batch_id, "capital_project_profile", natural_key, content, "added")
                else:
                    fail_if_changed(
                        "capital_project_profile",
                        natural_key,
                        {"raw_value": raw_value, "review_status": "approved"},
                        {"raw_value": existing_profile[1], "review_status": existing_profile[2]},
                    )
                    insert_event(cur, batch_id, "capital_project_profile", natural_key, content, "unchanged")
                profile_fields.append(content)

    debt_instrument_ids = {}
    for instrument in manifest["debt_instruments"]:
        debt_instrument_ids[instrument["key"]] = ensure_dimension(
            cur, batch_id, "debt_instrument", instrument["key"],
            "SELECT id FROM budget.debt_instrument WHERE reporting_entity_id=%s AND raw_label=%s AND effective_from='1900-01-01'",
            (entity_ids["charlottetown-water-sewer"], instrument["raw_label"]),
            """INSERT INTO budget.debt_instrument(reporting_entity_id,raw_label,normalized_label,maturity_date,effective_from)
               VALUES(%s,%s,%s,%s,'1900-01-01') RETURNING id""",
            (entity_ids["charlottetown-water-sewer"], instrument["raw_label"], instrument["key"],
             f"{instrument['maturity_year']}-12-31" if instrument.get("maturity_year") else None),
            instrument,
        )
    facts_by_key = {fact["key"]: fact for fact in manifest["facts"]}
    for link in manifest["debt_facts"]:
        debt_measure = facts_by_key[link["fact_key"]]["amount_type"]
        cur.execute("SELECT 1 FROM budget.debt_fact WHERE fact_id=%s", (fact_ids[link["fact_key"]],))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO budget.debt_fact(fact_id,debt_instrument_id,debt_measure) VALUES(%s,%s,%s)",
                (fact_ids[link["fact_key"]], debt_instrument_ids[link["instrument_key"]], debt_measure),
            )
            insert_event(cur, batch_id, "debt_fact", f"{link['instrument_key']}:{link['fact_key']}", link, "added")
        else:
            insert_event(cur, batch_id, "debt_fact", f"{link['instrument_key']}:{link['fact_key']}", link, "unchanged")

    reconciliation_ids = {}
    for record in reconciliations["records"]:
        reported_fact = facts_by_key[record["reported_fact_key"]]
        statement_key = reported_fact["line_key"].split(":", 1)[0]
        fiscal_period_id = one(
            cur,
            "SELECT fiscal_period_id FROM budget.document_period WHERE id=%s",
            (document_period_ids[reported_fact["document_period_key"]],),
        )
        input_ids = [fact_ids[key] for key in record["input_fact_keys"]]
        cur.execute(
            """SELECT id FROM budget.reconciliation_result
               WHERE statement_id=%s AND fiscal_period_id=%s AND check_type=%s""",
            (statement_ids[statement_key], fiscal_period_id, record["check_key"]),
        )
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                """INSERT INTO budget.reconciliation_result
                   (statement_id,fiscal_period_id,check_type,calculated_value,reported_value,difference,tolerance,passed,input_fact_ids)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (statement_ids[statement_key], fiscal_period_id, record["check_key"],
                 record["calculated_value"], record["reported_value"], record["difference"],
                 record["tolerance"], record["passed"], input_ids),
            )
            reconciliation_ids[record["check_key"]] = int(cur.fetchone()[0])
            insert_event(cur, batch_id, "reconciliation_result", record["check_key"], record, "added")
        else:
            reconciliation_ids[record["check_key"]] = int(existing[0])
            cur.execute(
                """SELECT calculated_value::text,reported_value::text,difference::text,tolerance::text,passed,input_fact_ids
                   FROM budget.reconciliation_result WHERE id=%s""",
                (reconciliation_ids[record["check_key"]],),
            )
            existing_reconciliation = cur.fetchone()
            fail_if_changed(
                "reconciliation_result",
                record["check_key"],
                {"calculated_value": db_numeric_text(record["calculated_value"]),
                 "reported_value": db_numeric_text(record["reported_value"]),
                 "difference": db_numeric_text(record["difference"]),
                 "tolerance": db_numeric_text(record["tolerance"]),
                 "passed": record["passed"], "input_fact_ids": input_ids},
                {"calculated_value": existing_reconciliation[0], "reported_value": existing_reconciliation[1],
                 "difference": existing_reconciliation[2], "tolerance": existing_reconciliation[3],
                 "passed": existing_reconciliation[4], "input_fact_ids": existing_reconciliation[5]},
            )
            insert_event(cur, batch_id, "reconciliation_result", record["check_key"], record, "unchanged")

    for issue in reconciliations["review_issues"]:
        review_key = issue["issue_key"]
        check_key = issue["reconciliation_check_key"]
        content = {
            "review_key": review_key,
            "issue_code": "reported_calculation_variance",
            "severity": "high",
            "status": issue["status"],
            "reason": issue["reason"],
        }
        cur.execute("SELECT id FROM budget.review_issue WHERE review_key=%s", (review_key,))
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                """INSERT INTO budget.review_issue
                   (review_key,reconciliation_result_id,subject_record_type,subject_natural_key,issue_code,severity,status,title,description,publication_effect,required_resolution,prohibited_action)
                   VALUES(%s,%s,'reconciliation',%s,'reported_calculation_variance','high',%s,%s,%s,%s,%s,%s)
                   RETURNING id""",
                (review_key, reconciliation_ids[check_key], check_key, issue["status"],
                 "Debt balance total source discrepancy",
                 "Manual sum of reported debt instrument balances is 2 CAD below the reported total.",
                 "Block publication unless shown as an approved source discrepancy.",
                 "Accept the source discrepancy or obtain authoritative clarification.",
                 "Do not silently alter source values to force reconciliation."),
            )
            issue_id = int(cur.fetchone()[0])
            insert_event(cur, batch_id, "review_issue", review_key, content, "added")
        else:
            issue_id = int(existing[0])
            insert_event(cur, batch_id, "review_issue", review_key, content, "unchanged")
        cur.execute(
            """INSERT INTO budget.review_issue_evidence(review_issue_id,reconciliation_result_id,evidence_role,evidence_order,notes)
               SELECT %s,%s,'reconciliation',0,%s
               WHERE NOT EXISTS (
                 SELECT 1 FROM budget.review_issue_evidence
                  WHERE review_issue_id=%s AND reconciliation_result_id=%s)""",
            (issue_id, reconciliation_ids[check_key], issue["reason"], issue_id, reconciliation_ids[check_key]),
        )

    cur.execute(
        """UPDATE budget.import_batch
              SET status='completed', completed_at=now(),
                  metrics_json = metrics_json || %s::jsonb
            WHERE id=%s""",
        (json.dumps({"counts": all_counts(manifest, reconciliations)}), batch_id),
    )
    ensure_no_publication(cur)
    cur.execute(
        "SELECT record_type,event_type,count(*) FROM budget.import_record_event WHERE batch_id=%s GROUP BY record_type,event_type",
        (batch_id,),
    )
    event_counts = [
        {"record_type": row[0], "event_type": row[1], "count": int(row[2])}
        for row in cur.fetchall()
    ]
    return {
        "schema_version": 1,
        "importer_version": IMPORTER_VERSION,
        "manifest_hash": manifest_hash,
        "reconciliation_hash": reconciliation_hash,
        "expected_counts": all_counts(manifest, reconciliations),
        "event_counts": sorted(event_counts, key=lambda item: (item["record_type"], item["event_type"])),
        "publication_snapshot_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="roll back after producing the import plan")
    args = parser.parse_args()
    manifest = load(MANIFEST_PATH)
    reconciliations = load(RECONCILIATION_PATH)
    municipality, source_document = document_metadata()
    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            plan = import_normalized(cur, manifest, reconciliations, municipality, source_document)
        PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.dry_run:
            connection.rollback()
            print(f"Full normalized import dry run validated; transaction rolled back. Plan: {PLAN_PATH}")
        else:
            connection.commit()
            print(f"Full normalized import completed. Plan: {PLAN_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

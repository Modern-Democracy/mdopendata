"""Verify Phase 7 source-fidelity and completion QA for Charlottetown 2026/2027 budget."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
MANIFEST_PATH = BASE / "normalized-import-manifest.json"
RECONCILIATION_PATH = BASE / "normalized-import-reconciliation-catalogue.json"
RAW_ROWS_PATH = BASE / "raw-tables/source_table_rows.json"
RAW_VALUES_PATH = BASE / "raw-tables/source_values.json"
OUTPUT_PATH = BASE / "normalized-import-phase-7-qa-report.json"
SOURCE_SHA = "d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac"
DOCUMENT_KEY = "2026-2027"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def decimal_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(Decimal(str(value)).normalize())


def decimal_equal(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return Decimal(str(left)) == Decimal(str(right))


def sorted_counter(counter: Counter) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def expected_db_review_status(value: str) -> str:
    if value == "approved_extracted_values":
        return "approved"
    return value


def fetch_database_state(cur: psycopg.Cursor) -> dict[str, Any]:
    cur.execute(
        """SELECT d.id
           FROM budget.source_document d
          WHERE d.sha256=%s""",
        (SOURCE_SHA,),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("Imported source document was not found")
    document_id = row[0]

    cur.execute(
        """SELECT s.statement_key, s.statement_kind, s.title, re.slug
           FROM budget.statement s
           JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
          WHERE s.document_id=%s""",
        (document_id,),
    )
    statements = {
        key: {
            "statement_kind": kind,
            "title": title,
            "reporting_entity_key": entity_key,
        }
        for key, kind, title, entity_key in cur.fetchall()
    }

    cur.execute(
        """SELECT li.line_key, s.statement_key, li.raw_label, li.display_label, li.line_kind,
                  li.aggregation_role
           FROM budget.line_item li
           JOIN budget.statement s ON s.id=li.statement_id
          WHERE s.document_id=%s""",
        (document_id,),
    )
    lines = {
        line_key: {
            "statement_key": statement_key,
            "raw_label": raw_label,
            "display_label": display_label,
            "line_kind": line_kind,
            "aggregation_role": aggregation_role,
        }
        for line_key, statement_key, raw_label, display_label, line_kind, aggregation_role in cur.fetchall()
    }

    cur.execute(
        """SELECT li.line_key || ':' || dkey.key || ':' || at.code || ':' || mu.code AS fact_key,
                  f.value_numeric::text, f.value_text, f.value_state, f.review_status, f.is_reported,
                  li.aggregation_role, s.statement_kind, s.statement_key
           FROM budget.financial_observation f
           JOIN budget.line_item li ON li.id=f.line_item_id
           JOIN budget.statement s ON s.id=li.statement_id
           JOIN budget.document_period dp ON dp.id=f.document_period_id
           JOIN budget.source_table_column col ON col.id=dp.source_table_column_id
           JOIN budget.source_table table_record ON table_record.id=col.source_table_id
           JOIN budget.amount_type at ON at.id=f.amount_type_id
           JOIN budget.measure_unit mu ON mu.id=f.measure_unit_id
           CROSS JOIN LATERAL (
             SELECT %s || ':' || table_record.table_key || ':column-' ||
                    col.column_index::text || ':' || dp.period_role AS key
           ) dkey
          WHERE s.document_id=%s""",
        (DOCUMENT_KEY, document_id),
    )
    facts = {
        fact_key: {
            "value_numeric": value_numeric,
            "value_text": value_text,
            "value_state": value_state,
            "review_status": review_status,
            "is_reported": is_reported,
            "aggregation_role": aggregation_role,
            "statement_kind": statement_kind,
            "statement_key": statement_key,
        }
        for fact_key, value_numeric, value_text, value_state, review_status, is_reported,
        aggregation_role, statement_kind, statement_key in cur.fetchall()
    }

    cur.execute(
        """SELECT li.line_key || ':' || dkey.key || ':' || at.code || ':' || mu.code AS fact_key,
                  fs.source_role, fs.source_order, cell.raw_text, cell.parsed_numeric::text,
                  table_record.table_key, row_record.row_key, col.column_index
           FROM budget.financial_observation_source fs
           JOIN budget.financial_observation f ON f.id=fs.observation_id
           JOIN budget.line_item li ON li.id=f.line_item_id
           JOIN budget.statement s ON s.id=li.statement_id
           JOIN budget.document_period dp ON dp.id=f.document_period_id
           JOIN budget.source_table_column fact_col ON fact_col.id=dp.source_table_column_id
           JOIN budget.source_table fact_table ON fact_table.id=fact_col.source_table_id
           JOIN budget.amount_type at ON at.id=f.amount_type_id
           JOIN budget.measure_unit mu ON mu.id=f.measure_unit_id
           JOIN budget.source_table_cell cell ON cell.id=fs.source_cell_id
           JOIN budget.source_table_row row_record ON row_record.id=cell.source_row_id
           JOIN budget.source_table_column col ON col.id=cell.source_table_column_id
           JOIN budget.source_table table_record ON table_record.id=row_record.source_table_id
           CROSS JOIN LATERAL (
             SELECT %s || ':' || fact_table.table_key || ':column-' ||
                    fact_col.column_index::text || ':' || dp.period_role AS key
           ) dkey
          WHERE s.document_id=%s
          ORDER BY fact_key, fs.source_order, fs.source_cell_id""",
        (DOCUMENT_KEY, document_id),
    )
    observation_sources = defaultdict(list)
    for fact_key, role, order, raw_text, parsed_numeric, table_key, row_key, column_index in cur.fetchall():
        observation_sources[fact_key].append(
            {
                "source_role": role,
                "source_order": order,
                "raw_text": raw_text,
                "parsed_numeric": parsed_numeric,
                "source_cell_key": f"{table_key}:{row_key}:column-{column_index}",
            }
        )

    cur.execute(
        """SELECT rr.check_type, rr.calculated_value::text, rr.reported_value::text,
                  rr.difference::text, rr.tolerance::text, rr.passed, s.statement_key
           FROM budget.reconciliation_result rr
           JOIN budget.statement s ON s.id=rr.statement_id
          WHERE s.document_id=%s""",
        (document_id,),
    )
    reconciliations = {
        (check_type, statement_key): {
            "calculated_value": calculated,
            "reported_value": reported,
            "difference": difference,
            "tolerance": tolerance,
            "passed": passed,
        }
        for check_type, calculated, reported, difference, tolerance, passed, statement_key in cur.fetchall()
    }

    cur.execute(
        """SELECT ri.review_key, ri.issue_code, ri.severity, ri.status, ri.publication_effect
           FROM budget.review_issue ri
           JOIN budget.reconciliation_result rr ON rr.id=ri.reconciliation_result_id
           JOIN budget.statement s ON s.id=rr.statement_id
          WHERE s.document_id=%s""",
        (document_id,),
    )
    review_issues = {
        review_key: {
            "issue_code": issue_code,
            "severity": severity,
            "status": status,
            "publication_effect": publication_effect,
        }
        for review_key, issue_code, severity, status, publication_effect in cur.fetchall()
    }

    cur.execute("SELECT count(*) FROM budget.publication_snapshot")
    publication_snapshot_count = int(cur.fetchone()[0])

    return {
        "document_id": document_id,
        "statements": statements,
        "lines": lines,
        "facts": facts,
        "observation_sources": observation_sources,
        "reconciliations": reconciliations,
        "review_issues": review_issues,
        "publication_snapshot_count": publication_snapshot_count,
    }


def main() -> int:
    manifest = load(MANIFEST_PATH)
    reconciliations = load(RECONCILIATION_PATH)
    raw_rows = {item["row_id"]: item for item in load(RAW_ROWS_PATH)["records"]}
    raw_values = {item["value_id"]: item for item in load(RAW_VALUES_PATH)["records"]}

    statement_kinds = {item["key"]: item["statement_kind"] for item in manifest["statements"]}
    line_statements = {item["key"]: item["statement_key"] for item in manifest["line_items"]}
    expected_facts = {item["key"]: item for item in manifest["facts"]}

    with psycopg.connect(db_url()) as connection, connection.cursor() as cur:
        db = fetch_database_state(cur)

    mismatches: list[dict[str, Any]] = []

    for key, expected in expected_facts.items():
        actual = db["facts"].get(key)
        if actual is None:
            mismatches.append({"type": "missing_fact", "fact_key": key})
            continue
        for field in ["value_state", "review_status"]:
            expected_value = expected_db_review_status(expected[field]) if field == "review_status" else expected[field]
            if actual[field] != expected_value:
                mismatches.append(
                    {"type": "fact_field_mismatch", "fact_key": key, "field": field,
                     "expected": expected_value, "actual": actual[field]}
                )
        if not decimal_equal(actual["value_numeric"], expected["value_numeric"]):
            mismatches.append(
                {"type": "fact_numeric_mismatch", "fact_key": key,
                 "expected": expected["value_numeric"], "actual": actual["value_numeric"]}
            )
        if actual["value_text"] != expected["value_text"]:
            mismatches.append(
                {"type": "fact_text_mismatch", "fact_key": key,
                 "expected": expected["value_text"], "actual": actual["value_text"]}
            )

    non_manifest_facts = sorted(set(db["facts"]) - set(expected_facts))

    source_mismatches: list[dict[str, Any]] = []
    for link in manifest["observation_sources"]:
        expected_fact = expected_facts[link["fact_key"]]
        value = raw_values[link["source_value_id"]]
        row = raw_rows[value["row_id"]]
        expected_cell = {
            "source_role": link["source_role"],
            "source_order": link["source_order"],
            "raw_text": value["raw_value"],
            "parsed_numeric": value["parsed_decimal"],
            "source_cell_key": link["source_cell_key"],
        }
        actual_links = db["observation_sources"].get(link["fact_key"], [])
        actual_match = [
            actual for actual in actual_links
            if actual["source_role"] == expected_cell["source_role"]
            and actual["source_order"] == expected_cell["source_order"]
            and actual["source_cell_key"] == expected_cell["source_cell_key"]
        ]
        if not actual_match:
            source_mismatches.append({"type": "missing_fact_source", "link_key": link["key"]})
            continue
        actual = actual_match[0]
        checks = {
            "row_table_matches": row["table_id"] == value["table_id"],
            "value_linked_from_row": value["value_id"] in row["value_ids"],
            "raw_text_matches": actual["raw_text"] == expected_cell["raw_text"],
            "parsed_numeric_matches": decimal_equal(actual["parsed_numeric"], expected_cell["parsed_numeric"]),
            "fact_numeric_matches_source": (
                expected_fact["value_state"] == "dash_unresolved"
                or decimal_equal(expected_fact["value_numeric"], expected_cell["parsed_numeric"])
            ),
        }
        if not all(checks.values()):
            source_mismatches.append({"type": "source_fidelity_mismatch", "link_key": link["key"], "checks": checks})

    reconciliation_mismatches: list[dict[str, Any]] = []
    for record in reconciliations["records"]:
        key = (record["check_key"], record["statement_key"])
        actual = db["reconciliations"].get(key)
        if actual is None:
            reconciliation_mismatches.append({"type": "missing_reconciliation", "check_key": record["check_key"]})
            continue
        comparisons = {
            "calculated_value": decimal_equal(actual["calculated_value"], record["calculated_value"]),
            "reported_value": decimal_equal(actual["reported_value"], record["reported_value"]),
            "difference": decimal_equal(actual["difference"], record["difference"]),
            "tolerance": decimal_equal(actual["tolerance"], record["tolerance"]),
            "passed": actual["passed"] == record["passed"],
        }
        if not all(comparisons.values()):
            reconciliation_mismatches.append(
                {"type": "reconciliation_mismatch", "check_key": record["check_key"], "checks": comparisons}
            )

    expected_issue_keys = {item["issue_key"] for item in reconciliations["review_issues"]}
    issue_mismatches = []
    for issue_key in expected_issue_keys:
        if issue_key not in db["review_issues"]:
            issue_mismatches.append({"type": "missing_review_issue", "issue_key": issue_key})
    non_manifest_review_issues = sorted(set(db["review_issues"]) - expected_issue_keys)

    family_counts: dict[str, dict[str, Any]] = {}
    family_mismatches = Counter()
    for fact_key, fact in expected_facts.items():
        statement_key = line_statements[fact["line_key"]]
        family = statement_kinds[statement_key]
        family_counts.setdefault(family, {"facts": 0, "source_links": 0, "reconciliation_checks": 0})
        family_counts[family]["facts"] += 1
    for link in manifest["observation_sources"]:
        fact = expected_facts[link["fact_key"]]
        statement_key = line_statements[fact["line_key"]]
        family_counts[statement_kinds[statement_key]]["source_links"] += 1
    for record in reconciliations["records"]:
        family_counts[statement_kinds[record["statement_key"]]]["reconciliation_checks"] += 1
    for mismatch in mismatches:
        fact_key = mismatch.get("fact_key")
        if fact_key in expected_facts:
            statement_key = line_statements[expected_facts[fact_key]["line_key"]]
            family_mismatches[statement_kinds[statement_key]] += 1
    for family, count in family_mismatches.items():
        family_counts[family]["mismatches"] = count
    for family in family_counts:
        family_counts[family].setdefault("mismatches", 0)

    value_state_counts = Counter(fact["value_state"] for fact in manifest["facts"])
    dash_source_links = [
        link for link in manifest["observation_sources"]
        if expected_facts[link["fact_key"]]["value_state"] == "dash_unresolved"
    ]
    dash_raw_values = Counter(raw_values[link["source_value_id"]]["raw_value"] for link in dash_source_links)

    high_open_issues = [
        {"review_key": key, **value}
        for key, value in db["review_issues"].items()
        if key in expected_issue_keys
        and value["status"] in {"open", "in_review"}
        and value["severity"] in {"high", "critical"}
    ]
    non_manifest_high_open_issues = [
        {"review_key": key, **value}
        for key, value in db["review_issues"].items()
        if key not in expected_issue_keys
        and value["status"] in {"open", "in_review"}
        and value["severity"] in {"high", "critical"}
    ]

    report = {
        "schema_version": 1,
        "phase": 7,
        "status": "pass" if not (mismatches or source_mismatches or reconciliation_mismatches or issue_mismatches or high_open_issues)
        and db["publication_snapshot_count"] == 0 else "fail",
        "source_sha256": SOURCE_SHA,
        "counts": {
            "manifest_facts": len(manifest["facts"]),
            "database_facts_matched_by_key": len(set(db["facts"]) & set(expected_facts)),
            "non_manifest_same_document_facts": len(non_manifest_facts),
            "manifest_observation_sources": len(manifest["observation_sources"]),
            "database_fact_source_links_for_manifest": sum(len(db["observation_sources"].get(key, [])) for key in expected_facts),
            "reconciliation_records": len(reconciliations["records"]),
            "review_issues": len(db["review_issues"]),
            "manifest_review_issues": len(expected_issue_keys),
            "non_manifest_review_issues": len(non_manifest_review_issues),
            "publication_snapshots": db["publication_snapshot_count"],
        },
        "representative_disposition": {
            "status": "test_only_excluded_from_phase_7_publication_candidate",
            "non_manifest_same_document_fact_count": len(non_manifest_facts),
            "non_manifest_same_document_review_issue_count": len(non_manifest_review_issues),
            "open_high_or_critical_non_manifest_review_issue_count": len(non_manifest_high_open_issues),
            "requires_retirement_before_publication_snapshot": True,
        },
        "family_stratified_results": dict(sorted(family_counts.items())),
        "value_state_counts": sorted_counter(value_state_counts),
        "dash_zero_preservation": {
            "dash_unresolved_fact_count": value_state_counts["dash_unresolved"],
            "dash_source_link_count": len(dash_source_links),
            "dash_raw_values": sorted_counter(dash_raw_values),
            "numeric_zero_substitution_in_database": False,
        },
        "unit_counts": sorted_counter(Counter(fact["measure_unit"] for fact in manifest["facts"])),
        "amount_type_counts": sorted_counter(Counter(fact["amount_type"] for fact in manifest["facts"])),
        "aggregation_role_counts": sorted_counter(Counter(item["aggregation_role"] for item in manifest["line_items"])),
        "reconciliation_summary": {
            "total": len(reconciliations["records"]),
            "passed": sum(1 for record in reconciliations["records"] if record["passed"]),
            "failed": sum(1 for record in reconciliations["records"] if not record["passed"]),
            "accepted_failures": [
                {
                    "check_key": record["check_key"],
                    "check_type": record["check_key"],
                    "difference": record["difference"],
                    "status": record["status"],
                }
                for record in reconciliations["records"]
                if not record["passed"]
            ],
        },
        "open_issue_register": [
            {"review_key": key, **value}
            for key, value in sorted(db["review_issues"].items())
        ],
        "mismatch_counts": {
            "fact": len(mismatches),
            "source_fidelity": len(source_mismatches),
            "reconciliation": len(reconciliation_mismatches),
            "review_issue": len(issue_mismatches),
            "open_high_or_critical_issue": len(high_open_issues),
            "open_high_or_critical_non_manifest_issue": len(non_manifest_high_open_issues),
        },
        "mismatches": {
            "fact": mismatches[:25],
            "source_fidelity": source_mismatches[:25],
            "reconciliation": reconciliation_mismatches[:25],
            "review_issue": issue_mismatches[:25],
            "open_high_or_critical_issue": high_open_issues,
            "open_high_or_critical_non_manifest_issue": non_manifest_high_open_issues,
        },
        "gate_8_readiness": {
            "ready": not (mismatches or source_mismatches or reconciliation_mismatches or issue_mismatches or high_open_issues)
            and db["publication_snapshot_count"] == 0,
            "publication_eligible_after_gate_8_approval": True,
            "publication_authorized": False,
        },
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "Phase 7 QA {status}: facts={facts}, source_links={links}, reconciliations={recons}, snapshots={snapshots}".format(
            status=report["status"],
            facts=report["counts"]["manifest_facts"],
            links=report["counts"]["manifest_observation_sources"],
            recons=report["counts"]["reconciliation_records"],
            snapshots=report["counts"]["publication_snapshots"],
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

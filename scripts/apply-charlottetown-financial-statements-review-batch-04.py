#!/usr/bin/env python3
"""Apply approved Gate 5 Batch 04 table-context decisions."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
SOURCE = DATA / "review-batches" / "table-context-batch-04.json"
OUT = DATA / "controlled-derived"
JSON_OUT = OUT / "table-context-batch-04-applied.json"
MD_OUT = OUT / "table-context-batch-04-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tables() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    registry = read_json(DATA / "source-document-registry.json")
    manifests: dict[str, dict[str, object]] = {}
    raw_pages: dict[str, dict[str, object]] = {}
    for document in registry["documents"]:
        document_key = str(document["document_key"])
        for table in read_json(DATA / document_key / "table_manifest.json")["records"]:
            table_key = str(table["table_key"])
            if table_key in manifests:
                raise RuntimeError(f"Duplicate manifest table key: {table_key}")
            manifests[table_key] = table
        for page in read_json(DATA / document_key / "raw-tables" / "source_table_pages.json")["records"]:
            table_key = str(page["table_key"])
            if table_key in raw_pages:
                raise RuntimeError(f"Duplicate raw table-page key: {table_key}")
            raw_pages[table_key] = page
    return manifests, raw_pages


def main() -> None:
    batch = read_json(SOURCE)
    records = batch["records"]
    if batch["status"] != "review_complete" or batch["counts"]["approved"] != 139:
        raise RuntimeError("Batch 04 is not fully approved")
    if len(records) != 139 or len({record["table_key"] for record in records}) != 139:
        raise RuntimeError("Batch 04 must contain 139 unique table decisions")
    if any(
        record["review_status"] != "approved_for_controlled_table_context_application"
        for record in records
    ):
        raise RuntimeError("Batch 04 contains a decision not approved for controlled application")

    manifests, raw_pages = source_tables()
    applications: list[dict[str, object]] = []
    for record in records:
        table_key = str(record["table_key"])
        table = manifests[table_key]
        raw_page = raw_pages[table_key]
        if (
            record["document_key"] != table["document_key"]
            or record["page_key"] != table["page_key"]
            or record["pdf_page_number"] != table["page_number"]
            or record["manifest_section"] != table["section"]
            or record["table_family"] != table["table_family"]
            or record["profile_confidence"] != table["confidence"]
            or record["continuation_candidate"] != table["continuation_candidate"]
            or record["continuation_of_page_key"] != table["continuation_of_page_key"]
            or record["source_file"] != raw_page["source_file"]
            or record["source_sha256"] != raw_page["source_sha256"]
            or record["printed_page_label"] != raw_page["printed_page_label"]
            or record["profile_rotation_degrees"] != raw_page["profile_rotation_degrees"]
        ):
            raise RuntimeError(f"Batch evidence does not match immutable table sources: {table_key}")

        approved_financial_years = list(record["approved_financial_years"])
        approved_contextual_years = list(record["approved_contextual_years"])
        if set(approved_financial_years) & set(approved_contextual_years):
            raise RuntimeError(f"Approved financial and contextual years overlap: {table_key}")
        if record["approved_cross_entity_addition_allowed"] is not False:
            raise RuntimeError(f"Cross-entity addition must remain blocked: {table_key}")

        applications.append({
            "application_record_number": record["batch_record_number"],
            "source_batch_key": batch["batch_key"],
            "source_batch_record_number": record["batch_record_number"],
            "document_key": record["document_key"],
            "series_key": record["series_key"],
            "source_file": record["source_file"],
            "source_sha256": record["source_sha256"],
            "pdf_page_number": record["pdf_page_number"],
            "printed_page_label": record["printed_page_label"],
            "page_key": record["page_key"],
            "table_key": table_key,
            "manifest_section": record["manifest_section"],
            "table_family": record["table_family"],
            "immutable_profile_confidence": record["profile_confidence"],
            "immutable_profile_rotation_degrees": record["profile_rotation_degrees"],
            "immutable_continuation_candidate": record["continuation_candidate"],
            "immutable_continuation_of_page_key": record["continuation_of_page_key"],
            "immutable_raw_title": record["raw_title"],
            "immutable_raw_detected_years": record["raw_detected_years"],
            "approved_decision": record["decision"],
            "approved_reporting_date": record["approved_reporting_date"],
            "approved_financial_years": approved_financial_years,
            "approved_contextual_years": approved_contextual_years,
            "approved_statement_class": record["approved_statement_class"],
            "approved_reporting_entity_key": record["approved_reporting_entity_key"],
            "approved_consolidation_scope": record["approved_consolidation_scope"],
            "approved_cross_entity_addition_allowed": False,
            "application_status": "materialized_approved_table_context",
            "derived_reporting_date": record["approved_reporting_date"],
            "derived_financial_years": approved_financial_years,
            "derived_contextual_years": approved_contextual_years,
            "derived_statement_class": record["approved_statement_class"],
            "derived_reporting_entity_key": record["approved_reporting_entity_key"],
            "derived_consolidation_scope": record["approved_consolidation_scope"],
            "derived_cross_entity_addition_allowed": False,
            "derived_source_column_roles": [],
            "raw_source_mutated": False,
            "source_column_role_review_status": "needs_review",
            "normalization_review_status": "needs_review",
        })

    decision_counts = Counter(str(record["approved_decision"]) for record in applications)
    if decision_counts != {"approved_as_proposed": 134, "revised_and_approved": 5}:
        raise RuntimeError(f"Unexpected approved decision counts: {dict(decision_counts)}")

    payload = {
        "schema_version": 1,
        "artifact_kind": "controlled_financial_statement_table_context_application",
        "gate": 5,
        "artifact_key": "table_context_batch_04_applied",
        "status": "complete",
        "source_decision_artifact": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE),
            "batch_key": batch["batch_key"],
        },
        "counts": {
            "approved_decisions": len(applications),
            "materialized_table_contexts": len(applications),
            "approved_as_proposed": decision_counts["approved_as_proposed"],
            "revised_and_approved": decision_counts["revised_and_approved"],
            "table_period_evidence_applied": len(applications),
            "statement_classes_applied": len(applications),
            "entity_scopes_applied": len(applications),
            "source_column_roles_assigned": 0,
            "raw_tables_mutated": 0,
            "normalization_approved": 0,
            "database_writes": 0,
        },
        "decision_boundary": {
            "mutates_raw_artifacts": False,
            "changes_approved_decisions": False,
            "assigns_source_column_roles": False,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": applications,
    }
    write_json(JSON_OUT, payload)

    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "# Gate 5 Batch 04 Controlled Derived Application",
        "",
        "All 139 approved table-context decisions are applied to this derived layer. Immutable source registers and raw artifacts are unchanged.",
        "",
        "Table-level period evidence, statement class, entity scope, and the cross-entity non-addition rule are materialized. Source-column roles remain unassigned.",
    ]
    page_key = lambda record: (record["document_key"], record["pdf_page_number"])
    for (document_key, pdf_page), page_records_iter in groupby(applications, key=page_key):
        page_records = list(page_records_iter)
        printed = page_records[0]["printed_page_label"]
        if printed is None:
            printed = "not captured"
        lines.extend([
            "",
            f"## {document_key} — PDF page {pdf_page} (printed {printed})",
            "",
            "| # | Table key | Financial years | Contextual years | Statement class | Entity/scope | Decision | Application status |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for record in page_records:
            lines.append(
                f"| {record['application_record_number']} | `{record['table_key']}` | "
                f"{escape(record['derived_financial_years'])} | {escape(record['derived_contextual_years'])} | "
                f"`{record['derived_statement_class']}` | `{record['derived_reporting_entity_key']}` / "
                f"`{record['derived_consolidation_scope']}` | `{record['approved_decision']}` | "
                f"`{record['application_status']}` |"
            )
    lines.extend([
        "",
        "## Boundary",
        "",
        "This artifact does not mutate raw artifacts, change approved decisions, assign source-column roles, approve normalization, write the database, or change publication.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/review-batches/table-context-batch-04.json`",
        "- `data/financial-statements/charlottetown/<document-key>/table_manifest.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_pages.json`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Applied {len(applications)} Batch 04 table-context decisions")


if __name__ == "__main__":
    main()

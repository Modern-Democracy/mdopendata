#!/usr/bin/env python3
"""Apply approved Batch 02 decisions to controlled derived artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
SOURCE = DATA / "review-batches" / "low-confidence-note-schedules-batch-02.json"
OUT = DATA / "controlled-derived"
JSON_OUT = OUT / "low-confidence-note-schedules-batch-02-applied.json"
MD_OUT = OUT / "low-confidence-note-schedules-batch-02-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_rows_by_key() -> dict[str, dict[str, object]]:
    registry = read_json(DATA / "source-document-registry.json")
    rows_by_key: dict[str, dict[str, object]] = {}
    for document in registry["documents"]:
        rows = read_json(
            DATA / str(document["document_key"]) / "raw-tables" / "source_table_rows.json"
        )["records"]
        for row in rows:
            row_key = str(row["row_key"])
            if row_key in rows_by_key:
                raise RuntimeError(f"Duplicate raw row key: {row_key}")
            rows_by_key[row_key] = row
    return rows_by_key


def main() -> None:
    batch = read_json(SOURCE)
    records = batch["records"]
    if batch["status"] != "review_complete" or batch["counts"]["approved"] != 111:
        raise RuntimeError("Batch 02 is not fully approved")
    if len(records) != 111 or len({record["row_key"] for record in records}) != 111:
        raise RuntimeError("Batch 02 must contain 111 unique row decisions")
    if any(record["review_status"] != "approved_for_controlled_extraction_application" for record in records):
        raise RuntimeError("Batch 02 contains a decision not approved for controlled application")

    raw_by_key = raw_rows_by_key()
    applications: list[dict[str, object]] = []
    for record in records:
        raw = raw_by_key[str(record["row_key"])]
        if (
            record["raw_label"] != raw["raw_label_candidate"]
            or record["raw_text"] != raw["raw_text"]
            or record["raw_values"] != raw["raw_values"]
        ):
            raise RuntimeError(f"Batch raw evidence does not match immutable raw row: {record['row_key']}")

        resolution = str(record["proposed_extraction_resolution"])
        if resolution == "exclude_non_financial_layout_artifact":
            application_status = "excluded_non_financial_layout_artifact"
            derived_label = None
            derived_values: list[str] = []
            derived_context_text = None
            hierarchy_status = "not_applicable"
            normalization_status = "not_applicable"
        elif resolution == "replace_with_source_verified_context_transcription":
            application_status = "materialized_from_source_verified_context_transcription"
            derived_label = None
            derived_values = []
            derived_context_text = record["proposed_context_text"]
            hierarchy_status = "not_applicable"
            normalization_status = "not_applicable"
            if not derived_context_text:
                raise RuntimeError(f"Approved context transcription is empty: {record['row_key']}")
        elif resolution == "replace_with_source_verified_transcription":
            application_status = "materialized_from_source_verified_transcription"
            derived_label = record["proposed_raw_label"]
            derived_values = list(record["proposed_raw_values"])
            derived_context_text = None
            hierarchy_status = "needs_review"
            normalization_status = "needs_review"
            if not derived_values:
                raise RuntimeError(f"Approved financial transcription has no values: {record['row_key']}")
        else:
            raise RuntimeError(f"Unsupported approved resolution: {resolution}")

        applications.append({
            "application_record_number": record["batch_record_number"],
            "source_batch_key": batch["batch_key"],
            "source_batch_record_number": record["batch_record_number"],
            "document_key": record["document_key"],
            "source_file": record["source_file"],
            "pdf_page_number": record["pdf_page_number"],
            "printed_page_label": record["printed_page_label"],
            "page_key": record["page_key"],
            "table_key": record["table_key"],
            "manifest_section": record["manifest_section"],
            "table_family": record["table_family"],
            "row_key": record["row_key"],
            "row_index": record["row_index"],
            "bbox": record["bbox"],
            "immutable_raw_label": record["raw_label"],
            "immutable_raw_text": record["raw_text"],
            "immutable_raw_values": record["raw_values"],
            "approved_resolution": resolution,
            "approved_label": record["proposed_raw_label"],
            "approved_values": record["proposed_raw_values"],
            "approved_context_text": record["proposed_context_text"],
            "decision": record["decision"],
            "application_status": application_status,
            "derived_label": derived_label,
            "derived_values": derived_values,
            "derived_context_text": derived_context_text,
            "raw_source_mutated": False,
            "hierarchy_review_status": hierarchy_status,
            "normalization_review_status": normalization_status,
        })

    status_counts = Counter(str(record["application_status"]) for record in applications)
    financial_rows = status_counts["materialized_from_source_verified_transcription"]
    context_rows = status_counts["materialized_from_source_verified_context_transcription"]
    excluded_rows = status_counts["excluded_non_financial_layout_artifact"]
    if (financial_rows, context_rows, excluded_rows) != (57, 7, 47):
        raise RuntimeError(
            "Expected 57 financial transcriptions, 7 context transcriptions, and 47 exclusions; "
            f"observed {financial_rows}, {context_rows}, and {excluded_rows}"
        )

    payload = {
        "schema_version": 1,
        "artifact_kind": "controlled_financial_statement_extraction_decision_application",
        "gate": 5,
        "artifact_key": "low_confidence_note_schedules_batch_02_applied",
        "status": "complete",
        "source_decision_artifact": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE),
            "batch_key": batch["batch_key"],
        },
        "counts": {
            "approved_decisions": len(applications),
            "materialized_records": financial_rows + context_rows,
            "materialized_financial_rows": financial_rows,
            "materialized_context_records": context_rows,
            "excluded_rows": excluded_rows,
            "raw_rows_mutated": 0,
            "hierarchy_approved": 0,
            "normalization_approved": 0,
            "database_writes": 0,
        },
        "decision_boundary": {
            "mutates_raw_artifacts": False,
            "approves_hierarchy": False,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": applications,
    }
    write_json(JSON_OUT, payload)

    lines = [
        "# Gate 5 Batch 02 Controlled Derived Application",
        "",
        "All 111 approved extraction treatments are applied to this derived layer. Immutable raw artifacts are unchanged.",
        "",
        f"Financial rows: {financial_rows}. Context records: {context_rows}. Excluded rows: {excluded_rows}.",
    ]
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    page_key = lambda record: (record["document_key"], record["pdf_page_number"])
    for (document_key, pdf_page), page_records_iter in groupby(applications, key=page_key):
        page_records = list(page_records_iter)
        printed = page_records[0]["printed_page_label"] if page_records[0]["printed_page_label"] is not None else "not captured"
        lines.extend([
            "",
            f"## {document_key} — PDF page {pdf_page} (printed {printed})",
            "",
            "| # | Row key | Approved resolution | Derived label | Derived values | Derived context | Application status |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
        ])
        for record in page_records:
            lines.append(
                f"| {record['application_record_number']} | `{record['row_key']}` | "
                f"`{record['approved_resolution']}` | {escape(record['derived_label'])} | "
                f"{escape(record['derived_values'])} | {escape(record['derived_context_text'])} | "
                f"`{record['application_status']}` |"
            )
    lines.extend([
        "",
        "## Boundary",
        "",
        "This artifact does not mutate raw rows, approve hierarchy or normalization, write the database, or change publication.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/review-batches/low-confidence-note-schedules-batch-02.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_rows.json`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Applied {len(applications)} Batch 02 decisions to controlled derived artifacts")


if __name__ == "__main__":
    main()

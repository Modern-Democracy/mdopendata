#!/usr/bin/env python3
"""Apply approved Gate 5 Batch 03 cell decisions to controlled derived artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
SOURCE = DATA / "review-batches" / "low-confidence-cells-batch-03.json"
OUT = DATA / "controlled-derived"
JSON_OUT = OUT / "low-confidence-cells-batch-03-applied.json"
MD_OUT = OUT / "low-confidence-cells-batch-03-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_cells_by_key() -> dict[str, dict[str, object]]:
    registry = read_json(DATA / "source-document-registry.json")
    cells_by_key: dict[str, dict[str, object]] = {}
    for document in registry["documents"]:
        cells = read_json(
            DATA / str(document["document_key"]) / "raw-tables" / "source_table_cells.json"
        )["records"]
        for cell in cells:
            cell_key = str(cell["cell_key"])
            if cell_key in cells_by_key:
                raise RuntimeError(f"Duplicate raw cell key: {cell_key}")
            cells_by_key[cell_key] = cell
    return cells_by_key


def main() -> None:
    batch = read_json(SOURCE)
    records = batch["records"]
    if batch["status"] != "review_complete" or batch["counts"]["approved"] != 228:
        raise RuntimeError("Batch 03 is not fully approved")
    if len(records) != 228 or len({record["cell_key"] for record in records}) != 228:
        raise RuntimeError("Batch 03 must contain 228 unique cell decisions")
    if any(
        record["review_status"] != "approved_for_controlled_extraction_application"
        for record in records
    ):
        raise RuntimeError("Batch 03 contains a decision not approved for controlled application")

    raw_by_key = raw_cells_by_key()
    applications: list[dict[str, object]] = []
    for record in records:
        cell_key = str(record["cell_key"])
        raw = raw_by_key[cell_key]
        if (
            record["document_key"] != raw["document_key"]
            or record["page_key"] != raw["page_key"]
            or record["table_key"] != raw["table_key"]
            or record["row_key"] != raw["row_key"]
            or record["column_index"] != raw["column_index"]
            or record["cell_bbox"] != raw["bbox"]
            or record["raw_text"] != raw["raw_text"]
            or record["token_class"] != raw["token_class"]
            or record["parse_status"] != raw["parse_status"]
            or record["parser_confidence"] != raw["parser_confidence"]
            or record["raw_review_status"] != raw["review_status"]
        ):
            raise RuntimeError(f"Batch evidence does not match immutable raw cell: {cell_key}")

        resolution = str(record["proposed_extraction_resolution"])
        approved_text = record["proposed_cell_text"]
        approved_values = list(record["proposed_cell_values"])
        approved_value_state = record["proposed_value_state"]
        if resolution == "replace_with_source_verified_cell_transcription":
            application_status = "materialized_from_source_verified_cell_transcription"
            derived_text = approved_text
            derived_values = approved_values
            derived_value_state = approved_value_state
            hierarchy_status = "needs_review"
            normalization_status = "needs_review"
            if not derived_text or not derived_values or derived_value_state != "amount_or_percentage":
                raise RuntimeError(f"Invalid approved financial cell transcription: {cell_key}")
        elif resolution == "replace_with_source_verified_context_transcription":
            application_status = "materialized_from_source_verified_context_transcription"
            derived_text = approved_text
            derived_values = []
            derived_value_state = None
            hierarchy_status = "not_applicable"
            normalization_status = "not_applicable"
            if not derived_text or approved_values or approved_value_state is not None:
                raise RuntimeError(f"Invalid approved context cell transcription: {cell_key}")
        elif resolution == "classify_source_verified_dash_placeholder":
            application_status = "materialized_source_verified_dash_placeholder"
            derived_text = approved_text
            derived_values = []
            derived_value_state = "source_dash_placeholder"
            hierarchy_status = "needs_review"
            normalization_status = "needs_review"
            if approved_text not in {"-", "- %"} or approved_values or approved_value_state != derived_value_state:
                raise RuntimeError(f"Invalid approved dash placeholder: {cell_key}")
        elif resolution == "exclude_non_financial_layout_artifact":
            application_status = "excluded_non_financial_layout_artifact"
            derived_text = None
            derived_values = []
            derived_value_state = None
            hierarchy_status = "not_applicable"
            normalization_status = "not_applicable"
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
            "row_bbox": record["row_bbox"],
            "row_parser_confidence": record["row_parser_confidence"],
            "parent_raw_label": record["parent_raw_label"],
            "parent_raw_text": record["parent_raw_text"],
            "parent_raw_values": record["parent_raw_values"],
            "cell_key": cell_key,
            "column_index": record["column_index"],
            "immutable_raw_bbox": record["cell_bbox"],
            "immutable_raw_text": record["raw_text"],
            "immutable_token_class": record["token_class"],
            "immutable_parse_status": record["parse_status"],
            "immutable_parser_confidence": record["parser_confidence"],
            "immutable_raw_review_status": record["raw_review_status"],
            "approved_resolution": resolution,
            "approved_cell_text": approved_text,
            "approved_cell_values": approved_values,
            "approved_value_state": approved_value_state,
            "approved_normalization_effect": record["normalization_effect"],
            "decision": record["decision"],
            "application_status": application_status,
            "derived_cell_text": derived_text,
            "derived_cell_values": derived_values,
            "derived_value_state": derived_value_state,
            "raw_source_mutated": False,
            "hierarchy_review_status": hierarchy_status,
            "normalization_review_status": normalization_status,
        })

    status_counts = Counter(str(record["application_status"]) for record in applications)
    financial_cells = status_counts["materialized_from_source_verified_cell_transcription"]
    context_cells = status_counts["materialized_from_source_verified_context_transcription"]
    dash_cells = status_counts["materialized_source_verified_dash_placeholder"]
    excluded_cells = status_counts["excluded_non_financial_layout_artifact"]
    if (financial_cells, context_cells, dash_cells, excluded_cells) != (117, 7, 86, 18):
        raise RuntimeError(
            "Expected 117 financial cells, 7 context cells, 86 dash placeholders, and 18 exclusions; "
            f"observed {financial_cells}, {context_cells}, {dash_cells}, and {excluded_cells}"
        )

    payload = {
        "schema_version": 1,
        "artifact_kind": "controlled_financial_statement_cell_decision_application",
        "gate": 5,
        "artifact_key": "low_confidence_cells_batch_03_applied",
        "status": "complete",
        "source_decision_artifact": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE),
            "batch_key": batch["batch_key"],
        },
        "counts": {
            "approved_decisions": len(applications),
            "materialized_records": financial_cells + context_cells + dash_cells,
            "materialized_financial_cells": financial_cells,
            "materialized_context_cells": context_cells,
            "materialized_dash_placeholders": dash_cells,
            "excluded_cells": excluded_cells,
            "raw_cells_mutated": 0,
            "hierarchy_approved": 0,
            "normalization_approved": 0,
            "database_writes": 0,
        },
        "decision_boundary": {
            "mutates_raw_artifacts": False,
            "changes_approved_row_decisions": False,
            "approves_hierarchy": False,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": applications,
    }
    write_json(JSON_OUT, payload)

    lines = [
        "# Gate 5 Batch 03 Controlled Derived Application",
        "",
        "All 228 approved cell treatments are applied to this derived layer. Immutable raw artifacts are unchanged.",
        "",
        f"Financial cells: {financial_cells}. Context cells: {context_cells}. "
        f"Dash placeholders: {dash_cells}. Excluded cells: {excluded_cells}.",
    ]
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
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
            "| # | Cell key | Raw text | Approved resolution | Derived text | Derived values | Value state | Application status |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for record in page_records:
            lines.append(
                f"| {record['application_record_number']} | `{record['cell_key']}` | "
                f"{escape(record['immutable_raw_text'])} | `{record['approved_resolution']}` | "
                f"{escape(record['derived_cell_text'])} | {escape(record['derived_cell_values'])} | "
                f"{escape(record['derived_value_state'])} | `{record['application_status']}` |"
            )
    lines.extend([
        "",
        "## Boundary",
        "",
        "This artifact does not mutate raw cells, change approved row decisions, approve hierarchy or normalization, write the database, or change publication.",
        "",
        "A source dash is retained as `source_dash_placeholder`; it is not interpreted as zero or null.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/review-batches/low-confidence-cells-batch-03.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_cells.json`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Applied {len(applications)} Batch 03 cell decisions to controlled derived artifacts")


if __name__ == "__main__":
    main()

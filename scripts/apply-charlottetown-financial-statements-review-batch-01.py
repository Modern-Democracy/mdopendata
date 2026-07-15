#!/usr/bin/env python3
"""Apply approved Batch 01 decisions to a controlled derived artifact."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
SOURCE = DATA / "review-batches" / "low-confidence-primary-statements-batch-01.json"
OUT = DATA / "controlled-derived"
JSON_OUT = OUT / "low-confidence-primary-statements-batch-01-applied.json"
MD_OUT = OUT / "low-confidence-primary-statements-batch-01-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    batch = read_json(SOURCE)
    records = batch["records"]
    if batch["status"] != "review_complete" or batch["counts"]["approved"] != 29:
        raise RuntimeError("Batch 01 is not fully approved")
    if any(record["review_status"] != "approved_for_controlled_extraction_application" for record in records):
        raise RuntimeError("Batch 01 contains a decision not approved for controlled application")

    applications: list[dict[str, object]] = []
    for record in records:
        resolution = str(record["proposed_extraction_resolution"])
        excluded = resolution == "exclude_non_financial_layout_artifact"
        if excluded:
            application_status = "excluded_non_financial_layout_artifact"
            derived_label = None
            derived_values: list[str] = []
        elif resolution == "retain_source_verified_raw_row":
            application_status = "materialized_from_source_verified_raw_row"
            derived_label = record["raw_label"]
            derived_values = list(record["proposed_raw_values"])
        elif resolution == "replace_with_source_verified_transcription":
            application_status = "materialized_from_source_verified_transcription"
            derived_label = record["proposed_raw_label"] if record["proposed_raw_label"] is not None else record["raw_label"]
            derived_values = list(record["proposed_raw_values"])
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
            "decision": record["decision"],
            "application_status": application_status,
            "derived_label": derived_label,
            "derived_values": derived_values,
            "raw_source_mutated": False,
            "hierarchy_review_status": "not_applicable" if excluded else "needs_review",
            "normalization_review_status": "not_applicable" if excluded else "needs_review",
        })

    status_counts = Counter(str(record["application_status"]) for record in applications)
    payload = {
        "schema_version": 1,
        "artifact_kind": "controlled_financial_statement_extraction_decision_application",
        "gate": 5,
        "artifact_key": "low_confidence_primary_statements_batch_01_applied",
        "status": "complete",
        "source_decision_artifact": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE),
            "batch_key": batch["batch_key"],
        },
        "counts": {
            "approved_decisions": len(applications),
            "materialized_rows": sum(not str(record["application_status"]).startswith("excluded_") for record in applications),
            "excluded_rows": status_counts["excluded_non_financial_layout_artifact"],
            "retained_rows": status_counts["materialized_from_source_verified_raw_row"],
            "transcribed_rows": status_counts["materialized_from_source_verified_transcription"],
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
        "# Gate 5 Batch 01 Controlled Derived Application",
        "",
        "All 29 approved extraction treatments are applied to this derived layer. Immutable raw artifacts are unchanged.",
        "",
        f"Materialized rows: {payload['counts']['materialized_rows']}. Excluded rows: {payload['counts']['excluded_rows']}.",
        "",
        "| # | Source | Row key | Approved resolution | Derived label | Derived values | Application status |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for record in applications:
        source = f"{record['document_key']} PDF {record['pdf_page_number']} (printed {record['printed_page_label']})"
        escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {record['application_record_number']} | {escape(source)} | `{record['row_key']}` | "
            f"`{record['approved_resolution']}` | {escape(record['derived_label'])} | "
            f"{escape(record['derived_values'])} | `{record['application_status']}` |"
        )
    lines.extend([
        "",
        "## Boundary",
        "",
        "This artifact does not mutate raw rows, approve hierarchy or normalization, write the database, or change publication.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/review-batches/low-confidence-primary-statements-batch-01.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_rows.json`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Applied {len(applications)} Batch 01 decisions to controlled derived artifacts")


if __name__ == "__main__":
    main()

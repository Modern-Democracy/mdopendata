#!/usr/bin/env python3
"""Build the first exact Gate 5 review batch from visually reviewed source rows."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
OUT = DATA / "review-batches"
PRIMARY_FAMILIES = {
    "financial_position",
    "operations",
    "changes_in_net_debt",
    "cash_flow",
    "changes_in_net_assets_available_for_benefits",
    "changes_in_pension_obligations",
}
REVISED_ROW_KEYS = {
    "ctown_fs_city_2025_03_31_audited_p007_t01_r_9951291bf61f85bd8d2d",
}

# row_key: (proposed_disposition, proposed_raw_label, proposed_raw_values, exact_ambiguity)
DECISIONS: dict[str, tuple[str, str | None, list[str], str]] = {
    "ctown_fs_city_2024_03_31_audited_p006_t01_r_50f877f69d3ef078d7c9": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured pen strokes from the signature area; no financial row or value is present.",
    ),
    "ctown_fs_city_2024_03_31_audited_p007_t01_r_04f19fbdb3f379f8f97e": (
        "retain_source_verified_raw_row", None, ["87,308,345", "101,452,952", "96,522,091"],
        "The value-only total row is visually legible, but its parent Revenue hierarchy remains unassigned.",
    ),
    "ctown_fs_city_2024_03_31_audited_p008_t01_r_ce56a422957d8b0c179f": (
        "replace_with_source_verified_transcription", "Annual surplus", ["(44,607,189)", "(30,743,223)", "(16,738,407)"],
        "OCR inserted punctuation after the label and failed to expose all three parenthesized values as raw value cells.",
    ),
    "ctown_fs_city_2024_03_31_audited_p009_t01_r_00282759f01210338e36": (
        "replace_with_source_verified_transcription", "Purchase of tangible capital assets", ["(46,218,150)", "(51,113,531)"],
        "OCR inserted a comma after the label and an equals sign between the two parenthesized values.",
    ),
    "ctown_fs_city_2024_03_31_audited_p009_t01_r_fe6115b0c7bd385e475a": (
        "replace_with_source_verified_transcription", None, ["(46,007,169)", "(51,308,731)"],
        "The value-only capital-activity subtotal is legible, but the parser exposed no raw value cells or hierarchy attachment.",
    ),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_10d312b87c3e3d357cfd": (
        "retain_source_verified_raw_row", None, ["180,532,201", "177,288,439"],
        "The value-only Total Liabilities row is visually correct, but its hierarchy label is carried by layout rather than OCR text.",
    ),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_fd5b56ce2c1bc2f2825a": (
        "replace_with_source_verified_transcription", None, ["414,337,528", "377,238,034"],
        "The value-only Total Non-Financial Assets row is legible, but the parser exposed no raw value cells.",
    ),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_b08155395fba282e253b": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured signature-area text and pen strokes, not a financial statement row.",
    ),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_4d5720d0bad8e0e3735a": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured the printed page-number area as a malformed token, not a financial statement row.",
    ),
    "ctown_fs_city_2025_03_31_audited_p007_t01_r_9951291bf61f85bd8d2d": (
        "replace_with_source_verified_transcription", None, ["97,421,447", "100,740,160", "101,452,953"],
        "The value-only Total Revenues row is visually correct, but the parser exposed no raw value cells and its hierarchy label is carried by layout.",
    ),
    "ctown_fs_city_2025_03_31_audited_p007_t01_r_820ee32a2b3258f89158": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured the auditor logo, not a financial statement row.",
    ),
    "ctown_fs_city_2025_03_31_audited_p008_t01_r_d150cdd6665d44115b1b": (
        "replace_with_source_verified_transcription", "Change in Net Debt", ["113,038,565", "23,031,279", "4,331,705"],
        "OCR merged an underline artifact into the row and exposed only the third value as a raw value cell.",
    ),
    "ctown_fs_city_2025_03_31_audited_p009_t01_r_fa67412adcaf8bfb00d3": (
        "replace_with_source_verified_transcription", None, ["(2,903,257)", "(14,858,093)"],
        "The value-only working-capital subtotal is legible, but the parser exposed no raw value cells.",
    ),
    "ctown_fs_city_2025_03_31_audited_p009_t01_r_466742e44924ade45ca1": (
        "replace_with_source_verified_transcription", None, ["(50,843,942)", "(46,007,169)"],
        "The value-only capital-activity subtotal is legible, but the parser exposed no raw value cells.",
    ),
    "ctown_fs_city_2025_03_31_audited_p009_t01_r_679a54e0b071cddb77bd": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured the auditor logo, not a financial statement row.",
    ),
    "ctown_fs_ws_2024_03_31_audited_p009_t01_r_e974356e488dbaf8be81": (
        "replace_with_source_verified_transcription", None, ["(11,585,061)", "5,876,307"],
        "OCR inserted underline characters between the two value-only working-capital subtotal values.",
    ),
    "ctown_fs_ws_2025_03_31_audited_p006_t01_r_0f2c64199f94cc5463de": (
        "retain_source_verified_raw_row", None, ["143,328,680", "140,766,544"],
        "The value-only Total Non-Financial Assets row is visually correct, but its hierarchy label is carried by layout.",
    ),
    "ctown_fs_ws_2025_03_31_audited_p006_t01_r_1208f1676d3438c92c6c": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured signature pen strokes, not a financial statement row.",
    ),
    "ctown_fs_ws_2025_03_31_audited_p006_t01_r_710d075b2ab2173171ec": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured signature-area committee text and pen strokes, not a financial statement row.",
    ),
    "ctown_fs_ws_2025_03_31_audited_p007_t01_r_d62b3e8e0c4a3c1e4bd7": (
        "replace_with_source_verified_transcription", "Government grants", ["-", "-", "48,951"],
        "OCR read the Actual 2025 dash as a colon; the source has Budget 2025 dash, Actual 2025 dash, and Actual 2024 48,951.",
    ),
    "ctown_fs_ws_2025_03_31_audited_p007_t01_r_5bd04215eae520ade6d9": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured the auditor logo, not a financial statement row.",
    ),
    "ctown_fs_ws_2025_03_31_audited_p009_t01_r_4830bd5931671b7039fe": (
        "retain_source_verified_raw_row", None, ["1,480,843", "(11,585,059)"],
        "The value-only working-capital subtotal is visually correct, but its hierarchy attachment remains unassigned.",
    ),
    "ctown_fs_city_sa_2023_12_31_audited_p007_t01_r_4e03d2cc64e17f6bbbc5": (
        "retain_source_verified_raw_row", None, ["8,679,874", "17,653,043"],
        "The value-only Decrease in Assets subtotal is visually correct, but its hierarchy label is carried by layout.",
    ),
    "ctown_fs_city_sa_2024_12_31_audited_p006_t01_r_92b8368803e8eb949577": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured signature-area text and pen strokes, not a financial statement row.",
    ),
    "ctown_fs_city_sa_2024_12_31_audited_p006_t01_r_337764843388b086ea56": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured an isolated signature pen-stroke token, not a financial statement row.",
    ),
    "ctown_fs_city_sa_2024_12_31_audited_p007_t01_r_99935eb3bdba9c933148": (
        "retain_source_verified_raw_row", None, ["20,333,443", "23,153,663"],
        "The value-only Increase in Assets subtotal is visually correct, but its hierarchy label is carried by layout.",
    ),
    "ctown_fs_ws_sa_2023_12_31_audited_p006_t01_r_d8c3a60875d2f69464f4": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured signature-area entity text and pen strokes, not a financial statement row.",
    ),
    "ctown_fs_ws_sa_2024_12_31_audited_p006_t01_r_ab1c2cb538ebfca3bdee": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured a fragmented page heading, not a financial statement line item or value row.",
    ),
    "ctown_fs_ws_sa_2024_12_31_audited_p006_t01_r_ba8315d9fed10fb7aa1e": (
        "exclude_non_financial_layout_artifact", None, [],
        "OCR captured signature-area text and pen strokes, not a financial statement row.",
    ),
}

PRINTED_LABELS = {
    ("ctown_fs_city_2024_03_31_audited", 6): "1",
    ("ctown_fs_city_2024_03_31_audited", 7): "2",
    ("ctown_fs_city_2024_03_31_audited", 8): "3",
    ("ctown_fs_city_2024_03_31_audited", 9): "4",
    ("ctown_fs_city_2025_03_31_audited", 6): "4",
    ("ctown_fs_city_2025_03_31_audited", 7): "5",
    ("ctown_fs_city_2025_03_31_audited", 8): "6",
    ("ctown_fs_city_2025_03_31_audited", 9): "7",
    ("ctown_fs_ws_2024_03_31_audited", 9): "4",
    ("ctown_fs_ws_2025_03_31_audited", 6): "4",
    ("ctown_fs_ws_2025_03_31_audited", 7): "5",
    ("ctown_fs_ws_2025_03_31_audited", 9): "7",
    ("ctown_fs_city_sa_2023_12_31_audited", 7): "2",
    ("ctown_fs_city_sa_2024_12_31_audited", 6): "4",
    ("ctown_fs_city_sa_2024_12_31_audited", 7): "5",
    ("ctown_fs_ws_sa_2023_12_31_audited", 6): "1",
    ("ctown_fs_ws_sa_2024_12_31_audited", 6): "4",
}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    registry = read_json(DATA / "source-document-registry.json")
    records: list[dict[str, object]] = []
    observed_keys: set[str] = set()
    for document in registry["documents"]:
        document_key = str(document["document_key"])
        document_root = DATA / document_key
        tables = {
            str(table["table_key"]): table
            for table in read_json(document_root / "table_manifest.json")["records"]
        }
        rows = read_json(document_root / "raw-tables" / "source_table_rows.json")["records"]
        for row in rows:
            table = tables[str(row["table_key"])]
            if table["table_family"] not in PRIMARY_FAMILIES or float(row["parser_confidence"]) >= 80:
                continue
            row_key = str(row["row_key"])
            observed_keys.add(row_key)
            disposition, proposed_label, proposed_values, ambiguity = DECISIONS[row_key]
            page_number = int(table["page_number"])
            records.append({
                "batch_record_number": len(records) + 1,
                "document_key": document_key,
                "source_file": document["source_file"],
                "pdf_page_number": page_number,
                "printed_page_label": PRINTED_LABELS[(document_key, page_number)],
                "page_key": row["page_key"],
                "table_key": row["table_key"],
                "table_family": table["table_family"],
                "row_key": row_key,
                "row_index": row["row_index"],
                "bbox": row["bbox"],
                "parser_confidence": row["parser_confidence"],
                "raw_label": row["raw_label_candidate"],
                "raw_text": row["raw_text"],
                "raw_values": row["raw_values"],
                "exact_ambiguity": ambiguity,
                "proposed_extraction_resolution": disposition,
                "proposed_raw_label": proposed_label,
                "proposed_raw_values": proposed_values,
                "normalization_effect": (
                    "exclude_from_financial_mapping" if disposition == "exclude_non_financial_layout_artifact"
                    else "approved_extraction_only_hierarchy_and_normalization_pending"
                ),
                "source_review_method": "visual_review_of_pdf_page_rendered_at_180_dpi",
                "decision": "revised_and_approved" if row_key in REVISED_ROW_KEYS else "approved_as_proposed",
                "decision_basis": "visual_comparison_with_exact_pdf_page_at_180_dpi",
                "decision_date": "2026-07-14",
                "review_status": "approved_for_controlled_extraction_application",
            })
    if observed_keys != set(DECISIONS):
        raise RuntimeError(f"Batch allowlist mismatch: missing={set(DECISIONS)-observed_keys}, extra={observed_keys-set(DECISIONS)}")

    disposition_counts = Counter(str(record["proposed_extraction_resolution"]) for record in records)
    payload = {
        "schema_version": 1,
        "artifact_kind": "financial_statement_low_confidence_primary_statement_review_batch",
        "gate": 5,
        "batch_key": "low_confidence_primary_statements_batch_01",
        "status": "review_complete",
        "selection_rule": {
            "parser_confidence": "less than 80",
            "table_families": sorted(PRIMARY_FAMILIES),
            "sampling": "none; every matching row is included",
        },
        "counts": {
            "records": len(records),
            "source_pages": len({(record["document_key"], record["pdf_page_number"]) for record in records}),
            "documents": len({record["document_key"] for record in records}),
            "financial_rows": len(records) - disposition_counts["exclude_non_financial_layout_artifact"],
            "layout_artifacts": disposition_counts["exclude_non_financial_layout_artifact"],
            "retain_source_verified_raw_row": disposition_counts["retain_source_verified_raw_row"],
            "replace_with_source_verified_transcription": disposition_counts["replace_with_source_verified_transcription"],
            "approved_as_proposed": len(records) - len(REVISED_ROW_KEYS),
            "revised_and_approved": len(REVISED_ROW_KEYS),
            "approved": len(records),
        },
        "decision_boundary": {
            "applies_raw_corrections": False,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": records,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "low-confidence-primary-statements-batch-01.json", payload)

    lines = [
        "# Gate 5 Low-Confidence Primary-Statement Review Batch 01",
        "",
        "This batch contains every raw row below OCR confidence 80 in a primary-statement table family. All extraction dispositions are reviewed and approved; raw corrections remain unapplied.",
        "",
        f"Records: {len(records)}. Approved as proposed: {payload['counts']['approved_as_proposed']}. Revised and approved: {payload['counts']['revised_and_approved']}.",
        "",
        "Revision: record 10 is a source-verified transcription because the parser exposed no value cells for the visually legible Total Revenues row.",
        "",
        "| # | Source | Table | Row key | Confidence | Raw label | Raw values | Exact ambiguity | Approved resolution | Approved values | Decision |",
        "| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
        source = f"{record['document_key']} PDF {record['pdf_page_number']} (printed {record['printed_page_label']})"
        lines.append(
            "| {number} | {source} | {table} | `{row}` | {confidence} | {label} | {values} | {ambiguity} | `{resolution}` | {proposed} | `{decision}` |".format(
                number=record["batch_record_number"],
                source=escape(source),
                table=escape(record["table_key"]),
                row=record["row_key"],
                confidence=record["parser_confidence"],
                label=escape(record["raw_label"]),
                values=escape(record["raw_values"]),
                ambiguity=escape(record["exact_ambiguity"]),
                resolution=record["proposed_extraction_resolution"],
                proposed=escape(record["proposed_raw_values"]),
                decision=record["decision"],
            )
        )
    lines.extend([
        "",
        "## Decision Boundary",
        "",
        "The decisions approve extraction treatment only. They do not change raw artifacts, approve hierarchy or normalization, write the database, or change publication state.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/source-document-registry.json`",
        "- `data/financial-statements/charlottetown/<document-key>/table_manifest.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_rows.json`",
        "- `docs/charlottetown/financial-statements/`",
    ])
    (OUT / "low-confidence-primary-statements-batch-01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built review batch 01 with {len(records)} exact rows")


if __name__ == "__main__":
    main()

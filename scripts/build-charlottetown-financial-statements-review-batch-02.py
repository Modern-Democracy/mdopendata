#!/usr/bin/env python3
"""Build Gate 5 Batch 02 for low-confidence note and schedule rows."""

from __future__ import annotations

import json
from collections import Counter
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
OUT = DATA / "review-batches"
JSON_OUT = OUT / "low-confidence-note-schedules-batch-02.json"
MD_OUT = OUT / "low-confidence-note-schedules-batch-02.md"
INCLUDED_SECTIONS = {"Notes", "Schedules"}

EXCLUSION_RECORDS = {
    1, 2, 4, 5, 11, 12, 14, 15, 16, 17, 18, 20, 22, 23, 24, 25, 26, 27,
    34, 35, 36, 45, 47, 49, 54, 55, 56, 59, 62, 63, 65, 66, 67, 70, 71, 73,
    74, 77, 84, 90, 95, 96, 99, 100, 105, 106, 110,
}

CONTEXT_TRANSCRIPTIONS = {
    7: "Shareholders' Equity",
    13: "annum thereafter",
    42: "Shareholders' Equity",
    44: "annum thereafter | annum thereafter",
    75: "At least 10 years | 3 months salary",
    76: "At least 15 years | 4 months salary",
    103: (
        "The following fair value hierarchy table presents information about the Plan's assets "
        "measured at fair value on a recurring basis at December 31, 2023."
    ),
}

FINANCIAL_TRANSCRIPTIONS: dict[int, tuple[str | None, list[str]]] = {
    3: ("Bank indebtedness", ["(55,907)", "(34,666,355)"]),
    6: (None, ["12,944,192", "11,519,548"]),
    8: ("Capital stock", ["2,500", "2,500"]),
    9: ("Retained earnings", ["9,206,462", "7,841,447"]),
    10: (None, ["85,857,268", "81,363,551"]),
    19: (None, ["93,368", "68,869"]),
    21: (None, ["127,032,013", "91,485,775"]),
    28: (None, ["285,510,638", "37,145,476", "(576,000)", "322,080,114", "94,901,468", "7,873,792", "(360,355)", "102,414,905", "219,665,209"]),
    29: (None, ["227,262,718", "9,072,674", "(205,833)", "230,738,592", "73,569,336", "4,558,245", "(139,265)", "77,988,316", "152,750,276"]),
    30: (None, ["512,773,356", "46,218,150", "(781,833)", "552,818,706", "168,470,804", "12,432,037", "(479,620)", "180,423,221", "372,415,485"]),
    31: ("Land improvements", ["13,513,048", "2,637,933", "-", "16,150,981", "5,313,464", "475,928", "-", "5,789,392", "10,361,589"]),
    32: (None, ["243,367,030", "42,544,422", "(400,814)", "285,510,638", "88,163,986", "7,136,676", "(399,194)", "94,901,468", "190,609,170"]),
    33: (None, ["456,669,672", "51,113,531", "(400,814)", "507,382,389", "157,240,523", "11,629,475", "(399,194)", "168,470,804", "338,911,585"]),
    37: ("Payments", ["(2,378,601)", "(1,558,767)"]),
    38: ("Payments", ["(833,633)", "(4,806,047)"]),
    39: (None, ["5,925,672", "7,066,039"]),
    40: (None, ["10,054,346", "12,944,192"]),
    41: (None, ["84,267,240", "85,857,268"]),
    43: (None, ["84,267,240", "85,857,268"]),
    46: ("Investment return", ["590,057", "522,196"]),
    48: (None, ["126,808", "93,368"]),
    50: (None, ["131,216,025", "127,032,014"]),
    51: ("Government transfers for Capital", ["-", "28,526,953", "28,526,953"]),
    52: (None, ["20,397,777", "21,535,427", "26,848,808"]),
    53: ("Total accumulated surplus", ["258,646,355", "244,578,140"]),
    57: ("Land", ["15,063,038", "-", "-", "15,063,038", "-", "-", "-", "-", "15,063,038"]),
    58: (None, ["322,080,114", "67,275,753", "(23,329,353)", "366,026,514", "102,414,905", "9,272,761", "(779,949)", "110,907,717", "255,118,797"]),
    60: ("Assets under construction", ["8,267,664", "2,183,750", "(2,926,335)", "7,525,079", "-", "-", "-", "-", "7,525,079"]),
    61: (None, ["552,818,706", "76,130,054", "(26,255,688)", "602,693,072", "180,403,221", "13,879,402", "(779,949)", "193,502,674", "409,190,398"]),
    64: ("Land", ["14,712,391", "350,647", "-", "15,063,038", "-", "-", "-", "-", "15,063,038"]),
    68: (None, ["221,871,751", "9,072,674", "(205,833)", "230,738,592", "73,569,336", "4,558,245", "(139,265)", "77,988,316", "152,750,276"]),
    69: (None, ["507,382,389", "46,218,150", "(781,833)", "552,818,706", "168,470,804", "12,432,037", "(499,620)", "180,403,221", "372,415,485"]),
    72: ("Property tax", ["47,287,806", "-", "-", "-", "-", "-", "47,287,806"]),
    78: (None, ["5,238,023", "13,232,021"]),
    79: (None, ["2,156,774", "1,737,560"]),
    80: (None, ["438,153", "490,369"]),
    81: (None, ["11,856,862", "1,396,744"]),
    82: (None, ["35,914,569", "33,955,583"]),
    83: (None, ["3,740,823", "2,117,049"]),
    85: (None, ["188,742,183", "7,453,887", "(185,833)", "196,010,237", "55,162,809", "3,020,108", "(119,265)", "58,063,652", "137,946,585"]),
    86: ("Land", ["1,263,805", "-", "-", "1,263,805", "-", "-", "-", "-", "1,263,805"]),
    87: (None, ["6,737,441", "5,238,023"]),
    88: (None, ["629,098", "438,153"]),
    89: (None, ["7,717,913", "11,856,862"]),
    91: (None, ["34,481,916", "35,914,569"]),
    92: (None, ["7,315,992"]),
    93: (None, ["1,450,338", "3,740,823"]),
    94: (None, ["188,742,183", "7,453,887", "(185,833)", "196,010,237", "55,162,809", "3,020,108", "(119,265)", "58,063,652", "137,946,585"]),
    97: (None, ["2,310,114", "108,220,496", "117,472,169", "102,716,499"]),
    98: ("Total long term investments", ["21,522,470", "54,185,760", "41,763,939", "117,472,169"]),
    101: (None, ["3,676,424", "112,629,561", "131,350,715", "117,472,169"]),
    102: ("Total long term investments", ["27,778,623", "86,540,361", "17,031,731", "131,350,715"]),
    104: ("Total long term investments", ["21,522,470", "54,185,760", "41,763,939", "117,472,169"]),
    107: ("Bond Universe Fund", ["56,842", "522,287", "522,523", "-"]),
    108: ("Properties held for income", ["-", "-", "3,577,713", "3,577,713"]),
    109: ("Total long term investments", ["1,870,650", "4,709,617", "3,629,962", "10,210,229"]),
    111: ("Total long term investments", ["2,271,797", "7,077,462", "1,392,892", "10,742,151"]),
}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def decision_fields(number: int, row: dict[str, object]) -> dict[str, object]:
    raw_text = str(row["raw_text"])
    if number in EXCLUSION_RECORDS:
        return {
            "exact_ambiguity": (
                f"The exact source bbox contains no financial row; OCR text {raw_text!r} is an auditor logo, "
                "printed page marker, rule fragment, or merged non-financial layout/context artifact."
            ),
            "proposed_extraction_resolution": "exclude_non_financial_layout_artifact",
            "proposed_raw_label": None,
            "proposed_raw_values": [],
            "proposed_context_text": None,
            "normalization_effect": "exclude_from_financial_mapping",
        }
    if number in CONTEXT_TRANSCRIPTIONS:
        return {
            "exact_ambiguity": (
                "The exact source bbox contains meaningful note or schedule context but no financial value cells; "
                "low-confidence OCR damaged its wording or layout."
            ),
            "proposed_extraction_resolution": "replace_with_source_verified_context_transcription",
            "proposed_raw_label": None,
            "proposed_raw_values": [],
            "proposed_context_text": CONTEXT_TRANSCRIPTIONS[number],
            "normalization_effect": "preserve_context_outside_financial_mapping",
        }
    label, values = FINANCIAL_TRANSCRIPTIONS[number]
    return {
        "exact_ambiguity": (
            "The exact source bbox contains a financial row or value sequence; low-confidence OCR omitted, "
            "corrupted, or mis-associated source label/value cells."
        ),
        "proposed_extraction_resolution": "replace_with_source_verified_transcription",
        "proposed_raw_label": label,
        "proposed_raw_values": values,
        "proposed_context_text": None,
        "normalization_effect": "eligible_for_controlled_derived_extraction_only",
    }


def main() -> None:
    registry = read_json(DATA / "source-document-registry.json")
    records: list[dict[str, object]] = []
    for document in registry["documents"]:
        document_key = str(document["document_key"])
        document_root = DATA / document_key
        tables = {
            str(table["table_key"]): table
            for table in read_json(document_root / "table_manifest.json")["records"]
        }
        page_evidence = {
            str(page["table_key"]): page
            for page in read_json(document_root / "raw-tables" / "source_table_pages.json")["records"]
        }
        rows = read_json(document_root / "raw-tables" / "source_table_rows.json")["records"]
        for row in rows:
            table = tables[str(row["table_key"])]
            if table["section"] not in INCLUDED_SECTIONS or float(row["parser_confidence"]) >= 80:
                continue
            page = page_evidence[str(row["table_key"])]
            number = len(records) + 1
            decision = decision_fields(number, row)
            records.append({
                "batch_record_number": number,
                "document_key": document_key,
                "source_file": document["source_file"],
                "pdf_page_number": table["page_number"],
                "printed_page_label": page["printed_page_label"],
                "page_key": row["page_key"],
                "table_key": row["table_key"],
                "manifest_section": table["section"],
                "table_family": table["table_family"],
                "row_key": row["row_key"],
                "row_index": row["row_index"],
                "bbox": row["bbox"],
                "parser_confidence": row["parser_confidence"],
                "raw_label": row["raw_label_candidate"],
                "raw_text": row["raw_text"],
                "raw_values": row["raw_values"],
                **decision,
                "source_review_method": "visual_review_of_exact_pdf_page_and_row_bbox_at_180_dpi",
                "decision": "revised_and_approved",
                "decision_basis": "visual_comparison_with_exact_pdf_page_and_row_bbox_at_180_dpi",
                "decision_date": "2026-07-14",
                "review_status": "approved_for_controlled_extraction_application",
            })

    family_counts = Counter(str(record["table_family"]) for record in records)
    section_counts = Counter(str(record["manifest_section"]) for record in records)
    value_bearing = sum(bool(record["raw_values"]) for record in records)
    payload = {
        "schema_version": 1,
        "artifact_kind": "financial_statement_low_confidence_note_schedule_review_batch",
        "gate": 5,
        "batch_key": "low_confidence_note_schedules_batch_02",
        "status": "review_complete",
        "selection_rule": {
            "parser_confidence": "less than 80",
            "manifest_sections": sorted(INCLUDED_SECTIONS),
            "excludes_batch_01_primary_statements": True,
            "sampling": "none; every matching row is included",
        },
        "counts": {
            "records": len(records),
            "source_pages": len({(record["document_key"], record["pdf_page_number"]) for record in records}),
            "documents": len({record["document_key"] for record in records}),
            "notes": section_counts["Notes"],
            "schedules": section_counts["Schedules"],
            "value_bearing_rows": value_bearing,
            "rows_without_parsed_values": len(records) - value_bearing,
            "financial_transcriptions": len(FINANCIAL_TRANSCRIPTIONS),
            "context_transcriptions": len(CONTEXT_TRANSCRIPTIONS),
            "layout_artifact_exclusions": len(EXCLUSION_RECORDS),
            "revised_and_approved": len(records),
            "approved": len(records),
        },
        "table_family_counts": dict(sorted(family_counts.items())),
        "decision_boundary": {
            "applies_raw_corrections": False,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": records,
    }
    if len(records) != 111:
        raise RuntimeError(f"Expected 111 Batch 02 rows, observed {len(records)}")
    if EXCLUSION_RECORDS | set(CONTEXT_TRANSCRIPTIONS) | set(FINANCIAL_TRANSCRIPTIONS) != set(range(1, 112)):
        raise RuntimeError("Batch 02 decision map does not cover exactly records 1 through 111")
    if (EXCLUSION_RECORDS & set(CONTEXT_TRANSCRIPTIONS)) or (EXCLUSION_RECORDS & set(FINANCIAL_TRANSCRIPTIONS)) or (set(CONTEXT_TRANSCRIPTIONS) & set(FINANCIAL_TRANSCRIPTIONS)):
        raise RuntimeError("Batch 02 decision categories overlap")
    write_json(JSON_OUT, payload)

    lines = [
        "# Gate 5 Low-Confidence Note and Schedule Review Batch 02",
        "",
        "This batch contains every raw row below parser confidence 80 in note-disclosure or schedule sections. All 111 exact row decisions were revised and approved after visual source review.",
        "",
        f"Records: {len(records)}. Notes: {section_counts['Notes']}. Schedules: {section_counts['Schedules']}. Source pages: {payload['counts']['source_pages']}.",
    ]
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    page_key = lambda record: (record["document_key"], record["pdf_page_number"])
    for (document_key, pdf_page), page_records_iter in groupby(records, key=page_key):
        page_records = list(page_records_iter)
        printed = page_records[0]["printed_page_label"] if page_records[0]["printed_page_label"] is not None else "not captured"
        lines.extend([
            "",
            f"## {document_key} — PDF page {pdf_page} (printed {printed})",
            "",
            "| # | Family and table | Row key | Confidence | Raw label | Raw values | Exact ambiguity | Approved resolution | Approved transcription | Decision |",
            "| ---: | --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
        ])
        for record in page_records:
            family_table = f"{record['table_family']} / {record['table_key']}"
            transcription = record["proposed_context_text"] or {
                "label": record["proposed_raw_label"],
                "values": record["proposed_raw_values"],
            }
            lines.append(
                f"| {record['batch_record_number']} | {escape(family_table)} | `{record['row_key']}` | "
                f"{record['parser_confidence']} | {escape(record['raw_label'])} | {escape(record['raw_values'])} | "
                f"{escape(record['exact_ambiguity'])} | `{record['proposed_extraction_resolution']}` | {escape(transcription)} | `{record['decision']}` |"
            )
    lines.extend([
        "",
        "## Decision Boundary",
        "",
        "The exact row decisions are complete. They do not alter raw evidence, apply controlled derived corrections, approve normalization, write the database, or change publication.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/source-document-registry.json`",
        "- `data/financial-statements/charlottetown/<document-key>/table_manifest.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_pages.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_rows.json`",
        "- `docs/charlottetown/financial-statements/`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built review batch 02 with {len(records)} exact rows")


if __name__ == "__main__":
    main()

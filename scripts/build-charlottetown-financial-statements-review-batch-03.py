#!/usr/bin/env python3
"""Build Gate 5 Batch 03 for remaining low-confidence cells."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
OUT = DATA / "review-batches"
JSON_OUT = OUT / "low-confidence-cells-batch-03.json"
MD_OUT = OUT / "low-confidence-cells-batch-03.md"
ROW_BATCHES = (
    OUT / "low-confidence-primary-statements-batch-01.json",
    OUT / "low-confidence-note-schedules-batch-02.json",
)
LOW_CONFIDENCE = 80.0
EXPECTED_SELECTION_FINGERPRINT = "da09ac9128c681795a31fc17e946f108d406a2d76630d46805408184808fd299"

EXCLUSION_RECORDS = {
    3, 11, 17, 141, 142, 182, 183, 193, 194, 195, 196, 202, 203, 206, 207, 208, 222, 223,
}

DASH_PLACEHOLDER_RECORDS = {
    5, 19, 22, 23, 26, 27, 28, 29, 30, 31, 35, 36, 37, 38, 40, 42, 43, 47,
    48, 50, 51, 54, 55, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
    70, 71, 74, 78, 79, 83, 84, 92, 93, 94, 96, 97, 99, 100, 103, 106, 109,
    110, 112, 113, 115, 120, 124, 130, 131, 135, 136, 143, 149, 150, 152, 156,
    163, 164, 165, 166, 167, 170, 171, 172, 173, 187, 188, 205, 211, 212, 213,
    216, 226, 227,
}

CONTEXT_TRANSCRIPTIONS = {
    18: "4.00% per annum",
    39: "Streets/sidewalks",
    56: "Services | & Environment",
    133: "Disposals",
    134: "End | Beginning",
    161: "Amort | Disposals",
    162: "End | Beginning",
}

TEXT_FINANCIAL_TRANSCRIPTIONS: dict[int, tuple[str, list[str]]] = {
    1: ("177,288,424 152,069,070", ["177,288,424", "152,069,070"]),
    2: ("372,415,485 338,911,585", ["372,415,485", "338,911,585"]),
    4: ("$ 244,578,139 $ 214,407,945", ["244,578,139", "214,407,945"]),
    6: ("$ 217,507,423 $ 132,659,880 $ 128,328,189", ["217,507,423", "132,659,880", "128,328,189"]),
    7: ("(27,350)", ["(27,350)"]),
    10: ("$ 15,694,379 $ (1,427,963)", ["15,694,379", "(1,427,963)"]),
    12: ("$ 16,594,852 $ 12,822,123", ["16,594,852", "12,822,123"]),
    13: ("(4,806,047) (4,308,130)", ["(4,806,047)", "(4,308,130)"]),
    24: ("245,383,472 213,094,823", ["245,383,472", "213,094,823"]),
    25: ("$ 244,578,139 $ 214,407,945", ["244,578,139", "214,407,945"]),
    32: ("47,574,176 123,379,580", ["47,574,176", "123,379,580"]),
    33: ("(119,265) 58,063,652 137,946,585", ["(119,265)", "58,063,652", "137,946,585"]),
    44: ("45,097,378 121,823,490", ["45,097,378", "121,823,490"]),
    46: ("55,162,809 133,579,374", ["55,162,809", "133,579,374"]),
    49: ("73,569,336 148,302,415", ["73,569,336", "148,302,415"]),
    72: ("131,216,025 127,032,014", ["131,216,025", "127,032,014"]),
    73: ("105,525,945 100,643,695", ["105,525,945", "100,643,695"]),
    75: ("244,578,140 214,407,945", ["244,578,140", "214,407,945"]),
    76: ("$ 258,646,355 $ 244,578,140", ["258,646,355", "244,578,140"]),
    80: ("$ 14,440,995 $ 30,743,224", ["14,440,995", "30,743,224"]),
    85: ("$ 1,162,537 $ 1,051,755", ["1,162,537", "1,051,755"]),
    86: ("$ 4,994,325 $ 3,378,857", ["4,994,325", "3,378,857"]),
    88: ("$ 10,307,823 $ 9,206,462", ["10,307,823", "9,206,462"]),
    95: ("256,079,160 245,383,471", ["256,079,160", "245,383,471"]),
    98: ("(488,000) 18,314,112", ["(488,000)", "18,314,112"]),
    101: ("82,594,957 154,071,601", ["82,594,957", "154,071,601"]),
    102: ("Land improvements 16,150,981", ["16,150,981"]),
    105: ("102,414,905 219,665,209", ["102,414,905", "219,665,209"]),
    108: ("47,574,176 123,379,580", ["47,574,176", "123,379,580"]),
    111: ("2,275,531", ["2,275,531"]),
    114: ("15,555,538", ["15,555,538"]),
    116: ("(22,951,540) (24,262,382)", ["(22,951,540)", "(24,262,382)"]),
    118: ("$ 117,815,004 $ 111,815,719", ["117,815,004", "111,815,719"]),
    122: ("$ 117,815,004 $ 111,815,719", ["117,815,004", "111,815,719"]),
    125: ("$ 6,752,436 $ (3,690,335)", ["6,752,436", "(3,690,335)"]),
    127: ("$ 13,883,811 $ 14,357,889", ["13,883,811", "14,357,889"]),
    128: ("$ 2,254,457 $ 1,061,294", ["2,254,457", "1,061,294"]),
    129: ("$ 117,815,004 $ 111,815,719", ["117,815,004", "111,815,719"]),
    145: ("$ 121,642,503 $ 117,815,002", ["121,642,503", "117,815,002"]),
    148: ("$ 121,642,503 $ 117,815,002", ["121,642,503", "117,815,002"]),
    151: ("$ 6,737,441 $ 5,238,023", ["6,737,441", "5,238,023"]),
    157: ("$ 13,391,328 $ 13,883,811", ["13,391,328", "13,883,811"]),
    159: ("$ 1,369,315 $ 2,254,457", ["1,369,315", "2,254,457"]),
    160: ("$ 121,642,503 $ 117,815,002", ["121,642,503", "117,815,002"]),
    169: ("$ 201,470,373 $ 58,063,652 $ 3,083,864", ["201,470,373", "58,063,652", "3,083,864"]),
    176: ("(85,833) 2,045,973", ["(85,833)", "2,045,973"]),
    181: ("103,552,673 111,520,128", ["103,552,673", "111,520,128"]),
    184: ("$ 242,475", ["242,475"]),
    186: ("27.21%", ["27.21%"]),
    189: ("131,350,715 117,472,169", ["131,350,715", "117,472,169"]),
    190: ("131,900,688 118,026,462", ["131,900,688", "118,026,462"]),
    192: ("$ 15,834,103 $ 10,118,190", ["15,834,103", "10,118,190"]),
    197: ("$ 131,411", ["131,411"]),
    198: ("$ 275,523", ["275,523"]),
    201: ("$ 545,770", ["545,770"]),
    210: ("27.21%", ["27.21%"]),
    214: ("$ 348,525", ["348,525"]),
    217: ("$ 2,925,655", ["2,925,655"]),
    218: ("$ 131,710", ["131,710"]),
    219: ("$ 684,998", ["684,998"]),
    220: ("$ 854,617", ["854,617"]),
    225: ("73,115", ["73,115"]),
    228: ("$ 131,411", ["131,411"]),
}

VALUE_CORRECTIONS = {
    16: "(792,142)",
    168: "(742,585)",
    185: "35,377,973",
}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision_fields(number: int, cell: dict[str, object]) -> dict[str, object]:
    raw_text = str(cell["raw_text"])
    if number in EXCLUSION_RECORDS:
        return {
            "exact_ambiguity": f"The exact source bbox contains no financial cell; OCR text {raw_text!r} is an isolated logo, bullet, signature mark, or table-edge artifact.",
            "proposed_extraction_resolution": "exclude_non_financial_layout_artifact",
            "proposed_cell_text": None,
            "proposed_cell_values": [],
            "proposed_value_state": None,
            "normalization_effect": "exclude_from_financial_mapping",
        }
    if number in DASH_PLACEHOLDER_RECORDS:
        source_text = "- %" if number == 211 else "-"
        return {
            "exact_ambiguity": f"The exact source bbox confirms OCR text {raw_text!r} is a source dash placeholder, not a negative sign or table rule.",
            "proposed_extraction_resolution": "classify_source_verified_dash_placeholder",
            "proposed_cell_text": source_text,
            "proposed_cell_values": [],
            "proposed_value_state": "source_dash_placeholder",
            "normalization_effect": "preserve_source_dash_and_block_zero_or_null_interpretation",
        }
    if number in CONTEXT_TRANSCRIPTIONS:
        return {
            "exact_ambiguity": f"The exact source bbox contains meaningful table context; low-confidence OCR text {raw_text!r} damaged wording or column separation.",
            "proposed_extraction_resolution": "replace_with_source_verified_context_transcription",
            "proposed_cell_text": CONTEXT_TRANSCRIPTIONS[number],
            "proposed_cell_values": [],
            "proposed_value_state": None,
            "normalization_effect": "preserve_context_outside_financial_mapping",
        }
    if number in TEXT_FINANCIAL_TRANSCRIPTIONS:
        source_text, values = TEXT_FINANCIAL_TRANSCRIPTIONS[number]
    elif str(cell["token_class"]) in {"amount_candidate", "signed_amount_candidate"}:
        source_text = VALUE_CORRECTIONS.get(number, raw_text)
        values = [source_text.replace("$", "").strip()]
    else:
        raise RuntimeError(f"Missing source-reviewed Batch 03 decision for record {number}")
    return {
        "exact_ambiguity": f"The exact source bbox contains financial content; low-confidence OCR text {raw_text!r} required source verification of text, digits, signs, and column order.",
        "proposed_extraction_resolution": "replace_with_source_verified_cell_transcription",
        "proposed_cell_text": source_text,
        "proposed_cell_values": values,
        "proposed_value_state": "amount_or_percentage",
        "normalization_effect": "eligible_for_controlled_derived_extraction_only",
    }


def main() -> None:
    registry = read_json(DATA / "source-document-registry.json")
    resolved_row_keys: set[str] = set()
    source_row_batches: list[dict[str, object]] = []
    for path in ROW_BATCHES:
        batch = read_json(path)
        if batch["status"] != "review_complete" or batch["counts"]["approved"] != len(batch["records"]):
            raise RuntimeError(f"Approved row decision batch is incomplete: {path.name}")
        resolved_row_keys.update(str(record["row_key"]) for record in batch["records"])
        source_row_batches.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "batch_key": batch["batch_key"],
            "approved_rows": len(batch["records"]),
        })

    records: list[dict[str, object]] = []
    total_low_confidence_cells = 0
    excluded_by_row_decision = 0
    for document in registry["documents"]:
        document_key = str(document["document_key"])
        document_root = DATA / document_key
        tables = {
            str(table["table_key"]): table
            for table in read_json(document_root / "table_manifest.json")["records"]
        }
        pages = {
            str(page["table_key"]): page
            for page in read_json(document_root / "raw-tables" / "source_table_pages.json")["records"]
        }
        rows = {
            str(row["row_key"]): row
            for row in read_json(document_root / "raw-tables" / "source_table_rows.json")["records"]
        }
        cells = read_json(document_root / "raw-tables" / "source_table_cells.json")["records"]
        for cell in cells:
            if float(cell["parser_confidence"]) >= LOW_CONFIDENCE:
                continue
            total_low_confidence_cells += 1
            if str(cell["row_key"]) in resolved_row_keys:
                excluded_by_row_decision += 1
                continue
            row = rows[str(cell["row_key"])]
            table = tables[str(cell["table_key"])]
            page = pages[str(cell["table_key"])]
            number = len(records) + 1
            decision = decision_fields(number, cell)
            records.append({
                "batch_record_number": number,
                "document_key": document_key,
                "source_file": document["source_file"],
                "pdf_page_number": table["page_number"],
                "printed_page_label": page["printed_page_label"],
                "page_key": cell["page_key"],
                "table_key": cell["table_key"],
                "manifest_section": table["section"],
                "table_family": table["table_family"],
                "row_key": cell["row_key"],
                "row_index": row["row_index"],
                "row_bbox": row["bbox"],
                "row_parser_confidence": row["parser_confidence"],
                "parent_raw_label": row["raw_label_candidate"],
                "parent_raw_text": row["raw_text"],
                "parent_raw_values": row["raw_values"],
                "cell_key": cell["cell_key"],
                "column_index": cell["column_index"],
                "cell_bbox": cell["bbox"],
                "raw_text": cell["raw_text"],
                "token_class": cell["token_class"],
                "parse_status": cell["parse_status"],
                "parser_confidence": cell["parser_confidence"],
                "raw_review_status": cell["review_status"],
                **decision,
                "source_review_method": "visual_review_of_exact_pdf_page_and_cell_bbox_at_180_dpi",
                "decision": "revised_and_approved",
                "decision_basis": "visual_comparison_with_exact_pdf_page_and_cell_bbox_at_180_dpi",
                "decision_date": "2026-07-14",
                "review_status": "approved_for_controlled_extraction_application",
            })

    token_counts = Counter(str(record["token_class"]) for record in records)
    family_counts = Counter(str(record["table_family"]) for record in records)
    section_counts = Counter(str(record["manifest_section"]) for record in records)
    payload = {
        "schema_version": 1,
        "artifact_kind": "financial_statement_remaining_low_confidence_cell_review_batch",
        "gate": 5,
        "batch_key": "remaining_low_confidence_cells_batch_03",
        "status": "review_complete",
        "selection_rule": {
            "cell_parser_confidence": "less than 80",
            "excludes_parent_rows_with_approved_batch_01_or_batch_02_decisions": True,
            "sampling": "none; every matching cell is included",
        },
        "source_row_decision_batches": source_row_batches,
        "counts": {
            "records": len(records),
            "source_pages": len({(record["document_key"], record["pdf_page_number"]) for record in records}),
            "documents": len({record["document_key"] for record in records}),
            "parent_rows": len({record["row_key"] for record in records}),
            "all_low_confidence_cells": total_low_confidence_cells,
            "excluded_by_approved_parent_row_decision": excluded_by_row_decision,
            "remaining_low_confidence_cells": len(records),
            "primary_statement_cells": section_counts["Primary statements"],
            "note_cells": section_counts["Notes"],
            "schedule_cells": section_counts["Schedules"],
            "financial_transcriptions": len(TEXT_FINANCIAL_TRANSCRIPTIONS) + 51 + 6 - 3,
            "context_transcriptions": len(CONTEXT_TRANSCRIPTIONS),
            "dash_placeholders": len(DASH_PLACEHOLDER_RECORDS),
            "layout_artifact_exclusions": len(EXCLUSION_RECORDS),
            "revised_and_approved": len(records),
            "approved": len(records),
        },
        "token_class_counts": dict(sorted(token_counts.items())),
        "table_family_counts": dict(sorted(family_counts.items())),
        "decision_boundary": {
            "changes_approved_row_decisions": False,
            "applies_raw_corrections": False,
            "approves_value_states": False,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": records,
    }
    if len(records) != 228 or total_low_confidence_cells != 405 or excluded_by_row_decision != 177:
        raise RuntimeError(
            "Expected 228 remaining of 405 low-confidence cells with 177 excluded by approved row decisions; "
            f"observed {len(records)}, {total_low_confidence_cells}, and {excluded_by_row_decision}"
        )
    fingerprint_source = [
        (record["cell_key"], record["raw_text"], record["parser_confidence"])
        for record in records
    ]
    selection_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_source, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if selection_fingerprint != EXPECTED_SELECTION_FINGERPRINT:
        raise RuntimeError(f"Batch 03 source selection changed: {selection_fingerprint}")
    decision_sets = [
        EXCLUSION_RECORDS,
        DASH_PLACEHOLDER_RECORDS,
        set(CONTEXT_TRANSCRIPTIONS),
        set(TEXT_FINANCIAL_TRANSCRIPTIONS),
        {number for number, record in enumerate(records, start=1) if record["token_class"] in {"amount_candidate", "signed_amount_candidate"}} - DASH_PLACEHOLDER_RECORDS,
    ]
    covered: set[int] = set()
    for decision_set in decision_sets:
        if covered & decision_set:
            raise RuntimeError("Batch 03 decision categories overlap")
        covered.update(decision_set)
    if covered != set(range(1, 229)):
        raise RuntimeError("Batch 03 decision map does not cover exactly records 1 through 228")
    write_json(JSON_OUT, payload)

    lines = [
        "# Gate 5 Remaining Low-Confidence Cell Review Batch 03",
        "",
        "This batch contains every cell below parser confidence 80 whose parent row is not already resolved by approved Batch 01 or Batch 02 treatment. All 228 exact cell decisions were revised and approved after visual source review.",
        "",
        f"Records: {len(records)}. Parent rows: {payload['counts']['parent_rows']}. Source pages: {payload['counts']['source_pages']}.",
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
            "| # | Family and table | Row and cell | Column | Confidence | Token class | Parent raw text | Cell raw text | Exact ambiguity | Approved resolution | Approved text | Approved values or state | Decision |",
            "| ---: | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for record in page_records:
            family_table = f"{record['table_family']} / {record['table_key']}"
            row_cell = f"{record['row_key']} / {record['cell_key']}"
            lines.append(
                f"| {record['batch_record_number']} | {escape(family_table)} | `{row_cell}` | "
                f"{record['column_index']} | {record['parser_confidence']} | `{record['token_class']}` | "
                f"{escape(record['parent_raw_text'])} | {escape(record['raw_text'])} | "
                f"{escape(record['exact_ambiguity'])} | `{record['proposed_extraction_resolution']}` | "
                f"{escape(record['proposed_cell_text'])} | {escape(record['proposed_cell_values'] or record['proposed_value_state'])} | "
                f"`{record['decision']}` |"
            )
    lines.extend([
        "",
        "## Decision Boundary",
        "",
        "The exact cell decisions are complete. They do not change approved row decisions, apply controlled-derived corrections, approve normalization, write the database, or change publication.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/review-batches/low-confidence-primary-statements-batch-01.json`",
        "- `data/financial-statements/charlottetown/review-batches/low-confidence-note-schedules-batch-02.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_cells.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_rows.json`",
        "- `docs/charlottetown/financial-statements/`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built review batch 03 with {len(records)} remaining low-confidence cells")


if __name__ == "__main__":
    main()

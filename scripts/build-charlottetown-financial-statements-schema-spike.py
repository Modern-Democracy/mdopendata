#!/usr/bin/env python3
"""Materialize Gate 3 representative financial-statement schema evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from PIL import Image


SCHEMA_VERSION = 1
RENDER_DPI = 220
LOW_CONFIDENCE = 80.0
PRINTED_PAGE_LABELS = {
    ("ctown_fs_city_2024_03_31_audited", 6): "1",
    ("ctown_fs_city_2025_03_31_audited", 6): "4",
    ("ctown_fs_city_2025_03_31_audited", 7): "5",
    ("ctown_fs_city_2025_03_31_audited", 9): "7",
    ("ctown_fs_city_sa_2024_12_31_audited", 6): "4",
    ("ctown_fs_ws_2025_03_31_audited", 7): "5",
    ("ctown_fs_ws_sa_2024_12_31_audited", 6): "4",
}

CONTROLS = [
    {
        "control_key": "city_2025_financial_position",
        "pattern": "consolidated_financial_position",
        "pages": [("ctown_fs_city_2025_03_31_audited", 6)],
        "expected_text": ["STATEMENT OF FINANCIAL POSITION", "5,954,281", "258,646,355"],
        "statement_class": "financial_position",
        "reporting_entity_key": "city_of_charlottetown",
        "assertions": [
            "Assets, liabilities, net debt, non-financial assets, and accumulated surplus retain hierarchy.",
            "Current and comparative actual columns remain separate document periods.",
            "A reported dash remains dash_unresolved rather than numeric zero.",
        ],
    },
    {
        "control_key": "city_2025_budget_actual_operations",
        "pattern": "budget_to_actual_operations",
        "pages": [("ctown_fs_city_2025_03_31_audited", 7)],
        "expected_text": ["STATEMENT OF OPERATIONS", "46,068,402", "47,287,806", "43,892,492"],
        "statement_class": "operations",
        "reporting_entity_key": "city_of_charlottetown",
        "assertions": [
            "Budget 2025, actual 2025, and actual 2024 are distinct source columns.",
            "Budget and actual are amount types; period identity remains document-owned.",
            "Reported totals remain non-additive reconciliation controls.",
        ],
    },
    {
        "control_key": "city_2025_cash_flow",
        "pattern": "cash_flow_sections",
        "pages": [("ctown_fs_city_2025_03_31_audited", 9)],
        "expected_text": ["STATEMENT OF CASH FLOW", "50,843,942", "3,811,233", "21,648,661"],
        "statement_class": "cash_flow",
        "reporting_entity_key": "city_of_charlottetown",
        "assertions": [
            "Operating, capital, investing, and financing sections retain separate hierarchy.",
            "Section totals are not additive with their detail rows.",
            "Parenthesized cash movements remain negative reported values.",
        ],
    },
    {
        "control_key": "water_sewer_2025_operations",
        "pattern": "component_operations",
        "pages": [("ctown_fs_ws_2025_03_31_audited", 7)],
        "expected_text": ["STATEMENT OF OPERATIONS", "12,430,885", "12,792,726", "12,478,489"],
        "statement_class": "operations",
        "reporting_entity_key": "charlottetown_water_and_sewer_corporation",
        "assertions": [
            "The Water and Sewer Corporation remains a separate reporting entity.",
            "Its values may link to City consolidated scope but must not be added to that scope.",
            "Budget and both actual columns retain document-specific identities.",
        ],
    },
    {
        "control_key": "city_superannuation_2024_position",
        "pattern": "pension_position",
        "pages": [("ctown_fs_city_sa_2024_12_31_audited", 6)],
        "expected_text": ["STATEMENT OF FINANCIAL POSITION", "131,900,688", "116,066,585", "15,834,103"],
        "statement_class": "financial_position",
        "reporting_entity_key": "city_of_charlottetown_superannuation_plan",
        "assertions": [
            "Plan assets, pension obligations, and net surplus retain pension-plan scope.",
            "December 31 periods cannot be joined to March 31 municipal periods by year label.",
            "The plan is related to the City but non-additive to City consolidated totals.",
        ],
    },
    {
        "control_key": "city_2024_comparative_difference",
        "pattern": "draft_audited_comparative_difference",
        "pages": [
            ("ctown_fs_city_2024_03_31_audited", 6),
            ("ctown_fs_city_2025_03_31_audited", 6),
        ],
        "expected_text": ["15,694,379", "15,694,380"],
        "statement_class": "financial_position",
        "reporting_entity_key": "city_of_charlottetown",
        "assertions": [
            "The 2024 cash value remains document-owned in both source documents.",
            "The one-dollar difference is not overwritten or silently reconciled.",
            "Any comparative_of or restates relationship requires a reviewed observation relationship.",
        ],
    },
    {
        "control_key": "water_sewer_superannuation_2024_date",
        "pattern": "filename_reporting_date_conflict",
        "pages": [("ctown_fs_ws_sa_2024_12_31_audited", 6)],
        "expected_text": ["DECEMBER 31, 2024", "10,663,117", "9,808,500", "854,617"],
        "statement_class": "financial_position",
        "reporting_entity_key": "charlottetown_water_and_sewer_corporation_superannuation_plan",
        "assertions": [
            "The visible December 31, 2024 reporting date controls period identity.",
            "The filename's December 21 text remains source metadata and creates no fiscal period.",
            "The related pension plan remains non-additive to Water and Sewer or City totals.",
        ],
    },
]


def stable_hash(*parts: object, length: int = 20) -> str:
    value = "|".join(str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def locate_tools() -> tuple[str, str]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise RuntimeError("pdftotext is unavailable")
    pdftoppm_sibling = Path(pdftotext).resolve().parent / "pdftoppm.exe"
    pdftoppm = str(pdftoppm_sibling) if pdftoppm_sibling.exists() else shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is unavailable")
    tesseract = shutil.which("tesseract")
    if not tesseract:
        tesseract = next(
            (
                str(candidate)
                for candidate in (
                    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
                    Path(r"C:\Program Files\PDF24\tesseract\tesseract.exe"),
                )
                if candidate.exists()
            ),
            None,
        )
    if not tesseract:
        raise RuntimeError("tesseract is unavailable")
    return pdftoppm, tesseract


def command_text(args: list[str]) -> str:
    return subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def normalized_bbox(x0: int, top: int, x1: int, bottom: int, width: int, height: int) -> list[float]:
    return [
        round(x0 / width, 6),
        round(top / height, 6),
        round(x1 / width, 6),
        round(bottom / height, 6),
    ]


def split_cells(words: list[dict[str, object]], gap: int = 55) -> list[list[dict[str, object]]]:
    cells: list[list[dict[str, object]]] = []
    for word in words:
        if not cells or int(word["x0"]) - int(cells[-1][-1]["x1"]) > gap:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def control_keys_for_page(document_key: str, page_number: int) -> list[str]:
    return [
        control["control_key"]
        for control in CONTROLS
        if (document_key, page_number) in control["pages"]
    ]


def extract_page(
    root: Path,
    document: dict[str, object],
    page_number: int,
    pdftoppm: str,
    tesseract: str,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], str]:
    document_key = str(document["document_key"])
    page_key = f"{document_key}_p{page_number:03d}"
    pdf = root / str(document["source_file"])
    controls = control_keys_for_page(document_key, page_number)
    profile_inventory = read_json(
        root / "data" / "financial-statements" / "charlottetown" / document_key / "page_inventory.json"
    )["records"]
    profile_page = next(record for record in profile_inventory if record["page_number"] == page_number)
    with tempfile.TemporaryDirectory(prefix=f"{page_key}-spike-") as temp_name:
        prefix = Path(temp_name) / "page"
        subprocess.run(
            [pdftoppm, "-f", str(page_number), "-l", str(page_number), "-png", "-r", str(RENDER_DPI), "-singlefile", str(pdf), str(prefix)],
            check=True,
            capture_output=True,
        )
        image_path = prefix.with_suffix(".png")
        with Image.open(image_path) as image:
            width, height = image.size
        tsv = command_text([tesseract, str(image_path), "stdout", "--psm", "4", "tsv"])

    words: list[dict[str, object]] = []
    for record in csv.DictReader(tsv.splitlines(), delimiter="\t"):
        value = (record.get("text") or "").strip()
        if record.get("level") != "5" or not value:
            continue
        confidence = float(record["conf"])
        if confidence < 0:
            continue
        left = int(record["left"])
        top = int(record["top"])
        words.append(
            {
                "text": value,
                "x0": left,
                "top": top,
                "x1": left + int(record["width"]),
                "bottom": top + int(record["height"]),
                "confidence": confidence,
                "line_key": (record["block_num"], record["par_num"], record["line_num"]),
            }
        )
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for word in words:
        grouped.setdefault(word["line_key"], []).append(word)
    lines = sorted(
        (sorted(line, key=lambda item: int(item["x0"])) for line in grouped.values()),
        key=lambda line: (min(int(word["top"]) for word in line), min(int(word["x0"]) for word in line)),
    )
    rows: list[dict[str, object]] = []
    cells: list[dict[str, object]] = []
    for row_index, line in enumerate(lines, start=1):
        raw_text = " ".join(str(word["text"]) for word in line)
        x0 = min(int(word["x0"]) for word in line)
        top = min(int(word["top"]) for word in line)
        x1 = max(int(word["x1"]) for word in line)
        bottom = max(int(word["bottom"]) for word in line)
        bbox = normalized_bbox(x0, top, x1, bottom, width, height)
        confidence = round(sum(float(word["confidence"]) for word in line) / len(line), 3)
        row_key = f"{page_key}_r_{stable_hash(round(bbox[1], 6), raw_text)}"
        rows.append(
            {
                "row_key": row_key,
                "page_key": page_key,
                "control_keys": controls,
                "row_index": row_index,
                "raw_text": raw_text,
                "bbox": bbox,
                "extraction_method": "ocr_tesseract_word_tsv",
                "parser_confidence": confidence,
                "review_status": "needs_review" if confidence < LOW_CONFIDENCE else "unreviewed",
            }
        )
        for column_index, cell_words in enumerate(split_cells(line), start=0):
            cell_text = " ".join(str(word["text"]) for word in cell_words)
            cell_confidence = round(
                sum(float(word["confidence"]) for word in cell_words) / len(cell_words), 3
            )
            cell_bbox = normalized_bbox(
                min(int(word["x0"]) for word in cell_words),
                min(int(word["top"]) for word in cell_words),
                max(int(word["x1"]) for word in cell_words),
                max(int(word["bottom"]) for word in cell_words),
                width,
                height,
            )
            cells.append(
                {
                    "cell_key": f"{row_key}_c_{column_index:02d}_{stable_hash(cell_text, cell_bbox)}",
                    "row_key": row_key,
                    "page_key": page_key,
                    "control_keys": controls,
                    "column_index": column_index,
                    "raw_text": cell_text,
                    "bbox": cell_bbox,
                    "parse_status": "unparsed",
                    "parser_confidence": cell_confidence,
                    "review_status": "needs_review" if cell_confidence < LOW_CONFIDENCE else "unreviewed",
                }
            )
    page_record = {
        "page_key": page_key,
        "document_key": document_key,
        "control_keys": controls,
        "source_file": document["source_file"],
        "source_sha256": document["sha256"],
        "pdf_page_number": page_number,
        "printed_page_label": profile_page["printed_page_label"] or PRINTED_PAGE_LABELS[(document_key, page_number)],
        "printed_page_label_method": (
            "profile_ocr" if profile_page["printed_page_label"] else "reviewed_control_manifest"
        ),
        "extraction_method": "ocr_tesseract_word_tsv",
        "extractor_psm": 4,
        "render_dpi": RENDER_DPI,
        "width_pixels": width,
        "height_pixels": height,
        "row_count": len(rows),
        "cell_count": len(cells),
    }
    full_text = "\n".join(row["raw_text"] for row in rows)
    return page_record, rows, cells, full_text


def source_columns_for(control: dict[str, object]) -> list[dict[str, object]]:
    pattern = control["pattern"]
    if pattern in {"budget_to_actual_operations", "component_operations"}:
        return [
            {"column_key": "label", "raw_header": None, "column_role": "line_label"},
            {"column_key": "budget_current", "raw_header": "Budget 2025", "period_role": "current", "amount_type": "budget"},
            {"column_key": "actual_current", "raw_header": "Actual 2025", "period_role": "current", "amount_type": "actual"},
            {"column_key": "actual_prior", "raw_header": "Actual 2024", "period_role": "comparative", "amount_type": "actual"},
        ]
    if pattern == "draft_audited_comparative_difference":
        return [
            {"column_key": "document_owned_actual", "period_role": "current_or_comparative", "amount_type": "actual"}
        ]
    return [
        {"column_key": "label", "raw_header": None, "column_role": "line_label"},
        {"column_key": "actual_current", "period_role": "current", "amount_type": "actual"},
        {"column_key": "actual_prior", "period_role": "comparative", "amount_type": "actual"},
    ]


def schema_projections() -> list[dict[str, object]]:
    planned_objects = {
        "document_accounting_context",
        "reporting_entity_relationship",
        "statement_class",
        "financial_observation_relationship",
    }
    records: list[dict[str, object]] = []
    for control in CONTROLS:
        document_key, first_page = control["pages"][0]
        records.append(
            {
                "control_key": control["control_key"],
                "pattern": control["pattern"],
                "source_pages": [f"{key}_p{page:03d}" for key, page in control["pages"]],
                "source_table_key": f"{document_key}_p{first_page:03d}_t01",
                "statement": {
                    "statement_key": f"{document_key}_{control['statement_class']}",
                    "statement_kind": "financial_statement",
                    "statement_class": control["statement_class"],
                    "reporting_entity_key": control["reporting_entity_key"],
                },
                "source_columns": source_columns_for(control),
                "existing_schema_records": [
                    "source_document",
                    "source_page",
                    "source_table",
                    "source_table_column",
                    "source_table_row",
                    "source_table_cell",
                    "reporting_entity",
                    "document_period",
                    "statement",
                    "line_item",
                    "financial_observation",
                    "financial_observation_source",
                ],
                "planned_migration_objects": sorted(planned_objects),
                "assertions": control["assertions"],
                "fit_status": "fits_with_planned_migration_029",
            }
        )
    return records


def schema_fit_report() -> dict[str, object]:
    findings = [
        {
            "finding_key": "raw_source_and_hierarchy_fit",
            "status": "fits_existing_schema",
            "evidence": "Source pages, tables, columns, rows, cells, line-item parents, aggregation roles, and observation provenance retain the representative source structure.",
        },
        {
            "finding_key": "budget_actual_period_role_fit",
            "status": "fits_existing_schema",
            "evidence": "document_period plus amount_type separates current budget, current actual, and comparative actual columns without fixed fiscal-year fields.",
        },
        {
            "finding_key": "accounting_context_gap",
            "status": "resolved_by_planned_migration_029",
            "required_object": "budget.document_accounting_context",
            "evidence": "Reporting framework, reporting date, assurance, opinion, consolidation scope, and authority cannot be represented together on source_document.",
        },
        {
            "finding_key": "controlled_statement_class_gap",
            "status": "resolved_by_planned_migration_029",
            "required_object": "budget.statement_class",
            "evidence": "Free-text statement_kind cannot enforce financial position, operations, cash flow, pension movement, and schedule classes.",
        },
        {
            "finding_key": "reporting_entity_scope_relationship_gap",
            "status": "resolved_by_planned_migration_029",
            "required_object": "budget.reporting_entity_relationship",
            "evidence": "Consolidated component and related non-additive pension relationships require effective, reviewed relation types rather than parent_entity_id.",
        },
        {
            "finding_key": "comparative_relationship_gap",
            "status": "resolved_by_planned_migration_029",
            "required_object": "budget.financial_observation_relationship",
            "evidence": "The two document-owned 2024 cash values differ by one dollar and require a reviewed relationship without overwriting either observation.",
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "financial_statement_schema_fit_report",
        "gate": 3,
        "status": "ready_for_migration_029",
        "controls_reviewed": len(CONTROLS),
        "findings": findings,
        "counts": {
            "fits_existing_schema": sum(item["status"] == "fits_existing_schema" for item in findings),
            "resolved_by_planned_migration_029": sum(item["status"] == "resolved_by_planned_migration_029" for item in findings),
            "unsupported_patterns": 0,
            "unplanned_schema_gaps": 0,
        },
        "architecture_decision": "Migrations 029 and 030 may proceed as planned. Gate 3 found no additional table family, identity protocol, or schema object requirement.",
        "prohibitions": [
            "Do not overwrite document-owned comparative values.",
            "Do not sum City consolidated, Water and Sewer component, or pension-plan scopes.",
            "Do not create a December 21 fiscal period from the Water and Sewer pension filename.",
            "Do not publish or import these spike projections as normalized observations.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("data/financial-statements/charlottetown/source-document-registry.json"))
    parser.add_argument("--out", type=Path, default=Path("data/financial-statements/charlottetown/schema-spike"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    registry_path = args.registry if args.registry.is_absolute() else root / args.registry
    out = args.out if args.out.is_absolute() else root / args.out
    out.mkdir(parents=True, exist_ok=True)
    registry = read_json(registry_path)
    by_key = {document["document_key"]: document for document in registry["documents"]}
    requested_pages = sorted(
        {(document_key, page) for control in CONTROLS for document_key, page in control["pages"]}
    )
    pdftoppm, tesseract = locate_tools()
    tesseract_version = command_text([tesseract, "--version"]).splitlines()[0]
    pages: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    cells: list[dict[str, object]] = []
    page_text: dict[tuple[str, int], str] = {}
    for document_key, page_number in requested_pages:
        print(f"Materializing {document_key} page {page_number}", flush=True)
        page, page_rows, page_cells, full_text = extract_page(
            root, by_key[document_key], page_number, pdftoppm, tesseract
        )
        page["extractor_version"] = tesseract_version
        pages.append(page)
        rows.extend(page_rows)
        cells.extend(page_cells)
        page_text[(document_key, page_number)] = full_text

    control_results: list[dict[str, object]] = []
    for control in CONTROLS:
        combined = "\n".join(page_text[page] for page in control["pages"])
        missing = [value for value in control["expected_text"] if value.upper() not in combined.upper()]
        control_results.append(
            {
                "control_key": control["control_key"],
                "pattern": control["pattern"],
                "source_pages": [f"{key}_p{page:03d}" for key, page in control["pages"]],
                "expected_text": control["expected_text"],
                "missing_expected_text": missing,
                "status": "pass" if not missing else "fail",
            }
        )
    fit = schema_fit_report()
    projections = schema_projections()
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "financial_statement_schema_spike_summary",
        "gate": 3,
        "status": "complete" if all(item["status"] == "pass" for item in control_results) else "failed",
        "counts": {
            "controls": len(CONTROLS),
            "unique_source_pages": len(pages),
            "source_rows": len(rows),
            "source_cells": len(cells),
            "low_confidence_rows": sum(row["parser_confidence"] < LOW_CONFIDENCE for row in rows),
            "low_confidence_cells": sum(cell["parser_confidence"] < LOW_CONFIDENCE for cell in cells),
            "null_row_bboxes": sum(row["bbox"] is None for row in rows),
            "null_cell_bboxes": sum(cell["bbox"] is None for cell in cells),
            "control_failures": sum(item["status"] != "pass" for item in control_results),
            "unsupported_patterns": fit["counts"]["unsupported_patterns"],
            "unplanned_schema_gaps": fit["counts"]["unplanned_schema_gaps"],
            "database_writes": 0,
        },
        "rows_by_page": dict(sorted(Counter(row["page_key"] for row in rows).items())),
        "cells_by_page": dict(sorted(Counter(cell["page_key"] for cell in cells).items())),
        "control_results": control_results,
        "outputs": [
            "representative-control-manifest.json",
            "representative-source-pages.json",
            "representative-source-rows.json",
            "representative-source-cells.json",
            "representative-schema-projections.json",
            "schema-fit-report.json",
            "spike-summary.json",
        ],
    }
    control_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "financial_statement_representative_control_manifest",
        "controls": CONTROLS,
    }
    write_json(out / "representative-control-manifest.json", control_manifest)
    write_json(out / "representative-source-pages.json", {"schema_version": SCHEMA_VERSION, "records": pages})
    write_json(out / "representative-source-rows.json", {"schema_version": SCHEMA_VERSION, "records": rows})
    write_json(out / "representative-source-cells.json", {"schema_version": SCHEMA_VERSION, "records": cells})
    write_json(out / "representative-schema-projections.json", {"schema_version": SCHEMA_VERSION, "records": projections})
    write_json(out / "schema-fit-report.json", fit)
    write_json(out / "spike-summary.json", summary)
    if summary["status"] != "complete":
        failures = [item for item in control_results if item["status"] != "pass"]
        raise RuntimeError(f"Representative controls failed: {failures}")
    print(
        f"Materialized {len(CONTROLS)} controls across {len(pages)} pages, {len(rows)} rows, and {len(cells)} cells",
        flush=True,
    )


if __name__ == "__main__":
    main()

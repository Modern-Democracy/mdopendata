#!/usr/bin/env python3
"""Materialize representative budget rows/cells and reconciliation controls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

import pdfplumber
from PIL import Image


EMBEDDED_CASES = [
    ("operating_detail", "2026-2027", 30),
    ("facility_operating_summary", "2026-2027", 105),
    ("capital_partner_funding", "2026-2027", 111),
    ("capital_project_profile", "2026-2027", 112),
    ("property_tax_calculation", "2026-2027", 149),
    ("long_term_debt", "2026-2027", 151),
]

PDF_NAMES = {
    "2024-2025": "2024-2025 Financial Plan Capital and Operational Budgets.pdf",
    "2025-2026": "2025-2026 Financial Plan Capital and Operational Budgets.pdf",
    "2026-2027": "2026-2027 Financial Plan Capital and Operating Budgets.pdf",
}


def stable_key(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def normalized_bbox(x0: float, top: float, x1: float, bottom: float, width: float, height: float) -> list[float]:
    return [round(x0 / width, 6), round(top / height, 6), round(x1 / width, 6), round(bottom / height, 6)]


def group_words(words: list[dict[str, object]], tolerance: float = 3.0) -> list[list[dict[str, object]]]:
    lines: list[list[dict[str, object]]] = []
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        for line in lines:
            if abs(float(line[0]["top"]) - float(word["top"])) <= tolerance:
                line.append(word)
                break
        else:
            lines.append([word])
    return [sorted(line, key=lambda item: float(item["x0"])) for line in lines]


def split_cells(words: list[dict[str, object]], gap: float = 18.0) -> list[list[dict[str, object]]]:
    cells: list[list[dict[str, object]]] = []
    for word in words:
        if not cells or float(word["x0"]) - float(cells[-1][-1]["x1"]) > gap:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def materialize_embedded(pdf_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    cells: list[dict[str, object]] = []
    pages: list[dict[str, object]] = []
    handles: dict[str, pdfplumber.PDF] = {}
    try:
        for case_key, document, page_number in EMBEDDED_CASES:
            pdf = handles.setdefault(document, pdfplumber.open(pdf_dir / PDF_NAMES[document]))
            page = pdf.pages[page_number - 1]
            words = page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False) or []
            page_key = f"{document}-p{page_number:03d}"
            pages.append({
                "case_key": case_key,
                "page_key": page_key,
                "document": document,
                "pdf_page_number": page_number,
                "page_order": 1,
                "page_role": "single_page",
                "extraction_method": "embedded_text",
                "width_points": page.width,
                "height_points": page.height,
            })
            for row_index, line in enumerate(group_words(words), start=1):
                text = " ".join(str(word["text"]) for word in line)
                row_key = f"{page_key}-r-{stable_key(round(float(line[0]['top']), 2), text)}"
                row_bbox = normalized_bbox(
                    min(float(word["x0"]) for word in line), min(float(word["top"]) for word in line),
                    max(float(word["x1"]) for word in line), max(float(word["bottom"]) for word in line),
                    page.width, page.height,
                )
                row = {
                    "case_key": case_key,
                    "row_key": row_key,
                    "page_key": page_key,
                    "row_index": row_index,
                    "raw_text": text,
                    "bbox": row_bbox,
                    "extraction_method": "embedded_text",
                }
                rows.append(row)
                for column_index, cell_words in enumerate(split_cells(line), start=1):
                    cell_text = " ".join(str(word["text"]) for word in cell_words)
                    cells.append({
                        "case_key": case_key,
                        "cell_key": f"{row_key}-c-{stable_key(column_index, cell_text)}",
                        "row_key": row_key,
                        "column_index": column_index,
                        "raw_text": cell_text,
                        "bbox": normalized_bbox(
                            min(float(word["x0"]) for word in cell_words), min(float(word["top"]) for word in cell_words),
                            max(float(word["x1"]) for word in cell_words), max(float(word["bottom"]) for word in cell_words),
                            page.width, page.height,
                        ),
                        "parse_status": "unreviewed",
                    })
    finally:
        for pdf in handles.values():
            pdf.close()
    return pages, rows, cells


def executable(name: str, candidates: list[Path]) -> str:
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"Required executable not found: {name}")


def materialize_ocr(pdf_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    pages: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    cells: list[dict[str, object]] = []
    case_key = "ocr_facility_detail"
    pdftoppm = executable("pdftoppm", [Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe"])
    tesseract = executable("tesseract", [Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"), Path(r"C:\Program Files\PDF24\tesseract\tesseract.exe")])
    tesseract_version = subprocess.run([tesseract, "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
    pdf_path = pdf_dir / PDF_NAMES["2024-2025"]
    with pdfplumber.open(pdf_path) as pdf:
        for page_order, page_number in enumerate(range(82, 88), start=1):
            source_page = pdf.pages[page_number - 1]
            page_key = f"2024-2025-p{page_number:03d}"
            with tempfile.TemporaryDirectory(prefix="budget-schema-spike-") as temp:
                prefix = Path(temp) / "page"
                subprocess.run([pdftoppm, "-f", str(page_number), "-l", str(page_number), "-png", "-r", "180", "-singlefile", str(pdf_path), str(prefix)], check=True, capture_output=True)
                image_path = prefix.with_suffix(".png")
                with Image.open(image_path) as image:
                    pixel_width, pixel_height = image.size
                result = subprocess.run([tesseract, str(image_path), "stdout", "--psm", "6", "tsv"], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
            word_records: list[dict[str, object]] = []
            for record in csv.DictReader(result.stdout.splitlines(), delimiter="\t"):
                if record.get("level") != "5" or not record.get("text", "").strip():
                    continue
                confidence = float(record["conf"])
                if confidence < 0:
                    continue
                word_records.append({
                    "text": record["text"].strip(),
                    "x0": int(record["left"]),
                    "top": int(record["top"]),
                    "x1": int(record["left"]) + int(record["width"]),
                    "bottom": int(record["top"]) + int(record["height"]),
                    "confidence": confidence,
                    "line_key": (record["block_num"], record["par_num"], record["line_num"]),
                })
            grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
            for word in word_records:
                grouped.setdefault(word["line_key"], []).append(word)
            lines = sorted((sorted(line, key=lambda item: int(item["x0"])) for line in grouped.values()), key=lambda line: (int(line[0]["top"]), int(line[0]["x0"])))
            pages.append({
                "case_key": case_key,
                "page_key": page_key,
                "document": "2024-2025",
                "pdf_page_number": page_number,
                "page_order": page_order,
                "page_role": "start" if page_order == 1 else ("end" if page_number == 87 else "continuation"),
                "extraction_method": "ocr_tesseract_word_tsv",
                "extractor_version": tesseract_version,
                "render_dpi": 180,
                "width_points": source_page.width,
                "height_points": source_page.height,
                "width_pixels": pixel_width,
                "height_pixels": pixel_height,
            })
            for row_index, line in enumerate(lines, start=1):
                text = " ".join(str(word["text"]) for word in line)
                row_key = f"{page_key}-r-{stable_key(round(int(line[0]['top']) / pixel_height, 6), text)}"
                row_confidence = round(sum(float(word["confidence"]) for word in line) / len(line), 3)
                rows.append({
                    "case_key": case_key,
                    "row_key": row_key,
                    "page_key": page_key,
                    "row_index": row_index,
                    "raw_text": text,
                    "bbox": normalized_bbox(min(int(word["x0"]) for word in line), min(int(word["top"]) for word in line), max(int(word["x1"]) for word in line), max(int(word["bottom"]) for word in line), pixel_width, pixel_height),
                    "extraction_method": "ocr_tesseract_word_tsv",
                    "ocr_confidence": row_confidence,
                    "ocr_review_status": "review_required_low_confidence" if row_confidence < 80 else "unreviewed",
                })
                for column_index, cell_words in enumerate(split_cells(line, gap=45.0), start=1):
                    cell_text = " ".join(str(word["text"]) for word in cell_words)
                    cell_confidence = round(sum(float(word["confidence"]) for word in cell_words) / len(cell_words), 3)
                    cells.append({
                        "case_key": case_key,
                        "cell_key": f"{row_key}-c-{stable_key(column_index, cell_text)}",
                        "row_key": row_key,
                        "column_index": column_index,
                        "raw_text": cell_text,
                        "bbox": normalized_bbox(min(int(word["x0"]) for word in cell_words), min(int(word["top"]) for word in cell_words), max(int(word["x1"]) for word in cell_words), max(int(word["bottom"]) for word in cell_words), pixel_width, pixel_height),
                        "parse_status": "review_required_low_ocr_confidence" if cell_confidence < 80 else "unreviewed_ocr",
                        "ocr_confidence": cell_confidence,
                    })
    return pages, rows, cells


def reconciliation(check_key: str, formula: str, inputs: dict[str, Decimal], calculated: Decimal, reported: Decimal | None, tolerance: Decimal = Decimal("1"), reported_state: str = "reported") -> dict[str, object]:
    difference = None if reported is None else calculated - reported
    passed = reported is not None and abs(difference) <= tolerance
    return {
        "check_key": check_key,
        "formula": formula,
        "inputs": {key: str(value) for key, value in inputs.items()},
        "calculated_value": str(calculated),
        "reported_value": None if reported is None else str(reported),
        "reported_value_state": reported_state,
        "difference": None if difference is None else str(difference),
        "tolerance": str(tolerance),
        "passed": passed,
    }


def reconciliations() -> list[dict[str, object]]:
    checks = [
        reconciliation("capital_environment_net", "gross + funding_deduction = net", {"gross": Decimal("1482450"), "funding_deduction": Decimal("-803335")}, Decimal("1482450") - Decimal("803335"), Decimal("679115")),
        reconciliation("capital_transit_net", "gross + funding_deduction = net", {"gross": Decimal("10399961"), "funding_deduction": Decimal("-6392577")}, Decimal("10399961") - Decimal("6392577"), Decimal("4007384")),
        reconciliation("capital_combined_net", "component nets sum to combined net", {"environment_net": Decimal("679115"), "transit_net": Decimal("4007384")}, Decimal("679115") + Decimal("4007384"), Decimal("4686499")),
        reconciliation("tax_pei_resident_residential", "assessment * rate / 100 = reported revenue", {"assessment": Decimal("2747064500"), "rate": Decimal("0.67")}, Decimal("2747064500") * Decimal("0.67") / Decimal("100"), Decimal("19991891")),
        reconciliation("debt_principal_interest", "principal + interest = combined total", {"principal": Decimal("5871868"), "interest": Decimal("5150182")}, Decimal("5871868") + Decimal("5150182"), Decimal("11022050")),
        reconciliation("facility_current_balance", "operating revenue - operating expense = earnings", {"revenue": Decimal("4073224"), "expense": Decimal("4073224")}, Decimal("4073224") - Decimal("4073224"), None, reported_state="dash_unresolved"),
        reconciliation("facility_prior_balance", "operating revenue - operating expense = earnings", {"revenue": Decimal("3822876"), "expense": Decimal("3819626")}, Decimal("3822876") - Decimal("3819626"), None, reported_state="dash_unresolved"),
    ]
    for check in checks:
        check["status"] = "pass" if check["passed"] else ("reported_dash_review" if check["reported_value_state"] == "dash_unresolved" else "source_variance_review")
    return checks


def review_issues(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key = {check["check_key"]: check for check in checks}
    return [
        {
            "review_key": "budget-review-2026-2027-tax-pei-resident-residential",
            "issue_code": "reported_calculation_variance",
            "subject_type": "reconciliation_result",
            "subject_key": "tax_pei_resident_residential",
            "municipality": "charlottetown",
            "document": "2026-2027",
            "pdf_pages": [149],
            "severity": "high",
            "status": "open",
            "title": "Displayed residential tax calculation does not reconcile",
            "description": "The displayed assessment multiplied by the displayed rate per $100 does not equal the displayed tax revenue.",
            "observed": by_key["tax_pei_resident_residential"],
            "publication_effect": "allow_reported_facts_with_warning_block_derived_tax_check",
            "required_resolution": "Obtain authoritative clarification or approve the three displayed values as independent reported facts with a persistent variance warning.",
            "allowed_decisions": ["clarified_by_authoritative_source", "accept_reported_values_with_warning", "superseded_by_corrected_source"],
            "prohibited_action": "Do not alter any reported value to force reconciliation."
        },
        {
            "review_key": "budget-review-2026-2027-facility-current-earnings-dash",
            "issue_code": "reported_dash_with_calculated_balance",
            "subject_type": "reconciliation_result",
            "subject_key": "facility_current_balance",
            "municipality": "charlottetown",
            "document": "2026-2027",
            "pdf_pages": [105],
            "severity": "medium",
            "status": "open",
            "title": "Current-period facility earnings is displayed as a dash",
            "description": "Revenue and expense both equal 4,073,224, producing a calculated zero, while the source displays a dash for earnings/loss.",
            "observed": by_key["facility_current_balance"],
            "publication_effect": "publish_dash_unresolved_allow_derived_zero_with_label",
            "required_resolution": "Confirm whether the dash means zero or not applicable; until then preserve the dash and label zero as derived.",
            "allowed_decisions": ["dash_means_zero", "dash_means_not_applicable", "retain_dash_unresolved"],
            "prohibited_action": "Do not convert the reported dash to a reported zero without review."
        },
        {
            "review_key": "budget-review-2026-2027-facility-prior-earnings-dash",
            "issue_code": "reported_dash_with_nonzero_calculated_balance",
            "subject_type": "reconciliation_result",
            "subject_key": "facility_prior_balance",
            "municipality": "charlottetown",
            "document": "2026-2027",
            "pdf_pages": [105],
            "severity": "high",
            "status": "open",
            "title": "Prior-period facility earnings dash conflicts with calculated balance",
            "description": "Reported prior-period revenue exceeds reported expense by 3,250, while the source displays a dash for earnings/loss.",
            "observed": by_key["facility_prior_balance"],
            "publication_effect": "publish_dash_unresolved_block_derived_earnings_without_warning",
            "required_resolution": "Confirm whether a source line is omitted, the dash has a special meaning, or a corrected statement exists.",
            "allowed_decisions": ["clarified_by_authoritative_source", "accept_calculated_balance_as_derived_with_warning", "retain_dash_unresolved", "superseded_by_corrected_source"],
            "prohibited_action": "Do not publish 3,250 as a reported earnings value."
        }
    ]


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", type=Path, default=Path("docs/charlottetown/budget"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/budget/charlottetown"))
    parser.add_argument("--out", type=Path, default=Path("data/budget/charlottetown/schema-spike"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    embedded_pages, embedded_rows, embedded_cells = materialize_embedded(args.pdf_dir)
    ocr_pages, ocr_rows, ocr_cells = materialize_ocr(args.pdf_dir)
    pages = embedded_pages + ocr_pages
    rows = embedded_rows + ocr_rows
    cells = embedded_cells + ocr_cells
    checks = reconciliations()
    issues = review_issues(checks)
    ocr_materialized_rows = [row for row in rows if row["case_key"] == "ocr_facility_detail"]
    ocr_materialized_cells = [cell for cell in cells if cell["case_key"] == "ocr_facility_detail"]
    summary = {
        "schema_version": 1,
        "case_count": len({page["case_key"] for page in pages}),
        "page_count": len(pages),
        "row_count": len(rows),
        "cell_count": len(cells),
        "reconciliation_count": len(checks),
        "reconciliation_passed": sum(check["passed"] for check in checks),
        "reconciliation_review": sum(not check["passed"] for check in checks),
        "review_issue_count": len(issues),
        "open_review_issue_count": sum(issue["status"] == "open" for issue in issues),
        "ocr_word_coordinates": {
            "page_count": len(ocr_pages),
            "row_count": len(ocr_materialized_rows),
            "cell_count": len(ocr_materialized_cells),
            "null_row_bbox_count": sum(row["bbox"] is None for row in ocr_materialized_rows),
            "null_cell_bbox_count": sum(cell["bbox"] is None for cell in ocr_materialized_cells),
            "minimum_row_confidence": min(row["ocr_confidence"] for row in ocr_materialized_rows),
            "mean_row_confidence": round(sum(row["ocr_confidence"] for row in ocr_materialized_rows) / len(ocr_materialized_rows), 3),
            "low_confidence_row_count": sum(row["ocr_confidence"] < 80 for row in ocr_materialized_rows),
            "low_confidence_cell_count": sum(cell["ocr_confidence"] < 80 for cell in ocr_materialized_cells),
        },
        "rows_by_case": dict(sorted((key, sum(row["case_key"] == key for row in rows)) for key in {row["case_key"] for row in rows})),
    }
    write_json(args.out / "representative-source-pages.json", {"schema_version": 1, "records": pages})
    write_json(args.out / "representative-source-rows.json", {"schema_version": 1, "records": rows})
    write_json(args.out / "representative-source-cells.json", {"schema_version": 1, "records": cells})
    write_json(args.out / "reconciliation-results.json", {"schema_version": 1, "records": checks})
    write_json(args.out / "review-issues.json", {"schema_version": 1, "records": issues})
    write_json(args.out / "spike-summary.json", summary)


if __name__ == "__main__":
    main()

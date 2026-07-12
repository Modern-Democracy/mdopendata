#!/usr/bin/env python3
"""Extract raw row and value records from Charlottetown budget table manifest.

The output is intentionally raw-first. It preserves page text lines and detected
numeric tokens without assigning normalized account, fund, or budget semantics.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median

import pdfplumber


VALUE_RE = re.compile(
    r"""
    (?P<rate>\$?\d+(?:\.\d+)?\s*/\s*(?:day|metre3|meter|100))
    |(?P<currency>\$\s*\(?-?(?:\d[\d,]*(?:\.\d+)?|\.\d+)\)?)
    |(?P<paren>\(-?\d[\d,]*(?:\.\d+)?\))
    |(?P<percent>-?\d+(?:\.\d+)?%)
    |(?P<number>\b-?\d{1,3}(?:,\s*\d{3})+(?:\.\d+)?\b|\b-?\d+\.\d+\b)
    """,
    re.IGNORECASE | re.VERBOSE,
)

ALIGNED_VALUE_RE = re.compile(r"(?<![\w,.(])(?:- -|--|-|\d{1,3})(?![\w,.%)])")
GRID_VALUE_RE = re.compile(r"^(?:- -|--|-|\$?\(?-?\d[\d,]*(?:\.\d+)?\)?)$")

# These two 2025/2026 pages share a debt schedule layout whose zero and dash
# cells are positioned in separate columns.  Line-level text extraction loses
# those cells, so retain the PDF coordinate grid for this approved page pair.
DEBT_GRID_PAGE_NUMBERS = {147, 149}


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def classify_value(raw: str) -> str:
    lower = raw.lower()
    if "%" in raw:
        return "percent"
    if "/" in raw or "day" in lower or "metre" in lower or "meter" in lower:
        return "rate"
    if "$" in raw:
        return "currency"
    if raw in {"-", "- -"}:
        return "dash"
    return "number"


def parse_decimal(raw: str) -> str | None:
    cleaned = raw.strip()
    if cleaned in {"-", "- -"}:
        return None
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r"[$,%]", "", cleaned)
    cleaned = re.sub(r"\s*/\s*(day|metre3|meter|100)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").replace(" ", "").strip()
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if negative:
        value = -value
    return format(value, "f")


def split_cells(raw_line: str) -> list[str]:
    cells = [cell.strip() for cell in re.split(r"\s{2,}", raw_line.strip()) if cell.strip()]
    return cells or [raw_line.strip()]


def is_page_number_line(line: str, page_number: int) -> bool:
    return line.strip() == str(page_number)


def row_kind(raw_text: str, values: list[dict[str, object]]) -> str:
    stripped = raw_text.strip()
    if not stripped:
        return "blank"
    if values and len(values) >= 2:
        return "data_or_total"
    if values:
        return "data_or_amount"
    if stripped.endswith(":"):
        return "heading"
    if stripped.isupper() and len(stripped) > 3:
        return "heading"
    return "label_or_heading"


def recover_aligned_values(
    rows: list[dict[str, object]], values: list[dict[str, object]], manifest_records: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Recover small integers and dashes only at inferred financial columns."""
    values_by_row: dict[str, list[dict[str, object]]] = defaultdict(list)
    for value in values:
        values_by_row[str(value["row_id"])].append(value)
    rows_by_table: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        rows_by_table[str(row["table_id"])].append(row)

    for table in manifest_records:
        table_id = str(table["table_id"])
        expected = max(1, len(table.get("columns_observed") or []) - 1)
        complete = []
        for row in rows_by_table[table_id]:
            current = sorted(values_by_row[str(row["row_id"])], key=lambda item: int(item["char_start"]))
            if len(current) == expected:
                complete.append(current)
        if not complete:
            continue
        anchors = [median(int(row_values[index]["char_end"]) for row_values in complete) for index in range(expected)]
        tolerance = 4 if len(anchors) == 1 else max(4, int(min(b - a for a, b in zip(anchors, anchors[1:])) / 2) + 1)
        for row in rows_by_table[table_id]:
            row_id = str(row["row_id"])
            raw_line = str(row["raw_text"])
            current = values_by_row[row_id]
            occupied = [(int(item["char_start"]), int(item["char_end"])) for item in current]
            candidates = []
            for match in ALIGNED_VALUE_RE.finditer(raw_line):
                if any(match.start() < end and match.end() > start for start, end in occupied):
                    continue
                nearest = min(range(len(anchors)), key=lambda index: abs(match.end() - anchors[index]))
                if abs(match.end() - anchors[nearest]) <= tolerance:
                    candidates.append((match.group(0), match.start(), match.end()))
            for raw_value, char_start, char_end in candidates:
                current.append({
                    "row_id": row_id, "table_id": table_id, "page_number": row["page_number"],
                    "row_index": row["row_index"], "physical_line_number": row["physical_line_number"],
                    "raw_value": raw_value, "parsed_decimal": parse_decimal(raw_value),
                    "value_kind": classify_value(raw_value), "char_start": char_start, "char_end": char_end,
                    "detection_method": "aligned_column_recovery",
                })
            current.sort(key=lambda item: int(item["char_start"]))
            for index, item in enumerate(current, start=1):
                item["value_index"] = index
                item["value_id"] = f"{row_id}_v{index:02d}"
            row["value_count"] = len(current)
            row["value_ids"] = [item["value_id"] for item in current]
            row["row_kind"] = row_kind(raw_line, current)
    rebuilt = [item for row in rows for item in values_by_row[str(row["row_id"])]]
    return rows, rebuilt


def extract_rows(manifest_path: Path, raw_pages_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    manifest = load_json(manifest_path)
    rows: list[dict[str, object]] = []
    values: list[dict[str, object]] = []

    for table in manifest["records"]:
        table_id = table["table_id"]
        page_number = table["page_start"]
        page_text_path = raw_pages_dir / f"page-{page_number:03d}.txt"
        text = page_text_path.read_text(encoding="utf-8")
        row_index = 0
        for physical_line_number, raw_line in enumerate(text.splitlines(), start=1):
            if not raw_line.strip() or is_page_number_line(raw_line, page_number):
                continue
            row_index += 1
            row_id = f"{table_id}_r{row_index:03d}"
            detected_values: list[dict[str, object]] = []
            matches = list(VALUE_RE.finditer(raw_line))
            token_positions = [(match.group(0).strip(), match.start(), match.end()) for match in matches]
            for value_index, (raw_value, char_start, char_end) in enumerate(token_positions, start=1):
                value_record = {
                    "value_id": f"{row_id}_v{value_index:02d}",
                    "row_id": row_id,
                    "table_id": table_id,
                    "page_number": page_number,
                    "row_index": row_index,
                    "physical_line_number": physical_line_number,
                    "value_index": value_index,
                    "raw_value": raw_value,
                    "parsed_decimal": parse_decimal(raw_value),
                    "value_kind": classify_value(raw_value),
                    "char_start": char_start,
                    "char_end": char_end,
                    "detection_method": "regex",
                }
                detected_values.append(value_record)
                values.append(value_record)

            rows.append(
                {
                    "row_id": row_id,
                    "table_id": table_id,
                    "page_number": page_number,
                    "row_index": row_index,
                    "physical_line_number": physical_line_number,
                    "raw_text": raw_line.rstrip(),
                    "trimmed_text": raw_line.strip(),
                    "indentation_spaces": len(raw_line) - len(raw_line.lstrip(" ")),
                    "cells": split_cells(raw_line),
                    "value_count": len(detected_values),
                    "value_ids": [value["value_id"] for value in detected_values],
                    "row_kind": row_kind(raw_line, detected_values),
                }
            )

    return recover_aligned_values(rows, values, manifest["records"])


def visible_pdf_object(item: dict[str, object]) -> bool:
    """Exclude transparent PDF glyphs used as layout placeholders."""
    if item.get("object_type") != "char":
        return True
    colour = item.get("non_stroking_color")
    return not (isinstance(colour, tuple) and len(colour) == 4 and colour[-1] == 0)


def visible_pdf_word_lines(page: object) -> list[list[dict[str, object]]]:
    """Group visible PDF words into rendered lines."""
    words = page.extract_words(x_tolerance=1, y_tolerance=1)
    lines: list[list[dict[str, object]]] = []
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        if not lines or abs(float(word["top"]) - float(lines[-1][0]["top"])) > 2:
            lines.append([word])
        else:
            lines[-1].append(word)
    return lines


def visible_pdf_lines(word_lines: list[list[dict[str, object]]]) -> list[str]:
    """Rebuild visible lines while retaining the large gaps between value columns."""
    output = []
    for words_on_line in word_lines:
        ordered = sorted(words_on_line, key=lambda item: float(item["x0"]))
        text = str(ordered[0]["text"])
        previous = ordered[0]
        for word in ordered[1:]:
            gap = float(word["x0"]) - float(previous["x1"])
            token = str(word["text"])
            if gap > 1.5 and not token.startswith(","):
                text += " "
            text += token
            previous = word
        output.append(text)
    return output


def debt_grid_anchors(word_lines: list[list[dict[str, object]]]) -> list[float] | None:
    """Locate the Balance, Principal, Interest, and Comments column starts."""
    for words_on_line in word_lines:
        by_text = {str(word["text"]).lower(): float(word["x0"]) for word in words_on_line}
        if all(label in by_text for label in ("balance", "principal", "interest", "comments")):
            return [by_text[label] for label in ("balance", "principal", "interest", "comments")]
    return None


def debt_grid_cells(words_on_line: list[dict[str, object]], anchors: list[float]) -> list[str]:
    """Return non-empty numeric debt cells using header-derived coordinate columns."""
    first_column_left = anchors[0] - (anchors[1] - anchors[0])
    numeric_words = [
        word for word in sorted(words_on_line, key=lambda item: float(item["x0"]))
        if float(word["x0"]) >= first_column_left and GRID_VALUE_RE.fullmatch(str(word["text"]))
    ]
    cells: list[tuple[str, float]] = []
    for word in numeric_words:
        text = str(word["text"])
        x0, x1 = float(word["x0"]), float(word["x1"])
        # PDF column rules can split the leading digit from the remainder of
        # a comma-formatted value at the exact same x coordinate boundary.
        if cells and x0 - cells[-1][1] <= 1.5 and "," in text and cells[-1][0].isdigit():
            cells[-1] = (cells[-1][0] + text, x1)
        else:
            cells.append((text, x1))
    return [text for text, _ in cells]


def coordinate_rows(
    manifest_path: Path, pdf_path: Path, prior_rows_path: Path | None, prior_values_path: Path | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Extract rendered text lines from visible PDF glyphs for raw-source regeneration."""
    manifest = load_json(manifest_path)
    prior_by_table: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    prior_rows_by_table: dict[str, list[dict[str, object]]] = defaultdict(list)
    prior_values_by_row: dict[str, list[dict[str, object]]] = defaultdict(list)
    if prior_rows_path and prior_rows_path.exists():
        for row in load_json(prior_rows_path)["records"]:
            prior_by_table[str(row["table_id"])][str(row["trimmed_text"])].append(str(row["row_id"]))
            prior_rows_by_table[str(row["table_id"])].append(row)
    if prior_values_path and prior_values_path.exists():
        for value in load_json(prior_values_path)["records"]:
            prior_values_by_row[str(value["row_id"])].append(value)

    rows: list[dict[str, object]] = []
    values: list[dict[str, object]] = []
    reused_row_ids = 0
    new_row_ids = 0
    fallback_table_count = 0
    with pdfplumber.open(pdf_path) as document:
        for table in manifest["records"]:
            table_id = str(table["table_id"])
            page_number = int(table["page_start"])
            page = document.pages[page_number - 1].filter(visible_pdf_object)
            word_lines = visible_pdf_word_lines(page)
            visible_lines = [line.strip() for line in visible_pdf_lines(word_lines) if line.strip()]
            if not visible_lines or all(line.isdigit() for line in visible_lines):
                fallback_rows = prior_rows_by_table[table_id]
                if not fallback_rows:
                    raise ValueError(f"No visible PDF text or prior raw rows for {table_id}")
                fallback_table_count += 1
                for prior_row in fallback_rows:
                    row = dict(prior_row)
                    row["extraction_method"] = "preextracted_text_fallback"
                    rows.append(row)
                    for prior_value in prior_values_by_row[str(row["row_id"])]:
                        value = dict(prior_value)
                        value["detection_method"] = "preextracted_text_fallback"
                        values.append(value)
                reused_row_ids += len(fallback_rows)
                continue
            prior_by_text = prior_by_table[table_id]
            row_index = 0
            grid_anchors = debt_grid_anchors(word_lines) if page_number in DEBT_GRID_PAGE_NUMBERS else None
            grid_active = False
            for physical_line_number, (source_line, words_on_line) in enumerate(zip(visible_lines, word_lines), start=1):
                raw_line = re.sub(r"(?<=\d)\s+,(?=\d)", ",", source_line).rstrip()
                # Printed page folios are source-layout artifacts, not table rows.  The
                # manifest page number can differ from the printed footer number.
                if not raw_line.strip() or is_page_number_line(raw_line, page_number) or raw_line.strip().isdigit():
                    continue
                row_index += 1
                trimmed = raw_line.strip()
                reusable = prior_by_text.get(trimmed, [])
                if reusable:
                    row_id = reusable.pop(0)
                    reused_row_ids += 1
                else:
                    row_id = f"{table_id}_coord_r{row_index:03d}"
                    new_row_ids += 1
                detected_values: list[dict[str, object]] = []
                label_end = None
                if grid_anchors and "Balance Principal Interest Comments" in raw_line:
                    grid_active = True
                grid_values = debt_grid_cells(words_on_line, grid_anchors) if grid_active and grid_anchors else []
                token_positions = (
                    [(value, raw_line.find(value), raw_line.find(value) + len(value), "pdf_visible_coordinate_cell_grid")
                     for value in grid_values]
                    if grid_values
                    else [(match.group(0).strip(), match.start(), match.end(), "pdf_visible_coordinate_text")
                          for match in VALUE_RE.finditer(raw_line)]
                )
                for value_index, (raw_value, char_start, char_end, detection_method) in enumerate(token_positions, start=1):
                    # Parenthesized single-digit staffing counts are part of a label,
                    # not the start of a financial value column.
                    parsed_value = parse_decimal(raw_value)
                    if label_end is None and not (
                        raw_value.startswith("(") and parsed_value is not None
                        and abs(Decimal(parsed_value)) < 100
                    ):
                        label_end = char_start
                    value = {
                        "value_id": f"{row_id}_v{value_index:02d}", "row_id": row_id,
                        "table_id": table_id, "page_number": page_number, "row_index": row_index,
                        "physical_line_number": physical_line_number, "value_index": value_index,
                        "raw_value": raw_value, "parsed_decimal": parse_decimal(raw_value),
                        "value_kind": classify_value(raw_value), "char_start": char_start,
                        "char_end": char_end, "detection_method": detection_method,
                    }
                    detected_values.append(value)
                    values.append(value)
                raw_label = raw_line[:label_end].strip() if label_end is not None else trimmed
                rows.append({
                    "row_id": row_id, "table_id": table_id, "page_number": page_number,
                    "row_index": row_index, "physical_line_number": physical_line_number,
                    "raw_text": raw_line, "trimmed_text": trimmed,
                    "indentation_spaces": len(raw_line) - len(raw_line.lstrip(" ")),
                    "cells": [raw_label] + [value["raw_value"] for value in detected_values],
                    "value_ids": [value["value_id"] for value in detected_values],
                    "row_kind": row_kind(raw_line, detected_values),
                    "extraction_method": "pdf_visible_coordinate_text",
                })
    report = {
        "schema_version": 1, "extraction_method": "pdf_visible_coordinate_text",
        "row_count": len(rows), "value_count": len(values), "reused_row_id_count": reused_row_ids,
        "new_row_id_count": new_row_ids, "preextracted_text_fallback_table_count": fallback_table_count,
    }
    return rows, values, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--raw-pages", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--pdf", type=Path, help="use visible PDF glyphs rather than pre-extracted page text")
    parser.add_argument("--prior-rows", type=Path, help="prior source_table_rows.json for exact-line ID reuse")
    parser.add_argument("--prior-values", type=Path, help="prior source_values.json for no-text fallback tables")
    args = parser.parse_args()

    coordinate_report = None
    if args.pdf:
        rows, values, coordinate_report = coordinate_rows(args.manifest, args.pdf, args.prior_rows, args.prior_values)
    else:
        rows, values = extract_rows(args.manifest, args.raw_pages)
    source_pdf = load_json(args.manifest)["source_pdf"]
    manifest_records = load_json(args.manifest)["records"]

    row_payload = {
        "schema_version": 1,
        "source_pdf": source_pdf,
        "source_manifest": str(args.manifest.as_posix()),
        "table_count": len(manifest_records),
        "row_count": len(rows),
        "records": rows,
    }
    value_payload = {
        "schema_version": 1,
        "source_pdf": source_pdf,
        "source_manifest": str(args.manifest.as_posix()),
        "table_count": len(manifest_records),
        "value_count": len(values),
        "records": values,
    }
    summary_payload = {
        "schema_version": 1,
        "source_pdf": source_pdf,
        "source_manifest": str(args.manifest.as_posix()),
        "table_count": len(manifest_records),
        "row_count": len(rows),
        "value_count": len(values),
        "rows_by_table_type": count_rows_by_table_type(rows, manifest_records),
        "values_by_kind": count_by(values, "value_kind"),
        "values_by_detection_method": count_by(values, "detection_method"),
    }

    write_json(args.out / "source_table_rows.json", row_payload)
    write_json(args.out / "source_values.json", value_payload)
    write_json(args.out / "raw_row_value_summary.json", summary_payload)
    if coordinate_report is not None:
        write_json(args.out / "coordinate-extraction-reconciliation.json", coordinate_report)


def count_by(records: list[dict[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def count_rows_by_table_type(
    rows: list[dict[str, object]], manifest_records: list[dict[str, object]]
) -> dict[str, int]:
    table_type_by_id = {str(record["table_id"]): str(record["table_type"]) for record in manifest_records}
    counts: dict[str, int] = {}
    for row in rows:
        table_type = table_type_by_id[str(row["table_id"])]
        counts[table_type] = counts.get(table_type, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()

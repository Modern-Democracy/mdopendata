#!/usr/bin/env python3
"""Extract raw row and value records from Charlottetown budget table manifest.

The output is intentionally raw-first. It preserves page text lines and detected
numeric tokens without assigning normalized account, fund, or budget semantics.
"""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


VALUE_RE = re.compile(
    r"""
    (?P<rate>\$?\d+(?:\.\d+)?\s*/\s*(?:day|metre3|meter|100))
    |(?P<currency>\$\s*\(?-?\d[\d,]*(?:\.\d+)?\)?)
    |(?P<paren>\(-?\d[\d,]*(?:\.\d+)?\))
    |(?P<percent>-?\d+(?:\.\d+)?%)
    |(?P<number>\b-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b-?\d+\.\d+\b)
    """,
    re.IGNORECASE | re.VERBOSE,
)


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
    return "number"


def parse_decimal(raw: str) -> str | None:
    cleaned = raw.strip()
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r"[$,%]", "", cleaned)
    cleaned = re.sub(r"\s*/\s*(day|metre3|meter|100)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").strip()
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
            for value_index, match in enumerate(VALUE_RE.finditer(raw_line), start=1):
                raw_value = match.group(0).strip()
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
                    "char_start": match.start(),
                    "char_end": match.end(),
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

    return rows, values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--raw-pages", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

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
    }

    write_json(args.out / "source_table_rows.json", row_payload)
    write_json(args.out / "source_values.json", value_payload)
    write_json(args.out / "raw_row_value_summary.json", summary_payload)


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

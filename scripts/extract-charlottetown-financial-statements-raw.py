#!/usr/bin/env python3
"""Generate deterministic Gate 5 raw table artifacts for eight financial statements.

The extractor validates Gate 1 hashes, uses Gate 2 table-page and rotation
decisions, and emits raw coordinate evidence only. It does not write a database
or assign normalized financial semantics.
"""

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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image


SCHEMA_VERSION = 1
RENDER_DPI = 220
LOW_CONFIDENCE = 80.0
YEAR_TOKEN_RE = re.compile(r"^(?:19|20)\d{2}$")
AMOUNT_TOKEN_RE = re.compile(
    r"^\$?\s*(?:\(\s*)?-?\s*\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*\)?$"
)
INTEGER_TOKEN_RE = re.compile(r"^\$?\s*(?:\(\s*)?-?\s*\d+(?:\.\d+)?\s*\)?$")
DASH_TOKEN_RE = re.compile(r"^(?:\$\s*)?[-–—]+$")


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(*parts: object, length: int = 20) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:length]


def command_text(args: list[str]) -> str:
    return subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def locate_tools() -> tuple[str, str]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise RuntimeError("pdftotext is unavailable")
    sibling = Path(pdftotext).resolve().parent / "pdftoppm.exe"
    pdftoppm = str(sibling) if sibling.exists() else shutil.which("pdftoppm")
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


def normalized_bbox(x0: int, top: int, x1: int, bottom: int, width: int, height: int) -> list[float]:
    return [
        round(x0 / width, 6),
        round(top / height, 6),
        round(x1 / width, 6),
        round(bottom / height, 6),
    ]


def token_class(raw_text: str) -> str:
    value = re.sub(r"\s+", " ", raw_text).strip()
    if YEAR_TOKEN_RE.fullmatch(value):
        return "year_or_reference"
    if DASH_TOKEN_RE.fullmatch(value):
        return "dash_candidate"
    if AMOUNT_TOKEN_RE.fullmatch(value) or INTEGER_TOKEN_RE.fullmatch(value):
        if value.startswith("(") or value.endswith(")") or re.search(r"-\s*\d", value):
            return "signed_amount_candidate"
        return "amount_candidate"
    return "text"


def split_cells(words: list[dict[str, object]], gap: int = 55) -> list[list[dict[str, object]]]:
    cells: list[list[dict[str, object]]] = []
    for word in words:
        if not cells or int(word["x0"]) - int(cells[-1][-1]["x1"]) > gap:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def extract_table_page(
    root: Path,
    document: dict[str, object],
    table: dict[str, object],
    profile_page: dict[str, object],
    pdftoppm: str,
    tesseract: str,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    document_key = str(document["document_key"])
    page_number = int(table["page_number"])
    page_key = str(table["page_key"])
    table_key = str(table["table_key"])
    rotation = int(profile_page["ocr_rotation_degrees"])
    pdf = root / str(document["source_file"])

    with tempfile.TemporaryDirectory(prefix=f"{page_key}-raw-") as temp_name:
        prefix = Path(temp_name) / "page"
        subprocess.run(
            [
                pdftoppm,
                "-f", str(page_number), "-l", str(page_number),
                "-png", "-r", str(RENDER_DPI), "-singlefile",
                str(pdf), str(prefix),
            ],
            check=True,
            capture_output=True,
        )
        image_path = prefix.with_suffix(".png")
        if rotation:
            rotated_path = Path(temp_name) / "page-rotated.png"
            with Image.open(image_path) as source:
                source.rotate(rotation, expand=True, fillcolor="white").save(rotated_path)
            image_path = rotated_path
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
        bbox = normalized_bbox(
            min(int(word["x0"]) for word in line),
            min(int(word["top"]) for word in line),
            max(int(word["x1"]) for word in line),
            max(int(word["bottom"]) for word in line),
            width,
            height,
        )
        confidence = round(sum(float(word["confidence"]) for word in line) / len(line), 3)
        row_key = f"{table_key}_r_{stable_hash(round(bbox[1], 6), raw_text)}"
        row_cells: list[dict[str, object]] = []
        for column_index, cell_words in enumerate(split_cells(line)):
            cell_text = " ".join(str(word["text"]) for word in cell_words)
            cell_bbox = normalized_bbox(
                min(int(word["x0"]) for word in cell_words),
                min(int(word["top"]) for word in cell_words),
                max(int(word["x1"]) for word in cell_words),
                max(int(word["bottom"]) for word in cell_words),
                width,
                height,
            )
            cell_confidence = round(
                sum(float(word["confidence"]) for word in cell_words) / len(cell_words), 3
            )
            classification = token_class(cell_text)
            cell = {
                "cell_key": f"{row_key}_c{column_index:02d}_{stable_hash(cell_text, cell_bbox)}",
                "document_key": document_key,
                "page_key": page_key,
                "table_key": table_key,
                "row_key": row_key,
                "column_index": column_index,
                "raw_text": cell_text,
                "bbox": cell_bbox,
                "token_class": classification,
                "parse_status": "unparsed",
                "parser_confidence": cell_confidence,
                "review_status": "needs_review" if cell_confidence < LOW_CONFIDENCE else "unreviewed",
            }
            row_cells.append(cell)
            cells.append(cell)
        value_cells = [cell for cell in row_cells if cell["token_class"] in {
            "amount_candidate", "signed_amount_candidate", "dash_candidate"
        }]
        label_cells = [cell["raw_text"] for cell in row_cells[: row_cells.index(value_cells[0])] ] if value_cells else []
        rows.append(
            {
                "row_key": row_key,
                "document_key": document_key,
                "page_key": page_key,
                "table_key": table_key,
                "row_index": row_index,
                "raw_text": raw_text,
                "raw_label_candidate": " ".join(label_cells).strip() or None,
                "raw_value_cell_keys": [cell["cell_key"] for cell in value_cells],
                "raw_values": [cell["raw_text"] for cell in value_cells],
                "bbox": bbox,
                "extraction_method": "ocr_tesseract_word_tsv",
                "parser_confidence": confidence,
                "review_status": "needs_review" if confidence < LOW_CONFIDENCE else "unreviewed",
            }
        )

    page = {
        "page_key": page_key,
        "document_key": document_key,
        "table_key": table_key,
        "source_file": document["source_file"],
        "source_sha256": document["sha256"],
        "pdf_page_number": page_number,
        "printed_page_label": profile_page["printed_page_label"],
        "table_family": table["table_family"],
        "profile_statement_class": table["statement_class"],
        "profile_confidence": table["confidence"],
        "profile_rotation_degrees": rotation,
        "continuation_candidate": table["continuation_candidate"],
        "continuation_of_page_key": table["continuation_of_page_key"],
        "render_dpi": RENDER_DPI,
        "width_pixels": width,
        "height_pixels": height,
        "extractor_psm": 4,
        "extraction_method": "ocr_tesseract_word_tsv",
        "row_count": len(rows),
        "cell_count": len(cells),
    }
    return page, rows, cells


def build_columns(table_key: str, cells: list[dict[str, object]]) -> list[dict[str, object]]:
    counts = Counter(int(cell["column_index"]) for cell in cells)
    return [
        {
            "column_key": f"{table_key}_c{index:02d}",
            "table_key": table_key,
            "column_index": index,
            "raw_header": None,
            "column_role": "unknown",
            "observed_cell_count": counts[index],
            "review_status": "needs_review",
        }
        for index in sorted(counts)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("data/financial-statements/charlottetown/source-document-registry.json"))
    parser.add_argument("--out", type=Path, default=Path("data/financial-statements/charlottetown"))
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    registry_path = args.registry if args.registry.is_absolute() else root / args.registry
    out_root = args.out if args.out.is_absolute() else root / args.out
    registry = read_json(registry_path)
    pdftoppm, tesseract = locate_tools()
    extractor_version = command_text([tesseract, "--version"]).splitlines()[0]
    all_pages: list[dict[str, object]] = []
    all_rows: list[dict[str, object]] = []
    all_cells: list[dict[str, object]] = []
    all_columns: list[dict[str, object]] = []

    for document in registry["documents"]:
        document_key = str(document["document_key"])
        source = root / str(document["source_file"])
        if sha256_file(source) != document["sha256"]:
            raise RuntimeError(f"{document_key}: SHA-256 differs from Gate 1")
        document_root = out_root / document_key
        table_manifest = read_json(document_root / "table_manifest.json")["records"]
        inventory = {
            int(page["page_number"]): page
            for page in read_json(document_root / "page_inventory.json")["records"]
        }
        tasks = [
            (root, document, table, inventory[int(table["page_number"])], pdftoppm, tesseract)
            for table in table_manifest
        ]
        print(f"Extracting {document_key}: {len(tasks)} table pages", flush=True)
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            results = list(executor.map(lambda values: extract_table_page(*values), tasks))
        pages = [page for page, _, _ in results]
        rows = [row for _, page_rows, _ in results for row in page_rows]
        cells = [cell for _, _, page_cells in results for cell in page_cells]
        by_table_cells: dict[str, list[dict[str, object]]] = {}
        for cell in cells:
            by_table_cells.setdefault(str(cell["table_key"]), []).append(cell)
        columns = [
            column
            for table_key in sorted(by_table_cells)
            for column in build_columns(table_key, by_table_cells[table_key])
        ]
        raw_root = document_root / "raw-tables"
        write_json(raw_root / "source_table_pages.json", {"schema_version": SCHEMA_VERSION, "records": pages})
        write_json(raw_root / "source_table_columns.json", {"schema_version": SCHEMA_VERSION, "records": columns})
        write_json(raw_root / "source_table_rows.json", {"schema_version": SCHEMA_VERSION, "records": rows})
        write_json(raw_root / "source_table_cells.json", {"schema_version": SCHEMA_VERSION, "records": cells})
        all_pages.extend(pages)
        all_columns.extend(columns)
        all_rows.extend(rows)
        all_cells.extend(cells)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "financial_statement_raw_extraction_summary",
        "gate": 5,
        "status": "complete",
        "extractor_version": extractor_version,
        "render_dpi": RENDER_DPI,
        "extractor_psm": 4,
        "counts": {
            "documents": len(registry["documents"]),
            "registered_pdf_pages": sum(int(document["page_count"]) for document in registry["documents"]),
            "extracted_table_pages": len(all_pages),
            "source_columns": len(all_columns),
            "source_rows": len(all_rows),
            "source_cells": len(all_cells),
            "value_candidate_cells": sum(cell["token_class"] in {"amount_candidate", "signed_amount_candidate", "dash_candidate"} for cell in all_cells),
            "low_confidence_rows": sum(float(row["parser_confidence"]) < LOW_CONFIDENCE for row in all_rows),
            "low_confidence_cells": sum(float(cell["parser_confidence"]) < LOW_CONFIDENCE for cell in all_cells),
            "rotated_table_pages": sum(int(page["profile_rotation_degrees"]) != 0 for page in all_pages),
            "database_writes": 0,
        },
        "documents": [
            {
                "document_key": document["document_key"],
                "table_pages": sum(page["document_key"] == document["document_key"] for page in all_pages),
                "rows": sum(row["document_key"] == document["document_key"] for row in all_rows),
                "cells": sum(cell["document_key"] == document["document_key"] for cell in all_cells),
            }
            for document in registry["documents"]
        ],
        "operational_boundary": {
            "raw_database_imported": False,
            "normalized_records_created": 0,
            "publication_changes": 0,
        },
    }
    if summary["counts"]["extracted_table_pages"] != 139:
        raise RuntimeError("Gate 2 table-page count changed")
    write_json(out_root / "gate-5-raw-extraction-summary.json", summary)
    print(
        f"Extracted {len(all_pages)} table pages, {len(all_rows)} rows, and {len(all_cells)} cells",
        flush=True,
    )


if __name__ == "__main__":
    main()

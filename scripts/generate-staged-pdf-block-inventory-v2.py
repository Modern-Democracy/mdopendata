#!/usr/bin/env python3
"""Generate a deterministic version 2 Stage 1 block inventory from Stage 0 evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT
    / "data"
    / "budget"
    / "charlottetown"
    / "2026-2027"
    / "staged-pdf"
    / "v1"
    / "stage-0"
    / "source-evidence.json"
)
DEFAULT_OUT = DEFAULT_SOURCE.parents[1] / "stage-1"
VALIDATOR_PATH = ROOT / "scripts" / "validate-staged-pdf-artifacts.py"
GENERATOR_NAME = "staged-pdf-block-inventory"
GENERATOR_VERSION = "5"
CONFIG = {
    "generator_version": GENERATOR_VERSION,
    "body_top": 0.18,
    "footer_top": 0.91,
    "sparse_page_word_limit": 15,
    "financial_numeric_minimum": 8,
    "geometry_source": "stage-0-word-evidence",
    "table_row_tolerance_factor": 0.65,
    "table_minimum_row_tolerance": 0.004,
    "table_cell_gap": 0.008,
}

NUMBER_RE = re.compile(r"(?:[$%]?[-+]?\d[\d,]*(?:\.\d+)?|\d{4}/\d{2,4})")
FINANCIAL_RE = re.compile(
    r"\b(?:budget|revenue|expense|expenditure|forecast|variance|assessment|rate|tax|debt|capital|operating|principal|interest)\b",
    re.IGNORECASE,
)
TABLE_NUMBER_RE = re.compile(r"^(?:[$â‚¬Â£]?\(?[-+]?\d[\d,]*(?:\.\d+)?\)?%?|[$â‚¬Â£]|[-â€”])$")
SUBTOTAL_RE = re.compile(r"\bsub[ -]?total\b", re.IGNORECASE)
TOTAL_RE = re.compile(r"\b(?:grand\s+)?total\b", re.IGNORECASE)
HEADER_CUE_RE = re.compile(
    r"\b(?:account|actual|approved|budget|category|department|description|forecast|project|variance|year)\b",
    re.IGNORECASE,
)


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("staged_pdf_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schema_reference(output: Path, schema_version: int) -> str:
    schema_name = (
        "staged-pdf-artifacts-v2.schema.json"
        if schema_version == 2
        else "staged-pdf-artifacts.schema.json"
    )
    schema = ROOT / "schema" / "json-schema" / schema_name
    return Path(os.path.relpath(schema, output)).as_posix()


def bounded(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 6)


def union_box(words: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "x0": bounded(min(word["bbox"]["x0"] for word in words)),
        "y0": bounded(min(word["bbox"]["y0"] for word in words)),
        "x1": bounded(max(word["bbox"]["x1"] for word in words)),
        "y1": bounded(max(word["bbox"]["y1"] for word in words)),
    }


def ordered_text(words: list[dict[str, Any]]) -> str:
    ordered = sorted(
        words,
        key=lambda word: (
            word.get("block_number", 0),
            word.get("line_number", 0),
            word.get("word_number", 0),
            word["bbox"]["y0"],
            word["bbox"]["x0"],
        ),
    )
    return " ".join(str(word.get("text", "")).strip() for word in ordered if word.get("text")).strip()


def classify_body(text: str, word_count: int, page_text: str = "") -> tuple[str, bool, str | None, list[str]]:
    lower = text.lower()
    page_lower = page_text.lower()
    numeric_count = len(NUMBER_RE.findall(text))
    financial = bool(FINANCIAL_RE.search(text)) and numeric_count >= CONFIG["financial_numeric_minimum"]
    chart_financial = (
        numeric_count >= 4
        and any(token in page_lower for token in ("revenue", "expense", "expenditure"))
        and text.count("%") >= 3
    )
    financial = financial or chart_financial
    if "table of contents" in page_lower:
        return "table_of_contents", False, None, ["contents-page"]
    profile_cues = sum(
        phrase in lower
        for phrase in ("project name", "department", "project cost", "funding source", "project description", "project timeline")
    )
    if "project" in lower and profile_cues >= 2:
        return "formatted_text", True, "capital_project_profile", ["project-profile-cues"]
    if financial:
        if "assessment" in lower and "rate" in lower:
            family = "tax_assessment_rate"
        elif "debt" in lower and any(token in lower for token in ("principal", "interest", "outstanding")):
            family = "debt_schedule"
        elif "capital" in lower and "project" in lower:
            family = "capital_budget_schedule"
        elif any(token in lower for token in ("forecast", "variance")):
            family = "operating_detail"
        else:
            family = "operating_statement"
        return "table", True, family, ["financial-text-cues", "numeric-density"]
    if word_count <= CONFIG["sparse_page_word_limit"]:
        return "divider", False, None, ["sparse-page"]
    return "formatted_text", False, None, ["prose-density"]


def table_word_rows(words: list[dict[str, Any]], table_bbox: dict[str, float]) -> list[list[dict[str, Any]]]:
    contained = [
        word for word in words
        if table_bbox["x0"] <= (word["bbox"]["x0"] + word["bbox"]["x1"]) / 2 <= table_bbox["x1"]
        and table_bbox["y0"] <= (word["bbox"]["y0"] + word["bbox"]["y1"]) / 2 <= table_bbox["y1"]
        and str(word.get("text", "")).strip()
    ]
    if not contained:
        return []
    heights = sorted(word["bbox"]["y1"] - word["bbox"]["y0"] for word in contained)
    tolerance = max(
        heights[len(heights) // 2] * CONFIG["table_row_tolerance_factor"],
        CONFIG["table_minimum_row_tolerance"],
    )
    rows: list[list[dict[str, Any]]] = []
    row_centres: list[float] = []
    for word in sorted(contained, key=lambda item: (
        (item["bbox"]["y0"] + item["bbox"]["y1"]) / 2,
        item["bbox"]["x0"],
    )):
        centre = (word["bbox"]["y0"] + word["bbox"]["y1"]) / 2
        if not rows or abs(centre - row_centres[-1]) > tolerance:
            rows.append([word])
            row_centres.append(centre)
        else:
            rows[-1].append(word)
            row_centres[-1] = sum(
                (item["bbox"]["y0"] + item["bbox"]["y1"]) / 2 for item in rows[-1]
            ) / len(rows[-1])
    return [sorted(row, key=lambda item: item["bbox"]["x0"]) for row in rows]


def is_table_number(word: dict[str, Any]) -> bool:
    return bool(TABLE_NUMBER_RE.fullmatch(str(word.get("text", "")).strip()))


def split_header_cells(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not words:
        return []
    cells = [[words[0]]]
    widths = sorted(word["bbox"]["x1"] - word["bbox"]["x0"] for word in words)
    gap_threshold = max(CONFIG["table_cell_gap"], widths[len(widths) // 2] * 1.25)
    for word in words[1:]:
        if word["bbox"]["x0"] - cells[-1][-1]["bbox"]["x1"] > gap_threshold:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def split_data_cells(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not words:
        return []
    heights = sorted(word["bbox"]["y1"] - word["bbox"]["y0"] for word in words)
    gap_threshold = max(CONFIG["table_cell_gap"], heights[len(heights) // 2] * 1.25)
    cells = [[words[0]]]
    for word in words[1:]:
        if word["bbox"]["x0"] - cells[-1][-1]["bbox"]["x1"] > gap_threshold:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def cluster_positions(values: list[float], tolerance: float = 0.035) -> list[float]:
    clusters: list[list[float]] = []
    for value in sorted(values):
        if not clusters or value - sum(clusters[-1]) / len(clusters[-1]) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [sum(cluster) / len(cluster) for cluster in clusters]


def table_grid(
    block_key: str,
    words: list[dict[str, Any]],
    table_bbox: dict[str, float],
    *,
    key_prefix: str = "cell",
    review: dict[str, Any] | None = None,
    schema_version: int = 1,
) -> dict[str, Any]:
    rows = table_word_rows(words, table_bbox)
    grid_review = review or {
        "status": "proposed",
        "reason_codes": ["automated-table-grid"],
        "decision_ids": [],
    }
    if not rows:
        return {
            "column_boundaries": [table_bbox["x0"], table_bbox["x1"]],
            "row_boundaries": [table_bbox["y0"], table_bbox["y1"]],
            "cells": [{
                "cell_key": f"{block_key}:{key_prefix}-r001-c001",
                "row_index": 0,
                "column_index": 0,
                "cell_type": "cell",
                "text_excerpt": None,
                "review": copy_review(grid_review),
            }],
            "review": copy_review(grid_review),
        }
    first_data_row = 0
    for row in rows:
        row_text = ordered_text(row)
        if not any(is_table_number(word) for word in row) or HEADER_CUE_RE.search(row_text):
            first_data_row += 1
        else:
            break
    value_starts: list[float] = []
    for row in rows[first_data_row:]:
        numeric_indexes = [index for index, word in enumerate(row) if is_table_number(word)]
        if numeric_indexes:
            value_starts.extend(group[0]["bbox"]["x0"] for group in split_data_cells(row[numeric_indexes[0]:]))
    if not value_starts:
        value_starts.extend(
            group[0]["bbox"]["x0"] for row in rows[:first_data_row] for group in split_header_cells(row)[1:]
        )
    starts = [value for value in cluster_positions(value_starts) if table_bbox["x0"] + .02 < value < table_bbox["x1"] - .02]
    column_centres = [table_bbox["x0"], *starts]
    column_boundaries = [table_bbox["x0"]]
    column_boundaries.extend(bounded((left + right) / 2) for left, right in zip(column_centres, column_centres[1:]))
    column_boundaries.append(table_bbox["x1"])
    row_boundaries = [table_bbox["y0"]]
    row_boundaries.extend(
        bounded((max(word["bbox"]["y1"] for word in upper) + min(word["bbox"]["y0"] for word in lower)) / 2)
        for upper, lower in zip(rows, rows[1:])
    )
    row_boundaries.append(table_bbox["y1"])
    cells: list[dict[str, Any]] = []
    column_count = len(column_boundaries) - 1
    title_row_count = 0
    if schema_version == 2 and column_count > 1 and len(rows) > 1:
        for row in rows[:-1]:
            title_text = ordered_text(row)
            if (
                NUMBER_RE.search(title_text)
                or len(split_header_cells(row)) != 1
                or len(title_text) > 80
                or len(title_text.split()) > 8
            ):
                break
            title_row_count += 1
        later_rows = rows[title_row_count:]
        if not later_rows or not any(
            any(is_table_number(word) for word in row) or len(split_header_cells(row)) > 1
            for row in later_rows
        ):
            title_row_count = 0
    for row_index, row in enumerate(rows):
        if title_row_count and row_index == 0:
            title_cell = {
                "cell_key": f"{block_key}:{key_prefix}-r001-c001",
                "row_index": 0,
                "column_index": 0,
                "column_span": column_count,
                "cell_type": "table_title",
                "text_excerpt": ordered_text([
                    word for title_row in rows[:title_row_count] for word in title_row
                ])[:240] or None,
                "review": copy_review(grid_review),
            }
            if title_row_count > 1:
                title_cell["row_span"] = title_row_count
            cells.append(title_cell)
            continue
        if row_index < title_row_count:
            continue
        row_text = ordered_text(row)
        if row_index < first_data_row:
            cell_type = "table_header" if first_data_row > 1 and row_index == 0 else "column_label"
        elif SUBTOTAL_RE.search(row_text):
            cell_type = "subtotal"
        elif TOTAL_RE.search(row_text):
            cell_type = "total"
        else:
            cell_type = "cell"
        for column_index in range(column_count):
            cell_words = [
                word for word in row
                if column_boundaries[column_index]
                <= (word["bbox"]["x0"] + word["bbox"]["x1"]) / 2
                <= column_boundaries[column_index + 1]
            ]
            resolved_type = "row_label" if cell_type == "cell" and column_index == 0 else cell_type
            excerpt = ordered_text(cell_words)[:240] or None
            cells.append({
                "cell_key": f"{block_key}:{key_prefix}-r{row_index + 1:03d}-c{column_index + 1:03d}",
                "row_index": row_index,
                "column_index": column_index,
                "cell_type": resolved_type,
                "text_excerpt": excerpt,
                "review": copy_review(grid_review),
            })
    return {
        "column_boundaries": column_boundaries,
        "row_boundaries": row_boundaries,
        "cells": cells,
        "review": copy_review(grid_review),
    }


def copy_review(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": review["status"],
        "reason_codes": list(review["reason_codes"]),
        "decision_ids": list(review["decision_ids"]),
    }


def internal_regions(
    block_key: str,
    block_type: str,
    words: list[dict[str, Any]],
    *,
    schema_version: int = 1,
) -> list[dict[str, Any]]:
    if block_type != "formatted_text":
        return []
    grouped: dict[int, list[dict[str, Any]]] = {}
    for word in words:
        grouped.setdefault(int(word.get("block_number", 0)), []).append(word)
    regions: list[dict[str, Any]] = []
    ordered_groups = sorted(
        grouped.values(),
        key=lambda group: (
            min(word["bbox"]["y0"] for word in group),
            min(word["bbox"]["x0"] for word in group),
        ),
    )
    for sequence, group_words in enumerate(
        ordered_groups,
        start=1,
    ):
        text = ordered_text(group_words)
        if not text:
            continue
        if (
            schema_version == 2
            and sequence == 1
            and len(ordered_groups) > 1
            and len(text.split()) <= 12
            and len(text) <= 100
            and not text.endswith((".", ";"))
        ):
            region_type = "title"
        elif re.match(r"^[\u2022\u00b7\u25aa\u25e6*\-]\s*", text):
            region_type = "bullet_list"
        elif re.match(r"^(?:\(?\d+|[A-Za-z])[.)]\s+", text):
            region_type = "sorted_list"
        else:
            region_type = "paragraph"
        regions.append({
            "region_key": f"{block_key}:region-{sequence:03d}",
            "region_type": region_type,
            "bbox": union_box(group_words),
            "text_excerpt": text[:240],
            "review": {"status": "proposed", "reason_codes": ["automated-internal-region"], "decision_ids": []},
        })
    return regions


def record(
    *,
    page: dict[str, Any],
    role: str,
    words: list[dict[str, Any]],
    reading_order: int,
    text_source: str,
    page_text: str,
    forced_type: str | None = None,
    schema_version: int = 1,
) -> dict[str, Any]:
    text = ordered_text(words)
    if forced_type:
        block_type = forced_type
        financial = False
        family = None
        reasons = [f"{forced_type}-position"]
    else:
        block_type, financial, family, reasons = classify_body(text, len(words), page_text)
    low_confidence = text_source == "ocr"
    confidence_level = "low" if low_confidence else "medium"
    confidence_score = 0.55 if low_confidence else (0.9 if forced_type else 0.78)
    review_status = "needs_review" if low_confidence else "proposed"
    review_reasons = ["automated-block-candidate"]
    if text_source == "ocr":
        review_reasons.append("ocr-derived-geometry")
    exclusion = "header_footer" if forced_type in {"header", "footer", "page_number"} else None
    block_key = f'{page["page_key"]}:{role}'
    box = union_box(words)
    return {
        "block_key": block_key,
        "candidate_key": block_key,
        "page_key": page["page_key"],
        "page_number": page["page_number"],
        "bbox": box,
        "polygon": None,
        "reading_order": reading_order,
        "block_type": block_type,
        "table_family_candidate": family,
        "text_source": text_source,
        "financial_candidate": financial,
        "regions": internal_regions(
            block_key, block_type, words, schema_version=schema_version
        ),
        "table_grid": (
            table_grid(block_key, words, box, schema_version=schema_version)
            if block_type == "table"
            else None
        ),
        "anchors": [],
        "confidence": {
            "level": confidence_level,
            "score": confidence_score,
            "reason_codes": reasons,
        },
        "evidence": [{
            "page_key": page["page_key"],
            "page_number": page["page_number"],
            "block_key": block_key,
            "bbox": box,
            "text_excerpt": text[:240] or None,
        }],
        "exclusion_disposition": exclusion,
        "review": {
            "status": review_status,
            "reason_codes": review_reasons,
            "decision_ids": [],
        },
    }


def page_records(
    page: dict[str, Any],
    words: list[dict[str, Any]],
    text_source: str,
    *,
    schema_version: int = 1,
) -> list[dict[str, Any]]:
    page_text = ordered_text(words)
    footer = [word for word in words if word["bbox"]["y0"] >= CONFIG["footer_top"]]
    content = [word for word in words if word not in footer]
    results: list[dict[str, Any]] = []
    if len(content) <= CONFIG["sparse_page_word_limit"]:
        regions = [("body", content, None)]
    else:
        header = [word for word in content if word["bbox"]["y1"] <= CONFIG["body_top"]]
        body = [word for word in content if word not in header]
        regions = [("title", header, "title"), ("body", body, None)]
    if footer:
        footer_text = ordered_text(footer).strip()
        footer_type = "page_number" if re.fullmatch(r"\d{1,3}", footer_text) else "footer"
        regions.append(("footer", footer, footer_type))
    for role, region_words, forced_type in regions:
        if region_words:
            results.append(
                record(
                    page=page,
                    role=role,
                    words=region_words,
                    reading_order=len(results) + 1,
                    text_source=text_source,
                    page_text=page_text,
                    forced_type=forced_type,
                    schema_version=schema_version,
                )
            )
    return results


def generate(*, source_evidence: Path, output: Path) -> tuple[dict[str, Any], str, str]:
    source_evidence = source_evidence.resolve()
    output = output.resolve()
    if not source_evidence.is_file():
        raise FileNotFoundError(source_evidence)
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Output must remain inside the repository: {output}")
    source = read_json(source_evidence)
    if source.get("artifact_type") != "source_evidence":
        raise ValueError("Stage 1 requires a source_evidence artifact")
    schema_version = int(source.get("schema_version", 1))
    if schema_version not in {1, 2}:
        raise ValueError(f"Unsupported source schema version: {schema_version}")
    validator = load_validator()
    source_errors = validator.validate_payload(source)
    if source_errors:
        raise RuntimeError("Invalid Stage 0 source evidence: " + "; ".join(source_errors[:5]))

    records: list[dict[str, Any]] = []
    page_dispositions: list[dict[str, Any]] = []
    for page in source["pages"]:
        use_ocr = page["ocr"]["status"] == "completed"
        evidence_relpath = (
            page["ocr"]["evidence_relpath"] if use_ocr else page["embedded_text"]["evidence_relpath"]
        )
        evidence = read_json(ROOT / evidence_relpath)
        blocks = page_records(
            page,
            evidence.get("words", []),
            "ocr" if use_ocr else "embedded",
            schema_version=schema_version,
        )
        records.extend(blocks)
        needs_review = not blocks or any(block["review"]["status"] == "needs_review" for block in blocks)
        if not blocks:
            status = "needs_review"
            reasons = ["no-word-derived-blocks"]
        elif needs_review:
            status = "needs_review"
            reasons = ["contains-low-confidence-blocks"]
        else:
            status = "inventoried"
            reasons = ["automated-candidate-inventory"]
        page_dispositions.append({
            "page_key": page["page_key"],
            "page_number": page["page_number"],
            "block_keys": [block["block_key"] for block in blocks],
            "status": status,
            "review": {"status": "needs_review" if needs_review else "proposed", "reason_codes": reasons, "decision_ids": []},
        })

    artifact = {
        "$schema": schema_reference(output, schema_version),
        "schema_version": schema_version,
        "artifact_type": "block_inventory",
        "artifact_key": f'{source["document_key"]}:block-inventory:v{schema_version}',
        "document_key": source["document_key"],
        "source_sha256": source["source_sha256"],
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "config_sha256": sha256_bytes(canonical_json_bytes(CONFIG)),
        },
        "upstream_artifacts": [{
            "artifact_type": "source_evidence",
            "artifact_key": source["artifact_key"],
            "sha256": sha256_path(source_evidence),
            **({"schema_version": schema_version} if schema_version == 2 else {}),
        }],
        "page_dispositions": page_dispositions,
        "records": records,
        "relationships": [],
    }
    errors = validator.validate_payload(artifact)
    if errors:
        raise RuntimeError("Generated Stage 1 artifact is invalid: " + "; ".join(errors[:10]))

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="stage-1-", dir=output.parent))
    try:
        artifact_path = temporary / "block-inventory.json"
        artifact_path.write_bytes(canonical_json_bytes(artifact))
        artifact_hash = sha256_path(artifact_path)
        if output.exists():
            existing = output / "block-inventory.json"
            if existing.is_file() and sha256_path(existing) == artifact_hash and len(list(output.iterdir())) == 1:
                return artifact, artifact_hash, "unchanged"
            raise RuntimeError("Stage 1 content conflict. Remove or move the existing output after review.")
        temporary.replace(output)
        return artifact, artifact_hash, "created"
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-evidence", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    artifact, artifact_hash, state = generate(source_evidence=args.source_evidence, output=args.out)
    financial = sum(record["financial_candidate"] for record in artifact["records"])
    review_pages = sum(page["status"] == "needs_review" for page in artifact["page_dispositions"])
    print(
        f"Stage 1 {state}: pages={len(artifact['page_dispositions'])}, "
        f"blocks={len(artifact['records'])}, financial_blocks={financial}, "
        f"review_pages={review_pages}, artifact_sha256={artifact_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

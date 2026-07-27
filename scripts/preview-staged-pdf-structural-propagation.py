#!/usr/bin/env python3
"""Preview deterministic document-scoped Stage 1 structural propagation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf"
SOURCE_PATH = WORKSPACE_ROOT / "v2/stage-0/source-evidence.json"
BLOCK_PATH = WORKSPACE_ROOT / "v2/stage-1/block-inventory.json"
REVIEW_PATH = WORKSPACE_ROOT / "v2/review/review-decisions.json"
GENERATOR_PATH = ROOT / "scripts/generate-staged-pdf-block-inventory-v2.py"
MATCHER_NAME = "document-structural-propagation"
MATCHER_VERSION = "1"
MATCHER_CONFIG = {
    "geometry_tolerance": 0.015,
    "supported_block_types": ["formatted_text", "table"],
    "scope": "current_document",
}
MATCHER_CONFIG_SHA256 = hashlib.sha256(
    json.dumps(MATCHER_CONFIG, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def configure_workspace(schema_version: int = 2) -> None:
    if schema_version != 2:
        raise ValueError("Structural propagation requires a version 2 workspace")
    global SOURCE_PATH, BLOCK_PATH, REVIEW_PATH
    workspace = WORKSPACE_ROOT / "v2"
    SOURCE_PATH = workspace / "stage-0/source-evidence.json"
    BLOCK_PATH = workspace / "stage-1/block-inventory.json"
    REVIEW_PATH = workspace / "review/review-decisions.json"


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("propagation_generator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load generator: {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def effective_span(cell: dict[str, Any], axis: str) -> int:
    return int(cell.get(f"{axis}_span", 1))


def cell_coordinates(cell: dict[str, Any]) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row in range(
            cell["row_index"], cell["row_index"] + effective_span(cell, "row")
        )
        for column in range(
            cell["column_index"],
            cell["column_index"] + effective_span(cell, "column"),
        )
    }


def relative_box(
    box: dict[str, float], parent: dict[str, float]
) -> tuple[float, float, float, float]:
    width = parent["x1"] - parent["x0"]
    height = parent["y1"] - parent["y0"]
    return (
        round((box["x0"] - parent["x0"]) / width, 6),
        round((box["y0"] - parent["y0"]) / height, 6),
        round((box["x1"] - parent["x0"]) / width, 6),
        round((box["y1"] - parent["y0"]) / height, 6),
    )


def pattern_payload(block: dict[str, Any]) -> dict[str, Any]:
    if block["block_type"] == "table":
        grid = block.get("table_grid")
        if not grid:
            raise ValueError("Reviewed source table requires a table grid")
        return {
            "block_type": "table",
            "table_family_candidate": block.get("table_family_candidate"),
            "row_count": len(grid["row_boundaries"]) - 1,
            "column_count": len(grid["column_boundaries"]) - 1,
            "cells": [
                {
                    "row_index": cell["row_index"],
                    "column_index": cell["column_index"],
                    "row_span": effective_span(cell, "row"),
                    "column_span": effective_span(cell, "column"),
                    "cell_type": cell["cell_type"],
                }
                for cell in sorted(
                    grid["cells"],
                    key=lambda item: (
                        item["row_index"],
                        item["column_index"],
                        item["cell_key"],
                    ),
                )
            ],
        }
    if block["block_type"] == "formatted_text":
        return {
            "block_type": "formatted_text",
            "regions": [
                {
                    "region_type": region["region_type"],
                    "relative_bbox": relative_box(region["bbox"], block["bbox"]),
                }
                for region in block["regions"]
            ],
        }
    raise ValueError("Find similar supports reviewed table and formatted-text blocks")


def pattern_sha256(block: dict[str, Any]) -> str:
    return digest_bytes(canonical_bytes(pattern_payload(block)))


def page_words(
    source: dict[str, Any],
    page_number: int,
    cache: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    if page_number in cache:
        return cache[page_number]
    page = next(
        (item for item in source["pages"] if item["page_number"] == page_number),
        None,
    )
    if page is None:
        raise RuntimeError(f"Source evidence has no page {page_number}")
    use_ocr = page["ocr"]["status"] == "completed"
    evidence_relpath = (
        page["ocr"]["evidence_relpath"]
        if use_ocr
        else page["embedded_text"]["evidence_relpath"]
    )
    evidence = read_json(ROOT / evidence_relpath)
    cache[page_number] = evidence.get("words", [])
    return cache[page_number]


def words_in_block(
    words: list[dict[str, Any]], bbox: dict[str, float]
) -> list[dict[str, Any]]:
    return [
        word
        for word in words
        if (word["bbox"]["x0"] + word["bbox"]["x1"]) / 2 >= bbox["x0"]
        and (word["bbox"]["x0"] + word["bbox"]["x1"]) / 2 <= bbox["x1"]
        and (word["bbox"]["y0"] + word["bbox"]["y1"]) / 2 >= bbox["y0"]
        and (word["bbox"]["y0"] + word["bbox"]["y1"]) / 2 <= bbox["y1"]
    ]


def joined_excerpt(cells: list[dict[str, Any]]) -> str | None:
    values = [
        cell["text_excerpt"]
        for cell in sorted(
            cells, key=lambda item: (item["row_index"], item["column_index"])
        )
        if cell.get("text_excerpt")
    ]
    return " ".join(dict.fromkeys(values))[:240] or None


def table_proposal(
    source_block: dict[str, Any],
    target: dict[str, Any],
    words: list[dict[str, Any]],
    generator: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    source_grid = source_block["table_grid"]
    detected = generator.table_grid(
        target["block_key"],
        words,
        target["bbox"],
        key_prefix="propagation-preview",
        schema_version=2,
    )
    source_rows = len(source_grid["row_boundaries"]) - 1
    source_columns = len(source_grid["column_boundaries"]) - 1
    target_rows = len(detected["row_boundaries"]) - 1
    target_columns = len(detected["column_boundaries"]) - 1
    evidence = [
        {
            "kind": "table_dimensions",
            "message": (
                f"source {source_rows}x{source_columns}; "
                f"target evidence {target_rows}x{target_columns}"
            ),
        }
    ]
    mismatches: list[dict[str, Any]] = []
    if source_block.get("table_family_candidate") != target.get(
        "table_family_candidate"
    ):
        mismatches.append(
            {
                "category": "source_authority",
                "severity": "material",
                "message": "Table-family candidates differ.",
            }
        )
    if (source_rows, source_columns) != (target_rows, target_columns):
        mismatches.append(
            {
                "category": "geometry",
                "severity": "material",
                "message": "Target evidence produces a different logical grid size.",
            }
        )
    if mismatches:
        return None, evidence, mismatches

    target_by_coordinate = {
        coordinate: cell
        for cell in detected["cells"]
        for coordinate in cell_coordinates(cell)
    }
    cells: list[dict[str, Any]] = []
    for source_cell in source_grid["cells"]:
        coordinates = sorted(cell_coordinates(source_cell))
        contributing = list(
            {
                target_by_coordinate[coordinate]["cell_key"]: target_by_coordinate[
                    coordinate
                ]
                for coordinate in coordinates
            }.values()
        )
        cell = {
            "cell_key": target_by_coordinate[
                (source_cell["row_index"], source_cell["column_index"])
            ]["cell_key"],
            "row_index": source_cell["row_index"],
            "column_index": source_cell["column_index"],
            "cell_type": source_cell["cell_type"],
            "text_excerpt": joined_excerpt(contributing),
            "review": copy.deepcopy(target["review"]),
        }
        row_span = effective_span(source_cell, "row")
        column_span = effective_span(source_cell, "column")
        if row_span != 1:
            cell["row_span"] = row_span
        if column_span != 1:
            cell["column_span"] = column_span
        cells.append(cell)
    proposal = {
        "row_boundaries": detected["row_boundaries"],
        "column_boundaries": detected["column_boundaries"],
        "cells": cells,
        "review": copy.deepcopy(target["review"]),
    }
    source_signature = [
        (
            cell["row_index"],
            cell["column_index"],
            effective_span(cell, "row"),
            effective_span(cell, "column"),
            cell["cell_type"],
        )
        for cell in source_grid["cells"]
    ]
    target_signature = [
        (
            cell["row_index"],
            cell["column_index"],
            effective_span(cell, "row"),
            effective_span(cell, "column"),
            cell["cell_type"],
        )
        for cell in target["table_grid"]["cells"]
    ]
    if source_signature != target_signature:
        mismatches.append(
            {
                "category": "geometry",
                "severity": "light",
                "message": "Target logical cell structure differs from the reviewed source.",
            }
        )
    return proposal, evidence, mismatches


def formatted_text_proposal(
    source_block: dict[str, Any],
    target: dict[str, Any],
    words: list[dict[str, Any]],
    generator: Any,
) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    detected = generator.internal_regions(
        target["block_key"],
        "formatted_text",
        words_in_block(words, target["bbox"]),
        schema_version=2,
    )
    source_regions = source_block["regions"]
    evidence = [
        {
            "kind": "region_count",
            "message": (
                f"source {len(source_regions)} regions; "
                f"target evidence {len(detected)} regions"
            ),
        }
    ]
    if len(source_regions) != len(detected):
        return None, evidence, [
            {
                "category": "block_count",
                "severity": "material",
                "message": "Target evidence produces a different internal-region count.",
            }
        ]
    proposal = []
    for index, (source_region, detected_region) in enumerate(
        zip(source_regions, detected, strict=True)
    ):
        proposal.append(
            {
                "region_key": (
                    target["regions"][index]["region_key"]
                    if index < len(target["regions"])
                    else f'{target["block_key"]}:propagation-region-{index + 1:03d}'
                ),
                "region_type": source_region["region_type"],
                "bbox": detected_region["bbox"],
                "text_excerpt": detected_region.get("text_excerpt"),
                "review": copy.deepcopy(target["review"]),
            }
        )
    mismatches = []
    if [item["region_type"] for item in target["regions"]] != [
        item["region_type"] for item in proposal
    ]:
        mismatches.append(
            {
                "category": "geometry",
                "severity": "light",
                "message": "Target internal-region classifications differ.",
            }
        )
    return proposal, evidence, mismatches


def rejected_pairs(review: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for event in review.get("events", []):
        if event.get("action") != "reject":
            continue
        for change in event.get("changes", []):
            value = change.get("new_value")
            if (
                change.get("field_path", "").startswith(
                    "/propagation_negative_controls/"
                )
                and isinstance(value, dict)
                and isinstance(value.get("pattern_sha256"), str)
                and isinstance(value.get("target_block_key"), str)
            ):
                pairs.add((value["pattern_sha256"], value["target_block_key"]))
    return pairs


def generate_preview(
    artifact: dict[str, Any],
    source: dict[str, Any],
    review: dict[str, Any],
    source_block_key: str,
) -> dict[str, Any]:
    source_block = next(
        (item for item in artifact["records"] if item["block_key"] == source_block_key),
        None,
    )
    if source_block is None:
        raise ValueError(f"Unknown source_block_key: {source_block_key}")
    if source_block["block_type"] not in MATCHER_CONFIG["supported_block_types"]:
        raise ValueError("Find similar supports table and formatted-text blocks")
    if source_block["review"]["status"] != "approved":
        raise ValueError("Find similar requires an approved source structure")
    pattern_hash = pattern_sha256(source_block)
    negatives = rejected_pairs(review)
    generator = load_generator()
    word_cache: dict[int, list[dict[str, Any]]] = {}
    candidates = []
    for target in artifact["records"]:
        if (
            target["block_key"] == source_block_key
            or target["block_type"] != source_block["block_type"]
        ):
            continue
        words = page_words(source, target["page_number"], word_cache)
        if target["block_type"] == "table":
            if not target.get("table_grid"):
                continue
            proposal, evidence, mismatches = table_proposal(
                source_block, target, words, generator
            )
            proposal_field = "table_grid"
        else:
            proposal, evidence, mismatches = formatted_text_proposal(
                source_block, target, words, generator
            )
            proposal_field = "regions"
        material = any(item["severity"] == "material" for item in mismatches)
        negative = (pattern_hash, target["block_key"]) in negatives
        fit_class = (
            "one_off"
            if negative
            else "material_variation"
            if material
            else "light_variation"
            if mismatches
            else "exact"
        )
        proposal_hash = (
            digest_bytes(canonical_bytes(proposal)) if proposal is not None else None
        )
        candidates.append(
            {
                "target_block_key": target["block_key"],
                "page_number": target["page_number"],
                "fit_class": fit_class,
                "confidence": (
                    0.98
                    if fit_class == "exact"
                    else 0.8
                    if fit_class == "light_variation"
                    else 0.0
                ),
                "matching_evidence": evidence,
                "mismatch_evidence": mismatches,
                "proposal_field": proposal_field,
                "proposal": proposal,
                "proposal_sha256": proposal_hash,
                "applicable": fit_class in {"exact", "light_variation"},
            }
        )
    candidates.sort(key=lambda item: (item["page_number"], item["target_block_key"]))
    return {
        "scope": "current_document",
        "source_block_key": source_block_key,
        "pattern_sha256": pattern_hash,
        "matcher": {
            "name": MATCHER_NAME,
            "version": MATCHER_VERSION,
            "config_sha256": MATCHER_CONFIG_SHA256,
        },
        "candidates": candidates,
    }


def preview_command(command: dict[str, Any]) -> dict[str, Any]:
    if set(command) != {
        "document_key",
        "source_block_key",
        "expected_artifact_sha256",
        "expected_review_artifact_sha256",
    }:
        raise ValueError("Propagation preview contains unsupported or missing fields")
    artifact = read_json(BLOCK_PATH)
    source = read_json(SOURCE_PATH)
    review = read_json(REVIEW_PATH)
    if command["document_key"] != artifact["document_key"]:
        raise ValueError("document_key does not match the Stage 1 artifact")
    if command["expected_artifact_sha256"] != digest_path(BLOCK_PATH):
        raise RuntimeError("stale artifact hash")
    if command["expected_review_artifact_sha256"] != digest_path(REVIEW_PATH):
        raise RuntimeError("stale review head")
    result = generate_preview(
        artifact, source, review, command["source_block_key"]
    )
    result["artifact_sha256"] = digest_path(BLOCK_PATH)
    result["review_artifact_sha256"] = digest_path(REVIEW_PATH)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                preview_command(read_json(args.command)),
                separators=(",", ":"),
                ensure_ascii=False,
            )
        )
        return 0
    except RuntimeError as error:
        print(json.dumps({"error": str(error), "kind": "conflict"}))
        return 2
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), "kind": "invalid"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

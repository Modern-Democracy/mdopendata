#!/usr/bin/env python3
"""Apply one reviewed Stage 1 block command and append its audit event."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BLOCK_PATH = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v1/stage-1/block-inventory.json"
REVIEW_PATH = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v1/review/review-decisions.json"
SOURCE_PATH = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v1/stage-0/source-evidence.json"
VALIDATOR_PATH = ROOT / "scripts/validate-staged-pdf-artifacts.py"
GENERATOR_PATH = ROOT / "scripts/generate-staged-pdf-block-inventory.py"
ALLOWED_TYPES = {
    "title", "formatted_text", "table", "chart", "other_visual", "map",
    "table_of_contents", "header", "footer", "page_number", "divider", "signature",
}
REGION_TYPES = {
    "formatted_text": {"paragraph", "bullet_list", "sorted_list"},
}
CELL_TYPES = {"table_header", "column_label", "row_label", "cell", "subtotal", "total"}
RELATIONSHIP_TYPES = {"graph_source_table", "table_continuation", "overview_detail"}
ALLOWED_ACTIONS = {
    "resize", "set_type", "delete", "create", "create_region", "resize_region",
    "set_region_type", "delete_region", "redetect_table_grid", "move_table_divider",
    "split_table_rows", "merge_table_rows", "split_table_columns", "merge_table_columns",
    "set_table_cell_type", "migrate_table_grids", "link", "unlink",
}
CONFIG_HASH = hashlib.sha256(b"staged-pdf-block-review-writer-v3\n").hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("staged_pdf_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("staged_pdf_block_generator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load generator: {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_box(value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != {"x0", "y0", "x1", "y1"}:
        raise ValueError("bbox must contain only x0, y0, x1, and y1")
    box = {key: round(float(value[key]), 6) for key in ("x0", "y0", "x1", "y1")}
    if not (0 <= box["x0"] < box["x1"] <= 1 and 0 <= box["y0"] < box["y1"] <= 1):
        raise ValueError("bbox coordinates must be ordered within 0..1")
    if box["x1"] - box["x0"] < 0.005 or box["y1"] - box["y0"] < 0.005:
        raise ValueError("bbox must be at least 0.5 percent wide and high")
    return box


def review_state(decision_id: str) -> dict[str, Any]:
    return {"status": "approved", "reason_codes": ["reviewer-correction"], "decision_ids": [decision_id]}


def exclusion_for(block_type: str) -> str | None:
    if block_type in {"header", "footer", "page_number"}:
        return "header_footer"
    return None


def locate_region(block: dict[str, Any], region_key: str) -> tuple[int, dict[str, Any]]:
    for index, region in enumerate(block["regions"]):
        if region["region_key"] == region_key:
            return index, region
    raise ValueError(f"Unknown region_key for {block['block_key']}: {region_key}")


def endpoint(command: dict[str, Any], name: str) -> dict[str, Any]:
    value = command.get(name)
    if not isinstance(value, dict) or set(value) != {"block_key", "region_key"}:
        raise ValueError(f"{name} must contain only block_key and region_key")
    if not isinstance(value["block_key"], str) or not (
        value["region_key"] is None or isinstance(value["region_key"], str)
    ):
        raise ValueError(f"{name} contains invalid keys")
    return copy.deepcopy(value)


def locate_block(artifact: dict[str, Any], block_key: str) -> tuple[int, dict[str, Any]]:
    for index, block in enumerate(artifact["records"]):
        if block["block_key"] == block_key:
            return index, block
    raise ValueError(f"Unknown block_key: {block_key}")


def source_locator(block: dict[str, Any], excerpt: str | None = None) -> dict[str, Any]:
    recorded_excerpt = None
    if block.get("evidence"):
        recorded_excerpt = block["evidence"][0].get("text_excerpt")
    return {
        "page_key": block["page_key"], "page_number": block["page_number"],
        "block_key": block["block_key"], "bbox": block["bbox"],
        "text_excerpt": excerpt if excerpt is not None else recorded_excerpt,
    }


def detect_table_grid(
    artifact: dict[str, Any], block: dict[str, Any], decision_id: str, sequence: int
) -> dict[str, Any]:
    if block["block_type"] != "table":
        raise ValueError("Table-grid detection requires a table block")
    source = read_json(SOURCE_PATH)
    if source.get("document_key") != artifact["document_key"] or source.get("source_sha256") != artifact["source_sha256"]:
        raise RuntimeError("Stage 0 source evidence does not match the Stage 1 artifact")
    page = next((item for item in source["pages"] if item["page_number"] == block["page_number"]), None)
    if page is None:
        raise RuntimeError(f"Stage 0 source evidence has no page {block['page_number']}")
    use_ocr = page["ocr"]["status"] == "completed"
    evidence_relpath = page["ocr"]["evidence_relpath"] if use_ocr else page["embedded_text"]["evidence_relpath"]
    evidence = read_json(ROOT / evidence_relpath)
    return load_generator().table_grid(
        block["block_key"], evidence.get("words", []), block["bbox"],
        key_prefix=f"grid-{sequence:06d}",
        review={
            "status": "needs_review",
            "reason_codes": ["automated-table-grid-detection"],
            "decision_ids": [decision_id],
        },
    )


def replace_detected_grid(
    artifact: dict[str, Any], block: dict[str, Any], decision_id: str, sequence: int
) -> tuple[list[str], dict[str, Any]]:
    prior = copy.deepcopy(block.get("table_grid"))
    block["regions"] = []
    block["table_grid"] = detect_table_grid(artifact, block, decision_id, sequence)
    change = {
        "field_path": f'/records/{block["block_key"]}/table_grid',
        "prior_value": prior,
        "new_value": copy.deepcopy(block["table_grid"]),
    }
    return [cell["cell_key"] for cell in block["table_grid"]["cells"]], change


def grid_matrix(grid: dict[str, Any]) -> list[list[dict[str, Any]]]:
    row_count = len(grid["row_boundaries"]) - 1
    column_count = len(grid["column_boundaries"]) - 1
    by_coordinate = {(cell["row_index"], cell["column_index"]): cell for cell in grid["cells"]}
    return [[by_coordinate[(row, column)] for column in range(column_count)] for row in range(row_count)]


def rebuilt_grid(
    block: dict[str, Any], row_boundaries: list[float], column_boundaries: list[float],
    cell_rows: list[list[dict[str, Any]]], decision_id: str, sequence: int,
) -> dict[str, Any]:
    cells = []
    for row_index, row in enumerate(cell_rows):
        for column_index, source in enumerate(row):
            cells.append({
                "cell_key": f'{block["block_key"]}:grid-{sequence:06d}-r{row_index + 1:03d}-c{column_index + 1:03d}',
                "row_index": row_index,
                "column_index": column_index,
                "cell_type": source["cell_type"],
                "text_excerpt": source.get("text_excerpt"),
                "review": review_state(decision_id),
            })
    return {
        "row_boundaries": [round(value, 6) for value in row_boundaries],
        "column_boundaries": [round(value, 6) for value in column_boundaries],
        "cells": cells,
        "review": review_state(decision_id),
    }


def table_grid(block: dict[str, Any]) -> dict[str, Any]:
    grid = block.get("table_grid")
    if block["block_type"] != "table" or not isinstance(grid, dict):
        raise ValueError("Table grid action requires a detected table grid")
    return grid


def selected_range(command: dict[str, Any], count: int, *, require_multiple: bool = False) -> tuple[int, int]:
    start = command.get("start_index")
    end = command.get("end_index")
    if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start <= end < count):
        raise ValueError("Selected range must be ordered, adjacent, and inside the grid")
    if require_multiple and start == end:
        raise ValueError("Merge requires at least two adjacent rows or columns")
    return start, end


def ensure_cells_unreferenced(artifact: dict[str, Any], cells: list[dict[str, Any]]) -> None:
    keys = {cell["cell_key"] for cell in cells}
    if any(
        endpoint["region_key"] in keys
        for relationship in artifact["relationships"]
        for endpoint in (relationship["source"], relationship["target"])
    ):
        raise ValueError("Grid structure cannot change while selected cells are used by relationships")


def apply_command(
    artifact: dict[str, Any], command: dict[str, Any], decision_id: str, sequence: int
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    action = command.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    changes: list[dict[str, Any]] = []
    locators: list[dict[str, Any]] = []

    if action == "migrate_table_grids":
        affected = []
        for block in artifact["records"]:
            prior_grid = copy.deepcopy(block.get("table_grid"))
            prior_regions = copy.deepcopy(block["regions"])
            if block["block_type"] == "table":
                block["regions"] = []
                block["table_grid"] = detect_table_grid(artifact, block, decision_id, sequence)
                block["review"] = {
                    "status": "needs_review",
                    "reason_codes": ["automated-table-grid-migration"],
                    "decision_ids": [decision_id],
                }
                affected.append(block["block_key"])
            else:
                block["table_grid"] = None
            changes.append({
                "field_path": f'/records/{block["block_key"]}/table_grid',
                "prior_value": prior_grid,
                "new_value": copy.deepcopy(block["table_grid"]),
            })
            if prior_regions != block["regions"]:
                changes.append({
                    "field_path": f'/records/{block["block_key"]}/regions',
                    "prior_value": prior_regions,
                    "new_value": copy.deepcopy(block["regions"]),
                })
        return affected, [source_locator(block) for block in artifact["records"] if block["block_key"] in affected], changes

    if action == "link":
        relationship_type = command.get("relationship_type")
        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"Unsupported relationship_type: {relationship_type}")
        source = endpoint(command, "source")
        target = endpoint(command, "target")
        relationship_key = f'{artifact["document_key"]}:relationship:{sequence:06d}'
        relationship = {
            "relationship_key": relationship_key,
            "relationship_type": relationship_type,
            "source": source,
            "target": target,
            "review": review_state(decision_id),
        }
        artifact["relationships"].append(relationship)
        for item in (source, target):
            _, related_block = locate_block(artifact, item["block_key"])
            locators.append(source_locator(related_block))
        changes.append({"field_path": f"/relationships/{relationship_key}", "prior_value": None, "new_value": copy.deepcopy(relationship)})
        return [relationship_key], locators, changes

    if action == "unlink":
        relationship_key = command.get("relationship_key")
        for index, relationship in enumerate(artifact["relationships"]):
            if relationship["relationship_key"] == relationship_key:
                prior = artifact["relationships"].pop(index)
                for item in (prior["source"], prior["target"]):
                    _, related_block = locate_block(artifact, item["block_key"])
                    locators.append(source_locator(related_block))
                changes.append({"field_path": f"/relationships/{relationship_key}", "prior_value": prior, "new_value": None})
                return [relationship_key], locators, changes
        raise ValueError(f"Unknown relationship_key: {relationship_key}")

    if action == "create":
        page_number = int(command.get("page_number", 0))
        page = next((item for item in artifact["page_dispositions"] if item["page_number"] == page_number), None)
        if page is None:
            raise ValueError(f"Unknown page_number: {page_number}")
        block_type = command.get("block_type")
        if block_type not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported block_type: {block_type}")
        bbox = normalized_box(command.get("bbox"))
        block_key = f'{page["page_key"]}:review-{sequence:06d}'
        if any(item["block_key"] == block_key for item in artifact["records"]):
            raise ValueError(f"Generated block key already exists: {block_key}")
        reading_order = max(
            (item["reading_order"] for item in artifact["records"] if item["page_number"] == page_number),
            default=0,
        ) + 1
        financial = bool(command.get("financial_candidate", block_type == "table"))
        block = {
            "block_key": block_key, "candidate_key": None, "page_key": page["page_key"],
            "page_number": page_number, "bbox": bbox, "polygon": None,
            "reading_order": reading_order, "block_type": block_type,
            "table_family_candidate": None, "text_source": "visual_only",
            "financial_candidate": financial, "anchors": [],
            "regions": [],
            "table_grid": None,
            "confidence": {"level": "reviewed", "score": 1.0, "reason_codes": ["reviewer-drawn"]},
            "evidence": [], "exclusion_disposition": exclusion_for(block_type),
            "review": review_state(decision_id),
        }
        if block_type == "table":
            block["table_grid"] = detect_table_grid(artifact, block, decision_id, sequence)
        block["evidence"] = [source_locator(block, None)]
        artifact["records"].append(block)
        page["block_keys"].append(block_key)
        page["status"] = "inventoried"
        changes.append({"field_path": f"/records/{block_key}", "prior_value": None, "new_value": copy.deepcopy(block)})
        locators.append(source_locator(block))
        return [block_key], locators, changes

    block_key = command.get("block_key")
    if not isinstance(block_key, str):
        raise ValueError("block_key is required")
    index, block = locate_block(artifact, block_key)
    prior_locator = source_locator(block)

    if action == "redetect_table_grid":
        affected_cells, change = replace_detected_grid(artifact, block, decision_id, sequence)
        changes.append(change)
        block["confidence"] = {
            "level": "medium", "score": 0.7,
            "reason_codes": ["automated-table-grid-detection"],
        }
        block["review"] = {
            "status": "needs_review",
            "reason_codes": ["automated-table-grid-detection"],
            "decision_ids": [decision_id],
        }
        block["evidence"] = [source_locator(block)]
        locators.append(source_locator(block))
        return [block_key, *affected_cells], locators, changes

    grid_actions = {
        "move_table_divider", "split_table_rows", "merge_table_rows",
        "split_table_columns", "merge_table_columns", "set_table_cell_type",
    }
    if action in grid_actions:
        grid = table_grid(block)
        prior_grid = copy.deepcopy(grid)
        matrix = grid_matrix(grid)
        if action == "move_table_divider":
            axis = command.get("axis")
            if axis not in {"row", "column"}:
                raise ValueError("axis must be row or column")
            boundaries = grid["row_boundaries" if axis == "row" else "column_boundaries"]
            divider_index = command.get("divider_index")
            position = round(float(command.get("position")), 6)
            if not isinstance(divider_index, int) or not (0 < divider_index < len(boundaries) - 1):
                raise ValueError("divider_index must identify an internal divider")
            if not boundaries[divider_index - 1] + .005 <= position <= boundaries[divider_index + 1] - .005:
                raise ValueError("Divider must leave adjacent cells at least 0.5 percent wide or high")
            boundaries[divider_index] = position
            affected_cells = []
        elif action == "set_table_cell_type":
            cell_key = command.get("cell_key")
            cell_type = command.get("cell_type")
            if cell_type not in CELL_TYPES:
                raise ValueError(f"Unsupported table cell type: {cell_type}")
            cell = next((item for item in grid["cells"] if item["cell_key"] == cell_key), None)
            if cell is None:
                raise ValueError(f"Unknown table cell: {cell_key}")
            cell["cell_type"] = cell_type
            cell["review"] = review_state(decision_id)
            affected_cells = [cell_key]
        else:
            row_count = len(matrix)
            column_count = len(matrix[0])
            selected_cells: list[dict[str, Any]] = []
            if action.endswith("_rows"):
                start, end = selected_range(command, row_count, require_multiple=action.startswith("merge"))
                selected_cells = [cell for row in matrix[start:end + 1] for cell in row]
                ensure_cells_unreferenced(artifact, selected_cells)
                if action.startswith("split"):
                    new_rows = []
                    new_boundaries = [grid["row_boundaries"][0]]
                    for row_index, row in enumerate(matrix):
                        if start <= row_index <= end:
                            midpoint = round((grid["row_boundaries"][row_index] + grid["row_boundaries"][row_index + 1]) / 2, 6)
                            new_rows.extend([
                                [{**cell, "text_excerpt": None} for cell in row],
                                [{**cell, "text_excerpt": None} for cell in row],
                            ])
                            new_boundaries.extend([midpoint, grid["row_boundaries"][row_index + 1]])
                        else:
                            new_rows.append(row)
                            new_boundaries.append(grid["row_boundaries"][row_index + 1])
                    matrix = new_rows
                    row_boundaries = new_boundaries
                else:
                    merged_row = []
                    for column in range(column_count):
                        sources = [matrix[row][column] for row in range(start, end + 1)]
                        types = {source["cell_type"] for source in sources}
                        excerpts = list(dict.fromkeys(source.get("text_excerpt") for source in sources if source.get("text_excerpt")))
                        merged_row.append({
                            **sources[0], "cell_type": types.pop() if len(types) == 1 else "cell",
                            "text_excerpt": " ".join(excerpts)[:240] or None,
                        })
                    matrix = matrix[:start] + [merged_row] + matrix[end + 1:]
                    row_boundaries = grid["row_boundaries"][:start + 1] + grid["row_boundaries"][end + 1:]
                column_boundaries = grid["column_boundaries"]
            else:
                start, end = selected_range(command, column_count, require_multiple=action.startswith("merge"))
                selected_cells = [matrix[row][column] for row in range(row_count) for column in range(start, end + 1)]
                ensure_cells_unreferenced(artifact, selected_cells)
                if action.startswith("split"):
                    new_columns = []
                    new_boundaries = [grid["column_boundaries"][0]]
                    for column in range(column_count):
                        if start <= column <= end:
                            midpoint = round((grid["column_boundaries"][column] + grid["column_boundaries"][column + 1]) / 2, 6)
                            new_columns.extend([column, column])
                            new_boundaries.extend([midpoint, grid["column_boundaries"][column + 1]])
                        else:
                            new_columns.append(column)
                            new_boundaries.append(grid["column_boundaries"][column + 1])
                    matrix = [[{**row[column], "text_excerpt": None} for column in new_columns] for row in matrix]
                    column_boundaries = new_boundaries
                else:
                    new_matrix = []
                    for row in matrix:
                        sources = row[start:end + 1]
                        types = {source["cell_type"] for source in sources}
                        excerpts = list(dict.fromkeys(source.get("text_excerpt") for source in sources if source.get("text_excerpt")))
                        merged = {
                            **sources[0], "cell_type": types.pop() if len(types) == 1 else "cell",
                            "text_excerpt": " ".join(excerpts)[:240] or None,
                        }
                        new_matrix.append(row[:start] + [merged] + row[end + 1:])
                    matrix = new_matrix
                    column_boundaries = grid["column_boundaries"][:start + 1] + grid["column_boundaries"][end + 1:]
                row_boundaries = grid["row_boundaries"]
            block["table_grid"] = rebuilt_grid(
                block, row_boundaries, column_boundaries, matrix, decision_id, sequence,
            )
            grid = block["table_grid"]
            affected_cells = [cell["cell_key"] for cell in grid["cells"]]
        grid["review"] = review_state(decision_id)
        block["review"] = review_state(decision_id)
        block["confidence"] = {"level": "reviewed", "score": 1.0, "reason_codes": ["reviewer-grid-correction"]}
        changes.append({
            "field_path": f"/records/{block_key}/table_grid",
            "prior_value": prior_grid,
            "new_value": copy.deepcopy(block["table_grid"]),
        })
        locators.append(source_locator(block))
        return [block_key, *affected_cells], locators, changes

    if action in {"create_region", "resize_region", "set_region_type", "delete_region"}:
        allowed = REGION_TYPES.get(block["block_type"])
        if not allowed:
            raise ValueError(f"Block type {block['block_type']} does not support internal regions")
        if action == "create_region":
            region_type = command.get("region_type")
            if region_type not in allowed:
                raise ValueError(f"Unsupported region_type for {block['block_type']}: {region_type}")
            bbox = normalized_box(command.get("bbox"))
            region_key = f'{block_key}:review-region-{sequence:06d}'
            region = {
                "region_key": region_key, "region_type": region_type, "bbox": bbox,
                "text_excerpt": None, "review": review_state(decision_id),
            }
            block["regions"].append(region)
            changes.append({"field_path": f"/records/{block_key}/regions/{region_key}", "prior_value": None, "new_value": copy.deepcopy(region)})
        else:
            region_key = command.get("region_key")
            if not isinstance(region_key, str):
                raise ValueError("region_key is required")
            region_index, region = locate_region(block, region_key)
            if action == "delete_region":
                prior = block["regions"].pop(region_index)
                changes.append({"field_path": f"/records/{block_key}/regions/{region_key}", "prior_value": prior, "new_value": None})
            elif action == "resize_region":
                prior = copy.deepcopy(region["bbox"])
                region["bbox"] = normalized_box(command.get("bbox"))
                region["review"] = review_state(decision_id)
                changes.append({"field_path": f"/records/{block_key}/regions/{region_key}/bbox", "prior_value": prior, "new_value": copy.deepcopy(region["bbox"])})
            else:
                region_type = command.get("region_type")
                if region_type not in allowed:
                    raise ValueError(f"Unsupported region_type for {block['block_type']}: {region_type}")
                prior = region["region_type"]
                region["region_type"] = region_type
                region["review"] = review_state(decision_id)
                changes.append({"field_path": f"/records/{block_key}/regions/{region_key}/region_type", "prior_value": prior, "new_value": region_type})
        block["confidence"] = {"level": "reviewed", "score": 1.0, "reason_codes": ["reviewer-correction"]}
        block["review"] = review_state(decision_id)
        locators.append(source_locator(block))
        affected = [block_key, region_key]
        return affected, locators, changes

    if action == "delete":
        prior = copy.deepcopy(block)
        prior_relationships = [
            relationship for relationship in artifact["relationships"]
            if relationship["source"]["block_key"] == block_key or relationship["target"]["block_key"] == block_key
        ]
        artifact["relationships"] = [
            relationship for relationship in artifact["relationships"] if relationship not in prior_relationships
        ]
        artifact["records"].pop(index)
        page = next(item for item in artifact["page_dispositions"] if item["page_key"] == block["page_key"])
        page["block_keys"].remove(block_key)
        page["status"] = "inventoried" if page["block_keys"] else "no_material_content"
        changes.append({"field_path": f"/records/{block_key}", "prior_value": prior, "new_value": None})
        if prior_relationships:
            changes.append({"field_path": "/relationships", "prior_value": prior_relationships, "new_value": []})
        return [block_key], [prior_locator], changes

    redetected = False
    if action == "resize":
        prior = copy.deepcopy(block["bbox"])
        block["bbox"] = normalized_box(command.get("bbox"))
        changes.append({"field_path": f"/records/{block_key}/bbox", "prior_value": prior, "new_value": copy.deepcopy(block["bbox"])})
        if command.get("redetect_table_grid") is True:
            affected_cells, change = replace_detected_grid(artifact, block, decision_id, sequence)
            changes.append(change)
            redetected = True
        elif command.get("redetect_table_grid") not in (None, False):
            raise ValueError("redetect_table_grid must be boolean")
        elif block.get("table_grid") is not None:
            prior_grid = copy.deepcopy(block["table_grid"])
            old_width = prior["x1"] - prior["x0"]
            old_height = prior["y1"] - prior["y0"]
            new_width = block["bbox"]["x1"] - block["bbox"]["x0"]
            new_height = block["bbox"]["y1"] - block["bbox"]["y0"]
            block["table_grid"]["column_boundaries"] = [
                round(block["bbox"]["x0"] + ((value - prior["x0"]) / old_width) * new_width, 6)
                for value in block["table_grid"]["column_boundaries"]
            ]
            block["table_grid"]["row_boundaries"] = [
                round(block["bbox"]["y0"] + ((value - prior["y0"]) / old_height) * new_height, 6)
                for value in block["table_grid"]["row_boundaries"]
            ]
            block["table_grid"]["column_boundaries"][0] = block["bbox"]["x0"]
            block["table_grid"]["column_boundaries"][-1] = block["bbox"]["x1"]
            block["table_grid"]["row_boundaries"][0] = block["bbox"]["y0"]
            block["table_grid"]["row_boundaries"][-1] = block["bbox"]["y1"]
            changes.append({
                "field_path": f"/records/{block_key}/table_grid",
                "prior_value": prior_grid,
                "new_value": copy.deepcopy(block["table_grid"]),
            })
    elif action == "set_type":
        block_type = command.get("block_type")
        if block_type not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported block_type: {block_type}")
        prior_type = block["block_type"]
        prior_financial = block["financial_candidate"]
        block["block_type"] = block_type
        block["financial_candidate"] = bool(command.get("financial_candidate", prior_financial))
        block["exclusion_disposition"] = exclusion_for(block_type)
        if block_type != "table":
            block["table_family_candidate"] = None
        prior_regions = copy.deepcopy(block["regions"])
        prior_grid = copy.deepcopy(block.get("table_grid"))
        allowed_regions = REGION_TYPES.get(block_type, set())
        block["regions"] = [region for region in block["regions"] if region["region_type"] in allowed_regions]
        block["table_grid"] = detect_table_grid(artifact, block, decision_id, sequence) if block_type == "table" else None
        changes.extend([
            {"field_path": f"/records/{block_key}/block_type", "prior_value": prior_type, "new_value": block_type},
            {"field_path": f"/records/{block_key}/financial_candidate", "prior_value": prior_financial, "new_value": block["financial_candidate"]},
            {"field_path": f"/records/{block_key}/regions", "prior_value": prior_regions, "new_value": copy.deepcopy(block["regions"])},
            {"field_path": f"/records/{block_key}/table_grid", "prior_value": prior_grid, "new_value": copy.deepcopy(block["table_grid"])},
        ])

    block["candidate_key"] = block.get("candidate_key")
    if redetected:
        block["confidence"] = {"level": "medium", "score": 0.7, "reason_codes": ["automated-table-grid-detection"]}
        block["review"] = {"status": "needs_review", "reason_codes": ["automated-table-grid-detection"], "decision_ids": [decision_id]}
    else:
        block["confidence"] = {"level": "reviewed", "score": 1.0, "reason_codes": ["reviewer-correction"]}
        block["review"] = review_state(decision_id)
    block["evidence"] = [source_locator(block)]
    locators.extend([prior_locator, source_locator(block)])
    return [block_key, *(affected_cells if redetected else [])], locators, changes


def initial_review_artifact(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": os.path.relpath(
            ROOT / "schema/json-schema/staged-pdf-artifacts.schema.json", REVIEW_PATH.parent
        ).replace("\\", "/"),
        "schema_version": 1, "artifact_type": "review_decisions",
        "artifact_key": f'{block["document_key"]}:review-decisions:v1',
        "document_key": block["document_key"], "source_sha256": block["source_sha256"],
        "generator": {"name": "staged-pdf-block-review-writer", "version": "1", "config_sha256": CONFIG_HASH},
        "upstream_artifacts": copy.deepcopy(block["upstream_artifacts"]),
        "target_artifacts": [], "events": [],
    }


def atomic_pair(block_bytes: bytes, review_bytes: bytes) -> None:
    BLOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    old_block = BLOCK_PATH.read_bytes()
    old_review = REVIEW_PATH.read_bytes() if REVIEW_PATH.exists() else None
    block_fd, block_name = tempfile.mkstemp(prefix=".block-inventory-", suffix=".json", dir=BLOCK_PATH.parent)
    review_fd, review_name = tempfile.mkstemp(prefix=".review-decisions-", suffix=".json", dir=REVIEW_PATH.parent)
    os.close(block_fd); os.close(review_fd)
    block_tmp, review_tmp = Path(block_name), Path(review_name)
    try:
        block_tmp.write_bytes(block_bytes); review_tmp.write_bytes(review_bytes)
        os.replace(block_tmp, BLOCK_PATH)
        try:
            os.replace(review_tmp, REVIEW_PATH)
        except Exception:
            BLOCK_PATH.write_bytes(old_block)
            if old_review is None and REVIEW_PATH.exists():
                REVIEW_PATH.unlink()
            elif old_review is not None:
                REVIEW_PATH.write_bytes(old_review)
            raise
    finally:
        block_tmp.unlink(missing_ok=True); review_tmp.unlink(missing_ok=True)


def validate_incremental_update(
    validator: Any,
    block: dict[str, Any],
    review: dict[str, Any],
    event: dict[str, Any],
    affected_keys: list[str],
) -> list[str]:
    errors: list[str] = []
    component_validators = validator.load_component_validators(
        ("block_record", "page_disposition", "block_relationship", "review_event")
    )
    affected = set(affected_keys)
    for record in block["records"]:
        if record["block_key"] in affected:
            errors.extend(validator.validate_component(record, "block_record", component_validators["block_record"]))
    for page in block["page_dispositions"]:
        errors.extend(validator.validate_component(page, "page_disposition", component_validators["page_disposition"]))
    for relationship in block["relationships"]:
        errors.extend(validator.validate_component(
            relationship, "block_relationship", component_validators["block_relationship"],
        ))
    errors.extend(validator.validate_component(event, "review_event", component_validators["review_event"]))
    if not errors:
        validator.check_block_inventory(block, errors)
        validator.check_review_decisions(review, errors)
        errors.extend(validator.validate_artifact_set([block, review]))
    return errors


def update(command_path: Path) -> dict[str, Any]:
    command = read_json(command_path)
    block = read_json(BLOCK_PATH)
    prior_hash = digest_path(BLOCK_PATH)
    if command.get("document_key") != block["document_key"]:
        raise ValueError("document_key does not match the Stage 1 artifact")
    if command.get("expected_artifact_sha256") != prior_hash:
        raise RuntimeError(f"stale artifact hash: expected {command.get('expected_artifact_sha256')}, current {prior_hash}")
    reason = str(command.get("reason", "")).strip()
    if not reason:
        raise ValueError("reason is required")
    review = read_json(REVIEW_PATH) if REVIEW_PATH.exists() else initial_review_artifact(block)
    sequence = len(review["events"]) + 1
    decision_id = f'{block["document_key"]}:decision:{sequence:06d}'
    affected, locators, changes = apply_command(block, command, decision_id, sequence)
    block_bytes = canonical_bytes(block)
    result_hash = digest_bytes(block_bytes)
    previous_hash = review["events"][-1]["event_sha256"] if review["events"] else None
    event = {
        "decision_id": decision_id, "sequence": sequence,
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reviewer": {"reviewer_id": "local-reviewer", "display_name": "Local reviewer", "role": "data-reviewer"},
        "action": command["action"], "reason": reason,
        "prior_artifact_sha256": prior_hash, "result_artifact_sha256": result_hash,
        "previous_event_sha256": previous_hash, "event_sha256": "0" * 64,
        "affected_keys": affected, "source_locators": locators, "changes": changes,
    }
    event_hash_payload = copy.deepcopy(event); event_hash_payload.pop("event_sha256")
    event["event_sha256"] = digest_bytes(canonical_bytes(event_hash_payload))
    review["target_artifacts"] = [{"artifact_type": "block_inventory", "artifact_key": block["artifact_key"], "sha256": result_hash}]
    review["events"].append(event)
    validator = load_validator()
    errors = validate_incremental_update(validator, block, review, event, affected)
    if errors:
        raise RuntimeError("Updated artifacts failed validation: " + "; ".join(errors[:10]))
    review_bytes = canonical_bytes(review)
    atomic_pair(block_bytes, review_bytes)
    return {
        "status": "applied", "action": command["action"], "decision_id": decision_id,
        "artifact_sha256": result_hash, "review_artifact_sha256": digest_bytes(review_bytes),
        "affected_keys": affected,
        "affected_page_numbers": sorted({locator["page_number"] for locator in locators}),
        "validation_mode": "incremental",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(update(args.command), separators=(",", ":")))
        return 0
    except RuntimeError as error:
        print(json.dumps({"error": str(error), "kind": "conflict" if "stale artifact hash" in str(error) else "validation"}, separators=(",", ":")))
        return 2
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), "kind": "invalid"}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

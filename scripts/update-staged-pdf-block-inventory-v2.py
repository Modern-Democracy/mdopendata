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
WORKSPACE_ROOT = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf"
BLOCK_PATH = WORKSPACE_ROOT / "v1/stage-1/block-inventory.json"
REVIEW_PATH = WORKSPACE_ROOT / "v1/review/review-decisions.json"
SOURCE_PATH = WORKSPACE_ROOT / "v1/stage-0/source-evidence.json"
VALIDATOR_PATH = ROOT / "scripts/validate-staged-pdf-artifacts.py"
GENERATOR_PATH = ROOT / "scripts/generate-staged-pdf-block-inventory-v2.py"
PROPAGATION_PATH = ROOT / "scripts/preview-staged-pdf-structural-propagation.py"
ALLOWED_TYPES = {
    "title", "formatted_text", "table", "chart", "other_visual", "map",
    "table_of_contents", "header", "footer", "page_number", "divider", "signature",
}
REGION_TYPES = {"paragraph", "bullet_list", "sorted_list"}
CELL_TYPES = {"table_header", "column_label", "row_label", "cell", "subtotal", "total"}
RELATIONSHIP_TYPES = {"graph_source_table", "table_continuation", "overview_detail"}
ALLOWED_ACTIONS = {
    "resize", "set_type", "delete", "create", "create_region", "resize_region",
    "set_region_type", "delete_region", "redetect_table_grid", "move_table_divider",
    "split_table_rows", "merge_table_rows", "split_table_columns", "merge_table_columns",
    "merge_table_cells", "split_table_cell", "set_table_cell_span",
    "set_table_cell_type", "migrate_table_grids", "link", "unlink",
    "apply_template", "auto_approve", "reject",
}
CONFIG_HASH = hashlib.sha256(b"staged-pdf-block-review-writer-v4\n").hexdigest()


def configure_workspace(schema_version: int) -> None:
    if schema_version not in {1, 2}:
        raise ValueError(f"Unsupported workspace schema version: {schema_version}")
    global BLOCK_PATH, REVIEW_PATH, SOURCE_PATH
    workspace = WORKSPACE_ROOT / f"v{schema_version}"
    BLOCK_PATH = workspace / "stage-1/block-inventory.json"
    REVIEW_PATH = workspace / "review/review-decisions.json"
    SOURCE_PATH = workspace / "stage-0/source-evidence.json"


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


def load_propagation_matcher() -> Any:
    spec = importlib.util.spec_from_file_location(
        "staged_pdf_propagation", PROPAGATION_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load propagation matcher: {PROPAGATION_PATH}")
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
        schema_version=int(artifact.get("schema_version", 1)),
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


def effective_span(cell: dict[str, Any], axis: str) -> int:
    return int(cell.get(f"{axis}_span", 1))


def cell_coordinates(cell: dict[str, Any]) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row in range(
            cell["row_index"],
            cell["row_index"] + effective_span(cell, "row"),
        )
        for column in range(
            cell["column_index"],
            cell["column_index"] + effective_span(cell, "column"),
        )
    }


def grid_matrix(grid: dict[str, Any]) -> list[list[dict[str, Any]]]:
    row_count = len(grid["row_boundaries"]) - 1
    column_count = len(grid["column_boundaries"]) - 1
    by_coordinate = {
        coordinate: cell
        for cell in grid["cells"]
        for coordinate in cell_coordinates(cell)
    }
    return [[by_coordinate[(row, column)] for column in range(column_count)] for row in range(row_count)]


def locate_cell(grid: dict[str, Any], cell_key: str) -> dict[str, Any]:
    cell = next((item for item in grid["cells"] if item["cell_key"] == cell_key), None)
    if cell is None:
        raise ValueError(f"Unknown table cell: {cell_key}")
    return cell


def ensure_unit_span_grid(grid: dict[str, Any]) -> None:
    if any(
        effective_span(cell, "row") != 1 or effective_span(cell, "column") != 1
        for cell in grid["cells"]
    ):
        raise ValueError(
            "Global row or column split and merge requires unit-span cells; "
            "split spanning cells first"
        )


def cell_with_span(
    *,
    cell_key: str,
    row_index: int,
    column_index: int,
    row_span: int,
    column_span: int,
    cell_type: str,
    text_excerpt: str | None,
    decision_id: str,
) -> dict[str, Any]:
    cell = {
        "cell_key": cell_key,
        "row_index": row_index,
        "column_index": column_index,
        "cell_type": cell_type,
        "text_excerpt": text_excerpt,
        "review": review_state(decision_id),
    }
    if row_span != 1:
        cell["row_span"] = row_span
    if column_span != 1:
        cell["column_span"] = column_span
    return cell


def joined_excerpt(cells: list[dict[str, Any]]) -> str | None:
    excerpts = [
        cell["text_excerpt"]
        for cell in sorted(
            cells, key=lambda item: (item["row_index"], item["column_index"])
        )
        if cell.get("text_excerpt")
    ]
    return " ".join(dict.fromkeys(excerpts))[:240] or None


def replace_cell_span(
    artifact: dict[str, Any],
    block: dict[str, Any],
    cell: dict[str, Any],
    row_span: int,
    column_span: int,
    decision_id: str,
    sequence: int,
) -> list[str]:
    grid = table_grid(block)
    row_count = len(grid["row_boundaries"]) - 1
    column_count = len(grid["column_boundaries"]) - 1
    if (
        not isinstance(row_span, int)
        or isinstance(row_span, bool)
        or not isinstance(column_span, int)
        or isinstance(column_span, bool)
        or row_span < 1
        or column_span < 1
    ):
        raise ValueError("row_span and column_span must be positive integers")
    if (
        cell["row_index"] + row_span > row_count
        or cell["column_index"] + column_span > column_count
    ):
        raise ValueError("Requested cell span extends outside the table grid")

    old_coordinates = cell_coordinates(cell)
    new_coordinates = {
        (row, column)
        for row in range(cell["row_index"], cell["row_index"] + row_span)
        for column in range(cell["column_index"], cell["column_index"] + column_span)
    }
    consumed = [
        other
        for other in grid["cells"]
        if other is not cell and cell_coordinates(other) & new_coordinates
    ]
    if any(not cell_coordinates(other).issubset(new_coordinates) for other in consumed):
        raise ValueError("Requested span would partially overlap another spanning cell")
    ensure_cells_unreferenced(artifact, consumed)

    if cell["cell_type"] == "table_title":
        at_boundary = cell["row_index"] == 0 or cell["row_index"] + row_span == row_count
        if cell["column_index"] != 0 or column_span != column_count or not at_boundary:
            raise ValueError("A table title must remain full-width at the top or bottom boundary")

    released = sorted(old_coordinates - new_coordinates)
    retained = [
        item for item in grid["cells"] if item is not cell and item not in consumed
    ]
    updated = cell_with_span(
        cell_key=cell["cell_key"],
        row_index=cell["row_index"],
        column_index=cell["column_index"],
        row_span=row_span,
        column_span=column_span,
        cell_type=cell["cell_type"],
        text_excerpt=joined_excerpt([cell, *consumed]),
        decision_id=decision_id,
    )
    released_type = "column_label" if cell["cell_type"] == "table_title" else cell["cell_type"]
    created = [
        cell_with_span(
            cell_key=(
                f'{block["block_key"]}:grid-{sequence:06d}-'
                f"r{row + 1:03d}-c{column + 1:03d}"
            ),
            row_index=row,
            column_index=column,
            row_span=1,
            column_span=1,
            cell_type=released_type,
            text_excerpt=None,
            decision_id=decision_id,
        )
        for row, column in released
    ]
    grid["cells"] = sorted(
        [*retained, updated, *created],
        key=lambda item: (item["row_index"], item["column_index"], item["cell_key"]),
    )
    return [cell["cell_key"], *(item["cell_key"] for item in consumed), *(item["cell_key"] for item in created)]


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


def ensure_removed_regions_unreferenced(
    artifact: dict[str, Any], removed_keys: set[str]
) -> None:
    if any(
        endpoint["region_key"] in removed_keys
        for relationship in artifact["relationships"]
        for endpoint in (relationship["source"], relationship["target"])
    ):
        raise ValueError(
            "Propagated structure cannot remove a relationship endpoint"
        )


def apply_command(
    artifact: dict[str, Any], command: dict[str, Any], decision_id: str, sequence: int
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    action = command.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    changes: list[dict[str, Any]] = []
    locators: list[dict[str, Any]] = []

    if action == "reject":
        source_block_key = command.get("source_block_key")
        pattern_hash = command.get("pattern_sha256")
        target_keys = command.get("target_block_keys")
        if (
            not isinstance(source_block_key, str)
            or not isinstance(pattern_hash, str)
            or not isinstance(target_keys, list)
            or not target_keys
            or len(set(target_keys)) != len(target_keys)
            or not all(isinstance(key, str) for key in target_keys)
        ):
            raise ValueError("Propagation rejection requires source, pattern, and unique targets")
        _, source_block = locate_block(artifact, source_block_key)
        locators.append(source_locator(source_block))
        for target_key in target_keys:
            _, target = locate_block(artifact, target_key)
            locators.append(source_locator(target))
            changes.append({
                "field_path": (
                    f"/propagation_negative_controls/{pattern_hash}/{target_key}"
                ),
                "prior_value": None,
                "new_value": {
                    "pattern_sha256": pattern_hash,
                    "source_block_key": source_block_key,
                    "target_block_key": target_key,
                },
            })
        return target_keys, locators, changes

    if action in {"apply_template", "auto_approve"}:
        source_block_key = command.get("source_block_key")
        pattern_hash = command.get("pattern_sha256")
        candidates = command.get("_verified_propagation_candidates")
        if (
            not isinstance(source_block_key, str)
            or not isinstance(pattern_hash, str)
            or not isinstance(candidates, list)
            or not candidates
        ):
            raise ValueError("Verified propagation candidates are required")
        _, source_block = locate_block(artifact, source_block_key)
        locators.append(source_locator(source_block))
        affected: list[str] = []
        propagated_review = (
            {
                "status": "approved",
                "reason_codes": ["template-policy-approval"],
                "decision_ids": [decision_id],
            }
            if action == "auto_approve"
            else review_state(decision_id)
        )
        for candidate in candidates:
            target_key = candidate["target_block_key"]
            _, target = locate_block(artifact, target_key)
            field = candidate["proposal_field"]
            if field not in {"regions", "table_grid"}:
                raise ValueError("Unsupported propagation proposal field")
            prior = copy.deepcopy(target[field])
            proposal = copy.deepcopy(candidate["proposal"])
            old_keys = (
                {cell["cell_key"] for cell in prior["cells"]}
                if field == "table_grid"
                else {region["region_key"] for region in prior}
            )
            new_keys = (
                {cell["cell_key"] for cell in proposal["cells"]}
                if field == "table_grid"
                else {region["region_key"] for region in proposal}
            )
            ensure_removed_regions_unreferenced(artifact, old_keys - new_keys)
            if field == "table_grid":
                proposal["review"] = copy.deepcopy(propagated_review)
                for cell in proposal["cells"]:
                    cell["review"] = copy.deepcopy(propagated_review)
            else:
                for region in proposal:
                    region["review"] = copy.deepcopy(propagated_review)
            target[field] = proposal
            target["review"] = copy.deepcopy(propagated_review)
            target["confidence"] = {
                "level": "reviewed",
                "score": candidate["confidence"],
                "reason_codes": ["document-structural-propagation"],
            }
            changes.append({
                "field_path": f"/records/{target_key}/{field}",
                "prior_value": prior,
                "new_value": copy.deepcopy(proposal),
            })
            if action == "auto_approve":
                changes.append({
                    "field_path": f"/policy_evaluations/{target_key}",
                    "prior_value": None,
                    "new_value": {
                        "policy_evaluation": copy.deepcopy(
                            candidate["policy_evaluation"]
                        ),
                        "automation_context": copy.deepcopy(
                            candidate["automation_context"]
                        ),
                    },
                })
            locators.append(source_locator(target))
            affected.append(target_key)
        return affected, locators, changes

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
            "financial_candidate": financial, "anchors": [], "regions": [],
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
        block["confidence"] = {"level": "medium", "score": 0.7, "reason_codes": ["automated-table-grid-detection"]}
        block["review"] = {"status": "needs_review", "reason_codes": ["automated-table-grid-detection"], "decision_ids": [decision_id]}
        block["evidence"] = [source_locator(block)]
        locators.append(source_locator(block))
        return [block_key, *affected_cells], locators, changes

    grid_actions = {
        "move_table_divider", "split_table_rows", "merge_table_rows",
        "split_table_columns", "merge_table_columns", "merge_table_cells",
        "split_table_cell", "set_table_cell_span", "set_table_cell_type",
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
            allowed_cell_types = CELL_TYPES | ({"table_title"} if artifact.get("schema_version") == 2 else set())
            if cell_type not in allowed_cell_types:
                raise ValueError(f"Unsupported table cell type: {cell_type}")
            cell = locate_cell(grid, cell_key)
            if cell_type == "table_title":
                row_count = len(grid["row_boundaries"]) - 1
                column_count = len(grid["column_boundaries"]) - 1
                row_span = effective_span(cell, "row")
                if cell["row_index"] != 0 and cell["row_index"] + row_span != row_count:
                    raise ValueError("A table title must be selected at the top or bottom boundary")
                if any(item["cell_type"] == "table_title" and item is not cell for item in grid["cells"]):
                    raise ValueError("A table can contain at most one table title")
                title_coordinates = {
                    (row, column)
                    for row in range(cell["row_index"], cell["row_index"] + row_span)
                    for column in range(column_count)
                }
                title_cells = [item for item in grid["cells"] if cell_coordinates(item) & title_coordinates]
                if any(not cell_coordinates(item).issubset(title_coordinates) for item in title_cells):
                    raise ValueError("Table title rows intersect another spanning cell")
                ensure_cells_unreferenced(artifact, [item for item in title_cells if item is not cell])
                grid["cells"] = [item for item in grid["cells"] if item not in title_cells]
                grid["cells"].append(cell_with_span(
                    cell_key=cell["cell_key"], row_index=cell["row_index"], column_index=0,
                    row_span=row_span, column_span=column_count, cell_type="table_title",
                    text_excerpt=joined_excerpt(title_cells), decision_id=decision_id,
                ))
                grid["cells"].sort(key=lambda item: (item["row_index"], item["column_index"], item["cell_key"]))
                affected_cells = [item["cell_key"] for item in title_cells]
            else:
                cell["cell_type"] = cell_type
                cell["review"] = review_state(decision_id)
                affected_cells = [cell_key]
        elif action == "set_table_cell_span":
            if artifact.get("schema_version") != 2:
                raise ValueError("Cell spans require a version 2 workspace")
            cell = locate_cell(grid, command.get("cell_key"))
            affected_cells = replace_cell_span(
                artifact, block, cell, command.get("row_span"), command.get("column_span"),
                decision_id, sequence,
            )
        elif action == "split_table_cell":
            if artifact.get("schema_version") != 2:
                raise ValueError("Spanning cells require a version 2 workspace")
            cell = locate_cell(grid, command.get("cell_key"))
            if effective_span(cell, "row") == 1 and effective_span(cell, "column") == 1:
                raise ValueError("Selected table cell does not span multiple coordinates")
            ensure_cells_unreferenced(artifact, [cell])
            coordinates = sorted(cell_coordinates(cell))
            split_type = "column_label" if cell["cell_type"] == "table_title" else cell["cell_type"]
            grid["cells"] = [item for item in grid["cells"] if item is not cell]
            replacements = [
                cell_with_span(
                    cell_key=f'{block["block_key"]}:grid-{sequence:06d}-r{row + 1:03d}-c{column + 1:03d}',
                    row_index=row, column_index=column, row_span=1, column_span=1,
                    cell_type=split_type, text_excerpt=cell.get("text_excerpt") if item_index == 0 else None,
                    decision_id=decision_id,
                )
                for item_index, (row, column) in enumerate(coordinates)
            ]
            grid["cells"].extend(replacements)
            grid["cells"].sort(key=lambda item: (item["row_index"], item["column_index"], item["cell_key"]))
            affected_cells = [cell["cell_key"], *(item["cell_key"] for item in replacements)]
        elif action == "merge_table_cells":
            if artifact.get("schema_version") != 2:
                raise ValueError("Spanning cells require a version 2 workspace")
            cell_keys = command.get("cell_keys")
            if (
                not isinstance(cell_keys, list) or len(cell_keys) < 2
                or len(set(cell_keys)) != len(cell_keys)
                or not all(isinstance(key, str) for key in cell_keys)
            ):
                raise ValueError("cell_keys must contain at least two unique table cell keys")
            selected = [locate_cell(grid, key) for key in cell_keys]
            selected_coordinates = set().union(*(cell_coordinates(item) for item in selected))
            min_row = min(row for row, _ in selected_coordinates)
            max_row = max(row for row, _ in selected_coordinates)
            min_column = min(column for _, column in selected_coordinates)
            max_column = max(column for _, column in selected_coordinates)
            rectangle = {
                (row, column)
                for row in range(min_row, max_row + 1)
                for column in range(min_column, max_column + 1)
            }
            if selected_coordinates != rectangle:
                raise ValueError("Merged cells must form one complete rectangle")
            ensure_cells_unreferenced(artifact, selected)
            types = {item["cell_type"] for item in selected}
            merged_type = types.pop() if len(types) == 1 else "cell"
            if merged_type == "table_title":
                row_count = len(grid["row_boundaries"]) - 1
                column_count = len(grid["column_boundaries"]) - 1
                if min_column != 0 or max_column + 1 != column_count or (min_row != 0 and max_row + 1 != row_count):
                    raise ValueError("A merged table title must be full-width at a boundary")
            merged = cell_with_span(
                cell_key=f'{block["block_key"]}:grid-{sequence:06d}-merged',
                row_index=min_row, column_index=min_column,
                row_span=max_row - min_row + 1, column_span=max_column - min_column + 1,
                cell_type=merged_type, text_excerpt=joined_excerpt(selected),
                decision_id=decision_id,
            )
            grid["cells"] = [item for item in grid["cells"] if item not in selected] + [merged]
            grid["cells"].sort(key=lambda item: (item["row_index"], item["column_index"], item["cell_key"]))
            affected_cells = [*cell_keys, merged["cell_key"]]
        else:
            ensure_unit_span_grid(grid)
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
        allowed = (
            REGION_TYPES | ({"title"} if artifact.get("schema_version") == 2 else set())
            if block["block_type"] == "formatted_text"
            else None
        )
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
        allowed_regions = (
            REGION_TYPES | ({"title"} if artifact.get("schema_version") == 2 else set())
            if block_type == "formatted_text"
            else set()
        )
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
    schema_version = int(block.get("schema_version", 1))
    schema_name = (
        "staged-pdf-artifacts-v2.schema.json"
        if schema_version == 2
        else "staged-pdf-artifacts.schema.json"
    )
    return {
        "$schema": os.path.relpath(
            ROOT / "schema/json-schema" / schema_name, REVIEW_PATH.parent
        ).replace("\\", "/"),
        "schema_version": schema_version, "artifact_type": "review_decisions",
        "artifact_key": f'{block["document_key"]}:review-decisions:v{schema_version}',
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
    schema_version = int(block.get("schema_version", 1))
    component_validators = validator.load_component_validators(
        ("block_record", "page_disposition", "block_relationship", "review_event"),
        schema_version,
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
    if command.get("action") in {"apply_template", "auto_approve", "reject"}:
        expected_review_hash = command.get("expected_review_artifact_sha256")
        current_review_hash = digest_path(REVIEW_PATH)
        if expected_review_hash != current_review_hash:
            raise RuntimeError(
                f"stale review head: expected {expected_review_hash}, current {current_review_hash}"
            )
        matcher = load_propagation_matcher()
        source = read_json(SOURCE_PATH)
        preview = matcher.generate_preview(
            block, source, review, command.get("source_block_key")
        )
        if command.get("pattern_sha256") != preview["pattern_sha256"]:
            raise RuntimeError("stale propagation pattern")
        by_target = {
            candidate["target_block_key"]: candidate
            for candidate in preview["candidates"]
        }
        if command["action"] in {"apply_template", "auto_approve"}:
            requested = command.get("targets")
            if (
                not isinstance(requested, list)
                or not requested
                or len({
                    item.get("target_block_key")
                    for item in requested
                    if isinstance(item, dict)
                }) != len(requested)
            ):
                raise ValueError("Propagation targets must be a non-empty unique list")
            verified = []
            for item in requested:
                if not isinstance(item, dict) or set(item) != {
                    "target_block_key", "proposal_sha256"
                }:
                    raise ValueError("Each propagation target requires key and proposal hash")
                candidate = by_target.get(item["target_block_key"])
                if (
                    candidate is None
                    or not candidate["applicable"]
                    or candidate["proposal_sha256"] != item["proposal_sha256"]
                ):
                    raise RuntimeError(
                        f"stale or ineligible propagation target: {item['target_block_key']}"
                    )
                if (
                    command["action"] == "auto_approve"
                    and candidate["policy_evaluation"]["outcome"] != "auto_approved"
                ):
                    raise RuntimeError(
                        f"policy does not authorize automatic approval: {item['target_block_key']}"
                    )
                verified.append(candidate)
            command["_verified_propagation_candidates"] = verified
            if command["action"] == "auto_approve":
                policy_refs = {
                    canonical_bytes(candidate["policy_evaluation"]["policy_ref"])
                    for candidate in verified
                }
                if len(policy_refs) != 1 or any(
                    candidate["policy_evaluation"]["policy_ref"] is None
                    for candidate in verified
                ):
                    raise RuntimeError("automatic approvals require one exact policy")
                command["_verified_policy_ref"] = copy.deepcopy(
                    verified[0]["policy_evaluation"]["policy_ref"]
                )
        else:
            target_keys = command.get("target_block_keys")
            if (
                not isinstance(target_keys, list)
                or not target_keys
                or any(key not in by_target for key in target_keys)
            ):
                raise ValueError("Propagation rejection targets are invalid")
    sequence = len(review["events"]) + 1
    decision_id = f'{block["document_key"]}:decision:{sequence:06d}'
    affected, locators, changes = apply_command(block, command, decision_id, sequence)
    block_bytes = canonical_bytes(block)
    result_hash = digest_bytes(block_bytes)
    previous_hash = review["events"][-1]["event_sha256"] if review["events"] else None
    automatic = command["action"] == "auto_approve"
    event = {
        "decision_id": decision_id, "sequence": sequence,
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reviewer": (
            {
                "reviewer_id": "staged-pdf-policy-evaluator",
                "display_name": "Staged PDF policy evaluator",
                "role": "automation",
            }
            if automatic
            else {
                "reviewer_id": "local-reviewer",
                "display_name": "Local reviewer",
                "role": "data-reviewer",
            }
        ),
        "action": command["action"], "reason": reason,
        "prior_artifact_sha256": prior_hash, "result_artifact_sha256": result_hash,
        "previous_event_sha256": previous_hash, "event_sha256": "0" * 64,
        "affected_keys": affected, "source_locators": locators, "changes": changes,
    }
    if block.get("schema_version") == 2:
        event["reviewer"]["actor_type"] = "system" if automatic else "human"
        event["decision_basis"] = "template_policy" if automatic else "reviewer"
        event["policy_ref"] = (
            copy.deepcopy(command["_verified_policy_ref"]) if automatic else None
        )
    event_hash_payload = copy.deepcopy(event); event_hash_payload.pop("event_sha256")
    event["event_sha256"] = digest_bytes(canonical_bytes(event_hash_payload))
    target_ref = {
        "artifact_type": "block_inventory",
        "artifact_key": block["artifact_key"],
        "sha256": result_hash,
    }
    if block.get("schema_version") == 2:
        target_ref["schema_version"] = 2
    review["target_artifacts"] = [target_ref]
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
    parser.add_argument("--workspace-version", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    try:
        configure_workspace(args.workspace_version)
        print(json.dumps(update(args.command), separators=(",", ":")))
        return 0
    except RuntimeError as error:
        conflict = any(
            marker in str(error)
            for marker in ("stale artifact hash", "stale review head", "stale propagation")
        )
        print(json.dumps({"error": str(error), "kind": "conflict" if conflict else "validation"}, separators=(",", ":")))
        return 2
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), "kind": "invalid"}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

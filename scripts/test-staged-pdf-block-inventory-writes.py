#!/usr/bin/env python3
"""Regression tests for reviewed Stage 1 block mutations."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/update-staged-pdf-block-inventory.py"
PILOT_BLOCK = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v1/stage-1/block-inventory.json"


def load_writer():
    spec = importlib.util.spec_from_file_location("stage1_writer", WRITER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(WRITER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlockInventoryWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.workspace = Path(tempfile.mkdtemp(prefix="stage-1-write-test-", dir=ROOT / "tmp"))
        self.writer = load_writer()
        self.writer.BLOCK_PATH = self.workspace / "stage-1/block-inventory.json"
        self.writer.REVIEW_PATH = self.workspace / "review/review-decisions.json"
        self.writer.BLOCK_PATH.parent.mkdir(parents=True)
        shutil.copyfile(PILOT_BLOCK, self.writer.BLOCK_PATH)

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def apply(self, command: dict):
        command.update({
            "document_key": "ctown-budget-2026-2027",
            "expected_artifact_sha256": self.writer.digest_path(self.writer.BLOCK_PATH),
            "reason": "Source image reviewed in test",
        })
        path = self.workspace / "command.json"
        path.write_text(json.dumps(command), encoding="utf-8")
        return self.writer.update(path)

    def test_blocks_regions_and_relationships_append_valid_events(self) -> None:
        created = self.apply({
            "action": "create", "page_number": 18,
            "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.8, "y1": 0.7},
            "block_type": "formatted_text", "financial_candidate": False,
        })
        self.assertEqual(created["validation_mode"], "incremental")
        self.assertEqual(created["affected_page_numbers"], [18])
        key = created["affected_keys"][0]
        self.apply({"action": "resize", "block_key": key, "bbox": {"x0": 0.08, "y0": 0.18, "x1": 0.9, "y1": 0.8}})
        region = self.apply({"action": "create_region", "block_key": key, "region_type": "paragraph", "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.8, "y1": 0.3}})["affected_keys"][1]
        self.apply({"action": "resize_region", "block_key": key, "region_key": region, "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.85, "y1": 0.32}})
        self.apply({"action": "set_region_type", "block_key": key, "region_key": region, "region_type": "bullet_list"})
        self.apply({"action": "delete_region", "block_key": key, "region_key": region})
        self.apply({"action": "set_type", "block_key": key, "block_type": "chart", "financial_candidate": True})
        target = self.apply({
            "action": "create", "page_number": 19,
            "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.8, "y1": 0.7},
            "block_type": "table", "financial_candidate": True,
        })["affected_keys"][0]
        relationship = self.apply({
            "action": "link", "relationship_type": "graph_source_table",
            "source": {"block_key": key, "region_key": None},
            "target": {"block_key": "ctown-budget-2026-2027:p018:body", "region_key": None},
        })
        self.assertEqual(relationship["affected_page_numbers"], [18])
        relationship = relationship["affected_keys"][0]
        self.apply({"action": "unlink", "relationship_key": relationship})
        continuation = self.apply({
            "action": "link", "relationship_type": "table_continuation",
            "source": {"block_key": "ctown-budget-2026-2027:p018:body", "region_key": None},
            "target": {"block_key": target, "region_key": None},
        })
        self.assertEqual(continuation["affected_page_numbers"], [18, 19])
        self.apply({"action": "unlink", "relationship_key": continuation["affected_keys"][0]})
        block = self.writer.read_json(self.writer.BLOCK_PATH)
        overview = next(item for item in block["records"] if item["block_key"] == "ctown-budget-2026-2027:p018:body")
        row_label = next(cell for cell in overview["table_grid"]["cells"] if cell["cell_type"] == "row_label")
        detail = self.apply({
            "action": "link", "relationship_type": "overview_detail",
            "source": {"block_key": overview["block_key"], "region_key": row_label["cell_key"]},
            "target": {"block_key": target, "region_key": None},
        })
        self.assertEqual(detail["affected_page_numbers"], [18, 19])
        self.apply({"action": "unlink", "relationship_key": detail["affected_keys"][0]})
        self.apply({"action": "delete", "block_key": key})
        self.apply({"action": "delete", "block_key": target})
        block = self.writer.read_json(self.writer.BLOCK_PATH)
        review = self.writer.read_json(self.writer.REVIEW_PATH)
        self.assertFalse(any(item["block_key"] == key for item in block["records"]))
        self.assertEqual(
            [event["action"] for event in review["events"]],
            ["create", "resize", "create_region", "resize_region", "set_region_type", "delete_region", "set_type", "create", "link", "unlink", "link", "unlink", "link", "unlink", "delete", "delete"],
        )
        self.assertEqual(self.writer.load_validator().validate_payload(block), [])
        self.assertEqual(self.writer.load_validator().validate_payload(review), [])

    def test_stale_hash_is_rejected_without_file_changes(self) -> None:
        before = self.writer.BLOCK_PATH.read_bytes()
        command = {
            "action": "resize", "block_key": "ctown-budget-2026-2027:p018:body",
            "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.8, "y1": 0.7},
            "document_key": "ctown-budget-2026-2027", "expected_artifact_sha256": "0" * 64,
            "reason": "Stale test",
        }
        path = self.workspace / "command.json"
        path.write_text(json.dumps(command), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "stale artifact hash"):
            self.writer.update(path)
        self.assertEqual(self.writer.BLOCK_PATH.read_bytes(), before)
        self.assertFalse(self.writer.REVIEW_PATH.exists())

    def test_formatted_text_parent_resize_scales_internal_regions(self) -> None:
        block_key = "ctown-budget-2026-2027:p034:body"
        before = next(
            item for item in self.writer.read_json(self.writer.BLOCK_PATH)["records"]
            if item["block_key"] == block_key
        )
        resized_bbox = {**before["bbox"], "y0": round(before["bbox"]["y0"] + 0.05, 6)}

        self.apply({"action": "resize", "block_key": block_key, "bbox": resized_bbox})

        after = next(
            item for item in self.writer.read_json(self.writer.BLOCK_PATH)["records"]
            if item["block_key"] == block_key
        )
        self.assertEqual(after["bbox"], resized_bbox)
        self.assertEqual(after["regions"][0]["bbox"]["y0"], resized_bbox["y0"])
        self.assertTrue(all(
            resized_bbox["y0"] <= region["bbox"]["y0"] < region["bbox"]["y1"] <= resized_bbox["y1"]
            for region in after["regions"]
        ))

    def test_recalculate_formatted_regions_replaces_internal_structure(self) -> None:
        block_key = "ctown-budget-2026-2027:p034:body"

        result = self.apply({"action": "redetect_regions", "block_key": block_key})

        block = next(
            item for item in self.writer.read_json(self.writer.BLOCK_PATH)["records"]
            if item["block_key"] == block_key
        )
        self.assertTrue(block["regions"])
        self.assertEqual(block["review"]["status"], "needs_review")
        self.assertTrue(all(
            region["region_key"] in result["affected_keys"]
            and region["review"]["status"] == "needs_review"
            and block["bbox"]["x0"] <= region["bbox"]["x0"] < region["bbox"]["x1"] <= block["bbox"]["x1"]
            and block["bbox"]["y0"] <= region["bbox"]["y0"] < region["bbox"]["y1"] <= block["bbox"]["y1"]
            for region in block["regions"]
        ))

    def test_table_grid_redetect_dividers_types_split_merge_and_resize(self) -> None:
        block_key = "ctown-budget-2026-2027:p018:body"
        first = self.apply({"action": "redetect_table_grid", "block_key": block_key})
        block = self.writer.read_json(self.writer.BLOCK_PATH)
        table = next(item for item in block["records"] if item["block_key"] == block_key)
        grid = table["table_grid"]
        self.assertGreater(len(grid["row_boundaries"]), 3)
        self.assertGreater(len(grid["column_boundaries"]), 2)
        self.assertIn("row_label", {cell["cell_type"] for cell in grid["cells"]})
        self.assertIn("cell", {cell["cell_type"] for cell in grid["cells"]})
        self.assertIn("total", {cell["cell_type"] for cell in grid["cells"]})
        self.assertEqual(table["review"]["status"], "needs_review")
        self.assertTrue(all(cell["cell_key"] in first["affected_keys"] for cell in grid["cells"]))

        divider = grid["column_boundaries"][1]
        moved = round(divider + .005, 6)
        self.apply({"action": "move_table_divider", "block_key": block_key, "axis": "column", "divider_index": 1, "position": moved})
        block = self.writer.read_json(self.writer.BLOCK_PATH)
        table = next(item for item in block["records"] if item["block_key"] == block_key)
        self.assertEqual(table["table_grid"]["column_boundaries"][1], moved)

        first_cell = table["table_grid"]["cells"][0]
        self.apply({"action": "set_table_cell_type", "block_key": block_key, "cell_key": first_cell["cell_key"], "cell_type": "total"})
        original_rows = len(table["table_grid"]["row_boundaries"]) - 1
        self.apply({"action": "split_table_rows", "block_key": block_key, "start_index": 0, "end_index": 0})
        block = self.writer.read_json(self.writer.BLOCK_PATH); table = next(item for item in block["records"] if item["block_key"] == block_key)
        self.assertEqual(len(table["table_grid"]["row_boundaries"]) - 1, original_rows + 1)
        self.assertEqual([cell["cell_type"] for cell in table["table_grid"]["cells"] if cell["column_index"] == 0][:2], ["total", "total"])
        conflict_cell = next(cell for cell in table["table_grid"]["cells"] if cell["row_index"] == 1 and cell["column_index"] == 0)
        self.apply({"action": "set_table_cell_type", "block_key": block_key, "cell_key": conflict_cell["cell_key"], "cell_type": "subtotal"})
        self.apply({"action": "merge_table_rows", "block_key": block_key, "start_index": 0, "end_index": 1})
        block = self.writer.read_json(self.writer.BLOCK_PATH); table = next(item for item in block["records"] if item["block_key"] == block_key)
        merged_cell = next(cell for cell in table["table_grid"]["cells"] if cell["row_index"] == 0 and cell["column_index"] == 0)
        self.assertEqual(merged_cell["cell_type"], "cell")

        original_columns = len(table["table_grid"]["column_boundaries"]) - 1
        self.apply({"action": "split_table_columns", "block_key": block_key, "start_index": 0, "end_index": 0})
        block = self.writer.read_json(self.writer.BLOCK_PATH); table = next(item for item in block["records"] if item["block_key"] == block_key)
        self.assertEqual(len(table["table_grid"]["column_boundaries"]) - 1, original_columns + 1)
        split_column_types = [
            cell["cell_type"] for cell in table["table_grid"]["cells"]
            if cell["row_index"] == 0 and cell["column_index"] in {0, 1}
        ]
        self.assertEqual(split_column_types, [merged_cell["cell_type"], merged_cell["cell_type"]])
        self.apply({"action": "merge_table_columns", "block_key": block_key, "start_index": 0, "end_index": 1})
        block = self.writer.read_json(self.writer.BLOCK_PATH); table = next(item for item in block["records"] if item["block_key"] == block_key)
        remerged_cell = next(cell for cell in table["table_grid"]["cells"] if cell["row_index"] == 0 and cell["column_index"] == 0)
        self.assertEqual(remerged_cell["cell_type"], merged_cell["cell_type"])

        resized_bbox = {"x0": 0.19, "y0": 0.63, "x1": 0.78, "y1": 0.77}
        self.apply({
            "action": "resize", "block_key": block_key, "bbox": resized_bbox,
            "redetect_table_grid": True,
        })
        block = self.writer.read_json(self.writer.BLOCK_PATH)
        table = next(item for item in block["records"] if item["block_key"] == block_key)
        self.assertEqual(table["bbox"], resized_bbox)
        self.assertTrue(table["table_grid"]["cells"])
        self.assertEqual(table["table_grid"]["column_boundaries"][0], resized_bbox["x0"])
        self.assertEqual(table["table_grid"]["column_boundaries"][-1], resized_bbox["x1"])
        self.assertEqual(table["table_grid"]["row_boundaries"][0], resized_bbox["y0"])
        self.assertEqual(table["table_grid"]["row_boundaries"][-1], resized_bbox["y1"])


if __name__ == "__main__":
    unittest.main()

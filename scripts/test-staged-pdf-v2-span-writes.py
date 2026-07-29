#!/usr/bin/env python3
"""Regression tests for version 2 spanning-cell and table-title writes."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts" / "update-staged-pdf-block-inventory-v2.py"
V1_FIXTURES_PATH = ROOT / "scripts" / "test-staged-pdf-artifact-schemas.py"
V2_FIXTURES_PATH = ROOT / "scripts" / "test-staged-pdf-artifact-schemas-v2.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Version2SpanWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.workspace = Path(tempfile.mkdtemp(prefix="stage-1-v2-write-", dir=ROOT / "tmp"))
        self.writer = load("stage1_v2_writer", WRITER_PATH)
        self.v1 = load("stage1_v1_fixtures", V1_FIXTURES_PATH)
        self.v2 = load("stage1_v2_fixtures", V2_FIXTURES_PATH)
        self.writer.BLOCK_PATH = self.workspace / "stage-1/block-inventory.json"
        self.writer.REVIEW_PATH = self.workspace / "review/review-decisions.json"
        self.writer.BLOCK_PATH.parent.mkdir(parents=True)
        self.artifact = self.v2.version_2(self.v1.block_inventory())
        self.writer.BLOCK_PATH.write_bytes(self.writer.canonical_bytes(self.artifact))

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def apply(self, command: dict):
        command.update({
            "document_key": "document",
            "expected_artifact_sha256": self.writer.digest_path(self.writer.BLOCK_PATH),
            "reason": "Version 2 span review test",
        })
        path = self.workspace / "command.json"
        path.write_text(json.dumps(command), encoding="utf-8")
        return self.writer.update(path)

    def block(self) -> dict:
        return self.writer.read_json(self.writer.BLOCK_PATH)["records"][0]

    def test_formatted_text_parent_resize_scales_internal_regions(self) -> None:
        block = self.artifact["records"][0]
        block["block_type"] = "formatted_text"
        block["table_grid"] = None
        block["regions"] = [{
            "region_key": f'{block["block_key"]}:region-001',
            "region_type": "paragraph",
            "bbox": copy.deepcopy(block["bbox"]),
            "text_excerpt": "Formatted text",
            "review": {"status": "proposed", "reason_codes": ["test"], "decision_ids": []},
        }]
        self.writer.BLOCK_PATH.write_bytes(self.writer.canonical_bytes(self.artifact))
        resized_bbox = {**block["bbox"], "y0": round(block["bbox"]["y0"] + 0.05, 6)}

        self.apply({"action": "resize", "block_key": block["block_key"], "bbox": resized_bbox})

        after = self.block()
        self.assertEqual(after["bbox"], resized_bbox)
        self.assertEqual(after["regions"][0]["bbox"], resized_bbox)

    def test_merge_title_split_and_explicit_span_round_trip(self) -> None:
        block_key = "document:p001:b001"
        top = [
            "document:p001:b001:cell-0-0",
            "document:p001:b001:cell-0-1",
        ]
        merged_result = self.apply({
            "action": "merge_table_cells",
            "block_key": block_key,
            "cell_keys": top,
        })
        merged = next(
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["cell_key"].endswith("-merged")
        )
        self.assertNotIn("row_span", merged)
        self.assertEqual(merged["column_span"], 2)

        self.apply({
            "action": "set_table_cell_type",
            "block_key": block_key,
            "cell_key": merged["cell_key"],
            "cell_type": "table_title",
        })
        title = next(
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["cell_type"] == "table_title"
        )
        self.assertEqual((title["row_index"], title["column_index"]), (0, 0))
        self.assertEqual(title["column_span"], 2)

        self.apply({
            "action": "split_table_cell",
            "block_key": block_key,
            "cell_key": title["cell_key"],
        })
        top_cells = [
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["row_index"] == 0
        ]
        self.assertEqual(len(top_cells), 2)
        self.assertTrue(all("row_span" not in cell and "column_span" not in cell for cell in top_cells))
        self.assertTrue(all(cell["cell_type"] == "column_label" for cell in top_cells))

        bottom_left = next(
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["row_index"] == 1 and cell["column_index"] == 0
        )
        self.apply({
            "action": "set_table_cell_span",
            "block_key": block_key,
            "cell_key": bottom_left["cell_key"],
            "row_span": 1,
            "column_span": 2,
        })
        spanned = next(
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["cell_key"] == bottom_left["cell_key"]
        )
        self.assertNotIn("row_span", spanned)
        self.assertEqual(spanned["column_span"], 2)

        self.apply({
            "action": "split_table_cell",
            "block_key": block_key,
            "cell_key": spanned["cell_key"],
        })
        unit_cells = self.block()["table_grid"]["cells"]
        top_left = next(
            cell for cell in unit_cells
            if cell["row_index"] == 0 and cell["column_index"] == 0
        )
        self.apply({
            "action": "set_table_cell_span",
            "block_key": block_key,
            "cell_key": top_left["cell_key"],
            "row_span": 2,
            "column_span": 2,
        })
        corner = next(
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["cell_key"] == top_left["cell_key"]
        )
        self.assertEqual((corner["row_span"], corner["column_span"]), (2, 2))
        self.assertEqual(len(self.block()["table_grid"]["cells"]), 1)

        self.apply({
            "action": "split_table_cell",
            "block_key": block_key,
            "cell_key": corner["cell_key"],
        })
        restored = self.block()["table_grid"]["cells"]
        self.assertEqual(len(restored), 4)
        self.assertTrue(
            all("row_span" not in cell and "column_span" not in cell for cell in restored)
        )

        review = self.writer.read_json(self.writer.REVIEW_PATH)
        self.assertEqual(
            [event["action"] for event in review["events"]],
            [
                "merge_table_cells",
                "set_table_cell_type",
                "split_table_cell",
                "set_table_cell_span",
                "split_table_cell",
                "set_table_cell_span",
                "split_table_cell",
            ],
        )
        self.assertTrue(all(event["reviewer"]["actor_type"] == "human" for event in review["events"]))
        self.assertTrue(all(event["decision_basis"] == "reviewer" for event in review["events"]))
        self.assertEqual(self.writer.load_validator().validate_payload(self.block_artifact()), [])
        self.assertIn(block_key, merged_result["affected_keys"])

    def block_artifact(self) -> dict:
        return self.writer.read_json(self.writer.BLOCK_PATH)

    def test_bottom_title_and_relationship_protection(self) -> None:
        block_key = "document:p001:b001"
        bottom_left = "document:p001:b001:cell-1-0"
        self.apply({
            "action": "set_table_cell_type",
            "block_key": block_key,
            "cell_key": bottom_left,
            "cell_type": "table_title",
        })
        title = next(
            cell for cell in self.block()["table_grid"]["cells"]
            if cell["cell_type"] == "table_title"
        )
        self.assertEqual(title["row_index"] + self.writer.effective_span(title, "row"), 2)
        self.assertEqual(self.writer.effective_span(title, "column"), 2)

        artifact = copy.deepcopy(self.artifact)
        artifact["relationships"] = [{
            "relationship_key": "document:relationship:1",
            "relationship_type": "overview_detail",
            "source": {
                "block_key": block_key,
                "region_key": "document:p001:b001:cell-1-0",
            },
            "target": {"block_key": block_key, "region_key": None},
            "review": self.v1.review(),
        }]
        with self.assertRaisesRegex(ValueError, "used by relationships"):
            self.writer.apply_command(
                artifact,
                {
                    "action": "merge_table_cells",
                    "block_key": block_key,
                    "cell_keys": [
                        "document:p001:b001:cell-1-0",
                        "document:p001:b001:cell-1-1",
                    ],
                },
                "document:decision:000001",
                1,
            )

    def test_formatted_text_title_region_is_accepted(self) -> None:
        block_key = "document:p001:b001"
        self.apply({
            "action": "set_type",
            "block_key": block_key,
            "block_type": "formatted_text",
            "financial_candidate": False,
        })
        result = self.apply({
            "action": "create_region",
            "block_key": block_key,
            "region_type": "title",
            "bbox": {"x0": .2, "y0": .2, "x1": .8, "y1": .3},
        })
        region = next(
            item for item in self.block()["regions"]
            if item["region_key"] in result["affected_keys"]
        )
        self.assertEqual(region["region_type"], "title")
        self.assertEqual(self.writer.load_validator().validate_payload(self.block_artifact()), [])

    def test_version_2_recalculates_formatted_regions_from_source_evidence(self) -> None:
        pilot_root = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v2"
        artifact = self.writer.read_json(pilot_root / "stage-1/block-inventory.json")
        self.writer.SOURCE_PATH = pilot_root / "stage-0/source-evidence.json"
        block = next(
            item for item in artifact["records"]
            if item["block_key"] == "ctown-budget-2026-2027:p034:body"
        )

        affected, _, changes = self.writer.apply_command(
            artifact,
            {"action": "redetect_regions", "block_key": block["block_key"]},
            "ctown-budget-2026-2027:decision:999999",
            999999,
        )

        self.assertTrue(block["regions"])
        self.assertIn(block["block_key"], affected)
        self.assertEqual(changes[0]["field_path"], f'/records/{block["block_key"]}/regions')
        self.assertTrue(all(
            region["region_type"] in {"title", "paragraph", "bullet_list", "sorted_list"}
            and region["review"]["status"] == "needs_review"
            and region["region_key"] in affected
            for region in block["regions"]
        ))


class MigratedPilotCompatibilityTests(unittest.TestCase):
    def test_existing_version_2_review_chain_accepts_next_event(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        workspace = Path(tempfile.mkdtemp(prefix="stage-1-v2-pilot-", dir=ROOT / "tmp"))
        try:
            writer = load("stage1_v2_pilot_writer", WRITER_PATH)
            writer.BLOCK_PATH = workspace / "stage-1/block-inventory.json"
            writer.REVIEW_PATH = workspace / "review/review-decisions.json"
            writer.BLOCK_PATH.parent.mkdir(parents=True)
            writer.REVIEW_PATH.parent.mkdir(parents=True)
            pilot = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v2"
            shutil.copyfile(pilot / "stage-1/block-inventory.json", writer.BLOCK_PATH)
            shutil.copyfile(pilot / "review/review-decisions.json", writer.REVIEW_PATH)
            block = writer.read_json(writer.BLOCK_PATH)
            table = next(record for record in block["records"] if record.get("table_grid"))
            cell = table["table_grid"]["cells"][0]
            command = {
                "document_key": block["document_key"],
                "expected_artifact_sha256": writer.digest_path(writer.BLOCK_PATH),
                "reason": "Migrated review-chain compatibility test",
                "action": "set_table_cell_type",
                "block_key": table["block_key"],
                "cell_key": cell["cell_key"],
                "cell_type": cell["cell_type"],
            }
            command_path = workspace / "command.json"
            command_path.write_text(json.dumps(command), encoding="utf-8")
            result = writer.update(command_path)
            review = writer.read_json(writer.REVIEW_PATH)
            self.assertEqual(result["decision_id"], "ctown-budget-2026-2027:decision:000106")
            self.assertEqual(review["events"][-1]["sequence"], 106)
            self.assertEqual(
                review["events"][-1]["previous_event_sha256"],
                review["events"][-2]["event_sha256"],
            )
            self.assertEqual(writer.load_validator().validate_payload(review), [])
        finally:
            shutil.rmtree(workspace)


if __name__ == "__main__":
    unittest.main()

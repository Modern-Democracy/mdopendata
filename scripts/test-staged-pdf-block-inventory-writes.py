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
            "block_type": "table", "financial_candidate": True,
        })
        key = created["affected_keys"][0]
        self.apply({"action": "resize", "block_key": key, "bbox": {"x0": 0.08, "y0": 0.18, "x1": 0.9, "y1": 0.8}})
        region = self.apply({"action": "create_region", "block_key": key, "region_type": "table_header", "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.8, "y1": 0.3}})["affected_keys"][1]
        self.apply({"action": "resize_region", "block_key": key, "region_key": region, "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.85, "y1": 0.32}})
        self.apply({"action": "set_region_type", "block_key": key, "region_key": region, "region_type": "column_label"})
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
            "target": {"block_key": target, "region_key": None},
        })["affected_keys"][0]
        self.apply({"action": "unlink", "relationship_key": relationship})
        self.apply({"action": "delete", "block_key": key})
        self.apply({"action": "delete", "block_key": target})
        block = self.writer.read_json(self.writer.BLOCK_PATH)
        review = self.writer.read_json(self.writer.REVIEW_PATH)
        self.assertFalse(any(item["block_key"] == key for item in block["records"]))
        self.assertEqual(
            [event["action"] for event in review["events"]],
            ["create", "resize", "create_region", "resize_region", "set_region_type", "delete_region", "set_type", "create", "link", "unlink", "delete", "delete"],
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


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Regression tests for document-scoped structural propagation."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCHER_PATH = ROOT / "scripts/preview-staged-pdf-structural-propagation.py"
WRITER_PATH = ROOT / "scripts/update-staged-pdf-block-inventory-v2.py"
WORKSPACE = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v2"
SOURCE_BLOCK_KEY = "ctown-budget-2026-2027:p018:body"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Version2PropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matcher = load("stage1_propagation_matcher", MATCHER_PATH)
        cls.source = cls.matcher.read_json(WORKSPACE / "stage-0/source-evidence.json")
        cls.block = cls.matcher.read_json(WORKSPACE / "stage-1/block-inventory.json")
        cls.review = cls.matcher.read_json(WORKSPACE / "review/review-decisions.json")

    def setUp(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.workspace = Path(
            tempfile.mkdtemp(prefix="stage-1-propagation-", dir=ROOT / "tmp")
        )
        self.block_path = self.workspace / "block-inventory.json"
        self.review_path = self.workspace / "review-decisions.json"
        shutil.copy2(WORKSPACE / "stage-1/block-inventory.json", self.block_path)
        shutil.copy2(WORKSPACE / "review/review-decisions.json", self.review_path)
        self.writer = load("stage1_propagation_writer", WRITER_PATH)
        self.writer.BLOCK_PATH = self.block_path
        self.writer.REVIEW_PATH = self.review_path
        self.writer.SOURCE_PATH = WORKSPACE / "stage-0/source-evidence.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def preview(self, review: dict | None = None) -> dict:
        return self.matcher.generate_preview(
            self.matcher.read_json(self.block_path),
            self.source,
            review if review is not None else self.matcher.read_json(self.review_path),
            SOURCE_BLOCK_KEY,
        )

    def write_command(self, payload: dict, name: str = "command.json") -> Path:
        path = self.workspace / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def base_command(self, action: str) -> dict:
        return {
            "action": action,
            "document_key": self.block["document_key"],
            "expected_artifact_sha256": self.writer.digest_path(self.block_path),
            "expected_review_artifact_sha256": self.writer.digest_path(self.review_path),
            "reason": "Document-scoped propagation regression",
        }

    def test_preview_is_deterministic_read_only_and_classifies_material_controls(self) -> None:
        before_block = self.block_path.read_bytes()
        before_review = self.review_path.read_bytes()
        first = self.preview()
        second = self.preview()
        self.assertEqual(
            self.matcher.canonical_bytes(first),
            self.matcher.canonical_bytes(second),
        )
        self.assertEqual(self.block_path.read_bytes(), before_block)
        self.assertEqual(self.review_path.read_bytes(), before_review)
        applicable = [item for item in first["candidates"] if item["applicable"]]
        material = [
            item
            for item in first["candidates"]
            if item["fit_class"] == "material_variation"
        ]
        self.assertEqual(len(applicable), 1)
        self.assertEqual(
            applicable[0]["target_block_key"],
            "ctown-budget-2026-2027:p023:body",
        )
        self.assertTrue(material)
        self.assertTrue(
            all(not item["applicable"] and item["proposal"] is None for item in material)
        )

    def test_apply_is_atomic_and_appends_exact_audit_event(self) -> None:
        preview = self.preview()
        candidate = next(item for item in preview["candidates"] if item["applicable"])
        source_before = copy.deepcopy(
            next(
                item
                for item in self.matcher.read_json(self.block_path)["records"]
                if item["block_key"] == SOURCE_BLOCK_KEY
            )
        )
        command = self.base_command("apply_template")
        command.update({
            "source_block_key": SOURCE_BLOCK_KEY,
            "pattern_sha256": preview["pattern_sha256"],
            "targets": [{
                "target_block_key": candidate["target_block_key"],
                "proposal_sha256": candidate["proposal_sha256"],
            }],
        })
        result = self.writer.update(self.write_command(command))
        updated = self.matcher.read_json(self.block_path)
        review = self.matcher.read_json(self.review_path)
        source_after = next(
            item for item in updated["records"] if item["block_key"] == SOURCE_BLOCK_KEY
        )
        target = next(
            item
            for item in updated["records"]
            if item["block_key"] == candidate["target_block_key"]
        )
        self.assertEqual(source_after, source_before)
        self.assertEqual(result["action"], "apply_template")
        self.assertEqual(target["review"]["status"], "approved")
        self.assertEqual(
            target["confidence"]["reason_codes"],
            ["document-structural-propagation"],
        )
        self.assertEqual(review["events"][-1]["action"], "apply_template")
        self.assertEqual(review["events"][-1]["affected_keys"], [target["block_key"]])
        validator = self.writer.load_validator()
        self.assertEqual(validator.validate_artifact_set([updated, review]), [])

    def test_stale_review_head_rejects_complete_apply(self) -> None:
        preview = self.preview()
        candidate = next(item for item in preview["candidates"] if item["applicable"])
        command = self.base_command("apply_template")
        command.update({
            "expected_review_artifact_sha256": "0" * 64,
            "source_block_key": SOURCE_BLOCK_KEY,
            "pattern_sha256": preview["pattern_sha256"],
            "targets": [{
                "target_block_key": candidate["target_block_key"],
                "proposal_sha256": candidate["proposal_sha256"],
            }],
        })
        before = (self.block_path.read_bytes(), self.review_path.read_bytes())
        with self.assertRaisesRegex(RuntimeError, "stale review head"):
            self.writer.update(self.write_command(command))
        self.assertEqual(
            (self.block_path.read_bytes(), self.review_path.read_bytes()),
            before,
        )

    def test_rejection_becomes_negative_control_on_later_preview(self) -> None:
        preview = self.preview()
        target = next(
            item
            for item in preview["candidates"]
            if item["fit_class"] == "material_variation"
        )
        command = self.base_command("reject")
        command.update({
            "source_block_key": SOURCE_BLOCK_KEY,
            "pattern_sha256": preview["pattern_sha256"],
            "target_block_keys": [target["target_block_key"]],
        })
        self.writer.update(self.write_command(command, "reject.json"))
        later = self.preview()
        rejected = next(
            item
            for item in later["candidates"]
            if item["target_block_key"] == target["target_block_key"]
        )
        self.assertEqual(rejected["fit_class"], "one_off")
        self.assertFalse(rejected["applicable"])
        event = self.matcher.read_json(self.review_path)["events"][-1]
        self.assertEqual(event["action"], "reject")
        self.assertTrue(
            event["changes"][0]["field_path"].startswith(
                "/propagation_negative_controls/"
            )
        )


if __name__ == "__main__":
    unittest.main()

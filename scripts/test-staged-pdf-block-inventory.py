#!/usr/bin/env python3
"""Regression tests for the deterministic Stage 1 block-inventory generator."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlockInventoryGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage0 = load("stage0_generator", ROOT / "scripts" / "generate-staged-pdf-source-evidence.py")
        cls.stage1 = load("stage1_generator", ROOT / "scripts" / "generate-staged-pdf-block-inventory.py")

    def setUp(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.workspace = Path(tempfile.mkdtemp(prefix="stage-1-test-", dir=ROOT / "tmp"))
        self.pdf = self.workspace / "fixture.pdf"
        self.stage0_out = self.workspace / "stage-0"
        self.stage1_out = self.workspace / "stage-1"
        with fitz.open() as document:
            page = document.new_page(width=612, height=792)
            page.insert_text((72, 72), "2026 2027 Operating Budget Revenue 10,000 Expense 8,000")
            page.insert_text((72, 300), "Forecast variance 2,000 financial statement")
            page.insert_text((300, 760), "1")
            document.save(self.pdf)
        self.stage0.generate(
            pdf=self.pdf, output=self.stage0_out, document_key="test-budget",
            municipality_key="charlottetown", document_kind="budget", title="Test budget",
            source_uri=None, render_dpi=72, thumbnail_dpi=72, minimum_embedded_word_count=5,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def generate(self):
        return self.stage1.generate(
            source_evidence=self.stage0_out / "source-evidence.json", output=self.stage1_out,
        )

    def test_generates_schema_valid_page_complete_inventory(self) -> None:
        artifact, artifact_hash, state = self.generate()
        self.assertEqual(state, "created")
        self.assertEqual(len(artifact["page_dispositions"]), 1)
        self.assertTrue(artifact["records"])
        self.assertEqual(
            artifact["page_dispositions"][0]["block_keys"],
            [record["block_key"] for record in artifact["records"]],
        )
        self.assertEqual(artifact_hash, self.stage1.sha256_path(self.stage1_out / "block-inventory.json"))
        self.assertEqual(self.stage1.load_validator().validate_payload(artifact), [])

    def test_identical_rerun_is_no_op_and_conflict_is_refused(self) -> None:
        _, first_hash, _ = self.generate()
        _, second_hash, state = self.generate()
        self.assertEqual((second_hash, state), (first_hash, "unchanged"))
        (self.stage1_out / "unexpected.txt").write_text("conflict", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Stage 1 content conflict"):
            self.generate()


if __name__ == "__main__":
    unittest.main()

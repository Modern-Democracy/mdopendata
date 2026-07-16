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

    def test_detects_table_grid_headers_labels_cells_subtotals_and_totals(self) -> None:
        def word(text: str, x0: float, y0: float, x1: float, y1: float) -> dict:
            return {"text": text, "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1}}

        words = [
            word("Operating", .10, .06, .20, .08), word("Budget", .21, .06, .29, .08),
            word("Department", .10, .10, .24, .12), word("2026", .55, .10, .61, .12),
            word("Budget", .62, .10, .70, .12), word("2027", .78, .10, .84, .12),
            word("Parks", .10, .20, .18, .22), word("1,250", .56, .20, .63, .22), word("1,500", .79, .20, .86, .22),
            word("Sub-Total", .10, .30, .22, .32), word("1,250", .56, .30, .63, .32), word("1,500", .79, .30, .86, .32),
            word("Total", .10, .40, .17, .42), word("1,250", .56, .40, .63, .42), word("1,500", .79, .40, .86, .42),
        ]
        grid = self.stage1.table_grid(
            "test-budget:p001:body", words, {"x0": .05, "y0": .05, "x1": .90, "y1": .45},
        )
        types = [cell["cell_type"] for cell in grid["cells"]]
        self.assertIn("table_header", types)
        self.assertIn("column_label", types)
        self.assertIn("row_label", types)
        self.assertGreaterEqual(types.count("cell"), 2)
        self.assertIn("subtotal", types)
        self.assertIn("total", types)
        self.assertEqual(len(grid["cells"]), (len(grid["row_boundaries"]) - 1) * (len(grid["column_boundaries"]) - 1))
        self.assertTrue(all(cell["review"]["status"] == "proposed" for cell in grid["cells"]))


if __name__ == "__main__":
    unittest.main()

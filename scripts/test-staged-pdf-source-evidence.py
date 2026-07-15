#!/usr/bin/env python3
"""Regression tests for the deterministic Stage 0 source-evidence generator."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate-staged-pdf-source-evidence.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("stage0_generator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load generator: {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourceEvidenceGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def setUp(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.workspace = Path(tempfile.mkdtemp(prefix="stage-0-test-", dir=ROOT / "tmp"))
        self.pdf = self.workspace / "fixture.pdf"
        self.output = self.workspace / "output"
        with fitz.open() as document:
            page = document.new_page(width=612, height=792)
            page.insert_text(
                (72, 72),
                "Charlottetown budget source evidence deterministic fixture words",
            )
            document.save(self.pdf)

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def generate(self):
        return self.generator.generate(
            pdf=self.pdf,
            output=self.output,
            document_key="test-budget",
            municipality_key="charlottetown",
            document_kind="budget",
            title="Test budget",
            source_uri=None,
            render_dpi=72,
            thumbnail_dpi=72,
            minimum_embedded_word_count=5,
        )

    def test_generates_valid_complete_source_evidence(self) -> None:
        artifact, artifact_hash, state = self.generate()

        self.assertEqual(state, "created")
        self.assertEqual(len(artifact["pages"]), 1)
        self.assertEqual(artifact["pages"][0]["ocr"]["status"], "not_needed")
        self.assertEqual(
            artifact_hash,
            self.generator.sha256_path(self.output / "source-evidence.json"),
        )
        self.assertTrue((self.output / "renders" / "page-001.png").is_file())
        self.assertTrue((self.output / "thumbnails" / "page-001.png").is_file())
        self.assertTrue((self.output / "embedded-words" / "page-001.json").is_file())
        validator = self.generator.load_artifact_validator()
        self.assertEqual(validator.validate_referenced_files(artifact), [])

    def test_identical_rerun_is_a_no_op(self) -> None:
        _, first_hash, first_state = self.generate()
        first_files = self.generator.directory_hashes(self.output)

        _, second_hash, second_state = self.generate()

        self.assertEqual(first_state, "created")
        self.assertEqual(second_state, "unchanged")
        self.assertEqual(second_hash, first_hash)
        self.assertEqual(self.generator.directory_hashes(self.output), first_files)

    def test_conflicting_existing_output_fails_without_overwrite(self) -> None:
        artifact, _, _ = self.generate()
        render = self.output / "renders" / "page-001.png"
        render.write_bytes(b"changed")

        validator = self.generator.load_artifact_validator()
        self.assertRegex(
            "\n".join(validator.validate_referenced_files(artifact)),
            "SHA-256 mismatch",
        )

        with self.assertRaisesRegex(RuntimeError, "Stage 0 content conflict"):
            self.generate()

        self.assertEqual(render.read_bytes(), b"changed")


if __name__ == "__main__":
    unittest.main()

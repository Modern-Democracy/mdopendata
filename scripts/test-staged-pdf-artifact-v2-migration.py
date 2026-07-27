#!/usr/bin/env python3
"""Regression tests for the staged PDF v1-to-v2 parallel migration."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATOR_PATH = ROOT / "scripts" / "migrate-staged-pdf-artifacts-v1-to-v2.py"
BASE = ROOT / "data" / "budget" / "charlottetown" / "2026-2027" / "staged-pdf"
V1 = BASE / "v1"
V2 = BASE / "v2"
OCCURRED_AT = "2026-07-27T00:00:00Z"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migrator = load_module("staged_pdf_v2_migrator_tests", MIGRATOR_PATH)


class StagedPdfV2MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_path = V1 / "stage-0" / "source-evidence.json"
        cls.blocks_path = V1 / "stage-1" / "block-inventory.json"
        cls.review_path = V1 / "review" / "review-decisions.json"
        cls.baseline_path = V2 / "phase-0" / "baseline-and-controls.json"
        cls.source = migrator.read_json(cls.source_path)
        cls.blocks = migrator.read_json(cls.blocks_path)
        cls.review = migrator.read_json(cls.review_path)
        cls.baseline = migrator.read_json(cls.baseline_path)
        cls.input_hashes = {
            "source_evidence": migrator.digest_path(cls.source_path),
            "block_inventory": migrator.digest_path(cls.blocks_path),
            "review_decisions": migrator.digest_path(cls.review_path),
        }

    def output_paths(self, root: Path) -> dict[str, Path]:
        return {
            "source_evidence": root / "stage-0" / "source-evidence.json",
            "block_inventory": root / "stage-1" / "block-inventory.json",
            "review_decisions": root / "review" / "review-decisions.json",
            "migration_report": root / "phase-2" / "migration-report.json",
        }

    def migrated(self, root: Path):
        return migrator.migrate_payloads(
            self.source,
            self.blocks,
            self.review,
            self.input_hashes,
            self.output_paths(root),
            OCCURRED_AT,
        )

    def test_frozen_version_1_hashes_match_baseline(self) -> None:
        actual = migrator.assert_frozen_inputs(
            self.source_path,
            self.blocks_path,
            self.review_path,
            self.baseline,
        )
        self.assertEqual(actual, self.input_hashes)

    def test_migration_is_canonically_deterministic(self) -> None:
        first = self.migrated(ROOT / "tmp" / "migration-run-a" / "v2")
        second = self.migrated(ROOT / "tmp" / "migration-run-b" / "v2")
        self.assertEqual(
            [migrator.canonical_bytes(value) for value in first],
            [migrator.canonical_bytes(value) for value in second],
        )

    def test_preserves_keys_spans_and_review_history(self) -> None:
        source_v2, blocks_v2, review_v2, report = self.migrated(
            ROOT / "tmp" / "migration-preservation" / "v2"
        )
        migrator.assert_preservation(
            self.source,
            self.blocks,
            self.review,
            source_v2,
            blocks_v2,
            review_v2,
        )
        self.assertEqual(len(review_v2["events"]), len(self.review["events"]) + 1)
        self.assertEqual(review_v2["events"][-1]["action"], "migrate_schema")
        self.assertEqual(review_v2["events"][-1]["reviewer"]["actor_type"], "system")
        self.assertEqual(
            report["review_policies"]["seeded_review_required_policy_count"], 0
        )
        self.assertEqual(report["controls"]["database_write_count"], 0)
        self.assertEqual(report["controls"]["publication_write_count"], 0)

    def test_generated_pilot_set_validates_and_hashes_resolve(self) -> None:
        paths = self.output_paths(V2)
        payloads = [
            migrator.read_json(paths["source_evidence"]),
            migrator.read_json(paths["block_inventory"]),
            migrator.read_json(paths["review_decisions"]),
        ]
        migrator.validate_outputs(payloads)
        report = migrator.read_json(paths["migration_report"])
        for name in ("source_evidence", "block_inventory", "review_decisions"):
            self.assertEqual(
                report["outputs"][name]["sha256"],
                migrator.digest_path(paths[name]),
            )
            self.assertEqual(report["outputs"][name]["schema_version"], 2)

    def test_conflicting_output_is_rejected_before_writes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            root = Path(temporary)
            first = root / "first.json"
            conflict = root / "conflict.json"
            conflict.write_bytes(b"conflict\n")
            with self.assertRaises(FileExistsError):
                migrator.preflight_and_write(
                    {
                        first: b"first\n",
                        conflict: b"replacement\n",
                    }
                )
            self.assertFalse(first.exists())
            self.assertEqual(conflict.read_bytes(), b"conflict\n")


if __name__ == "__main__":
    unittest.main()

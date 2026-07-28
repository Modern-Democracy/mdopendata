#!/usr/bin/env python3
"""Regression tests for Phase 7 parity and handoff readiness."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate-staged-pdf-v2-parity-report.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "staged_pdf_v2_parity", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StagedPdfV2ParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parity = load()

    def test_pilot_structure_is_exact_and_handoff_passes(self) -> None:
        report = self.parity.build_report(self.parity.DEFAULT_PATHS)
        self.assertEqual(report["summary"], {
            "total": 858,
            "matched": 753,
            "missing": 0,
            "extra": 1,
            "changed": 0,
            "provenance_shifted": 104,
        })
        self.assertTrue(report["passed"])
        self.assertEqual(report["blockers"], [])
        self.assertEqual(
            self.parity.load_validator().validate_payload(report), []
        )

    def test_two_clean_comparisons_are_byte_identical(self) -> None:
        first = self.parity.build_report(self.parity.DEFAULT_PATHS)
        second = self.parity.build_report(self.parity.DEFAULT_PATHS)
        self.assertEqual(
            self.parity.canonical_bytes(first),
            self.parity.canonical_bytes(second),
        )
        self.assertEqual(
            first["run_controls"]["first_run_canonical_sha256"],
            first["run_controls"]["second_run_canonical_sha256"],
        )

    def test_review_provenance_shift_has_exact_migration_disposition(self) -> None:
        report = self.parity.build_report(self.parity.DEFAULT_PATHS)
        record = next(
            item for item in report["records"]
            if item["comparison_key"].endswith("decision:000001")
        )
        self.assertEqual(record["status"], "provenance_shifted")
        self.assertEqual(record["changed_fields"], [
            "/decision_basis",
            "/policy_ref",
            "/reviewer/actor_type",
        ])
        self.assertEqual(record["disposition"], "approved_equivalence")
        self.assertEqual(
            record["decision_id"],
            "ctown-budget-2026-2027:decision:000105",
        )

    def test_targeted_shadow_change_is_blocked_with_exact_source_locator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = dict(self.parity.DEFAULT_PATHS)
            shadow_path = root / "block-inventory.json"
            shadow = self.parity.read_json(paths["v2_blocks"])
            target = copy.deepcopy(shadow["records"][0])
            shadow["records"][0]["block_type"] = "formatted_text"
            shadow_path.write_text(
                json.dumps(shadow, ensure_ascii=False),
                encoding="utf-8",
            )
            paths["v2_blocks"] = shadow_path
            report = self.parity.build_report(paths)
        record = next(
            item for item in report["records"]
            if item["comparison_key"] == f"block:{target['block_key']}"
        )
        self.assertEqual(record["status"], "changed")
        self.assertEqual(record["changed_fields"], ["/block_type"])
        self.assertEqual(record["disposition"], "blocked_review")
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["blockers"][0]["blocker_key"],
            "phase-7:unresolved-parity-discrepancies",
        )
        self.assertIn(
            record["comparison_key"],
            report["blockers"][0]["affected_comparison_keys"],
        )
        self.assertEqual(
            record["source_locators"][0]["page_number"],
            target["page_number"],
        )

    def test_generation_does_not_change_frozen_inputs(self) -> None:
        before = {
            name: digest(path)
            for name, path in self.parity.DEFAULT_PATHS.items()
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "parity-report.json"
            report = self.parity.build_report(self.parity.DEFAULT_PATHS)
            self.assertEqual(
                self.parity.write_atomic(
                    output, self.parity.canonical_bytes(report)
                ),
                "created",
            )
            self.assertEqual(
                self.parity.write_atomic(
                    output, self.parity.canonical_bytes(report)
                ),
                "unchanged",
            )
        after = {
            name: digest(path)
            for name, path in self.parity.DEFAULT_PATHS.items()
        }
        self.assertEqual(before, after)

    def test_local_reviewer_exposes_validated_read_only_parity(self) -> None:
        server = (ROOT / "web/server.js").read_text(encoding="utf-8")
        html = (
            ROOT / "web/public/pdf-inventory-review/index.html"
        ).read_text(encoding="utf-8")
        app = (
            ROOT / "web/public/pdf-inventory-review/app.js"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "loadPdfInventoryParityReport", server
        )
        self.assertIn(
            "stagedPdfValidatorPath, pdfInventoryReviewParityArtifactPath",
            server,
        )
        self.assertIn(
            "Baseline parity and handoff", html
        )
        self.assertIn(
            "fetchJson(`${apiRoot}/parity`).then", app
        )

    def test_version_two_is_default_with_version_one_rollback(self) -> None:
        server = (ROOT / "web/server.js").read_text(encoding="utf-8")
        launcher = (
            ROOT / "scripts/start-staged-pdf-review.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'process.env.PDF_INVENTORY_REVIEW_SCHEMA_VERSION || "2"',
            server,
        )
        self.assertIn("[int]$SchemaVersion = 2", launcher)
        self.assertIn("[ValidateSet(1, 2)]", launcher)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Regression tests for live Snapshot 3 verification."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-staged-pdf-v2-live-snapshot.py"


def load():
    spec = importlib.util.spec_from_file_location("live_snapshot", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = load()
        cls.shadow = cls.verifier.load(cls.verifier.SHADOW_PATH)
        cls.manifest = cls.verifier.load(cls.verifier.MANIFEST_PATH)
        cls.expected = cls.verifier.expected_summary(
            cls.shadow, cls.manifest
        )

    def test_expected_set_is_complete_and_unique(self) -> None:
        self.assertEqual(self.expected["observation_count"], 2290)
        self.assertEqual(self.expected["distinct_semantic_count"], 2290)
        self.assertEqual(self.expected["source_link_count"], 2290)
        self.assertEqual(self.expected["distinct_source_link_count"], 2290)

    def test_sql_is_snapshot_and_document_scoped(self) -> None:
        sql = self.verifier.verification_sql()
        self.assertIn("po.snapshot_id=3", sql)
        self.assertIn("s.document_id=9", sql)
        self.assertIn("string_agg(canonical_record", sql)
        self.assertNotIn("INSERT ", sql.upper())
        self.assertNotIn("UPDATE ", sql.upper())
        self.assertNotIn("DELETE ", sql.upper())

    def test_mismatch_fails_closed(self) -> None:
        actual = {
            "snapshot_id": 3,
            "release_label": "test",
            "status": "published",
            "source_document_ids": [7, 8, 9],
            "snapshot_observation_count": 6381,
            **self.expected,
            "observations_without_source": 0,
        }
        actual["semantic_digest"] = "0" * 32
        report = self.verifier.build_report(
            self.expected, actual, self.shadow
        )
        self.assertFalse(report["passed"])
        self.assertFalse(report["controls"]["semantic_set_matches"])

    def test_materialized_live_verification_passes_all_controls(self) -> None:
        report = self.verifier.load(self.verifier.OUTPUT_PATH)
        self.assertTrue(report["passed"])
        self.assertEqual(report["transaction_mode"], "read_only")
        self.assertEqual(report["database_write_count"], 0)
        self.assertTrue(all(report["controls"].values()))
        self.assertEqual(
            report["actual"]["semantic_digest"],
            self.expected["semantic_digest"],
        )
        self.assertEqual(
            report["actual"]["source_digest"],
            self.expected["source_digest"],
        )


if __name__ == "__main__":
    unittest.main()

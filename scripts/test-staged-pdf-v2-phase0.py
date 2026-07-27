#!/usr/bin/env python3
"""Verify the frozen version 1 baseline and version 2 control catalogue."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = (
    ROOT
    / "data"
    / "budget"
    / "charlottetown"
    / "2026-2027"
    / "staged-pdf"
    / "v2"
    / "phase-0"
    / "baseline-and-controls.json"
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StagedPdfV2Phase0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = read_json(BASELINE_PATH)

    def test_frozen_version_1_artifact_hashes_match(self) -> None:
        version_1 = self.baseline["version_1"]
        for key in ("schema", "source_evidence", "block_inventory", "review_decisions"):
            record = version_1[key]
            with self.subTest(key=key):
                self.assertEqual(sha256_path(ROOT / record["repo_relpath"]), record["sha256"])
        implementation = version_1["implementation"]
        self.assertEqual(
            sha256_path(ROOT / "scripts" / "generate-staged-pdf-block-inventory.py"),
            implementation["generator_sha256"],
        )
        self.assertEqual(
            sha256_path(ROOT / "scripts" / "update-staged-pdf-block-inventory.py"),
            implementation["writer_sha256"],
        )

    def test_frozen_inventory_counts_match(self) -> None:
        version_1 = self.baseline["version_1"]
        source = read_json(ROOT / version_1["source_evidence"]["repo_relpath"])
        blocks = read_json(ROOT / version_1["block_inventory"]["repo_relpath"])
        decisions = read_json(ROOT / version_1["review_decisions"]["repo_relpath"])
        actual = {
            "pages": len(source["pages"]),
            "blocks": len(blocks["records"]),
            "tables": sum(record["block_type"] == "table" for record in blocks["records"]),
            "cells": sum(
                len(record["table_grid"]["cells"])
                for record in blocks["records"]
                if record.get("table_grid")
            ),
            "formatted_text_regions": sum(len(record["regions"]) for record in blocks["records"]),
            "relationships": len(blocks["relationships"]),
            "review_events": len(decisions["events"]),
        }
        self.assertEqual(actual, version_1["inventory"])
        self.assertEqual(
            decisions["events"][-1]["event_sha256"],
            version_1["review_decisions"]["review_head_sha256"],
        )

    def test_control_catalogue_covers_phase_1_risks(self) -> None:
        positive = set(self.baseline["positive_controls"])
        negative = set(self.baseline["negative_controls"])
        self.assertTrue(
            {
                "omitted-unit-spans",
                "explicit-unit-spans",
                "horizontal-span",
                "vertical-span",
                "two-dimensional-span",
                "top-table-title",
                "bottom-table-title",
                "formatted-text-title",
                "review-required-policy",
                "sample-review-policy",
                "automatic-approval-policy",
            }.issubset(positive)
        )
        self.assertTrue(
            {
                "overlapping-spans",
                "incomplete-span-coverage",
                "out-of-range-span",
                "duplicate-table-title",
                "partial-width-table-title",
                "internal-table-title",
                "material-variation-auto-approval",
                "non-allowlisted-light-variation",
                "unknown-template-policy-reference",
                "policy-drift",
            }.issubset(negative)
        )


if __name__ == "__main__":
    unittest.main()

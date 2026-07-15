#!/usr/bin/env python3
"""Regression checks for controlled application of Gate 5 Batch 01."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "low-confidence-primary-statements-batch-01.json"
APPLIED_PATH = DATA / "controlled-derived" / "low-confidence-primary-statements-batch-01-applied.json"
APPLIED_MD = DATA / "controlled-derived" / "low-confidence-primary-statements-batch-01-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewApplicationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = read_json(BATCH_PATH)
        cls.applied = read_json(APPLIED_PATH)
        cls.records = cls.applied["records"]
        cls.batch_by_key = {record["row_key"]: record for record in cls.batch["records"]}
        cls.raw_by_key: dict[str, dict[str, object]] = {}
        registry = read_json(DATA / "source-document-registry.json")
        for document in registry["documents"]:
            rows = read_json(DATA / document["document_key"] / "raw-tables" / "source_table_rows.json")["records"]
            cls.raw_by_key.update({row["row_key"]: row for row in rows})
        cls.markdown = APPLIED_MD.read_text(encoding="utf-8")

    def test_source_decision_artifact_is_exact_and_fully_approved(self) -> None:
        source = self.applied["source_decision_artifact"]
        self.assertEqual(source["batch_key"], "low_confidence_primary_statements_batch_01")
        self.assertEqual(source["sha256"], hashlib.sha256(BATCH_PATH.read_bytes()).hexdigest())
        self.assertEqual(self.batch["counts"]["approved"], 29)

    def test_application_counts_and_boundary_are_exact(self) -> None:
        self.assertEqual(
            self.applied["counts"],
            {
                "approved_decisions": 29,
                "materialized_rows": 16,
                "excluded_rows": 13,
                "retained_rows": 6,
                "transcribed_rows": 10,
                "raw_rows_mutated": 0,
                "hierarchy_approved": 0,
                "normalization_approved": 0,
                "database_writes": 0,
            },
        )
        self.assertEqual(set(self.applied["decision_boundary"].values()), {False})
        self.assertEqual(len({record["row_key"] for record in self.records}), 29)

    def test_every_application_round_trips_to_batch_and_immutable_raw_row(self) -> None:
        for record in self.records:
            decision = self.batch_by_key[record["row_key"]]
            raw = self.raw_by_key[record["row_key"]]
            self.assertEqual(record["source_batch_record_number"], decision["batch_record_number"])
            self.assertEqual(record["approved_resolution"], decision["proposed_extraction_resolution"])
            self.assertEqual(record["approved_label"], decision["proposed_raw_label"])
            self.assertEqual(record["approved_values"], decision["proposed_raw_values"])
            self.assertEqual(record["immutable_raw_label"], raw["raw_label_candidate"])
            self.assertEqual(record["immutable_raw_text"], raw["raw_text"])
            self.assertEqual(record["immutable_raw_values"], raw["raw_values"])
            self.assertFalse(record["raw_source_mutated"])

    def test_approved_resolutions_are_applied_without_normalization(self) -> None:
        for record in self.records:
            resolution = record["approved_resolution"]
            if resolution == "exclude_non_financial_layout_artifact":
                self.assertEqual(record["application_status"], "excluded_non_financial_layout_artifact")
                self.assertIsNone(record["derived_label"])
                self.assertEqual(record["derived_values"], [])
                self.assertEqual(record["hierarchy_review_status"], "not_applicable")
            elif resolution == "retain_source_verified_raw_row":
                self.assertEqual(record["application_status"], "materialized_from_source_verified_raw_row")
                self.assertEqual(record["derived_values"], record["approved_values"])
                self.assertEqual(record["hierarchy_review_status"], "needs_review")
            else:
                self.assertEqual(record["application_status"], "materialized_from_source_verified_transcription")
                self.assertEqual(record["derived_values"], record["approved_values"])
                self.assertEqual(record["hierarchy_review_status"], "needs_review")
            self.assertIn(record["normalization_review_status"], {"needs_review", "not_applicable"})

    def test_human_application_artifact_contains_every_row_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(f"`{record['row_key']}`"), 1)


if __name__ == "__main__":
    unittest.main()

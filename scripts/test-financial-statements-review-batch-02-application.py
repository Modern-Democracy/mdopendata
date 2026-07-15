#!/usr/bin/env python3
"""Regression checks for controlled application of Gate 5 Batch 02."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "low-confidence-note-schedules-batch-02.json"
APPLIED_PATH = DATA / "controlled-derived" / "low-confidence-note-schedules-batch-02-applied.json"
APPLIED_MD = DATA / "controlled-derived" / "low-confidence-note-schedules-batch-02-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatch02ApplicationTest(unittest.TestCase):
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
        self.assertEqual(source["batch_key"], "low_confidence_note_schedules_batch_02")
        self.assertEqual(source["sha256"], hashlib.sha256(BATCH_PATH.read_bytes()).hexdigest())
        self.assertEqual(self.batch["counts"]["approved"], 111)

    def test_application_counts_and_boundary_are_exact(self) -> None:
        self.assertEqual(
            self.applied["counts"],
            {
                "approved_decisions": 111,
                "materialized_records": 64,
                "materialized_financial_rows": 57,
                "materialized_context_records": 7,
                "excluded_rows": 47,
                "raw_rows_mutated": 0,
                "hierarchy_approved": 0,
                "normalization_approved": 0,
                "database_writes": 0,
            },
        )
        self.assertEqual(set(self.applied["decision_boundary"].values()), {False})
        self.assertEqual(len(self.records), 111)
        self.assertEqual(len({record["row_key"] for record in self.records}), 111)

    def test_every_application_round_trips_to_batch_and_immutable_raw_row(self) -> None:
        for record in self.records:
            decision = self.batch_by_key[record["row_key"]]
            raw = self.raw_by_key[record["row_key"]]
            self.assertEqual(record["source_batch_record_number"], decision["batch_record_number"])
            self.assertEqual(record["approved_resolution"], decision["proposed_extraction_resolution"])
            self.assertEqual(record["approved_label"], decision["proposed_raw_label"])
            self.assertEqual(record["approved_values"], decision["proposed_raw_values"])
            self.assertEqual(record["approved_context_text"], decision["proposed_context_text"])
            self.assertEqual(record["immutable_raw_label"], raw["raw_label_candidate"])
            self.assertEqual(record["immutable_raw_text"], raw["raw_text"])
            self.assertEqual(record["immutable_raw_values"], raw["raw_values"])
            self.assertFalse(record["raw_source_mutated"])

    def test_each_resolution_has_the_exact_controlled_effect(self) -> None:
        for record in self.records:
            resolution = record["approved_resolution"]
            if resolution == "exclude_non_financial_layout_artifact":
                self.assertEqual(record["application_status"], "excluded_non_financial_layout_artifact")
                self.assertIsNone(record["derived_label"])
                self.assertEqual(record["derived_values"], [])
                self.assertIsNone(record["derived_context_text"])
                self.assertEqual(record["hierarchy_review_status"], "not_applicable")
            elif resolution == "replace_with_source_verified_context_transcription":
                self.assertEqual(record["application_status"], "materialized_from_source_verified_context_transcription")
                self.assertEqual(record["derived_context_text"], record["approved_context_text"])
                self.assertEqual(record["derived_values"], [])
                self.assertEqual(record["normalization_review_status"], "not_applicable")
            else:
                self.assertEqual(record["application_status"], "materialized_from_source_verified_transcription")
                self.assertEqual(record["derived_label"], record["approved_label"])
                self.assertEqual(record["derived_values"], record["approved_values"])
                self.assertEqual(record["hierarchy_review_status"], "needs_review")
                self.assertEqual(record["normalization_review_status"], "needs_review")

    def test_source_fidelity_controls_survive_application(self) -> None:
        by_number = {record["application_record_number"]: record for record in self.records}
        self.assertEqual(by_number[28]["derived_values"][2], "(576,000)")
        self.assertEqual(by_number[51]["derived_values"], ["-", "28,526,953", "28,526,953"])
        self.assertEqual(by_number[69]["derived_values"][6], "(499,620)")
        self.assertEqual(by_number[72]["derived_label"], "Property tax")
        self.assertEqual(by_number[103]["derived_context_text"].split()[-1], "2023.")
        self.assertEqual(by_number[108]["derived_values"], ["-", "-", "3,577,713", "3,577,713"])

    def test_human_application_artifact_has_67_page_groups_and_every_row_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(f"`{record['row_key']}`"), 1)
        for document_key, page_number in {
            (record["document_key"], record["pdf_page_number"])
            for record in self.records
        }:
            self.assertEqual(self.markdown.count(f"## {document_key} — PDF page {page_number} "), 1)


if __name__ == "__main__":
    unittest.main()

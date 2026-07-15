#!/usr/bin/env python3
"""Regression checks for controlled application of Gate 5 Batch 03."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "low-confidence-cells-batch-03.json"
APPLIED_PATH = DATA / "controlled-derived" / "low-confidence-cells-batch-03-applied.json"
APPLIED_MD = DATA / "controlled-derived" / "low-confidence-cells-batch-03-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatch03ApplicationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = read_json(BATCH_PATH)
        cls.applied = read_json(APPLIED_PATH)
        cls.records = cls.applied["records"]
        cls.batch_by_key = {record["cell_key"]: record for record in cls.batch["records"]}
        cls.raw_by_key: dict[str, dict[str, object]] = {}
        registry = read_json(DATA / "source-document-registry.json")
        for document in registry["documents"]:
            cells = read_json(
                DATA / document["document_key"] / "raw-tables" / "source_table_cells.json"
            )["records"]
            for cell in cells:
                cls.assertNotIn(cls, cell["cell_key"], cls.raw_by_key)
                cls.raw_by_key[cell["cell_key"]] = cell
        cls.markdown = APPLIED_MD.read_text(encoding="utf-8")

    def test_source_decision_artifact_is_exact_and_fully_approved(self) -> None:
        source = self.applied["source_decision_artifact"]
        self.assertEqual(source["batch_key"], "remaining_low_confidence_cells_batch_03")
        self.assertEqual(source["sha256"], hashlib.sha256(BATCH_PATH.read_bytes()).hexdigest())
        self.assertEqual(self.batch["counts"]["approved"], 228)

    def test_application_counts_and_boundary_are_exact(self) -> None:
        self.assertEqual(
            self.applied["counts"],
            {
                "approved_decisions": 228,
                "materialized_records": 210,
                "materialized_financial_cells": 117,
                "materialized_context_cells": 7,
                "materialized_dash_placeholders": 86,
                "excluded_cells": 18,
                "raw_cells_mutated": 0,
                "hierarchy_approved": 0,
                "normalization_approved": 0,
                "database_writes": 0,
            },
        )
        self.assertEqual(set(self.applied["decision_boundary"].values()), {False})
        self.assertEqual(len(self.records), 228)
        self.assertEqual(len({record["cell_key"] for record in self.records}), 228)

    def test_every_application_round_trips_to_batch_and_immutable_raw_cell(self) -> None:
        for record in self.records:
            decision = self.batch_by_key[record["cell_key"]]
            raw = self.raw_by_key[record["cell_key"]]
            self.assertEqual(record["source_batch_record_number"], decision["batch_record_number"])
            self.assertEqual(record["approved_resolution"], decision["proposed_extraction_resolution"])
            self.assertEqual(record["approved_cell_text"], decision["proposed_cell_text"])
            self.assertEqual(record["approved_cell_values"], decision["proposed_cell_values"])
            self.assertEqual(record["approved_value_state"], decision["proposed_value_state"])
            self.assertEqual(record["immutable_raw_bbox"], raw["bbox"])
            self.assertEqual(record["immutable_raw_text"], raw["raw_text"])
            self.assertEqual(record["immutable_token_class"], raw["token_class"])
            self.assertEqual(record["immutable_parse_status"], raw["parse_status"])
            self.assertEqual(record["immutable_parser_confidence"], raw["parser_confidence"])
            self.assertEqual(record["immutable_raw_review_status"], raw["review_status"])
            self.assertFalse(record["raw_source_mutated"])

    def test_each_resolution_has_the_exact_controlled_effect(self) -> None:
        for record in self.records:
            resolution = record["approved_resolution"]
            if resolution == "replace_with_source_verified_cell_transcription":
                self.assertEqual(record["application_status"], "materialized_from_source_verified_cell_transcription")
                self.assertEqual(record["derived_cell_text"], record["approved_cell_text"])
                self.assertEqual(record["derived_cell_values"], record["approved_cell_values"])
                self.assertEqual(record["derived_value_state"], "amount_or_percentage")
                self.assertEqual(record["normalization_review_status"], "needs_review")
            elif resolution == "replace_with_source_verified_context_transcription":
                self.assertEqual(record["application_status"], "materialized_from_source_verified_context_transcription")
                self.assertEqual(record["derived_cell_text"], record["approved_cell_text"])
                self.assertEqual(record["derived_cell_values"], [])
                self.assertIsNone(record["derived_value_state"])
                self.assertEqual(record["normalization_review_status"], "not_applicable")
            elif resolution == "classify_source_verified_dash_placeholder":
                self.assertEqual(record["application_status"], "materialized_source_verified_dash_placeholder")
                self.assertIn(record["derived_cell_text"], {"-", "- %"})
                self.assertEqual(record["derived_cell_values"], [])
                self.assertEqual(record["derived_value_state"], "source_dash_placeholder")
                self.assertEqual(record["normalization_review_status"], "needs_review")
            else:
                self.assertEqual(resolution, "exclude_non_financial_layout_artifact")
                self.assertEqual(record["application_status"], "excluded_non_financial_layout_artifact")
                self.assertIsNone(record["derived_cell_text"])
                self.assertEqual(record["derived_cell_values"], [])
                self.assertIsNone(record["derived_value_state"])
                self.assertEqual(record["hierarchy_review_status"], "not_applicable")

    def test_source_fidelity_controls_survive_application(self) -> None:
        by_number = {record["application_record_number"]: record for record in self.records}
        self.assertEqual(by_number[16]["derived_cell_values"], ["(792,142)"])
        self.assertEqual(by_number[168]["derived_cell_values"], ["(742,585)"])
        self.assertEqual(by_number[185]["derived_cell_values"], ["35,377,973"])
        self.assertEqual(by_number[211]["derived_cell_text"], "- %")
        self.assertEqual(by_number[211]["derived_value_state"], "source_dash_placeholder")
        self.assertEqual(by_number[225]["derived_cell_values"], ["73,115"])

    def test_human_application_artifact_has_77_page_groups_and_every_cell_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(f"`{record['cell_key']}`"), 1)
        page_groups = {
            (record["document_key"], record["pdf_page_number"])
            for record in self.records
        }
        self.assertEqual(len(page_groups), 77)
        for document_key, page_number in page_groups:
            self.assertEqual(self.markdown.count(f"## {document_key} — PDF page {page_number} "), 1)


if __name__ == "__main__":
    unittest.main()

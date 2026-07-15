#!/usr/bin/env python3
"""Regression checks for Gate 5 remaining low-confidence cell Batch 03."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "low-confidence-cells-batch-03.json"
BATCH_MD = DATA / "review-batches" / "low-confidence-cells-batch-03.md"
ROW_BATCH_PATHS = (
    DATA / "review-batches" / "low-confidence-primary-statements-batch-01.json",
    DATA / "review-batches" / "low-confidence-note-schedules-batch-02.json",
)


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatch03Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = read_json(DATA / "source-document-registry.json")
        cls.batch = read_json(BATCH_PATH)
        cls.records = cls.batch["records"]
        cls.cells_by_key: dict[str, dict[str, object]] = {}
        cls.rows_by_key: dict[str, dict[str, object]] = {}
        cls.tables_by_key: dict[str, dict[str, object]] = {}
        cls.pages_by_table: dict[str, dict[str, object]] = {}
        cls.all_low_confidence_keys: set[str] = set()
        for document in cls.registry["documents"]:
            root = DATA / document["document_key"]
            tables = read_json(root / "table_manifest.json")["records"]
            pages = read_json(root / "raw-tables" / "source_table_pages.json")["records"]
            rows = read_json(root / "raw-tables" / "source_table_rows.json")["records"]
            cells = read_json(root / "raw-tables" / "source_table_cells.json")["records"]
            cls.tables_by_key.update({table["table_key"]: table for table in tables})
            cls.pages_by_table.update({page["table_key"]: page for page in pages})
            cls.rows_by_key.update({row["row_key"]: row for row in rows})
            cls.cells_by_key.update({cell["cell_key"]: cell for cell in cells})
            cls.all_low_confidence_keys.update(
                cell["cell_key"] for cell in cells if float(cell["parser_confidence"]) < 80
            )
        cls.resolved_row_keys = {
            record["row_key"]
            for path in ROW_BATCH_PATHS
            for record in read_json(path)["records"]
        }
        cls.expected_keys = {
            key for key in cls.all_low_confidence_keys
            if cls.cells_by_key[key]["row_key"] not in cls.resolved_row_keys
        }
        cls.markdown = BATCH_MD.read_text(encoding="utf-8")

    def test_batch_is_complete_unsampled_and_excludes_resolved_parent_rows(self) -> None:
        actual_keys = {record["cell_key"] for record in self.records}
        excluded_keys = self.all_low_confidence_keys - self.expected_keys
        self.assertEqual(actual_keys, self.expected_keys)
        self.assertEqual(len(actual_keys), 228)
        self.assertEqual(len(excluded_keys), 177)
        self.assertEqual(len(self.all_low_confidence_keys), 405)
        self.assertTrue(all(self.cells_by_key[key]["row_key"] in self.resolved_row_keys for key in excluded_keys))
        self.assertEqual(self.batch["selection_rule"]["sampling"], "none; every matching cell is included")
        for source, path in zip(self.batch["source_row_decision_batches"], ROW_BATCH_PATHS, strict=True):
            self.assertEqual(source["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_counts_classes_families_and_boundary_are_exact(self) -> None:
        self.assertEqual(
            self.batch["counts"],
            {
                "records": 228,
                "source_pages": 77,
                "documents": 8,
                "parent_rows": 191,
                "all_low_confidence_cells": 405,
                "excluded_by_approved_parent_row_decision": 177,
                "remaining_low_confidence_cells": 228,
                "primary_statement_cells": 51,
                "note_cells": 84,
                "schedule_cells": 93,
                "financial_transcriptions": 117,
                "context_transcriptions": 7,
                "dash_placeholders": 86,
                "layout_artifact_exclusions": 18,
                "revised_and_approved": 228,
                "approved": 228,
            },
        )
        self.assertEqual(
            self.batch["token_class_counts"],
            {"amount_candidate": 51, "dash_candidate": 69, "signed_amount_candidate": 6, "text": 102},
        )
        self.assertEqual(
            self.batch["table_family_counts"],
            {
                "budget_reconciliation_note": 5,
                "cash_flow": 9,
                "changes_in_net_assets_available_for_benefits": 3,
                "changes_in_net_debt": 7,
                "changes_in_pension_obligations": 1,
                "financial_position": 19,
                "note_disclosure_table": 79,
                "operations": 12,
                "segmented_disclosure_schedule": 28,
                "tangible_capital_assets_schedule": 65,
            },
        )
        self.assertEqual(set(self.batch["decision_boundary"].values()), {False})
        self.assertEqual(self.batch["status"], "review_complete")

    def test_every_locator_and_raw_field_round_trips(self) -> None:
        source_files = {document["document_key"]: document["source_file"] for document in self.registry["documents"]}
        for number, record in enumerate(self.records, start=1):
            cell = self.cells_by_key[record["cell_key"]]
            row = self.rows_by_key[record["row_key"]]
            table = self.tables_by_key[record["table_key"]]
            page = self.pages_by_table[record["table_key"]]
            self.assertEqual(record["batch_record_number"], number)
            self.assertEqual(record["column_index"], cell["column_index"])
            self.assertEqual(record["cell_bbox"], cell["bbox"])
            self.assertEqual(record["raw_text"], cell["raw_text"])
            self.assertEqual(record["token_class"], cell["token_class"])
            self.assertEqual(record["parser_confidence"], cell["parser_confidence"])
            self.assertEqual(record["parent_raw_text"], row["raw_text"])
            self.assertEqual(record["parent_raw_values"], row["raw_values"])
            self.assertEqual(record["pdf_page_number"], table["page_number"])
            self.assertEqual(record["printed_page_label"], page["printed_page_label"])
            self.assertEqual(record["source_file"], source_files[record["document_key"]])
            self.assertTrue((ROOT / record["source_file"]).is_file())

    def test_every_cell_has_exact_approved_source_decision(self) -> None:
        allowed_resolutions = {
            "replace_with_source_verified_cell_transcription",
            "replace_with_source_verified_context_transcription",
            "classify_source_verified_dash_placeholder",
            "exclude_non_financial_layout_artifact",
        }
        for record in self.records:
            self.assertLess(float(record["parser_confidence"]), 80)
            self.assertTrue(record["exact_ambiguity"])
            self.assertIn(record["proposed_extraction_resolution"], allowed_resolutions)
            self.assertEqual(record["source_review_method"], "visual_review_of_exact_pdf_page_and_cell_bbox_at_180_dpi")
            self.assertEqual(record["decision"], "revised_and_approved")
            self.assertEqual(record["decision_date"], "2026-07-14")
            self.assertEqual(record["review_status"], "approved_for_controlled_extraction_application")

    def test_source_fidelity_corrections_and_value_states_are_locked(self) -> None:
        by_number = {record["batch_record_number"]: record for record in self.records}
        self.assertEqual(by_number[16]["proposed_cell_values"], ["(792,142)"])
        self.assertEqual(by_number[168]["proposed_cell_values"], ["(742,585)"])
        self.assertEqual(by_number[185]["proposed_cell_values"], ["35,377,973"])
        self.assertEqual(by_number[211]["proposed_cell_text"], "- %")
        self.assertEqual(by_number[211]["proposed_value_state"], "source_dash_placeholder")
        self.assertEqual(by_number[225]["proposed_cell_values"], ["73,115"])
        self.assertEqual(by_number[193]["proposed_extraction_resolution"], "exclude_non_financial_layout_artifact")
        self.assertEqual(by_number[161]["proposed_cell_text"], "Amort | Disposals")

    def test_human_review_artifact_has_77_page_groups_and_every_cell_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(record["cell_key"]), 1)
        for document_key, page_number in {
            (record["document_key"], record["pdf_page_number"])
            for record in self.records
        }:
            self.assertEqual(self.markdown.count(f"## {document_key} — PDF page {page_number} "), 1)


if __name__ == "__main__":
    unittest.main()

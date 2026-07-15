#!/usr/bin/env python3
"""Regression checks for Gate 5 low-confidence note/schedule Batch 02."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "low-confidence-note-schedules-batch-02.json"
BATCH_MD = DATA / "review-batches" / "low-confidence-note-schedules-batch-02.md"
INCLUDED_SECTIONS = {"Notes", "Schedules"}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatch02Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = read_json(DATA / "source-document-registry.json")
        cls.batch = read_json(BATCH_PATH)
        cls.records = cls.batch["records"]
        cls.rows_by_key: dict[str, dict[str, object]] = {}
        cls.tables_by_key: dict[str, dict[str, object]] = {}
        cls.pages_by_table: dict[str, dict[str, object]] = {}
        cls.expected_keys: set[str] = set()
        cls.all_low_confidence_keys: set[str] = set()
        for document in cls.registry["documents"]:
            document_root = DATA / document["document_key"]
            tables = read_json(document_root / "table_manifest.json")["records"]
            pages = read_json(document_root / "raw-tables" / "source_table_pages.json")["records"]
            rows = read_json(document_root / "raw-tables" / "source_table_rows.json")["records"]
            cls.tables_by_key.update({table["table_key"]: table for table in tables})
            cls.pages_by_table.update({page["table_key"]: page for page in pages})
            cls.rows_by_key.update({row["row_key"]: row for row in rows})
            for row in rows:
                table = cls.tables_by_key[row["table_key"]]
                if float(row["parser_confidence"]) < 80:
                    cls.all_low_confidence_keys.add(row["row_key"])
                    if table["section"] in INCLUDED_SECTIONS:
                        cls.expected_keys.add(row["row_key"])
        cls.batch01_keys = {
            record["row_key"]
            for record in read_json(DATA / "review-batches" / "low-confidence-primary-statements-batch-01.json")["records"]
        }
        cls.markdown = BATCH_MD.read_text(encoding="utf-8")

    def test_batch_is_complete_unsampled_and_disjoint_from_batch_01(self) -> None:
        actual_keys = {record["row_key"] for record in self.records}
        self.assertEqual(actual_keys, self.expected_keys)
        self.assertEqual(len(actual_keys), 111)
        self.assertEqual(actual_keys & self.batch01_keys, set())
        self.assertEqual(actual_keys | self.batch01_keys, self.all_low_confidence_keys)
        self.assertEqual(self.batch["selection_rule"]["sampling"], "none; every matching row is included")

    def test_counts_families_and_review_boundary_are_exact(self) -> None:
        self.assertEqual(
            self.batch["counts"],
            {
                "records": 111,
                "source_pages": 67,
                "documents": 8,
                "notes": 82,
                "schedules": 29,
                "value_bearing_rows": 26,
                "rows_without_parsed_values": 85,
                "financial_transcriptions": 57,
                "context_transcriptions": 7,
                "layout_artifact_exclusions": 47,
                "revised_and_approved": 111,
                "approved": 111,
            },
        )
        self.assertEqual(
            self.batch["table_family_counts"],
            {
                "budget_reconciliation_note": 5,
                "note_disclosure_table": 77,
                "segmented_disclosure_schedule": 4,
                "tangible_capital_assets_schedule": 25,
            },
        )
        self.assertEqual(set(self.batch["decision_boundary"].values()), {False})
        self.assertEqual(self.batch["status"], "review_complete")
        self.assertTrue(all(
            record["decision"] == "revised_and_approved"
            and record["review_status"] == "approved_for_controlled_extraction_application"
            for record in self.records
        ))

    def test_every_locator_and_raw_field_round_trips(self) -> None:
        source_files = {document["document_key"]: document["source_file"] for document in self.registry["documents"]}
        for number, record in enumerate(self.records, start=1):
            row = self.rows_by_key[record["row_key"]]
            table = self.tables_by_key[record["table_key"]]
            page = self.pages_by_table[record["table_key"]]
            self.assertEqual(record["batch_record_number"], number)
            self.assertEqual(record["document_key"], row["document_key"])
            self.assertEqual(record["page_key"], row["page_key"])
            self.assertEqual(record["row_index"], row["row_index"])
            self.assertEqual(record["bbox"], row["bbox"])
            self.assertEqual(record["parser_confidence"], row["parser_confidence"])
            self.assertEqual(record["raw_label"], row["raw_label_candidate"])
            self.assertEqual(record["raw_text"], row["raw_text"])
            self.assertEqual(record["raw_values"], row["raw_values"])
            self.assertEqual(record["pdf_page_number"], table["page_number"])
            self.assertEqual(record["manifest_section"], table["section"])
            self.assertEqual(record["table_family"], table["table_family"])
            self.assertEqual(record["printed_page_label"], page["printed_page_label"])
            self.assertEqual(record["source_file"], source_files[record["document_key"]])
            self.assertTrue((ROOT / record["source_file"]).is_file())

    def test_each_row_has_exact_approved_source_decision(self) -> None:
        allowed_resolutions = {
            "replace_with_source_verified_transcription",
            "replace_with_source_verified_context_transcription",
            "exclude_non_financial_layout_artifact",
        }
        for record in self.records:
            self.assertTrue(record["exact_ambiguity"])
            self.assertIn(record["proposed_extraction_resolution"], allowed_resolutions)
            self.assertEqual(record["source_review_method"], "visual_review_of_exact_pdf_page_and_row_bbox_at_180_dpi")
            self.assertEqual(record["decision_date"], "2026-07-14")

    def test_approved_transcriptions_lock_source_signs_and_values(self) -> None:
        by_number = {record["batch_record_number"]: record for record in self.records}
        self.assertEqual(by_number[28]["proposed_raw_values"][2], "(576,000)")
        self.assertEqual(by_number[51]["proposed_raw_values"], ["-", "28,526,953", "28,526,953"])
        self.assertEqual(by_number[58]["proposed_raw_values"][2:4], ["(23,329,353)", "366,026,514"])
        self.assertEqual(by_number[69]["proposed_raw_values"][6], "(499,620)")
        self.assertEqual(by_number[72]["proposed_raw_label"], "Property tax")
        self.assertEqual(len(by_number[72]["proposed_raw_values"]), 7)
        self.assertEqual(by_number[103]["proposed_context_text"].split()[-1], "2023.")
        self.assertEqual(by_number[108]["proposed_raw_values"], ["-", "-", "3,577,713", "3,577,713"])

    def test_human_review_artifact_contains_every_row_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(f"`{record['row_key']}`"), 1)
        for document_key, page_number in {
            (record["document_key"], record["pdf_page_number"])
            for record in self.records
        }:
            self.assertEqual(self.markdown.count(f"## {document_key} — PDF page {page_number} "), 1)


if __name__ == "__main__":
    unittest.main()

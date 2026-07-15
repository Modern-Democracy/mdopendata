#!/usr/bin/env python3
"""Regression checks for Gate 5 Batch 04 table-context review."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "table-context-batch-04.json"
MD_PATH = DATA / "review-batches" / "table-context-batch-04.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatch04Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = read_json(BATCH_PATH)
        cls.records = cls.batch["records"]
        cls.markdown = MD_PATH.read_text(encoding="utf-8")

    def test_batch_has_every_table_exactly_once_and_all_are_approved(self) -> None:
        self.assertEqual(self.batch["status"], "review_complete")
        self.assertEqual(len(self.records), 139)
        self.assertEqual(len({item["table_key"] for item in self.records}), 139)
        self.assertEqual(len({item["page_key"] for item in self.records}), 139)
        self.assertEqual(len({item["document_key"] for item in self.records}), 8)
        self.assertTrue(all(item["decision"] in {"approved_as_proposed", "revised_and_approved"} for item in self.records))
        self.assertTrue(all(item["review_status"] == "approved_for_controlled_table_context_application" for item in self.records))

    def test_source_register_hashes_and_keys_are_exact(self) -> None:
        expected_keys = None
        for filename in ("period-review.json", "statement-class-review.json", "entity-scope-review.json"):
            path = DATA / filename
            artifact_path = path.relative_to(ROOT).as_posix()
            self.assertEqual(self.batch["source_artifacts"][artifact_path], hashlib.sha256(path.read_bytes()).hexdigest())
            keys = {item["table_key"] for item in read_json(path)["records"]}
            expected_keys = keys if expected_keys is None else expected_keys
            self.assertEqual(keys, expected_keys)
        self.assertEqual({item["table_key"] for item in self.records}, expected_keys)

    def test_proposals_round_trip_to_source_registers(self) -> None:
        periods = {item["table_key"]: item for item in read_json(DATA / "period-review.json")["records"]}
        classes = {item["table_key"]: item for item in read_json(DATA / "statement-class-review.json")["records"]}
        scopes = {item["table_key"]: item for item in read_json(DATA / "entity-scope-review.json")["records"]}
        for item in self.records:
            key = item["table_key"]
            self.assertEqual(item["raw_detected_years"], periods[key]["raw_detected_periods"])
            self.assertEqual(item["proposed_reporting_date"], periods[key]["proposed_reporting_date"])
            self.assertEqual(item["proposed_statement_class"], classes[key]["proposed_statement_class"])
            self.assertEqual(item["proposed_reporting_entity_key"], scopes[key]["proposed_reporting_entity_key"])
            self.assertEqual(item["proposed_consolidation_scope"], scopes[key]["proposed_consolidation_scope"])
            self.assertFalse(item["cross_entity_addition_allowed"])

    def test_approved_fields_are_complete_and_column_roles_are_deferred(self) -> None:
        for item in self.records:
            self.assertEqual(item["approved_reporting_date"], item["proposed_reporting_date"])
            self.assertEqual(item["approved_statement_class"], item["proposed_statement_class"])
            self.assertEqual(item["approved_reporting_entity_key"], item["proposed_reporting_entity_key"])
            self.assertEqual(item["approved_consolidation_scope"], item["proposed_consolidation_scope"])
            self.assertFalse(item["approved_cross_entity_addition_allowed"])
            self.assertFalse(item["source_column_roles_proposed"])
            self.assertEqual(item["decision_date"], "2026-07-15")

    def test_five_exact_period_revisions_are_preserved(self) -> None:
        revised = {item["batch_record_number"]: item for item in self.records if item["decision"] == "revised_and_approved"}
        self.assertEqual(set(revised), {11, 18, 46, 94, 109})
        self.assertEqual(revised[11]["approved_financial_years"], ["2024", "2023"])
        self.assertEqual(revised[18]["approved_financial_years"], ["2024", "2023", "2025", "2026", "2027", "2028", "2029"])
        self.assertEqual(revised[46]["approved_financial_years"], ["2025", "2024", "2026", "2027", "2028", "2029", "2030"])
        self.assertEqual(revised[94]["approved_contextual_years"], ["2016", "2054"])
        self.assertEqual(revised[109]["approved_contextual_years"], ["2016"])

    def test_neighboring_debt_maturity_dates_remain_contextual(self) -> None:
        by_number = {item["batch_record_number"]: item for item in self.records}
        for number in (17, 45, 93, 108):
            item = by_number[number]
            self.assertEqual(item["decision"], "approved_as_proposed")
            current = item["approved_reporting_date"][:4]
            prior = str(int(current) - 1)
            self.assertEqual(item["approved_financial_years"], [current, prior])
            self.assertTrue(item["approved_contextual_years"])

    def test_approved_years_preserve_raw_evidence_with_one_visual_ocr_exception(self) -> None:
        for item in self.records:
            approved = set(item["approved_financial_years"]) | set(item["approved_contextual_years"])
            raw = set(item["raw_detected_years"])
            if item["batch_record_number"] == 11:
                self.assertEqual(approved - raw, {"2023"})
            else:
                self.assertEqual(approved - raw, set())

    def test_decision_counts_and_boundary_are_exact(self) -> None:
        self.assertTrue(self.batch["decision_boundary"]["approves_table_period_evidence"])
        self.assertTrue(self.batch["decision_boundary"]["approves_statement_classes"])
        self.assertTrue(self.batch["decision_boundary"]["approves_entity_scope"])
        self.assertFalse(self.batch["decision_boundary"]["assigns_source_column_roles"])
        self.assertFalse(self.batch["decision_boundary"]["approves_normalization"])
        self.assertEqual(self.batch["counts"]["approved_as_proposed"], 134)
        self.assertEqual(self.batch["counts"]["revised_and_approved"], 5)
        self.assertEqual(self.batch["counts"]["approved"], 139)
        self.assertEqual(self.batch["counts"]["needs_review"], 0)
        self.assertEqual(sum(self.batch["records_by_table_family"].values()), 139)

    def test_human_artifact_has_each_exact_page_and_table_once(self) -> None:
        for item in self.records:
            heading = f"## {item['document_key']} — PDF page {item['pdf_page_number']} "
            self.assertEqual(self.markdown.count(heading), 1)
            self.assertEqual(self.markdown.count(f"`{item['table_key']}`"), 1)


if __name__ == "__main__":
    unittest.main()

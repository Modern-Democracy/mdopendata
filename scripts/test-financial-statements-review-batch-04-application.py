#!/usr/bin/env python3
"""Regression checks for controlled application of Gate 5 Batch 04."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_PATH = DATA / "review-batches" / "table-context-batch-04.json"
APPLIED_PATH = DATA / "controlled-derived" / "table-context-batch-04-applied.json"
APPLIED_MD = DATA / "controlled-derived" / "table-context-batch-04-applied.md"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatch04ApplicationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = read_json(BATCH_PATH)
        cls.applied = read_json(APPLIED_PATH)
        cls.records = cls.applied["records"]
        cls.batch_by_key = {record["table_key"]: record for record in cls.batch["records"]}
        cls.manifests: dict[str, dict[str, object]] = {}
        cls.raw_pages: dict[str, dict[str, object]] = {}
        registry = read_json(DATA / "source-document-registry.json")
        for document in registry["documents"]:
            document_key = document["document_key"]
            cls.manifests.update({
                table["table_key"]: table
                for table in read_json(DATA / document_key / "table_manifest.json")["records"]
            })
            cls.raw_pages.update({
                page["table_key"]: page
                for page in read_json(DATA / document_key / "raw-tables" / "source_table_pages.json")["records"]
            })
        cls.markdown = APPLIED_MD.read_text(encoding="utf-8")

    def test_source_decision_artifact_is_exact_and_fully_approved(self) -> None:
        source = self.applied["source_decision_artifact"]
        self.assertEqual(source["batch_key"], "table_context_batch_04")
        self.assertEqual(source["sha256"], hashlib.sha256(BATCH_PATH.read_bytes()).hexdigest())
        self.assertEqual(self.batch["counts"]["approved"], 139)

    def test_application_counts_and_boundary_are_exact(self) -> None:
        self.assertEqual(
            self.applied["counts"],
            {
                "approved_decisions": 139,
                "materialized_table_contexts": 139,
                "approved_as_proposed": 134,
                "revised_and_approved": 5,
                "table_period_evidence_applied": 139,
                "statement_classes_applied": 139,
                "entity_scopes_applied": 139,
                "source_column_roles_assigned": 0,
                "raw_tables_mutated": 0,
                "normalization_approved": 0,
                "database_writes": 0,
            },
        )
        self.assertEqual(set(self.applied["decision_boundary"].values()), {False})
        self.assertEqual(len(self.records), 139)
        self.assertEqual(len({record["table_key"] for record in self.records}), 139)

    def test_every_application_round_trips_to_decision_and_immutable_sources(self) -> None:
        for record in self.records:
            decision = self.batch_by_key[record["table_key"]]
            table = self.manifests[record["table_key"]]
            raw_page = self.raw_pages[record["table_key"]]
            self.assertEqual(record["source_batch_record_number"], decision["batch_record_number"])
            self.assertEqual(record["approved_decision"], decision["decision"])
            self.assertEqual(record["immutable_profile_confidence"], table["confidence"])
            self.assertEqual(record["immutable_profile_rotation_degrees"], raw_page["profile_rotation_degrees"])
            self.assertEqual(record["source_sha256"], raw_page["source_sha256"])
            self.assertFalse(record["raw_source_mutated"])

    def test_approved_context_is_materialized_without_column_roles(self) -> None:
        for record in self.records:
            decision = self.batch_by_key[record["table_key"]]
            self.assertEqual(record["application_status"], "materialized_approved_table_context")
            self.assertEqual(record["derived_reporting_date"], decision["approved_reporting_date"])
            self.assertEqual(record["derived_financial_years"], decision["approved_financial_years"])
            self.assertEqual(record["derived_contextual_years"], decision["approved_contextual_years"])
            self.assertEqual(record["derived_statement_class"], decision["approved_statement_class"])
            self.assertEqual(record["derived_reporting_entity_key"], decision["approved_reporting_entity_key"])
            self.assertEqual(record["derived_consolidation_scope"], decision["approved_consolidation_scope"])
            self.assertFalse(record["derived_cross_entity_addition_allowed"])
            self.assertEqual(record["derived_source_column_roles"], [])
            self.assertEqual(record["source_column_role_review_status"], "needs_review")
            self.assertEqual(record["normalization_review_status"], "needs_review")

    def test_five_revised_period_controls_survive_application(self) -> None:
        by_number = {record["application_record_number"]: record for record in self.records}
        revised = {number for number, record in by_number.items() if record["approved_decision"] == "revised_and_approved"}
        self.assertEqual(revised, {11, 18, 46, 94, 109})
        self.assertEqual(by_number[11]["derived_financial_years"], ["2024", "2023"])
        self.assertEqual(by_number[18]["derived_financial_years"][-5:], ["2025", "2026", "2027", "2028", "2029"])
        self.assertEqual(by_number[46]["derived_financial_years"][-5:], ["2026", "2027", "2028", "2029", "2030"])
        self.assertEqual(by_number[94]["derived_contextual_years"], ["2016", "2054"])
        self.assertEqual(by_number[109]["derived_contextual_years"], ["2016"])

    def test_human_artifact_has_139_page_groups_and_every_table_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(f"`{record['table_key']}`"), 1)
            heading = f"## {record['document_key']} — PDF page {record['pdf_page_number']} "
            self.assertEqual(self.markdown.count(heading), 1)


if __name__ == "__main__":
    unittest.main()

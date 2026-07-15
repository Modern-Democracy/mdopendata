#!/usr/bin/env python3
"""Regression checks for Charlottetown financial-statement Gate 2 artifacts."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
REGISTRY = DATA / "source-document-registry.json"
SUMMARY = DATA / "gate-2-profile-summary.json"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class FinancialStatementProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = read_json(REGISTRY)
        cls.summary = read_json(SUMMARY)

    def test_summary_satisfies_gate_2_counts(self) -> None:
        self.assertEqual(self.summary["status"], "complete")
        self.assertEqual(self.summary["counts"]["documents"], 8)
        self.assertEqual(self.summary["counts"]["pages"], 188)
        self.assertEqual(self.summary["counts"]["pages_with_disposition"], 188)
        self.assertEqual(self.summary["counts"]["unclassified_financial_tables"], 0)
        checks = self.summary["gate_checks"]
        self.assertTrue(checks["all_registry_documents_profiled"])
        self.assertTrue(checks["all_registry_pages_profiled"])
        self.assertTrue(checks["every_page_has_disposition"])
        self.assertEqual(checks["unclassified_financial_table_count"], 0)
        self.assertEqual(checks["database_writes"], 0)

    def test_registry_sources_remain_immutable(self) -> None:
        for document in self.registry["documents"]:
            source = ROOT / document["source_file"]
            self.assertEqual(sha256(source), document["sha256"], document["document_key"])
            self.assertEqual(source.stat().st_size, document["file_size_bytes"])

    def test_each_document_has_complete_page_and_table_artifacts(self) -> None:
        allowed_dispositions = {
            "administrative_front_matter",
            "financial_table_candidate",
            "financial_note_narrative",
            "context_or_narrative",
            "blank_or_scan_artifact",
        }
        for document in self.registry["documents"]:
            key = document["document_key"]
            directory = DATA / key
            profile = read_json(directory / "source_profile.json")
            inventory = read_json(directory / "page_inventory.json")["records"]
            manifest = read_json(directory / "table_manifest.json")["records"]
            self.assertEqual(profile["sha256"], document["sha256"])
            self.assertEqual(len(inventory), document["page_count"])
            self.assertEqual([page["page_number"] for page in inventory], list(range(1, document["page_count"] + 1)))
            self.assertEqual(len({page["page_key"] for page in inventory}), len(inventory))
            self.assertTrue(all(page["disposition"] in allowed_dispositions for page in inventory))
            self.assertTrue(all((not page["table_candidate"]) or page["table_family"] for page in inventory))
            candidate_keys = {f'{page["page_key"]}_t01' for page in inventory if page["table_candidate"]}
            self.assertEqual(candidate_keys, {table["table_key"] for table in manifest})
            self.assertEqual(len(list((directory / "profile-raw-pages").glob("page-*.txt"))), document["page_count"])
            self.assertEqual(len(list((directory / "profile-ocr-pages").glob("page-*.txt"))), document["page_count"])
            self.assertFalse((directory / "rendered-pages").exists())

    def test_expected_primary_statement_classes_are_present_once(self) -> None:
        public_sector = {"financial_position", "operations", "changes_in_net_debt", "cash_flow"}
        pension = {
            "financial_position",
            "changes_in_net_assets_available_for_benefits",
            "changes_in_pension_obligations",
        }
        for document in self.registry["documents"]:
            key = document["document_key"]
            inventory = read_json(DATA / key / "page_inventory.json")["records"]
            observed = [page["statement_class"] for page in inventory if page["content_type"] == "financial_statement"]
            expected = pension if document["entity_type"] == "pension_plan" else public_sector
            self.assertEqual(set(observed), expected, key)
            self.assertEqual(len(observed), len(expected), key)

    def test_city_budget_figure_notes_are_specific_reconciliation_candidates(self) -> None:
        for key in (
            "ctown_fs_city_2024_03_31_audited",
            "ctown_fs_city_2025_03_31_audited",
        ):
            inventory = read_json(DATA / key / "page_inventory.json")["records"]
            page = next(record for record in inventory if record["page_number"] == 28)
            self.assertEqual(page["content_type"], "notes")
            self.assertEqual(page["disposition"], "financial_table_candidate")
            self.assertEqual(page["table_family"], "budget_reconciliation_note")

    def test_registered_front_matter_and_first_statement_pages(self) -> None:
        for document in self.registry["documents"]:
            key = document["document_key"]
            by_page = {
                page["page_number"]: page
                for page in read_json(DATA / key / "page_inventory.json")["records"]
            }
            evidence = document["source_evidence"]
            self.assertEqual(by_page[evidence["cover_pdf_page"]]["content_type"], "cover")
            self.assertEqual(by_page[evidence["index_pdf_page"]]["content_type"], "index")
            for page in evidence["auditor_report_pdf_pages"]:
                self.assertEqual(by_page[page]["content_type"], "auditor_report", f"{key} page {page}")
            self.assertEqual(by_page[evidence["first_statement_pdf_page"]]["statement_class"], "financial_position")


if __name__ == "__main__":
    unittest.main()

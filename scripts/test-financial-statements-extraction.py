#!/usr/bin/env python3
"""Regression checks for Gate 5 financial-statement raw and review artifacts."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
VALUE_CLASSES = {"amount_candidate", "signed_amount_candidate", "dash_candidate"}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementExtractionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = read_json(DATA / "source-document-registry.json")
        cls.raw_summary = read_json(DATA / "gate-5-raw-extraction-summary.json")
        cls.review_summary = read_json(DATA / "gate-5-review-summary.json")
        cls.pages: list[dict[str, object]] = []
        cls.columns: list[dict[str, object]] = []
        cls.rows: list[dict[str, object]] = []
        cls.cells: list[dict[str, object]] = []
        cls.manifest_tables: list[dict[str, object]] = []
        for document in cls.registry["documents"]:
            document_root = DATA / document["document_key"]
            cls.pages.extend(read_json(document_root / "raw-tables" / "source_table_pages.json")["records"])
            cls.columns.extend(read_json(document_root / "raw-tables" / "source_table_columns.json")["records"])
            cls.rows.extend(read_json(document_root / "raw-tables" / "source_table_rows.json")["records"])
            cls.cells.extend(read_json(document_root / "raw-tables" / "source_table_cells.json")["records"])
            cls.manifest_tables.extend(read_json(document_root / "table_manifest.json")["records"])

    def test_all_registered_documents_and_profiled_tables_are_extracted(self) -> None:
        self.assertEqual(self.raw_summary["status"], "complete")
        self.assertEqual(self.raw_summary["counts"]["documents"], 8)
        self.assertEqual(self.raw_summary["counts"]["registered_pdf_pages"], 188)
        self.assertEqual(len(self.pages), 139)
        self.assertEqual({page["table_key"] for page in self.pages}, {table["table_key"] for table in self.manifest_tables})
        self.assertEqual(self.raw_summary["counts"]["database_writes"], 0)

    def test_raw_keys_coordinates_and_references_are_complete(self) -> None:
        self.assertEqual(len({row["row_key"] for row in self.rows}), len(self.rows))
        self.assertEqual(len({cell["cell_key"] for cell in self.cells}), len(self.cells))
        row_keys = {row["row_key"] for row in self.rows}
        table_keys = {page["table_key"] for page in self.pages}
        for record in self.rows + self.cells:
            bbox = record["bbox"]
            self.assertEqual(len(bbox), 4)
            self.assertTrue(all(0 <= value <= 1 for value in bbox))
            self.assertLessEqual(bbox[0], bbox[2])
            self.assertLessEqual(bbox[1], bbox[3])
        self.assertTrue(all(cell["row_key"] in row_keys for cell in self.cells))
        self.assertTrue(all(row["table_key"] in table_keys for row in self.rows))
        self.assertTrue(all(column["table_key"] in table_keys for column in self.columns))

    def test_raw_counts_match_artifacts(self) -> None:
        counts = self.raw_summary["counts"]
        self.assertEqual(counts["source_columns"], len(self.columns))
        self.assertEqual(counts["source_rows"], len(self.rows))
        self.assertEqual(counts["source_cells"], len(self.cells))
        self.assertEqual(counts["value_candidate_cells"], sum(cell["token_class"] in VALUE_CLASSES for cell in self.cells))
        self.assertEqual(counts["rotated_table_pages"], 8)

    def test_narrative_years_are_not_value_candidates(self) -> None:
        year_cells = [cell for cell in self.cells if cell["token_class"] == "year_or_reference"]
        self.assertGreater(len(year_cells), 0)
        self.assertTrue(all(cell["cell_key"] not in {
            key for row in self.rows for key in row["raw_value_cell_keys"]
        } for cell in year_cells))

    def test_representative_values_and_document_owned_comparatives_survive(self) -> None:
        by_page: dict[str, str] = {}
        for row in self.rows:
            by_page.setdefault(str(row["page_key"]), "")
            by_page[str(row["page_key"])] += " " + str(row["raw_text"])
        controls = {
            "ctown_fs_city_2024_03_31_audited_p006": "15,694,379",
            "ctown_fs_city_2025_03_31_audited_p006": "15,694,380",
            "ctown_fs_ws_2025_03_31_audited_p007": "12,430,885",
            "ctown_fs_city_sa_2024_12_31_audited_p006": "131,900,688",
            "ctown_fs_ws_sa_2024_12_31_audited_p006": "10,663,117",
        }
        for page_key, expected in controls.items():
            self.assertIn(expected, by_page[page_key])

    def test_sign_and_dash_evidence_is_preserved_for_review(self) -> None:
        sign_review = read_json(DATA / "dash-sign-review.json")
        self.assertGreater(sign_review["counts"]["records"], 0)
        self.assertEqual(sign_review["counts"]["approved"], 0)
        for record in sign_review["records"]:
            self.assertIn(record["token_class"], {"signed_amount_candidate", "dash_candidate"})
            self.assertTrue(record["raw_cell_text"])
            self.assertIsNone(record["proposed_sign"])
            self.assertEqual(record["review_status"], "needs_review")

    def test_every_controlled_row_has_an_exact_source_locator(self) -> None:
        for filename in (
            "hierarchy-review.json",
            "budget-equivalence-review.json",
            "taxonomy-review.json",
        ):
            payload = read_json(DATA / filename)
            for record in payload["records"]:
                for key in ("document_key", "pdf_page_number", "page_key", "table_key", "row_key", "raw_label", "raw_values"):
                    self.assertIn(key, record, f"{filename}: {key}")
                self.assertEqual(record["review_status"], "needs_review")
                self.assertIsNone(record["decision"])

    def test_review_queue_is_non_approving_and_scope_safe(self) -> None:
        self.assertEqual(self.review_summary["status"], "complete_with_review_queue")
        self.assertEqual(self.review_summary["counts"]["approved_records"], 0)
        self.assertEqual(self.review_summary["counts"]["database_writes"], 0)
        self.assertEqual(self.review_summary["counts"]["reporting_entity_relationship_candidates"], 3)
        scopes = read_json(DATA / "entity-scope-review.json")["records"]
        self.assertTrue(all(record["cross_entity_addition_allowed"] is False for record in scopes))
        comparisons = read_json(DATA / "comparative-relationship-review.json")["records"]
        self.assertTrue(all(record["match_basis"] == "exact_compacted_raw_label_within_table_family" for record in comparisons))
        self.assertTrue(all(record["review_status"] == "needs_review" and record["decision"] is None for record in comparisons))

    def test_review_locators_round_trip_to_exact_raw_rows(self) -> None:
        rows_by_key = {row["row_key"]: row for row in self.rows}

        def assert_locator(record: dict[str, object]) -> None:
            row = rows_by_key[record["row_key"]]
            self.assertEqual(record["document_key"], row["document_key"])
            self.assertEqual(record["page_key"], row["page_key"])
            self.assertEqual(record["table_key"], row["table_key"])
            self.assertEqual(record["raw_label"], row["raw_label_candidate"] or row["raw_text"])
            self.assertEqual(record["raw_values"], row["raw_values"])

        for filename in (
            "hierarchy-review.json",
            "dash-sign-review.json",
            "budget-equivalence-review.json",
            "taxonomy-review.json",
        ):
            for record in read_json(DATA / filename)["records"]:
                assert_locator(record)
        for record in read_json(DATA / "comparative-relationship-review.json")["records"]:
            assert_locator(record["source"])
            assert_locator(record["target"])


if __name__ == "__main__":
    unittest.main()

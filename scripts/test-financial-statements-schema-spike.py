#!/usr/bin/env python3
"""Regression checks for the Charlottetown financial-statement Gate 3 spike."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
SPIKE = DATA / "schema-spike"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementSchemaSpikeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = read_json(DATA / "source-document-registry.json")
        cls.summary = read_json(SPIKE / "spike-summary.json")
        cls.pages = read_json(SPIKE / "representative-source-pages.json")["records"]
        cls.rows = read_json(SPIKE / "representative-source-rows.json")["records"]
        cls.cells = read_json(SPIKE / "representative-source-cells.json")["records"]
        cls.projections = read_json(SPIKE / "representative-schema-projections.json")["records"]
        cls.fit = read_json(SPIKE / "schema-fit-report.json")

    def test_all_seven_controls_pass_without_database_writes(self) -> None:
        self.assertEqual(self.summary["status"], "complete")
        self.assertEqual(self.summary["counts"]["controls"], 7)
        self.assertEqual(self.summary["counts"]["unique_source_pages"], 7)
        self.assertEqual(self.summary["counts"]["control_failures"], 0)
        self.assertEqual(self.summary["counts"]["database_writes"], 0)
        self.assertTrue(all(result["status"] == "pass" for result in self.summary["control_results"]))

    def test_source_pages_match_registry_and_retain_printed_labels(self) -> None:
        registry = {document["document_key"]: document for document in self.registry["documents"]}
        self.assertEqual(len({page["page_key"] for page in self.pages}), 7)
        for page in self.pages:
            document = registry[page["document_key"]]
            self.assertEqual(page["source_sha256"], document["sha256"])
            self.assertLessEqual(page["pdf_page_number"], document["page_count"])
            self.assertIsNotNone(page["printed_page_label"], page["page_key"])
            self.assertEqual(page["extraction_method"], "ocr_tesseract_word_tsv")
            self.assertEqual(page["extractor_psm"], 4)

    def test_raw_rows_and_cells_have_stable_unique_coordinate_evidence(self) -> None:
        self.assertEqual(len({row["row_key"] for row in self.rows}), len(self.rows))
        self.assertEqual(len({cell["cell_key"] for cell in self.cells}), len(self.cells))
        row_keys = {row["row_key"] for row in self.rows}
        for record in self.rows + self.cells:
            bbox = record["bbox"]
            self.assertEqual(len(bbox), 4)
            self.assertTrue(all(0 <= value <= 1 for value in bbox))
            self.assertLessEqual(bbox[0], bbox[2])
            self.assertLessEqual(bbox[1], bbox[3])
            self.assertGreaterEqual(record["parser_confidence"], 0)
            self.assertLessEqual(record["parser_confidence"], 100)
        self.assertTrue(all(cell["row_key"] in row_keys for cell in self.cells))
        self.assertEqual(self.summary["counts"]["null_row_bboxes"], 0)
        self.assertEqual(self.summary["counts"]["null_cell_bboxes"], 0)

    def test_comparative_difference_is_document_owned(self) -> None:
        by_page: dict[str, str] = {}
        for row in self.rows:
            by_page.setdefault(row["page_key"], "")
            by_page[row["page_key"]] += " " + row["raw_text"]
        self.assertIn("15,694,379", by_page["ctown_fs_city_2024_03_31_audited_p006"])
        self.assertIn("15,694,380", by_page["ctown_fs_city_2025_03_31_audited_p006"])
        projection = next(item for item in self.projections if item["control_key"] == "city_2024_comparative_difference")
        self.assertIn("financial_observation_relationship", projection["planned_migration_objects"])
        self.assertNotIn("value_numeric", projection)

    def test_budget_actual_columns_and_entity_scopes_remain_separate(self) -> None:
        by_key = {projection["control_key"]: projection for projection in self.projections}
        for key in ("city_2025_budget_actual_operations", "water_sewer_2025_operations"):
            columns = by_key[key]["source_columns"]
            roles = [(column.get("period_role"), column.get("amount_type")) for column in columns]
            self.assertEqual(
                roles[1:],
                [("current", "budget"), ("current", "actual"), ("comparative", "actual")],
            )
        self.assertNotEqual(
            by_key["city_2025_budget_actual_operations"]["statement"]["reporting_entity_key"],
            by_key["water_sewer_2025_operations"]["statement"]["reporting_entity_key"],
        )
        self.assertNotEqual(
            by_key["city_2025_financial_position"]["statement"]["reporting_entity_key"],
            by_key["city_superannuation_2024_position"]["statement"]["reporting_entity_key"],
        )

    def test_filename_conflict_does_not_create_december_21_period(self) -> None:
        page_key = "ctown_fs_ws_sa_2024_12_31_audited_p006"
        text = " ".join(row["raw_text"] for row in self.rows if row["page_key"] == page_key)
        self.assertIn("DECEMBER 31, 2024", text.upper())
        self.assertNotIn("DECEMBER 21, 2024", text.upper())
        projection = next(item for item in self.projections if item["control_key"] == "water_sewer_superannuation_2024_date")
        self.assertEqual(
            projection["statement"]["reporting_entity_key"],
            "charlottetown_water_and_sewer_corporation_superannuation_plan",
        )

    def test_architecture_decision_has_no_unplanned_gap(self) -> None:
        self.assertEqual(self.fit["status"], "ready_for_migration_029")
        self.assertEqual(self.fit["counts"]["unsupported_patterns"], 0)
        self.assertEqual(self.fit["counts"]["unplanned_schema_gaps"], 0)
        required = {
            "budget.document_accounting_context",
            "budget.statement_class",
            "budget.reporting_entity_relationship",
            "budget.financial_observation_relationship",
        }
        observed = {
            finding["required_object"]
            for finding in self.fit["findings"]
            if finding["status"] == "resolved_by_planned_migration_029"
        }
        self.assertEqual(observed, required)


if __name__ == "__main__":
    unittest.main()

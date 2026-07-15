#!/usr/bin/env python3
"""Regression checks for Gate 5 low-confidence primary-statement batch 01."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
BATCH_JSON = DATA / "review-batches" / "low-confidence-primary-statements-batch-01.json"
BATCH_MD = DATA / "review-batches" / "low-confidence-primary-statements-batch-01.md"
PRIMARY_FAMILIES = {
    "financial_position",
    "operations",
    "changes_in_net_debt",
    "cash_flow",
    "changes_in_net_assets_available_for_benefits",
    "changes_in_pension_obligations",
}
APPROVED_TREATMENTS = {
    "ctown_fs_city_2024_03_31_audited_p006_t01_r_50f877f69d3ef078d7c9": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_city_2024_03_31_audited_p007_t01_r_04f19fbdb3f379f8f97e": ("retain_source_verified_raw_row", ["87,308,345", "101,452,952", "96,522,091"]),
    "ctown_fs_city_2024_03_31_audited_p008_t01_r_ce56a422957d8b0c179f": ("replace_with_source_verified_transcription", ["(44,607,189)", "(30,743,223)", "(16,738,407)"]),
    "ctown_fs_city_2024_03_31_audited_p009_t01_r_00282759f01210338e36": ("replace_with_source_verified_transcription", ["(46,218,150)", "(51,113,531)"]),
    "ctown_fs_city_2024_03_31_audited_p009_t01_r_fe6115b0c7bd385e475a": ("replace_with_source_verified_transcription", ["(46,007,169)", "(51,308,731)"]),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_10d312b87c3e3d357cfd": ("retain_source_verified_raw_row", ["180,532,201", "177,288,439"]),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_fd5b56ce2c1bc2f2825a": ("replace_with_source_verified_transcription", ["414,337,528", "377,238,034"]),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_b08155395fba282e253b": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_city_2025_03_31_audited_p006_t01_r_4d5720d0bad8e0e3735a": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_city_2025_03_31_audited_p007_t01_r_9951291bf61f85bd8d2d": ("replace_with_source_verified_transcription", ["97,421,447", "100,740,160", "101,452,953"]),
    "ctown_fs_city_2025_03_31_audited_p007_t01_r_820ee32a2b3258f89158": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_city_2025_03_31_audited_p008_t01_r_d150cdd6665d44115b1b": ("replace_with_source_verified_transcription", ["113,038,565", "23,031,279", "4,331,705"]),
    "ctown_fs_city_2025_03_31_audited_p009_t01_r_fa67412adcaf8bfb00d3": ("replace_with_source_verified_transcription", ["(2,903,257)", "(14,858,093)"]),
    "ctown_fs_city_2025_03_31_audited_p009_t01_r_466742e44924ade45ca1": ("replace_with_source_verified_transcription", ["(50,843,942)", "(46,007,169)"]),
    "ctown_fs_city_2025_03_31_audited_p009_t01_r_679a54e0b071cddb77bd": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_ws_2024_03_31_audited_p009_t01_r_e974356e488dbaf8be81": ("replace_with_source_verified_transcription", ["(11,585,061)", "5,876,307"]),
    "ctown_fs_ws_2025_03_31_audited_p006_t01_r_0f2c64199f94cc5463de": ("retain_source_verified_raw_row", ["143,328,680", "140,766,544"]),
    "ctown_fs_ws_2025_03_31_audited_p006_t01_r_1208f1676d3438c92c6c": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_ws_2025_03_31_audited_p006_t01_r_710d075b2ab2173171ec": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_ws_2025_03_31_audited_p007_t01_r_d62b3e8e0c4a3c1e4bd7": ("replace_with_source_verified_transcription", ["-", "-", "48,951"]),
    "ctown_fs_ws_2025_03_31_audited_p007_t01_r_5bd04215eae520ade6d9": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_ws_2025_03_31_audited_p009_t01_r_4830bd5931671b7039fe": ("retain_source_verified_raw_row", ["1,480,843", "(11,585,059)"]),
    "ctown_fs_city_sa_2023_12_31_audited_p007_t01_r_4e03d2cc64e17f6bbbc5": ("retain_source_verified_raw_row", ["8,679,874", "17,653,043"]),
    "ctown_fs_city_sa_2024_12_31_audited_p006_t01_r_92b8368803e8eb949577": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_city_sa_2024_12_31_audited_p006_t01_r_337764843388b086ea56": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_city_sa_2024_12_31_audited_p007_t01_r_99935eb3bdba9c933148": ("retain_source_verified_raw_row", ["20,333,443", "23,153,663"]),
    "ctown_fs_ws_sa_2023_12_31_audited_p006_t01_r_d8c3a60875d2f69464f4": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_ws_sa_2024_12_31_audited_p006_t01_r_ab1c2cb538ebfca3bdee": ("exclude_non_financial_layout_artifact", []),
    "ctown_fs_ws_sa_2024_12_31_audited_p006_t01_r_ba8315d9fed10fb7aa1e": ("exclude_non_financial_layout_artifact", []),
}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class FinancialStatementReviewBatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = read_json(DATA / "source-document-registry.json")
        cls.batch = read_json(BATCH_JSON)
        cls.records = cls.batch["records"]
        cls.markdown = BATCH_MD.read_text(encoding="utf-8")
        cls.rows_by_key: dict[str, dict[str, object]] = {}
        cls.tables_by_key: dict[str, dict[str, object]] = {}
        cls.expected_keys: set[str] = set()
        for document in cls.registry["documents"]:
            document_root = DATA / document["document_key"]
            tables = read_json(document_root / "table_manifest.json")["records"]
            rows = read_json(document_root / "raw-tables" / "source_table_rows.json")["records"]
            cls.tables_by_key.update({table["table_key"]: table for table in tables})
            cls.rows_by_key.update({row["row_key"]: row for row in rows})
            for row in rows:
                table = cls.tables_by_key[row["table_key"]]
                if table["table_family"] in PRIMARY_FAMILIES and float(row["parser_confidence"]) < 80:
                    cls.expected_keys.add(row["row_key"])

    def test_batch_is_the_complete_unsampled_allowlist(self) -> None:
        actual_keys = {record["row_key"] for record in self.records}
        self.assertEqual(actual_keys, self.expected_keys)
        self.assertEqual(len(self.records), 29)
        self.assertEqual(len(actual_keys), len(self.records))
        self.assertEqual(self.batch["selection_rule"]["sampling"], "none; every matching row is included")
        self.assertTrue(all(float(record["parser_confidence"]) < 80 for record in self.records))
        self.assertTrue(all(record["table_family"] in PRIMARY_FAMILIES for record in self.records))

    def test_counts_and_review_boundary_are_exact(self) -> None:
        self.assertEqual(self.batch["status"], "review_complete")
        self.assertEqual(
            self.batch["counts"],
            {
                "records": 29,
                "source_pages": 17,
                "documents": 8,
                "financial_rows": 16,
                "layout_artifacts": 13,
                "retain_source_verified_raw_row": 6,
                "replace_with_source_verified_transcription": 10,
                "approved_as_proposed": 28,
                "revised_and_approved": 1,
                "approved": 29,
            },
        )
        self.assertEqual(set(self.batch["decision_boundary"].values()), {False})
        self.assertEqual(Counter(record["decision"] for record in self.records), {"approved_as_proposed": 28, "revised_and_approved": 1})
        self.assertTrue(all(record["review_status"] == "approved_for_controlled_extraction_application" for record in self.records))
        self.assertTrue(all(record["decision_basis"] == "visual_comparison_with_exact_pdf_page_at_180_dpi" for record in self.records))
        self.assertTrue(all(record["decision_date"] == "2026-07-14" for record in self.records))

    def test_every_locator_and_raw_field_round_trips(self) -> None:
        source_files = {document["document_key"]: document["source_file"] for document in self.registry["documents"]}
        for number, record in enumerate(self.records, start=1):
            row = self.rows_by_key[record["row_key"]]
            table = self.tables_by_key[record["table_key"]]
            self.assertEqual(record["batch_record_number"], number)
            self.assertEqual(record["document_key"], row["document_key"])
            self.assertEqual(record["page_key"], row["page_key"])
            self.assertEqual(record["table_key"], row["table_key"])
            self.assertEqual(record["row_index"], row["row_index"])
            self.assertEqual(record["bbox"], row["bbox"])
            self.assertEqual(record["parser_confidence"], row["parser_confidence"])
            self.assertEqual(record["raw_label"], row["raw_label_candidate"])
            self.assertEqual(record["raw_text"], row["raw_text"])
            self.assertEqual(record["raw_values"], row["raw_values"])
            self.assertEqual(record["pdf_page_number"], table["page_number"])
            self.assertEqual(record["table_family"], table["table_family"])
            self.assertEqual(record["source_file"], source_files[record["document_key"]])
            self.assertTrue((ROOT / record["source_file"]).is_file())
            self.assertTrue(record["printed_page_label"])
            self.assertTrue(record["exact_ambiguity"])

    def test_proposals_are_internally_consistent(self) -> None:
        disposition_counts = Counter(record["proposed_extraction_resolution"] for record in self.records)
        self.assertEqual(
            disposition_counts,
            {
                "exclude_non_financial_layout_artifact": 13,
                "retain_source_verified_raw_row": 6,
                "replace_with_source_verified_transcription": 10,
            },
        )
        for record in self.records:
            disposition = record["proposed_extraction_resolution"]
            if disposition == "exclude_non_financial_layout_artifact":
                self.assertEqual(record["proposed_raw_values"], [])
                self.assertEqual(record["normalization_effect"], "exclude_from_financial_mapping")
            elif disposition == "retain_source_verified_raw_row":
                if record["raw_values"]:
                    self.assertEqual(record["proposed_raw_values"], record["raw_values"])
                else:
                    self.assertEqual(" ".join(record["proposed_raw_values"]), record["raw_text"])
            else:
                self.assertTrue(record["proposed_raw_values"])
                self.assertNotEqual(record["proposed_raw_values"], record["raw_values"])

    def test_all_approved_treatments_match_visual_source_controls(self) -> None:
        actual = {
            record["row_key"]: (
                record["proposed_extraction_resolution"],
                record["proposed_raw_values"],
            )
            for record in self.records
        }
        self.assertEqual(actual, APPROVED_TREATMENTS)

    def test_source_verified_transcription_controls(self) -> None:
        by_key = {record["row_key"]: record for record in self.records}
        controls = {
            "ctown_fs_city_2024_03_31_audited_p008_t01_r_ce56a422957d8b0c179f":
                ["(44,607,189)", "(30,743,223)", "(16,738,407)"],
            "ctown_fs_city_2025_03_31_audited_p008_t01_r_d150cdd6665d44115b1b":
                ["113,038,565", "23,031,279", "4,331,705"],
            "ctown_fs_ws_2025_03_31_audited_p007_t01_r_d62b3e8e0c4a3c1e4bd7":
                ["-", "-", "48,951"],
        }
        for row_key, expected_values in controls.items():
            self.assertEqual(by_key[row_key]["proposed_raw_values"], expected_values)

    def test_single_revision_is_exact_and_source_supported(self) -> None:
        revised = [record for record in self.records if record["decision"] == "revised_and_approved"]
        self.assertEqual(len(revised), 1)
        record = revised[0]
        self.assertEqual(record["batch_record_number"], 10)
        self.assertEqual(record["row_key"], "ctown_fs_city_2025_03_31_audited_p007_t01_r_9951291bf61f85bd8d2d")
        self.assertEqual(record["raw_values"], [])
        self.assertEqual(record["raw_text"], "97,421,447 100,740,160 101,452,953")
        self.assertEqual(record["proposed_extraction_resolution"], "replace_with_source_verified_transcription")
        self.assertEqual(record["proposed_raw_values"], ["97,421,447", "100,740,160", "101,452,953"])

    def test_human_review_artifact_contains_every_exact_row_once(self) -> None:
        for record in self.records:
            self.assertEqual(self.markdown.count(f"`{record['row_key']}`"), 1)
            self.assertIn(f"PDF {record['pdf_page_number']} (printed {record['printed_page_label']})", self.markdown)


if __name__ == "__main__":
    unittest.main()

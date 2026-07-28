#!/usr/bin/env python3
"""Regression tests for Stage 2 grouping and shadow observations."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate-staged-pdf-v2-stage-2.py"


def load():
    spec = importlib.util.spec_from_file_location("stage2", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage2 = load()
        cls.groups, cls.observations = cls.stage2.build(
            cls.stage2.DEFAULT_PATHS
        )

    def test_every_financial_block_has_one_primary_owner(self) -> None:
        blocks = self.stage2.read_json(
            self.stage2.DEFAULT_PATHS["blocks"]
        )["records"]
        financial = {
            item["block_key"] for item in blocks
            if item["financial_candidate"]
        }
        owners = [
            member["block_key"]
            for group in self.groups["records"]
            for member in group["members"]
            if member["ownership"] == "primary"
        ]
        self.assertTrue(financial.issubset(set(owners)))
        self.assertEqual(len(owners), len(set(owners)))

    def test_representative_boundaries_and_relationships(self) -> None:
        by_key = {
            item["group_key"]: item for item in self.groups["records"]
        }
        supporting = by_key[
            self.stage2.group_key(
                "operating-supporting-schedules-statement"
            )
        ]
        self.assertEqual(
            [21, 22, 23],
            sorted({
                int(member["block_key"].split(":p")[1][:3])
                for member in supporting["members"]
            }),
        )
        detail = by_key[
            self.stage2.group_key(
                "public-works-buildings-detail-statement"
            )
        ]
        self.assertEqual((88, 92), (detail["page_start"], detail["page_end"]))
        water = by_key[
            self.stage2.group_key(
                "appendix-water-sewer-debt-statement"
            )
        ]
        self.assertEqual(
            ["preceded_by_divider"],
            [item["relationship_type"] for item in water["relationships"]],
        )

    def test_shadow_export_reproduces_snapshot_three_count(self) -> None:
        self.assertEqual(self.observations["summary"], {
            "manifest_observations": 2165,
            "recovered_property_tax_observations": 76,
            "recovered_city_debt_observations": 49,
            "total_observations": 2290,
            "natural_key_duplicates": 0,
            "unmapped_groups": 0,
            "database_write_count": 0,
            "publication_write_count": 0,
        })
        self.assertEqual(len(self.observations["records"]), 2290)

    def test_property_tax_revenue_uses_last_source_value(self) -> None:
        record = next(
            item for item in self.observations["records"]
            if item["natural_key"]["line_key"].endswith(
                "row-012-non-residents-revenue"
            )
        )
        self.assertEqual(record["value_numeric"], "1554094")
        self.assertEqual(
            record["source"]["value_ids"],
            ["ctown_budget_2026_2027_p149_r012_v04"],
        )

    def test_two_clean_runs_are_canonical(self) -> None:
        second = self.stage2.build(self.stage2.DEFAULT_PATHS)
        self.assertEqual(
            tuple(map(self.stage2.canonical_bytes, (self.groups, self.observations))),
            tuple(map(self.stage2.canonical_bytes, second)),
        )


if __name__ == "__main__":
    unittest.main()

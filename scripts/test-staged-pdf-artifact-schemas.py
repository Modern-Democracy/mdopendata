#!/usr/bin/env python3
"""Regression tests for staged PDF artifact JSON Schemas and semantic validation."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate-staged-pdf-artifacts.py"
SPEC = importlib.util.spec_from_file_location("staged_pdf_validator", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR_MODULE)

SCHEMA_REF = "../../schema/json-schema/staged-pdf-artifacts.schema.json"
SOURCE_HASH = "a" * 64
CONFIG_HASH = "b" * 64
ARTIFACT_HASH = "c" * 64
EVENT_HASH = "d" * 64
TEMPLATE_HASH = "e" * 64


def generator() -> dict:
    return {
        "name": "staged-pdf-test",
        "version": "1",
        "config_sha256": CONFIG_HASH,
    }


def review(status: str = "approved") -> dict:
    return {"status": status, "reason_codes": [], "decision_ids": []}


def locator(block_key: str | None = "document:p001:b001") -> dict:
    return {
        "page_key": "document:p001",
        "page_number": 1,
        "block_key": block_key,
        "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9},
        "text_excerpt": "Operating Budget",
    }


def document_header(artifact_type: str) -> dict:
    return {
        "$schema": SCHEMA_REF,
        "schema_version": 1,
        "artifact_type": artifact_type,
        "artifact_key": f"document:{artifact_type}:v1",
        "document_key": "document",
        "source_sha256": SOURCE_HASH,
        "generator": generator(),
        "upstream_artifacts": [],
    }


def source_evidence() -> dict:
    payload = document_header("source_evidence")
    payload.update(
        {
            "source": {
                "title": "Test Document",
                "municipality_key": "test",
                "document_kind": "budget",
                "repo_relpath": "docs/test.pdf",
                "source_uri": None,
                "sha256": SOURCE_HASH,
                "page_count": 1,
            },
            "render_policy": {
                "renderer": "fitz",
                "renderer_version": "1",
                "dpi": 144,
                "color_mode": "rgb",
            },
            "ocr_policy": {
                "mode": "when_text_deficient",
                "minimum_embedded_word_count": 5,
                "engine": "tesseract",
                "engine_version": "5",
            },
            "pages": [
                {
                    "page_key": "document:p001",
                    "page_number": 1,
                    "width_pt": 612,
                    "height_pt": 792,
                    "rotation": 0,
                    "media_box": {"x0": 0, "y0": 0, "x1": 612, "y1": 792},
                    "crop_box": {"x0": 0, "y0": 0, "x1": 612, "y1": 792},
                    "render": {
                        "repo_relpath": "data/runs/render-001.png",
                        "sha256": ARTIFACT_HASH,
                        "width_px": 1224,
                        "height_px": 1584,
                        "dpi": 144,
                    },
                    "thumbnail": {
                        "repo_relpath": "data/runs/thumb-001.png",
                        "sha256": ARTIFACT_HASH,
                        "width_px": 306,
                        "height_px": 396,
                        "dpi": 72,
                    },
                    "embedded_text": {
                        "available": True,
                        "word_count": 20,
                        "evidence_relpath": "data/runs/page-001.words.json",
                        "sha256": ARTIFACT_HASH,
                    },
                    "ocr": {
                        "status": "not_needed",
                        "engine": None,
                        "engine_version": None,
                        "rotation": None,
                        "dpi": None,
                        "mean_confidence": None,
                        "evidence_relpath": None,
                        "sha256": None,
                    },
                    "evidence_disposition": "complete",
                    "review": review(),
                }
            ],
        }
    )
    return payload


def block_inventory() -> dict:
    payload = document_header("block_inventory")
    payload.update(
        {
            "page_dispositions": [
                {
                    "page_key": "document:p001",
                    "page_number": 1,
                    "block_keys": ["document:p001:b001"],
                    "status": "inventoried",
                    "review": review(),
                }
            ],
            "records": [
                {
                    "block_key": "document:p001:b001",
                    "candidate_key": "run:candidate:1",
                    "page_key": "document:p001",
                    "page_number": 1,
                    "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9},
                    "polygon": None,
                    "reading_order": 1,
                    "block_type": "table",
                    "table_family_candidate": "operating_statement",
                    "text_source": "embedded",
                    "financial_candidate": True,
                    "regions": [],
                    "table_grid": {
                        "column_boundaries": [0.1, 0.5, 0.9],
                        "row_boundaries": [0.1, 0.2, 0.9],
                        "cells": [
                            {"cell_key": f"document:p001:b001:cell-{row}-{column}", "row_index": row, "column_index": column, "cell_type": "column_label" if row == 0 else ("row_label" if column == 0 else "cell"), "text_excerpt": None, "review": review()}
                            for row in range(2) for column in range(2)
                        ],
                        "review": review(),
                    },
                    "anchors": [
                        {
                            "anchor_key": "operating-heading",
                            "value_raw": "Operating Budget",
                            "bbox": {"x0": 0.3, "y0": 0.1, "x1": 0.7, "y1": 0.2},
                            "source": "embedded",
                        }
                    ],
                    "confidence": {
                        "level": "reviewed",
                        "score": None,
                        "reason_codes": [],
                    },
                    "evidence": [locator()],
                    "exclusion_disposition": None,
                    "review": review(),
                }
            ],
            "relationships": [],
        }
    )
    return payload


def content_groups() -> dict:
    payload = document_header("content_groups")
    payload["records"] = [
        {
            "group_key": "document:group:operating",
            "title": "Operating Budget",
            "family_candidate": "operating_statement",
            "disposition": "normalize",
            "page_start": 1,
            "page_end": 1,
            "members": [
                {
                    "block_key": "document:p001:b001",
                    "order": 1,
                    "role": "body",
                    "ownership": "primary",
                }
            ],
            "continuation_edges": [],
            "inherited_headers": [],
            "entity_candidates": ["Test Municipality"],
            "period_candidates": ["2026/2027"],
            "relationships": [],
            "review": review(),
        }
    ]
    return payload


def structural_template() -> dict:
    return {
        "$schema": SCHEMA_REF,
        "schema_version": 1,
        "artifact_type": "structural_template",
        "artifact_key": "template:operating:1.0.0",
        "generator": generator(),
        "upstream_artifacts": [],
        "template_key": "operating-statement",
        "template_version": "1.0.0",
        "status": "approved",
        "reuse_scope": "exact_document",
        "source_family": "municipal-budget",
        "supported_text_sources": ["embedded"],
        "anchors": [
            {
                "anchor_key": "operating-heading",
                "match_type": "normalized_text",
                "value": "Operating Budget",
                "region": {"x0": 0.2, "y0": 0.0, "x1": 0.8, "y1": 0.3},
                "geometry_tolerance": 0.05,
                "required": True,
            }
        ],
        "block_rules": [
            {
                "rule_key": "table-body",
                "block_type": "table",
                "minimum_count": 1,
                "maximum_count": 1,
                "reading_order": 1,
                "required": True,
            }
        ],
        "column_bands": [
            {
                "column_key": "label",
                "role_candidate": "raw_label",
                "x0": 0.1,
                "x1": 0.5,
                "tolerance": 0.03,
                "required": True,
            }
        ],
        "header_policy": {
            "mode": "repeated",
            "source_anchor_keys": ["operating-heading"],
            "allow_optional_repetition": False,
        },
        "continuation_rules": [],
        "termination_rules": [
            {
                "rule_key": "document-end",
                "rule_type": "end_of_group",
                "parameters": {},
                "required": True,
            }
        ],
        "negative_controls": [],
        "regression_controls": [
            {
                "control_key": "page-1-positive",
                "control_type": "positive",
                "source_locator": locator(),
                "expected_result": "One operating table block",
            }
        ],
        "approval": review(),
    }


def template_applications() -> dict:
    payload = document_header("template_applications")
    payload["records"] = [
        {
            "application_key": "document:application:operating",
            "group_key": "document:group:operating",
            "template_key": "operating-statement",
            "template_version": "1.0.0",
            "template_artifact_sha256": TEMPLATE_HASH,
            "fit_class": "exact",
            "anchor_matches": [
                {
                    "anchor_key": "operating-heading",
                    "matched": True,
                    "observed_value": "Operating Budget",
                    "observed_bbox": {"x0": 0.3, "y0": 0.1, "x1": 0.7, "y1": 0.2},
                    "score": 1.0,
                }
            ],
            "geometry_deltas": [
                {
                    "target_key": "operating-heading",
                    "delta_x0": 0,
                    "delta_y0": 0,
                    "delta_x1": 0,
                    "delta_y1": 0,
                    "within_tolerance": True,
                }
            ],
            "mismatches": [],
            "one_off_exception": None,
            "review": review(),
        }
    ]
    return payload


def review_decisions() -> dict:
    payload = document_header("review_decisions")
    payload.update(
        {
            "target_artifacts": [
                {
                    "artifact_type": "block_inventory",
                    "artifact_key": "document:block_inventory:v1",
                    "sha256": ARTIFACT_HASH,
                }
            ],
            "events": [
                {
                    "decision_id": "decision:1",
                    "sequence": 1,
                    "occurred_at": "2026-07-15T12:00:00Z",
                    "reviewer": {
                        "reviewer_id": "reviewer:1",
                        "display_name": "Reviewer",
                        "role": "data-reviewer",
                    },
                    "action": "approve",
                    "reason": "Source layout verified",
                    "prior_artifact_sha256": None,
                    "result_artifact_sha256": ARTIFACT_HASH,
                    "previous_event_sha256": None,
                    "event_sha256": EVENT_HASH,
                    "affected_keys": ["document:p001:b001"],
                    "source_locators": [locator()],
                    "changes": [],
                }
            ],
        }
    )
    return payload


def parity_report() -> dict:
    payload = document_header("parity_report")
    payload.update(
        {
            "baseline": {
                "source_document_id": 9,
                "source_sha256": SOURCE_HASH,
                "artifact_refs": [],
                "publication_snapshot_ids": [3],
            },
            "summary": {
                "total": 1,
                "matched": 1,
                "missing": 0,
                "extra": 0,
                "changed": 0,
                "provenance_shifted": 0,
            },
            "records": [
                {
                    "comparison_key": "observation:1",
                    "status": "matched",
                    "baseline_record": {"value": "100"},
                    "shadow_record": {"value": "100"},
                    "changed_fields": [],
                    "source_locators": [locator()],
                    "disposition": None,
                    "decision_id": None,
                }
            ],
            "run_controls": {
                "first_run_canonical_sha256": ARTIFACT_HASH,
                "second_run_canonical_sha256": ARTIFACT_HASH,
                "database_write_count": 0,
                "publication_snapshot_count_before": 2,
                "publication_snapshot_count_after": 2,
            },
            "passed": True,
            "blockers": [],
        }
    )
    return payload


def all_payloads() -> list[dict]:
    return [
        source_evidence(),
        block_inventory(),
        content_groups(),
        structural_template(),
        template_applications(),
        review_decisions(),
        parity_report(),
    ]


class StagedPdfArtifactSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = VALIDATOR_MODULE.load_validator()

    def assert_valid(self, payload: dict) -> None:
        self.assertEqual(
            VALIDATOR_MODULE.validate_payload(payload, self.validator),
            [],
        )

    def test_all_artifact_contracts_and_cross_references_pass(self) -> None:
        payloads = all_payloads()
        for payload in payloads:
            with self.subTest(payload["artifact_type"]):
                self.assert_valid(payload)
        self.assertEqual(VALIDATOR_MODULE.validate_artifact_set(payloads), [])

    def test_closed_contract_rejects_unknown_property(self) -> None:
        payload = source_evidence()
        payload["unexpected"] = True
        self.assertTrue(VALIDATOR_MODULE.validate_payload(payload, self.validator))

    def test_repository_path_rejects_parent_traversal(self) -> None:
        payload = source_evidence()
        payload["source"]["repo_relpath"] = "../outside.pdf"
        self.assertTrue(VALIDATOR_MODULE.validate_payload(payload, self.validator))

    def test_source_page_count_semantic_mismatch_fails(self) -> None:
        payload = source_evidence()
        payload["source"]["page_count"] = 2
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("page_count" in error for error in errors))

    def test_invalid_block_box_fails(self) -> None:
        payload = block_inventory()
        payload["records"][0]["bbox"]["x1"] = 0.05
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("x0 must be less than x1" in error for error in errors))

    def test_table_grid_must_match_parent_and_cover_each_coordinate(self) -> None:
        payload = block_inventory()
        grid = payload["records"][0]["table_grid"]
        grid["column_boundaries"][0] = 0.01
        grid["cells"].pop()
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("outer boundaries" in error for error in errors))
        self.assertTrue(any("one cell for every row and column" in error for error in errors))

    def test_component_validator_rejects_invalid_changed_block(self) -> None:
        record = block_inventory()["records"][0]
        component_validator = VALIDATOR_MODULE.load_component_validator("block_record")
        self.assertEqual(
            VALIDATOR_MODULE.validate_component(record, "block_record", component_validator),
            [],
        )
        record["unexpected"] = True
        errors = VALIDATOR_MODULE.validate_component(record, "block_record", component_validator)
        self.assertTrue(any("Additional properties" in error for error in errors))

    def test_relationship_endpoint_types_are_enforced(self) -> None:
        payload = block_inventory()
        payload["relationships"] = [{
            "relationship_key": "document:relationship:1",
            "relationship_type": "graph_source_table",
            "source": {"block_key": "document:p001:b001", "region_key": None},
            "target": {"block_key": "document:p001:b001", "region_key": None},
            "review": review(),
        }]
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("whole chart" in error for error in errors))

    def test_overview_relationship_requires_row_label_cell(self) -> None:
        payload = block_inventory()
        payload["relationships"] = [{
            "relationship_key": "document:relationship:1",
            "relationship_type": "overview_detail",
            "source": {"block_key": "document:p001:b001", "region_key": None},
            "target": {"block_key": "document:p001:b001", "region_key": None},
            "review": review(),
        }]
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("row-label cell" in error for error in errors))

    def test_group_duplicate_primary_ownership_fails(self) -> None:
        payload = content_groups()
        second = copy.deepcopy(payload["records"][0])
        second["group_key"] = "document:group:second"
        payload["records"].append(second)
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("multiple primary owners" in error for error in errors))

    def test_material_template_variation_cannot_be_approved(self) -> None:
        payload = template_applications()
        record = payload["records"][0]
        record["fit_class"] = "material_variation"
        record["mismatches"] = [
            {
                "mismatch_key": "mismatch:1",
                "category": "column_role",
                "severity": "material",
                "message": "Column meaning changed",
                "source_locators": [locator()],
            }
        ]
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(errors)

    def test_review_event_chain_break_fails(self) -> None:
        payload = review_decisions()
        second = copy.deepcopy(payload["events"][0])
        second["decision_id"] = "decision:2"
        second["sequence"] = 2
        second["previous_event_sha256"] = ARTIFACT_HASH
        second["event_sha256"] = TEMPLATE_HASH
        payload["events"].append(second)
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("prior event hash" in error for error in errors))

    def test_parity_summary_mismatch_fails(self) -> None:
        payload = parity_report()
        payload["summary"]["matched"] = 0
        errors = VALIDATOR_MODULE.validate_payload(payload, self.validator)
        self.assertTrue(any("does not match" in error for error in errors))

    def test_cross_artifact_unknown_block_fails(self) -> None:
        payloads = all_payloads()
        groups = next(item for item in payloads if item["artifact_type"] == "content_groups")
        groups["records"][0]["members"][0]["block_key"] = "document:p001:unknown"
        errors = VALIDATOR_MODULE.validate_artifact_set(payloads)
        self.assertTrue(any("unknown blocks" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Regression tests for staged PDF artifact schema version 2."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-staged-pdf-artifacts.py"
V1_TEST_PATH = ROOT / "scripts" / "test-staged-pdf-artifact-schemas.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator_module = load_module("staged_pdf_validator_v2", VALIDATOR_PATH)
v1 = load_module("staged_pdf_schema_v1_fixtures", V1_TEST_PATH)

SCHEMA_REF_V2 = "../../schema/json-schema/staged-pdf-artifacts-v2.schema.json"
POLICY_HASH = "f" * 64


def add_artifact_ref_versions(value) -> None:
    if isinstance(value, dict):
        if {"artifact_type", "artifact_key", "sha256"}.issubset(value):
            value["schema_version"] = 2
        for child in value.values():
            add_artifact_ref_versions(child)
    elif isinstance(value, list):
        for child in value:
            add_artifact_ref_versions(child)


def version_2(payload: dict) -> dict:
    payload = copy.deepcopy(payload)
    payload["$schema"] = SCHEMA_REF_V2
    payload["schema_version"] = 2
    payload["artifact_key"] = payload["artifact_key"].replace(":v1", ":v2")
    add_artifact_ref_versions(payload)
    if payload["artifact_type"] == "structural_template":
        payload["internal_region_rules"] = []
        payload["table_title_policy"] = {
            "mode": "absent",
            "allowed_positions": [],
            "anchor_keys": [],
        }
    if payload["artifact_type"] == "template_applications":
        for record in payload["records"]:
            record["policy_evaluation"] = {
                "policy_ref": policy_ref(),
                "outcome": "review_required",
                "selected_for_sample": False,
                "fit_eligible": True,
                "matcher_config_sha256": v1.CONFIG_HASH,
                "reason_codes": ["policy-review-required"],
            }
    if payload["artifact_type"] == "review_decisions":
        for event in payload["events"]:
            event["reviewer"]["actor_type"] = "human"
            event["decision_basis"] = "reviewer"
            event["policy_ref"] = None
    return payload


def artifact_ref(artifact_type: str, artifact_key: str, sha256: str) -> dict:
    return {
        "artifact_type": artifact_type,
        "artifact_key": artifact_key,
        "schema_version": 2,
        "sha256": sha256,
    }


def policy_ref() -> dict:
    return artifact_ref(
        "template_review_policy",
        "policy:operating:1.0.0",
        POLICY_HASH,
    )


def policy(mode: str = "review_required") -> dict:
    promoted = mode != "review_required"
    reviewed = 2 if promoted else 0
    return {
        "$schema": SCHEMA_REF_V2,
        "schema_version": 2,
        "artifact_type": "template_review_policy",
        "artifact_key": "policy:operating:1.0.0",
        "generator": v1.generator(),
        "upstream_artifacts": [],
        "policy_key": "policy:operating",
        "policy_version": "1.0.0",
        "status": "approved",
        "template_binding": {
            "template_key": "operating-statement",
            "template_version": "1.0.0",
            "artifact_ref": artifact_ref(
                "structural_template",
                "template:operating:1.0.0",
                v1.TEMPLATE_HASH,
            ),
        },
        "supersedes_policy_ref": None,
        "scope": {
            "reuse_scope": "exact_document",
            "jurisdiction_key": "test",
            "source_family": "municipal-budget",
            "document_family": "annual-budget",
        },
        "matcher": v1.generator(),
        "mode": mode,
        "eligible_fit_classes": ["exact", "light_variation"],
        "allowed_light_mismatch_categories": ["geometry"],
        "sample_rate": 1 if mode == "review_required" else (0.5 if mode == "sample_review" else 0),
        "promotion_gates": {
            "minimum_positive_examples": 1 if promoted else 0,
            "minimum_negative_controls": 1 if promoted else 0,
            "minimum_reviewed_applications": 2 if promoted else 0,
            "minimum_observed_precision": 1 if promoted else 0,
            "maximum_false_approvals": 0,
        },
        "promotion_evidence": {
            "positive_application_keys": ["application:positive"] if promoted else [],
            "negative_control_keys": ["control:negative"] if promoted else [],
            "validation_run_keys": ["validation:1"] if promoted else [],
            "reviewed_application_count": reviewed,
            "accepted_application_count": reviewed,
            "rejected_application_count": 0,
            "false_approval_count": 0,
            "observed_precision": 1 if promoted else None,
        },
        "suspension_rules": {
            "material_mismatch": True,
            "negative_control_failure": True,
            "sample_rejection": True,
            "matcher_change": True,
            "source_profile_change": True,
        },
        "approval": {
            "status": "approved",
            "reason_codes": ["reviewer-policy-approval"],
            "decision_ids": ["decision:policy:1"],
        },
    }


def all_payloads() -> list[dict]:
    payloads = [version_2(payload) for payload in v1.all_payloads()]
    payloads.insert(4, policy())
    return payloads


def cells_for_2x2(kind: str) -> list[dict]:
    review = v1.review()

    def cell(key: str, row: int, column: int, **values) -> dict:
        return {
            "cell_key": key,
            "row_index": row,
            "column_index": column,
            "cell_type": values.pop("cell_type", "cell"),
            "text_excerpt": None,
            "review": review,
            **values,
        }

    if kind == "omitted":
        return [cell(f"cell:{row}:{column}", row, column) for row in range(2) for column in range(2)]
    if kind == "explicit":
        return [cell(f"cell:{row}:{column}", row, column, row_span=1, column_span=1) for row in range(2) for column in range(2)]
    if kind == "horizontal":
        return [cell("cell:top", 0, 0, column_span=2), cell("cell:bottom-left", 1, 0), cell("cell:bottom-right", 1, 1)]
    if kind == "vertical":
        return [cell("cell:left", 0, 0, row_span=2), cell("cell:top-right", 0, 1), cell("cell:bottom-right", 1, 1)]
    if kind == "two-dimensional":
        return [cell("cell:all", 0, 0, row_span=2, column_span=2)]
    if kind == "top-title":
        return [cell("cell:title", 0, 0, column_span=2, cell_type="table_title"), cell("cell:bottom-left", 1, 0), cell("cell:bottom-right", 1, 1)]
    if kind == "bottom-title":
        return [cell("cell:top-left", 0, 0), cell("cell:top-right", 0, 1), cell("cell:title", 1, 0, column_span=2, cell_type="table_title")]
    raise ValueError(kind)


def block_with_cells(kind: str) -> dict:
    payload = version_2(v1.block_inventory())
    payload["records"][0]["table_grid"]["cells"] = cells_for_2x2(kind)
    return payload


class StagedPdfArtifactSchemaV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = validator_module.load_validator(2)

    def assert_valid(self, payload: dict) -> None:
        self.assertEqual(validator_module.validate_payload(payload, self.validator), [])

    def test_version_1_contracts_still_pass_unchanged(self) -> None:
        validator = validator_module.load_validator(1)
        for payload in v1.all_payloads():
            with self.subTest(payload["artifact_type"]):
                self.assertEqual(validator_module.validate_payload(payload, validator), [])

    def test_all_version_2_contracts_and_cross_references_pass(self) -> None:
        payloads = all_payloads()
        for payload in payloads:
            with self.subTest(payload["artifact_type"]):
                self.assert_valid(payload)
        self.assertEqual(validator_module.validate_artifact_set(payloads), [])

    def test_omitted_and_explicit_unit_spans_are_equivalent(self) -> None:
        self.assert_valid(block_with_cells("omitted"))
        self.assert_valid(block_with_cells("explicit"))

    def test_horizontal_vertical_and_two_dimensional_spans_pass(self) -> None:
        for kind in ("horizontal", "vertical", "two-dimensional"):
            with self.subTest(kind=kind):
                self.assert_valid(block_with_cells(kind))

    def test_top_and_bottom_table_titles_pass(self) -> None:
        for kind in ("top-title", "bottom-title"):
            with self.subTest(kind=kind):
                self.assert_valid(block_with_cells(kind))

    def test_overlap_gap_and_overflow_fail(self) -> None:
        overlap = block_with_cells("omitted")
        overlap["records"][0]["table_grid"]["cells"][0]["column_span"] = 2
        gap = block_with_cells("omitted")
        gap["records"][0]["table_grid"]["cells"].pop()
        overflow = block_with_cells("two-dimensional")
        overflow["records"][0]["table_grid"]["cells"][0]["row_span"] = 3
        for name, payload in (("overlap", overlap), ("gap", gap), ("overflow", overflow)):
            with self.subTest(name=name):
                errors = validator_module.validate_payload(payload, self.validator)
                self.assertTrue(any("effective spans" in error for error in errors))

    def test_invalid_table_title_positions_and_counts_fail(self) -> None:
        partial = block_with_cells("omitted")
        partial["records"][0]["table_grid"]["cells"][0]["cell_type"] = "table_title"
        duplicate = block_with_cells("top-title")
        duplicate["records"][0]["table_grid"]["cells"] = [
            {**cells_for_2x2("top-title")[0]},
            {**cells_for_2x2("bottom-title")[-1]},
        ]
        internal = block_with_cells("omitted")
        grid = internal["records"][0]["table_grid"]
        grid["row_boundaries"] = [0.1, 0.2, 0.3, 0.9]
        grid["cells"] = [
            {**cell, "cell_key": f"top:{index}", "row_index": 0}
            for index, cell in enumerate(cells_for_2x2("omitted")[:2])
        ] + [
            {
                **cells_for_2x2("top-title")[0],
                "cell_key": "internal:title",
                "row_index": 1,
            }
        ] + [
            {**cell, "cell_key": f"bottom:{index}", "row_index": 2}
            for index, cell in enumerate(cells_for_2x2("omitted")[:2])
        ]
        for name, payload in (("partial", partial), ("duplicate", duplicate), ("internal", internal)):
            with self.subTest(name=name):
                errors = validator_module.validate_payload(payload, self.validator)
                self.assertTrue(any("table_title" in error for error in errors))

    def test_formatted_text_title_passes_and_duplicate_sibling_fails(self) -> None:
        payload = version_2(v1.block_inventory())
        record = payload["records"][0]
        record["block_type"] = "formatted_text"
        record["financial_candidate"] = False
        record["table_grid"] = None
        record["regions"] = [{
            "region_key": "document:p001:b001:title",
            "region_type": "title",
            "bbox": {"x0": 0.2, "y0": 0.2, "x1": 0.8, "y1": 0.3},
            "text_excerpt": "Operating Budget",
            "review": v1.review(),
        }]
        self.assert_valid(payload)
        sibling = copy.deepcopy(record)
        sibling["block_key"] = "document:p001:b002"
        sibling["block_type"] = "title"
        sibling["bbox"] = copy.deepcopy(record["regions"][0]["bbox"])
        sibling["regions"] = []
        payload["records"].append(sibling)
        payload["page_dispositions"][0]["block_keys"].append(sibling["block_key"])
        errors = validator_module.validate_payload(payload, self.validator)
        self.assertTrue(any("duplicates sibling title" in error for error in errors))

    def test_review_policy_modes_pass(self) -> None:
        for mode in ("review_required", "sample_review", "auto_approve"):
            with self.subTest(mode=mode):
                self.assert_valid(policy(mode))

    def test_policy_references_require_version_2(self) -> None:
        policy_payload = policy()
        policy_payload["template_binding"]["artifact_ref"]["schema_version"] = 1
        errors = validator_module.validate_payload(policy_payload, self.validator)
        self.assertTrue(any("requires a version 2 template" in error for error in errors))
        applications = version_2(v1.template_applications())
        applications["records"][0]["policy_evaluation"]["policy_ref"]["schema_version"] = 1
        errors = validator_module.validate_payload(applications, self.validator)
        self.assertTrue(any("version 2 policy" in error for error in errors))

    def test_sample_review_requires_a_partial_sample_rate(self) -> None:
        payload = policy("sample_review")
        payload["sample_rate"] = 1
        self.assertTrue(validator_module.validate_payload(payload, self.validator))

    def test_material_variation_cannot_auto_approve(self) -> None:
        payload = version_2(v1.template_applications())
        record = payload["records"][0]
        record["fit_class"] = "material_variation"
        record["mismatches"] = [{
            "mismatch_key": "mismatch:material",
            "category": "column_role",
            "severity": "material",
            "message": "Column role changed",
            "source_locators": [v1.locator()],
        }]
        record["policy_evaluation"].update({
            "outcome": "auto_approved",
            "fit_eligible": True,
        })
        record["review"] = {
            "status": "needs_review",
            "reason_codes": ["material-template-mismatch"],
            "decision_ids": [],
        }
        errors = validator_module.validate_payload(payload, self.validator)
        self.assertTrue(any("material variation" in error for error in errors))

    def test_non_allowlisted_light_variation_and_unknown_policy_fail(self) -> None:
        payloads = all_payloads()
        applications = next(item for item in payloads if item["artifact_type"] == "template_applications")
        record = applications["records"][0]
        record["fit_class"] = "light_variation"
        record["mismatches"] = [{
            "mismatch_key": "mismatch:unit",
            "category": "unit",
            "severity": "light",
            "message": "Unit cue shifted",
            "source_locators": [v1.locator()],
        }]
        record["policy_evaluation"].update({"outcome": "auto_approved", "fit_eligible": True})
        record["review"] = {
            "status": "approved",
            "reason_codes": ["policy-auto-approve"],
            "decision_ids": ["decision:auto:1"],
        }
        policy_payload = next(item for item in payloads if item["artifact_type"] == "template_review_policy")
        policy_payload.update(copy.deepcopy(policy("auto_approve")))
        errors = validator_module.validate_artifact_set(payloads)
        self.assertTrue(any("non-allowlisted" in error for error in errors))
        record["policy_evaluation"]["policy_ref"]["artifact_key"] = "policy:unknown"
        errors = validator_module.validate_artifact_set(payloads)
        self.assertTrue(any("unknown policy" in error for error in errors))

    def test_matcher_policy_drift_fails(self) -> None:
        payloads = all_payloads()
        applications = next(item for item in payloads if item["artifact_type"] == "template_applications")
        applications["records"][0]["policy_evaluation"]["matcher_config_sha256"] = "0" * 64
        errors = validator_module.validate_artifact_set(payloads)
        self.assertTrue(any("matcher configuration differs" in error for error in errors))

    def test_automatic_decision_actor_and_policy_promotion_actor_are_enforced(self) -> None:
        payload = version_2(v1.review_decisions())
        event = payload["events"][0]
        event.update({
            "action": "auto_approve",
            "decision_basis": "template_policy",
            "policy_ref": policy_ref(),
        })
        event["reviewer"]["actor_type"] = "human"
        errors = validator_module.validate_payload(payload, self.validator)
        self.assertTrue(any("system actor" in error for error in errors))
        event.update({"action": "promote_policy", "decision_basis": "reviewer", "policy_ref": None})
        event["reviewer"]["actor_type"] = "system"
        errors = validator_module.validate_payload(payload, self.validator)
        self.assertTrue(any("human actor" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

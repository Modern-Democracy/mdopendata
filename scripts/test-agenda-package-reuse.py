#!/usr/bin/env python3
"""Regression tests for Phase 6 agenda-package reuse."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/preview-agenda-package-reuse.py"
CANONICAL_ROOT = (
    ROOT
    / "data/document-ingestion/profiles/"
    "charlottetown-council-public-meeting/v1"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name, path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load():
    return load_module(SCRIPT_PATH, "agenda_package_reuse")


def artifact_ref(artifact_type: str, key: str, character: str) -> dict:
    return {
        "artifact_type": artifact_type,
        "artifact_key": key,
        "schema_version": 2,
        "sha256": character * 64,
    }


def anchor(key: str, value: str, *, match_type: str = "normalized_text") -> dict:
    return {
        "anchor_key": key,
        "match_type": match_type,
        "value": value,
        "required": True,
    }


def template(
    key: str,
    family: str,
    start: list[dict],
    *,
    continuation: list[dict] | None = None,
    end: list[dict] | None = None,
    minimum: int = 1,
    maximum: int = 1,
    mode: str = "auto_approve",
    sample_rate: float = 0,
    priority: int = 10,
) -> dict:
    return {
        "document_template_key": key,
        "document_family": family,
        "priority": priority,
        "template_ref": artifact_ref(
            "structural_template", f"{key}:1.0.0", "a"
        ),
        "policy_ref": artifact_ref(
            "template_review_policy", f"{key}:policy:1.0.0", "b"
        ),
        "policy_mode": mode,
        "sample_rate": sample_rate,
        "start_anchors": start,
        "continuation_anchors": continuation or [],
        "end_anchors": end or [],
        "minimum_pages": minimum,
        "maximum_pages": maximum,
        "allow_visual_only_continuation": False,
    }


class AgendaPackageReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matcher = load()

    def setUp(self) -> None:
        self.profile = {
            "$schema": "agenda-package-reuse-profile.schema.json",
            "schema_version": 1,
            "profile_key": "charlottetown:council-package",
            "profile_version": "1.0.0",
            "status": "approved",
            "scope": {
                "jurisdiction_key": "charlottetown",
                "source_family": "charlottetown-council",
                "document_family": "agenda-package",
                "reuse_scope": "cross_edition_family",
            },
            "package_grammar": {
                "first_document_family": "agenda",
                "allowed_transitions": [
                    {"from": "agenda", "to": "minutes"},
                    {"from": "minutes", "to": "minutes"},
                ],
                "require_complete_coverage": True,
            },
            "document_templates": [
                template(
                    "charlottetown:agenda",
                    "agenda",
                    [anchor("agenda-heading", "REGULAR MONTHLY MEETING OF COUNCIL AGENDA")],
                ),
                template(
                    "charlottetown:minutes",
                    "minutes",
                    [anchor("minutes-heading", r"CITY OF CHARLOTTETOWN\s+DRAFT", match_type="regex")],
                    continuation=[
                        anchor("minutes-page", r"Page [23] of 3", match_type="regex")
                    ],
                    end=[
                        anchor("minutes-end", "Page 3 of 3")
                    ],
                    minimum=3,
                    maximum=3,
                    mode="review_required",
                    sample_rate=1,
                ),
            ],
            "positive_controls": [{
                "control_key": "positive:single-and-multi",
                "package_key": "package:positive",
                "page_numbers": [1, 2, 3, 4],
                "expected_result": "matched",
            }],
            "negative_controls": [{
                "control_key": "negative:minutes-not-agenda",
                "package_key": "package:negative",
                "page_numbers": [1],
                "expected_result": "unknown",
            }],
            "approval": {
                "status": "approved",
                "decision_id": "decision:profile:000001",
            },
        }
        self.package = {
            "package_key": "package:positive",
            "source_sha256": "c" * 64,
            "jurisdiction_key": "charlottetown",
            "source_family": "charlottetown-council",
            "document_family": "agenda-package",
            "pages": [
                {
                    "page_number": 1,
                    "text_source": "embedded",
                    "text": "CITY OF CHARLOTTETOWN\nREGULAR MONTHLY MEETING OF COUNCIL AGENDA",
                },
                {
                    "page_number": 2,
                    "text_source": "embedded",
                    "text": "CITY OF CHARLOTTETOWN DRAFT\nMinutes\nPage 1 of 3",
                },
                {
                    "page_number": 3,
                    "text_source": "embedded",
                    "text": "Minutes continued\nPage 2 of 3",
                },
                {
                    "page_number": 4,
                    "text_source": "embedded",
                    "text": "Minutes concluded\nPage 3 of 3",
                },
            ],
        }

    def test_single_and_multi_page_documents_preserve_order_and_coverage(self) -> None:
        result = self.matcher.preview(self.profile, self.package)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(
            [
                (item["document_family"], item["page_start"], item["page_end"])
                for item in result["documents"]
            ],
            [("agenda", 1, 1), ("minutes", 2, 4)],
        )
        self.assertEqual(
            [
                page["page_role"]
                for page in result["documents"][1]["page_sequence"]
            ],
            ["document_start", "document_continuation", "document_end"],
        )
        self.assertEqual(result["coverage"], {
            "total_pages": 4,
            "assigned_pages": 4,
            "unknown_pages": 0,
            "conflicting_pages": 0,
            "omitted_pages": 0,
        })
        self.assertEqual(
            self.matcher.validate(
                self.matcher.PREVIEW_SCHEMA_PATH, result
            ),
            [],
        )

    def test_later_package_can_auto_approve_under_exact_active_policies(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["document_templates"][1]["policy_mode"] = "auto_approve"
        profile["document_templates"][1]["sample_rate"] = 0
        first = self.matcher.preview(profile, self.package)
        second = self.matcher.preview(profile, self.package)
        self.assertEqual(
            self.matcher.canonical_bytes(first),
            self.matcher.canonical_bytes(second),
        )
        self.assertEqual(first["status"], "matched")
        self.assertTrue(all(
            item["policy_evaluation"]["outcome"] == "auto_approved"
            for item in first["documents"]
        ))

    def test_deterministic_sampling_is_stable(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["document_templates"][1]["policy_mode"] = "sample_review"
        profile["document_templates"][1]["sample_rate"] = 0.5
        first = self.matcher.preview(profile, self.package)
        second = self.matcher.preview(profile, self.package)
        self.assertEqual(
            first["documents"][1]["policy_evaluation"],
            second["documents"][1]["policy_evaluation"],
        )

    def test_nearest_negative_is_unknown_not_forced_into_agenda(self) -> None:
        package = copy.deepcopy(self.package)
        package["package_key"] = "package:negative"
        package["pages"][0]["text"] = (
            "CITY OF CHARLOTTETOWN\nREGULAR MONTHLY MEETING OF COUNCIL"
        )
        result = self.matcher.preview(self.profile, package)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["unknown_pages"], [1])
        self.assertEqual(result["coverage"]["omitted_pages"], 0)
        self.assertEqual(result["documents"][0]["document_family"], "minutes")
        self.assertEqual(
            result["documents"][0]["fit_class"], "material_variation"
        )

    def test_equal_priority_start_match_is_reported_as_conflict(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["document_templates"].append(
            template(
                "charlottetown:agenda-conflict",
                "agenda",
                [anchor("agenda-conflict", "REGULAR MONTHLY MEETING OF COUNCIL AGENDA")],
            )
        )
        result = self.matcher.preview(profile, self.package)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["conflicts"][0]["page_number"], 1)
        self.assertEqual(result["coverage"]["conflicting_pages"], 1)
        self.assertEqual(result["coverage"]["omitted_pages"], 0)

    def test_missing_end_anchor_is_material_and_blocks_policy(self) -> None:
        package = copy.deepcopy(self.package)
        package["pages"][-1]["text"] = "Minutes concluded without pagination"
        result = self.matcher.preview(self.profile, package)
        minutes = result["documents"][1]
        self.assertEqual(minutes["fit_class"], "material_variation")
        self.assertEqual(
            minutes["policy_evaluation"]["outcome"], "blocked"
        )
        self.assertTrue(any(
            item["reason"] == "end-anchor-mismatch"
            for item in minutes["unresolved_evidence"]
        ))

    def test_source_profile_scope_mismatch_fails_closed(self) -> None:
        package = copy.deepcopy(self.package)
        package["jurisdiction_key"] = "halifax"
        with self.assertRaisesRegex(ValueError, "outside the approved profile scope"):
            self.matcher.preview(self.profile, package)

    def test_contract_schemas_are_valid_draft_2020_12(self) -> None:
        for path in (
            self.matcher.PROFILE_SCHEMA_PATH,
            self.matcher.PREVIEW_SCHEMA_PATH,
        ):
            Draft202012Validator.check_schema(
                json.loads(path.read_text(encoding="utf-8"))
            )

    def test_reviewer_exposes_read_only_reuse_preview(self) -> None:
        server = (ROOT / "web/server.js").read_text(encoding="utf-8")
        ui = (
            ROOT
            / "web/public/ui_kits/agenda-package-ingestion/index.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "/reuse-preview", server
        )
        self.assertIn(
            "preview-agenda-package-reuse.py", server
        )
        self.assertIn(
            "document_family: source.document_type_key", server
        )
        self.assertIn(
            "Municipal package reuse preview", ui
        )
        self.assertIn(
            "without changing page classifications", ui
        )

    def test_canonical_real_package_profile_and_controls(self) -> None:
        profile = json.loads(
            (CANONICAL_ROOT / "profile.json").read_text(encoding="utf-8")
        )
        positive_package = json.loads(
            (CANONICAL_ROOT / "positive-package.json").read_text(
                encoding="utf-8"
            )
        )
        negative_package = json.loads(
            (CANONICAL_ROOT / "negative-package.json").read_text(
                encoding="utf-8"
            )
        )
        source_control = json.loads(
            (CANONICAL_ROOT / "source-control.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            self.matcher.validate(self.matcher.PROFILE_SCHEMA_PATH, profile),
            [],
        )
        self.assertEqual(profile["status"], "approved")
        self.assertEqual(
            {item["policy_mode"] for item in profile["document_templates"]},
            {"review_required"},
        )
        validator = load_module(
            ROOT / "scripts/validate-staged-pdf-artifacts.py",
            "agenda_package_artifact_validator",
        )
        for item in profile["document_templates"]:
            family = item["document_family"]
            template_path = (
                CANONICAL_ROOT / family / "structural-template.json"
            )
            policy_path = (
                CANONICAL_ROOT / family / "template-review-policy.json"
            )
            template = json.loads(template_path.read_text(encoding="utf-8"))
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            self.assertEqual(validator.validate_payload(template), [])
            self.assertEqual(validator.validate_payload(policy), [])
            self.assertEqual(
                hashlib.sha256(template_path.read_bytes()).hexdigest(),
                item["template_ref"]["sha256"],
            )
            self.assertEqual(
                hashlib.sha256(policy_path.read_bytes()).hexdigest(),
                item["policy_ref"]["sha256"],
            )
        self.assertEqual(
            source_control["positive_source"]["page_classification_ids"],
            [1, 2, 3, 4, 5, 6],
        )
        self.assertEqual(
            source_control["positive_source"]["assembly_ids"],
            [12, 13, 14, 15, 16],
        )
        positive = self.matcher.preview(profile, positive_package)
        self.assertEqual(positive["status"], "needs_review")
        self.assertEqual(
            [
                (item["page_start"], item["page_end"], item["fit_class"])
                for item in positive["documents"]
            ],
            [
                (1, 1, "exact"),
                (2, 2, "exact"),
                (3, 3, "exact"),
                (4, 4, "exact"),
                (5, 6, "exact"),
            ],
        )
        self.assertEqual(positive["coverage"], {
            "total_pages": 6,
            "assigned_pages": 6,
            "unknown_pages": 0,
            "conflicting_pages": 0,
            "omitted_pages": 0,
        })
        negative = self.matcher.preview(profile, negative_package)
        self.assertEqual(negative["status"], "blocked")
        self.assertEqual(negative["documents"], [])
        self.assertEqual(negative["unknown_pages"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(negative["coverage"]["omitted_pages"], 0)


if __name__ == "__main__":
    unittest.main()

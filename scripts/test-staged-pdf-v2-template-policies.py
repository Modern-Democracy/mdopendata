#!/usr/bin/env python3
"""Regression tests for immutable Stage 1 templates and review policies."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER_PATH = ROOT / "scripts/manage-staged-pdf-template-policy-v2.py"
MATCHER_PATH = ROOT / "scripts/preview-staged-pdf-structural-propagation.py"
WRITER_PATH = ROOT / "scripts/update-staged-pdf-block-inventory-v2.py"
CANONICAL = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v2"
SOURCE_BLOCK_KEY = "ctown-budget-2026-2027:p018:body"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Version2TemplatePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.root = Path(
            tempfile.mkdtemp(prefix="stage-1-template-policy-", dir=ROOT / "tmp")
        )
        self.workspace = self.root / "v2"
        for relative in (
            "stage-0/source-evidence.json",
            "stage-1/block-inventory.json",
            "review/review-decisions.json",
        ):
            target = self.workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(CANONICAL / relative, target)
        self.manager = load("stage1_template_policy_manager", MANAGER_PATH)
        self.matcher = load("stage1_template_policy_matcher", MATCHER_PATH)
        self.writer = load("stage1_template_policy_writer", WRITER_PATH)
        self.manager.configure_workspace(self.workspace)
        self.matcher.BLOCK_PATH = self.workspace / "stage-1/block-inventory.json"
        self.matcher.SOURCE_PATH = self.workspace / "stage-0/source-evidence.json"
        self.matcher.REVIEW_PATH = self.workspace / "review/review-decisions.json"
        self.writer.BLOCK_PATH = self.matcher.BLOCK_PATH
        self.writer.SOURCE_PATH = self.matcher.SOURCE_PATH
        self.writer.REVIEW_PATH = self.matcher.REVIEW_PATH
        self.block = self.manager.read_json(self.manager.BLOCK_PATH)
        self.source = self.manager.read_json(self.matcher.SOURCE_PATH)
        self.preview = self.matcher.generate_preview(
            self.block,
            self.source,
            self.manager.read_json(self.manager.REVIEW_PATH),
            SOURCE_BLOCK_KEY,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def command(self, action: str, **extra) -> dict:
        return {
            "action": action,
            "document_key": self.block["document_key"],
            "source_block_key": SOURCE_BLOCK_KEY,
            "pattern_sha256": self.preview["pattern_sha256"],
            "expected_artifact_sha256": self.manager.digest_path(
                self.manager.BLOCK_PATH
            ),
            "expected_review_artifact_sha256": self.manager.digest_path(
                self.manager.REVIEW_PATH
            ),
            "reason": "Template policy regression",
            **extra,
        }

    def promote_template(self) -> dict:
        return self.manager.manage(self.command("promote_template"))

    def test_template_and_review_policy_are_immutable_and_valid(self) -> None:
        template_result = self.promote_template()
        template = template_result["artifact"]
        self.assertEqual(template["reuse_scope"], "exact_document")
        self.assertEqual(template["status"], "approved")
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            self.manager.manage(self.command("promote_template"))
        policy_result = self.manager.manage(
            self.command("promote_policy", mode="review_required")
        )
        policy = policy_result["artifact"]
        self.assertEqual(policy["mode"], "review_required")
        self.assertEqual(
            policy["template_binding"]["artifact_ref"]["sha256"],
            template_result["artifact_sha256"],
        )
        validator = self.manager.load_validator()
        self.assertEqual(validator.validate_payload(template), [])
        self.assertEqual(validator.validate_payload(policy), [])

    def test_evidence_gates_block_premature_automation(self) -> None:
        self.promote_template()
        before = self.manager.REVIEW_PATH.read_bytes()
        with self.assertRaisesRegex(ValueError, "promotion gates"):
            self.manager.manage(self.command("promote_policy", mode="auto_approve"))
        self.assertEqual(self.manager.REVIEW_PATH.read_bytes(), before)
        self.assertEqual(
            list(self.manager.POLICY_ROOT.rglob("template-review-policy.json")),
            [],
        )

    def test_sampling_is_deterministic_and_material_variation_is_blocked(self) -> None:
        template_result = self.promote_template()
        template = copy.deepcopy(template_result["artifact"])
        template["negative_controls"] = [{
            "control_key": "negative:test:001",
            "control_type": "negative",
            "source_locator": copy.deepcopy(
                template["regression_controls"][0]["source_locator"]
            ),
            "expected_result": "Known mismatch remains blocked.",
        }]
        review = {"events": []}
        locator = copy.deepcopy(template["regression_controls"][0]["source_locator"])
        for index in range(4):
            review["events"].append({
                "decision_id": f"accepted:{index}",
                "action": "apply_template",
                "source_locators": [locator],
            })
        review["events"].append({
            "decision_id": "rejected:0",
            "action": "reject",
            "source_locators": [locator],
        })
        policy = self.manager.policy_from_template(
            template,
            template_result["artifact_sha256"],
            review,
            "sample_review",
            "test:decision",
        )
        policy_entry = {
            "artifact": policy,
            "sha256": self.manager.digest_bytes(
                self.manager.canonical_bytes(policy)
            ),
        }
        exact = {
            "target_block_key": "target:exact",
            "fit_class": "exact",
            "mismatch_evidence": [],
        }
        first = self.manager.evaluate_candidate(
            exact, {"artifact": template}, policy_entry
        )
        second = self.manager.evaluate_candidate(
            exact, {"artifact": template}, policy_entry
        )
        self.assertEqual(first, second)
        material = {
            "target_block_key": "target:material",
            "fit_class": "material_variation",
            "mismatch_evidence": [{"category": "structure"}],
        }
        self.assertEqual(
            self.manager.evaluate_candidate(
                material, {"artifact": template}, policy_entry
            )["outcome"],
            "blocked",
        )
        template_entry = {
            "artifact": template,
            "sha256": template_result["artifact_sha256"],
        }
        self.manager.registry_for_pattern = (
            lambda _document_key, _pattern_sha256: {
                "template": template_entry,
                "policy": policy_entry,
            }
        )
        preview = {
            "source_block_key": SOURCE_BLOCK_KEY,
            "pattern_sha256": self.preview["pattern_sha256"],
            "matcher": copy.deepcopy(self.preview["matcher"]),
            "candidates": [
                copy.deepcopy(
                    next(
                        item
                        for item in self.preview["candidates"]
                        if item["applicable"]
                    )
                )
            ],
        }
        suspended = self.manager.evaluate_preview(
            preview,
            self.block["document_key"],
            {
                "events": [
                    {
                        "decision_id": "test:decision",
                        "sequence": 1,
                        "action": "promote_policy",
                        "changes": [],
                    },
                    {
                        "decision_id": "test:reject",
                        "sequence": 2,
                        "action": "reject",
                        "changes": [{
                            "new_value": {
                                "pattern_sha256": self.preview["pattern_sha256"]
                            }
                        }],
                    },
                ]
            },
        )
        self.assertTrue(suspended["registry"]["runtime_suspended"])
        self.assertIn(
            "sample-rejection",
            suspended["registry"]["suspension_reason_codes"],
        )
        self.assertEqual(
            suspended["candidates"][0]["policy_evaluation"]["outcome"],
            "blocked",
        )

    def test_suspension_supersedes_with_review_required_policy(self) -> None:
        template_result = self.promote_template()
        first = self.manager.manage(
            self.command("promote_policy", mode="review_required")
        )
        suspended = self.manager.manage(self.command("suspend_policy"))["artifact"]
        self.assertEqual(suspended["mode"], "review_required")
        self.assertIn("policy-suspended", suspended["approval"]["reason_codes"])
        self.assertEqual(
            suspended["supersedes_policy_ref"]["sha256"],
            first["artifact_sha256"],
        )

    def test_automatic_apply_records_exact_system_policy_audit(self) -> None:
        candidate = next(
            item for item in self.preview["candidates"] if item["applicable"]
        )
        policy_ref = {
            "artifact_type": "template_review_policy",
            "artifact_key": "ctown-budget-2026-2027:policy:test:1.0.0",
            "schema_version": 2,
            "sha256": "a" * 64,
        }
        candidate = copy.deepcopy(candidate)
        candidate["policy_evaluation"] = {
            "policy_ref": policy_ref,
            "outcome": "auto_approved",
            "selected_for_sample": False,
            "fit_eligible": True,
            "matcher_config_sha256": "b" * 64,
            "reason_codes": ["policy-auto-approve"],
        }
        candidate["automation_context"] = {
            "source_block_key": SOURCE_BLOCK_KEY,
            "pattern_sha256": self.preview["pattern_sha256"],
            "template_ref": {
                "artifact_type": "structural_template",
                "artifact_key": "ctown-budget-2026-2027:template:test:1.0.0",
                "schema_version": 2,
                "sha256": "c" * 64,
            },
            "policy_ref": policy_ref,
            "matcher": copy.deepcopy(self.preview["matcher"]),
            "fit_class": candidate["fit_class"],
            "matching_evidence": copy.deepcopy(candidate["matching_evidence"]),
            "mismatch_evidence": copy.deepcopy(candidate["mismatch_evidence"]),
        }

        class FakeMatcher:
            @staticmethod
            def generate_preview(*_args):
                return {
                    "pattern_sha256": self.preview["pattern_sha256"],
                    "candidates": [candidate],
                }

        self.writer.load_propagation_matcher = lambda: FakeMatcher
        command = self.command(
            "auto_approve",
            targets=[{
                "target_block_key": candidate["target_block_key"],
                "proposal_sha256": candidate["proposal_sha256"],
            }],
        )
        command_path = self.root / "auto-command.json"
        command_path.write_text(json.dumps(command), encoding="utf-8")
        result = self.writer.update(command_path)
        review = self.manager.read_json(self.manager.REVIEW_PATH)
        event = review["events"][-1]
        self.assertEqual(result["action"], "auto_approve")
        self.assertEqual(event["reviewer"]["actor_type"], "system")
        self.assertEqual(event["decision_basis"], "template_policy")
        self.assertEqual(event["policy_ref"], policy_ref)
        self.assertEqual(
            event["changes"][-1]["new_value"]["automation_context"]["policy_ref"],
            policy_ref,
        )
        event_hash_payload = copy.deepcopy(event)
        event_hash_payload.pop("event_sha256")
        self.assertEqual(
            event["event_sha256"],
            self.writer.digest_bytes(
                self.writer.canonical_bytes(event_hash_payload)
            ),
        )


if __name__ == "__main__":
    unittest.main()

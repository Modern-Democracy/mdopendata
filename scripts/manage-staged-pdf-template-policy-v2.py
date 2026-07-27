#!/usr/bin/env python3
"""Manage immutable Stage 1 structural templates and review policies."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data/budget/charlottetown/2026-2027/staged-pdf/v2"
BLOCK_PATH = WORKSPACE / "stage-1/block-inventory.json"
REVIEW_PATH = WORKSPACE / "review/review-decisions.json"
TEMPLATE_ROOT = WORKSPACE / "templates"
POLICY_ROOT = WORKSPACE / "policies"
VALIDATOR_PATH = ROOT / "scripts/validate-staged-pdf-artifacts.py"
PROPAGATION_PATH = ROOT / "scripts/preview-staged-pdf-structural-propagation.py"
SCHEMA_REF = "staged-pdf-artifacts-v2.schema.json"
GENERATOR = {
    "name": "staged-pdf-template-policy-manager",
    "version": "1",
    "config_sha256": hashlib.sha256(
        b"staged-pdf-template-policy-manager-v1\n"
    ).hexdigest(),
}
MATCHER = {
    "name": "document-structural-propagation",
    "version": "1",
    "config_sha256": hashlib.sha256(
        json.dumps(
            {
                "geometry_tolerance": 0.015,
                "scope": "current_document",
                "supported_block_types": ["formatted_text", "table"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest(),
}


def configure_workspace(workspace: Path) -> None:
    global WORKSPACE, BLOCK_PATH, REVIEW_PATH, TEMPLATE_ROOT, POLICY_ROOT
    WORKSPACE = workspace
    BLOCK_PATH = WORKSPACE / "stage-1/block-inventory.json"
    REVIEW_PATH = WORKSPACE / "review/review-decisions.json"
    TEMPLATE_ROOT = WORKSPACE / "templates"
    POLICY_ROOT = WORKSPACE / "policies"


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("template_policy_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_propagation_matcher() -> Any:
    spec = importlib.util.spec_from_file_location(
        "template_policy_propagation", PROPAGATION_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load propagation matcher: {PROPAGATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def artifact_ref(payload: dict[str, Any], sha256: str) -> dict[str, Any]:
    return {
        "artifact_type": payload["artifact_type"],
        "artifact_key": payload["artifact_key"],
        "schema_version": 2,
        "sha256": sha256,
    }


def source_locator(block: dict[str, Any]) -> dict[str, Any]:
    excerpt = block.get("evidence", [{}])[0].get("text_excerpt")
    return {
        "page_key": block["page_key"],
        "page_number": block["page_number"],
        "block_key": block["block_key"],
        "bbox": copy.deepcopy(block["bbox"]),
        "text_excerpt": excerpt,
    }


def pattern_fragment(pattern_sha256: str) -> str:
    if (
        not isinstance(pattern_sha256, str)
        or len(pattern_sha256) != 64
        or any(character not in "0123456789abcdef" for character in pattern_sha256)
    ):
        raise ValueError("pattern_sha256 must be a lowercase SHA-256")
    return pattern_sha256[:16]


def template_identity(document_key: str, pattern_sha256: str) -> tuple[str, str]:
    fragment = pattern_fragment(pattern_sha256)
    return (
        f"{document_key}:template:{fragment}",
        f"{document_key}:template:{fragment}:1.0.0",
    )


def policy_identity(template_key: str) -> str:
    return template_key.replace(":template:", ":policy:")


def next_patch_version(version: str) -> str:
    major, minor, patch = (int(value) for value in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def version_tuple(version: str) -> tuple[int, int, int]:
    return tuple(int(value) for value in version.split("."))  # type: ignore[return-value]


def reviewed_state(decision_id: str, reason: str) -> dict[str, Any]:
    return {
        "status": "approved",
        "reason_codes": [reason],
        "decision_ids": [decision_id],
    }


def rejected_controls(
    review: dict[str, Any], pattern_sha256: str
) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in review["events"]:
        if event["action"] != "reject":
            continue
        locators = {
            locator["block_key"]: locator
            for locator in event["source_locators"]
            if locator.get("block_key")
        }
        for change in event["changes"]:
            value = change.get("new_value")
            if (
                isinstance(value, dict)
                and value.get("pattern_sha256") == pattern_sha256
                and isinstance(value.get("target_block_key"), str)
            ):
                target_key = value["target_block_key"]
                if target_key in seen or target_key not in locators:
                    continue
                seen.add(target_key)
                controls.append({
                    "control_key": f"negative:{pattern_fragment(pattern_sha256)}:{len(controls) + 1:03d}",
                    "control_type": "negative",
                    "source_locator": copy.deepcopy(locators[target_key]),
                    "expected_result": "Document-scoped candidate remains ineligible.",
                })
    return controls


def template_from_block(
    block_artifact: dict[str, Any],
    review: dict[str, Any],
    block: dict[str, Any],
    pattern_sha256: str,
    decision_id: str,
) -> dict[str, Any]:
    template_key, artifact_key = template_identity(
        block_artifact["document_key"], pattern_sha256
    )
    anchor_key = f"anchor:{pattern_fragment(pattern_sha256)}"
    excerpt = block.get("evidence", [{}])[0].get("text_excerpt")
    column_bands = []
    internal_rules = []
    title_cells = []
    if block["block_type"] == "table":
        grid = block["table_grid"]
        width = block["bbox"]["x1"] - block["bbox"]["x0"]
        for index in range(len(grid["column_boundaries"]) - 1):
            x0 = (grid["column_boundaries"][index] - block["bbox"]["x0"]) / width
            x1 = (grid["column_boundaries"][index + 1] - block["bbox"]["x0"]) / width
            column_bands.append({
                "column_key": f"column:{index + 1:03d}",
                "role_candidate": f"column:{index + 1:03d}",
                "x0": round(x0, 6),
                "x1": round(x1, 6),
                "tolerance": 0.03,
                "required": True,
            })
        title_cells = [
            cell for cell in grid["cells"] if cell["cell_type"] == "table_title"
        ]
    else:
        counts: dict[str, int] = {}
        for region in block["regions"]:
            counts[region["region_type"]] = counts.get(region["region_type"], 0) + 1
        internal_rules = [
            {
                "rule_key": f"region:{region_type}",
                "parent_block_type": "formatted_text",
                "region_type": region_type,
                "minimum_count": count,
                "maximum_count": count,
                "reading_order": None,
                "required": True,
            }
            for region_type, count in sorted(counts.items())
        ]
    negatives = rejected_controls(review, pattern_sha256)
    return {
        "$schema": SCHEMA_REF,
        "schema_version": 2,
        "artifact_type": "structural_template",
        "artifact_key": artifact_key,
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [
            artifact_ref(block_artifact, digest_path(BLOCK_PATH))
        ],
        "template_key": template_key,
        "template_version": "1.0.0",
        "status": "approved",
        "reuse_scope": "exact_document",
        "source_family": "charlottetown-budget",
        "supported_text_sources": [block["text_source"]],
        "anchors": [{
            "anchor_key": anchor_key,
            "match_type": "normalized_text",
            "value": excerpt[:240] if excerpt else None,
            "region": copy.deepcopy(block["bbox"]),
            "geometry_tolerance": 0.03,
            "required": True,
        }],
        "block_rules": [{
            "rule_key": f"block:{block['block_type']}",
            "block_type": block["block_type"],
            "minimum_count": 1,
            "maximum_count": 1,
            "reading_order": 1,
            "required": True,
        }],
        "internal_region_rules": internal_rules,
        "column_bands": column_bands,
        "header_policy": {
            "mode": "repeated" if block["block_type"] == "table" else "absent",
            "source_anchor_keys": [anchor_key],
            "allow_optional_repetition": False,
        },
        "table_title_policy": {
            "mode": "required" if title_cells else "absent",
            "allowed_positions": (
                [
                    "top"
                    if title_cells[0]["row_index"] == 0
                    else "bottom"
                ]
                if title_cells
                else []
            ),
            "anchor_keys": [anchor_key] if title_cells else [],
        },
        "continuation_rules": [],
        "termination_rules": [{
            "rule_key": "current-document-boundary",
            "rule_type": "end_of_document_scope",
            "parameters": {"document_key": block_artifact["document_key"]},
            "required": True,
        }],
        "negative_controls": negatives,
        "regression_controls": [{
            "control_key": f"positive:{pattern_fragment(pattern_sha256)}:001",
            "control_type": "positive",
            "source_locator": source_locator(block),
            "expected_result": "Reviewed source block matches its immutable structure.",
        }],
        "approval": reviewed_state(decision_id, "reviewer-template-promotion"),
    }


def promotion_evidence(
    review: dict[str, Any], template: dict[str, Any]
) -> dict[str, Any]:
    source_key = template["regression_controls"][0]["source_locator"]["block_key"]
    accepted_events = [
        event
        for event in review["events"]
        if event["action"] in {"apply_template", "auto_approve"}
        and any(locator.get("block_key") == source_key for locator in event["source_locators"])
    ]
    rejected_events = [
        event
        for event in review["events"]
        if event["action"] == "reject"
        and any(locator.get("block_key") == source_key for locator in event["source_locators"])
    ]
    accepted = len(accepted_events)
    rejected = len(rejected_events)
    reviewed = accepted + rejected
    return {
        "positive_application_keys": [
            event["decision_id"] for event in accepted_events
        ],
        "negative_control_keys": [
            control["control_key"] for control in template["negative_controls"]
        ],
        "validation_run_keys": [
            f"validation:{template['template_key']}:{template['template_version']}"
        ],
        "reviewed_application_count": reviewed,
        "accepted_application_count": accepted,
        "rejected_application_count": rejected,
        "false_approval_count": 0,
        "observed_precision": accepted / reviewed if reviewed else None,
    }


def policy_from_template(
    template: dict[str, Any],
    template_sha256: str,
    review: dict[str, Any],
    mode: str,
    decision_id: str,
    *,
    previous: dict[str, Any] | None = None,
    previous_sha256: str | None = None,
    reason_code: str = "reviewer-policy-approval",
) -> dict[str, Any]:
    if mode not in {"review_required", "sample_review", "auto_approve"}:
        raise ValueError(f"Unsupported policy mode: {mode}")
    policy_key = policy_identity(template["template_key"])
    version = next_patch_version(previous["policy_version"]) if previous else "1.0.0"
    promoted = mode != "review_required"
    evidence = promotion_evidence(review, template)
    policy = {
        "$schema": SCHEMA_REF,
        "schema_version": 2,
        "artifact_type": "template_review_policy",
        "artifact_key": f"{policy_key}:{version}",
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [artifact_ref(template, template_sha256)],
        "policy_key": policy_key,
        "policy_version": version,
        "status": "approved",
        "template_binding": {
            "template_key": template["template_key"],
            "template_version": template["template_version"],
            "artifact_ref": artifact_ref(template, template_sha256),
        },
        "supersedes_policy_ref": (
            artifact_ref(previous, previous_sha256)
            if previous is not None and previous_sha256 is not None
            else None
        ),
        "scope": {
            "reuse_scope": "exact_document",
            "jurisdiction_key": "charlottetown",
            "source_family": template["source_family"],
            "document_family": "annual-budget",
        },
        "matcher": copy.deepcopy(MATCHER),
        "mode": mode,
        "eligible_fit_classes": ["exact", "light_variation"],
        "allowed_light_mismatch_categories": ["geometry"],
        "sample_rate": (
            1 if mode == "review_required" else 0.5 if mode == "sample_review" else 0
        ),
        "promotion_gates": {
            "minimum_positive_examples": 1 if promoted else 0,
            "minimum_negative_controls": 1 if promoted else 0,
            "minimum_reviewed_applications": 2 if promoted else 0,
            "minimum_observed_precision": 0.8 if promoted else 0,
            "maximum_false_approvals": 0,
        },
        "promotion_evidence": evidence,
        "suspension_rules": {
            "material_mismatch": True,
            "negative_control_failure": True,
            "sample_rejection": True,
            "matcher_change": True,
            "source_profile_change": True,
        },
        "approval": reviewed_state(decision_id, reason_code),
    }
    errors = load_validator().validate_payload(policy)
    if errors:
        raise ValueError("Policy does not satisfy promotion gates: " + "; ".join(errors[:8]))
    return policy


def registry_files(root: Path, filename: str) -> list[Path]:
    return sorted(root.glob(f"*/**/{filename}")) if root.exists() else []


def registry_snapshot() -> dict[str, Any]:
    templates = []
    for path in registry_files(TEMPLATE_ROOT, "structural-template.json"):
        payload = read_json(path)
        templates.append({
            "artifact": payload,
            "sha256": digest_path(path),
            "repo_relpath": path.relative_to(ROOT).as_posix(),
        })
    policies = []
    for path in registry_files(POLICY_ROOT, "template-review-policy.json"):
        payload = read_json(path)
        policies.append({
            "artifact": payload,
            "sha256": digest_path(path),
            "repo_relpath": path.relative_to(ROOT).as_posix(),
        })
    templates.sort(key=lambda item: (
        item["artifact"]["template_key"],
        version_tuple(item["artifact"]["template_version"]),
    ))
    policies.sort(key=lambda item: (
        item["artifact"]["policy_key"],
        version_tuple(item["artifact"]["policy_version"]),
    ))
    return {"templates": templates, "policies": policies}


def registry_for_pattern(
    document_key: str, pattern_sha256: str
) -> dict[str, Any]:
    template_key, _ = template_identity(document_key, pattern_sha256)
    snapshot = registry_snapshot()
    templates = [
        item for item in snapshot["templates"]
        if item["artifact"]["template_key"] == template_key
    ]
    template = templates[-1] if templates else None
    policies = (
        [
            item for item in snapshot["policies"]
            if template
            and item["artifact"]["template_binding"]["template_key"] == template_key
        ]
        if template
        else []
    )
    return {"template": template, "policy": policies[-1] if policies else None}


def deterministic_sample(policy_sha256: str, target_key: str, rate: float) -> bool:
    value = int(hashlib.sha256(f"{policy_sha256}:{target_key}".encode()).hexdigest(), 16)
    return value / (2**256 - 1) < rate


def evaluate_candidate(
    candidate: dict[str, Any],
    template_entry: dict[str, Any] | None,
    policy_entry: dict[str, Any] | None,
    *,
    runtime_suspended: bool = False,
) -> dict[str, Any]:
    if template_entry is None or policy_entry is None:
        return {
            "policy_ref": None,
            "outcome": "review_required",
            "selected_for_sample": False,
            "fit_eligible": candidate["fit_class"] in {"exact", "light_variation"},
            "matcher_config_sha256": MATCHER["config_sha256"],
            "reason_codes": ["no-approved-policy"],
        }
    policy = policy_entry["artifact"]
    categories = {item["category"] for item in candidate["mismatch_evidence"]}
    fit_eligible = (
        candidate["fit_class"] in policy["eligible_fit_classes"]
        and (
            candidate["fit_class"] != "light_variation"
            or categories.issubset(set(policy["allowed_light_mismatch_categories"]))
        )
    )
    policy_ref = artifact_ref(policy, policy_entry["sha256"])
    if candidate["fit_class"] in {"material_variation", "one_off"} or not fit_eligible:
        outcome = "blocked"
        sampled = False
        reasons = ["policy-fit-ineligible"]
    elif runtime_suspended or "policy-suspended" in policy["approval"]["reason_codes"]:
        outcome = "blocked"
        sampled = False
        reasons = ["policy-suspended"]
    elif policy["mode"] == "review_required":
        outcome = "review_required"
        sampled = False
        reasons = ["policy-review-required"]
    elif policy["mode"] == "sample_review":
        sampled = deterministic_sample(
            policy_entry["sha256"], candidate["target_block_key"], policy["sample_rate"]
        )
        outcome = "selected_for_sample" if sampled else "auto_approved"
        reasons = ["deterministic-sample" if sampled else "deterministic-sample-bypass"]
    else:
        outcome = "auto_approved"
        sampled = False
        reasons = ["policy-auto-approve"]
    return {
        "policy_ref": policy_ref,
        "outcome": outcome,
        "selected_for_sample": sampled,
        "fit_eligible": fit_eligible,
        "matcher_config_sha256": policy["matcher"]["config_sha256"],
        "reason_codes": reasons,
    }


def evaluate_preview(
    preview: dict[str, Any],
    document_key: str,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry_for_pattern(document_key, preview["pattern_sha256"])
    policy = registry["policy"]["artifact"] if registry["policy"] else None
    material_drift = any(
        candidate["fit_class"] == "material_variation"
        and "source_authority" not in {
            item["category"] for item in candidate["mismatch_evidence"]
        }
        for candidate in preview["candidates"]
    )
    suspension_reasons = []
    if policy and policy["mode"] != "review_required":
        if (
            policy["suspension_rules"]["material_mismatch"]
            and material_drift
        ):
            suspension_reasons.append("material-mismatch")
        if (
            policy["suspension_rules"]["matcher_change"]
            and policy["matcher"]["config_sha256"]
            != preview["matcher"]["config_sha256"]
        ):
            suspension_reasons.append("matcher-change")
        negative_keys = {
            control["source_locator"]["block_key"]
            for control in registry["template"]["artifact"]["negative_controls"]
        }
        if (
            policy["suspension_rules"]["negative_control_failure"]
            and any(
                candidate["target_block_key"] in negative_keys
                and candidate["fit_class"] != "one_off"
                for candidate in preview["candidates"]
            )
        ):
            suspension_reasons.append("negative-control-failure")
        approval_id = policy["approval"]["decision_ids"][-1]
        approval_sequence = next(
            (
                event["sequence"]
                for event in (review or {}).get("events", [])
                if event["decision_id"] == approval_id
            ),
            0,
        )
        if (
            policy["suspension_rules"]["sample_rejection"]
            and any(
                event["sequence"] > approval_sequence
                and event["action"] == "reject"
                and any(
                    isinstance(change.get("new_value"), dict)
                    and change["new_value"].get("pattern_sha256")
                    == preview["pattern_sha256"]
                    for change in event["changes"]
                )
                for event in (review or {}).get("events", [])
            )
        ):
            suspension_reasons.append("sample-rejection")
    runtime_suspended = bool(suspension_reasons)
    for candidate in preview["candidates"]:
        candidate["policy_evaluation"] = evaluate_candidate(
            candidate,
            registry["template"],
            registry["policy"],
            runtime_suspended=runtime_suspended,
        )
        candidate["automation_context"] = {
            "source_block_key": preview["source_block_key"],
            "pattern_sha256": preview["pattern_sha256"],
            "template_ref": (
                artifact_ref(
                    registry["template"]["artifact"],
                    registry["template"]["sha256"],
                )
                if registry["template"]
                else None
            ),
            "policy_ref": candidate["policy_evaluation"]["policy_ref"],
            "matcher": copy.deepcopy(preview["matcher"]),
            "fit_class": candidate["fit_class"],
            "matching_evidence": copy.deepcopy(candidate["matching_evidence"]),
            "mismatch_evidence": copy.deepcopy(candidate["mismatch_evidence"]),
        }
    preview["registry"] = {
        "template": registry["template"],
        "policy": registry["policy"],
        "runtime_suspended": runtime_suspended,
        "suspension_reason_codes": suspension_reasons,
    }
    return preview


def append_event(
    review: dict[str, Any],
    *,
    action: str,
    reason: str,
    affected_keys: list[str],
    locators: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    prior_sha256: str,
    result_payload: dict[str, Any],
    result_sha256: str,
    decision_id: str,
    policy_ref: dict[str, Any] | None = None,
) -> None:
    sequence = len(review["events"]) + 1
    event = {
        "decision_id": decision_id,
        "sequence": sequence,
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reviewer": {
            "reviewer_id": "local-reviewer",
            "display_name": "Local reviewer",
            "role": "data-reviewer",
            "actor_type": "human",
        },
        "decision_basis": "reviewer",
        "policy_ref": policy_ref,
        "action": action,
        "reason": reason,
        "prior_artifact_sha256": prior_sha256,
        "result_artifact_sha256": result_sha256,
        "previous_event_sha256": (
            review["events"][-1]["event_sha256"] if review["events"] else None
        ),
        "event_sha256": "0" * 64,
        "affected_keys": list(dict.fromkeys(affected_keys)),
        "source_locators": locators,
        "changes": changes,
    }
    hash_payload = copy.deepcopy(event)
    hash_payload.pop("event_sha256")
    event["event_sha256"] = digest_bytes(canonical_bytes(hash_payload))
    review["target_artifacts"] = [artifact_ref(result_payload, result_sha256)]
    review["events"].append(event)


def atomic_new_artifact(path: Path, payload: bytes, review: bytes) -> None:
    if path.exists():
        if path.read_bytes() == payload:
            raise RuntimeError("immutable artifact already exists")
        raise RuntimeError(f"immutable artifact conflict: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    old_review = REVIEW_PATH.read_bytes()
    artifact_fd, artifact_name = tempfile.mkstemp(prefix=".artifact-", suffix=".json", dir=path.parent)
    review_fd, review_name = tempfile.mkstemp(prefix=".review-", suffix=".json", dir=REVIEW_PATH.parent)
    os.close(artifact_fd)
    os.close(review_fd)
    artifact_tmp = Path(artifact_name)
    review_tmp = Path(review_name)
    try:
        artifact_tmp.write_bytes(payload)
        review_tmp.write_bytes(review)
        os.replace(artifact_tmp, path)
        try:
            os.replace(review_tmp, REVIEW_PATH)
        except Exception:
            path.unlink(missing_ok=True)
            REVIEW_PATH.write_bytes(old_review)
            raise
    finally:
        artifact_tmp.unlink(missing_ok=True)
        review_tmp.unlink(missing_ok=True)


def manage(command: dict[str, Any]) -> dict[str, Any]:
    action = command.get("action")
    if action not in {
        "promote_template", "promote_policy", "demote_policy", "suspend_policy"
    }:
        raise ValueError(f"Unsupported template-policy action: {action}")
    block_artifact = read_json(BLOCK_PATH)
    review = read_json(REVIEW_PATH)
    block_hash = digest_path(BLOCK_PATH)
    review_hash = digest_path(REVIEW_PATH)
    if command.get("document_key") != block_artifact["document_key"]:
        raise ValueError("document_key does not match the block artifact")
    if command.get("expected_artifact_sha256") != block_hash:
        raise RuntimeError("stale artifact hash")
    if command.get("expected_review_artifact_sha256") != review_hash:
        raise RuntimeError("stale review head")
    reason = str(command.get("reason", "")).strip()
    if not reason:
        raise ValueError("reason is required")
    pattern_sha256 = command.get("pattern_sha256")
    source_key = command.get("source_block_key")
    block = next(
        (
            item
            for item in block_artifact["records"]
            if item["block_key"] == source_key
        ),
        None,
    )
    if block is None or block["review"]["status"] != "approved":
        raise ValueError("Template policy actions require an approved source block")
    actual_pattern_sha256 = load_propagation_matcher().pattern_sha256(block)
    if pattern_sha256 != actual_pattern_sha256:
        raise RuntimeError("stale propagation pattern")
    registry = registry_for_pattern(block_artifact["document_key"], pattern_sha256)
    if (
        registry["template"] is not None
        and registry["template"]["artifact"]["regression_controls"][0][
            "source_locator"
        ]["block_key"] != source_key
    ):
        raise ValueError("source block does not match the registered template")
    sequence = len(review["events"]) + 1
    decision_id = f'{block_artifact["document_key"]}:decision:{sequence:06d}'

    if action == "promote_template":
        if registry["template"] is not None:
            raise RuntimeError("immutable template already exists")
        artifact = template_from_block(
            block_artifact, review, block, pattern_sha256, decision_id
        )
        validator = load_validator()
        errors = validator.validate_payload(artifact)
        if errors:
            raise RuntimeError("Template failed validation: " + "; ".join(errors[:8]))
        artifact_bytes = canonical_bytes(artifact)
        artifact_hash = digest_bytes(artifact_bytes)
        review_next = copy.deepcopy(review)
        append_event(
            review_next,
            action="create",
            reason=reason,
            affected_keys=[artifact["template_key"], source_key],
            locators=[source_locator(block)],
            changes=[{
                "field_path": f"/template_registry/{artifact['artifact_key']}",
                "prior_value": None,
                "new_value": artifact_ref(artifact, artifact_hash),
            }],
            prior_sha256=block_hash,
            result_payload=artifact,
            result_sha256=artifact_hash,
            decision_id=decision_id,
        )
        errors = validator.validate_payload(review_next)
        if errors:
            raise RuntimeError("Review history failed validation: " + "; ".join(errors[:8]))
        path = TEMPLATE_ROOT / pattern_fragment(pattern_sha256) / "1.0.0" / "structural-template.json"
    else:
        if registry["template"] is None:
            raise ValueError("Policy action requires an immutable template")
        template_entry = registry["template"]
        previous_entry = registry["policy"]
        if action == "promote_policy":
            mode = command.get("mode")
            reason_code = "reviewer-policy-approval"
        elif action == "demote_policy":
            if previous_entry is None:
                raise ValueError("Policy demotion requires an active policy")
            mode = "review_required"
            reason_code = "policy-demoted"
        else:
            if previous_entry is None:
                raise ValueError("Policy suspension requires an active policy")
            mode = "review_required"
            reason_code = "policy-suspended"
        artifact = policy_from_template(
            template_entry["artifact"],
            template_entry["sha256"],
            review,
            mode,
            decision_id,
            previous=previous_entry["artifact"] if previous_entry else None,
            previous_sha256=previous_entry["sha256"] if previous_entry else None,
            reason_code=reason_code,
        )
        artifact_bytes = canonical_bytes(artifact)
        artifact_hash = digest_bytes(artifact_bytes)
        review_next = copy.deepcopy(review)
        review_action = (
            "promote_policy"
            if action == "promote_policy"
            else "demote_policy"
            if action == "demote_policy"
            else "suspend_policy"
        )
        append_event(
            review_next,
            action=review_action,
            reason=reason,
            affected_keys=[artifact["policy_key"], artifact["template_binding"]["template_key"]],
            locators=[
                copy.deepcopy(
                    template_entry["artifact"]["regression_controls"][0]["source_locator"]
                )
            ],
            changes=[{
                "field_path": f"/policy_registry/{artifact['artifact_key']}",
                "prior_value": (
                    artifact_ref(previous_entry["artifact"], previous_entry["sha256"])
                    if previous_entry
                    else None
                ),
                "new_value": artifact_ref(artifact, artifact_hash),
            }],
            prior_sha256=previous_entry["sha256"] if previous_entry else template_entry["sha256"],
            result_payload=artifact,
            result_sha256=artifact_hash,
            decision_id=decision_id,
            policy_ref=artifact_ref(artifact, artifact_hash),
        )
        validator = load_validator()
        errors = validator.validate_payload(review_next)
        if errors:
            raise RuntimeError("Review history failed validation: " + "; ".join(errors[:8]))
        path = POLICY_ROOT / pattern_fragment(pattern_sha256) / artifact["policy_version"] / "template-review-policy.json"

    atomic_new_artifact(path, artifact_bytes, canonical_bytes(review_next))
    return {
        "status": "created",
        "action": action,
        "artifact": artifact,
        "artifact_sha256": artifact_hash,
        "review_artifact_sha256": digest_path(REVIEW_PATH),
        "decision_id": decision_id,
        "registry": registry_for_pattern(block_artifact["document_key"], pattern_sha256),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", type=Path)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    try:
        if args.list:
            result = registry_snapshot()
        elif args.command:
            result = manage(read_json(args.command))
        else:
            raise ValueError("--command or --list is required")
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
        return 0
    except RuntimeError as error:
        kind = "conflict" if any(
            marker in str(error)
            for marker in ("stale", "immutable")
        ) else "validation"
        print(json.dumps({"error": str(error), "kind": kind}))
        return 2
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), "kind": "invalid"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Preview deterministic municipal-source reuse across agenda packages."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA_PATH = (
    ROOT / "schema/json-schema/agenda-package-reuse-profile.schema.json"
)
PREVIEW_SCHEMA_PATH = (
    ROOT / "schema/json-schema/agenda-package-reuse-preview.schema.json"
)
MATCHER_CONFIG = {
    "anchor_normalization": "nfkc-casefold-whitespace-v1",
    "boundary_strategy": "ordered-start-anchor-segmentation-v1",
    "conflict_strategy": "equal-priority-block",
    "coverage": "exactly-once-or-explicitly-unresolved",
}
MATCHER = {
    "name": "agenda-package-reuse",
    "version": "1",
    "config_sha256": hashlib.sha256(
        json.dumps(
            MATCHER_CONFIG, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest(),
}


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(schema_path: Path, payload: dict[str, Any]) -> list[str]:
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(
            validator.iter_errors(payload),
            key=lambda item: list(item.absolute_path),
        )
    ]


def normalized_text(value: str) -> str:
    import unicodedata

    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def anchor_match(anchor: dict[str, Any], text: str) -> dict[str, Any]:
    if anchor["match_type"] == "normalized_text":
        matched = normalized_text(anchor["value"]) in normalized_text(text)
    else:
        try:
            matched = re.search(anchor["value"], text, re.IGNORECASE | re.MULTILINE) is not None
        except re.error as error:
            raise ValueError(
                f"Invalid regex for anchor {anchor['anchor_key']}: {error}"
            ) from error
    return {
        "anchor_key": anchor["anchor_key"],
        "match_type": anchor["match_type"],
        "required": anchor["required"],
        "matched": matched,
    }


def evaluate_anchors(
    anchors: list[dict[str, Any]], text: str
) -> tuple[bool, list[dict[str, Any]], bool]:
    evidence = [anchor_match(anchor, text) for anchor in anchors]
    eligible = all(
        item["matched"] for item in evidence if item["required"]
    )
    optional_missed = any(
        not item["matched"] for item in evidence if not item["required"]
    )
    return eligible, evidence, optional_missed


def validate_package(package: dict[str, Any]) -> None:
    required = {
        "package_key",
        "source_sha256",
        "jurisdiction_key",
        "source_family",
        "document_family",
        "pages",
    }
    if set(package) != required:
        raise ValueError("Package input contains unsupported or missing fields")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._:-]*", package["package_key"]):
        raise ValueError("package_key is invalid")
    if not re.fullmatch(r"[a-f0-9]{64}", package["source_sha256"]):
        raise ValueError("source_sha256 must be a lowercase SHA-256")
    pages = package["pages"]
    if not isinstance(pages, list) or not pages:
        raise ValueError("Package pages must be a non-empty list")
    if [page.get("page_number") for page in pages] != list(
        range(1, len(pages) + 1)
    ):
        raise ValueError("Package pages must be consecutive and source ordered")
    for page in pages:
        if set(page) != {"page_number", "text_source", "text"}:
            raise ValueError("Package page contains unsupported or missing fields")
        if page["text_source"] not in {
            "embedded",
            "ocr",
            "visual_only",
            "mixed",
        }:
            raise ValueError("Package page text_source is invalid")
        if not isinstance(page["text"], str):
            raise ValueError("Package page text must be a string")


def validate_profile_semantics(profile: dict[str, Any]) -> None:
    if profile["status"] != "approved":
        raise ValueError("Agenda package reuse requires an approved profile")
    template_keys = [
        template["document_template_key"]
        for template in profile["document_templates"]
    ]
    if len(template_keys) != len(set(template_keys)):
        raise ValueError("Document template keys must be unique")
    families = {
        template["document_family"]
        for template in profile["document_templates"]
    }
    grammar = profile["package_grammar"]
    if grammar["first_document_family"] not in families:
        raise ValueError("Package grammar first family has no document template")
    for transition in grammar["allowed_transitions"]:
        if transition["from"] not in families or transition["to"] not in families:
            raise ValueError("Package grammar transition references an unknown family")
    for template in profile["document_templates"]:
        if template["minimum_pages"] > template["maximum_pages"]:
            raise ValueError(
                f"{template['document_template_key']} has inverted page limits"
            )
        if (
            template["template_ref"]["artifact_type"]
            != "structural_template"
            or template["policy_ref"]["artifact_type"]
            != "template_review_policy"
        ):
            raise ValueError("Template and policy references have incorrect types")
        anchor_keys = [
            anchor["anchor_key"]
            for group in ("start_anchors", "continuation_anchors", "end_anchors")
            for anchor in template[group]
        ]
        if len(anchor_keys) != len(set(anchor_keys)):
            raise ValueError(
                f"{template['document_template_key']} anchor keys must be unique"
            )


def start_candidates(
    profile: dict[str, Any], pages: list[dict[str, Any]]
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    starts: dict[int, dict[str, Any]] = {}
    conflicts = []
    for page in pages:
        candidates = []
        for template in profile["document_templates"]:
            eligible, evidence, optional_missed = evaluate_anchors(
                template["start_anchors"], page["text"]
            )
            if eligible:
                candidates.append({
                    "template": template,
                    "evidence": evidence,
                    "optional_missed": optional_missed,
                })
        if not candidates:
            continue
        candidates.sort(
            key=lambda item: (
                -item["template"]["priority"],
                item["template"]["document_template_key"],
            )
        )
        highest = candidates[0]["template"]["priority"]
        tied = [
            candidate
            for candidate in candidates
            if candidate["template"]["priority"] == highest
        ]
        if len(tied) > 1:
            conflicts.append({
                "page_number": page["page_number"],
                "reason": "ambiguous-start-anchor",
                "candidate_template_keys": sorted(
                    candidate["template"]["document_template_key"]
                    for candidate in tied
                ),
            })
        else:
            starts[page["page_number"]] = candidates[0]
    return starts, conflicts


def deterministic_sample(
    policy_sha256: str, application_key: str, rate: float
) -> bool:
    value = int(
        hashlib.sha256(
            f"{policy_sha256}:{application_key}".encode("utf-8")
        ).hexdigest(),
        16,
    )
    return value / (2**256 - 1) < rate


def policy_evaluation(
    template: dict[str, Any], application_key: str, fit_class: str
) -> dict[str, Any]:
    policy_ref = copy.deepcopy(template["policy_ref"])
    if fit_class == "material_variation":
        return {
            "policy_ref": policy_ref,
            "outcome": "blocked",
            "selected_for_sample": False,
            "reason_codes": ["material-package-variation"],
        }
    mode = template["policy_mode"]
    if mode == "review_required":
        outcome = "review_required"
        sampled = False
        reasons = ["policy-review-required"]
    elif mode == "sample_review":
        sampled = deterministic_sample(
            policy_ref["sha256"], application_key, template["sample_rate"]
        )
        outcome = "selected_for_sample" if sampled else "auto_approved"
        reasons = [
            "deterministic-sample"
            if sampled
            else "deterministic-sample-bypass"
        ]
    else:
        outcome = "auto_approved"
        sampled = False
        reasons = ["policy-auto-approve"]
    return {
        "policy_ref": policy_ref,
        "outcome": outcome,
        "selected_for_sample": sampled,
        "reason_codes": reasons,
    }


def page_role(index: int, count: int) -> str:
    if count == 1:
        return "single_page"
    if index == 0:
        return "document_start"
    if index == count - 1:
        return "document_end"
    return "document_continuation"


def build_document(
    package: dict[str, Any],
    source_order: int,
    start: int,
    end: int,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    template = candidate["template"]
    pages = package["pages"][start - 1:end]
    unresolved = []
    boundary = [{
        "boundary": "start",
        "page_number": start,
        "anchor_matches": copy.deepcopy(candidate["evidence"]),
    }]
    optional_missed = candidate["optional_missed"]
    count = len(pages)
    if not template["minimum_pages"] <= count <= template["maximum_pages"]:
        unresolved.append({
            "reason": "page-count-outside-template-range",
            "observed": count,
            "minimum": template["minimum_pages"],
            "maximum": template["maximum_pages"],
        })
    sequence = []
    for index, page in enumerate(pages):
        role = page_role(index, count)
        anchor_matches = []
        if role in {"document_continuation", "document_end"}:
            eligible, anchor_matches, missed = evaluate_anchors(
                template["continuation_anchors"], page["text"]
            )
            optional_missed = optional_missed or missed
            if not eligible:
                if not (
                    template["allow_visual_only_continuation"]
                    and page["text_source"] == "visual_only"
                ):
                    unresolved.append({
                        "reason": "continuation-anchor-mismatch",
                        "page_number": page["page_number"],
                        "anchor_matches": copy.deepcopy(anchor_matches),
                    })
        sequence.append({
            "page_number": page["page_number"],
            "page_role": role,
            "page_template_key": (
                f"{template['document_template_key']}:{role}"
            ),
            "anchor_matches": anchor_matches,
        })
    if template["end_anchors"]:
        eligible, evidence, missed = evaluate_anchors(
            template["end_anchors"], pages[-1]["text"]
        )
        optional_missed = optional_missed or missed
        boundary.append({
            "boundary": "end",
            "page_number": end,
            "anchor_matches": copy.deepcopy(evidence),
        })
        if not eligible:
            unresolved.append({
                "reason": "end-anchor-mismatch",
                "page_number": end,
                "anchor_matches": copy.deepcopy(evidence),
            })
    else:
        boundary.append({
            "boundary": "end",
            "page_number": end,
            "anchor_matches": [],
            "basis": "next-document-start-or-package-end",
        })
    fit_class = (
        "material_variation"
        if unresolved
        else "light_variation"
        if optional_missed
        else "exact"
    )
    matched = sum(
        1
        for item in candidate["evidence"]
        if item["matched"]
    )
    total = max(len(candidate["evidence"]), 1)
    confidence = 0 if unresolved else round(matched / total, 6)
    document_key = (
        f"{package['package_key']}:document:{source_order:04d}"
    )
    return {
        "document_key": document_key,
        "source_order": source_order,
        "document_family": template["document_family"],
        "page_start": start,
        "page_end": end,
        "page_count": count,
        "fit_class": fit_class,
        "confidence": confidence,
        "template_ref": copy.deepcopy(template["template_ref"]),
        "boundary_evidence": boundary,
        "unresolved_evidence": unresolved,
        "page_sequence": sequence,
        "policy_evaluation": policy_evaluation(
            template, document_key, fit_class
        ),
    }


def preview(profile: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    errors = validate(PROFILE_SCHEMA_PATH, profile)
    if errors:
        raise ValueError("Profile schema validation failed: " + "; ".join(errors[:8]))
    validate_profile_semantics(profile)
    validate_package(package)
    scope = profile["scope"]
    for field in ("jurisdiction_key", "source_family", "document_family"):
        if package[field] != scope[field]:
            raise ValueError(f"Package {field} is outside the approved profile scope")

    starts, conflicts = start_candidates(profile, package["pages"])
    conflict_pages = {item["page_number"] for item in conflicts}
    boundaries = sorted(set(starts) | conflict_pages)
    documents = []
    assigned: set[int] = set()
    for start in sorted(starts):
        next_boundaries = [boundary for boundary in boundaries if boundary > start]
        end = (next_boundaries[0] - 1) if next_boundaries else len(package["pages"])
        if end < start:
            continue
        document = build_document(
            package, len(documents) + 1, start, end, starts[start]
        )
        documents.append(document)
        assigned.update(range(start, end + 1))

    grammar = profile["package_grammar"]
    allowed = {
        (transition["from"], transition["to"])
        for transition in grammar["allowed_transitions"]
    }
    if documents and documents[0]["document_family"] != grammar["first_document_family"]:
        documents[0]["unresolved_evidence"].append({
            "reason": "unexpected-first-document-family",
            "expected": grammar["first_document_family"],
            "observed": documents[0]["document_family"],
        })
    for prior, current in zip(documents, documents[1:]):
        if (prior["document_family"], current["document_family"]) not in allowed:
            current["unresolved_evidence"].append({
                "reason": "disallowed-document-transition",
                "from": prior["document_family"],
                "to": current["document_family"],
            })
    for document in documents:
        if document["unresolved_evidence"]:
            document["fit_class"] = "material_variation"
            document["confidence"] = 0
            template = next(
                item
                for item in profile["document_templates"]
                if item["template_ref"] == document["template_ref"]
            )
            document["policy_evaluation"] = policy_evaluation(
                template, document["document_key"], "material_variation"
            )

    unknown_pages = sorted(
        set(range(1, len(package["pages"]) + 1))
        - assigned
        - conflict_pages
    )
    overlap_pages = []
    coverage_counts = {
        page_number: sum(
            document["page_start"] <= page_number <= document["page_end"]
            for document in documents
        )
        for page_number in range(1, len(package["pages"]) + 1)
    }
    overlap_pages = sorted(
        page_number
        for page_number, count in coverage_counts.items()
        if count > 1
    )
    if overlap_pages:
        conflicts.extend({
            "page_number": page_number,
            "reason": "overlapping-document-assignment",
            "candidate_template_keys": sorted({
                document["template_ref"]["artifact_key"]
                for document in documents
                if document["page_start"] <= page_number <= document["page_end"]
            }),
        } for page_number in overlap_pages)
    assigned_pages = {
        page_number
        for page_number, count in coverage_counts.items()
        if count == 1
    }
    omitted = (
        set(range(1, len(package["pages"]) + 1))
        - assigned_pages
        - set(unknown_pages)
        - {item["page_number"] for item in conflicts}
    )
    blocked = bool(
        unknown_pages
        or conflicts
        or omitted
        or any(
            document["fit_class"] == "material_variation"
            for document in documents
        )
    )
    needs_review = any(
        document["policy_evaluation"]["outcome"]
        in {"review_required", "selected_for_sample"}
        for document in documents
    )
    result = {
        "$schema": "agenda-package-reuse-preview.schema.json",
        "schema_version": 1,
        "package_key": package["package_key"],
        "source_sha256": package["source_sha256"],
        "profile_ref": {
            "profile_key": profile["profile_key"],
            "profile_version": profile["profile_version"],
            "sha256": digest_bytes(canonical_bytes(profile)),
        },
        "matcher": copy.deepcopy(MATCHER),
        "status": (
            "blocked" if blocked else "needs_review" if needs_review else "matched"
        ),
        "documents": documents,
        "unknown_pages": unknown_pages,
        "conflicts": sorted(
            conflicts, key=lambda item: (item["page_number"], item["reason"])
        ),
        "coverage": {
            "total_pages": len(package["pages"]),
            "assigned_pages": len(assigned_pages),
            "unknown_pages": len(unknown_pages),
            "conflicting_pages": len({
                item["page_number"] for item in conflicts
            }),
            "omitted_pages": len(omitted),
        },
    }
    errors = validate(PREVIEW_SCHEMA_PATH, result)
    if errors:
        raise RuntimeError(
            "Reuse preview schema validation failed: " + "; ".join(errors[:8])
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = preview(read_json(args.profile), read_json(args.package))
        print(
            json.dumps(
                result,
                indent=2 if args.pretty else None,
                sort_keys=args.pretty,
                ensure_ascii=False,
                separators=None if args.pretty else (",", ":"),
            )
        )
        return 0
    except RuntimeError as error:
        print(json.dumps({"error": str(error), "kind": "validation"}))
        return 2
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), "kind": "invalid"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

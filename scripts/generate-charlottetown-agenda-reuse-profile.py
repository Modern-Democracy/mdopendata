#!/usr/bin/env python3
"""Promote the reviewed Charlottetown public-meeting package into Phase 6 artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    ROOT
    / "data/document-ingestion/profiles/"
    "charlottetown-council-public-meeting/v1"
)
POSITIVE_DOCUMENT_ID = 2
NEGATIVE_DOCUMENT_ID = 3
POSITIVE_SOURCE_SHA256 = (
    "73d48c77694d443e5351089c19864ce58958c17cb3c96c3d412f1182d08f2636"
)
NEGATIVE_SOURCE_SHA256 = (
    "d529b04147218eaf379ab063515ab965da7532188539746795fc5d253388a994"
)
SOURCE_FAMILY = "charlottetown-council"
PROFILE_DECISION_ID = (
    "decision:phase-6:charlottetown-public-meeting-profile:2026-07-27"
)
SCHEMA_REF = "staged-pdf-artifacts-v2.schema.json"
GENERATOR_CONFIG = {
    "positive_source_document_id": POSITIVE_DOCUMENT_ID,
    "negative_source_document_id": NEGATIVE_DOCUMENT_ID,
    "negative_page_limit": 6,
    "policy_mode": "review_required",
    "source_family": SOURCE_FAMILY,
}
GENERATOR = {
    "name": "agenda-package-profile-promotion",
    "version": "1",
    "config_sha256": hashlib.sha256(
        json.dumps(
            GENERATOR_CONFIG, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest(),
}
MATCHER = {
    "name": "agenda-package-reuse",
    "version": "1",
    "config_sha256": hashlib.sha256(
        json.dumps(
            {
                "anchor_normalization": "nfkc-casefold-whitespace-v1",
                "boundary_strategy": "ordered-start-anchor-segmentation-v1",
                "conflict_strategy": "equal-priority-block",
                "coverage": "exactly-once-or-explicitly-unresolved",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest(),
}


DOCUMENT_SPECS = [
    {
        "document_key": "test-agenda",
        "family": "public-meeting-agenda",
        "page_start": 1,
        "page_end": 1,
        "priority": 100,
        "start": [
            (
                "public-meeting-heading",
                "regex",
                r"CITY OF CHARLOTTETOWN\s+PUBLIC MEETING OF COUNCIL",
            ),
        ],
        "continuation": [],
        "end": [],
    },
    {
        "document_key": "information-sheet",
        "family": "public-meeting-information-sheet",
        "page_start": 2,
        "page_end": 2,
        "priority": 90,
        "start": [
            (
                "information-sheet-heading",
                "normalized_text",
                "Information Sheet for Public Meeting of Council",
            ),
        ],
        "continuation": [],
        "end": [],
    },
    {
        "document_key": "facebook-notice",
        "family": "public-meeting-facebook-notice",
        "page_start": 3,
        "page_end": 3,
        "priority": 80,
        "start": [
            (
                "facebook-notice-heading",
                "regex",
                r"Facebook notification posted [A-Z][a-z]+ \d{1,2}, \d{4}",
            ),
        ],
        "continuation": [],
        "end": [],
    },
    {
        "document_key": "website-notice",
        "family": "public-meeting-website-notice",
        "page_start": 4,
        "page_end": 4,
        "priority": 70,
        "start": [
            (
                "website-notice-heading",
                "regex",
                r"City.s Website posted [A-Z][a-z]+ \d{1,2}, \d{4}",
            ),
        ],
        "continuation": [],
        "end": [],
    },
    {
        "document_key": "mailed-notice-and-map",
        "family": "public-meeting-mailed-notice-map",
        "page_start": 5,
        "page_end": 6,
        "priority": 60,
        "start": [
            (
                "mailed-notice-heading",
                "normalized_text",
                "NOTICE OF PUBLIC MEETING",
            ),
        ],
        "continuation": [
            (
                "bia-map-heading",
                "normalized_text",
                "Proposed Geographical Business Improvement Area (BIA)",
            ),
        ],
        "end": [
            (
                "bia-map-end",
                "normalized_text",
                "West Royalty Business & BioScience Inc. (WRBB)",
            ),
        ],
    },
]


def db_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "127.0.0.1"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def artifact_ref(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": payload["artifact_type"],
        "artifact_key": payload["artifact_key"],
        "schema_version": payload["schema_version"],
        "sha256": digest_bytes(canonical_bytes(payload)),
    }


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reviewed_state(*decision_ids: str) -> dict[str, Any]:
    return {
        "status": "approved",
        "reason_codes": [
            "approved-page-template",
            "approved-package-assembly",
            "phase-6-profile-approval",
        ],
        "decision_ids": list(dict.fromkeys((*decision_ids, PROFILE_DECISION_ID))),
    }


def anchor_payload(
    key: str, match_type: str, value: str
) -> dict[str, Any]:
    return {
        "anchor_key": key,
        "match_type": match_type,
        "value": value,
        "required": True,
    }


def source_locator(
    package_key: str,
    page_number: int,
    text: str,
) -> dict[str, Any]:
    return {
        "page_key": f"{package_key}:p{page_number:04d}",
        "page_number": page_number,
        "block_key": None,
        "bbox": None,
        "text_excerpt": " ".join(text.split())[:240] or None,
    }


def fetch_source(
    cursor: psycopg.Cursor[Any],
    source_document_id: int,
    expected_sha256: str,
    *,
    page_limit: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cursor.execute(
        """
        SELECT source_document_id, source_document_key, jurisdiction_key,
               document_family_key, document_type_key, title_raw,
               page_count, source_file_hash, metadata
        FROM documents.source_document
        WHERE source_document_id = %s AND is_active
        """,
        (source_document_id,),
    )
    source = cursor.fetchone()
    if source is None or source["source_file_hash"] != expected_sha256:
        raise RuntimeError(
            f"Source document {source_document_id} identity does not match"
        )
    cursor.execute(
        """
        SELECT source_page_id, page_number, text_raw, text_extraction_status
        FROM documents.source_page
        WHERE source_document_id = %s AND is_active
          AND (%s::integer IS NULL OR page_number <= %s::integer)
        ORDER BY page_number
        """,
        (source_document_id, page_limit, page_limit),
    )
    pages = cursor.fetchall()
    expected = (
        min(source["page_count"], page_limit)
        if page_limit is not None
        else source["page_count"]
    )
    if [page["page_number"] for page in pages] != list(
        range(1, expected + 1)
    ):
        raise RuntimeError(
            f"Source document {source_document_id} page coverage is incomplete"
        )
    return source, pages


def fetch_positive_review(
    cursor: psycopg.Cursor[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cursor.execute(
        """
        SELECT sp.page_number, sp.source_page_id,
               pc.page_classification_id, pc.review_status,
               pt.page_template_id, pt.page_template_key, pt.status,
               p.pattern_id, p.pattern_key, p.status AS pattern_status
        FROM documents.source_page sp
        JOIN documents.page_classification pc
          ON pc.source_page_id = sp.source_page_id AND pc.is_active
        JOIN documents.page_template pt
          ON pt.page_template_id = pc.page_template_id
        JOIN documents.pattern p ON p.pattern_id = pc.pattern_id
        WHERE sp.source_document_id = %s AND sp.is_active
        ORDER BY sp.page_number
        """,
        (POSITIVE_DOCUMENT_ID,),
    )
    reviews = cursor.fetchall()
    if len(reviews) != 6 or any(
        row["review_status"] != "accepted"
        or row["status"] != "active"
        or row["pattern_status"] != "approved"
        for row in reviews
    ):
        raise RuntimeError("Positive package page review is incomplete")
    cursor.execute(
        """
        SELECT package_document_assembly_id, document_key, document_order,
               title, page_start, page_end, is_agenda,
               primary_agenda_item_key, page_template_keys, assembly_rule,
               status, approved_at
        FROM documents.package_document_assembly
        WHERE source_document_id = %s AND is_active
        ORDER BY document_order
        """,
        (POSITIVE_DOCUMENT_ID,),
    )
    assembly = cursor.fetchall()
    if len(assembly) != 5 or any(
        row["status"] != "approved" or row["approved_at"] is None
        for row in assembly
    ):
        raise RuntimeError("Positive package assembly review is incomplete")
    observed = [
        (row["document_key"], row["page_start"], row["page_end"])
        for row in assembly
    ]
    expected = [
        (spec["document_key"], spec["page_start"], spec["page_end"])
        for spec in DOCUMENT_SPECS
    ]
    if observed != expected:
        raise RuntimeError("Positive package assembly differs from Phase 6 scope")
    return reviews, assembly


def package_input(
    source: dict[str, Any],
    pages: list[dict[str, Any]],
    *,
    package_key: str | None = None,
) -> dict[str, Any]:
    return {
        "package_key": package_key or source["source_document_key"],
        "source_sha256": source["source_file_hash"],
        "jurisdiction_key": source["jurisdiction_key"],
        "source_family": SOURCE_FAMILY,
        "document_family": source["document_type_key"],
        "pages": [
            {
                "page_number": page["page_number"],
                "text_source": (
                    page["text_extraction_status"]
                    if page["text_extraction_status"]
                    in {"embedded", "ocr", "visual_only", "mixed"}
                    else "embedded"
                ),
                "text": page["text_raw"] or "",
            }
            for page in pages
        ],
    }


def build_template(
    spec: dict[str, Any],
    package: dict[str, Any],
    reviews: list[dict[str, Any]],
    assembly: dict[str, Any],
    negative_package: dict[str, Any],
) -> dict[str, Any]:
    template_key = f"charlottetown-public-meeting:{spec['family']}"
    all_anchors = [
        anchor_payload(*item)
        for group in ("start", "continuation", "end")
        for item in spec[group]
    ]
    decision_ids = [
        f"documents:page-classification:{reviews[index - 1]['page_classification_id']}"
        for index in range(spec["page_start"], spec["page_end"] + 1)
    ]
    decision_ids.append(
        "documents:package-document-assembly:"
        f"{assembly['package_document_assembly_id']}"
    )
    positive_controls = [
        {
            "control_key": (
                f"positive:{spec['family']}:p{page_number:04d}"
            ),
            "control_type": "positive",
            "source_locator": source_locator(
                package["package_key"],
                page_number,
                package["pages"][page_number - 1]["text"],
            ),
            "expected_result": (
                "Reviewed source page matches the approved document family."
            ),
        }
        for page_number in range(spec["page_start"], spec["page_end"] + 1)
    ]
    return {
        "$schema": SCHEMA_REF,
        "schema_version": 2,
        "artifact_type": "structural_template",
        "artifact_key": f"{template_key}:1.0.0",
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [],
        "template_key": template_key,
        "template_version": "1.0.0",
        "status": "approved",
        "reuse_scope": "same_edition_family",
        "source_family": SOURCE_FAMILY,
        "supported_text_sources": ["embedded"],
        "anchors": [
            {
                **item,
                "region": {"x0": 0, "y0": 0, "x1": 1, "y1": 1},
                "geometry_tolerance": 1,
            }
            for item in all_anchors
        ],
        "block_rules": [{
            "rule_key": "block:formatted-text",
            "block_type": "formatted_text",
            "minimum_count": 1,
            "maximum_count": None,
            "reading_order": 1,
            "required": True,
        }],
        "internal_region_rules": [],
        "column_bands": [],
        "header_policy": {
            "mode": "absent",
            "source_anchor_keys": [],
            "allow_optional_repetition": False,
        },
        "table_title_policy": {
            "mode": "absent",
            "allowed_positions": [],
            "anchor_keys": [],
        },
        "continuation_rules": [
            {
                "rule_key": f"continuation:{key}",
                "rule_type": "required_text_anchor",
                "parameters": {"anchor_key": key},
                "required": True,
            }
            for key, _, _ in spec["continuation"]
        ],
        "termination_rules": [{
            "rule_key": "approved-document-boundary",
            "rule_type": "next-document-start-or-package-end",
            "parameters": {
                "minimum_pages": spec["page_end"] - spec["page_start"] + 1,
                "maximum_pages": spec["page_end"] - spec["page_start"] + 1,
            },
            "required": True,
        }],
        "negative_controls": [{
            "control_key": f"negative:{spec['family']}:regular-council-p0001",
            "control_type": "negative",
            "source_locator": source_locator(
                negative_package["package_key"],
                1,
                negative_package["pages"][0]["text"],
            ),
            "expected_result": (
                "Regular-council package page remains unmatched."
            ),
        }],
        "regression_controls": positive_controls,
        "approval": reviewed_state(*decision_ids),
    }


def build_policy(
    template: dict[str, Any],
    positive_control_key: str,
) -> dict[str, Any]:
    template_reference = artifact_ref(template)
    policy_key = f"{template['template_key']}:review-policy"
    return {
        "$schema": SCHEMA_REF,
        "schema_version": 2,
        "artifact_type": "template_review_policy",
        "artifact_key": f"{policy_key}:1.0.0",
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [template_reference],
        "policy_key": policy_key,
        "policy_version": "1.0.0",
        "status": "approved",
        "template_binding": {
            "template_key": template["template_key"],
            "template_version": template["template_version"],
            "artifact_ref": template_reference,
        },
        "supersedes_policy_ref": None,
        "scope": {
            "reuse_scope": "same_edition_family",
            "jurisdiction_key": "charlottetown-pe",
            "source_family": SOURCE_FAMILY,
            "document_family": template["template_key"].split(":")[-1],
        },
        "matcher": copy.deepcopy(MATCHER),
        "mode": "review_required",
        "eligible_fit_classes": ["exact", "light_variation"],
        "allowed_light_mismatch_categories": [],
        "sample_rate": 1,
        "promotion_gates": {
            "minimum_positive_examples": 0,
            "minimum_negative_controls": 0,
            "minimum_reviewed_applications": 0,
            "minimum_observed_precision": 0,
            "maximum_false_approvals": 0,
        },
        "promotion_evidence": {
            "positive_application_keys": [positive_control_key],
            "negative_control_keys": [
                template["negative_controls"][0]["control_key"]
            ],
            "validation_run_keys": [
                f"validation:{template['template_key']}:1.0.0"
            ],
            "reviewed_application_count": 1,
            "accepted_application_count": 1,
            "rejected_application_count": 0,
            "false_approval_count": 0,
            "observed_precision": 1,
        },
        "suspension_rules": {
            "material_mismatch": True,
            "negative_control_failure": True,
            "sample_rejection": True,
            "matcher_change": True,
            "source_profile_change": True,
        },
        "approval": copy.deepcopy(template["approval"]),
    }


def build_profile(
    templates: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    positive: dict[str, Any],
    negative: dict[str, Any],
) -> dict[str, Any]:
    document_templates = []
    for spec, template, policy in zip(
        DOCUMENT_SPECS, templates, policies, strict=True
    ):
        document_templates.append({
            "document_template_key": template["template_key"],
            "document_family": spec["family"],
            "priority": spec["priority"],
            "template_ref": artifact_ref(template),
            "policy_ref": artifact_ref(policy),
            "policy_mode": "review_required",
            "sample_rate": 1,
            "start_anchors": [
                anchor_payload(*item) for item in spec["start"]
            ],
            "continuation_anchors": [
                anchor_payload(*item) for item in spec["continuation"]
            ],
            "end_anchors": [
                anchor_payload(*item) for item in spec["end"]
            ],
            "minimum_pages": spec["page_end"] - spec["page_start"] + 1,
            "maximum_pages": spec["page_end"] - spec["page_start"] + 1,
            "allow_visual_only_continuation": False,
        })
    transitions = [
        {
            "from": DOCUMENT_SPECS[index]["family"],
            "to": DOCUMENT_SPECS[index + 1]["family"],
        }
        for index in range(len(DOCUMENT_SPECS) - 1)
    ]
    return {
        "$schema": "agenda-package-reuse-profile.schema.json",
        "schema_version": 1,
        "profile_key": "charlottetown:council-public-meeting-package",
        "profile_version": "1.0.0",
        "status": "approved",
        "scope": {
            "jurisdiction_key": "charlottetown-pe",
            "source_family": SOURCE_FAMILY,
            "document_family": "agenda-package",
            "reuse_scope": "same_edition_family",
        },
        "package_grammar": {
            "first_document_family": DOCUMENT_SPECS[0]["family"],
            "allowed_transitions": transitions,
            "require_complete_coverage": True,
        },
        "document_templates": document_templates,
        "positive_controls": [{
            "control_key": "positive:public-meeting-single-and-multipage",
            "package_key": positive["package_key"],
            "page_numbers": list(range(1, 7)),
            "expected_result": "matched",
        }],
        "negative_controls": [{
            "control_key": "negative:regular-council-first-six-pages",
            "package_key": negative["package_key"],
            "page_numbers": list(range(1, 7)),
            "expected_result": "unknown",
        }],
        "approval": {
            "status": "approved",
            "decision_id": PROFILE_DECISION_ID,
        },
    }


def write_atomic(path: Path, value: dict[str, Any]) -> str:
    body = canonical_bytes(value)
    if path.exists():
        return "unchanged" if path.read_bytes() == body else "conflict"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return "created"


def backfill_source_family(
    connection: psycopg.Connection[Any],
    *,
    apply: bool,
) -> dict[str, Any]:
    expected = {
        POSITIVE_DOCUMENT_ID: POSITIVE_SOURCE_SHA256,
        NEGATIVE_DOCUMENT_ID: NEGATIVE_SOURCE_SHA256,
    }
    pending = []
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT source_document_id, source_file_hash,
                   metadata->>'source_family' AS source_family
            FROM documents.source_document
            WHERE source_document_id = ANY(%s) AND is_active
            ORDER BY source_document_id
            """,
            (list(expected),),
        )
        rows = cursor.fetchall()
        if {
            row["source_document_id"]: row["source_file_hash"]
            for row in rows
        } != expected:
            raise RuntimeError("Source-family backfill allowlist identity mismatch")
        pending = [
            row["source_document_id"]
            for row in rows
            if row["source_family"] != SOURCE_FAMILY
        ]
        updated = 0
        if apply and pending:
            cursor.execute(
                """
                UPDATE documents.source_document
                SET metadata = metadata || jsonb_build_object(
                    'source_family', %s::text
                )
                WHERE source_document_id = ANY(%s)
                  AND metadata->>'source_family' IS DISTINCT FROM %s
                """,
                (SOURCE_FAMILY, pending, SOURCE_FAMILY),
            )
            updated = cursor.rowcount
        if apply:
            connection.commit()
        else:
            connection.rollback()
    return {
        "allowlisted_source_document_ids": sorted(expected),
        "pending_before": len(pending),
        "updated": updated,
        "applied": apply,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--apply-source-family", action="store_true")
    args = parser.parse_args()

    preview_module = load_module(
        ROOT / "scripts/preview-agenda-package-reuse.py",
        "agenda_package_reuse",
    )
    validator_module = load_module(
        ROOT / "scripts/validate-staged-pdf-artifacts.py",
        "staged_pdf_validator",
    )
    with psycopg.connect(db_url(), row_factory=dict_row) as connection:
        backfill = backfill_source_family(
            connection, apply=args.apply_source_family
        )
        if backfill["pending_before"] and not args.apply_source_family:
            print(json.dumps({
                "status": "dry_run",
                "backfill": backfill,
                "outputs_created": 0,
            }, sort_keys=True))
            return 0
        with connection.cursor(row_factory=dict_row) as cursor:
            positive_source, positive_pages = fetch_source(
                cursor,
                POSITIVE_DOCUMENT_ID,
                POSITIVE_SOURCE_SHA256,
            )
            negative_source, negative_pages = fetch_source(
                cursor,
                NEGATIVE_DOCUMENT_ID,
                NEGATIVE_SOURCE_SHA256,
                page_limit=6,
            )
            reviews, assembly = fetch_positive_review(cursor)

    positive = package_input(positive_source, positive_pages)
    negative = package_input(
        negative_source,
        negative_pages,
        package_key=f"{negative_source['source_document_key']}:control:first-six",
    )
    templates = [
        build_template(
            spec,
            positive,
            reviews,
            assembly[index],
            negative,
        )
        for index, spec in enumerate(DOCUMENT_SPECS)
    ]
    policies = [
        build_policy(
            template,
            f"positive:{spec['family']}:{positive['package_key']}",
        )
        for spec, template in zip(DOCUMENT_SPECS, templates, strict=True)
    ]
    for artifact in [*templates, *policies]:
        errors = validator_module.validate_payload(artifact)
        if errors:
            raise RuntimeError(
                f"{artifact['artifact_key']} validation failed: "
                + "; ".join(errors[:8])
            )
    profile = build_profile(templates, policies, positive, negative)
    profile_errors = preview_module.validate(
        preview_module.PROFILE_SCHEMA_PATH, profile
    )
    if profile_errors:
        raise RuntimeError(
            "Profile validation failed: " + "; ".join(profile_errors[:8])
        )
    positive_preview = preview_module.preview(profile, positive)
    negative_preview = preview_module.preview(profile, negative)
    if (
        positive_preview["status"] != "needs_review"
        or len(positive_preview["documents"]) != 5
        or positive_preview["coverage"]["assigned_pages"] != 6
        or positive_preview["unknown_pages"]
        or positive_preview["conflicts"]
        or any(
            document["fit_class"] != "exact"
            for document in positive_preview["documents"]
        )
    ):
        raise RuntimeError(
            "Positive package control did not match exactly: "
            + json.dumps({
                "status": positive_preview["status"],
                "documents": [
                    {
                        "family": item["document_family"],
                        "pages": [item["page_start"], item["page_end"]],
                        "fit": item["fit_class"],
                        "unresolved": item["unresolved_evidence"],
                    }
                    for item in positive_preview["documents"]
                ],
                "unknown_pages": positive_preview["unknown_pages"],
                "conflicts": positive_preview["conflicts"],
                "coverage": positive_preview["coverage"],
            }, sort_keys=True)
        )
    if (
        negative_preview["status"] != "blocked"
        or negative_preview["unknown_pages"] != list(range(1, 7))
        or negative_preview["documents"]
        or negative_preview["coverage"]["omitted_pages"] != 0
    ):
        raise RuntimeError("Nearest-negative package control did not block")

    source_control = {
        "schema_version": 1,
        "source_family": SOURCE_FAMILY,
        "positive_source": {
            "source_document_id": POSITIVE_DOCUMENT_ID,
            "source_sha256": POSITIVE_SOURCE_SHA256,
            "page_classification_ids": [
                row["page_classification_id"] for row in reviews
            ],
            "page_template_ids": [row["page_template_id"] for row in reviews],
            "pattern_ids": [row["pattern_id"] for row in reviews],
            "assembly_ids": [
                row["package_document_assembly_id"] for row in assembly
            ],
        },
        "negative_source": {
            "source_document_id": NEGATIVE_DOCUMENT_ID,
            "source_sha256": NEGATIVE_SOURCE_SHA256,
            "page_numbers": list(range(1, 7)),
            "review_status": "unreviewed-negative-control-only",
        },
        "approval_decision_id": PROFILE_DECISION_ID,
        "source_family_backfill_status": "verified",
        "publication_write_count": 0,
    }
    outputs: list[tuple[Path, dict[str, Any]]] = [
        (args.output_root / "source-control.json", source_control),
        (args.output_root / "positive-package.json", positive),
        (args.output_root / "negative-package.json", negative),
        (args.output_root / "profile.json", profile),
        (args.output_root / "positive-preview.json", positive_preview),
        (args.output_root / "negative-preview.json", negative_preview),
    ]
    for spec, template, policy in zip(
        DOCUMENT_SPECS, templates, policies, strict=True
    ):
        family_root = args.output_root / spec["family"]
        outputs.extend([
            (family_root / "structural-template.json", template),
            (family_root / "template-review-policy.json", policy),
        ])
    statuses = {}
    for path, value in outputs:
        status = write_atomic(path, value)
        if status == "conflict":
            raise RuntimeError(f"Refusing to replace differing output: {path}")
        statuses[path.relative_to(args.output_root).as_posix()] = status
    print(json.dumps({
        "output_root": (
            args.output_root.relative_to(ROOT).as_posix()
            if args.output_root.is_relative_to(ROOT)
            else str(args.output_root)
        ),
        "outputs": statuses,
        "backfill": backfill,
        "positive": {
            "status": positive_preview["status"],
            "documents": len(positive_preview["documents"]),
            "assigned_pages": positive_preview["coverage"]["assigned_pages"],
        },
        "negative": {
            "status": negative_preview["status"],
            "unknown_pages": negative_preview["unknown_pages"],
        },
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

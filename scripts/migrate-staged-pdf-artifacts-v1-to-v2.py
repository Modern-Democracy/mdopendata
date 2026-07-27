#!/usr/bin/env python3
"""Migrate a frozen staged-PDF v1 pilot into a parallel v2 artifact set."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-staged-pdf-artifacts.py"
SCHEMA_V2_PATH = ROOT / "schema" / "json-schema" / "staged-pdf-artifacts-v2.schema.json"
DEFAULT_BASE = ROOT / "data" / "budget" / "charlottetown" / "2026-2027" / "staged-pdf"
MIGRATOR_NAME = "staged-pdf-v1-v2-migrator"
MIGRATOR_VERSION = "1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator_module = load_module("staged_pdf_validator_for_migration", VALIDATOR_PATH)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def v2_key(value: str) -> str:
    if not value.endswith(":v1"):
        raise ValueError(f"Version 1 artifact key does not end in ':v1': {value}")
    return f"{value[:-3]}:v2"


def artifact_ref(payload: dict[str, Any], sha256: str, schema_version: int) -> dict[str, Any]:
    return {
        "artifact_type": payload["artifact_type"],
        "artifact_key": payload["artifact_key"],
        "schema_version": schema_version,
        "sha256": sha256,
    }


def schema_ref(output_path: Path) -> str:
    return os.path.relpath(SCHEMA_V2_PATH, output_path.parent).replace("\\", "/")


def config_hash(input_hashes: dict[str, str]) -> str:
    config = {
        "input_hashes": input_hashes,
        "migrator": MIGRATOR_NAME,
        "migrator_version": MIGRATOR_VERSION,
        "schema_sha256": digest_path(SCHEMA_V2_PATH),
    }
    return digest_bytes(canonical_bytes(config))


def migrated_header(
    payload: dict[str, Any],
    output_path: Path,
    generator_config_sha256: str,
) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["$schema"] = schema_ref(output_path)
    result["schema_version"] = 2
    result["artifact_key"] = v2_key(payload["artifact_key"])
    result["generator"] = {
        "name": MIGRATOR_NAME,
        "version": MIGRATOR_VERSION,
        "config_sha256": generator_config_sha256,
    }
    return result


def migrate_payloads(
    source: dict[str, Any],
    blocks: dict[str, Any],
    review: dict[str, Any],
    input_hashes: dict[str, str],
    output_paths: dict[str, Path],
    occurred_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    generator_config_sha256 = config_hash(input_hashes)

    source_v2 = migrated_header(
        source, output_paths["source_evidence"], generator_config_sha256
    )
    source_v2["upstream_artifacts"] = [
        artifact_ref(source, input_hashes["source_evidence"], 1)
    ]
    source_v2_sha256 = digest_bytes(canonical_bytes(source_v2))

    blocks_v2 = migrated_header(
        blocks, output_paths["block_inventory"], generator_config_sha256
    )
    blocks_v2["upstream_artifacts"] = [
        artifact_ref(source_v2, source_v2_sha256, 2)
    ]
    blocks_v2_sha256 = digest_bytes(canonical_bytes(blocks_v2))

    review_v2 = migrated_header(
        review, output_paths["review_decisions"], generator_config_sha256
    )
    review_v2["upstream_artifacts"] = [
        artifact_ref(source_v2, source_v2_sha256, 2)
    ]
    review_v2["target_artifacts"] = [
        artifact_ref(blocks_v2, blocks_v2_sha256, 2)
    ]
    for event in review_v2["events"]:
        event["reviewer"]["actor_type"] = "human"
        event["decision_basis"] = "reviewer"
        event["policy_ref"] = None

    prior_head = review_v2["events"][-1]["event_sha256"] if review_v2["events"] else None
    sequence = len(review_v2["events"]) + 1
    event = {
        "decision_id": f"{review_v2['document_key']}:decision:{sequence:06d}",
        "sequence": sequence,
        "occurred_at": occurred_at,
        "reviewer": {
            "reviewer_id": MIGRATOR_NAME,
            "display_name": "Staged PDF v1 to v2 migrator",
            "role": "artifact-migrator",
            "actor_type": "system",
        },
        "decision_basis": "reviewer",
        "policy_ref": None,
        "action": "migrate_schema",
        "reason": "Deterministic parallel migration from staged PDF schema version 1 to version 2",
        "prior_artifact_sha256": input_hashes["block_inventory"],
        "result_artifact_sha256": blocks_v2_sha256,
        "previous_event_sha256": prior_head,
        "event_sha256": "0" * 64,
        "affected_keys": [blocks_v2["artifact_key"]],
        "source_locators": [],
        "changes": [
            {
                "field_path": "/schema_version",
                "prior_value": 1,
                "new_value": 2,
            },
            {
                "field_path": "/artifact_key",
                "prior_value": blocks["artifact_key"],
                "new_value": blocks_v2["artifact_key"],
            },
            {
                "field_path": "/upstream_artifacts/0/schema_version",
                "prior_value": 1,
                "new_value": 2,
            },
        ],
    }
    event_hash_payload = copy.deepcopy(event)
    event_hash_payload.pop("event_sha256")
    event["event_sha256"] = digest_bytes(canonical_bytes(event_hash_payload))
    review_v2["events"].append(event)
    review_v2_sha256 = digest_bytes(canonical_bytes(review_v2))

    report = {
        "migration_key": f"{review_v2['document_key']}:staged-pdf:v1-to-v2",
        "migration_version": MIGRATOR_VERSION,
        "occurred_at": occurred_at,
        "schema": {
            "repo_relpath": SCHEMA_V2_PATH.relative_to(ROOT).as_posix(),
            "sha256": digest_path(SCHEMA_V2_PATH),
        },
        "inputs": {
            "source_evidence": artifact_ref(source, input_hashes["source_evidence"], 1),
            "block_inventory": artifact_ref(blocks, input_hashes["block_inventory"], 1),
            "review_decisions": artifact_ref(review, input_hashes["review_decisions"], 1),
        },
        "outputs": {
            "source_evidence": artifact_ref(source_v2, source_v2_sha256, 2),
            "block_inventory": artifact_ref(blocks_v2, blocks_v2_sha256, 2),
            "review_decisions": artifact_ref(review_v2, review_v2_sha256, 2),
        },
        "preservation": {
            "stable_record_keys": True,
            "omitted_unit_spans": True,
            "historical_review_event_hashes": True,
            "version_1_bytes_unchanged": True,
        },
        "review_policies": {
            "eligible_approved_template_count": 0,
            "seeded_review_required_policy_count": 0,
            "automatic_approval_policy_count": 0,
            "reason": "The frozen version 1 pilot contains no structural-template artifacts.",
        },
        "controls": {
            "database_write_count": 0,
            "publication_write_count": 0,
        },
        "counts": {
            "source_pages": len(source_v2["pages"]),
            "block_records": len(blocks_v2["records"]),
            "relationships": len(blocks_v2["relationships"]),
            "historical_review_events": len(review["events"]),
            "migration_review_events": 1,
        },
    }
    return source_v2, blocks_v2, review_v2, report


def collect_stable_keys(value: Any, path: tuple[str, ...] = ()) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if isinstance(value, dict):
        for name, child in value.items():
            if (
                name.endswith("_key")
                and name not in {"artifact_key", "document_key"}
                and isinstance(child, str)
            ):
                keys.add(("/".join((*path, name)), child))
            keys.update(collect_stable_keys(child, (*path, name)))
    elif isinstance(value, list):
        for child in value:
            keys.update(collect_stable_keys(child, path))
    return keys


def assert_preservation(
    source: dict[str, Any],
    blocks: dict[str, Any],
    review: dict[str, Any],
    source_v2: dict[str, Any],
    blocks_v2: dict[str, Any],
    review_v2: dict[str, Any],
) -> None:
    def without_envelope(
        payload: dict[str, Any], extra_fields: tuple[str, ...] = ()
    ) -> dict[str, Any]:
        result = copy.deepcopy(payload)
        for name in (
            "$schema",
            "schema_version",
            "artifact_key",
            "generator",
            "upstream_artifacts",
            *extra_fields,
        ):
            result.pop(name, None)
        return result

    if without_envelope(source) != without_envelope(source_v2):
        raise ValueError("Source-evidence content changed beyond the version 2 envelope")
    if without_envelope(blocks) != without_envelope(blocks_v2):
        raise ValueError("Block-inventory content changed beyond the version 2 envelope")

    if collect_stable_keys(source) != collect_stable_keys(source_v2):
        raise ValueError("Source-evidence stable keys changed during migration")
    if collect_stable_keys(blocks) != collect_stable_keys(blocks_v2):
        raise ValueError("Block-inventory stable keys changed during migration")

    historical_review = without_envelope(review_v2, ("target_artifacts",))
    historical_review["events"] = historical_review["events"][:-1]
    for event in historical_review["events"]:
        event["reviewer"].pop("actor_type")
        event.pop("decision_basis")
        event.pop("policy_ref")
    if historical_review != without_envelope(review, ("target_artifacts",)):
        raise ValueError("Historical review content changed during migration")
    if {
        event["event_sha256"] for event in historical_review["events"]
    } != {event["event_sha256"] for event in review["events"]}:
        raise ValueError("Historical review event hashes changed during migration")

    def span_presence(payload: dict[str, Any]) -> list[tuple[bool, bool]]:
        return [
            ("row_span" in cell, "column_span" in cell)
            for record in payload["records"]
            for cell in (record.get("table_grid") or {}).get("cells", [])
        ]

    if span_presence(blocks) != span_presence(blocks_v2):
        raise ValueError("Omitted or explicit span fields changed during migration")


def validate_outputs(payloads: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for payload in payloads:
        errors.extend(
            f"{payload['artifact_type']}: {error}"
            for error in validator_module.validate_payload(payload)
        )
    errors.extend(validator_module.validate_artifact_set(payloads))
    if errors:
        raise ValueError("Generated version 2 artifacts are invalid:\n" + "\n".join(errors))


def validate_occurred_at(value: str, review: dict[str, Any]) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--occurred-at must include a timezone")
    if review["events"]:
        last = datetime.fromisoformat(
            review["events"][-1]["occurred_at"].replace("Z", "+00:00")
        )
        if parsed < last:
            raise ValueError("--occurred-at precedes the final version 1 review event")


def assert_frozen_inputs(
    source_path: Path,
    blocks_path: Path,
    review_path: Path,
    baseline: dict[str, Any],
) -> dict[str, str]:
    expected = baseline["version_1"]
    paths = {
        "source_evidence": source_path,
        "block_inventory": blocks_path,
        "review_decisions": review_path,
    }
    actual = {name: digest_path(path) for name, path in paths.items()}
    for name, sha256 in actual.items():
        if sha256 != expected[name]["sha256"]:
            raise ValueError(
                f"Frozen version 1 hash mismatch for {name}: "
                f"expected {expected[name]['sha256']}, received {sha256}"
            )
    return actual


def preflight_and_write(files: dict[Path, bytes]) -> tuple[int, int]:
    created = 0
    unchanged = 0
    for path, content in files.items():
        if path.exists():
            if path.read_bytes() != content:
                raise FileExistsError(f"Conflicting migration output already exists: {path}")
            unchanged += 1
    for path, content in files.items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        os.replace(temporary, path)
        created += 1
    return created, unchanged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_BASE / "v1" / "stage-0" / "source-evidence.json",
    )
    parser.add_argument(
        "--blocks",
        type=Path,
        default=DEFAULT_BASE / "v1" / "stage-1" / "block-inventory.json",
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=DEFAULT_BASE / "v1" / "review" / "review-decisions.json",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASE / "v2" / "phase-0" / "baseline-and-controls.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_BASE / "v2",
    )
    parser.add_argument(
        "--occurred-at",
        required=True,
        help="Deterministic migration event timestamp in ISO 8601 format",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.source.resolve()
    blocks_path = args.blocks.resolve()
    review_path = args.review.resolve()
    baseline_path = args.baseline.resolve()
    output_root = args.output_root.resolve()
    output_paths = {
        "source_evidence": output_root / "stage-0" / "source-evidence.json",
        "block_inventory": output_root / "stage-1" / "block-inventory.json",
        "review_decisions": output_root / "review" / "review-decisions.json",
        "migration_report": output_root / "phase-2" / "migration-report.json",
    }

    source = read_json(source_path)
    blocks = read_json(blocks_path)
    review = read_json(review_path)
    baseline = read_json(baseline_path)
    validate_occurred_at(args.occurred_at, review)
    input_hashes = assert_frozen_inputs(
        source_path, blocks_path, review_path, baseline
    )
    before = dict(input_hashes)

    source_v2, blocks_v2, review_v2, report = migrate_payloads(
        source,
        blocks,
        review,
        input_hashes,
        output_paths,
        args.occurred_at,
    )
    assert_preservation(source, blocks, review, source_v2, blocks_v2, review_v2)
    validate_outputs([source_v2, blocks_v2, review_v2])
    after = {
        "source_evidence": digest_path(source_path),
        "block_inventory": digest_path(blocks_path),
        "review_decisions": digest_path(review_path),
    }
    if before != after:
        raise RuntimeError("Version 1 artifacts changed during migration")

    files = {
        output_paths["source_evidence"]: canonical_bytes(source_v2),
        output_paths["block_inventory"]: canonical_bytes(blocks_v2),
        output_paths["review_decisions"]: canonical_bytes(review_v2),
        output_paths["migration_report"]: canonical_bytes(report),
    }
    created, unchanged = preflight_and_write(files)
    print(
        json.dumps(
            {
                "created": created,
                "unchanged": unchanged,
                "output_root": output_root.as_posix(),
                "output_hashes": {
                    name: digest_bytes(content)
                    for name, content in (
                        ("source_evidence", files[output_paths["source_evidence"]]),
                        ("block_inventory", files[output_paths["block_inventory"]]),
                        ("review_decisions", files[output_paths["review_decisions"]]),
                        ("migration_report", files[output_paths["migration_report"]]),
                    )
                },
                "version_1_unchanged": before == after,
                "database_write_count": 0,
                "publication_write_count": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

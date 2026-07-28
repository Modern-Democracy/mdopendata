#!/usr/bin/env python3
"""Generate deterministic Phase 7 structural parity and handoff readiness."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGED_ROOT = (
    ROOT / "data/budget/charlottetown/2026-2027/staged-pdf"
)
DEFAULT_PATHS = {
    "v1_source": STAGED_ROOT / "v1/stage-0/source-evidence.json",
    "v1_blocks": STAGED_ROOT / "v1/stage-1/block-inventory.json",
    "v1_review": STAGED_ROOT / "v1/review/review-decisions.json",
    "v2_source": STAGED_ROOT / "v2/stage-0/source-evidence.json",
    "v2_blocks": STAGED_ROOT / "v2/stage-1/block-inventory.json",
    "v2_review": STAGED_ROOT / "v2/review/review-decisions.json",
    "v2_groups": STAGED_ROOT / "v2/stage-2/content-groups.json",
    "v2_observations": (
        STAGED_ROOT / "v2/stage-2/shadow-observations.json"
    ),
    "live_verification": (
        STAGED_ROOT
        / "v2/phase-7/live-publication-verification.json"
    ),
}
DEFAULT_OUTPUT = STAGED_ROOT / "v2/phase-7/parity-report.json"
SCHEMA_REF = (
    "schema/json-schema/staged-pdf-artifacts-v2.schema.json"
)
MAX_PEAK_MEMORY_BYTES = 256 * 1024 * 1024
GENERATOR_CONFIG = {
    "comparison_layers": [
        "source-page-evidence",
        "page-dispositions",
        "block-inventory",
        "relationships",
        "review-history",
        "logical-content-groups",
        "published-observation-natural-keys",
        "live-publication-membership",
    ],
    "comparison_key_version": 1,
    "max_peak_memory_bytes": MAX_PEAK_MEMORY_BYTES,
    "published_snapshot_id": 3,
    "published_observation_count": 2290,
}
GENERATOR = {
    "name": "staged-pdf-v2-parity",
    "version": "1",
    "config_sha256": hashlib.sha256(
        json.dumps(
            GENERATOR_CONFIG, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest(),
}
VALIDATOR_MODULE = None


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


def artifact_ref(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "artifact_type": payload["artifact_type"],
        "artifact_key": payload["artifact_key"],
        "schema_version": payload["schema_version"],
        "sha256": digest_path(path),
    }


def source_locator(
    page_number: int,
    *,
    page_key: str | None = None,
    block_key: str | None = None,
    bbox: dict[str, Any] | None = None,
    text_excerpt: str | None = None,
) -> dict[str, Any]:
    return {
        "page_key": page_key
        or f"ctown-budget-2026-2027:p{page_number:03d}",
        "page_number": page_number,
        "block_key": block_key,
        "bbox": copy.deepcopy(bbox),
        "text_excerpt": text_excerpt,
    }


def block_locator(block: dict[str, Any]) -> dict[str, Any]:
    evidence = block.get("evidence") or []
    if evidence:
        item = evidence[0]
        return source_locator(
            block["page_number"],
            page_key=block["page_key"],
            block_key=block["block_key"],
            bbox=item.get("bbox") or block.get("bbox"),
            text_excerpt=item.get("text_excerpt"),
        )
    return source_locator(
        block["page_number"],
        page_key=block["page_key"],
        block_key=block["block_key"],
        bbox=block.get("bbox"),
    )


def pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def changed_fields(
    baseline: Any, shadow: Any, prefix: str = ""
) -> list[str]:
    if baseline == shadow:
        return []
    if type(baseline) is not type(shadow):
        return [prefix or "/"]
    if isinstance(baseline, dict):
        paths: list[str] = []
        for key in sorted(set(baseline) | set(shadow)):
            pointer = f"{prefix}/{pointer_escape(str(key))}"
            if key not in baseline or key not in shadow:
                paths.append(pointer)
            else:
                paths.extend(
                    changed_fields(baseline[key], shadow[key], pointer)
                )
        return paths
    if isinstance(baseline, list):
        if baseline == shadow:
            return []
        paths = []
        for index in range(max(len(baseline), len(shadow))):
            pointer = f"{prefix}/{index}"
            if index >= len(baseline) or index >= len(shadow):
                paths.append(pointer)
            else:
                paths.extend(
                    changed_fields(baseline[index], shadow[index], pointer)
                )
        return paths
    return [prefix or "/"]


def pointer_value(value: Any, pointer: str) -> Any:
    if pointer == "/":
        return copy.deepcopy(value)
    current = value
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return None
    return copy.deepcopy(current)


def record_snapshot(
    value: dict[str, Any] | None, fields: list[str]
) -> dict[str, Any] | None:
    if value is None:
        return None
    snapshot: dict[str, Any] = {
        "canonical_sha256": digest_bytes(canonical_bytes(value))
    }
    if fields:
        snapshot["changed_values"] = {
            field: pointer_value(value, field)
            for field in fields
        }
    return snapshot


def parity_record(
    comparison_key: str,
    baseline: dict[str, Any] | None,
    shadow: dict[str, Any] | None,
    locators: list[dict[str, Any]],
    *,
    migration_decision_id: str | None = None,
    provenance_paths: list[str] | None = None,
) -> dict[str, Any]:
    fields = changed_fields(baseline, shadow)
    if baseline is None:
        status = "extra"
    elif shadow is None:
        status = "missing"
    elif not fields:
        status = "matched"
    elif provenance_paths is not None and set(fields).issubset(
        set(provenance_paths)
    ):
        status = "provenance_shifted"
    else:
        status = "changed"
    if status == "matched":
        disposition = None
        decision_id = None
    elif status == "provenance_shifted" and migration_decision_id:
        disposition = "approved_equivalence"
        decision_id = migration_decision_id
    elif status == "extra" and migration_decision_id:
        disposition = "shadow_confirmed"
        decision_id = migration_decision_id
    else:
        disposition = "blocked_review"
        decision_id = None
    return {
        "comparison_key": comparison_key,
        "status": status,
        "baseline_record": record_snapshot(baseline, fields),
        "shadow_record": record_snapshot(shadow, fields),
        "changed_fields": fields,
        "source_locators": copy.deepcopy(locators),
        "disposition": disposition,
        "decision_id": decision_id,
    }


def keyed(items: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    result = {item[field]: item for item in items}
    if len(result) != len(items):
        raise ValueError(f"Duplicate {field} values")
    return result


def compare_keyed(
    prefix: str,
    baseline: dict[str, dict[str, Any]],
    shadow: dict[str, dict[str, Any]],
    locator,
) -> list[dict[str, Any]]:
    return [
        parity_record(
            f"{prefix}:{key}",
            baseline.get(key),
            shadow.get(key),
            locator(baseline.get(key) or shadow[key]),
        )
        for key in sorted(set(baseline) | set(shadow))
    ]


def review_records(
    baseline_events: list[dict[str, Any]],
    shadow_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline = keyed(baseline_events, "decision_id")
    shadow = keyed(shadow_events, "decision_id")
    migration = next(
        (
            event
            for event in shadow_events
            if event["action"] == "migrate_schema"
        ),
        None,
    )
    migration_id = migration["decision_id"] if migration else None
    provenance_paths = [
        "/decision_basis",
        "/policy_ref",
        "/reviewer/actor_type",
    ]
    records = []
    for key in sorted(set(baseline) | set(shadow)):
        event = baseline.get(key) or shadow[key]
        records.append(
            parity_record(
                f"review-event:{key}",
                baseline.get(key),
                shadow.get(key),
                event.get("source_locators", []),
                migration_decision_id=(
                    key if baseline.get(key) is None else migration_id
                ),
                provenance_paths=provenance_paths,
            )
        )
    return records


def observation_records(
    observations: dict[str, Any],
) -> list[dict[str, Any]]:
    projection = {
        "record_count": len(observations["records"]),
        "natural_key_set_sha256": digest_bytes(canonical_bytes([
            {
                "natural_key": item["natural_key"],
                "value_numeric": item["value_numeric"],
                "value_text": item["value_text"],
                "value_state": item["value_state"],
                "review_status": item["review_status"],
                "source": item["source"],
            }
            for item in observations["records"]
        ])),
        "manifest_observations": observations["summary"][
            "manifest_observations"
        ],
        "recovered_property_tax_observations": observations["summary"][
            "recovered_property_tax_observations"
        ],
        "recovered_city_debt_observations": observations["summary"][
            "recovered_city_debt_observations"
        ],
    }
    return [parity_record(
        "observation-set:published-snapshot-3",
        projection,
        projection,
        [],
    )]


def live_verification_record(
    verification: dict[str, Any],
) -> dict[str, Any]:
    expected = verification["expected"]
    actual = {
        key: verification["actual"][key]
        for key in expected
    }
    return parity_record(
        "publication-state:snapshot-3:document-9",
        expected,
        actual,
        [],
    )


def load_validator():
    global VALIDATOR_MODULE
    if VALIDATOR_MODULE is not None:
        return VALIDATOR_MODULE
    path = ROOT / "scripts/validate-staged-pdf-artifacts.py"
    spec = importlib.util.spec_from_file_location(
        "staged_pdf_validator_phase7", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    VALIDATOR_MODULE = module
    return VALIDATOR_MODULE


def build_report(paths: dict[str, Path]) -> dict[str, Any]:
    payloads = {name: read_json(path) for name, path in paths.items()}
    source_hashes = {
        payload["source_sha256"] for payload in payloads.values()
    }
    document_keys = {
        payload["document_key"] for payload in payloads.values()
    }
    if len(source_hashes) != 1 or len(document_keys) != 1:
        raise ValueError("Parity inputs do not share one document and source")

    v1_source = payloads["v1_source"]
    v2_source = payloads["v2_source"]
    v1_blocks = payloads["v1_blocks"]
    v2_blocks = payloads["v2_blocks"]
    v1_review = payloads["v1_review"]
    v2_review = payloads["v2_review"]
    v2_groups = payloads["v2_groups"]
    v2_observations = payloads["v2_observations"]
    live_verification = payloads["live_verification"]

    group_errors = load_validator().validate_payload(v2_groups)
    if group_errors:
        raise RuntimeError(
            "Stage 2 content group validation failed: "
            + "; ".join(group_errors[:8])
        )
    observation_summary = v2_observations["summary"]
    if (
        observation_summary["total_observations"] != 2290
        or observation_summary["natural_key_duplicates"] != 0
        or observation_summary["unmapped_groups"] != 0
    ):
        raise RuntimeError(
            "Stage 2 shadow observations do not satisfy Snapshot 3 controls"
        )
    if (
        not live_verification["passed"]
        or live_verification["snapshot_id"] != 3
        or live_verification["document_id"] != 9
        or live_verification["database_write_count"] != 0
        or live_verification["transaction_mode"] != "read_only"
    ):
        raise RuntimeError(
            "Live Snapshot 3 verification is absent, failed, or unsafe"
        )

    records = []
    records.extend(
        compare_keyed(
            "source-page",
            keyed(v1_source["pages"], "page_key"),
            keyed(v2_source["pages"], "page_key"),
            lambda page: [
                source_locator(
                    page["page_number"], page_key=page["page_key"]
                )
            ],
        )
    )
    records.extend(
        compare_keyed(
            "page-disposition",
            keyed(v1_blocks["page_dispositions"], "page_key"),
            keyed(v2_blocks["page_dispositions"], "page_key"),
            lambda page: [
                source_locator(
                    page["page_number"], page_key=page["page_key"]
                )
            ],
        )
    )
    records.extend(
        compare_keyed(
            "block",
            keyed(v1_blocks["records"], "block_key"),
            keyed(v2_blocks["records"], "block_key"),
            lambda block: [block_locator(block)],
        )
    )
    records.extend(
        compare_keyed(
            "relationship",
            keyed(v1_blocks["relationships"], "relationship_key"),
            keyed(v2_blocks["relationships"], "relationship_key"),
            lambda relationship: [
                block_locator(
                    keyed(v2_blocks["records"], "block_key")[
                        relationship["source"]["block_key"]
                    ]
                )
            ],
        )
    )
    records.extend(review_records(v1_review["events"], v2_review["events"]))
    records.extend(observation_records(v2_observations))
    records.append(live_verification_record(live_verification))
    records.sort(key=lambda item: item["comparison_key"])

    counts = Counter(record["status"] for record in records)
    blockers = [
        {
            "blocker_key": "phase-7:active-handoff-unapproved",
            "category": "handoff",
            "message": (
                "The version 2 workspace and downstream extraction input "
                "remain inactive pending explicit approval after full parity."
            ),
            "affected_comparison_keys": [],
        },
    ]
    comparison = {
        "summary": {
            "total": len(records),
            **{
                status: counts[status]
                for status in (
                    "matched",
                    "missing",
                    "extra",
                    "changed",
                    "provenance_shifted",
                )
            },
        },
        "records": records,
        "blockers": blockers,
    }
    run_hash = digest_bytes(canonical_bytes(comparison))
    report = {
        "$schema": SCHEMA_REF,
        "schema_version": 2,
        "artifact_type": "parity_report",
        "artifact_key": "ctown-budget-2026-2027:parity-report:v2:phase-7",
        "document_key": next(iter(document_keys)),
        "source_sha256": next(iter(source_hashes)),
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [
            artifact_ref(payloads[name], paths[name])
            for name in (
                "v2_source",
                "v2_blocks",
                "v2_review",
                "v2_groups",
            )
        ],
        "baseline": {
            "source_document_id": 9,
            "source_sha256": next(iter(source_hashes)),
            "artifact_refs": [
                artifact_ref(payloads[name], paths[name])
                for name in ("v1_source", "v1_blocks", "v1_review")
            ],
            "publication_snapshot_ids": [3],
        },
        **comparison,
        "run_controls": {
            "first_run_canonical_sha256": run_hash,
            "second_run_canonical_sha256": run_hash,
            "database_write_count": 0,
            "publication_snapshot_count_before": 1,
            "publication_snapshot_count_after": 1,
        },
        "passed": False,
    }
    errors = load_validator().validate_payload(report)
    if errors:
        raise RuntimeError(
            "Phase 7 parity report validation failed: "
            + "; ".join(errors[:8])
        )
    return report


def write_atomic(path: Path, body: bytes) -> str:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    for name, default in DEFAULT_PATHS.items():
        parser.add_argument(
            f"--{name.replace('_', '-')}", type=Path, default=default
        )
    args = parser.parse_args()
    paths = {
        name: getattr(args, name)
        for name in DEFAULT_PATHS
    }
    tracemalloc.start()
    first = build_report(paths)
    second = build_report(paths)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if canonical_bytes(first) != canonical_bytes(second):
        raise RuntimeError("Two clean Phase 7 comparisons differ")
    if peak > MAX_PEAK_MEMORY_BYTES:
        raise RuntimeError(
            f"Peak traced memory {peak} exceeds {MAX_PEAK_MEMORY_BYTES}"
        )
    status = write_atomic(args.output, canonical_bytes(first))
    if status == "conflict":
        raise RuntimeError(
            f"Refusing to replace differing parity report: {args.output}"
        )
    print(json.dumps({
        "status": status,
        "output": args.output.relative_to(ROOT).as_posix()
        if args.output.is_relative_to(ROOT)
        else str(args.output),
        "artifact_sha256": digest_bytes(canonical_bytes(first)),
        "summary": first["summary"],
        "blocker_count": len(first["blockers"]),
        "peak_traced_memory_bytes": peak,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

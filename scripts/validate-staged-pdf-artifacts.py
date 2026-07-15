#!/usr/bin/env python3
"""Validate staged PDF artifacts against JSON Schema and cross-record invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "json-schema" / "staged-pdf-artifacts.schema.json"
DOCUMENT_ARTIFACT_TYPES = {
    "source_evidence",
    "block_inventory",
    "content_groups",
    "template_applications",
    "review_decisions",
    "parity_report",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_validator() -> Draft202012Validator:
    schema = read_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def location(parts: Iterable[object]) -> str:
    values = [str(part) for part in parts]
    return "$" if not values else "$." + ".".join(values)


def duplicates(values: Iterable[object]) -> list[object]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def check_box(box: dict[str, Any], path: str, errors: list[str]) -> None:
    if box["x0"] >= box["x1"]:
        errors.append(f"{path}: x0 must be less than x1")
    if box["y0"] >= box["y1"]:
        errors.append(f"{path}: y0 must be less than y1")


def check_source_evidence(payload: dict[str, Any], errors: list[str]) -> None:
    source = payload["source"]
    pages = payload["pages"]
    if source["sha256"] != payload["source_sha256"]:
        errors.append("$.source.sha256: must equal $.source_sha256")
    if source["page_count"] != len(pages):
        errors.append("$.source.page_count: must equal the number of page records")
    page_numbers = [page["page_number"] for page in pages]
    if page_numbers != list(range(1, source["page_count"] + 1)):
        errors.append("$.pages: page_number values must be consecutive and ordered from 1")
    for field, values in {
        "page_key": [page["page_key"] for page in pages],
        "page_number": page_numbers,
    }.items():
        found = duplicates(values)
        if found:
            errors.append(f"$.pages: duplicate {field} values: {found}")
    for index, page in enumerate(pages):
        check_box(page["media_box"], f"$.pages.{index}.media_box", errors)
        check_box(page["crop_box"], f"$.pages.{index}.crop_box", errors)


def validate_referenced_files(payload: dict[str, Any]) -> list[str]:
    """Verify source-evidence repository paths and recorded content hashes."""
    if payload.get("artifact_type") != "source_evidence":
        return []
    references: list[tuple[str, str, str]] = [
        ("$.source.repo_relpath", payload["source"]["repo_relpath"], payload["source"]["sha256"])
    ]
    for index, page in enumerate(payload["pages"]):
        references.extend(
            [
                (
                    f"$.pages.{index}.render.repo_relpath",
                    page["render"]["repo_relpath"],
                    page["render"]["sha256"],
                ),
                (
                    f"$.pages.{index}.thumbnail.repo_relpath",
                    page["thumbnail"]["repo_relpath"],
                    page["thumbnail"]["sha256"],
                ),
                (
                    f"$.pages.{index}.embedded_text.evidence_relpath",
                    page["embedded_text"]["evidence_relpath"],
                    page["embedded_text"]["sha256"],
                ),
            ]
        )
        ocr = page["ocr"]
        if ocr["evidence_relpath"] is not None and ocr["sha256"] is not None:
            references.append(
                (
                    f"$.pages.{index}.ocr.evidence_relpath",
                    ocr["evidence_relpath"],
                    ocr["sha256"],
                )
            )
    errors: list[str] = []
    root = ROOT.resolve()
    for field, repo_relpath, expected_hash in references:
        target = (root / repo_relpath).resolve()
        if not target.is_relative_to(root):
            errors.append(f"{field}: resolved outside repository")
        elif not target.is_file():
            errors.append(f"{field}: referenced file does not exist: {repo_relpath}")
        else:
            actual_hash = sha256_path(target)
            if actual_hash != expected_hash:
                errors.append(
                    f"{field}: SHA-256 mismatch for {repo_relpath}; "
                    f"expected {expected_hash}, found {actual_hash}"
                )
    return errors


def check_block_inventory(payload: dict[str, Any], errors: list[str]) -> None:
    pages = payload["page_dispositions"]
    records = payload["records"]
    block_keys = [record["block_key"] for record in records]
    page_keys = [page["page_key"] for page in pages]
    for field, values in {
        "block_key": block_keys,
        "page disposition key": page_keys,
        "page disposition number": [page["page_number"] for page in pages],
    }.items():
        found = duplicates(values)
        if found:
            errors.append(f"$: duplicate {field} values: {found}")
    known_blocks = set(block_keys)
    blocks_by_key = {record["block_key"]: record for record in records}
    region_owners: dict[str, str] = {}
    listed_blocks: list[str] = []
    page_key_set = set(page_keys)
    for index, page in enumerate(pages):
        listed_blocks.extend(page["block_keys"])
        unknown = sorted(set(page["block_keys"]) - known_blocks)
        if unknown:
            errors.append(f"$.page_dispositions.{index}.block_keys: unknown keys: {unknown}")
    if sorted(listed_blocks) != sorted(block_keys):
        errors.append("$.page_dispositions: block_keys must account for every block exactly once")
    for index, record in enumerate(records):
        if record["page_key"] not in page_key_set:
            errors.append(f"$.records.{index}.page_key: unknown page key")
        check_box(record["bbox"], f"$.records.{index}.bbox", errors)
        allowed_regions = {
            "formatted_text": {"paragraph", "bullet_list", "sorted_list"},
            "table": {"table_header", "column_label", "row_label", "cell", "subtotal", "total"},
        }.get(record["block_type"], set())
        for region_index, region in enumerate(record["regions"]):
            region_key = region["region_key"]
            if region_key in region_owners:
                errors.append(f"$.records.{index}.regions.{region_index}.region_key: duplicate region key")
            region_owners[region_key] = record["block_key"]
            check_box(region["bbox"], f"$.records.{index}.regions.{region_index}.bbox", errors)
            if region["region_type"] not in allowed_regions:
                errors.append(
                    f"$.records.{index}.regions.{region_index}.region_type: not allowed for {record['block_type']}"
                )
            block_box = record["bbox"]
            region_box = region["bbox"]
            if not (
                block_box["x0"] <= region_box["x0"] < region_box["x1"] <= block_box["x1"]
                and block_box["y0"] <= region_box["y0"] < region_box["y1"] <= block_box["y1"]
            ):
                errors.append(f"$.records.{index}.regions.{region_index}.bbox: must be inside parent block")
        for anchor_index, anchor in enumerate(record["anchors"]):
            check_box(anchor["bbox"], f"$.records.{index}.anchors.{anchor_index}.bbox", errors)
    relationship_keys = [relationship["relationship_key"] for relationship in payload["relationships"]]
    found = duplicates(relationship_keys)
    if found:
        errors.append(f"$.relationships: duplicate relationship_key values: {found}")
    for index, relationship in enumerate(payload["relationships"]):
        endpoints: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        for name in ("source", "target"):
            endpoint = relationship[name]
            block = blocks_by_key.get(endpoint["block_key"])
            endpoints.append((endpoint, block))
            if block is None:
                errors.append(f"$.relationships.{index}.{name}.block_key: unknown block")
            elif endpoint["region_key"] is not None and region_owners.get(endpoint["region_key"]) != endpoint["block_key"]:
                errors.append(f"$.relationships.{index}.{name}.region_key: unknown for endpoint block")
        source, target = endpoints
        if source[1] is None or target[1] is None:
            continue
        relation_type = relationship["relationship_type"]
        if relation_type == "graph_source_table" and not (
            source[1]["block_type"] == "chart" and target[1]["block_type"] == "table"
        ):
            errors.append(f"$.relationships.{index}: graph source relationships require chart to table")
        elif relation_type == "table_continuation" and not (
            source[1]["block_type"] == "table" and target[1]["block_type"] == "table"
            and source[1]["page_number"] != target[1]["page_number"]
        ):
            errors.append(f"$.relationships.{index}: table continuation requires tables on different pages")
        elif relation_type == "overview_detail" and not (
            source[1]["block_type"] == "table" and source[0]["region_key"] is not None
            and target[1]["block_type"] == "table"
        ):
            errors.append(f"$.relationships.{index}: overview detail requires a table region linked to a table")


def check_content_groups(payload: dict[str, Any], errors: list[str]) -> None:
    groups = payload["records"]
    group_keys = [group["group_key"] for group in groups]
    found = duplicates(group_keys)
    if found:
        errors.append(f"$.records: duplicate group_key values: {found}")
    group_key_set = set(group_keys)
    primary_owners: list[str] = []
    for index, group in enumerate(groups):
        if group["page_start"] > group["page_end"]:
            errors.append(f"$.records.{index}: page_start must not exceed page_end")
        members = group["members"]
        member_keys = [member["block_key"] for member in members]
        member_set = set(member_keys)
        if duplicates(member_keys):
            errors.append(f"$.records.{index}.members: duplicate block keys")
        orders = [member["order"] for member in members]
        if sorted(orders) != list(range(1, len(members) + 1)):
            errors.append(f"$.records.{index}.members: order must be consecutive from 1")
        primary_owners.extend(
            member["block_key"] for member in members if member["ownership"] == "primary"
        )
        for edge_index, edge in enumerate(group["continuation_edges"]):
            if edge["from_block_key"] not in member_set or edge["to_block_key"] not in member_set:
                errors.append(
                    f"$.records.{index}.continuation_edges.{edge_index}: edge endpoints must be group members"
                )
        for header_index, header in enumerate(group["inherited_headers"]):
            if (
                header["target_block_key"] not in member_set
                or header["source_block_key"] not in member_set
            ):
                errors.append(
                    f"$.records.{index}.inherited_headers.{header_index}: header endpoints must be group members"
                )
        for relation_index, relation in enumerate(group["relationships"]):
            if relation["target_group_key"] not in group_key_set:
                errors.append(
                    f"$.records.{index}.relationships.{relation_index}: unknown target group"
                )
    found = duplicates(primary_owners)
    if found:
        errors.append(f"$.records: blocks have multiple primary owners: {found}")


def check_structural_template(payload: dict[str, Any], errors: list[str]) -> None:
    for index, anchor in enumerate(payload["anchors"]):
        check_box(anchor["region"], f"$.anchors.{index}.region", errors)
    unique_fields = {
        "anchors": ("anchor_key", payload["anchors"]),
        "block_rules": ("rule_key", payload["block_rules"]),
        "column_bands": ("column_key", payload["column_bands"]),
        "continuation_rules": ("rule_key", payload["continuation_rules"]),
        "termination_rules": ("rule_key", payload["termination_rules"]),
        "negative_controls": ("control_key", payload["negative_controls"]),
        "regression_controls": ("control_key", payload["regression_controls"]),
    }
    for path, (field, records) in unique_fields.items():
        found = duplicates(record[field] for record in records)
        if found:
            errors.append(f"$.{path}: duplicate {field} values: {found}")
    anchor_keys = {anchor["anchor_key"] for anchor in payload["anchors"]}
    unknown_headers = sorted(set(payload["header_policy"]["source_anchor_keys"]) - anchor_keys)
    if unknown_headers:
        errors.append(f"$.header_policy.source_anchor_keys: unknown anchors: {unknown_headers}")
    for index, rule in enumerate(payload["block_rules"]):
        maximum = rule["maximum_count"]
        if maximum is not None and rule["minimum_count"] > maximum:
            errors.append(f"$.block_rules.{index}: minimum_count must not exceed maximum_count")
    for index, column in enumerate(payload["column_bands"]):
        if column["x0"] >= column["x1"]:
            errors.append(f"$.column_bands.{index}: x0 must be less than x1")


def check_template_applications(payload: dict[str, Any], errors: list[str]) -> None:
    records = payload["records"]
    for field in ["application_key", "group_key"]:
        found = duplicates(record[field] for record in records)
        if found:
            errors.append(f"$.records: duplicate {field} values: {found}")
    for index, record in enumerate(records):
        material = [
            mismatch for mismatch in record["mismatches"] if mismatch["severity"] == "material"
        ]
        if record["fit_class"] == "material_variation" and not material:
            errors.append(
                f"$.records.{index}.mismatches: material variation requires a material mismatch"
            )
        if record["fit_class"] in {"exact", "light_variation"} and material:
            errors.append(
                f"$.records.{index}.mismatches: accepted fit classes cannot contain material mismatches"
            )


def check_review_decisions(payload: dict[str, Any], errors: list[str]) -> None:
    events = payload["events"]
    found = duplicates(event["decision_id"] for event in events)
    if found:
        errors.append(f"$.events: duplicate decision_id values: {found}")
    if [event["sequence"] for event in events] != list(range(1, len(events) + 1)):
        errors.append("$.events: sequence must be consecutive and ordered from 1")
    previous_hash: str | None = None
    for index, event in enumerate(events):
        if event["previous_event_sha256"] != previous_hash:
            errors.append(
                f"$.events.{index}.previous_event_sha256: does not match prior event hash"
            )
        previous_hash = event["event_sha256"]


def check_parity_report(payload: dict[str, Any], errors: list[str]) -> None:
    records = payload["records"]
    summary = payload["summary"]
    found = duplicates(record["comparison_key"] for record in records)
    if found:
        errors.append(f"$.records: duplicate comparison_key values: {found}")
    counts = Counter(record["status"] for record in records)
    if summary["total"] != len(records):
        errors.append("$.summary.total: must equal the number of parity records")
    for status in ["matched", "missing", "extra", "changed", "provenance_shifted"]:
        if summary[status] != counts[status]:
            errors.append(f"$.summary.{status}: does not match parity record count")
    controls = payload["run_controls"]
    if payload["passed"]:
        if payload["blockers"]:
            errors.append("$.blockers: must be empty when passed is true")
        if controls["first_run_canonical_sha256"] != controls["second_run_canonical_sha256"]:
            errors.append("$.run_controls: canonical run hashes must match when passed is true")
        if controls["database_write_count"] != 0:
            errors.append("$.run_controls.database_write_count: must be zero when passed is true")
        if (
            controls["publication_snapshot_count_before"]
            != controls["publication_snapshot_count_after"]
        ):
            errors.append("$.run_controls: publication snapshot count changed on a passed run")


SEMANTIC_CHECKS = {
    "source_evidence": check_source_evidence,
    "block_inventory": check_block_inventory,
    "content_groups": check_content_groups,
    "structural_template": check_structural_template,
    "template_applications": check_template_applications,
    "review_decisions": check_review_decisions,
    "parity_report": check_parity_report,
}


def validate_payload(
    payload: dict[str, Any], validator: Draft202012Validator | None = None
) -> list[str]:
    validator = validator or load_validator()
    errors = [
        f"{location(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]
    artifact_type = payload.get("artifact_type")
    if not errors and artifact_type in SEMANTIC_CHECKS:
        SEMANTIC_CHECKS[artifact_type](payload, errors)
    return errors


def validate_artifact_set(payloads: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    document_payloads = [
        payload for payload in payloads if payload.get("artifact_type") in DOCUMENT_ARTIFACT_TYPES
    ]
    document_keys = {payload["document_key"] for payload in document_payloads}
    source_hashes = {payload["source_sha256"] for payload in document_payloads}
    if len(document_keys) > 1:
        errors.append(f"artifact set: multiple document keys: {sorted(document_keys)}")
    if len(source_hashes) > 1:
        errors.append(f"artifact set: multiple source hashes: {sorted(source_hashes)}")

    by_type: dict[str, list[dict[str, Any]]] = {}
    for payload in payloads:
        by_type.setdefault(payload["artifact_type"], []).append(payload)

    def single(artifact_type: str) -> dict[str, Any] | None:
        matches = by_type.get(artifact_type, [])
        if len(matches) > 1:
            errors.append(f"artifact set: multiple {artifact_type} artifacts")
        return matches[0] if matches else None

    source = single("source_evidence")
    blocks = single("block_inventory")
    groups = single("content_groups")
    applications = single("template_applications")
    parity = single("parity_report")
    templates = by_type.get("structural_template", [])

    if source and blocks:
        source_pages = {page["page_key"] for page in source["pages"]}
        block_pages = {page["page_key"] for page in blocks["page_dispositions"]}
        if source_pages != block_pages:
            errors.append("artifact set: source and block inventory page keys differ")
    if blocks and groups:
        block_keys = {record["block_key"] for record in blocks["records"]}
        used = {
            member["block_key"]
            for group in groups["records"]
            for member in group["members"]
        }
        unknown = sorted(used - block_keys)
        if unknown:
            errors.append(f"artifact set: groups reference unknown blocks: {unknown}")
    if groups and applications:
        group_keys = {record["group_key"] for record in groups["records"]}
        unknown = sorted(
            {record["group_key"] for record in applications["records"]} - group_keys
        )
        if unknown:
            errors.append(f"artifact set: applications reference unknown groups: {unknown}")
    if templates and applications:
        expected = {
            (template["template_key"], template["template_version"])
            for template in templates
        }
        wrong = sorted(
            record["application_key"]
            for record in applications["records"]
            if (record["template_key"], record["template_version"]) not in expected
        )
        if wrong:
            errors.append(f"artifact set: applications reference unknown templates: {wrong}")
    if source and parity and parity["baseline"]["source_sha256"] != source["source_sha256"]:
        errors.append("artifact set: parity baseline source hash differs from source evidence")
    return errors


def expand_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(sorted(path.rglob("*.json")))
        else:
            expanded.append(path)
    return expanded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()

    validator = load_validator()
    if args.schema_only:
        print(f"Valid Draft 2020-12 schema: {SCHEMA_PATH.relative_to(ROOT)}")
        return 0
    if not args.paths:
        parser.error("provide one or more artifact files or directories, or use --schema-only")

    failures: list[str] = []
    payloads: list[dict[str, Any]] = []
    for path in expand_paths(args.paths):
        payload = read_json(path)
        payload_errors = validate_payload(payload, validator)
        for error in payload_errors:
            failures.append(f"{path}: {error}")
        if not payload_errors:
            payloads.append(payload)
            for error in validate_referenced_files(payload):
                failures.append(f"{path}: {error}")
    for error in validate_artifact_set(payloads):
        failures.append(error)

    if failures:
        for failure in failures:
            print(failure)
        return 1
    print(f"Validated {len(payloads)} staged PDF artifact files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
SCHEMA_PATHS = {
    1: ROOT / "schema" / "json-schema" / "staged-pdf-artifacts.schema.json",
    2: ROOT / "schema" / "json-schema" / "staged-pdf-artifacts-v2.schema.json",
}
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


def schema_path(schema_version: int) -> Path:
    try:
        return SCHEMA_PATHS[schema_version]
    except KeyError as error:
        raise ValueError(f"Unsupported staged PDF schema version: {schema_version}") from error


def load_validator(schema_version: int = 1) -> Draft202012Validator:
    schema = read_json(schema_path(schema_version))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def load_component_validator(
    definition: str, schema_version: int = 1
) -> Draft202012Validator:
    return load_component_validators([definition], schema_version)[definition]


def load_component_validators(
    definitions: Iterable[str], schema_version: int = 1
) -> dict[str, Draft202012Validator]:
    schema = read_json(schema_path(schema_version))
    validators: dict[str, Draft202012Validator] = {}
    for definition in definitions:
        if definition not in schema["$defs"]:
            raise ValueError(f"Unknown schema definition: {definition}")
        component_schema = {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
        validators[definition] = Draft202012Validator(component_schema, format_checker=FormatChecker())
    return validators


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


def effective_span(cell: dict[str, Any], axis: str) -> int:
    return int(cell.get(f"{axis}_span", 1))


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
    internal_items: dict[str, dict[str, Any]] = {}
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
        formatted_regions = {"paragraph", "bullet_list", "sorted_list"}
        if payload.get("schema_version") == 2:
            formatted_regions.add("title")
        allowed_regions = {
            "formatted_text": formatted_regions,
        }.get(record["block_type"], set())
        for region_index, region in enumerate(record["regions"]):
            region_key = region["region_key"]
            if region_key in region_owners:
                errors.append(f"$.records.{index}.regions.{region_index}.region_key: duplicate region key")
            region_owners[region_key] = record["block_key"]
            internal_items[region_key] = region
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
        grid = record["table_grid"]
        if record["block_type"] == "table" and grid is None:
            errors.append(f"$.records.{index}.table_grid: table blocks require a grid")
        elif record["block_type"] != "table" and grid is not None:
            errors.append(f"$.records.{index}.table_grid: only table blocks can have a grid")
        elif grid is not None:
            columns = grid["column_boundaries"]
            rows = grid["row_boundaries"]
            if any(left >= right for left, right in zip(columns, columns[1:])):
                errors.append(f"$.records.{index}.table_grid.column_boundaries: must be strictly increasing")
            if any(top >= bottom for top, bottom in zip(rows, rows[1:])):
                errors.append(f"$.records.{index}.table_grid.row_boundaries: must be strictly increasing")
            block_box = record["bbox"]
            if columns[0] != block_box["x0"] or columns[-1] != block_box["x1"]:
                errors.append(f"$.records.{index}.table_grid.column_boundaries: outer boundaries must equal block bbox")
            if rows[0] != block_box["y0"] or rows[-1] != block_box["y1"]:
                errors.append(f"$.records.{index}.table_grid.row_boundaries: outer boundaries must equal block bbox")
            expected_coordinates = {
                (row, column)
                for row in range(len(rows) - 1)
                for column in range(len(columns) - 1)
            }
            if payload.get("schema_version") == 2:
                covered_coordinates: list[tuple[int, int]] = []
                table_titles: list[dict[str, Any]] = []
                for cell in grid["cells"]:
                    row_start = cell["row_index"]
                    column_start = cell["column_index"]
                    row_span = effective_span(cell, "row")
                    column_span = effective_span(cell, "column")
                    covered_coordinates.extend(
                        (row, column)
                        for row in range(row_start, row_start + row_span)
                        for column in range(column_start, column_start + column_span)
                    )
                    if cell["cell_type"] == "table_title":
                        table_titles.append(cell)
                actual_coordinates = set(covered_coordinates)
                if (
                    actual_coordinates != expected_coordinates
                    or len(covered_coordinates) != len(actual_coordinates)
                ):
                    errors.append(
                        f"$.records.{index}.table_grid.cells: effective spans must cover every row and column exactly once"
                    )
                if len(table_titles) > 1:
                    errors.append(f"$.records.{index}.table_grid.cells: table requires at most one table_title")
                for title in table_titles:
                    row_end = title["row_index"] + effective_span(title, "row")
                    if title["column_index"] != 0 or effective_span(title, "column") != len(columns) - 1:
                        errors.append(f"$.records.{index}.table_grid.cells: table_title must span the complete table width")
                    if title["row_index"] != 0 and row_end != len(rows) - 1:
                        errors.append(f"$.records.{index}.table_grid.cells: table_title must be at the top or bottom boundary")
            else:
                actual_coordinates = {(cell["row_index"], cell["column_index"]) for cell in grid["cells"]}
                if actual_coordinates != expected_coordinates or len(grid["cells"]) != len(expected_coordinates):
                    errors.append(f"$.records.{index}.table_grid.cells: must contain one cell for every row and column")
            cell_keys = [cell["cell_key"] for cell in grid["cells"]]
            if duplicates(cell_keys):
                errors.append(f"$.records.{index}.table_grid.cells: duplicate cell keys")
            for cell in grid["cells"]:
                if cell["cell_key"] in region_owners:
                    errors.append(f"$.records.{index}.table_grid.cells: duplicate internal key")
                region_owners[cell["cell_key"]] = record["block_key"]
                internal_items[cell["cell_key"]] = cell
        for anchor_index, anchor in enumerate(record["anchors"]):
            check_box(anchor["bbox"], f"$.records.{index}.anchors.{anchor_index}.bbox", errors)
    if payload.get("schema_version") == 2:
        sibling_titles = {
            (record["page_key"], tuple(record["bbox"][key] for key in ("x0", "y0", "x1", "y1")))
            for record in records
            if record["block_type"] == "title"
        }
        for record_index, record in enumerate(records):
            for region_index, region in enumerate(record["regions"]):
                identity = (
                    record["page_key"],
                    tuple(region["bbox"][key] for key in ("x0", "y0", "x1", "y1")),
                )
                if region["region_type"] == "title" and identity in sibling_titles:
                    errors.append(
                        f"$.records.{record_index}.regions.{region_index}: internal title duplicates sibling title geometry"
                    )
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
            source[1]["block_type"] == "chart" and source[0]["region_key"] is None
            and target[1]["block_type"] == "table" and target[0]["region_key"] is None
        ):
            errors.append(f"$.relationships.{index}: graph source relationships require a whole chart linked to a whole table")
        elif relation_type == "table_continuation" and not (
            source[1]["block_type"] == "table" and target[1]["block_type"] == "table"
            and source[0]["region_key"] is None and target[0]["region_key"] is None
            and source[1]["page_number"] != target[1]["page_number"]
        ):
            errors.append(f"$.relationships.{index}: table continuation requires whole tables on different pages")
        elif relation_type == "overview_detail" and not (
            source[1]["block_type"] == "table" and source[0]["region_key"] is not None
            and internal_items.get(source[0]["region_key"], {}).get("cell_type") == "row_label"
            and target[1]["block_type"] == "table" and target[0]["region_key"] is None
            and source[0]["block_key"] != target[0]["block_key"]
        ):
            errors.append(f"$.relationships.{index}: overview detail requires a row-label cell linked to a different whole detail table")


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
    if payload.get("schema_version") == 2:
        unique_fields["internal_region_rules"] = (
            "rule_key",
            payload["internal_region_rules"],
        )
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
    if payload.get("schema_version") == 2:
        for index, rule in enumerate(payload["internal_region_rules"]):
            maximum = rule["maximum_count"]
            if maximum is not None and rule["minimum_count"] > maximum:
                errors.append(
                    f"$.internal_region_rules.{index}: minimum_count must not exceed maximum_count"
                )
        title_policy = payload["table_title_policy"]
        unknown_title_anchors = sorted(set(title_policy["anchor_keys"]) - anchor_keys)
        if unknown_title_anchors:
            errors.append(
                f"$.table_title_policy.anchor_keys: unknown anchors: {unknown_title_anchors}"
            )
        if title_policy["mode"] == "absent" and title_policy["allowed_positions"]:
            errors.append(
                "$.table_title_policy.allowed_positions: must be empty when mode is absent"
            )
        if title_policy["mode"] != "absent" and not title_policy["allowed_positions"]:
            errors.append(
                "$.table_title_policy.allowed_positions: must identify top or bottom when title is allowed"
            )
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
        if payload.get("schema_version") == 2:
            evaluation = record["policy_evaluation"]
            if evaluation["policy_ref"] is not None and evaluation["policy_ref"]["schema_version"] != 2:
                errors.append(
                    f"$.records.{index}.policy_evaluation.policy_ref: must reference version 2 policy"
                )
            if record["fit_class"] == "material_variation" and evaluation["outcome"] not in {
                "review_required",
                "blocked",
            }:
                errors.append(
                    f"$.records.{index}.policy_evaluation.outcome: material variation cannot be automatically approved"
                )
            if evaluation["outcome"] == "auto_approved":
                if evaluation["policy_ref"] is None:
                    errors.append(
                        f"$.records.{index}.policy_evaluation.policy_ref: automatic approval requires a policy"
                    )
                if not evaluation["fit_eligible"]:
                    errors.append(
                        f"$.records.{index}.policy_evaluation.fit_eligible: automatic approval requires eligible fit"
                    )
                if record["review"]["status"] != "approved" or not record["review"]["decision_ids"]:
                    errors.append(
                        f"$.records.{index}.review: automatic approval requires approved status and a decision"
                    )
            if evaluation["outcome"] == "selected_for_sample" and record["review"]["status"] != "needs_review":
                errors.append(
                    f"$.records.{index}.review.status: sampled application must need review"
                )


def check_template_review_policy(payload: dict[str, Any], errors: list[str]) -> None:
    binding = payload["template_binding"]
    if binding["artifact_ref"]["artifact_type"] != "structural_template":
        errors.append("$.template_binding.artifact_ref: must reference structural_template")
    if binding["artifact_ref"]["schema_version"] != 2:
        errors.append("$.template_binding.artifact_ref: policy requires a version 2 template")
    supersedes = payload["supersedes_policy_ref"]
    if supersedes is not None and supersedes["artifact_type"] != "template_review_policy":
        errors.append("$.supersedes_policy_ref: must reference template_review_policy")
    evidence = payload["promotion_evidence"]
    reviewed = evidence["reviewed_application_count"]
    accepted = evidence["accepted_application_count"]
    rejected = evidence["rejected_application_count"]
    if accepted + rejected != reviewed:
        errors.append(
            "$.promotion_evidence: accepted and rejected counts must equal reviewed application count"
        )
    expected_precision = accepted / reviewed if reviewed else None
    observed_precision = evidence["observed_precision"]
    if expected_precision is None:
        if observed_precision is not None:
            errors.append("$.promotion_evidence.observed_precision: must be null with no reviewed applications")
    elif observed_precision is None or abs(observed_precision - expected_precision) > 1e-9:
        errors.append("$.promotion_evidence.observed_precision: must equal accepted divided by reviewed")
    if payload["status"] == "approved" and payload["mode"] != "review_required":
        gates = payload["promotion_gates"]
        checks = [
            (len(evidence["positive_application_keys"]) >= gates["minimum_positive_examples"], "positive examples"),
            (len(evidence["negative_control_keys"]) >= gates["minimum_negative_controls"], "negative controls"),
            (reviewed >= gates["minimum_reviewed_applications"], "reviewed applications"),
            (observed_precision is not None and observed_precision >= gates["minimum_observed_precision"], "observed precision"),
            (evidence["false_approval_count"] <= gates["maximum_false_approvals"], "false approvals"),
        ]
        for passed, label in checks:
            if not passed:
                errors.append(f"$.promotion_evidence: approved policy does not meet {label} gate")


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
        if payload.get("schema_version") == 2:
            policy_ref = event["policy_ref"]
            if policy_ref is not None and policy_ref["artifact_type"] != "template_review_policy":
                errors.append(f"$.events.{index}.policy_ref: must reference template_review_policy")
            if policy_ref is not None and policy_ref["schema_version"] != 2:
                errors.append(f"$.events.{index}.policy_ref: must reference version 2 policy")
            if event["decision_basis"] == "template_policy":
                if policy_ref is None:
                    errors.append(f"$.events.{index}.policy_ref: template policy decision requires a policy")
                if event["reviewer"]["actor_type"] != "system":
                    errors.append(f"$.events.{index}.reviewer.actor_type: template policy decision requires system actor")
            if event["action"] == "auto_approve" and event["decision_basis"] != "template_policy":
                errors.append(f"$.events.{index}.decision_basis: automatic approval requires template policy")
            if event["action"] == "promote_policy" and event["reviewer"]["actor_type"] != "human":
                errors.append(f"$.events.{index}.reviewer.actor_type: policy promotion requires human actor")


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
    "template_review_policy": check_template_review_policy,
    "template_applications": check_template_applications,
    "review_decisions": check_review_decisions,
    "parity_report": check_parity_report,
}


def validate_payload(
    payload: dict[str, Any], validator: Draft202012Validator | None = None
) -> list[str]:
    validator = validator or load_validator(int(payload.get("schema_version", 1)))
    errors = [
        f"{location(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]
    artifact_type = payload.get("artifact_type")
    if not errors and artifact_type in SEMANTIC_CHECKS:
        SEMANTIC_CHECKS[artifact_type](payload, errors)
    return errors


def validate_component(
    payload: Any, definition: str, validator: Draft202012Validator | None = None
) -> list[str]:
    validator = validator or load_component_validator(definition)
    return [
        f"{location(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]


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
    policies = by_type.get("template_review_policy", [])

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
    if templates and policies:
        templates_by_key = {
            (template["artifact_key"], template["template_key"], template["template_version"])
            for template in templates
        }
        wrong = sorted(
            policy["policy_key"]
            for policy in policies
            if (
                policy["template_binding"]["artifact_ref"]["artifact_key"],
                policy["template_binding"]["template_key"],
                policy["template_binding"]["template_version"],
            ) not in templates_by_key
        )
        if wrong:
            errors.append(f"artifact set: policies reference unknown templates: {wrong}")
    if policies and applications:
        policies_by_artifact = {policy["artifact_key"]: policy for policy in policies}
        for record in applications["records"]:
            evaluation = record.get("policy_evaluation")
            if not evaluation or evaluation["policy_ref"] is None:
                continue
            policy_ref = evaluation["policy_ref"]
            policy = policies_by_artifact.get(policy_ref["artifact_key"])
            if policy is None:
                errors.append(
                    f"artifact set: application {record['application_key']} references unknown policy"
                )
                continue
            binding = policy["template_binding"]
            if (
                record["template_key"] != binding["template_key"]
                or record["template_version"] != binding["template_version"]
                or record["template_artifact_sha256"] != binding["artifact_ref"]["sha256"]
            ):
                errors.append(
                    f"artifact set: application {record['application_key']} policy binds a different template"
                )
            if evaluation["matcher_config_sha256"] != policy["matcher"]["config_sha256"]:
                errors.append(
                    f"artifact set: application {record['application_key']} matcher configuration differs from policy"
                )
            if evaluation["outcome"] == "auto_approved":
                if policy["status"] != "approved" or policy["mode"] not in {"sample_review", "auto_approve"}:
                    errors.append(
                        f"artifact set: application {record['application_key']} automatic approval uses ineligible policy"
                    )
                if record["fit_class"] not in policy["eligible_fit_classes"]:
                    errors.append(
                        f"artifact set: application {record['application_key']} fit is not policy-eligible"
                    )
                light_categories = {
                    mismatch["category"]
                    for mismatch in record["mismatches"]
                    if mismatch["severity"] == "light"
                }
                if not light_categories.issubset(set(policy["allowed_light_mismatch_categories"])):
                    errors.append(
                        f"artifact set: application {record['application_key']} has non-allowlisted light mismatch"
                    )
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

    if args.schema_only:
        for version, path in sorted(SCHEMA_PATHS.items()):
            load_validator(version)
            print(f"Valid Draft 2020-12 schema v{version}: {path.relative_to(ROOT)}")
        return 0
    if not args.paths:
        parser.error("provide one or more artifact files or directories, or use --schema-only")

    failures: list[str] = []
    payloads: list[dict[str, Any]] = []
    for path in expand_paths(args.paths):
        payload = read_json(path)
        payload_errors = validate_payload(payload)
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

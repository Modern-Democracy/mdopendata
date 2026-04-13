from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOTS = (
    REPO_ROOT / "data" / "zoning",
    REPO_ROOT / "data" / "municipal-planning-strategy",
)

BYLAW_CROSSWALK = {
    "dartmouth": {
        "community_plan_name": "Dartmouth",
        "crosswalk_note": "Resolved by intersecting HFX_Halifax_Zoning_Boundaries with HFX_Community_Plan_Areas where PLAN_NAME = Dartmouth.",
    },
    "halifax-mainland": {
        "community_plan_name": "Halifax",
        "crosswalk_note": "Resolved by intersecting HFX_Halifax_Zoning_Boundaries with HFX_Community_Plan_Areas where PLAN_NAME = Halifax.",
    },
}


def db_env() -> tuple[str, str, str]:
    return (
        os.environ.get("PGCONTAINER", "mdopendata-postgis"),
        os.environ.get("PGDATABASE", "mdopendata"),
        os.environ.get("PGUSER", "mdopendata"),
    )


def psql(sql: str) -> None:
    container, database, user = db_env()
    (REPO_ROOT / ".docker-local").mkdir(exist_ok=True)
    env = os.environ.copy()
    env["DOCKER_CONFIG"] = str(REPO_ROOT / ".docker-local")
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        user,
        "-d",
        database,
    ]
    result = subprocess.run(
        command,
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)


def sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def sql_json(value: Any) -> str:
    return sql_text(json.dumps(value, ensure_ascii=True, sort_keys=True)) + "::jsonb"


def sql_array(values: list[str] | None) -> str:
    if not values:
        return "NULL"
    return "ARRAY[" + ", ".join(sql_text(value) for value in values) + "]"


def normalize_relpath(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def infer_section_kind(relpath: str) -> str:
    name = Path(relpath).name
    parent = Path(relpath).parent.name
    if parent == "zones":
        return "zone"
    if parent == "schedules":
        return "schedule"
    if name == "definitions.json":
        return "definitions"
    if name == "maps.json":
        return "maps"
    if name == "spatial-features-needed.json":
        return "spatial_features_needed"
    if name == "general-provisions.json":
        return "general_provisions"
    if name.startswith("appendix-"):
        return "appendix"
    return "document"


def infer_bylaw_metadata(payload: dict[str, Any], slug: str) -> dict[str, Any]:
    metadata = (
        payload.get("document_metadata")
        or payload.get("section_metadata")
        or payload.get("schedule_metadata")
        or {}
    )
    bylaw_name = (
        metadata.get("bylaw_name")
        or metadata.get("document_name")
        or payload.get("document_name")
        or slug.replace("-", " ").title()
    )
    jurisdiction = metadata.get("jurisdiction") or "Unknown"
    source_document_path = metadata.get("source_document_path") or payload.get("source_document_path")
    crosswalk = BYLAW_CROSSWALK.get(slug, {})
    return {
        "bylaw_slug": slug,
        "jurisdiction": jurisdiction,
        "bylaw_name": bylaw_name,
        "source_document_path": source_document_path,
        "existing_spatial_bylaw_id": crosswalk.get("existing_spatial_bylaw_id"),
        "metadata": {
            "community_plan_name": crosswalk.get("community_plan_name"),
            "crosswalk_note": crosswalk.get("crosswalk_note"),
        },
    }


def pages_json(payload: dict[str, Any]) -> dict[str, Any]:
    source = (
        payload.get("source_section")
        or payload.get("section_metadata")
        or payload.get("document_metadata")
        or payload.get("schedule_metadata")
        or {}
    )
    result: dict[str, Any] = {}
    for key in (
        "pdf_page",
        "pdf_page_start",
        "pdf_page_end",
        "bylaw_page",
        "bylaw_page_start",
        "bylaw_page_end",
        "mps_page_start",
        "mps_page_end",
        "section_range_raw",
    ):
        if key in source:
            result[key] = source[key]
    return result


def join_conditions(values: list[str] | None) -> str | None:
    if not values:
        return None
    return " | ".join(values)


def make_source_key(*parts: str | int | None) -> str:
    return "::".join(str(part) for part in parts if part not in (None, "", []))


def canonicalize_label(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def add_provision(
    provisions: list[dict[str, Any]],
    *,
    source_key: str,
    section_relpath: str,
    zone_code: str | None,
    provision_kind: str,
    section_label_raw: str | None,
    clause_label_raw: str | None,
    clause_path: list[str] | None,
    parent_clause_label_raw: str | None,
    text_value: str | None,
    status: str | None,
    citations_json: Any,
    metadata: dict[str, Any] | None = None,
) -> None:
    provisions.append(
        {
            "source_key": source_key,
            "section_relpath": section_relpath,
            "zone_code": zone_code,
            "provision_kind": provision_kind,
            "section_label_raw": section_label_raw,
            "clause_label_raw": clause_label_raw,
            "clause_path": clause_path,
            "parent_clause_label_raw": parent_clause_label_raw,
            "text_value": text_value,
            "status": status,
            "citations_json": citations_json or {},
            "metadata": metadata or {},
        }
    )


def add_rule(
    rules: list[dict[str, Any]],
    *,
    source_key: str,
    provision_source_key: str,
    bylaw_slug: str,
    zone_code: str | None,
    rule_type: str,
    metric: str | None = None,
    use_name: str | None = None,
    numeric_value: Any = None,
    value_text: str | None = None,
    unit: str | None = None,
    comparator: str | None = None,
    condition_text: str | None = None,
    applicability_scope: str | None = None,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    rules.append(
        {
            "source_key": source_key,
            "provision_source_key": provision_source_key,
            "bylaw_slug": bylaw_slug,
            "zone_code": zone_code,
            "rule_type": rule_type,
            "metric": metric,
            "use_name": use_name,
            "numeric_value": numeric_value,
            "value_text": value_text,
            "unit": unit,
            "comparator": comparator,
            "condition_text": condition_text,
            "applicability_scope": applicability_scope,
            "status": status,
            "metadata": metadata or {},
        }
    )


def collect_area_tokens(item: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in ("applicability_scope", "area_source_reference", "schedule_reference"):
        value = item.get(key)
        if not value:
            continue
        tokens.add(canonicalize_label(value) or "")
        if isinstance(value, str):
            tokens.add(value.lower().replace("-", "_").replace(" ", "_"))
    for key in ("area_name", "subarea_name"):
        value = item.get(key)
        token = canonicalize_label(value) if value else None
        if token:
            tokens.add(token)
    return {token for token in tokens if token}


def link_rule_to_spatial_refs(
    links: list[dict[str, str]],
    spatial_refs_by_bylaw: dict[str, list[dict[str, Any]]],
    *,
    bylaw_slug: str,
    rule_source_key: str,
    item: dict[str, Any],
) -> None:
    tokens = collect_area_tokens(item)
    if not tokens:
        return
    seen: set[str] = set()
    for spatial_ref in spatial_refs_by_bylaw.get(bylaw_slug, []):
        feature_key = (spatial_ref.get("feature_key") or "").lower().replace("-", "_")
        source_label = canonicalize_label(spatial_ref.get("source_label_raw"))
        schedule_file = canonicalize_label(spatial_ref.get("schedule_file"))
        candidates = {feature_key}
        if source_label:
            candidates.add(source_label)
        if schedule_file:
            candidates.add(schedule_file)
        if not any(token and any(token in candidate or candidate in token for candidate in candidates) for token in tokens):
            continue
        source_key = make_source_key("rule_spatial", rule_source_key, spatial_ref["source_key"])
        if source_key in seen:
            continue
        seen.add(source_key)
        links.append(
            {
                "source_key": source_key,
                "rule_source_key": rule_source_key,
                "spatial_source_key": spatial_ref["source_key"],
                "applicability_type": "applies_to",
                "priority_order": "50",
                "notes": "Inferred from area or schedule reference in source JSON.",
            }
        )


def insert_zone_rules(
    *,
    bylaw_slug: str,
    relpath: str,
    zone_code: str,
    payload: dict[str, Any],
    provisions: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    spatial_links: list[dict[str, str]],
    spatial_refs_by_bylaw: dict[str, list[dict[str, Any]]],
) -> None:
    def base_provision(item: dict[str, Any], provision_kind: str, index: int, text_value: str | None, metadata: dict[str, Any] | None = None) -> str:
        source_key = make_source_key(relpath, provision_kind, item.get("clause_label_raw"), item.get("section_label_raw"), index)
        add_provision(
            provisions,
            source_key=source_key,
            section_relpath=relpath,
            zone_code=zone_code,
            provision_kind=provision_kind,
            section_label_raw=item.get("section_label_raw"),
            clause_label_raw=item.get("clause_label_raw"),
            clause_path=item.get("clause_path"),
            parent_clause_label_raw=item.get("parent_clause_label_raw"),
            text_value=text_value,
            status=item.get("status"),
            citations_json=item.get("citations") or payload.get("citations") or {},
            metadata=metadata,
        )
        return source_key

    for index, item in enumerate(payload.get("permitted_uses", []), start=1):
        provision_key = base_provision(
            item,
            "permitted_use",
            index,
            item.get("use_name"),
            {"defined_term_refs": item.get("defined_term_refs"), "link_method": item.get("link_method")},
        )
        rule_key = make_source_key(provision_key, "rule", item.get("use_type"), index)
        add_rule(
            rules,
            source_key=rule_key,
            provision_source_key=provision_key,
            bylaw_slug=bylaw_slug,
            zone_code=zone_code,
            rule_type=item.get("use_type") or "permitted_use",
            use_name=item.get("use_name"),
            condition_text=join_conditions(item.get("conditions")),
            applicability_scope=item.get("applicability_scope"),
            status=item.get("status"),
            metadata={"linked_sections": item.get("linked_sections"), "defined_term_refs": item.get("defined_term_refs")},
        )
        link_rule_to_spatial_refs(spatial_links, spatial_refs_by_bylaw, bylaw_slug=bylaw_slug, rule_source_key=rule_key, item=item)

    for index, item in enumerate(payload.get("prohibitions", []), start=1):
        provision_key = base_provision(item, "prohibition", index, item.get("summary"))
        add_rule(
            rules,
            source_key=make_source_key(provision_key, "rule", item.get("rule_type"), index),
            provision_source_key=provision_key,
            bylaw_slug=bylaw_slug,
            zone_code=zone_code,
            rule_type=item.get("rule_type") or "prohibition",
            value_text=item.get("summary"),
            status=item.get("status"),
        )

    requirements = payload.get("requirements", {})
    for group_name in ("base_dimensional_controls", "accessory_building_controls", "corner_lot_controls"):
        for index, item in enumerate(requirements.get(group_name, []), start=1):
            text_value = item.get("summary") or item.get("metric")
            provision_key = base_provision(item, group_name, index, text_value)
            controls = item.get("controls")
            if controls:
                for control_index, control in enumerate(controls, start=1):
                    add_rule(
                        rules,
                        source_key=make_source_key(provision_key, "rule", control.get("metric"), control_index),
                        provision_source_key=provision_key,
                        bylaw_slug=bylaw_slug,
                        zone_code=zone_code,
                        rule_type=group_name,
                        metric=control.get("metric"),
                        numeric_value=control.get("value"),
                        value_text=control.get("condition_text"),
                        unit=control.get("unit"),
                        condition_text=control.get("condition_text"),
                        status=item.get("status"),
                    )
            else:
                add_rule(
                    rules,
                    source_key=make_source_key(provision_key, "rule", item.get("metric") or group_name, index),
                    provision_source_key=provision_key,
                    bylaw_slug=bylaw_slug,
                    zone_code=zone_code,
                    rule_type=group_name,
                    metric=item.get("metric"),
                    numeric_value=item.get("value"),
                    value_text=item.get("summary"),
                    unit=item.get("unit"),
                    condition_text=item.get("condition_text") or join_conditions(item.get("conditions")),
                    status=item.get("status"),
                    metadata={"building_types": item.get("building_types")},
                )

    for index, item in enumerate(requirements.get("area_specific_overrides", []), start=1):
        provision_key = base_provision(item, "area_specific_override", index, item.get("area_name"))
        for requirement_index, requirement in enumerate(item.get("requirements", []), start=1):
            rule_key = make_source_key(provision_key, "rule", requirement.get("metric"), requirement_index)
            add_rule(
                rules,
                source_key=rule_key,
                provision_source_key=provision_key,
                bylaw_slug=bylaw_slug,
                zone_code=zone_code,
                rule_type="area_specific_override",
                metric=requirement.get("metric"),
                numeric_value=requirement.get("value"),
                unit=requirement.get("unit"),
                condition_text=requirement.get("condition_text"),
                applicability_scope=item.get("area_source_reference") or item.get("schedule_reference") or item.get("area_name"),
                status=item.get("status"),
                metadata={"override_type": item.get("override_type"), "exceptions": item.get("exceptions")},
            )
            link_rule_to_spatial_refs(spatial_links, spatial_refs_by_bylaw, bylaw_slug=bylaw_slug, rule_source_key=rule_key, item=item)
        for subarea_index, subarea in enumerate(item.get("subareas", []), start=1):
            for requirement_index, requirement in enumerate(subarea.get("requirements", []), start=1):
                rule_key = make_source_key(
                    provision_key,
                    "subarea_rule",
                    subarea.get("clause_label_raw"),
                    requirement.get("metric"),
                    subarea_index,
                    requirement_index,
                )
                add_rule(
                    rules,
                    source_key=rule_key,
                    provision_source_key=provision_key,
                    bylaw_slug=bylaw_slug,
                    zone_code=zone_code,
                    rule_type="area_specific_override",
                    metric=requirement.get("metric"),
                    numeric_value=requirement.get("value"),
                    unit=requirement.get("unit"),
                    condition_text=requirement.get("condition_text"),
                    applicability_scope=subarea.get("subarea_name") or item.get("area_source_reference") or item.get("area_name"),
                    status=item.get("status"),
                    metadata={"subarea_name": subarea.get("subarea_name"), "parent_clause_label_raw": item.get("clause_label_raw")},
                )
                link_rule_to_spatial_refs(spatial_links, spatial_refs_by_bylaw, bylaw_slug=bylaw_slug, rule_source_key=rule_key, item={**item, **subarea})

    for index, item in enumerate(payload.get("sign_controls", []), start=1):
        provision_key = base_provision(item, "sign_control", index, item.get("sign_type"))
        add_rule(
            rules,
            source_key=make_source_key(provision_key, "rule", item.get("sign_type"), index),
            provision_source_key=provision_key,
            bylaw_slug=bylaw_slug,
            zone_code=zone_code,
            rule_type="sign_control",
            metric="sign_area_maximum" if item.get("max_area") is not None else None,
            use_name=item.get("sign_type"),
            numeric_value=item.get("max_area"),
            unit=item.get("unit"),
            condition_text=join_conditions(item.get("conditions")),
            status=item.get("status"),
        )

    for index, item in enumerate(payload.get("use_specific_standards", []), start=1):
        provision_key = base_provision(
            item,
            "use_specific_standard",
            index,
            item.get("use_name") or item.get("summary"),
            {"section_path": item.get("section_path")},
        )
        controls = item.get("controls")
        if controls:
            for control_index, control in enumerate(controls, start=1):
                rule_key = make_source_key(provision_key, "rule", control.get("metric"), control_index)
                add_rule(
                    rules,
                    source_key=rule_key,
                    provision_source_key=provision_key,
                    bylaw_slug=bylaw_slug,
                    zone_code=zone_code,
                    rule_type="use_specific_standard",
                    metric=control.get("metric"),
                    use_name=item.get("use_name"),
                    numeric_value=control.get("value"),
                    value_text=control.get("condition_text"),
                    unit=control.get("unit"),
                    condition_text=control.get("condition_text") or join_conditions(item.get("conditions")),
                    applicability_scope=item.get("area_name"),
                    status=item.get("status"),
                )
                link_rule_to_spatial_refs(spatial_links, spatial_refs_by_bylaw, bylaw_slug=bylaw_slug, rule_source_key=rule_key, item=item)
        elif item.get("conditions"):
            add_rule(
                rules,
                source_key=make_source_key(provision_key, "rule", item.get("section_label_raw"), index),
                provision_source_key=provision_key,
                bylaw_slug=bylaw_slug,
                zone_code=zone_code,
                rule_type="use_specific_standard",
                use_name=item.get("use_name"),
                value_text=join_conditions(item.get("conditions")),
                applicability_scope=item.get("area_name"),
                status=item.get("status"),
            )


def insert_mps_content(
    *,
    bylaw_slug: str,
    relpath: str,
    payload: dict[str, Any],
    provisions: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> None:
    section_metadata = payload.get("section_metadata") or {}
    section_label_raw = section_metadata.get("section_label_raw")
    title_label_raw = section_metadata.get("title_label_raw")
    section_slug = section_metadata.get("section_slug")
    section_type = section_metadata.get("section_type")
    section_status = section_metadata.get("status") or payload.get("status")

    for index, block in enumerate(payload.get("context_blocks", []), start=1):
        add_provision(
            provisions,
            source_key=make_source_key(relpath, "context_block", index),
            section_relpath=relpath,
            zone_code=None,
            provision_kind="mps_context_block",
            section_label_raw=section_label_raw,
            clause_label_raw=None,
            clause_path=None,
            parent_clause_label_raw=None,
            text_value=block.get("text"),
            status=section_status,
            citations_json={
                key: block.get(key)
                for key in ("pdf_page_start", "pdf_page_end", "mps_page_start", "mps_page_end")
                if block.get(key) is not None
            },
            metadata={
                "title_label_raw": title_label_raw,
                "section_slug": section_slug,
                "section_type": section_type,
                "topic": block.get("topic"),
            },
        )

    for index, objective in enumerate(payload.get("objectives", []), start=1):
        add_provision(
            provisions,
            source_key=make_source_key(relpath, "objective", objective.get("label_raw"), index),
            section_relpath=relpath,
            zone_code=None,
            provision_kind="mps_objective",
            section_label_raw=section_label_raw,
            clause_label_raw=objective.get("label_raw"),
            clause_path=None,
            parent_clause_label_raw=None,
            text_value=objective.get("text"),
            status=section_status,
            citations_json={
                key: objective.get(key)
                for key in ("pdf_page_start", "pdf_page_end", "mps_page_start", "mps_page_end")
                if objective.get(key) is not None
            },
            metadata={
                "title_label_raw": title_label_raw,
                "section_slug": section_slug,
                "section_type": section_type,
                "topic": objective.get("topic"),
            },
        )

    for index, policy in enumerate(payload.get("policies", []), start=1):
        provision_key = make_source_key(relpath, "policy", policy.get("policy_label_raw"), index)
        add_provision(
            provisions,
            source_key=provision_key,
            section_relpath=relpath,
            zone_code=None,
            provision_kind="mps_policy",
            section_label_raw=section_label_raw,
            clause_label_raw=policy.get("policy_label_raw") or policy.get("label_raw"),
            clause_path=None,
            parent_clause_label_raw=None,
            text_value=policy.get("text"),
            status=section_status,
            citations_json={
                key: policy.get(key)
                for key in ("pdf_page_start", "pdf_page_end", "mps_page_start", "mps_page_end")
                if policy.get(key) is not None
            },
            metadata={
                "title_label_raw": title_label_raw,
                "section_slug": section_slug,
                "section_type": section_type,
                "policy_type": policy.get("policy_type"),
                "modality": policy.get("modality"),
                "topic": policy.get("topic"),
                "label_raw": policy.get("label_raw"),
            },
        )
        add_rule(
            rules,
            source_key=make_source_key(provision_key, "rule"),
            provision_source_key=provision_key,
            bylaw_slug=bylaw_slug,
            zone_code=None,
            rule_type=policy.get("policy_type") or "mps_policy",
            value_text=policy.get("text"),
            condition_text=policy.get("text"),
            applicability_scope=section_label_raw,
            status=section_status,
            metadata={
                "policy_label_raw": policy.get("policy_label_raw"),
                "label_raw": policy.get("label_raw"),
                "modality": policy.get("modality"),
                "section_slug": section_slug,
                "section_type": section_type,
                "title_label_raw": title_label_raw,
                "topic": policy.get("topic"),
            },
        )


def build_dataset() -> dict[str, Any]:
    bylaws: dict[str, dict[str, Any]] = {}
    section_files: list[dict[str, Any]] = []
    zones: dict[tuple[str, str], dict[str, Any]] = {}
    definitions: list[dict[str, Any]] = []
    definition_counts: dict[tuple[str, str], int] = {}
    provisions: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    spatial_refs: list[dict[str, Any]] = []
    spatial_links: list[dict[str, str]] = []
    spatial_refs_by_bylaw: dict[str, list[dict[str, Any]]] = {}

    json_paths: list[Path] = []
    for data_root in DATA_ROOTS:
        json_paths.extend(sorted(data_root.glob("*/*.json")))
        json_paths.extend(sorted(data_root.glob("*/*/*.json")))

    for path in json_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        root_kind = "municipal-planning-strategy" if path.is_relative_to(DATA_ROOTS[1]) else "zoning"
        if path.is_relative_to(DATA_ROOTS[0]):
            area_slug = path.relative_to(DATA_ROOTS[0]).parts[0]
        else:
            area_slug = path.relative_to(DATA_ROOTS[1]).parts[0]
        slug = f"{area_slug}-mps" if root_kind == "municipal-planning-strategy" else area_slug
        relpath = normalize_relpath(path)

        if slug not in bylaws:
            bylaws[slug] = infer_bylaw_metadata(payload, slug)
        else:
            inferred = infer_bylaw_metadata(payload, slug)
            if not bylaws[slug].get("source_document_path") and inferred.get("source_document_path"):
                bylaws[slug]["source_document_path"] = inferred["source_document_path"]

        document_metadata = (
            payload.get("document_metadata")
            or payload.get("section_metadata")
            or payload.get("schedule_metadata")
            or {}
        )
        section_files.append(
            {
                "bylaw_slug": slug,
                "section_kind": infer_section_kind(relpath),
                "source_relpath": relpath,
                "document_type": document_metadata.get("document_type"),
                "status": document_metadata.get("status") or payload.get("status"),
                "zone_code": document_metadata.get("zone_code"),
                "schedule_label_raw": document_metadata.get("schedule_label_raw"),
                "source_pages_json": pages_json(payload),
                "raw_json": payload,
            }
        )

        if document_metadata.get("zone_code"):
            zones[(slug, document_metadata["zone_code"])] = {
                "bylaw_slug": slug,
                "zone_code": document_metadata["zone_code"],
                "zone_name": document_metadata.get("zone_name"),
                "zone_section_start_json": document_metadata.get("zone_section_start") or {},
                "zone_section_end_json": document_metadata.get("zone_section_end_before") or {},
                "metadata": {
                    "zone_established_by": document_metadata.get("zone_established_by"),
                    "general_context": payload.get("general_context"),
                    "normalization_policy": payload.get("normalization_policy"),
                    "citations": payload.get("citations"),
                    "open_issues": payload.get("open_issues"),
                },
            }

        if "definitions" in payload:
            for entry in payload["definitions"]:
                term_raw = entry.get("term_raw") or entry.get("term_label_raw")
                definition_key = entry.get("definition_key") or canonicalize_label(term_raw) or make_source_key(relpath, "definition", entry.get("entry_index"))
                dedupe_key = (slug, definition_key)
                definition_counts[dedupe_key] = definition_counts.get(dedupe_key, 0) + 1
                if definition_counts[dedupe_key] > 1:
                    definition_key = f"{definition_key}__{definition_counts[dedupe_key]}"
                definitions.append(
                    {
                        "bylaw_slug": slug,
                        "definition_key": definition_key,
                        "term_raw": term_raw,
                        "definition_text": entry.get("definition_text") or entry.get("text") or "",
                        "status": entry.get("status"),
                        "section_label_raw": entry.get("section_label_raw"),
                        "citations_json": entry.get("citations") or {},
                        "metadata": {"entry_index": entry.get("entry_index")},
                    }
                )

        if "sections" in payload:
            for section_index, section in enumerate(payload["sections"], start=1):
                for provision_index, provision in enumerate(section.get("provisions", []), start=1):
                    add_provision(
                        provisions,
                        source_key=make_source_key(relpath, "section", section_index, provision_index),
                        section_relpath=relpath,
                        zone_code=document_metadata.get("zone_code"),
                        provision_kind="section_provision",
                        section_label_raw=section.get("section_label_raw"),
                        clause_label_raw=provision.get("provision_label_raw") or provision.get("clause_label_raw"),
                        clause_path=provision.get("clause_path"),
                        parent_clause_label_raw=None,
                        text_value=provision.get("text"),
                        status=provision.get("status"),
                        citations_json=provision.get("citations") or section.get("citations") or {},
                        metadata={
                            "heading_context_raw": provision.get("heading_context_raw"),
                            "title_label_raw": section.get("title_label_raw"),
                            "order_index": section.get("order_index"),
                        },
                    )

        if "provisions" in payload:
            for provision_index, provision in enumerate(payload["provisions"], start=1):
                add_provision(
                    provisions,
                    source_key=make_source_key(relpath, "provision", provision_index),
                    section_relpath=relpath,
                    zone_code=document_metadata.get("zone_code"),
                    provision_kind="flat_provision",
                    section_label_raw=document_metadata.get("schedule_label_raw"),
                    clause_label_raw=provision.get("provision_label_raw") or provision.get("clause_label_raw"),
                    clause_path=provision.get("clause_path"),
                    parent_clause_label_raw=None,
                    text_value=provision.get("text"),
                    status=provision.get("status"),
                    citations_json=provision.get("citations") or {},
                    metadata={},
                )

        if "references" in payload:
            for index, reference in enumerate(payload["references"], start=1):
                record = {
                    "source_key": make_source_key(relpath, "spatial_reference", index, reference.get("feature_key")),
                    "bylaw_slug": slug,
                    "section_relpath": relpath,
                    "zone_code": None,
                    "provision_source_key": None,
                    "feature_key": reference.get("feature_key"),
                    "feature_class": reference.get("feature_class"),
                    "source_type": reference.get("reference_type"),
                    "source_label_raw": reference.get("source_label_raw"),
                    "schedule_file": reference.get("schedule_file"),
                    "extraction_status": None,
                    "target_schema": "public" if reference.get("planned_postgis_target") == "spatial_features.geom" else None,
                    "target_table": "spatial_features" if reference.get("planned_postgis_target") == "spatial_features.geom" else None,
                    "target_identifier": reference.get("feature_key"),
                    "join_method": "feature_key_reference",
                    "metadata": {
                        "pdf_page_start": reference.get("pdf_page_start"),
                        "pdf_page_end": reference.get("pdf_page_end"),
                        "bylaw_page_start": reference.get("bylaw_page_start"),
                        "bylaw_page_end": reference.get("bylaw_page_end"),
                        "mps_page_start": reference.get("mps_page_start"),
                        "mps_page_end": reference.get("mps_page_end"),
                        "title_text": reference.get("title_text"),
                        "section_label_raw": reference.get("section_label_raw"),
                        "section_slug": reference.get("section_slug"),
                    },
                }
                spatial_refs.append(record)
                spatial_refs_by_bylaw.setdefault(slug, []).append(record)

        if "spatial_features_needed" in payload:
            for index, feature in enumerate(payload["spatial_features_needed"], start=1):
                record = {
                    "source_key": make_source_key(relpath, "spatial_needed", index, feature.get("feature_key")),
                    "bylaw_slug": slug,
                    "section_relpath": relpath,
                    "zone_code": document_metadata.get("zone_code"),
                    "provision_source_key": None,
                    "feature_key": feature.get("feature_key"),
                    "feature_class": feature.get("feature_class"),
                    "source_type": feature.get("source_type"),
                    "source_label_raw": feature.get("source_label_raw"),
                    "schedule_file": feature.get("schedule_file"),
                    "extraction_status": feature.get("source_type"),
                    "target_schema": "public" if feature.get("planned_postgis_target") == "spatial_features.geom" else None,
                    "target_table": "spatial_features" if feature.get("planned_postgis_target") == "spatial_features.geom" else None,
                    "target_identifier": feature.get("feature_key"),
                    "join_method": "feature_key_backlog",
                    "metadata": {
                        "reason": feature.get("reason"),
                        "source_document_page": feature.get("source_document_page"),
                        "section_label_raw": feature.get("section_label_raw"),
                        "section_slug": feature.get("section_slug"),
                    },
                }
                spatial_refs.append(record)
                spatial_refs_by_bylaw.setdefault(slug, []).append(record)

        if document_metadata.get("zone_code"):
            insert_zone_rules(
                bylaw_slug=slug,
                relpath=relpath,
                zone_code=document_metadata["zone_code"],
                payload=payload,
                provisions=provisions,
                rules=rules,
                spatial_links=spatial_links,
                spatial_refs_by_bylaw=spatial_refs_by_bylaw,
            )
        elif payload.get("section_metadata"):
            insert_mps_content(
                bylaw_slug=slug,
                relpath=relpath,
                payload=payload,
                provisions=provisions,
                rules=rules,
            )

    return {
        "bylaws": list(bylaws.values()),
        "section_files": section_files,
        "zones": list(zones.values()),
        "definitions": definitions,
        "provisions": provisions,
        "rules": rules,
        "spatial_refs": spatial_refs,
        "spatial_links": spatial_links,
    }


def build_sql(dataset: dict[str, Any]) -> str:
    statements: list[str] = [
        "BEGIN;",
        "TRUNCATE TABLE hrm.rule_spatial_applicability, hrm.rule_atom, hrm.zone_spatial_match, hrm.spatial_reference, hrm.provision, hrm.definition, hrm.zone, hrm.section_file, hrm.bylaw RESTART IDENTITY CASCADE;",
    ]

    for row in dataset["bylaws"]:
        statements.append(
            "INSERT INTO hrm.bylaw (bylaw_slug, jurisdiction, bylaw_name, source_document_path, existing_spatial_bylaw_id, metadata) VALUES ("
            + ", ".join(
                [
                    sql_text(row["bylaw_slug"]),
                    sql_text(row["jurisdiction"]),
                    sql_text(row["bylaw_name"]),
                    sql_text(row.get("source_document_path")),
                    sql_text(row.get("existing_spatial_bylaw_id")),
                    sql_json(row.get("metadata") or {}),
                ]
            )
            + ");"
        )

    for row in dataset["section_files"]:
        statements.append(
            "INSERT INTO hrm.section_file (bylaw_pk, section_kind, source_relpath, document_type, status, zone_code, schedule_label_raw, source_pages_json, raw_json) VALUES ("
            + ", ".join(
                [
                    f"(SELECT bylaw_pk FROM hrm.bylaw WHERE bylaw_slug = {sql_text(row['bylaw_slug'])})",
                    sql_text(row["section_kind"]),
                    sql_text(row["source_relpath"]),
                    sql_text(row.get("document_type")),
                    sql_text(row.get("status")),
                    sql_text(row.get("zone_code")),
                    sql_text(row.get("schedule_label_raw")),
                    sql_json(row.get("source_pages_json") or {}),
                    sql_json(row["raw_json"]),
                ]
            )
            + ");"
        )

    for row in dataset["zones"]:
        statements.append(
            "INSERT INTO hrm.zone (bylaw_pk, zone_code, zone_name, zone_section_start_json, zone_section_end_json, metadata) VALUES ("
            + ", ".join(
                [
                    f"(SELECT bylaw_pk FROM hrm.bylaw WHERE bylaw_slug = {sql_text(row['bylaw_slug'])})",
                    sql_text(row["zone_code"]),
                    sql_text(row.get("zone_name")),
                    sql_json(row.get("zone_section_start_json") or {}),
                    sql_json(row.get("zone_section_end_json") or {}),
                    sql_json(row.get("metadata") or {}),
                ]
            )
            + ");"
        )

    for row in dataset["definitions"]:
        statements.append(
            "INSERT INTO hrm.definition (bylaw_pk, definition_key, term_raw, definition_text, status, section_label_raw, citations_json, metadata) VALUES ("
            + ", ".join(
                [
                    f"(SELECT bylaw_pk FROM hrm.bylaw WHERE bylaw_slug = {sql_text(row['bylaw_slug'])})",
                    sql_text(row["definition_key"]),
                    sql_text(row["term_raw"]),
                    sql_text(row["definition_text"]),
                    sql_text(row.get("status")),
                    sql_text(row.get("section_label_raw")),
                    sql_json(row.get("citations_json") or {}),
                    sql_json(row.get("metadata") or {}),
                ]
            )
            + ");"
        )

    for row in dataset["provisions"]:
        zone_expr = "NULL"
        if row.get("zone_code"):
            zone_expr = (
                "(SELECT z.zone_pk FROM hrm.zone AS z "
                "JOIN hrm.section_file AS sf ON sf.source_relpath = "
                f"{sql_text(row['section_relpath'])} "
                "JOIN hrm.bylaw AS b ON b.bylaw_pk = z.bylaw_pk AND b.bylaw_pk = sf.bylaw_pk "
                f"WHERE z.zone_code = {sql_text(row['zone_code'])})"
            )
        statements.append(
            "INSERT INTO hrm.provision (source_key, section_file_pk, zone_pk, provision_kind, section_label_raw, clause_label_raw, clause_path, parent_clause_label_raw, text_value, status, citations_json, metadata) VALUES ("
            + ", ".join(
                [
                    sql_text(row["source_key"]),
                    f"(SELECT section_file_pk FROM hrm.section_file WHERE source_relpath = {sql_text(row['section_relpath'])})",
                    zone_expr,
                    sql_text(row["provision_kind"]),
                    sql_text(row.get("section_label_raw")),
                    sql_text(row.get("clause_label_raw")),
                    sql_array(row.get("clause_path")),
                    sql_text(row.get("parent_clause_label_raw")),
                    sql_text(row.get("text_value")),
                    sql_text(row.get("status")),
                    sql_json(row.get("citations_json") or {}),
                    sql_json(row.get("metadata") or {}),
                ]
            )
            + ");"
        )

    for row in dataset["rules"]:
        zone_expr = "NULL"
        if row.get("zone_code"):
            zone_expr = (
                "(SELECT z.zone_pk FROM hrm.zone AS z "
                "JOIN hrm.bylaw AS b ON b.bylaw_pk = z.bylaw_pk "
                f"WHERE b.bylaw_slug = {sql_text(row['bylaw_slug'])} AND z.zone_code = {sql_text(row['zone_code'])})"
            )
        statements.append(
            "INSERT INTO hrm.rule_atom (source_key, provision_pk, zone_pk, rule_type, metric, use_name, numeric_value, value_text, unit, comparator, condition_text, applicability_scope, status, metadata) VALUES ("
            + ", ".join(
                [
                    sql_text(row["source_key"]),
                    f"(SELECT provision_pk FROM hrm.provision WHERE source_key = {sql_text(row['provision_source_key'])})",
                    zone_expr,
                    sql_text(row["rule_type"]),
                    sql_text(row.get("metric")),
                    sql_text(row.get("use_name")),
                    "NULL" if row.get("numeric_value") is None else str(row["numeric_value"]),
                    sql_text(row.get("value_text")),
                    sql_text(row.get("unit")),
                    sql_text(row.get("comparator")),
                    sql_text(row.get("condition_text")),
                    sql_text(row.get("applicability_scope")),
                    sql_text(row.get("status")),
                    sql_json(row.get("metadata") or {}),
                ]
            )
            + ");"
        )

    for row in dataset["spatial_refs"]:
        zone_expr = "NULL"
        if row.get("zone_code"):
            zone_expr = (
                "(SELECT z.zone_pk FROM hrm.zone AS z "
                "JOIN hrm.bylaw AS b ON b.bylaw_pk = z.bylaw_pk "
                f"WHERE b.bylaw_slug = {sql_text(row['bylaw_slug'])} AND z.zone_code = {sql_text(row['zone_code'])})"
            )
        statements.append(
            "INSERT INTO hrm.spatial_reference (source_key, bylaw_pk, section_file_pk, zone_pk, provision_pk, feature_key, feature_class, source_type, source_label_raw, schedule_file, extraction_status, target_schema, target_table, target_identifier, join_method, metadata) VALUES ("
            + ", ".join(
                [
                    sql_text(row["source_key"]),
                    f"(SELECT bylaw_pk FROM hrm.bylaw WHERE bylaw_slug = {sql_text(row['bylaw_slug'])})",
                    f"(SELECT section_file_pk FROM hrm.section_file WHERE source_relpath = {sql_text(row['section_relpath'])})",
                    zone_expr,
                    "NULL",
                    sql_text(row.get("feature_key")),
                    sql_text(row.get("feature_class")),
                    sql_text(row.get("source_type")),
                    sql_text(row.get("source_label_raw")),
                    sql_text(row.get("schedule_file")),
                    sql_text(row.get("extraction_status")),
                    sql_text(row.get("target_schema")),
                    sql_text(row.get("target_table")),
                    sql_text(row.get("target_identifier")),
                    sql_text(row.get("join_method")),
                    sql_json(row.get("metadata") or {}),
                ]
            )
            + ");"
        )

    for row in dataset["spatial_links"]:
        statements.append(
            "INSERT INTO hrm.rule_spatial_applicability (source_key, rule_atom_pk, spatial_ref_pk, applicability_type, priority_order, notes, metadata) VALUES ("
            + ", ".join(
                [
                    sql_text(row["source_key"]),
                    f"(SELECT rule_atom_pk FROM hrm.rule_atom WHERE source_key = {sql_text(row['rule_source_key'])})",
                    f"(SELECT spatial_ref_pk FROM hrm.spatial_reference WHERE source_key = {sql_text(row['spatial_source_key'])})",
                    sql_text(row["applicability_type"]),
                    row["priority_order"],
                    sql_text(row.get("notes")),
                    "'{}'::jsonb",
                ]
            )
            + ");"
        )

    statements.extend(
        [
            """
            INSERT INTO hrm.zone_spatial_match (zone_pk, target_schema, target_table, target_feature_id, match_method, confidence, metadata)
            SELECT
              DISTINCT z.zone_pk,
              'public',
              'HFX_Halifax_Zoning_Boundaries',
              hz.source_feature_id,
              'community_plan_area_intersection_and_zone_code',
              1.0,
              jsonb_build_object(
                'description', hz.description,
                'source', hz.source,
                'community_plan_name', cp."PLAN_NAME",
                'community_plan_id', cp."PLAN_ID"
              )
            FROM hrm.zone AS z
            JOIN hrm.bylaw AS b
              ON b.bylaw_pk = z.bylaw_pk
            JOIN public."HFX_Community_Plan_Areas" AS cp
              ON cp."PLAN_NAME" = b.metadata->>'community_plan_name'
            JOIN public."HFX_Halifax_Zoning_Boundaries" AS hz
              ON upper(hz.zone) = upper(z.zone_code)
             AND ST_Intersects(hz.geom, cp.geom)
            WHERE b.metadata ? 'community_plan_name';
            """,
            "COMMIT;",
        ]
    )

    return "\n".join(statement.rstrip() for statement in statements if statement)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import normalized zoning JSON into PostGIS.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary counts without modifying the database.")
    args = parser.parse_args()

    dataset = build_dataset()
    summary = {
        "bylaws": len(dataset["bylaws"]),
        "definitions": len(dataset["definitions"]),
        "provisions": len(dataset["provisions"]),
        "rule_spatial_links": len(dataset["spatial_links"]),
        "rules": len(dataset["rules"]),
        "section_files": len(dataset["section_files"]),
        "spatial_refs": len(dataset["spatial_refs"]),
        "zones": len(dataset["zones"]),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.dry_run:
        return 0

    psql(build_sql(dataset))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

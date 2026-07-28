#!/usr/bin/env python3
"""Generate Stage 2 logical groups and a write-free shadow observation export."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import tempfile
import tracemalloc
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUDGET = ROOT / "data/budget/charlottetown/2026-2027"
V2 = BUDGET / "staged-pdf/v2"
DEFAULT_PATHS = {
    "blocks": V2 / "stage-1/block-inventory.json",
    "source": V2 / "stage-0/source-evidence.json",
    "canonical": BUDGET / "canonical-table-inventory.json",
    "manifest": BUDGET / "normalized-import-manifest.json",
    "rows": BUDGET / "raw-tables/source_table_rows.json",
    "values": BUDGET / "raw-tables/source_values.json",
}
DEFAULT_GROUPS = V2 / "stage-2/content-groups.json"
DEFAULT_OBSERVATIONS = V2 / "stage-2/shadow-observations.json"
SCHEMA_REF = "schema/json-schema/staged-pdf-artifacts-v2.schema.json"
GENERATOR = {
    "name": "staged-pdf-v2-stage-2",
    "version": "1",
    "config_sha256": hashlib.sha256(
        b"statement-scoped-groups|reviewed-raw-adapter|snapshot-3"
    ).hexdigest(),
}
MAX_PEAK_MEMORY_BYTES = 96 * 1024 * 1024


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def artifact_ref(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "artifact_key": payload["artifact_key"],
        "artifact_type": payload["artifact_type"],
        "schema_version": payload["schema_version"],
        "sha256": digest_bytes(path.read_bytes()),
    }


def review(
    status: str,
    reason: str,
    decision_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason_codes": [reason],
        "decision_ids": decision_ids or [],
    }


def page_from_row(row_key: str | None) -> int | None:
    match = re.search(r"_p(\d{3})_", row_key or "")
    return int(match.group(1)) if match else None


def group_key(statement_key: str) -> str:
    return f"ctown-budget-2026-2027:group:{statement_key}"


def body_key(page: int) -> str:
    return f"ctown-budget-2026-2027:p{page:03d}:body"


def title_key(page: int) -> str:
    return f"ctown-budget-2026-2027:p{page:03d}:title"


def group_record(
    key: str,
    title: str,
    family: str | None,
    disposition: str,
    pages: list[int],
    block_keys: set[str],
    entities: list[str],
    periods: list[str],
    status: str,
    reason: str,
    decision_ids: list[str] | None = None,
) -> dict[str, Any]:
    members = []
    bodies = []
    for page in sorted(pages):
        if title_key(page) in block_keys:
            members.append((title_key(page), "header"))
        if body_key(page) in block_keys:
            members.append(
                (body_key(page), "body" if not bodies else "continuation")
            )
            bodies.append(body_key(page))
    if not members:
        raise ValueError(f"Group {key} has no Stage 1 members")
    edge_review = review(status, reason, decision_ids)
    return {
        "group_key": key,
        "title": title,
        "family_candidate": family,
        "disposition": disposition,
        "page_start": min(pages),
        "page_end": max(pages),
        "members": [
            {
                "block_key": block,
                "order": index,
                "role": role,
                "ownership": "primary",
            }
            for index, (block, role) in enumerate(members, 1)
        ],
        "continuation_edges": [
            {
                "from_block_key": left,
                "to_block_key": right,
                "evidence_codes": [
                    "reviewed-statement-identity",
                    "source-page-order",
                ],
                "confidence": {
                    "level": "reviewed",
                    "score": 1,
                    "reason_codes": ["approved-normalization-mapping"],
                },
                "review": copy.deepcopy(edge_review),
            }
            for left, right in zip(bodies, bodies[1:])
        ],
        "inherited_headers": [
            {
                "target_block_key": target,
                "source_block_key": source,
                "header_role": "prior-page-column-context",
                "review": copy.deepcopy(edge_review),
            }
            for source, target in zip(bodies, bodies[1:])
        ],
        "entity_candidates": sorted(set(entities)),
        "period_candidates": sorted(set(periods)),
        "relationships": [],
        "review": review(status, reason, decision_ids),
    }


def build_groups(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blocks_payload = inputs["blocks"]
    manifest = inputs["manifest"]
    canonical = inputs["canonical"]["records"]
    block_keys = {item["block_key"] for item in blocks_payload["records"]}
    financial_blocks = {
        item["block_key"]
        for item in blocks_payload["records"]
        if item["financial_candidate"]
    }
    lines = {item["key"]: item for item in manifest["line_items"]}
    statements = {item["key"]: item for item in manifest["statements"]}
    periods = {
        item["key"]: item for item in manifest["document_periods"]
    }
    statement_pages: dict[str, set[int]] = defaultdict(set)
    statement_periods: dict[str, set[str]] = defaultdict(set)
    for fact in manifest["facts"]:
        line = lines[fact["line_key"]]
        page = page_from_row(line.get("source_row_id"))
        if page is not None:
            statement_pages[line["statement_key"]].add(page)
        period = periods[fact["document_period_key"]]
        statement_periods[line["statement_key"]].add(
            period["fiscal_period_key"]
        )

    # Snapshot 3 added these reviewed appendices after the normalized manifest.
    virtual = {
        "appendix-property-tax-statement": {
            "title": "Appendix 1 - Schedule of Property Taxes",
            "statement_kind": "tax_assessment_rate",
            "reporting_entity_key": "city-of-charlottetown",
            "pages": {149},
            "periods": {"2026-2027-budget"},
        },
        "appendix-city-debt-statement": {
            "title": "Appendix 2 - Fiscal Services - Schedule of Long Term Debt",
            "statement_kind": "debt",
            "reporting_entity_key": "city-of-charlottetown",
            "pages": {151},
            "periods": {"2026-2027-budget"},
        },
    }

    records = []
    owned: set[str] = set()
    statement_to_group = {}
    for statement_key in sorted(statement_pages):
        statement = statements[statement_key]
        pages = sorted(statement_pages[statement_key])
        record = group_record(
            group_key(statement_key),
            statement["title"],
            statement["statement_kind"].replace("_", "-"),
            "normalize",
            pages,
            block_keys,
            [statement["reporting_entity_key"]],
            sorted(statement_periods[statement_key]),
            "approved",
            "approved-normalization-mapping",
        )
        records.append(record)
        owned.update(
            member["block_key"] for member in record["members"]
        )
        statement_to_group[statement_key] = record["group_key"]
    for statement_key, statement in virtual.items():
        record = group_record(
            group_key(statement_key),
            statement["title"],
            statement["statement_kind"].replace("_", "-"),
            "normalize",
            sorted(statement["pages"]),
            block_keys,
            [statement["reporting_entity_key"]],
            sorted(statement["periods"]),
            "approved",
            "reviewed-snapshot-3-appendix-recovery",
        )
        records.append(record)
        owned.update(
            member["block_key"] for member in record["members"]
        )
        statement_to_group[statement_key] = record["group_key"]

    candidate_by_page = {item["page_start"]: item for item in canonical}
    for page, candidate in sorted(candidate_by_page.items()):
        available = [
            key for key in (title_key(page), body_key(page))
            if key in block_keys and key not in owned
        ]
        if not available:
            continue
        record = group_record(
            f"ctown-budget-2026-2027:group:{candidate['canonical_key']}",
            candidate["section_title"],
            candidate["family"].replace("_", "-"),
            candidate["disposition"],
            [page],
            set(available),
            candidate["entity_candidates"],
            ["2026/2027"],
            "approved",
            "reviewed-canonical-table-disposition",
        )
        records.append(record)
        owned.update(
            member["block_key"] for member in record["members"]
        )

    # These narrative pages are Stage 1 table false positives and were absent
    # from the reviewed canonical table inventory.
    for page in (9, 11, 13):
        record = group_record(
            f"ctown-budget-2026-2027:group:narrative-negative-p{page:03d}",
            f"Narrative negative control page {page}",
            "narrative-negative-control",
            "excluded",
            [page],
            block_keys,
            [],
            [],
            "approved",
            "reviewed-normalization-negative-control",
            ["ctown-budget-2026-2027:decision:000039"],
        )
        records.append(record)
        owned.update(
            member["block_key"] for member in record["members"]
        )

    if body_key(152) in block_keys:
        divider = group_record(
            "ctown-budget-2026-2027:group:water-sewer-debt-divider",
            "Water and Sewer long-term debt divider",
            "section-divider",
            "non_financial",
            [152],
            block_keys,
            [],
            [],
            "approved",
            "reviewed-section-divider",
        )
        divider["members"][0]["role"] = "divider"
        records.append(divider)
        owned.update(
            member["block_key"] for member in divider["members"]
        )

    by_key = {item["group_key"]: item for item in records}
    for relationship in manifest["statement_relationships"]:
        parent = statement_to_group[relationship["parent_statement_key"]]
        child = statement_to_group[relationship["child_statement_key"]]
        relation_review = review(
            "approved", "approved-statement-relationship"
        )
        by_key[parent]["relationships"].append({
            "target_group_key": child,
            "relationship_type": "summary_of",
            "review": copy.deepcopy(relation_review),
        })
        by_key[child]["relationships"].append({
            "target_group_key": parent,
            "relationship_type": "detail_of",
            "review": copy.deepcopy(relation_review),
        })

    page_groups = defaultdict(list)
    for record in records:
        page_groups[record["page_start"]].append(record)
    if 152 in page_groups and "appendix-city-debt-statement" in statement_to_group:
        target = by_key[statement_to_group["appendix-city-debt-statement"]]
        # The divider precedes the Water and Sewer appendix on page 153.
        water = statement_to_group.get("appendix-water-sewer-debt-statement")
        if water:
            by_key[water]["relationships"].append({
                "target_group_key": page_groups[152][0]["group_key"],
                "relationship_type": "preceded_by_divider",
                "review": review("approved", "reviewed-section-divider"),
            })

    unowned = sorted(financial_blocks - owned)
    if unowned:
        raise ValueError(
            "Financial blocks without Stage 2 ownership: "
            + ", ".join(unowned)
        )
    records.sort(key=lambda item: (item["page_start"], item["group_key"]))
    payload = {
        "$schema": SCHEMA_REF,
        "schema_version": 2,
        "artifact_type": "content_groups",
        "artifact_key": "ctown-budget-2026-2027:content-groups:v2",
        "document_key": blocks_payload["document_key"],
        "source_sha256": blocks_payload["source_sha256"],
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [],
        "records": records,
    }
    return payload


def decimal_text(raw: str) -> str:
    value = Decimal(raw.replace("$", "").replace(",", "").strip() or "0")
    return format(value, "f")


def source_projection(
    statement_key: str,
    line_key: str,
    period_key: str,
    amount_type: str,
    unit: str,
    value_numeric: str | None,
    value_text: str | None,
    value_state: str,
    row_id: str,
    value_ids: list[str],
    page: int,
    table_id: str,
    group: str,
    origin: str,
) -> dict[str, Any]:
    natural_key = {
        "statement_key": statement_key,
        "line_key": line_key,
        "document_period_key": period_key,
        "amount_type": amount_type,
        "measure_unit": unit,
    }
    return {
        "observation_key": digest_bytes(canonical_bytes(natural_key)).lower(),
        "natural_key": natural_key,
        "group_key": group,
        "value_numeric": value_numeric,
        "value_text": value_text,
        "value_state": value_state,
        "review_status": "approved",
        "source": {
            "table_id": table_id,
            "row_id": row_id,
            "value_ids": value_ids,
            "page_number": page,
        },
        "baseline_origin": origin,
    }


def recovered_observations(
    rows: list[dict[str, Any]],
    group_map: dict[str, str],
) -> list[dict[str, Any]]:
    records = []
    by_page = defaultdict(list)
    for row in rows:
        by_page[row["page_number"]].append(row)
    tax_pattern = re.compile(
        r"^\s*(.+?)\s+\$?([\d,]+)\s+x\s+\$?([\d.]+)"
        r"\s+per\s+\$100\s+\$\s*([\d,]+)\s*$",
        re.IGNORECASE,
    )
    single_pattern = re.compile(r"^\s*(.*?)\s*\$\s*([\d,]+)\s*$")
    current_group = "Property Taxes"
    for row in by_page[149]:
        match = tax_pattern.match(row["raw_text"])
        if match:
            label, assessment, rate, revenue = match.groups()
            group_slug = re.sub(
                r"[^a-z0-9]+", "-", current_group.casefold()
            ).strip("-")
            base = f"row-{row['row_index']:03d}-{group_slug}"
            specs = (
                ("assessment", assessment, "cad", 0),
                ("rate", rate, "cad_per_100_assessed", 1),
                ("revenue", revenue, "cad", -1),
            )
            for suffix, value, unit, source_index in specs:
                amount = "tax_revenue" if suffix == "revenue" else suffix
                records.append(source_projection(
                    "appendix-property-tax-statement",
                    f"{base}-{suffix}",
                    f"2026-2027:ctown_budget_2026_2027_p149:"
                    f"appendix-{suffix}",
                    amount,
                    unit,
                    decimal_text(value),
                    None,
                    "reported_zero" if Decimal(decimal_text(value)) == 0
                    else "reported",
                    row["row_id"],
                    [row["value_ids"][source_index]],
                    149,
                    row["table_id"],
                    group_map["appendix-property-tax-statement"],
                    "snapshot-3-reviewed-appendix-recovery",
                ))
            continue
        single = single_pattern.match(row["raw_text"])
        if single:
            label, value = single.groups()
            records.append(source_projection(
                "appendix-property-tax-statement",
                f"row-{row['row_index']:03d}-revenue",
                "2026-2027:ctown_budget_2026_2027_p149:"
                "appendix-tax-revenue",
                "tax_revenue",
                "cad",
                decimal_text(value),
                None,
                "reported_zero" if Decimal(decimal_text(value)) == 0
                else "reported",
                row["row_id"],
                row["value_ids"][-1:],
                149,
                row["table_id"],
                group_map["appendix-property-tax-statement"],
                "snapshot-3-reviewed-appendix-recovery",
            ))
            continue
        heading = row["trimmed_text"]
        if (
            heading
            and row["row_index"] > 3
            and not re.search(
                r"operating budget|city of charlottetown",
                heading,
                re.IGNORECASE,
            )
        ):
            current_group = heading.rstrip(":")

    debt_pattern = re.compile(
        r"^\s*(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+|-)\s*$"
    )
    for row in by_page[151]:
        match = debt_pattern.match(row["raw_text"])
        if match:
            _, balance, principal, interest = match.groups()
            for index, (measure, value) in enumerate((
                ("balance", balance),
                ("principal", principal),
                ("interest", interest),
            )):
                numeric = decimal_text(value if value != "-" else "0")
                records.append(source_projection(
                    "appendix-city-debt-statement",
                    f"row-{row['row_index']:03d}-{measure}",
                    f"2026-2027:ctown_budget_2026_2027_p151:"
                    f"appendix-{measure}",
                    measure,
                    "cad",
                    numeric,
                    None,
                    "reported_zero" if Decimal(numeric) == 0 else "reported",
                    row["row_id"],
                    [row["value_ids"][index]],
                    151,
                    row["table_id"],
                    group_map["appendix-city-debt-statement"],
                    "snapshot-3-reviewed-appendix-recovery",
                ))
            continue
        total = single_pattern.match(row["raw_text"])
        if total and "Total Interest and Principal" in row["raw_text"]:
            _, value = total.groups()
            records.append(source_projection(
                "appendix-city-debt-statement",
                f"row-{row['row_index']:03d}-total",
                "2026-2027:ctown_budget_2026_2027_p151:"
                "appendix-principal",
                "budget",
                "cad",
                decimal_text(value),
                None,
                "reported",
                row["row_id"],
                row["value_ids"][-1:],
                151,
                row["table_id"],
                group_map["appendix-city-debt-statement"],
                "snapshot-3-reviewed-appendix-recovery",
            ))
    return records


def build_observations(
    inputs: dict[str, dict[str, Any]],
    groups: dict[str, Any],
) -> dict[str, Any]:
    manifest = inputs["manifest"]
    lines = {item["key"]: item for item in manifest["line_items"]}
    statements = {item["key"]: item for item in manifest["statements"]}
    fact_sources = {
        item["fact_key"]: item for item in manifest["fact_sources"]
    }
    group_map = {
        item["group_key"].rsplit(":", 1)[-1]: item["group_key"]
        for item in groups["records"]
        if ":group:" in item["group_key"]
    }
    records = []
    for fact in manifest["facts"]:
        line = lines[fact["line_key"]]
        source = fact_sources[fact["key"]]
        page = page_from_row(line["source_row_id"])
        if page is None:
            raise ValueError(f"Fact has no source page: {fact['key']}")
        statement_key = line["statement_key"]
        records.append(source_projection(
            statement_key,
            fact["line_key"],
            fact["document_period_key"],
            fact["amount_type"],
            fact["measure_unit"],
            fact["value_numeric"],
            fact["value_text"],
            fact["value_state"],
            line["source_row_id"],
            [source["source_value_id"]],
            page,
            source["source_cell_key"].split(":full-", 1)[0],
            group_map[statement_key],
            "approved-normalized-import-manifest",
        ))
    recovered = recovered_observations(inputs["rows"]["records"], group_map)
    records.extend(recovered)
    records.sort(key=lambda item: item["observation_key"])
    keys = [item["observation_key"] for item in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Shadow observation natural keys are not unique")
    if len(manifest["facts"]) != 2165 or len(recovered) != 125:
        raise ValueError(
            f"Expected 2165 + 125 observations; got "
            f"{len(manifest['facts'])} + {len(recovered)}"
        )
    return {
        "schema_version": 1,
        "artifact_type": "shadow_observations",
        "artifact_key": "ctown-budget-2026-2027:shadow-observations:v2",
        "document_key": groups["document_key"],
        "source_sha256": groups["source_sha256"],
        "generator": copy.deepcopy(GENERATOR),
        "upstream_artifacts": [],
        "baseline": {
            "publication_snapshot_id": 3,
            "expected_observation_count": 2290,
            "basis": (
                "approved normalized manifest plus reviewed property-tax "
                "and City-debt appendix recovery used by Snapshot 3"
            ),
            "live_membership_verified": False,
        },
        "summary": {
            "manifest_observations": 2165,
            "recovered_property_tax_observations": sum(
                item["source"]["page_number"] == 149 for item in recovered
            ),
            "recovered_city_debt_observations": sum(
                item["source"]["page_number"] == 151 for item in recovered
            ),
            "total_observations": len(records),
            "natural_key_duplicates": len(keys) - len(set(keys)),
            "unmapped_groups": 0,
            "database_write_count": 0,
            "publication_write_count": 0,
        },
        "records": records,
    }


def load_validator():
    path = ROOT / "scripts/validate-staged-pdf-artifacts.py"
    spec = importlib.util.spec_from_file_location(
        "staged_pdf_validator_stage2", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(paths: dict[str, Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = {name: read_json(path) for name, path in paths.items()}
    groups = build_groups(inputs)
    groups["upstream_artifacts"] = [
        artifact_ref(inputs["source"], paths["source"]),
        artifact_ref(inputs["blocks"], paths["blocks"]),
    ]
    errors = load_validator().validate_payload(groups)
    if errors:
        raise RuntimeError("Content group validation failed: " + "; ".join(errors[:8]))
    observations = build_observations(inputs, groups)
    observations["upstream_artifacts"] = [
        {
            "artifact_key": groups["artifact_key"],
            "artifact_type": groups["artifact_type"],
            "schema_version": groups["schema_version"],
            "sha256": digest_bytes(canonical_bytes(groups)),
        }
    ]
    return groups, observations


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
    parser.add_argument("--groups-output", type=Path, default=DEFAULT_GROUPS)
    parser.add_argument(
        "--observations-output", type=Path, default=DEFAULT_OBSERVATIONS
    )
    for name, default in DEFAULT_PATHS.items():
        parser.add_argument(
            f"--{name.replace('_', '-')}", type=Path, default=default
        )
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in DEFAULT_PATHS}
    tracemalloc.start()
    first = build(paths)
    second = build(paths)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if tuple(map(canonical_bytes, first)) != tuple(map(canonical_bytes, second)):
        raise RuntimeError("Two clean Stage 2 runs differ")
    if peak > MAX_PEAK_MEMORY_BYTES:
        raise RuntimeError(
            f"Peak traced memory {peak} exceeds {MAX_PEAK_MEMORY_BYTES}"
        )
    statuses = {
        "groups": write_atomic(args.groups_output, canonical_bytes(first[0])),
        "observations": write_atomic(
            args.observations_output, canonical_bytes(first[1])
        ),
    }
    conflicts = [name for name, status in statuses.items() if status == "conflict"]
    if conflicts:
        raise RuntimeError(
            "Refusing to replace differing Stage 2 artifacts: "
            + ", ".join(conflicts)
        )
    print(json.dumps({
        "statuses": statuses,
        "group_count": len(first[0]["records"]),
        "observation_summary": first[1]["summary"],
        "peak_traced_memory_bytes": peak,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

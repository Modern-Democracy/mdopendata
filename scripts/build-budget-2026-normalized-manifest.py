"""Build the deterministic 2026/2027 full-document normalized manifest."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
NORM = BASE / "normalization"
OUTPUT = BASE / "normalized-import-manifest.json"
REPORT = BASE / "normalized-import-manifest-report.json"

DOCUMENT_KEY = "2026-2027"
DOCUMENT_SHA = "d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac"
RAW_IMPORT_VERSION = "full-2"
PERIODS = {
    "2025-2026-budget": ("2025-05-01", "2026-04-30", "budget"),
    "2025-2026-forecast": ("2025-05-01", "2026-04-30", "forecast"),
    "2026-2027-budget": ("2026-05-01", "2027-04-30", "budget"),
}
PROFILE_SCHEDULE_PAGES = {
    **{page: {111} for page in range(112, 117)},
    **{page: {117} for page in range(118, 120)},
    121: {120},
    **{page: {122, 123} for page in range(124, 127)},
    **{page: {127} for page in range(128, 133)},
    **{page: {133, 134, 135} for page in range(136, 144)},
}
PROFILE_PROJECT_LINKS = {
    "downtown-tree-planters": ["downtown-tree-pits-and-planters"],
    "victoria-park-ev-charger": ["ev-charger"],
    "public-transit-buses": ["buses"],
    "new-fire-station": ["new-fire-station-build"],
    "new-city-website": ["new-charlottetown-ca-website"],
    "multi-use-outdoor-facility": ["multi-sport-outdoor-facility"],
    "east-royalty-landfill-old-road-and-active-transportation-pathway": ["east-royalty-park-old-road-at-pathway"],
    "investigative-tools-and-technology": ["investigative-tools-tech"],
    "euston-st-redevelopment": ["euston-street-redevelopment"],
    "sherwood-recreation-hall-upgrades": ["sherwood-rec-hall-upgrades"],
    "north-river-road-capital-drive-intersection-upgrades": ["north-river-road-mp-phase-1", "capital-drive-phase-1"],
    "new-sidewalk-construction": ["sidewalks-new-construction"],
}
ENTITY_BY_SECTION = {
    "water-sewer-operating": "charlottetown-water-sewer",
    "appendix-water-sewer-debt": "charlottetown-water-sewer",
    "civic-centre-operating": "charlottetown-civic-centre-management",
    "bell-aliant-operating": "bell-aliant-centre",
}
UNIT_MAP = {"CAD": "cad", "CAD_per_100_assessed_value": "cad_per_100_assessed",
            "CAD_per_year": "cad_per_year", "CAD_per_day": "cad_per_day",
            "CAD_per_cubic_metre": "cad_per_cubic_metre"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    values = {x["value_id"]: x for x in load(BASE / "raw-tables/source_values.json")["records"]}
    candidates = {x["canonical_key"]: x for x in load(BASE / "canonical-table-inventory.json")["records"]}
    rows, profiles, instruments, statement_relationships = [], [], [], []

    def add(section: str, row: dict, fact_list: list[dict], entity: str | None = None,
            statement_key: str | None = None, extension: dict | None = None) -> None:
        rows.append({"section": section, "row": row, "facts": fact_list,
                     "entity": entity, "statement_key": statement_key, "extension": extension})

    for path in sorted(NORM.glob("*-row-mapping.json")):
        data = load(path); section = data["section_key"]
        if "summary_rows" in data:
            summary_statement_key = f"{section}-statement"
            detail_statement_key = f"{section}-detail-statement"
            for row in data["summary_rows"]:
                add(section, row, row["facts"], statement_key=summary_statement_key)
            for row in data.get("supporting_rows", []):
                add(section, row, [row], statement_key=detail_statement_key)
            if data.get("supporting_rows"):
                statement_relationships.append({
                    "parent_statement_key": summary_statement_key,
                    "child_statement_key": detail_statement_key,
                    "relationship_type": "summary_detail",
                })
        elif path.name == "bell-aliant-department-row-mapping.json":
            for page in data["pages"]:
                for row in page["rows"]: add(section, row, row["facts"])
        elif path.name == "civic-centre-operating-row-mapping.json":
            for row in data["rows"]: add(section, row, [row])
        elif path.name == "tax-utility-rate-row-mapping.json":
            for row in data["rows"]:
                fact = dict(row); fact["document_period_key"] = data["period_key"]
                add(section, row, [fact], row["reporting_entity_key"])
        elif path.name == "water-sewer-debt-row-mapping.json":
            for item in data["instruments"]:
                key = slug(item["raw_label"])
                instruments.append({"key": key, "raw_label": item["raw_label"],
                                    "maturity_year": item.get("maturity_year")})
                add(section, item, item["facts"], extension={"debt_instrument_key": key})
            total = data["reported_total"]
            add(section, total, total["facts"])
        elif "rows" in data and all("facts" in row for row in data["rows"]):
            for row in data["rows"]: add(section, row, row["facts"])
        else:
            raise ValueError(f"Unsupported row mapping shape: {path.name}")

    capital = load(NORM / "capital-budget-schedule-mapping.json")
    for schedule in capital["schedules"]:
        statement = schedule.get("section_key") or f"capital-page-{schedule['page_number']}"
        for row in schedule["rows"]:
            project_key = slug(row["raw_label"])
            is_project = row.get("line_kind") == "detail" and row.get("aggregation_role") == "additive_detail"
            add(statement, row, row["facts"], statement_key=f"{statement}-capital",
                extension={"capital_project_key": project_key} if is_project else None)

    profile_data = load(NORM / "capital-project-profile-mapping.json")
    for profile in profile_data["profiles"]:
        key = slug(profile["project"] or profile["title"])
        profiles.append({"key": key, "capital_project_keys": [key], "page_number": profile["page_number"],
                         "candidate_key": profile["candidate_key"], "title": profile["title"],
                         "department": profile["department"], "project": profile["project"],
                         "source_row_ids": profile["source_row_ids"],
                         "description_lines": profile["description_lines"],
                         "strategic_alignment": profile["strategic_alignment"],
                         "review_status": profile["review_status"]})

    if len(rows) != 1163:
        raise ValueError(f"Expected 1163 mapped rows, found {len(rows)}")
    if sum(len(x["facts"]) for x in rows) != 2165:
        raise ValueError("Expected 2165 mapped facts")

    source_tables, statements, line_items, facts, fact_sources = {}, {}, [], [], []
    organization_units = set()
    capital_projects, capital_aliases, capital_facts, debt_facts = {}, [], [], []
    collision_keys = set()

    for wrapped in rows:
        section, row = wrapped["section"], wrapped["row"]
        entity = wrapped["entity"] or row.get("reporting_entity_key") or ENTITY_BY_SECTION.get(section, "city-of-charlottetown")
        statement_key = wrapped["statement_key"] or f"{section}-statement"
        statements.setdefault(statement_key, {"key": statement_key, "document_key": DOCUMENT_KEY,
            "reporting_entity_key": entity, "fund_key": None,
            "statement_kind": "capital" if section.startswith("capital-") else "debt" if "debt" in section else "tax" if section == "operating-supporting-schedules" and "rate_type" in row else "operating",
            "title": section.replace("-", " ").title()})
        row_id = row["row_id"]
        line_key = f"{statement_key}:{row_id}"
        if line_key in collision_keys: raise ValueError(f"Duplicate line key: {line_key}")
        collision_keys.add(line_key)
        role = row.get("aggregation_role")
        role = {"additive_detail": "detail", "supporting_breakdown": "non_additive"}.get(role, role)
        if role == "reported_total": role = "total" if row.get("line_kind") == "total" else "subtotal"
        if role == "deduction": role = "non_additive"
        if role is None and "rate_type" in row: role = "non_additive"
        if role not in {"detail", "subtotal", "total", "memo", "non_additive"}:
            raise ValueError(f"Unmapped aggregation role {role!r} for {row_id}")
        unit_key = row.get("organization_unit_key")
        if unit_key: organization_units.add((entity, unit_key))
        line_items.append({"key": line_key, "statement_key": statement_key, "source_row_id": row_id,
            "parent_line_key": None, "raw_label": row["raw_label"], "display_label": row["raw_label"],
            "line_kind": row.get("line_kind", "detail"), "aggregation_role": role,
            "organization_unit_key": unit_key, "review_status": row.get("review_status")})

        ext = wrapped["extension"] or {}
        if "capital_project_key" in ext:
            pkey = ext["capital_project_key"]
            capital_projects.setdefault(pkey, {"key": pkey, "reporting_entity_key": entity,
                                               "display_name": row["raw_label"],
                                               "schedule_page": int(re.search(r"_p(\d+)_", row_id).group(1))})
            capital_aliases.append({"project_key": pkey, "document_key": DOCUMENT_KEY,
                                    "raw_label": row["raw_label"], "source_row_id": row_id})
        for fact in wrapped["facts"]:
            source_id = fact["source_value_id"]
            source = values[source_id]
            table_key = f"{source['table_id']}:{RAW_IMPORT_VERSION}"
            source_tables.setdefault(table_key, {"key": table_key, "document_key": DOCUMENT_KEY,
                                                  "page_number": source["page_number"]})
            period = fact.get("document_period_key")
            if period not in PERIODS: raise ValueError(f"Unknown period {period!r} for {source_id}")
            if fact.get("amount_type") in {"balance", "principal", "interest"}:
                amount = fact["amount_type"]
            elif fact.get("amount_type") == "partner_funding": amount = "funding_deduction"
            elif section.startswith("capital-"):
                amount = "net" if role in {"total", "subtotal"} and "net" in row["raw_label"].lower() else "gross"
            elif "rate_type" in row: amount = "actual"
            else: amount = PERIODS[period][2]
            unit = UNIT_MAP[fact["measure_unit"]]
            dp_key = f"{DOCUMENT_KEY}:{table_key}:column-{source['value_index']}:{PERIODS[period][2]}"
            fact_key = f"{line_key}:{dp_key}:{amount}:{unit}"
            value_state = {"reported_value": "reported"}.get(fact["value_state"], fact["value_state"])
            facts.append({"key": fact_key, "line_key": line_key, "document_period_key": dp_key,
                          "amount_type": amount, "measure_unit": unit,
                          "value_numeric": fact.get("numeric_value"), "value_text": None,
                          "value_state": value_state, "review_status": row.get("review_status")})
            fact_sources.append({"key": f"{fact_key}:{source_id}:reported_value:1", "fact_key": fact_key,
                                 "source_value_id": source_id,
                                 "source_cell_key": f"{source['table_id']}:{RAW_IMPORT_VERSION}:{source['row_id']}:column-{source['value_index']}",
                                 "source_role": "reported_value", "source_order": 1})
            if "capital_project_key" in ext: capital_facts.append({"project_key": ext["capital_project_key"], "fact_key": fact_key})
            if "debt_instrument_key" in ext: debt_facts.append({"instrument_key": ext["debt_instrument_key"], "fact_key": fact_key})

    document_periods = {}
    for fact in facts:
        key = fact["document_period_key"]
        parts = key.rsplit(":", 2)
        table_key = parts[0].split(":", 1)[1]
        column_index = int(parts[1].removeprefix("column-"))
        role = parts[2]
        fiscal_key = next(p for p, spec in PERIODS.items() if spec[2] == role and any(
            f["document_period_key"] == key and values[next(s["source_value_id"] for s in fact_sources if s["fact_key"] == f["key"])]["value_index"] == column_index for f in facts))
        # Period label on the originating artifact disambiguates budget years.
        source_fact = next(f for f in facts if f["document_period_key"] == key)
        source_link = next(s for s in fact_sources if s["fact_key"] == source_fact["key"])
        source_id = source_link["source_value_id"]
        original = next(source_fact for wrapped in rows for source_fact in wrapped["facts"] if source_fact["source_value_id"] == source_id)
        fiscal_key = original["document_period_key"]
        document_periods[key] = {"key": key, "document_key": DOCUMENT_KEY, "source_table_key": table_key,
                                 "source_column_index": column_index, "fiscal_period_key": fiscal_key,
                                 "period_role": role}

    unresolved_profiles = []
    for profile in profiles:
        if profile["key"] in capital_projects:
            continue
        links = PROFILE_PROJECT_LINKS.get(profile["key"])
        if links:
            missing = [key for key in links if key not in capital_projects]
            if missing: raise ValueError(f"Approved profile links missing schedule projects: {missing}")
            profile["capital_project_keys"] = links
        elif profile["key"] == "vehicle-equipment":
            profile["capital_project_keys"] = []
            profile["review_exception"] = "awaiting_city_clarification_no_schedule_residual"
        else:
            unresolved_profiles.append(profile["key"])
            profile["capital_project_keys"] = []

    statement_keys = set(statements)
    for relationship in statement_relationships:
        if relationship["parent_statement_key"] not in statement_keys:
            raise ValueError(f"Missing relationship parent statement: {relationship}")
        if relationship["child_statement_key"] not in statement_keys:
            raise ValueError(f"Missing relationship child statement: {relationship}")
        if relationship["parent_statement_key"] == relationship["child_statement_key"]:
            raise ValueError(f"Statement relationship cannot self-reference: {relationship}")
    relationship_keys = {
        (x["parent_statement_key"], x["child_statement_key"], x["relationship_type"])
        for x in statement_relationships
    }
    if len(relationship_keys) != len(statement_relationships):
        raise ValueError("Duplicate statement relationship")

    manifest = {
        "manifest_metadata": {"schema_version": 1, "document_key": DOCUMENT_KEY, "status": "gate_3_review",
                              "generator": "build-budget-2026-normalized-manifest.py"},
        "source_documents": [{"key": DOCUMENT_KEY, "sha256": DOCUMENT_SHA}],
        "source_tables": sorted(source_tables.values(), key=lambda x: x["key"]),
        "reporting_entities": [
            {"key": "bell-aliant-centre", "display_name": "Bell Aliant Centre", "entity_type": "facility"},
            {"key": "charlottetown-civic-centre-management", "display_name": "Charlottetown Civic Centre Management Inc.", "entity_type": "facility"},
            {"key": "charlottetown-water-sewer", "display_name": "Charlottetown Water and Sewer", "entity_type": "utility"},
            {"key": "city-of-charlottetown", "display_name": "City of Charlottetown", "entity_type": "municipality"}],
        "organization_units": [{"key": k, "reporting_entity_key": e} for e, k in sorted(organization_units)],
        "funds": [],
        "fiscal_periods": [{"key": k, "start_date": v[0], "end_date": v[1], "period_kind": v[2]} for k, v in PERIODS.items()],
        "document_periods": sorted(document_periods.values(), key=lambda x: x["key"]),
        "statements": sorted(statements.values(), key=lambda x: x["key"]),
        "statement_relationships": sorted(statement_relationships, key=lambda x: (
            x["parent_statement_key"], x["child_statement_key"], x["relationship_type"])),
        "line_items": sorted(line_items, key=lambda x: x["key"]),
        "facts": sorted(facts, key=lambda x: x["key"]),
        "fact_sources": sorted(fact_sources, key=lambda x: x["key"]),
        "capital_projects": sorted(capital_projects.values(), key=lambda x: x["key"]),
        "capital_project_references": sorted([
            {"key": f"{DOCUMENT_KEY}:{alias['source_row_id']}:{alias['project_key']}",
             "project_key": alias["project_key"], "source_table_key": alias["source_row_id"].rsplit("_r", 1)[0] + ":full-2",
             "source_row_id": alias["source_row_id"], "raw_label": alias["raw_label"],
             "reference_kind": "capital_schedule", "document_adoption_state": "adopted", "identity_evidence": "exact"}
            for alias in capital_aliases
        ], key=lambda x: x["key"]),
        "capital_project_aliases": sorted(capital_aliases, key=lambda x: (x["project_key"], x["source_row_id"])),
        "capital_project_profiles": sorted(profiles, key=lambda x: (x["key"], x["page_number"])),
        "capital_project_facts": sorted(capital_facts, key=lambda x: (x["project_key"], x["fact_key"])),
        "debt_instruments": sorted(instruments, key=lambda x: x["key"]),
        "debt_facts": sorted(debt_facts, key=lambda x: (x["instrument_key"], x["fact_key"])),
        "reconciliations": [], "review_issues": [], "expected_counts": []}
    counts = {k: len(v) for k, v in manifest.items() if isinstance(v, list)}
    manifest["expected_counts"] = [{"record_type": k, "count": v} for k, v in sorted(counts.items())]
    manifest_hash = canonical_hash(manifest)
    manifest["manifest_metadata"]["manifest_hash_without_hash_field"] = manifest_hash
    OUTPUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    alias_review = []
    for profile in profiles:
        if profile["capital_project_keys"]:
            continue
        allowed_pages = PROFILE_SCHEDULE_PAGES[profile["page_number"]]
        relevant_projects = {key: item for key, item in capital_projects.items()
                             if item["schedule_page"] in allowed_pages}
        ranked = sorted(
            ({"capital_project_key": key,
              "schedule_label": relevant_projects[key]["display_name"],
              "similarity": round(SequenceMatcher(None, profile["key"], key).ratio(), 4)}
             for key in relevant_projects),
            key=lambda item: (-item["similarity"], item["capital_project_key"]),
        )[:5]
        alias_review.append({"profile_key": profile["key"], "page_number": profile["page_number"],
                             "title": profile["title"], "department": profile["department"],
                             "project": profile["project"], "candidate_schedule_projects": ranked})

    report = {"schema_version": 1, "manifest_hash": manifest_hash, "counts": counts,
              "fact_counts_by_amount_type": dict(sorted(Counter(x["amount_type"] for x in facts).items())),
              "fact_counts_by_measure_unit": dict(sorted(Counter(x["measure_unit"] for x in facts).items())),
              "fact_counts_by_value_state": dict(sorted(Counter(x["value_state"] for x in facts).items())),
              "identity_collisions": [],
              "unresolved_decisions": [{"issue": "capital_profile_project_alias_unresolved", "profile_key": key}
                                       for key in unresolved_profiles],
              "extension_links": {"capital_profiles": len(profiles),
                                  "capital_profiles_linked": sum(bool(x["capital_project_keys"]) for x in profiles),
                                  "capital_profile_project_links": sum(len(x["capital_project_keys"]) for x in profiles),
                                  "capital_profiles_unresolved": len(unresolved_profiles),
                                  "debt_instruments": len(instruments), "debt_facts": len(debt_facts)},
              "capital_profile_alias_review": alias_review,
              "review_exceptions": [{"profile_key": "vehicle-equipment",
                                     "reason": "awaiting_city_clarification_no_schedule_residual"}],
              "representative_retirement_fact_count": 19}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(line_items)} lines and {len(facts)} facts; manifest {manifest_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

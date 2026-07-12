"""Build deterministic normalized manifests for reviewed prior-year budgets."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown"
DOCUMENTS = ("2024-2025", "2025-2026")
RAW_VERSION_BY_DOCUMENT = {"2024-2025": "full-3", "2025-2026": "full-3"}
ENTITY_SPECS = {
    "city-of-charlottetown": ("City of Charlottetown", "municipality"),
    "charlottetown-water-and-sewer": ("Charlottetown Water and Sewer", "utility"),
    "bell-aliant-centre": ("Bell Aliant Centre", "facility"),
}
UNIT_MAP = {
    "CAD": "cad",
    "CAD_per_100_assessed_value": "cad_per_100_assessed",
    "CAD_per_year": "cad_per_year",
    "CAD_per_day": "cad_per_day",
    "CAD_per_cubic_metre": "cad_per_cubic_metre",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def period_spec(key: str) -> dict:
    match = re.fullmatch(r"(\d{4})-(\d{4})-(budget|forecast|actual)", key)
    if not match:
        raise ValueError(f"Unsupported period key: {key}")
    start, end, kind = match.groups()
    return {"key": key, "start_date": f"{start}-04-01", "end_date": f"{end}-03-31", "period_kind": kind}


def main() -> int:
    registry = load(BASE / "capital-project-registry.json")
    projects_by_key = {item["project_key"]: item for item in registry["projects"]}
    for document in DOCUMENTS:
        raw_version = RAW_VERSION_BY_DOCUMENT[document]
        root = BASE / document
        mapping = load(root / "phase-2-row-mapping-input.json")
        aliases = load(root / "capital-project-alias-review.json")["records"]
        identities = {item["table_key"]: item for item in load(root / "capital-project-profile-identity-review.json")["records"]}
        raw_values = {item["value_id"]: item for item in load(root / "raw-tables/source_values.json")["records"]}
        source_pdf = ROOT / load(root / "table_manifest.json")["source_pdf"]
        source_sha256 = hashlib.sha256(source_pdf.read_bytes()).hexdigest()

        statements, lines, facts, sources = [], [], [], []
        document_periods: dict[tuple[str, int, str], dict] = {}
        fiscal_period_keys: set[str] = set()
        entities: set[str] = set()
        fact_by_row: dict[str, list[str]] = {}

        for record in mapping["records"]:
            rows_by_entity: dict[str, list[dict]] = defaultdict(list)
            for row in record["rows"]:
                if row.get("facts"):
                    rows_by_entity[row.get("reporting_entity_key") or "city-of-charlottetown"].append(row)
            for entity, rows_with_facts in sorted(rows_by_entity.items()):
                entity_suffix = f"-{entity}" if len(rows_by_entity) > 1 else ""
                statement_key = f"{document}-{record['table_family']}-p{record['page_start']:03d}{entity_suffix}"
                entities.add(entity)
                statements.append({
                    "key": statement_key, "document_key": document,
                    "reporting_entity_key": entity, "fund_key": None,
                    "statement_kind": record["table_family"],
                    "title": f"{record['table_family'].replace('_', ' ').title()} - PDF page {record['page_start']}",
                })
                for row in rows_with_facts:
                    line_key = f"{statement_key}:{row['row_id']}"
                    raw_label = row.get("raw_label") or row.get("source_group_label") or row["raw_text"]
                    lines.append({
                        "key": line_key, "statement_key": statement_key,
                        "source_row_id": row["row_id"], "parent_line_key": None,
                        "raw_label": raw_label, "display_label": row.get("normalized_label") or raw_label,
                        "line_kind": row["row_semantics"], "aggregation_role": "detail" if row["aggregation_role"] == "deduction" else row["aggregation_role"],
                        "organization_unit_key": None, "review_status": "approved",
                    })
                    for index, fact in enumerate(row["facts"], 1):
                        value = raw_values[fact["source_value_id"]]
                        source_table_key = f"{record['table_id']}:{raw_version}"
                        column_index = int(value["value_index"])
                        period_role = fact["document_period_key"].rsplit("-", 1)[-1]
                        dp_tuple = (source_table_key, column_index, period_role)
                        dp_key = f"{document}:{source_table_key}:column-{column_index}:{period_role}"
                        document_periods[dp_tuple] = {
                            "key": dp_key, "document_key": document, "source_table_key": source_table_key,
                            "source_column_index": column_index, "fiscal_period_key": fact["document_period_key"],
                            "period_role": period_role,
                        }
                        fiscal_period_keys.add(fact["document_period_key"])
                        amount_type = fact["amount_type"]
                        if record["table_family"] == "capital_budget_schedule":
                            if row["aggregation_role"] == "deduction":
                                amount_type = "funding_deduction"
                            elif (row.get("normalized_label") or row.get("raw_label") or "").lower().startswith("net "):
                                amount_type = "net"
                            else:
                                amount_type = "gross"
                        elif amount_type == "reported_amount":
                            amount_type = period_role
                        elif amount_type == "partner_funding":
                            amount_type = "funding_deduction"
                        unit = UNIT_MAP[fact["measure_unit"]]
                        fact_key = f"{line_key}:{dp_key}:{amount_type}:{unit}:{index}"
                        value_state = {"reported_value": "reported", "reported_zero": "reported_zero", "dash_unresolved": "dash_unresolved"}[fact["value_state"]]
                        facts.append({
                            "key": fact_key, "line_key": line_key, "document_period_key": dp_key,
                            "amount_type": amount_type, "measure_unit": unit,
                            "value_numeric": fact["numeric_value"], "value_text": None,
                            "value_state": value_state, "review_status": "approved",
                        })
                        source_cell_key = f"{source_table_key}:{row['row_id']}:column-{column_index}"
                        sources.append({
                            "key": f"{fact_key}:{fact['source_value_id']}:reported_value:1",
                            "fact_key": fact_key, "source_value_id": fact["source_value_id"],
                            "source_cell_key": source_cell_key, "source_role": "reported_value", "source_order": 1,
                        })
                        fact_by_row.setdefault(row["row_id"], []).append(fact_key)

        project_keys = sorted({key for item in aliases for key in item.get("capital_project_keys", [])})
        capital_projects = [{
            "key": key, "reporting_entity_key": "city-of-charlottetown",
            "display_name": projects_by_key.get(key, {}).get("display_name", key.replace("-", " ").title()),
            "schedule_page": None,
        } for key in project_keys]
        entities.add("city-of-charlottetown")
        references, project_aliases, profiles = [], [], []
        profile_records = {record["table_id"]: record for record in mapping["records"] if record["table_family"] == "capital_project_profile"}
        for alias in aliases:
            identity = identities[alias["table_key"]]
            table_id = f"ctown_budget_{document.replace('-', '_')}_p{alias['page_start']:03d}"
            profile_record = profile_records.get(table_id)
            source_rows = [row["row_id"] for row in profile_record["rows"]] if profile_record else []
            source_row = source_rows[0] if source_rows else None
            raw_label = identity["source_title"] or identity["source_project"] or identity["title_guess"]
            for key in alias.get("capital_project_keys", []):
                references.append({
                    "key": f"{document}:{alias['table_key']}:{key}", "project_key": key,
                    "source_table_key": f"{table_id}:{raw_version}", "source_row_id": source_row,
                    "raw_label": raw_label, "reference_kind": "capital_profile",
                    "document_adoption_state": "adopted", "identity_evidence": "exact" if alias["alias_decision"] == "mapped_existing" else "strong",
                })
                project_aliases.append({"project_key": key, "document_key": document, "raw_label": raw_label, "source_row_id": source_row})
            if source_rows:
                narrative = [row["raw_text"] for row in profile_record["rows"] if row["raw_text"]]
                profiles.append({
                    "key": f"{document}-{slug(raw_label)}", "capital_project_keys": alias.get("capital_project_keys", []),
                    "page_number": alias["page_start"], "candidate_key": alias["table_key"],
                    "title": identity["source_title"] or identity["title_guess"], "department": None,
                    "project": identity["source_project"],
                    "source_row_ids": {"title": source_rows[:1], "department": [], "project": source_rows[:1], "description": source_rows, "strategic_alignment": []},
                    "description_lines": narrative, "strategic_alignment": [], "review_status": "approved_narrative_only",
                })

        alias_key_by_slug = {}
        for alias in aliases:
            for project_key in alias.get("capital_project_keys", []):
                for label in (alias.get("source_title"), alias.get("source_project"), alias.get("title_guess")):
                    if label:
                        alias_key_by_slug[slug(label)] = project_key
        facts_by_line: dict[str, list[str]] = defaultdict(list)
        for fact in facts:
            facts_by_line[fact["line_key"]].append(fact["key"])
        capital_project_facts = []
        for line in lines:
            if "capital_budget_schedule" not in line["statement_key"]:
                continue
            project_key = alias_key_by_slug.get(slug(line["display_label"]))
            if project_key:
                capital_project_facts.extend({"project_key": project_key, "fact_key": fact_key} for fact_key in facts_by_line[line["key"]])

        debt_instruments, debt_facts = [], []
        debt_path = root / "debt-identity-review.json"
        if debt_path.exists():
            for review in load(debt_path)["records"]:
                for instrument in review["instrument_records"]:
                    key = instrument.get("debt_instrument_key")
                    if not key:
                        continue
                    debt_instruments.append({
                        "key": key, "reporting_entity_key": instrument["reporting_entity_key"],
                        "raw_label": instrument["raw_label"], "normalized_label": instrument.get("normalized_label") or instrument["raw_label"],
                        "maturity_year": int(instrument["maturity_year"]) if instrument.get("maturity_year") else None,
                    })
                    for fact_key in fact_by_row.get(instrument["row_id"], []):
                        debt_facts.append({"instrument_key": key, "fact_key": fact_key})

        source_tables = sorted(
            {source["source_cell_key"].split(":", 1)[0] + ":" + raw_version for source in sources}
            | {reference["source_table_key"] for reference in references}
        )
        manifest = {
            "manifest_metadata": {"schema_version": 1, "document_key": document, "status": "gate_3_review", "generator": Path(__file__).name},
            "source_documents": [{"key": document, "sha256": source_sha256}],
            "source_tables": [{"key": key, "document_key": document, "page_number": int(re.search(r"_p(\d+)", key).group(1))} for key in source_tables],
            "reporting_entities": [{"key": key, "display_name": ENTITY_SPECS[key][0], "entity_type": ENTITY_SPECS[key][1]} for key in sorted(entities)],
            "organization_units": [], "funds": [],
            "fiscal_periods": [period_spec(key) for key in sorted(fiscal_period_keys)],
            "document_periods": sorted(document_periods.values(), key=lambda item: item["key"]),
            "statements": statements, "statement_relationships": [], "line_items": lines,
            "facts": facts, "fact_sources": sources,
            "capital_projects": capital_projects, "capital_project_references": references,
            "capital_project_aliases": project_aliases, "capital_project_profiles": profiles,
            "capital_project_facts": capital_project_facts, "debt_instruments": debt_instruments, "debt_facts": debt_facts,
            "reconciliations": [], "review_issues": [],
        }
        count_keys = [key for key, value in manifest.items() if isinstance(value, list) and key not in {"reconciliations", "review_issues"}]
        manifest["expected_counts"] = [{"record_type": key, "count": len(manifest[key])} for key in sorted(count_keys)]
        manifest["manifest_metadata"]["manifest_hash_without_hash_field"] = canonical_hash(manifest)
        output = root / "normalized-import-manifest.json"
        output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report = {
            "document_key": document, "manifest_hash": manifest["manifest_metadata"]["manifest_hash_without_hash_field"],
            "counts": {key: len(value) for key, value in manifest.items() if isinstance(value, list)},
            "fact_counts_by_period": dict(Counter(item["document_period_key"].split(":")[-1] for item in facts)),
            "status": "approved" if mapping["summary"]["unresolved_row_count"] == 0 else "blocked",
        }
        (root / "normalized-import-manifest-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

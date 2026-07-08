"""Build reviewed inventory and normalization-review artifacts for 2026/2027."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"

# Reviewed document structure. Page-level canonical identities remain stable; these
# ranges only establish the source section that must be reviewed as a unit.
SECTION_RULES = [
    (12, 12, "budget-overview", "Budget overview"),
    (15, 15, "funding-taxation", "Funding and taxation"),
    (18, 20, "consolidated-operating", "Consolidated operating budget"),
    (21, 23, "operating-supporting-schedules", "Operating supporting schedules"),
    (28, 33, "city-government", "City Government Services"),
    (35, 41, "economic-tourism-culture", "Economic, Tourism and Cultural Development"),
    (43, 46, "environment-sustainability-transit", "Environment, Sustainability and Transit"),
    (48, 50, "finance-audit-fiscal", "Finance, Audit and Fiscal Services"),
    (52, 55, "fire-services", "Fire Services"),
    (57, 60, "human-resources", "Human Resources"),
    (62, 64, "mayor-council", "Mayor and Council"),
    (66, 74, "parks-recreation", "Parks and Recreation"),
    (76, 80, "planning-heritage", "Planning and Heritage"),
    (82, 85, "police-services", "Police Services"),
    (87, 92, "public-works-buildings", "Public Works and Municipal Buildings"),
    (94, 99, "water-sewer-operating", "Charlottetown Water and Sewer Services"),
    (101, 104, "civic-centre-operating", "Charlottetown Civic Centre Management Inc."),
    (105, 108, "bell-aliant-operating", "Bell Aliant Centre operating budget"),
    (110, 110, "capital-consolidated", "Consolidated capital budget"),
    (111, 116, "capital-environment-transit", "Environment, Sustainability and Transit capital"),
    (117, 119, "capital-fire", "Fire and Emergency Preparedness capital"),
    (120, 121, "capital-information-technology", "Information Technology capital"),
    (122, 126, "capital-parks-recreation", "Parks and Recreation capital"),
    (127, 132, "capital-police", "Police capital"),
    (133, 143, "capital-public-works", "Public Works capital"),
    (144, 144, "capital-water-sewer", "Charlottetown Water and Sewer capital"),
    (146, 146, "capital-eastlink", "Charlottetown Eastlink Centre capital"),
    (147, 147, "capital-bell-aliant", "Charlottetown Bell Aliant Centre capital"),
    (149, 149, "appendix-tax", "Property tax appendix"),
    (151, 151, "appendix-city-debt", "City long-term debt appendix"),
    (153, 153, "appendix-water-sewer-debt", "Water and Sewer long-term debt appendix"),
]


def section_for(page: int) -> tuple[str, str]:
    matches = [(key, title) for start, end, key, title in SECTION_RULES if start <= page <= end]
    if len(matches) != 1:
        raise ValueError(f"Page {page} must belong to exactly one reviewed section")
    return matches[0]


def page_role(candidate: dict) -> str:
    page = int(candidate["page_start"])
    family = candidate["table_family"]
    if page in {18, 19, 105, 110}:
        return "summary"
    if family in {"operating_statement", "facility_operating_statement", "capital_budget_schedule", "debt_schedule", "tax_assessment_rate"}:
        return "statement"
    if family == "capital_project_profile":
        return "profile"
    if family == "operating_detail":
        return "detail"
    return "context"


def load(name: str) -> list[dict]:
    return json.loads((BASE / name).read_text(encoding="utf-8"))["records"]


def write(name: str, payload: object) -> None:
    path = BASE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def build_consolidated_operating_mapping() -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    mapped_rows = []
    entity = "city-of-charlottetown"
    parent = None
    for row in (item for item in rows if item["page_number"] == 20):
        text = row["trimmed_text"]
        if row["row_index"] == 5:
            entity = "city-of-charlottetown"
        elif row["row_index"] == 33:
            entity = "charlottetown-water-sewer"
        if not row["value_ids"]:
            if text in {"Revenue", "Expenses"}:
                parent = slug(text)
            continue
        label = row["cells"][0]
        is_total = label.startswith("Total ") or any(token in label for token in ("Surplus (Deficit)", "Profit (Loss)"))
        facts = []
        for value_id in row["value_ids"]:
            value = values[value_id]
            period = {1: "2025-2026-budget", 2: "2025-2026-forecast", 3: "2026-2027-budget"}[value["value_index"]]
            facts.append({
                "source_value_id": value_id,
                "document_period_key": period,
                "amount_type": "reported_amount",
                "measure_unit": "CAD",
                "value_state": "reported_value",
                "numeric_value": value["parsed_decimal"],
            })
        mapped_rows.append({
            "row_id": row["row_id"],
            "reporting_entity_key": entity,
            "line_key": f"{entity}-{slug(label)}",
            "raw_label": label,
            "source_section": parent,
            "line_kind": "total" if is_total else "detail",
            "aggregation_role": "reported_total" if is_total else "additive_detail",
            "facts": facts,
            "review_status": "approved",
        })
    write("normalization/consolidated-operating-row-mapping.json", {
        "schema_version": 1,
        "section_key": "consolidated-operating",
        "authoritative_candidate_key": "ctown-2026-2027-2026-2027-p020",
        "duplicate_summary_candidate_keys": ["ctown-2026-2027-2026-2027-p018", "ctown-2026-2027-2026-2027-p019"],
        "periods": [
            {"key": "2025-2026-budget", "source_label": "2025/2026 Budget", "role": "budget"},
            {"key": "2025-2026-forecast", "source_label": "2025/2026 Forecast", "role": "forecast"},
            {"key": "2026-2027-budget", "source_label": "2026/2027 Budget", "role": "budget"},
        ],
        "rows": mapped_rows,
        "review_note": "Pages 18 and 19 repeat 2026/2027 presentation totals from the authoritative three-period statement on page 20.",
    })


def build_operating_supporting_mapping() -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    periods = {1: "2025-2026-budget", 2: "2025-2026-forecast", 3: "2026-2027-budget"}
    mapped_rows = []
    unit = None
    headings = {"Fiscal Services", "Planning", "Police", "Cody Banks Arena", "Simmons Arena", "Other Revenue"}
    for row in (item for item in rows if item["page_number"] in {21, 22}):
        if row["trimmed_text"] in headings:
            unit = slug(row["trimmed_text"])
        if not row["value_ids"] or row["row_index"] <= 7:
            continue
        facts = []
        for value_id in row["value_ids"]:
            value = values[value_id]
            facts.append({
                "source_value_id": value_id,
                "document_period_key": periods[value["value_index"]],
                "amount_type": "reported_amount",
                "measure_unit": "CAD",
                "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
                "numeric_value": value["parsed_decimal"],
            })
        mapped_rows.append({
            "row_id": row["row_id"],
            "raw_label": row["cells"][0],
            "organization_unit_key": unit,
            "line_kind": "total" if row["trimmed_text"].startswith("Budget Item Totals") else "detail",
            "aggregation_role": "reported_total" if row["trimmed_text"].startswith("Budget Item Totals") else "additive_detail",
            "facts": facts,
            "review_status": "approved_extracted_values",
        })
    write("normalization/operating-supporting-row-mapping.json", {
        "schema_version": 1,
        "section_key": "operating-supporting-schedules",
        "candidate_keys": ["ctown-2026-2027-2026-2027-p021", "ctown-2026-2027-2026-2027-p022"],
        "mapping_status": "approved",
        "rows": mapped_rows,
        "blocking_rows": [],
    })

    rate_rows = []
    for row in (item for item in rows if item["page_number"] == 23 and item["row_index"] in set(range(4, 12)) | {15, 16, 17, 20, 21, 22, 23}):
        value = values[row["value_ids"][0]]
        if row["row_index"] <= 11:
            rate_type, unit_name = "property_tax", "CAD_per_100_assessed_value"
        elif row["row_index"] <= 17:
            rate_type, unit_name = "unmetered_utility", "CAD_per_year"
        elif "Base Rate" in row["trimmed_text"]:
            rate_type, unit_name = "metered_utility_base", "CAD_per_day"
        else:
            rate_type = "metered_utility_consumption"
            unit_name = "CAD_per_cubic_metre"
        rate_rows.append({
            "row_id": row["row_id"],
            "raw_label": row["cells"][0],
            "rate_type": rate_type,
            "reporting_entity_key": "city-of-charlottetown" if row["row_index"] <= 11 else "charlottetown-water-sewer",
            "measure_unit": unit_name,
            "source_value_id": value["value_id"],
            "numeric_value": value["parsed_decimal"],
            "value_state": "reported_value",
            "review_status": "approved",
        })
    write("normalization/tax-utility-rate-row-mapping.json", {
        "schema_version": 1,
        "section_key": "operating-supporting-schedules",
        "candidate_key": "ctown-2026-2027-2026-2027-p023",
        "period_key": "2026-2027-budget",
        "rows": rate_rows,
    })


def build_city_government_mapping() -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    periods = {1: "2025-2026-budget", 2: "2025-2026-forecast", 3: "2026-2027-budget"}
    summary_rows = []
    unit = None
    for row in (item for item in rows if item["page_number"] == 28):
        if row["trimmed_text"] in {"City Government", "Strategic Priorities", "Communications", "Information Technology"}:
            unit = slug(row["trimmed_text"])
        if not row["value_ids"] or row["row_index"] < 9:
            continue
        facts = []
        for value_id in row["value_ids"]:
            value = values[value_id]
            facts.append({
                "source_value_id": value_id,
                "document_period_key": periods[value["value_index"]],
                "numeric_value": value["parsed_decimal"],
                "measure_unit": "CAD",
                "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
            })
        is_total = row["trimmed_text"].startswith(("Total ", "Net "))
        summary_rows.append({
            "row_id": row["row_id"], "raw_label": row["cells"][0],
            "organization_unit_key": unit,
            "line_kind": "total" if is_total else "detail",
            "aggregation_role": "reported_total" if is_total else "additive_detail",
            "facts": facts, "review_status": "approved",
        })

    detail_rows = []
    current_label = None
    for row in (item for item in rows if item["page_number"] in {29, 30, 31, 32, 33}):
        text = row["trimmed_text"]
        if text.endswith(":"):
            current_label = text[:-1]
        monetary = [values[value_id] for value_id in row["value_ids"] if "," in values[value_id]["raw_value"]]
        if not monetary:
            continue
        value = monetary[-1]
        label = current_label or text
        detail_rows.append({
            "row_id": row["row_id"], "raw_label": label,
            "source_text": text,
            "document_period_key": "2026-2027-budget",
            "source_value_id": value["value_id"], "numeric_value": value["parsed_decimal"],
            "measure_unit": "CAD", "value_state": "reported_value",
            "aggregation_role": "supporting_breakdown", "review_status": "approved",
        })
        current_label = None
    write("normalization/city-government-row-mapping.json", {
        "schema_version": 1, "section_key": "city-government", "mapping_status": "approved",
        "authoritative_candidate_key": "ctown-2026-2027-2026-2027-p028",
        "supporting_candidate_keys": [f"ctown-2026-2027-2026-2027-p{page:03d}" for page in range(29, 34)],
        "summary_rows": summary_rows, "supporting_rows": detail_rows,
        "ignored_source_tokens": "Parenthetical staff counts and layout zeros/dashes are not monetary facts.",
    })


def build_departmental_operating_mapping(
    section_key: str, summary_pages: set[int], detail_pages: set[int], output_name: str,
    summary_row_overrides: dict[str, dict] | None = None,
) -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    periods = {1: "2025-2026-budget", 2: "2025-2026-forecast", 3: "2026-2027-budget"}
    summary_rows = []
    summary_row_overrides = summary_row_overrides or {}
    consumed_value_ids = {
        value_id for override in summary_row_overrides.values()
        for value_id in override.get("value_ids", [])
    }
    pending_label = None
    ignored_labels = {"Expenses"}
    for row in (item for item in rows if item["page_number"] in summary_pages):
        text = row["trimmed_text"]
        override = summary_row_overrides.get(row["row_id"])
        current_ids = override.get("value_ids", row["value_ids"]) if override else [
            value_id for value_id in row["value_ids"] if value_id not in consumed_value_ids
        ]
        current = [values[value_id] for value_id in current_ids]
        financial = [value for value in current if value["value_kind"] in {"number", "dash", "currency"}]
        if len(financial) == 3:
            label = override["label"] if override else (
                row["cells"][0] if not row["cells"][0][0].isdigit() and row["cells"][0] not in {"-", "--"} else pending_label
            )
            if not label:
                label = "__following_label__"
            facts = [{
                "source_value_id": value["value_id"], "document_period_key": periods[index],
                "numeric_value": value["parsed_decimal"], "measure_unit": "CAD",
                "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
            } for index, value in enumerate(financial, start=1)]
            is_total = label.startswith(("Total ", "Net ")) or label == "Expenditures"
            summary_rows.append({
                "row_id": row["row_id"], "raw_label": label,
                "line_kind": "total" if is_total else "detail",
                "aggregation_role": "reported_total" if is_total else "additive_detail",
                "facts": facts, "review_status": "approved",
            })
            pending_label = None
        elif not current and text.startswith(("Total ", "Net ")) and summary_rows and summary_rows[-1]["raw_label"] == "__following_label__":
            summary_rows[-1]["raw_label"] = text
            summary_rows[-1]["line_kind"] = "total"
            summary_rows[-1]["aggregation_role"] = "reported_total"
        elif not current and text not in ignored_labels and not text.startswith(("CITY OF", "2026/2027", "2025/2026")):
            pending_label = text.rstrip(":")

    detail_rows = []
    pending_label = None
    for row in (item for item in rows if item["page_number"] in detail_pages):
        text = row["trimmed_text"]
        current = [values[value_id] for value_id in row["value_ids"]]
        monetary = [value for value in current if value["value_kind"] in {"number", "currency"} and value["parsed_decimal"] is not None and abs(float(value["parsed_decimal"])) >= 100]
        if monetary:
            value = monetary[-1]
            label = pending_label or (row["cells"][0] if not row["cells"][0][0].isdigit() else text)
            detail_rows.append({
                "row_id": row["row_id"], "raw_label": label, "source_text": text,
                "document_period_key": "2026-2027-budget", "source_value_id": value["value_id"],
                "numeric_value": value["parsed_decimal"], "measure_unit": "CAD",
                "value_state": "reported_value", "aggregation_role": "supporting_breakdown",
                "review_status": "approved",
            })
            pending_label = None
        elif text.endswith(":"):
            pending_label = text[:-1]
    if any(row["raw_label"] == "__following_label__" for row in summary_rows):
        raise ValueError(f"Unresolved following label in {section_key}")
    write(f"normalization/{output_name}", {
        "schema_version": 1, "section_key": section_key, "mapping_status": "approved",
        "summary_candidate_keys": [f"ctown-2026-2027-2026-2027-p{page:03d}" for page in sorted(summary_pages)],
        "supporting_candidate_keys": [f"ctown-2026-2027-2026-2027-p{page:03d}" for page in sorted(detail_pages)],
        "summary_rows": summary_rows, "supporting_rows": detail_rows,
    })


def build_capital_mappings(schedule_pages: set[int], profile_pages: set[int]) -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    schedules = []
    for page in sorted(schedule_pages):
        mapped_rows = []
        for row in (item for item in rows if item["page_number"] == page):
            financial = [values[value_id] for value_id in row["value_ids"] if values[value_id]["value_kind"] in {"number", "currency", "dash"}]
            if not financial or row["row_index"] <= 3:
                continue
            label = row["cells"][0]
            role = "deduction" if label.startswith("Less:") else "reported_total" if label.startswith(("Total ", "Net Total ")) else "additive_detail"
            periods = ["2025-2026-budget", "2026-2027-budget"] if page == 110 else ["2026-2027-budget"]
            facts = [{
                "source_value_id": value["value_id"], "document_period_key": period,
                "numeric_value": value["parsed_decimal"], "measure_unit": "CAD",
                "amount_type": "partner_funding" if role == "deduction" else "reported_amount",
                "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
            } for period, value in zip(periods, financial[-len(periods):])]
            mapped_rows.append({
                "row_id": row["row_id"], "raw_label": label,
                "line_kind": "total" if role == "reported_total" else "detail",
                "aggregation_role": role, "facts": facts, "review_status": "approved",
            })
        schedules.append({"page_number": page, "rows": mapped_rows})
    write("normalization/capital-budget-schedule-mapping.json", {
        "schema_version": 1, "mapping_status": "approved", "schedules": schedules,
    })

    profiles = []
    for page in sorted(profile_pages):
        page_rows = [row for row in rows if row["page_number"] == page]
        text = [row["trimmed_text"] for row in page_rows]
        department_index = next((i for i, line in enumerate(text) if line.startswith("Department:")), None)
        project_index = next((i for i, line in enumerate(text) if line.startswith("Project:")), None)
        description_start = text.index("Project Description") + 1 if "Project Description" in text else None
        alignment_start = text.index("Strategic Alignment") if "Strategic Alignment" in text else len(text)
        if department_index is None or project_index is None or description_start is None:
            raise ValueError(f"Capital profile page {page} lacks required field boundaries")
        if not (0 < department_index < project_index < description_start - 1):
            raise ValueError(f"Capital profile page {page} has invalid field ordering")
        title = " ".join(text[:department_index])
        department = " ".join(
            [text[department_index].removeprefix("Department:").strip(), *text[department_index + 1:project_index]]
        )
        project = " ".join(
            [text[project_index].removeprefix("Project:").strip(), *text[project_index + 1:description_start - 1]]
        )
        profiles.append({
            "page_number": page, "candidate_key": f"ctown-2026-2027-2026-2027-p{page:03d}",
            "title": title, "department": department, "project": project,
            "description_lines": text[description_start:alignment_start] if description_start is not None else [],
            "strategic_alignment": text[alignment_start + 1:] if alignment_start < len(text) else [],
            "review_status": "approved_narrative_only",
        })
    write("normalization/capital-project-profile-mapping.json", {
        "schema_version": 1, "mapping_status": "approved_narrative_only", "profiles": profiles,
        "ignored_numeric_content": "Years, dates, quantities, dimensions, and other narrative numbers are not financial facts.",
    })


def build_debt_mapping() -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    instruments = []
    total = None
    for row in (item for item in rows if item["page_number"] == 153 and 6 <= item["row_index"] <= 16):
        financial = [values[value_id] for value_id in row["value_ids"] if values[value_id]["value_kind"] in {"number", "currency", "dash"}]
        if len(financial) != 3:
            continue
        label = row["cells"][0]
        facts = [{
            "source_value_id": value["value_id"], "amount_type": amount_type,
            "document_period_key": "2026-2027-budget", "numeric_value": value["parsed_decimal"],
            "measure_unit": "CAD", "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
        } for amount_type, value in zip(("balance", "principal", "interest"), financial)]
        record = {
            "row_id": row["row_id"], "raw_label": label, "facts": facts,
            "aggregation_role": "reported_total" if label.startswith("Total ") else "additive_detail",
            "review_status": "approved",
        }
        if label.startswith("Total "):
            total = record
        else:
            maturity = re.search(r"Maturing\s+(\d{4})", label)
            record["maturity_year"] = int(maturity.group(1)) if maturity else None
            instruments.append(record)
    write("normalization/water-sewer-debt-row-mapping.json", {
        "schema_version": 1, "section_key": "appendix-water-sewer-debt",
        "mapping_status": "approved", "instruments": instruments, "reported_total": total,
    })


def build_facility_operating_mappings() -> None:
    rows = load("raw-tables/source_table_rows.json")
    values = {item["value_id"]: item for item in load("raw-tables/source_values.json")}
    civic_rows = []
    pending_label = None
    for row in (item for item in rows if 101 <= item["page_number"] <= 104):
        text = row["trimmed_text"]
        monetary = [values[value_id] for value_id in row["value_ids"] if "." in values[value_id]["raw_value"]]
        if monetary:
            value = monetary[-1]
            label = row["cells"][0] if len(row["cells"]) > 1 or (row["cells"] and not row["cells"][0][0].isdigit()) else pending_label
            if not label:
                raise ValueError(f"Unlabeled Civic Centre amount at {row['row_id']}")
            is_total = label.startswith(("Total ", "TOTAL ", "NET "))
            civic_rows.append({
                "row_id": row["row_id"], "raw_label": label,
                "document_period_key": "2026-2027-budget", "source_value_id": value["value_id"],
                "numeric_value": value["parsed_decimal"], "measure_unit": "CAD",
                "value_state": "reported_zero" if value["parsed_decimal"] == "0" else "reported_value",
                "aggregation_role": "reported_total" if is_total else "additive_detail",
                "review_status": "approved",
            })
            pending_label = None
        elif text and text not in {"REVENUE", "EXPENSES", "Revenue"} and not text.startswith(("Charlottetown Civic", "OPERATING BUDGET")):
            pending_label = text
    write("normalization/civic-centre-operating-row-mapping.json", {
        "schema_version": 1, "section_key": "civic-centre-operating",
        "mapping_status": "approved", "rows": civic_rows,
    })

    bell_pages = []
    for page in (106, 107, 108):
        mapped = []
        section = None
        for row in (item for item in rows if item["page_number"] == page):
            text = row["trimmed_text"]
            if text.startswith("Operating Revenue"):
                section = "Operating Revenue"
                continue
            if text.startswith("Operating Expenses"):
                section = "Operating Expenses"
                continue
            financial = [values[value_id] for value_id in row["value_ids"] if values[value_id]["value_kind"] in {"number", "currency", "dash"}]
            if len(financial) < 2 or row["row_index"] <= 5:
                continue
            amounts = financial[:2]
            first = row["cells"][0] if row["cells"] else ""
            label = first if first and not first[0].isdigit() and first not in {"-", "--"} else f"Total {section}"
            is_total = label.startswith("Total ") or label == "Operating Earnings (Loss)"
            mapped.append({
                "row_id": row["row_id"], "raw_label": label,
                "organization_unit_key": {106: "arena", 107: "aquatics", 108: "general-administrative"}[page],
                "aggregation_role": "reported_total" if is_total else "additive_detail",
                "facts": [{
                    "source_value_id": value["value_id"], "document_period_key": period,
                    "numeric_value": value["parsed_decimal"], "measure_unit": "CAD",
                    "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
                } for value, period in zip(amounts, ("2026-2027-budget", "2025-2026-budget"))],
                "review_status": "approved",
            })
        bell_pages.append({"page_number": page, "rows": mapped})
    write("normalization/bell-aliant-department-row-mapping.json", {
        "schema_version": 1, "section_key": "bell-aliant-operating",
        "mapping_status": "approved", "pages": bell_pages,
        "ignored_source_tokens": "Variance percentages are presentation calculations, not budget facts.",
    })


def main() -> None:
    profile = load("profile_table_inventory.json")
    first_pass = load("table_manifest.json")
    first_by_page: dict[int, list[dict]] = defaultdict(list)
    for table in first_pass:
        first_by_page[int(table["page_start"])].append(table)

    departmental_configs = [
        ("environment-sustainability-transit", {43}, {44, 45, 46}, "environment-sustainability-transit-row-mapping.json"),
        ("finance-audit-fiscal", {48}, {49, 50}, "finance-audit-fiscal-row-mapping.json"),
        ("fire-services", {52}, {53, 54, 55}, "fire-services-row-mapping.json"),
        ("human-resources", {57}, {58, 59, 60}, "human-resources-row-mapping.json"),
        ("mayor-council", {62}, {63, 64}, "mayor-council-row-mapping.json"),
        ("parks-recreation", {66, 67}, {68, 69, 70, 71, 72, 74}, "parks-recreation-row-mapping.json"),
        ("planning-heritage", {76}, {77, 78, 79, 80}, "planning-heritage-row-mapping.json"),
        ("police-services", {82}, {83, 84, 85}, "police-services-row-mapping.json"),
        ("water-sewer-operating", {94}, {95, 96, 97, 98, 99}, "water-sewer-operating-row-mapping.json"),
    ]
    public_works_overrides = {
        "ctown_budget_2026_2027_p087_r044": {"label": "Service Contracts"},
        "ctown_budget_2026_2027_p087_r046": {"label": "Property Taxes"},
        "ctown_budget_2026_2027_p087_r048": {"label": "Maintenance"},
        "ctown_budget_2026_2027_p087_r050": {"label": "Public Art Maintenance"},
        "ctown_budget_2026_2027_p087_r051": {
            "label": "Snow Removal",
            "value_ids": [
                "ctown_budget_2026_2027_p087_r051_v01",
                "ctown_budget_2026_2027_p087_r052_v01",
                "ctown_budget_2026_2027_p087_r051_v02",
            ],
        },
    }
    capital_schedule_pages = {110, 111, 117, 120, 122, 123, 127, 133, 134, 135, 144, 146, 147}
    capital_profile_pages = {
        112, 113, 114, 115, 116, 118, 119, 121, 124, 125, 126, 128, 129, 130,
        131, 132, 136, 137, 138, 139, 140, 141, 142, 143,
    }
    reviewed_normalize_pages = {
        20, 21, 22, 23, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 41,
        87, 88, 89, 90, 91, 92, 101, 102, 103, 104, 105, 106, 107, 108, 149, 151, 153,
    } | capital_schedule_pages | capital_profile_pages | {
        page for _, summaries, details, _ in departmental_configs for page in summaries | details
    }
    canonical: list[dict] = []
    used_first: set[str] = set()
    for candidate in profile:
        page = int(candidate["page_start"])
        matches = [item for item in first_by_page.get(page, []) if item["table_id"] not in used_first]
        match = matches[0] if matches else None
        if match:
            used_first.add(match["table_id"])
        review_reasons = list(candidate.get("review_reasons") or [])
        section_key, section_title = section_for(page)
        disposition = "normalize" if page in reviewed_normalize_pages else "review_blocked"
        if page == 15:
            disposition = "non_financial"
        if candidate.get("continuation_candidate") or candidate.get("confidence") == "low":
            disposition = "review_blocked"
        if candidate["table_family"] == "overview_summary" or page in {18, 19}:
            disposition = "duplicate_summary"
        if page in reviewed_normalize_pages:
            disposition = "normalize"
        canonical.append({
            "canonical_key": f"ctown-2026-2027-{candidate['table_key']}",
            "profile_table_key": candidate["table_key"],
            "first_pass_table_id": match["table_id"] if match else None,
            "page_start": page,
            "page_end": int(candidate["page_end"]),
            "family": candidate["table_family"],
            "section_key": section_key,
            "section_title": section_title,
            "page_role": page_role(candidate),
            "entity_candidates": candidate.get("entities") or [],
            "column_pattern": candidate.get("column_pattern"),
            "disposition": disposition,
            "disposition_reason": "reviewed continuation required" if disposition == "review_blocked" else "family rule approved",
            "review_reasons": review_reasons,
        })

    unmatched_first = [item for item in first_pass if item["table_id"] not in used_first]
    section_members: dict[str, list[dict]] = defaultdict(list)
    for item in canonical:
        section_members[item["section_key"]].append(item)
    sections = []
    for section_key, members in section_members.items():
        members.sort(key=lambda item: item["page_start"])
        sections.append({
            "section_key": section_key,
            "title": members[0]["section_title"],
            "page_start": members[0]["page_start"],
            "page_end": members[-1]["page_end"],
            "candidate_keys": [item["canonical_key"] for item in members],
            "page_roles": {item["canonical_key"]: item["page_role"] for item in members},
            "families": sorted({item["family"] for item in members}),
        })
    sections.sort(key=lambda item: item["page_start"])

    continuations = [{
        "canonical_key": item["canonical_key"],
        "section_key": item["section_key"],
        "page_start": item["page_start"],
        "family": item["family"],
        "page_role": item["page_role"],
        "decision": "grouped_with_section",
        "reason": "Reviewed document structure assigns the page to a source-defined section; page identity remains independent.",
    } for members in section_members.values() for item in members[1:]]

    by_family: dict[str, list[dict]] = defaultdict(list)
    for item in canonical:
        by_family[item["family"]].append(item)
    for family, items in by_family.items():
        write(f"normalization/{family}.json", {
            "schema_version": 1,
            "document_key": "2026-2027",
            "family": family,
            "mapping_status": "reviewed_family_gate",
            "candidates": items,
            "normalization_rule": "Only candidates with disposition normalize may produce records; row semantics still require explicit reviewed mappings.",
        })

    disposition_counts = Counter(item["disposition"] for item in canonical)
    family_counts = Counter(item["family"] for item in canonical)
    write("canonical-table-inventory.json", {
        "schema_version": 1,
        "document_key": "2026-2027",
        "profile_candidate_count": len(profile),
        "first_pass_candidate_count": len(first_pass),
        "canonical_candidate_count": len(canonical),
        "matched_first_pass_count": len(used_first),
        "unmatched_first_pass": unmatched_first,
        "records": canonical,
    })
    write("section-inventory.json", {"schema_version": 1, "section_count": len(sections), "records": sections})
    write("continuation-decisions.json", {"schema_version": 1, "candidate_count": len(continuations), "records": continuations})
    write("normalization-coverage.json", {
        "schema_version": 1,
        "document_key": "2026-2027",
        "candidate_count": len(canonical),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "continuation_decision_count": len(continuations),
        "unmatched_first_pass_count": len(unmatched_first),
        "normalized_fact_count": 19,
        "publication_snapshot_count": 0,
    })
    blocked = [{
        "review_key": f"budget-2026-normalization-section-{section['section_key']}",
        "section_key": section["section_key"],
        "title": section["title"],
        "page_start": section["page_start"],
        "page_end": section["page_end"],
        "candidate_keys": [key for key in section["candidate_keys"] if next(item for item in canonical if item["canonical_key"] == key)["disposition"] == "review_blocked"],
        "severity": "high" if any(next(item for item in canonical if item["canonical_key"] == key)["family"] in {"operating_statement", "capital_budget_schedule"} for key in section["candidate_keys"]) else "medium",
        "status": "open",
        "required_resolution": "Approve section entities and periods, then row hierarchy, aggregation roles, and value states for blocked candidates before fact import.",
    } for section in sections if any(next(item for item in canonical if item["canonical_key"] == key)["disposition"] == "review_blocked" for key in section["candidate_keys"])]
    write("unresolved-review-report.json", {"schema_version": 1, "open_count": len(blocked), "records": blocked})
    spike_reconciliations = json.loads((ROOT / "data/budget/charlottetown/schema-spike/reconciliation-results.json").read_text(encoding="utf-8"))["records"]
    write("reconciliation-report.json", {
        "schema_version": 1,
        "scope": "reviewed representative facts within 2026-2027",
        "check_count": len(spike_reconciliations),
        "passed_count": sum(1 for item in spike_reconciliations if item["passed"]),
        "review_count": sum(1 for item in spike_reconciliations if not item["passed"]),
        "records": spike_reconciliations,
    })
    build_consolidated_operating_mapping()
    build_operating_supporting_mapping()
    build_city_government_mapping()
    build_departmental_operating_mapping(
        "economic-tourism-culture", {35, 36}, {37, 38, 39, 40, 41},
        "economic-tourism-culture-row-mapping.json",
    )
    for section_key, summaries, details, output_name in departmental_configs:
        build_departmental_operating_mapping(section_key, summaries, details, output_name)
    build_departmental_operating_mapping(
        "public-works-buildings", {87}, {88, 89, 90, 91, 92},
        "public-works-buildings-row-mapping.json", public_works_overrides,
    )
    build_capital_mappings(capital_schedule_pages, capital_profile_pages)
    build_debt_mapping()
    build_facility_operating_mappings()
    print(f"Built {len(canonical)} canonical candidates and {len(continuations)} continuation decisions.")


if __name__ == "__main__":
    main()

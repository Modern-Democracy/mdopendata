from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fitz
except ModuleNotFoundError:  # pragma: no cover - supports lighter Python envs.
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "charlottetown" / "charlottetown-zoning-bylaw.pdf"
OUT = ROOT / "data" / "zoning" / "charlottetown"
CODE_TABLES = ROOT / "data" / "normalized" / "code-tables"

SOURCE_REL = "docs/charlottetown/charlottetown-zoning-bylaw.pdf"
BYLAW_NAME = "Zoning & Development Bylaw (PH-ZD.2 rev 049)"
JURISDICTION = "City of Charlottetown"

UNIT_MAP = {
    "m": "m",
    "metre": "m",
    "metres": "m",
    "meter": "m",
    "meters": "m",
    "ft": "ft",
    "feet": "ft",
    "foot": "ft",
    "sq m": "sq_m",
    "sq. m": "sq_m",
    "sqm": "sq_m",
    "sq ft": "sq_ft",
    "sq. ft": "sq_ft",
    "sqft": "sq_ft",
    "ac": "acre",
    "acre": "acre",
    "acres": "acre",
    "ha": "ha",
    "%": "percent",
    "percent": "percent",
    "storey": "storey",
    "storeys": "storey",
    "storeys": "storey",
    "bedroom": "bedroom",
    "bedrooms": "bedroom",
    "unit": "unit",
    "units": "unit",
    "dwelling unit": "dwelling_unit",
    "dwelling units": "dwelling_unit",
    "parking space": "parking_space",
    "parking spaces": "parking_space",
    "seat": "seat",
    "seats": "seat",
    "room": "room",
    "rooms": "room",
}

UNIT_RE = "|".join(
    re.escape(unit)
    for unit in sorted(UNIT_MAP, key=len, reverse=True)
)
MEASUREMENT_RE = re.compile(
    rf"(?P<value>\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?P<unit>{UNIT_RE})\b",
    re.IGNORECASE,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_text(text: str | None) -> str:
    return " ".join((text or "").split())


def slugify(value: str | None) -> str:
    value = (value or "").lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return re.sub(r"-+", "-", value) or "unknown"


def code_key(value: str | None) -> str:
    value = clean_text(value).lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return re.sub(r"_+", "_", value)


def citation(raw: dict[str, Any] | None) -> dict[str, int | None]:
    raw = raw or {}
    return {
        "pdf_page_start": raw.get("pdf_page_start"),
        "pdf_page_end": raw.get("pdf_page_end"),
        "bylaw_page_start": raw.get("bylaw_page_start"),
        "bylaw_page_end": raw.get("bylaw_page_end"),
    }


def source_ref(ref_type: str, ref_id: str) -> dict[str, str]:
    return {"source_ref_type": ref_type, "source_ref_id": ref_id}


def make_review_flag(
    flag_id: str,
    review_type: str,
    description: str,
    refs: list[dict[str, str]] | None = None,
    severity: str = "warning",
    blocking: bool = False,
) -> dict[str, Any]:
    flag: dict[str, Any] = {
        "review_flag_id": flag_id,
        "severity": severity,
        "blocking": blocking,
        "review_type": review_type,
        "description": description,
    }
    if refs:
        flag["source_refs"] = refs
    return flag


def load_seed_entries(table: str) -> list[dict[str, Any]]:
    data = read_json(CODE_TABLES / f"{table}.seed.json")
    return data["entries"]


def build_lookup(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for entry in entries:
        for value in [entry.get("code"), entry.get("label")]:
            key = code_key(value)
            if key:
                lookup[key] = entry
    return lookup


USE_TERM_SPLITS = {
    "retail_store_with_connected_retail_warehouse_light_manufacturing_or_assembly_facility": [
        "retail_store",
        "retail_warehouse",
        "light_manufacturing",
        "assembly_facility",
    ],
    "warehouse_and_or_distribution_centre": ["warehouse", "distribution_centre"],
    "warehouse_and_or_distribution_center": ["warehouse", "distribution_centre"],
}

USE_TERM_ALIASES = {
    "agriculture_and_resource_land_uses": "agricultural_and_resource_land_uses",
    "docking_for_private_boats_and_watercraft_subject_to_provincial_and_federal_approvals": (
        "docking_for_private_boats_and_watercraft"
    ),
    "manufacturing_light": "light_manufacturing",
    "offices": "office",
    "commercial_daycare": "commercial_daycare_centre",
    "government_offices": "government_office",
    "public_utility_service_operations": "public_utility_service_operation",
    "recreation_or_fitness_center_indoors": "recreation_or_fitness_centre_indoors",
    "shopping_center": "shopping_centre",
    "transportation_services": "transportation_service",
    "automobile_sales_and_services": "automobile_sales_and_service",
    "apartment_building": "apartment_dwelling",
    "apartment_dwellings": "apartment_dwelling",
    "apartments": "apartment_dwelling",
    "duplex_dwellings": "duplex_dwelling",
    "semi_detached_dwellings": "semi_detached_dwelling",
    "stacked_townhouse": "stacked_townhouse_dwelling",
    "converted_dwellings": "converted_dwelling",
    "one_single_detached_dwelling_per_lot_with_serviced_lot_frontage": "single_detached_dwelling",
    "home_daycare_home": "home_daycare",
}

NON_QUERYABLE_USE_TERMS = {
    "ancillary_uses_to_the_foregoing",
    "council_shall_give_due_consideration_to_other_sections_of_this_by_law_but_council_may_approve_any_use_or_development_in_a_cda_zone_which_it_deems_to_be_in_the_public_interest_notwithstanding_all_other_sections_of_this_by_law_but_only_after_following_the_procedures_set_out_in_this_section",
    "subject_to_sections_35_inclusive_the_water_lots_shall_remain_as_a_water_lot_open_space_zone_in_which_no_development_may_occur_other_than_navigation_and_required_infrastructure_related_to_navigation",
    "existing_uses_such_as_navigation_and_docking_for_commercial_e_g_petroleum_aggregate_and_cruise_ships_vessels_and_navigation_docking_and_marinas_related_to_the_port_authority",
}


class Normalizer:
    def __init__(self) -> None:
        self.term_lookup = build_lookup(load_seed_entries("term"))
        self.use_lookup = build_lookup(load_seed_entries("use"))
        self.requirement_codes = {entry["code"] for entry in load_seed_entries("requirement_type")}
        self.measure_codes = {entry["code"] for entry in load_seed_entries("measure_type")}
        self.unit_codes = {entry["code"] for entry in load_seed_entries("unit")}

    def match_term(self, raw: str) -> tuple[str, dict[str, Any] | None]:
        key = code_key(strip_list_punctuation(raw))
        key = USE_TERM_ALIASES.get(key, key)
        if key in self.use_lookup:
            return "use", self.use_lookup[key]
        if key in self.term_lookup:
            return "term", self.term_lookup[key]
        return "term", None

    def match_term_components(self, raw: str) -> list[dict[str, Any]]:
        raw = strip_list_punctuation(raw)
        key = code_key(raw)
        component_codes = USE_TERM_SPLITS.get(key)
        if component_codes:
            components = []
            for code in component_codes:
                entry = self.use_lookup.get(code) or self.term_lookup.get(code)
                components.append(
                    {
                        "raw": entry.get("label") if entry else code.replace("_", " ").title(),
                        "table": "use" if code in self.use_lookup else "term",
                        "entry": entry,
                        "normalized": code,
                    }
                )
            return components

        table, entry = self.match_term(raw)
        normalized = entry["code"] if entry else code_key(raw)
        return [{"raw": raw, "table": table, "entry": entry, "normalized": normalized}]


def strip_list_punctuation(text: str | None) -> str:
    text = clean_text(text)
    text = re.sub(r"(;|,|\.)$", "", text).strip()
    text = re.sub(r"\s+and$", "", text, flags=re.IGNORECASE).strip()
    return text


def zone_title_from_heading(metadata: dict[str, Any]) -> str:
    heading = metadata.get("chapter_heading_raw") or ""
    part = str(metadata.get("part_label_raw") or "")
    title = re.sub(rf"^\s*{re.escape(part)}\s+", "", heading).strip()
    return title or metadata.get("zone_name") or ""


def doc_citation_from_legacy(legacy: dict[str, Any], fallback: dict[str, Any] | None = None) -> dict[str, int | None]:
    if fallback:
        return citation(fallback)
    source = legacy.get("source_section") or {}
    if source:
        return citation(source)
    zone_citation = (legacy.get("citations") or {}).get("zone_section")
    if zone_citation:
        return citation(zone_citation)
    return citation({})


def clause_id(prefix: str, section_id: str, provision: dict[str, Any], index: int) -> str:
    path = provision.get("clause_path") or []
    if path:
        raw = "-".join(str(part) for part in path)
    else:
        raw = provision.get("provision_label_raw") or provision.get("clause_label_raw") or str(index)
    return f"{prefix}-clause-{slugify(raw)}"


def section_id(prefix: str, label: str | None, index: int) -> str:
    return f"{prefix}-section-{slugify(label or str(index))}"


def table_id(prefix: str, label: str | None, index: int) -> str:
    return f"{prefix}-table-{slugify(label or str(index))}"


def table_headings(raw_headings: list[str] | None) -> list[str]:
    joined = clean_text(" ".join(raw_headings or []))
    if not joined:
        return ["value"]
    known = {
        "Interior Lot Corner Lot": ["Interior Lot", "Corner Lot"],
        "Interior Lot Corner Lots": ["Interior Lot", "Corner Lot"],
        "Interior Lots Corner Lots": ["Interior Lot", "Corner Lot"],
        "Townhouse Stacked Townhouse": ["Townhouse", "Stacked Townhouse"],
        "End-on Sites Front on Sites": ["End-on Sites", "Front on Sites"],
    }
    if joined in known:
        return known[joined]
    if " Interior " in f" {joined} " and " Corner " in f" {joined} ":
        return ["Interior Lot", "Corner Lot"]
    return [joined]


def find_heading_y(words: list[tuple[float, float, float, float, str]], title: str) -> float | None:
    target = re.sub(r"[^A-Z0-9]+", " ", title.upper()).strip()
    if not target:
        return None
    rows: dict[int, list[tuple[float, str]]] = {}
    for x0, y0, _x1, _y1, word in words:
        if x0 < 90:
            continue
        rows.setdefault(round(y0), []).append((x0, word))
    for y, row_words in rows.items():
        line = " ".join(word for _x, word in sorted(row_words))
        normalized = re.sub(r"[^A-Z0-9]+", " ", line.upper()).strip()
        if target in normalized:
            return float(y)
    return None


def group_words_into_lines(words: list[tuple[float, float, float, float, str]]) -> list[list[tuple[float, str]]]:
    lines: list[tuple[float, list[tuple[float, str]]]] = []
    for x0, y0, _x1, _y1, word in sorted(words, key=lambda item: (item[1], item[0])):
        if not lines or abs(lines[-1][0] - y0) > 5:
            lines.append((y0, [(x0, word)]))
        else:
            lines[-1][1].append((x0, word))
    return [line for _y, line in lines]


def text_in_range(line: list[tuple[float, str]], left: float, right: float) -> str:
    return clean_text(" ".join(word for x, word in sorted(line) if left <= x < right))


def append_cell_text(existing: str, addition: str) -> str:
    if not addition:
        return existing
    return clean_text(f"{existing} {addition}" if existing else addition)


def condition_split_for_requirement(requirement_text: str) -> tuple[str, list[str]]:
    patterns = [
        ("Front yard access Rear lane access", ["Front yard access", "Rear lane access"]),
        ("Front Access (Minimum) Rear Lane Access (Minimum)", ["Front Access (Minimum)", "Rear Lane Access (Minimum)"]),
        ("Eight (8) or less units More than eight (8) units", ["Eight (8) or less units", "More than eight (8) units"]),
        ("Townhouse Stacked Townhouse", ["Townhouse", "Stacked Townhouse"]),
        ("End-on Sites Front on Sites", ["End-on Sites", "Front on Sites"]),
        ("For three (3) bedrooms For each additional bedroom", ["For three (3) bedrooms", "For each additional bedroom"]),
        (
            "Any Building type, 3 units or less Townhouse Dwelling: 4 units or more Apartment Dwelling: 4 units or more Any other permitted Use",
            [
                "Any Building type, 3 units or less",
                "Townhouse Dwelling: 4 units or more",
                "Apartment Dwelling: 4 units or more",
                "Any other permitted Use",
            ],
        ),
    ]
    for suffix, conditions in patterns:
        if requirement_text.endswith(suffix):
            return clean_text(requirement_text[: -len(suffix)]), conditions
    return requirement_text, []


def measurement_value_groups(text: str) -> list[str]:
    matches = list(MEASUREMENT_RE.finditer(text))
    groups = []
    index = 0
    while index < len(matches):
        match = matches[index]
        end = match.end()
        if index + 1 < len(matches) and compatible_alternative_units(
            unit_code(match.group("unit")),
            unit_code(matches[index + 1].group("unit")),
        ):
            end = matches[index + 1].end()
            if text[end : end + 1] == ")":
                end += 1
            index += 2
        else:
            index += 1
        groups.append(clean_text(text[match.start() : end]))
    return groups


def split_condition_rows(table: dict[str, Any]) -> dict[str, Any]:
    columns = [column for column in table.get("columns_raw") or [] if column.get("column_id") != "condition"]
    condition_column = {"column_id": "condition", "column_label_raw": "", "source_order": 3}
    value_columns = columns[2:]
    rows_out = []
    split_seen = False
    for row in table.get("rows_raw") or []:
        cell_by_id = {cell["column_id"]: cell for cell in row.get("cells_raw") or []}
        requirement_cell = cell_by_id.get("requirement")
        if not requirement_cell:
            rows_out.append(row)
            continue
        base_requirement, conditions = condition_split_for_requirement(requirement_cell.get("cell_text_raw") or "")
        if not conditions:
            rows_out.append(row)
            continue
        split_values: dict[str, list[str]] = {}
        can_split = True
        for column in value_columns:
            cell = cell_by_id.get(column["column_id"], {})
            text = cell.get("cell_text_raw") or ""
            groups = measurement_value_groups(text)
            if text and len(groups) != len(conditions):
                can_split = False
                break
            split_values[column["column_id"]] = groups if text else [""] * len(conditions)
        if not can_split:
            rows_out.append(row)
            continue
        split_seen = True
        row_number = (cell_by_id.get("row_number") or {}).get("cell_text_raw") or ""
        for condition_index, condition in enumerate(conditions, start=1):
            row_id = f"{row['row_id']}-{slugify(condition)}"
            cells = [
                {
                    "cell_id": f"{row_id}-row-number",
                    "column_id": "row_number",
                    "cell_text_raw": row_number if condition_index == 1 else "",
                },
                {
                    "cell_id": f"{row_id}-requirement",
                    "column_id": "requirement",
                    "cell_text_raw": base_requirement,
                },
                {
                    "cell_id": f"{row_id}-condition",
                    "column_id": "condition",
                    "cell_text_raw": condition,
                },
            ]
            for column in value_columns:
                cells.append(
                    {
                        "cell_id": f"{row_id}-{column['column_id']}",
                        "column_id": column["column_id"],
                        "cell_text_raw": split_values[column["column_id"]][condition_index - 1],
                    }
                )
            rows_out.append({"row_id": row_id, "source_order": len(rows_out) + 1, "cells_raw": cells})
    if not split_seen:
        return table
    table = dict(table)
    table["columns_raw"] = [
        columns[0],
        columns[1],
        condition_column,
        *[{**column, "source_order": index} for index, column in enumerate(value_columns, start=4)],
    ]
    table["rows_raw"] = rows_out
    return table


def fallback_table_column_bounds(value_column_count: int) -> tuple[float, list[tuple[float, float]]]:
    if value_column_count == 1:
        return 300.0, [(300.0, 560.0)]
    if value_column_count == 2:
        return 300.0, [(300.0, 420.0), (420.0, 560.0)]
    width = 260.0 / value_column_count
    return 300.0, [(300.0 + (idx * width), 300.0 + ((idx + 1) * width)) for idx in range(value_column_count)]


def column_label_key(label: str) -> str:
    words = re.findall(r"[A-Za-z]+", label)
    return words[0].upper() if words else ""


def infer_table_column_bounds(
    lines: list[list[tuple[float, str]]],
    value_columns: list[dict[str, Any]],
) -> tuple[float, list[tuple[float, float]]]:
    fallback_requirement_right, fallback_bounds = fallback_table_column_bounds(len(value_columns))
    first_row_index = next(
        (
            idx
            for idx, line in enumerate(lines)
            if line and re.fullmatch(r"\d+", sorted(line)[0][1]) and sorted(line)[0][0] < 130
        ),
        None,
    )
    if first_row_index is None:
        return fallback_requirement_right, fallback_bounds
    header_lines = lines[:first_row_index]
    starts = []
    for column in value_columns:
        key = column_label_key(column.get("column_label_raw") or "")
        if not key:
            return fallback_requirement_right, fallback_bounds
        matches = [
            x
            for line in header_lines
            for x, word in line
            if re.sub(r"[^A-Za-z]+", "", word).upper().startswith(key)
        ]
        if not matches:
            return fallback_requirement_right, fallback_bounds
        starts.append(min(matches))
    if len(starts) != len(value_columns) or starts != sorted(starts):
        return fallback_requirement_right, fallback_bounds
    requirement_right = max(125.0, starts[0] - 5.0)
    bounds = []
    for idx, start in enumerate(starts):
        right = starts[idx + 1] - 3.0 if idx + 1 < len(starts) else 560.0
        bounds.append((start, right))
    return requirement_right, bounds


def is_table_footer_or_following_text(line_text: str) -> bool:
    normalized = line_text.upper()
    return "PH-ZD" in normalized or "UPDATED AS OF" in normalized


def is_non_table_heading(line_text: str) -> bool:
    if re.match(r"^\d+\s", line_text):
        return False
    normalized = re.sub(r"[^A-Z0-9]+", " ", line_text.upper()).strip()
    return bool(
        re.search(
            r"\b(ACCESSORY|SECONDARY|PERMITTED USES|PROHIBITED|SPECIAL REQUIREMENTS|REGULATIONS FOR)\b",
            normalized,
        )
    )


def rebuild_table_from_pdf(doc: Any, section: dict[str, Any], next_section: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None or not section.get("tables_raw"):
        return None
    citation_value = section.get("citations") or {}
    pdf_start = citation_value.get("pdf_page_start")
    pdf_end = citation_value.get("pdf_page_end") or pdf_start
    if not pdf_start:
        return None
    first_table = section["tables_raw"][0]
    columns = [column for column in first_table.get("columns_raw") or [] if column.get("column_id") != "condition"]
    value_columns = columns[2:]
    if not value_columns:
        return None

    rows_out = []
    row_order = 0
    for pdf_page in range(int(pdf_start), int(pdf_end) + 1):
        words = [(w[0], w[1], w[2], w[3], w[4]) for w in doc[pdf_page - 1].get_text("words")]
        y_start = find_heading_y(words, section.get("section_title_raw") or "")
        if y_start is None:
            y_start = 0.0 if pdf_page != int(pdf_start) else 60.0
        y_end = None
        if next_section and (next_section.get("citations") or {}).get("pdf_page_start") == pdf_page:
            y_end = find_heading_y(words, next_section.get("section_title_raw") or "")
        if y_end is None:
            y_end = 740.0
        table_words = [
            word
            for word in words
            if y_start + 10 <= word[1] <= y_end - 3 and 100 <= word[0] <= 560
        ]
        lines = group_words_into_lines(table_words)
        requirement_right, value_bounds = infer_table_column_bounds(lines, value_columns)
        current: dict[str, Any] | None = None
        for line in lines:
            line_text = clean_text(" ".join(word for _x, word in sorted(line)))
            if not line_text:
                continue
            if is_table_footer_or_following_text(line_text):
                break
            if is_non_table_heading(line_text):
                if current is None:
                    continue
                break
            first = sorted(line)[0]
            if re.fullmatch(r"\d+", first[1]) and first[0] < 130:
                row_order += 1
                row_id = f"{first_table['table_id']}-row-{row_order}"
                cells = [
                    {
                        "cell_id": f"{row_id}-row-number",
                        "column_id": "row_number",
                        "cell_text_raw": first[1],
                    },
                    {
                        "cell_id": f"{row_id}-requirement",
                        "column_id": "requirement",
                        "cell_text_raw": text_in_range(line, 130, requirement_right),
                    },
                ]
                for idx, column in enumerate(value_columns):
                    left, right = value_bounds[idx]
                    cells.append(
                        {
                            "cell_id": f"{row_id}-{column['column_id']}",
                            "column_id": column["column_id"],
                            "cell_text_raw": text_in_range(line, left, right),
                        }
                    )
                current = {"row_id": row_id, "source_order": row_order, "cells_raw": cells}
                rows_out.append(current)
                continue
            if current is None:
                continue
            current["cells_raw"][1]["cell_text_raw"] = append_cell_text(
                current["cells_raw"][1]["cell_text_raw"],
                text_in_range(line, 130, requirement_right),
            )
            for idx, column in enumerate(value_columns):
                left, right = value_bounds[idx]
                current["cells_raw"][idx + 2]["cell_text_raw"] = append_cell_text(
                    current["cells_raw"][idx + 2]["cell_text_raw"],
                    text_in_range(line, left, right),
                )
    if not rows_out:
        return None
    rebuilt = dict(first_table)
    rebuilt["columns_raw"] = columns
    rebuilt["rows_raw"] = rows_out
    return split_condition_rows(rebuilt)


def rebuild_schema_tables_from_pdf(doc: Any, data: dict[str, Any]) -> bool:
    changed = False
    sections = (data.get("raw_data") or {}).get("sections_raw") or []
    for index, section in enumerate(sections):
        if not section.get("tables_raw"):
            continue
        next_section = sections[index + 1] if index + 1 < len(sections) else None
        rebuilt = rebuild_table_from_pdf(doc, section, next_section)
        if rebuilt and rebuilt.get("rows_raw") != section["tables_raw"][0].get("rows_raw"):
            section["tables_raw"][0] = rebuilt
            changed = True
    if changed:
        prefix = ((data.get("raw_data") or {}).get("source_units") or [{}])[0].get("source_unit_id") or "document"
        review_flags = data.setdefault("review_flags", [])
        numeric_values, requirements, other_requirements = build_numeric_and_requirements(sections, prefix, review_flags)
        structured = data.setdefault("structured_data", base_structured_data())
        structured["numeric_values"] = numeric_values
        structured["requirements"] = requirements
        structured["other_requirements"] = other_requirements
        for group in structured.get("regulation_groups") or []:
            group["requirement_refs"] = [req["requirement_id"] for req in requirements]
    return changed


def rebuild_clause_refs(data: dict[str, Any]) -> dict[str, Any]:
    raw_data = data.get("raw_data") or {}
    refs = []
    for section in raw_data.get("sections_raw") or []:
        section_id_value = section.get("section_id") or ""
        for clause in section.get("clauses_raw") or []:
            refs.append(
                {
                    "clause_id": clause["clause_id"],
                    "section_id": section_id_value,
                    "source_order": len(refs) + 1,
                }
            )
    raw_data.pop("clauses_index", None)
    raw_data["clause_refs"] = refs
    return data


def reset_review_flags(data: dict[str, Any]) -> dict[str, Any]:
    data["review_flags"] = []
    return data


def refresh_schema_numeric_values(data: dict[str, Any]) -> dict[str, Any]:
    sections = (data.get("raw_data") or {}).get("sections_raw") or []
    if not sections:
        return data
    prefix = ((data.get("raw_data") or {}).get("source_units") or [{}])[0].get("source_unit_id") or "document"
    review_flags = data.setdefault("review_flags", [])
    numeric_values, requirements, other_requirements = build_numeric_and_requirements(sections, prefix, review_flags)
    structured = data.setdefault("structured_data", base_structured_data())
    structured["numeric_values"] = numeric_values
    structured["requirements"] = requirements
    structured["other_requirements"] = other_requirements
    for group in structured.get("regulation_groups") or []:
        group["requirement_refs"] = [req["requirement_id"] for req in requirements]
    return data


def split_table_values(text: str, count: int) -> tuple[str, list[str]]:
    text = clean_text(text)
    matches = list(MEASUREMENT_RE.finditer(text))
    if count <= 1 or len(matches) < count:
        return text, [text]
    label = text[: matches[0].start()].strip()
    values = []
    for idx, match in enumerate(matches[:count]):
        end = matches[idx + 1].start() if idx + 1 < min(len(matches), count) else len(text)
        values.append(text[match.start() : end].strip())
    return label or text, values


def build_table_raw(prefix: str, section: dict[str, Any], sec_id: str, source_order: int) -> dict[str, Any]:
    headings = table_headings(section.get("table_column_headings_raw"))
    tid = table_id(prefix, section.get("section_label_raw") or section.get("title_label_raw"), source_order)
    columns = [
        {"column_id": "row_number", "column_label_raw": "", "source_order": 1},
        {"column_id": "requirement", "column_label_raw": "", "source_order": 2},
    ]
    for idx, heading in enumerate(headings, start=3):
        columns.append({"column_id": slugify(heading).replace("-", "_"), "column_label_raw": heading, "source_order": idx})

    rows = []
    for row_order, provision in enumerate(section.get("provisions") or [], start=1):
        label = str(provision.get("provision_label_raw") or row_order)
        requirement, values = split_table_values(provision.get("text") or "", len(headings))
        cells = [
            {"cell_id": f"{tid}-row-{row_order}-row-number", "column_id": "row_number", "cell_text_raw": label},
            {"cell_id": f"{tid}-row-{row_order}-requirement", "column_id": "requirement", "cell_text_raw": requirement},
        ]
        for idx, heading in enumerate(headings):
            column_id = slugify(heading).replace("-", "_")
            value = values[idx] if idx < len(values) else ""
            cells.append({"cell_id": f"{tid}-row-{row_order}-{column_id}", "column_id": column_id, "cell_text_raw": value})
        rows.append({"row_id": f"{tid}-row-{row_order}", "source_order": row_order, "cells_raw": cells})

    return {
        "table_id": tid,
        "table_title_raw": section.get("title_label_raw") or section.get("section_title_raw") or "",
        "source_order": source_order,
        "columns_raw": columns,
        "rows_raw": rows,
        "citations": citation(section.get("citations")),
        "_section_id": sec_id,
    }


def build_raw_sections(prefix: str, sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_sections = []
    clause_refs = []
    table_refs = []
    for sec_order, section in enumerate(sections, start=1):
        label = section.get("section_label_raw")
        sec_id = section_id(prefix, label, sec_order)
        raw_section: dict[str, Any] = {
            "section_id": sec_id,
            "section_label_raw": str(label or ""),
            "section_title_raw": section.get("title_label_raw") or section.get("section_title_raw") or "",
            "source_order": sec_order,
            "clauses_raw": [],
            "tables_raw": [],
            "citations": citation(section.get("citations")),
        }
        if section.get("table_column_headings_raw"):
            table = build_table_raw(prefix, section, sec_id, len(table_refs) + 1)
            raw_section["tables_raw"].append({k: v for k, v in table.items() if not k.startswith("_")})
            table_refs.append({"table_id": table["table_id"], "section_id": sec_id})
        else:
            id_by_path: dict[tuple[str, ...], str] = {}
            for clause_order, provision in enumerate(section.get("provisions") or [], start=1):
                cid = clause_id(prefix, sec_id, provision, clause_order)
                path = tuple(str(part) for part in (provision.get("clause_path") or []))
                if path:
                    id_by_path[path] = cid
                parent_id = id_by_path.get(path[:-1]) if len(path) > 1 else None
                raw_clause = {
                    "clause_id": cid,
                    "clause_label_raw": str(provision.get("provision_label_raw") or provision.get("clause_label_raw") or ""),
                    "clause_text_raw": clean_text(provision.get("text")),
                    "parent_clause_id": parent_id,
                    "source_order": clause_order,
                    "citations": citation(provision.get("citations") or section.get("citations")),
                }
                raw_section["clauses_raw"].append(raw_clause)
                clause_refs.append(
                    {
                        "clause_id": cid,
                        "section_id": sec_id,
                        "source_order": len(clause_refs) + 1,
                    }
                )
        raw_sections.append(raw_section)
    return raw_sections, clause_refs, table_refs


def flatten_table_cells(raw_sections: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    output = []
    for section in raw_sections:
        for table in section.get("tables_raw") or []:
            column_by_id = {column["column_id"]: column for column in table.get("columns_raw") or []}
            for row in table.get("rows_raw") or []:
                for cell in row.get("cells_raw") or []:
                    output.append((table, row, cell, column_by_id.get(cell["column_id"], {})))
    return output


def parse_number(value: str) -> float | int:
    number = float(value.replace(",", ""))
    return int(number) if number.is_integer() else number


def unit_code(raw: str) -> str:
    return UNIT_MAP.get(clean_text(raw).lower().rstrip("."), "none")


def measure_type_for_unit(unit: str, text: str) -> str:
    if unit in {"sq_m", "sq_ft", "ha", "acre"}:
        return "area"
    if unit in {"m", "ft"}:
        lowered = text.lower()
        if "height" in lowered:
            return "height"
        return "length"
    if unit == "percent":
        return "percentage"
    if unit in {"storey", "bedroom", "dwelling_unit", "unit", "parking_space", "seat", "room", "sign"}:
        return "count"
    return "unknown"


def comparator_from_text(text: str) -> str:
    lowered = text.lower()
    if "minimum" in lowered or "(min" in lowered:
        return "minimum"
    if "maximum" in lowered or "(max" in lowered:
        return "maximum"
    if "not less than" in lowered or "at least" in lowered:
        return "at_least"
    if "not more than" in lowered or "at most" in lowered:
        return "at_most"
    if "less than" in lowered:
        return "less_than"
    if "greater than" in lowered:
        return "greater_than"
    return "exact"


def requirement_category(text: str) -> str:
    lowered = text.lower()
    categories = [
        ("lot_area", ["lot area"]),
        ("lot_frontage", ["frontage", "lot width"]),
        ("front_yard", ["front yard"]),
        ("rear_yard", ["rear yard"]),
        ("side_yard", ["side yard", "interior yard"]),
        ("flankage_yard", ["flankage"]),
        ("height", ["height", "storey"]),
        ("density", ["density", "dwelling units per"]),
        ("lot_coverage", ["lot coverage", "coverage"]),
        ("parking", ["parking"]),
        ("floor_area", ["floor area", "gross floor area"]),
        ("setback", ["setback", "stepback", "step back"]),
    ]
    for category, needles in categories:
        if any(needle in lowered for needle in needles):
            return category
    return code_key(text)[:80] or "other"


def compatible_alternative_units(primary_unit: str, alternative_unit: str) -> bool:
    return (primary_unit, alternative_unit) in {("m", "ft"), ("sq_m", "sq_ft"), ("ha", "acre")}


def numeric_record_from_match(
    numeric_id: str,
    match: re.Match[str],
    context_text: str,
    source_text: str,
    ref: dict[str, str],
    alternative_match: re.Match[str] | None = None,
) -> dict[str, Any]:
    unit = unit_code(match.group("unit"))
    value_raw = match.group(0)
    alternative_values = []
    if alternative_match is not None:
        alternative_unit = unit_code(alternative_match.group("unit"))
        end = alternative_match.end()
        if source_text[end : end + 1] == ")":
            end += 1
        value_raw = clean_text(source_text[match.start() : end])
        alternative_values.append(
            {
                "value_raw": alternative_match.group(0),
                "value": parse_number(alternative_match.group("value")),
                "unit": alternative_unit,
                "measure_type": measure_type_for_unit(alternative_unit, context_text),
            }
        )
    return {
        "numeric_value_id": numeric_id,
        "value_raw": value_raw,
        "value": parse_number(match.group("value")),
        "unit": unit,
        "measure_type": measure_type_for_unit(unit, context_text),
        "comparator": comparator_from_text(context_text),
        "alternative_values": alternative_values,
        "source_refs": [ref],
        "confidence": "medium",
    }


def grouped_numeric_records(
    matches: list[re.Match[str]],
    id_base: str,
    context_text: str,
    source_text: str,
    ref: dict[str, str],
) -> list[dict[str, Any]]:
    records = []
    index = 0
    record_index = 1
    while index < len(matches):
        match = matches[index]
        next_match = matches[index + 1] if index + 1 < len(matches) else None
        alternative = None
        if next_match and compatible_alternative_units(unit_code(match.group("unit")), unit_code(next_match.group("unit"))):
            alternative = next_match
            index += 2
        else:
            index += 1
        records.append(
            numeric_record_from_match(
                f"{id_base}-{record_index}",
                match,
                context_text,
                source_text,
                ref,
                alternative,
            )
        )
        record_index += 1
    return records


def build_numeric_and_requirements(
    raw_sections: list[dict[str, Any]],
    prefix: str,
    review_flags: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    numeric_values = []
    requirements = []
    other_requirements = []
    seen_requirement_text: set[str] = set()

    for table, row, cell, column in flatten_table_cells(raw_sections):
        if cell["column_id"] in {"row_number", "requirement", "condition"}:
            continue
        row_label = next((c["cell_text_raw"] for c in row["cells_raw"] if c["column_id"] == "requirement"), "")
        condition_text = next((c["cell_text_raw"] for c in row["cells_raw"] if c["column_id"] == "condition"), "")
        context_text = clean_text(f"{row_label} {condition_text} {column.get('column_label_raw', '')} {cell['cell_text_raw']}")
        matches = list(MEASUREMENT_RE.finditer(cell["cell_text_raw"]))
        records = grouped_numeric_records(
            matches,
            f"{prefix}-num-{slugify(row['row_id'])}-{slugify(cell['column_id'])}",
            context_text,
            cell["cell_text_raw"],
            source_ref("table_cell", cell["cell_id"]),
        )
        numeric_values.extend(records)
        numeric_refs = [record["numeric_value_id"] for record in records]
        if numeric_refs:
            req_id = f"{prefix}-req-{slugify(row['row_id'])}-{slugify(cell['column_id'])}"
            requirements.append(
                {
                    "requirement_id": req_id,
                    "requirement_type": "dimensional_standard",
                    "requirement_category": requirement_category(row_label),
                    "requirement_label_raw": row_label,
                    "requirement_text_raw": context_text,
                    "applicability": {
                        "applies_to_lot_contexts": [code_key(column.get("column_label_raw"))]
                        if column.get("column_label_raw")
                        else [],
                        "conditions": [
                            {"condition_type": "table_row_condition", "condition_text_raw": condition_text}
                        ]
                        if condition_text
                        else [],
                    },
                    "numeric_value_refs": numeric_refs,
                    "term_refs": [],
                    "source_refs": [source_ref("table_row", row["row_id"])],
                    "confidence": "medium",
                }
            )
        elif cell["cell_text_raw"]:
            review_flags.append(
                make_review_flag(
                    f"{prefix}-flag-unparsed-table-value-{slugify(cell['cell_id'])}",
                    "numeric_value_review",
                    f"Table cell value was preserved but not normalized: {cell['cell_text_raw']}",
                    [source_ref("table_cell", cell["cell_id"])],
                )
            )

    for section in raw_sections:
        for clause in section.get("clauses_raw") or []:
            text = clause["clause_text_raw"]
            matches = list(MEASUREMENT_RE.finditer(text))
            if not matches:
                continue
            records = grouped_numeric_records(
                matches,
                f"{prefix}-num-{slugify(clause['clause_id'])}",
                text,
                text,
                source_ref("clause", clause["clause_id"]),
            )
            numeric_values.extend(records)
            numeric_refs = [record["numeric_value_id"] for record in records]
            key = clause["clause_id"]
            if key in seen_requirement_text:
                continue
            seen_requirement_text.add(key)
            target = requirements if any(word in text.lower() for word in ["minimum", "maximum", "height", "yard", "area", "setback", "frontage"]) else other_requirements
            target.append(
                {
                    "requirement_id": f"{prefix}-req-{slugify(clause['clause_id'])}",
                    "requirement_type": "dimensional_standard" if target is requirements else "other",
                    "requirement_category": requirement_category(text),
                    "requirement_label_raw": clause["clause_label_raw"],
                    "requirement_text_raw": text,
                    "applicability": {"conditions": []},
                    "numeric_value_refs": numeric_refs,
                    "term_refs": [],
                    "source_refs": [source_ref("clause", clause["clause_id"])],
                    "confidence": "medium" if target is requirements else "needs_review",
                }
            )

    return numeric_values, requirements, other_requirements


def term_category_from_entry(table: str, entry: dict[str, Any] | None) -> str:
    if not entry:
        return "unknown"
    metadata = entry.get("metadata") or {}
    return metadata.get("category") or metadata.get("term_category") or "unknown"


def confidence_from_entry(entry: dict[str, Any] | None) -> str:
    if not entry:
        return "needs_review"
    return "needs_review" if entry.get("status") == "review" else "high"


KNOWN_ZONE_CODES = [
    "ER-MUVC",
    "DMUN",
    "R-4A",
    "R-4B",
    "R-3T",
    "R-1S",
    "R-1L",
    "R-1N",
    "MUC",
    "CDA",
    "DMS",
    "DMU",
    "DN",
    "DC",
    "WF",
    "WLC",
    "PZ",
    "PC",
    "MH",
    "MHR",
    "M-1",
    "M-2",
    "M-3",
    "R-2S",
    "R-2",
    "R-3",
    "R-4",
    "C-1",
    "C-2",
    "C-3",
    "FD",
    "OS",
    "P",
    "I",
    "A",
]

ZONE_NAME_CODES = {
    "airport": "A",
    "business park industrial": "M-3",
    "downtown mixed use neighbourhood": "DMUN",
    "downtown neighbourhood": "DN",
    "downtown core": "DC",
    "downtown mixed use": "DMU",
    "er-mixed use village centre": "ER-MUVC",
    "institutional": "I",
    "park/cultural": "PC",
    "parks/cultural": "PC",
    "port": "PZ",
    "waterfront": "WF",
}


def referenced_zone_codes(text: str) -> list[str]:
    found: list[str] = []
    normalized = clean_text(text)
    for code in KNOWN_ZONE_CODES:
        code_pattern = re.escape(code).replace("\\-", r"[- ]?")
        if re.search(rf"\b{code_pattern}\b(?:\s+Zone)?", normalized, flags=re.IGNORECASE) and code not in found:
            found.append(code)
    lowered = normalized.lower()
    for name, code in ZONE_NAME_CODES.items():
        if f"{name} zone" in lowered and code not in found:
            found.append(code)
    return found


def zone_reference_relationship_types(text: str) -> list[str]:
    lowered = text.lower()
    types = []
    if "uses permitted in" in lowered or "uses as permitted in" in lowered or "uses permitted" in lowered:
        types.append("inherits_uses")
    if "regulations" in lowered or "subject to" in lowered:
        types.append("inherits_regulations")
    return types or ["references_zone"]


def is_zone_reference_clause(text: str) -> bool:
    lowered = text.lower()
    return bool(referenced_zone_codes(text)) and (
        "uses permitted" in lowered
        or "uses as permitted" in lowered
        or "subject to the regulations" in lowered
        or "subject to regulations" in lowered
        or "regulations for permitted uses" in lowered
    )


def raw_clause_lookup(raw_sections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    clauses = {}
    for section in raw_sections:
        for clause in section.get("clauses_raw") or []:
            clauses[clause["clause_id"]] = clause
    return clauses


def build_zone_reference_structures(
    data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    metadata = data.get("document_metadata") or {}
    prefix = ((data.get("raw_data") or {}).get("source_units") or [{}])[0].get("source_unit_id") or f"zone-{slugify(metadata.get('zone_code'))}"
    source_zone_code = metadata.get("zone_code") or prefix.replace("zone-", "").upper()
    clauses = raw_clause_lookup((data.get("raw_data") or {}).get("sections_raw") or [])
    terms = []
    relationships = []
    reference_clause_ids: set[str] = set()
    relationship_keys: set[tuple[str, str, str]] = set()
    for clause_id, clause in clauses.items():
        raw_text = strip_list_punctuation(clause.get("clause_text_raw") or "")
        target_zone_codes = referenced_zone_codes(raw_text)
        if not is_zone_reference_clause(raw_text) or not target_zone_codes:
            continue
        reference_clause_ids.add(clause_id)
        normalized_targets = "_".join(code_key(code) for code in target_zone_codes)
        terms.append(
            {
                "term_id": f"{prefix}-term-reference-{slugify(clause_id)}",
                "term_raw": raw_text,
                "term_normalized": f"zone_reference_{normalized_targets}",
                "term_category": "document_reference",
                "source_refs": [source_ref("clause", clause_id)],
                "confidence": "high",
            }
        )
        for target_zone_code in target_zone_codes:
            for relationship_type in zone_reference_relationship_types(raw_text):
                key = (relationship_type, clause_id, target_zone_code)
                if key in relationship_keys:
                    continue
                relationship_keys.add(key)
                relationships.append(
                    {
                        "relationship_id": f"{prefix}-relationship-{relationship_type}-{slugify(target_zone_code)}-{slugify(clause_id)}",
                        "relationship_type": relationship_type,
                        "source_ref": source_ref("zone", source_zone_code),
                        "target_ref": source_ref("zone", target_zone_code),
                        "scope": "zone_reference_clause",
                        "source_clause_ref": clause_id,
                        "join_behavior": "include_target_values" if relationship_type.startswith("inherits_") else "reference_only",
                        "confidence": "high",
                    }
                )
    return terms, relationships, reference_clause_ids


def apply_zone_reference_model(data: dict[str, Any]) -> dict[str, Any]:
    if (data.get("document_metadata") or {}).get("document_type") != "zone":
        structured = data.get("structured_data") or {}
        structured["zone_relationships"] = [
            relationship
            for relationship in structured.get("zone_relationships") or []
            if relationship.get("scope") != "zone_reference_clause"
        ]
        structured["cross_references"] = [
            relationship
            for relationship in structured.get("cross_references") or []
            if relationship.get("scope") != "zone_reference_clause"
        ]
        return data
    structured = data.setdefault("structured_data", base_structured_data())
    reference_terms, relationships, reference_clause_ids = build_zone_reference_structures(data)
    if not reference_clause_ids:
        return data
    reference_clause_term_ids = {term["term_id"] for term in reference_terms}
    removed_use_term_ids = {
        use.get("use_term_id")
        for use in structured.get("uses") or []
        if use.get("source_clause_ref") in reference_clause_ids
    }
    structured["uses"] = [
        use for use in structured.get("uses") or [] if use.get("source_clause_ref") not in reference_clause_ids
    ]
    filtered_terms = []
    for term in structured.get("terms") or []:
        source_clause_ids = {
            ref.get("source_ref_id")
            for ref in term.get("source_refs") or []
            if ref.get("source_ref_type") == "clause"
        }
        if term.get("term_id") in removed_use_term_ids or source_clause_ids <= reference_clause_ids and source_clause_ids:
            continue
        filtered_terms.append(term)
    existing_term_ids = {term["term_id"] for term in filtered_terms}
    for term in reference_terms:
        if term["term_id"] not in existing_term_ids:
            filtered_terms.append(term)
            existing_term_ids.add(term["term_id"])
    structured["terms"] = filtered_terms
    structured["zone_relationships"] = [
        relationship
        for relationship in structured.get("zone_relationships") or []
        if relationship.get("source_clause_ref") not in reference_clause_ids
    ]
    structured["cross_references"] = [
        relationship
        for relationship in structured.get("cross_references") or []
        if relationship.get("source_clause_ref") not in reference_clause_ids
    ]
    existing_relationship_ids = {
        relationship.get("relationship_id")
        for relationship in (structured.get("zone_relationships") or []) + (structured.get("cross_references") or [])
    }
    for relationship in relationships:
        if relationship["relationship_id"] not in existing_relationship_ids:
            structured["zone_relationships"].append(relationship)
            existing_relationship_ids.add(relationship["relationship_id"])
    cross_reference_keys: set[tuple[str, str]] = set()
    for relationship in relationships:
        key = (relationship["source_clause_ref"], relationship["target_ref"]["source_ref_id"])
        if key in cross_reference_keys:
            continue
        cross_reference_keys.add(key)
        cross_reference = {
            **relationship,
            "relationship_id": f"{relationship['source_ref']['source_ref_id'].lower().replace('-', '_')}-cross-reference",
            "relationship_type": "references_zone",
            "join_behavior": "reference_only",
        }
        cross_reference["relationship_id"] = (
            f"{((data.get('raw_data') or {}).get('source_units') or [{}])[0].get('source_unit_id')}"
            f"-cross-reference-references-zone-{slugify(relationship['target_ref']['source_ref_id'])}-{slugify(relationship['source_clause_ref'])}"
        )
        if cross_reference["relationship_id"] not in existing_relationship_ids:
            structured["cross_references"].append(cross_reference)
            existing_relationship_ids.add(cross_reference["relationship_id"])
    for group in structured.get("regulation_groups") or []:
        group["regulated_use_terms"] = [
            term_id
            for term_id in group.get("regulated_use_terms") or []
            if term_id not in removed_use_term_ids and term_id not in reference_clause_term_ids
        ]
    data["review_flags"] = [
        flag
        for flag in data.get("review_flags") or []
        if not any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") in reference_clause_ids
            for ref in flag.get("source_refs") or []
        )
    ]
    return data


def build_terms_and_uses(
    normalizer: Normalizer,
    legacy_uses: list[dict[str, Any]],
    prefix: str,
    clause_lookup: dict[tuple[str, ...], str],
    review_flags: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    terms_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    uses = []
    for index, item in enumerate(legacy_uses, start=1):
        raw_name = strip_list_punctuation(item.get("use_name"))
        if not raw_name:
            continue
        path = tuple(str(part) for part in (item.get("clause_path") or []))
        src_clause = clause_lookup.get(path)
        refs = [source_ref("clause", src_clause)] if src_clause else []
        if src_clause and is_zone_reference_clause(raw_name):
            continue
        components = normalizer.match_term_components(raw_name)
        for component_index, component in enumerate(components, start=1):
            table = component["table"]
            entry = component["entry"]
            normalized = component["normalized"]
            if normalized in NON_QUERYABLE_USE_TERMS:
                continue
            component_raw = component["raw"]
            category = term_category_from_entry(table, entry)
            term_key = (table if entry else "unmatched", normalized)
            term_id = f"{prefix}-term-{term_key[0]}-{normalized}"
            if term_key not in terms_by_key:
                term = {
                    "term_id": term_id,
                    "term_raw": component_raw,
                    "term_normalized": normalized,
                    "term_category": category,
                    "source_refs": refs,
                    "confidence": confidence_from_entry(entry),
                }
                if entry:
                    term["code_table"] = table
                    term["code"] = normalized
                terms_by_key[term_key] = term
            elif refs:
                existing_refs = terms_by_key[term_key].setdefault("source_refs", [])
                if refs[0] not in existing_refs:
                    existing_refs.append(refs[0])

            if not entry or entry.get("status") == "review":
                review_type = "code_table_review" if entry else "code_table_match_review"
                description = (
                    f"Use phrase matched a review-status code table entry: {component_raw}"
                    if entry
                    else f"Use phrase was preserved but did not match reviewed term/use code tables: {component_raw}"
                )
                review_flags.append(
                    make_review_flag(
                        f"{prefix}-flag-unmatched-use-{slugify(component_raw)}-{index}-{component_index}",
                        review_type,
                        description,
                        refs,
                    )
                )

            use_type = item.get("use_type") or ""
            use_status = "accessory_or_secondary" if use_type == "accessory_or_secondary_use" else "permitted"
            use_id_suffix = slugify(component_raw if len(components) > 1 else raw_name)
            uses.append(
                {
                    "use_id": f"{prefix}-use-{use_id_suffix}-{index}-{component_index}",
                    "use_name_raw": component_raw,
                    "use_term_id": term_id,
                    "use_status": use_status,
                    "source_clause_ref": src_clause or "",
                    "confidence": confidence_from_entry(entry),
                }
            )
    return list(terms_by_key.values()), uses


def clause_lookup_from_raw(raw_sections: list[dict[str, Any]]) -> dict[tuple[str, ...], str]:
    lookup: dict[tuple[str, ...], str] = {}
    current_parent_path: tuple[str, ...] = ()
    for section in raw_sections:
        for clause in section.get("clauses_raw") or []:
            label = clause["clause_label_raw"]
            if re.fullmatch(r"\d+(?:\.\d+)+", label):
                current_parent_path = (label,)
                lookup[current_parent_path] = clause["clause_id"]
            elif current_parent_path:
                lookup[current_parent_path + (label,)] = clause["clause_id"]
            lookup[(label,)] = clause["clause_id"]
    return lookup


def base_structured_data() -> dict[str, Any]:
    return {
        "terms": [],
        "uses": [],
        "numeric_values": [],
        "requirements": [],
        "regulation_groups": [],
        "conditional_rule_groups": [],
        "zone_relationships": [],
        "map_layer_references": [],
        "other_requirements": [],
        "cross_references": [],
    }


def map_refs(prefix: str, citation_value: dict[str, Any], zone_code: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_id = f"{prefix}-map-zoning-map"
    raw = [
        {
            "map_reference_id": raw_id,
            "map_label_raw": "Zoning Map",
            "map_title_raw": "Charlottetown Zoning Map 2026",
            "text_raw": "Current zoning map raster package represented in PostGIS-compatible spatial artifacts.",
            "citations": citation_value,
        }
    ]
    structured = [
        {
            "map_reference_id": raw_id,
            "map_title_raw": "Charlottetown Zoning Map 2026",
            "map_label_raw": "Zoning Map",
            "map_reference_type": "zoning_map",
            "postgis_schema": "public",
            "postgis_table": "spatial_features",
            "postgis_layer_name": "charlottetown_zoning_map_2026_raster",
            "feature_key": zone_code or "zoning_map",
            "source_refs": [source_ref("map_reference", raw_id)],
            "confidence": "medium",
        }
    ]
    return raw, structured


def transform_zone(normalizer: Normalizer, legacy: dict[str, Any]) -> dict[str, Any]:
    metadata = legacy.get("document_metadata") or {}
    prefix = f"zone-{slugify(metadata.get('zone_code'))}"
    raw_sections, clause_refs, table_refs = build_raw_sections(prefix, legacy.get("requirement_sections") or [])
    review_flags: list[dict[str, Any]] = []
    clause_lookup = clause_lookup_from_raw(raw_sections)
    terms, uses = build_terms_and_uses(normalizer, legacy.get("permitted_uses") or [], prefix, clause_lookup, review_flags)
    numeric_values, requirements, other_requirements = build_numeric_and_requirements(raw_sections, prefix, review_flags)
    doc_cite = doc_citation_from_legacy(legacy)
    raw_map_refs, structured_map_refs = map_refs(prefix, doc_cite, metadata.get("zone_code"))
    source_unit_id = prefix
    structured = base_structured_data()
    structured.update(
        {
            "terms": terms,
            "uses": uses,
            "numeric_values": numeric_values,
            "requirements": requirements,
            "regulation_groups": [
                {
                    "regulation_group_id": f"{prefix}-regulation-group-zone",
                    "group_label_raw": str(metadata.get("part_label_raw") or ""),
                    "group_title_raw": zone_title_from_heading(metadata),
                    "regulated_use_terms": [use["use_term_id"] for use in uses if use.get("use_status") == "permitted"],
                    "applicability": {"applies_to_zone_codes": [metadata.get("zone_code")], "conditions": []},
                    "requirement_refs": [req["requirement_id"] for req in requirements],
                    "source_section_ref": raw_sections[0]["section_id"] if raw_sections else source_unit_id,
                    "confidence": "medium",
                }
            ],
            "map_layer_references": structured_map_refs,
            "other_requirements": other_requirements,
        }
    )
    data_for_references = {"document_metadata": {**metadata, "document_type": "zone"}, "raw_data": {"source_units": [{"source_unit_id": prefix}], "sections_raw": raw_sections}, "structured_data": structured, "review_flags": review_flags}
    apply_zone_reference_model(data_for_references)
    structured = data_for_references["structured_data"]
    review_flags = data_for_references["review_flags"]
    for issue_index, issue in enumerate(legacy.get("open_issues") or [], start=1):
        review_flags.append(
            make_review_flag(
                f"{prefix}-flag-legacy-open-issue-{issue_index}",
                issue.get("issue_type") or "legacy_extraction_review",
                issue.get("description") or "Legacy extraction issue preserved for review.",
                [source_ref("source_unit", source_unit_id)],
            )
        )
    return {
        "$schema": "../../../schema/json-schema/charlottetown-bylaw-extraction.schema.json",
        "document_metadata": {
            "jurisdiction": metadata.get("jurisdiction") or JURISDICTION,
            "bylaw_name": metadata.get("bylaw_name") or BYLAW_NAME,
            "source_document_path": metadata.get("source_document_path") or SOURCE_REL,
            "document_type": "zone",
            "zone_code": metadata.get("zone_code") or "",
            "zone_name": metadata.get("zone_name") or "",
            "zone_label_raw": str(metadata.get("part_label_raw") or ""),
            "zone_title_raw": zone_title_from_heading(metadata),
            "citations": doc_cite,
        },
        "raw_data": {
            "source_units": [
                {
                    "source_unit_id": source_unit_id,
                    "source_unit_type": "zone",
                    "label_raw": str(metadata.get("part_label_raw") or ""),
                    "title_raw": zone_title_from_heading(metadata),
                    "text_raw": "\n".join(
                        clause["clause_text_raw"]
                        for section in raw_sections
                        for clause in section.get("clauses_raw") or []
                    ),
                    "source_order": 1,
                    "citations": doc_cite,
                }
            ],
            "sections_raw": raw_sections,
            "clause_refs": clause_refs,
            "tables_raw": table_refs,
            "map_references_raw": raw_map_refs,
        },
        "structured_data": structured,
        "review_flags": review_flags,
    }


def transform_sections_doc(normalizer: Normalizer, legacy: dict[str, Any], document_type: str) -> dict[str, Any]:
    metadata = legacy.get("document_metadata") or {}
    source = legacy.get("source_section") or {}
    prefix = f"doc-{slugify(document_type)}"
    raw_sections, clause_refs, table_refs = build_raw_sections(prefix, legacy.get("sections") or [])
    review_flags: list[dict[str, Any]] = []
    numeric_values, requirements, other_requirements = build_numeric_and_requirements(raw_sections, prefix, review_flags)
    raw_map_refs, structured_map_refs = map_refs(prefix, citation(source))
    structured = base_structured_data()
    structured.update(
        {
            "numeric_values": numeric_values,
            "requirements": requirements,
            "regulation_groups": [
                {
                    "regulation_group_id": f"{prefix}-regulation-group",
                    "group_title_raw": source.get("title_label_raw") or metadata.get("document_type") or document_type,
                    "requirement_refs": [req["requirement_id"] for req in requirements],
                    "source_section_ref": raw_sections[0]["section_id"] if raw_sections else f"{prefix}-source",
                    "confidence": "medium",
                }
            ],
            "map_layer_references": structured_map_refs,
            "other_requirements": other_requirements,
        }
    )
    for issue_index, issue in enumerate(legacy.get("open_issues") or [], start=1):
        review_flags.append(
            make_review_flag(
                f"{prefix}-flag-legacy-open-issue-{issue_index}",
                issue.get("issue_type") or "legacy_extraction_review",
                issue.get("description") or "Legacy extraction issue preserved for review.",
                [source_ref("document", prefix)],
            )
        )
    return {
        "$schema": "../../schema/json-schema/charlottetown-bylaw-extraction.schema.json",
        "document_metadata": {
            "jurisdiction": metadata.get("jurisdiction") or JURISDICTION,
            "bylaw_name": metadata.get("bylaw_name") or BYLAW_NAME,
            "source_document_path": metadata.get("source_document_path") or SOURCE_REL,
            "document_type": document_type,
            "document_label_raw": source.get("section_range_raw") or "",
            "document_title_raw": source.get("title_label_raw") or document_type,
            "citations": citation(source),
        },
        "raw_data": {
            "source_units": [
                {
                    "source_unit_id": f"{prefix}-source",
                    "source_unit_type": document_type,
                    "label_raw": source.get("section_range_raw") or "",
                    "title_raw": source.get("title_label_raw") or "",
                    "text_raw": "\n".join(
                        clause["clause_text_raw"]
                        for section in raw_sections
                        for clause in section.get("clauses_raw") or []
                    ),
                    "source_order": 1,
                    "citations": citation(source),
                }
            ],
            "sections_raw": raw_sections,
            "clause_refs": clause_refs,
            "tables_raw": table_refs,
            "map_references_raw": raw_map_refs,
        },
        "structured_data": structured,
        "review_flags": review_flags,
    }


def transform_definitions(normalizer: Normalizer, legacy: dict[str, Any]) -> dict[str, Any]:
    metadata = legacy.get("document_metadata") or {}
    source = legacy.get("source_section") or {}
    prefix = "doc-definitions"
    entries_raw = []
    definitions = []
    terms_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    review_flags: list[dict[str, Any]] = []
    for index, entry in enumerate(legacy.get("definitions") or [], start=1):
        raw_term = clean_text(entry.get("term_raw"))
        definition_text = clean_text(entry.get("definition_text"))
        entry_id = f"{prefix}-entry-{index}"
        entries_raw.append(
            {
                "definition_entry_id": entry_id,
                "term_raw": raw_term,
                "definition_text_raw": definition_text,
                "source_order": index,
                "citations": citation(entry.get("citations")),
            }
        )
        table, matched = normalizer.match_term(raw_term)
        if matched:
            term_id = f"{prefix}-term-{table}-{matched['code']}"
            term_key = (table, matched["code"])
            if term_key not in terms_by_key:
                terms_by_key[term_key] = {
                    "term_id": term_id,
                    "term_raw": raw_term,
                    "term_normalized": matched["code"],
                    "term_category": term_category_from_entry(table, matched),
                    "code_table": table,
                    "code": matched["code"],
                    "source_refs": [source_ref("definition", entry_id)],
                    "confidence": "high",
                }
        else:
            term_id = ""
        definitions.append(
            {
                "definition_id": f"{prefix}-definition-{index}",
                "definition_key": entry.get("definition_key") or code_key(raw_term),
                "term_raw": raw_term,
                "term_id": term_id,
                "definition_text": definition_text,
                "source_refs": [source_ref("definition", entry_id)],
                "cross_references": [],
                "confidence": "medium" if definition_text else "needs_review",
            }
        )
    structured = base_structured_data()
    structured["terms"] = list(terms_by_key.values())
    structured["definitions"] = definitions
    return {
        "$schema": "../../schema/json-schema/charlottetown-bylaw-extraction.schema.json",
        "document_metadata": {
            "jurisdiction": metadata.get("jurisdiction") or JURISDICTION,
            "bylaw_name": metadata.get("bylaw_name") or BYLAW_NAME,
            "source_document_path": metadata.get("source_document_path") or SOURCE_REL,
            "document_type": "definitions",
            "document_label_raw": source.get("section_range_raw") or "APPENDIX A",
            "document_title_raw": source.get("title_label_raw") or "DEFINITIONS",
            "citations": citation(source),
        },
        "raw_data": {
            "source_units": [
                {
                    "source_unit_id": f"{prefix}-source",
                    "source_unit_type": "definitions",
                    "label_raw": source.get("section_range_raw") or "APPENDIX A",
                    "title_raw": source.get("title_label_raw") or "DEFINITIONS",
                    "text_raw": "\n".join(f"{item['term_raw']}: {item['definition_text_raw']}" for item in entries_raw),
                    "source_order": 1,
                    "citations": citation(source),
                }
            ],
            "entries_raw": entries_raw,
            "clause_refs": [],
            "tables_raw": [],
            "map_references_raw": [],
        },
        "structured_data": structured,
        "review_flags": review_flags,
    }


def transform_appendix(normalizer: Normalizer, legacy: dict[str, Any], filename: str) -> dict[str, Any]:
    metadata = legacy.get("document_metadata") or {}
    prefix = f"appendix-{slugify(metadata.get('part_label_raw') or filename)}"
    blocks = legacy.get("content_blocks") or []
    pages_raw = []
    order = 1
    for block in blocks:
        for page in block.get("text_by_page") or []:
            pdf_page = page.get("pdf_page")
            pages_raw.append(
                {
                    "page_id": f"{prefix}-page-{pdf_page or order}",
                    "pdf_page": pdf_page,
                    "bylaw_page": pdf_page,
                    "text_raw": page.get("text") or "",
                    "source_order": order,
                }
            )
            order += 1
    cite = citation((blocks[0] if blocks else {}).get("citations") or (legacy.get("citations") or {}).get("appendix"))
    raw_map_refs, structured_map_refs = map_refs(prefix, cite)
    structured = base_structured_data()
    structured["map_layer_references"] = structured_map_refs
    structured["spatial_references"] = structured_map_refs
    if "site-specific" in (metadata.get("title_label_raw") or "").lower() or "site specific" in (metadata.get("title_label_raw") or "").lower():
        structured["site_specific_rules"] = []
    review_flags = [
        make_review_flag(
            f"{prefix}-flag-appendix-table-review",
            "appendix_table_review",
            "Appendix table pages are preserved by page; row-level normalization requires source layout review.",
            [source_ref("document", f"{prefix}-source")],
        )
    ]
    return {
        "$schema": "../../schema/json-schema/charlottetown-bylaw-extraction.schema.json",
        "document_metadata": {
            "jurisdiction": metadata.get("jurisdiction") or JURISDICTION,
            "bylaw_name": metadata.get("bylaw_name") or BYLAW_NAME,
            "source_document_path": metadata.get("source_document_path") or SOURCE_REL,
            "document_type": "appendix_table",
            "appendix_label_raw": metadata.get("part_label_raw") or "",
            "appendix_title_raw": metadata.get("title_label_raw") or "",
            "citations": cite,
        },
        "raw_data": {
            "source_units": [
                {
                    "source_unit_id": f"{prefix}-source",
                    "source_unit_type": "appendix_table",
                    "label_raw": metadata.get("part_label_raw") or "",
                    "title_raw": metadata.get("title_label_raw") or "",
                    "text_raw": "\n".join(page["text_raw"] for page in pages_raw),
                    "source_order": 1,
                    "citations": cite,
                }
            ],
            "pages_raw": pages_raw,
            "clause_refs": [],
            "tables_raw": [],
            "map_references_raw": raw_map_refs,
        },
        "structured_data": structured,
        "review_flags": review_flags,
    }


def update_readme() -> None:
    readme = OUT / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    note = (
        "\n## Approved schema extraction update\n\n"
        "- Bylaw JSON files are emitted in the approved `charlottetown-bylaw-extraction` schema shape.\n"
        "- Legacy top-level importer compatibility fields are not preserved in generated bylaw JSON files.\n"
        "- Reviewed term and use code tables are matched through `structured_data.terms[]` and linked from `structured_data.uses[].use_term_id`.\n"
        "- Unknown normalized assignments are preserved with `review_flags[]`.\n"
    )
    if "## Approved schema extraction update" not in text:
        readme.write_text(text.rstrip() + note, encoding="utf-8")


def strip_unreviewed_term_codes(data: dict[str, Any]) -> dict[str, Any]:
    return data


def refresh_schema_terms(normalizer: Normalizer, data: dict[str, Any]) -> dict[str, Any]:
    structured = data.get("structured_data") or {}
    prefix = ((data.get("raw_data") or {}).get("source_units") or [{}])[0].get("source_unit_id") or "document"
    id_changes: dict[str, list[str]] = {}
    review_flags = data.setdefault("review_flags", [])
    existing_flag_ids = {flag.get("review_flag_id") for flag in review_flags}
    refreshed_terms = []
    seen_ids: set[str] = set()
    for term in structured.get("terms") or []:
        old_id = term["term_id"]
        components = normalizer.match_term_components(term.get("term_raw") or term.get("term_normalized") or "")
        new_ids = []
        for component in components:
            table = component["table"]
            entry = component["entry"]
            normalized = component["normalized"]
            if normalized in NON_QUERYABLE_USE_TERMS:
                id_changes[old_id] = []
                continue
            new_id = f"{prefix}-term-{table}-{normalized}"
            new_ids.append(new_id)
            refreshed = dict(term)
            if entry:
                refreshed["term_id"] = new_id
                refreshed["term_raw"] = component["raw"]
                refreshed["term_normalized"] = normalized
                refreshed["term_category"] = term_category_from_entry(table, entry)
                refreshed["code_table"] = table
                refreshed["code"] = normalized
                refreshed["confidence"] = confidence_from_entry(entry)
                id_changes[f"{prefix}-term-term-{normalized}"] = [new_id]
                id_changes[f"{prefix}-term-unmatched-{normalized}"] = [new_id]
                if entry.get("status") == "review":
                    flag_id = f"{prefix}-flag-review-code-{slugify(normalized)}"
                    if flag_id not in existing_flag_ids:
                        review_flags.append(
                            make_review_flag(
                                flag_id,
                                "code_table_review",
                                f"Term matched a review-status code table entry: {component['raw'] or normalized}",
                                refreshed.get("source_refs") or [],
                            )
                        )
                        existing_flag_ids.add(flag_id)
            else:
                refreshed["term_id"] = new_id
                refreshed["term_raw"] = component["raw"]
                refreshed["term_normalized"] = normalized
                refreshed["term_category"] = "unknown"
                refreshed["confidence"] = "needs_review"
                refreshed.pop("code_table", None)
                refreshed.pop("code", None)
                flag_id = f"{prefix}-flag-unmatched-term-{slugify(component['raw'] or normalized or old_id)}"
                if flag_id not in existing_flag_ids:
                    review_flags.append(
                        make_review_flag(
                            flag_id,
                            "code_table_match_review",
                            f"Term was preserved but did not match reviewed term/use code tables: {component['raw'] or normalized}",
                            refreshed.get("source_refs") or [],
                        )
                    )
                    existing_flag_ids.add(flag_id)
            if refreshed["term_id"] not in seen_ids:
                refreshed_terms.append(refreshed)
                seen_ids.add(refreshed["term_id"])
        id_changes[old_id] = new_ids
    structured["terms"] = refreshed_terms
    term_confidence_by_id = {term["term_id"]: term.get("confidence", "needs_review") for term in refreshed_terms}
    refreshed_uses = []
    seen_use_ids: set[str] = set()
    for use in structured.get("uses") or []:
        if use.get("use_status") == "accessory":
            use["use_status"] = "accessory_or_secondary"
        components = normalizer.match_term_components(use.get("use_name_raw") or "")
        if all(component["normalized"] in NON_QUERYABLE_USE_TERMS for component in components):
            continue
        if len(components) > 1:
            for index, component in enumerate(components, start=1):
                table = component["table"]
                normalized = component["normalized"]
                if normalized in NON_QUERYABLE_USE_TERMS:
                    continue
                new_use = dict(use)
                new_use["use_id"] = f"{use['use_id']}-{slugify(normalized)}"
                new_use["use_name_raw"] = component["raw"]
                new_use["use_term_id"] = f"{prefix}-term-{table}-{normalized}"
                new_use["confidence"] = term_confidence_by_id.get(new_use["use_term_id"], "needs_review")
                if new_use["use_id"] not in seen_use_ids:
                    refreshed_uses.append(new_use)
                    seen_use_ids.add(new_use["use_id"])
            continue
        if use.get("use_term_id") in id_changes and id_changes[use["use_term_id"]]:
            use["use_term_id"] = id_changes[use["use_term_id"]][0]
        if use.get("use_term_id") in term_confidence_by_id:
            use["confidence"] = term_confidence_by_id[use["use_term_id"]]
        if use["use_id"] not in seen_use_ids:
            refreshed_uses.append(use)
            seen_use_ids.add(use["use_id"])
    structured["uses"] = refreshed_uses

    def expand_refs(term_ids: list[str]) -> list[str]:
        expanded = []
        seen = set()
        for term_id in term_ids:
            replacements = id_changes.get(term_id, [term_id])
            for replacement in replacements:
                if replacement not in seen:
                    expanded.append(replacement)
                    seen.add(replacement)
        return expanded

    for requirement in structured.get("requirements") or []:
        requirement["term_refs"] = expand_refs(requirement.get("term_refs") or [])
    for group in structured.get("regulation_groups") or []:
        group["regulated_use_terms"] = expand_refs(group.get("regulated_use_terms") or [])
    return data


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    if fitz is None:
        raise RuntimeError("PyMuPDF is required to rebuild coordinate-aware Charlottetown regulation tables.")
    manifest_path = OUT / "source-manifest.json"
    manifest = read_json(manifest_path)
    normalizer = Normalizer()
    pdf_doc = fitz.open(SOURCE)

    for zone in manifest.get("zones", []):
        path = OUT / zone["file"]
        data = read_json(path)
        if {"raw_data", "structured_data", "review_flags"}.issubset(data):
            rebuild_clause_refs(data)
            rebuild_schema_tables_from_pdf(pdf_doc, data)
            reset_review_flags(data)
            refresh_schema_numeric_values(data)
            write_json(path, apply_zone_reference_model(refresh_schema_terms(normalizer, strip_unreviewed_term_codes(data))))
            continue
        transformed = transform_zone(normalizer, data)
        rebuild_schema_tables_from_pdf(pdf_doc, transformed)
        write_json(path, transformed)

    for item in manifest.get("document_files", []):
        path = OUT / item["file"]
        if not path.exists():
            continue
        data = read_json(path)
        if {"raw_data", "structured_data", "review_flags"}.issubset(data):
            rebuild_clause_refs(data)
            rebuild_schema_tables_from_pdf(pdf_doc, data)
            reset_review_flags(data)
            refresh_schema_numeric_values(data)
            write_json(path, apply_zone_reference_model(refresh_schema_terms(normalizer, strip_unreviewed_term_codes(data))))
            continue
        document_type = item.get("document_type") or (data.get("document_metadata") or {}).get("document_type")
        if document_type == "definitions":
            write_json(path, transform_definitions(normalizer, data))
        elif document_type in {"general_provisions", "design_standards"}:
            write_json(path, transform_sections_doc(normalizer, data, document_type))

    for item in manifest.get("supporting_files", []):
        path = OUT / item["file"]
        if not path.exists():
            continue
        data = read_json(path)
        if {"raw_data", "structured_data", "review_flags"}.issubset(data):
            rebuild_clause_refs(data)
            rebuild_schema_tables_from_pdf(pdf_doc, data)
            reset_review_flags(data)
            refresh_schema_numeric_values(data)
            write_json(path, apply_zone_reference_model(refresh_schema_terms(normalizer, strip_unreviewed_term_codes(data))))
            continue
        write_json(path, transform_appendix(normalizer, data, item["file"]))

    manifest["extracted_at_local"] = datetime.now().replace(microsecond=0).isoformat()
    manifest["extractor"] = "scripts/extract-charlottetown-zoning-bylaw.py; approved schema extraction"
    limits = manifest.setdefault("known_limits", [])
    new_limits = [
        "Generated JSON files use the approved extraction schema and omit legacy importer compatibility fields.",
        "Reviewed term and use code tables are matched through structured_data.terms and linked from uses.use_term_id.",
        "Unmatched normalized terms, use phrases, table cells, and layout-sensitive content are preserved with review_flags.",
    ]
    for limit in new_limits:
        if limit not in limits:
            limits.append(limit)
    write_json(manifest_path, manifest)
    update_readme()


if __name__ == "__main__":
    main()

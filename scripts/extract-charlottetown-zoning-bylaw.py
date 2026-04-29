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
    "m2": "sq_m",
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
    "building": "building",
    "buildings": "building",
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
    for unit in sorted((unit for unit in UNIT_MAP if unit != "m2"), key=len, reverse=True)
)
MEASUREMENT_RE = re.compile(
    rf"(?P<value>\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?P<unit>{UNIT_RE})\b",
    re.IGNORECASE,
)
TABLE_UNIT_RE = "|".join(
    re.escape(unit)
    for unit in sorted(UNIT_MAP, key=len, reverse=True)
)
TABLE_MEASUREMENT_RE = re.compile(
    rf"(?P<value>\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?P<unit>{TABLE_UNIT_RE})(?=\b|[^A-Za-z0-9_]|$)",
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
    "hostel_hotel": ["hostel", "hotel"],
    "parking_lot_structure": ["parking_lot", "parking_structure"],
    "semi_detached_or_duplex_dwelling": ["semi_detached_dwelling", "duplex_dwelling"],
    "single_detached_dwelling_up_to_4_units": ["single_detached_dwelling"],
    "retail_store_with_connected_retail_warehouse_light_manufacturing_or_assembly_facility": [
        "retail_store",
        "retail_warehouse",
        "light_manufacturing",
        "assembly_facility",
    ],
    "the_only_permitted_uses_in_this_zone_include_single_detached_dwellings_additions_or_accessory_buildings_are_permitted_according_to_section_3_1": [
        "single_detached_dwelling",
        "accessory_building",
    ],
    "warehouse_and_or_distribution_centre": ["warehouse", "distribution_centre"],
    "warehouse_and_or_distribution_center": ["warehouse", "distribution_centre"],
    "warehouse_storage_facility_and_or_distribution_centre": ["warehouse", "storage_facility", "distribution_centre"],
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
    "apartment_dwelling": "apartment_building",
    "apartment_dwellings": "apartment_building",
    "apartments": "apartment_building",
    "duplex_dwellings": "duplex_dwelling",
    "semi_detached_dwellings": "semi_detached_dwelling",
    "stacked_townhouse": "stacked_townhouse_dwelling",
    "converted_dwellings": "converted_dwelling",
    "multi_unit_dwelling": "apartment_building",
    "multi_unit_dwellings": "apartment_building",
    "one_single_detached_dwelling_per_lot_with_serviced_lot_frontage": "single_detached_dwelling",
    "home_daycare_home": "home_daycare",
    "tourist_accommodation": "tourist_accommodations",
    "transitional_housing": "transitional_housing_facility",
}

NON_QUERYABLE_USE_TERMS = {
    "ancillary_uses_to_the_foregoing",
    "coverage_max_60",
    "council_shall_give_due_consideration_to_other_sections_of_this_by_law_but_council_may_approve_any_use_or_development_in_a_cda_zone_which_it_deems_to_be_in_the_public_interest_notwithstanding_all_other_sections_of_this_by_law_but_only_after_following_the_procedures_set_out_in_this_section",
    "existing_uses",
    "flaglots_are_permitted_with_no_less_than_6_m_frontage_as_long_as_all_other_site_and_building",
    "flankage_yard_setback_min_6_m",
    "footprint_building_max_800_m2",
    "front_yard_setback_min_6_m",
    "golf_course_zoning_and_development_byl_aw",
    "lot_area_min_1_100_m2",
    "rear_yard_setback_min_6_m",
    "separation_between_units_min_6_m",
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
    current: dict[str, Any] | None = None
    previous_requirement_right: float | None = None
    previous_value_bounds: list[tuple[float, float]] | None = None
    carry_across_pages = first_table.get("table_id") == "zone-dc-table-regulations-for-permitted-uses"
    for pdf_page in range(int(pdf_start), int(pdf_end) + 1):
        if not carry_across_pages:
            current = None
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
        if (
            carry_across_pages
            and pdf_page != int(pdf_start)
            and previous_requirement_right is not None
            and previous_value_bounds is not None
        ):
            requirement_right = previous_requirement_right
            value_bounds = previous_value_bounds
        elif carry_across_pages:
            previous_requirement_right = requirement_right
            previous_value_bounds = value_bounds
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


def repair_mur_mixed_density_section(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "MUR":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    section = next((item for item in sections if item.get("section_id") == "zone-mur-section-21-2"), None)
    if not section or not section.get("tables_raw"):
        return False
    parent_id = "zone-mur-clause-21-2-2"
    page_80 = {"pdf_page_start": 80, "pdf_page_end": 80, "bylaw_page_start": 80, "bylaw_page_end": 80}
    page_81 = {"pdf_page_start": 81, "pdf_page_end": 81, "bylaw_page_start": 81, "bylaw_page_end": 81}
    clauses = [
        (
            "zone-mur-clause-21-2-1",
            "21.2.1",
            "Development within the MUR Zone is meant to be of a mixed variety of building forms and density. Building forms within this Zone shall consist of a combination of Townhouse Dwellings, Semi-detached or Duplex Dwellings, Single-detached Dwellings, Nursing Homes and Community Care Facilities.",
            None,
            page_80,
        ),
        (
            parent_id,
            "21.2.2",
            "Within the MUR Zone the following Building forms shall be permitted on any Block in the percentages indicated:",
            None,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-2-a",
            "a",
            "Semi-detached and Duplex Dwellings shall be permitted on up to 25% of the Lots;",
            parent_id,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-2-b",
            "b",
            "Townhouses/Stacked Townhouses/Block Townhouse Dwellings shall be permitted on up to 25% of the Lots;",
            parent_id,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-2-c",
            "c",
            "Single-detached Dwellings shall be permitted on up to 35% of the Lots; and",
            parent_id,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-2-d",
            "d",
            "Institutional Uses as permitted in the R-3 Zone shall be permitted on up to 15% of the Lots. However, if the percentage for Institutional Uses is not used than the percentage allocated to this use can be allocated in 1/3 increments for the remaining uses as stipulated in this section or the remaining portion can be allocated in whole to Single-detached Dwellings.",
            parent_id,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-3",
            "21.2.3",
            "Single-detached, Semi-detached and Duplex Dwellings shall be permitted on adjoining Lots on the same side of the street adjacent to townhouse Dwellings. At least one side of a run of semi-detached or duplex Dwelling must be flanked by a Single-detached Dwelling.",
            None,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-4",
            "21.2.4",
            "No more than three (3) Townhouse Dwellings with a maximum of twelve (12) units total on all three (3) lots shall be permitted to be constructed on adjoining Lots on the same side of the street.",
            None,
            page_80,
        ),
        (
            "zone-mur-clause-21-2-5",
            "21.2.5",
            "At no time shall more than two (2) Townhouse Dwelling consisting of more than six (6) Dwelling Units be permitted to be constructed on adjoining Lots.",
            None,
            page_81,
        ),
        (
            "zone-mur-clause-21-2-6",
            "21.2.6",
            "Subdivision of land within the MUR Zone shall be undertaken in Phases. Prior to approval of a Subdivision within the MUR Zone a concept plan shall be submitted for the overall parcel. The concept plan shall indicate the Phases of Development and shall ensure the mixed density formula has been satisfied for the overall parcel of land.",
            None,
            page_81,
        ),
    ]
    section["clauses_raw"] = [
        {
            "clause_id": clause_id_value,
            "clause_label_raw": label,
            "clause_text_raw": text,
            "parent_clause_id": parent_clause_id,
            "source_order": order,
            "citations": cite,
        }
        for order, (clause_id_value, label, text, parent_clause_id, cite) in enumerate(clauses, start=1)
    ]
    section["tables_raw"] = []
    raw_data["tables_raw"] = [
        table_ref for table_ref in raw_data.get("tables_raw") or [] if table_ref.get("section_id") != section["section_id"]
    ]
    source_units = raw_data.get("source_units") or []
    if source_units:
        source_units[0]["text_raw"] = "\n".join(
            clause["clause_text_raw"]
            for raw_section in sections
            for clause in raw_section.get("clauses_raw") or []
        )
    rebuild_clause_refs(data)
    return True


def make_table_row(table_id_value: str, row_order: int, row_number: str, requirement: str, values: dict[str, str]) -> dict[str, Any]:
    row_id = f"{table_id_value}-row-{row_order}"
    cells = [
        {"cell_id": f"{row_id}-row-number", "column_id": "row_number", "cell_text_raw": row_number},
        {"cell_id": f"{row_id}-requirement", "column_id": "requirement", "cell_text_raw": requirement},
    ]
    for column_id, value in values.items():
        cells.append({"cell_id": f"{row_id}-{column_id}", "column_id": column_id, "cell_text_raw": value})
    return {"row_id": row_id, "source_order": row_order, "cells_raw": cells}


def make_labeled_table_row(
    table_id_value: str,
    row_order: int,
    row_label: str,
    values: dict[str, str],
) -> dict[str, Any]:
    row_id = f"{table_id_value}-row-{row_order}"
    cells = [{"cell_id": f"{row_id}-row-label", "column_id": "row_label", "cell_text_raw": row_label}]
    for column_id, value in values.items():
        cells.append({"cell_id": f"{row_id}-{column_id}", "column_id": column_id, "cell_text_raw": value})
    return {"row_id": row_id, "source_order": row_order, "cells_raw": cells}


def table_rows_text(table: dict[str, Any]) -> list[str]:
    rows = []
    for row in table.get("rows_raw") or []:
        rows.append(clean_text(" ".join(cell.get("cell_text_raw") or "" for cell in row.get("cells_raw") or [])))
    return [row for row in rows if row]


def refresh_source_unit_text_from_raw(data: dict[str, Any]) -> None:
    raw_data = data.get("raw_data") or {}
    source_units = raw_data.get("source_units") or []
    if not source_units:
        return
    parts = []
    for raw_section in raw_data.get("sections_raw") or []:
        clauses_by_id = {clause.get("clause_id"): clause for clause in raw_section.get("clauses_raw") or []}
        tables_by_id = {table.get("table_id"): table for table in raw_section.get("tables_raw") or []}
        content_refs = sorted(raw_section.get("content_refs") or [], key=lambda item: item.get("source_order", 0))
        if content_refs:
            for ref in content_refs:
                if ref.get("content_type") == "clause":
                    clause = clauses_by_id.get(ref.get("content_id"))
                    if clause and clause.get("clause_text_raw"):
                        parts.append(clause["clause_text_raw"])
                elif ref.get("content_type") == "table":
                    table = tables_by_id.get(ref.get("content_id"))
                    if table:
                        parts.extend(table_rows_text(table))
            continue
        for clause in raw_section.get("clauses_raw") or []:
            if clause.get("clause_text_raw"):
                parts.append(clause["clause_text_raw"])
        for table in raw_section.get("tables_raw") or []:
            parts.extend(table_rows_text(table))
    source_units[0]["text_raw"] = "\n".join(parts)


def table_row_label_sort_key(label: str | None) -> tuple[int, int | str]:
    raw = clean_text(label).strip()
    match = re.fullmatch(r"\(([^)]+)\)", raw)
    token = match.group(1).lower() if match else raw.lower()
    if token.isdigit():
        return (0, int(token))
    if token.isalpha():
        value = 0
        for char in token:
            value = (value * 26) + (ord(char) - 96)
        return (1, value)
    return (2, token)


TABLE_ROW_VALUE_RE = re.compile(
    r"(?:^|\s)(N/A|min\.|max\.|no less than|no more than|at least|at most|greater than|less than|equal to|up to)(?=\s|$)",
    re.IGNORECASE,
)


def general_provisions_table_columns(labels: list[tuple[str, str]]) -> list[dict[str, Any]]:
    return [
        {"column_id": column_id, "column_label_raw": label, "source_order": index}
        for index, (column_id, label) in enumerate(labels, start=1)
    ]


def replace_section_table(section: dict[str, Any], table: dict[str, Any]) -> None:
    section["tables_raw"] = [
        existing for existing in section.get("tables_raw") or [] if existing.get("table_id") != table["table_id"]
    ]
    section["tables_raw"].append(table)
    section["tables_raw"].sort(key=lambda item: item.get("source_order", 0))


def remove_clause_id_range(section: dict[str, Any], clause_ids: set[str]) -> None:
    section["clauses_raw"] = [
        clause for clause in section.get("clauses_raw") or [] if clause.get("clause_id") not in clause_ids
    ]
    for index, clause in enumerate(section["clauses_raw"], start=1):
        clause["source_order"] = index


def find_raw_section(sections: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    return next((section for section in sections if section.get("section_label_raw") == label), None)


def resequence_clauses(section: dict[str, Any]) -> None:
    for index, clause in enumerate(section.get("clauses_raw") or [], start=1):
        clause["source_order"] = index


def reparent_clause(
    clause: dict[str, Any],
    new_section_label: str,
    parent_clause_id: str | None,
    parent_decimal: str | None = None,
) -> None:
    label = clean_text(clause.get("clause_label_raw"))
    token = clean_text(label).strip(".()")
    if label.startswith("."):
        suffix = token
    elif parent_decimal:
        suffix = f"{parent_decimal}-{token}"
    else:
        suffix = token
    clause["clause_id"] = f"doc-general-provisions-clause-{slugify(new_section_label)}-{slugify(suffix)}"
    clause["parent_clause_id"] = parent_clause_id


def merge_section_title_clause(section: dict[str, Any], suffix: str) -> bool:
    clauses = section.get("clauses_raw") or []
    if not clauses:
        return False
    first = clauses[0]
    if first.get("clause_label_raw") != "section":
        return False
    if clean_text(first.get("clause_text_raw")) != suffix:
        return False
    section["section_title_raw"] = clean_text(f"{section.get('section_title_raw', '')} {suffix}")
    section["clauses_raw"] = clauses[1:]
    resequence_clauses(section)
    return True


def repair_charlottetown_draft_general_provisions_tables(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    section_2_19 = find_raw_section(sections, "2.19")
    section_3_1 = find_raw_section(sections, "3.1")
    if section_2_19 and section_3_1:
        moved = []
        moved_ids = {
            "doc-general-provisions-clause-2-19-4-d",
            "doc-general-provisions-clause-2-19-4-e",
            "doc-general-provisions-clause-2-19-4-f",
            "doc-general-provisions-clause-2-19-4-g",
        }
        kept = []
        for clause in section_2_19.get("clauses_raw") or []:
            if clause.get("clause_id") in moved_ids:
                reparent_clause(clause, "3.1", "doc-general-provisions-clause-3-1-2", "2")
                moved.append(clause)
            else:
                kept.append(clause)
        if moved:
            section_2_19["clauses_raw"] = kept
            section_3_1["clauses_raw"].extend(moved)
            resequence_clauses(section_2_19)
            resequence_clauses(section_3_1)
            changed = True

        table_id_value = "doc-general-provisions-table-3-1-2-a"
        replace_section_table(
            section_3_1,
            {
                "table_id": table_id_value,
                "table_title_raw": "Table 3.1 Non-Habitable accessory buildings requirements per lot",
                "source_order": 7,
                "columns_raw": general_provisions_table_columns(
                    [
                        ("row_label", ""),
                        ("lot_area", "Lot Area"),
                        ("accessory_buildings_permitted", "# of Accessory Buildings permitted"),
                        ("total_building_footprint_maximum", "Total Building Footprint (max.)"),
                        ("height_maximum", "Height (max.)"),
                    ]
                ),
                "rows_raw": [
                    make_labeled_table_row(table_id_value, 1, "a", {"lot_area": "< 0.5 Acres", "accessory_buildings_permitted": "One", "total_building_footprint_maximum": "10% of the lot area", "height_maximum": "5.3 m (17.5 ft)"}),
                    make_labeled_table_row(table_id_value, 2, "b", {"lot_area": "> 0.5 to 0.99 Acres", "accessory_buildings_permitted": "Two", "total_building_footprint_maximum": "79 m2 combined", "height_maximum": "6.1 m (20 ft)"}),
                    make_labeled_table_row(table_id_value, 3, "c", {"lot_area": "> 1 Acre", "accessory_buildings_permitted": "Three", "total_building_footprint_maximum": "111.5 m2 combined; however, no individual accessory building shall exceed 79 m2", "height_maximum": "6.1 m (20 ft)"}),
                ],
                "citations": {"pdf_page_start": 21, "pdf_page_end": 21, "bylaw_page_start": 17, "bylaw_page_end": 17},
            },
        )
        changed = True

    section_3_2 = find_raw_section(sections, "3.2")
    if section_3_2:
        clause_3_2_1 = next((clause for clause in section_3_2.get("clauses_raw") or [] if clause.get("clause_id") == "doc-general-provisions-clause-3-2-1"), None)
        if clause_3_2_1:
            clause_3_2_1["clause_text_raw"] = "Projecting structures listed in Table 3.2 shall be permitted to project from a primary building into the required Yard for the distance specified."
        table_id_value = "doc-general-provisions-table-3-2-1"
        replace_section_table(
            section_3_2,
            {
                "table_id": table_id_value,
                "table_title_raw": "Table 3.2 Projecting Structures into yard setbacks",
                "source_order": 3,
                "columns_raw": general_provisions_table_columns(
                    [
                        ("row_label", ""),
                        ("structure", "Structure"),
                        ("yard_projection_permitted", "Yard in which projection is permitted"),
                        ("maximum_projection_into_yard", "Maximum projection into Yard"),
                        ("minimum_distance_from_lot_line", "Minimum distance from Lot Line"),
                    ]
                ),
                "rows_raw": [
                    make_labeled_table_row(table_id_value, 1, "a", {"structure": "Air Conditioning / Heat Pump units", "yard_projection_permitted": "All yards", "maximum_projection_into_yard": "1.5m", "minimum_distance_from_lot_line": "1 m"}),
                    make_labeled_table_row(table_id_value, 2, "b", {"structure": "Awning/Canopy", "yard_projection_permitted": "Front, Rear, Flankage", "maximum_projection_into_yard": "1.0 m (3.3 ft)", "minimum_distance_from_lot_line": "0.3 m (1 ft)"}),
                    make_labeled_table_row(table_id_value, 3, "c", {"structure": "Balcony", "yard_projection_permitted": "Front, flankage, rear", "maximum_projection_into_yard": "1.2 m (3.9 ft)", "minimum_distance_from_lot_line": "1 m (3.3 ft)"}),
                    make_labeled_table_row(table_id_value, 4, "d", {"structure": "Bay window", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "0.6 m (2.0 ft)", "minimum_distance_from_lot_line": "1 m (3.3 ft)"}),
                    make_labeled_table_row(table_id_value, 5, "e", {"structure": "Ramp", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "1.83 m (6 ft)", "minimum_distance_from_lot_line": "1 m (3.3 ft)"}),
                    make_labeled_table_row(table_id_value, 6, "f", {"structure": "Exterior staircase (landing and stairs connecting to the First Storey)", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "1.83m (6 ft)", "minimum_distance_from_lot_line": "6 m (19.7 ft) from the front lot line and flankage lot line; 1.2 m (3.9 ft) from the side or rear lot line"}),
                    make_labeled_table_row(table_id_value, 7, "g", {"structure": "Exterior staircase (fire escape and any stairs extending beyond the First Storey)", "yard_projection_permitted": "Side and rear", "maximum_projection_into_yard": "1.2 m (3.9 ft)", "minimum_distance_from_lot_line": "1.2 m (3.9 ft)"}),
                    make_labeled_table_row(table_id_value, 8, "h", {"structure": "Deck 0.3 m (1.0 ft) or more above Grade", "yard_projection_permitted": "Rear, side, Flankage", "maximum_projection_into_yard": "", "minimum_distance_from_lot_line": "Same as minimum Side Yard for the building, except in R-1L R-1S, R-1N, R-2 and R-2S Zones where the Setback is 4.6 m (15.1 ft) from the rear lot line"}),
                    make_labeled_table_row(table_id_value, 9, "i", {"structure": "Deck at Grade or less than 0.3 m (1.0 ft)", "yard_projection_permitted": "Rear, side, Flankage", "maximum_projection_into_yard": "", "minimum_distance_from_lot_line": "1 m (3.3 ft)"}),
                    make_labeled_table_row(table_id_value, 10, "j", {"structure": "Deck at Grade or less than 0.3 m (1.0 ft)", "yard_projection_permitted": "Front Yard", "maximum_projection_into_yard": "1.83m (6 ft)", "minimum_distance_from_lot_line": "2 m (6.6 ft)"}),
                    make_labeled_table_row(table_id_value, 11, "k", {"structure": "Porch", "yard_projection_permitted": "Front, rear, Flankage", "maximum_projection_into_yard": "1.5 m (4.9 ft)", "minimum_distance_from_lot_line": "1 m (3.3 ft)"}),
                ],
                "citations": {"pdf_page_start": 22, "pdf_page_end": 22, "bylaw_page_start": 18, "bylaw_page_end": 18},
            },
        )
        changed = True

    section_3_6 = find_raw_section(sections, "3.6")
    if section_3_6:
        clause_3_6_1 = next((clause for clause in section_3_6.get("clauses_raw") or [] if clause.get("clause_id") == "doc-general-provisions-clause-3-6-1"), None)
        if clause_3_6_1:
            clause_3_6_1["clause_text_raw"] = "The maximum Height of a building may be increased, to accommodate the following rooftop height exemptions as listed in Table 3.3."
        table_id_value = "doc-general-provisions-table-3-6-1"
        replace_section_table(
            section_3_6,
            {
                "table_id": table_id_value,
                "table_title_raw": "Table 3.3 Rooftop Height Exemptions",
                "source_order": 2,
                "columns_raw": general_provisions_table_columns(
                    [
                        ("row_label", ""),
                        ("feature", "Feature"),
                        ("maximum_height_above_maximum_roof", "Column 1: Maximum height above maximum roof"),
                        ("roof_coverage_restriction", "Column 2: 30% roof coverage restriction"),
                        ("minimum_setback_from_roof_edge", "Column 3: Minimum setback from roof edge facing front flanking lot lines"),
                    ]
                ),
                "rows_raw": [
                    make_labeled_table_row(table_id_value, 1, "a", {"feature": "Antenna", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 2, "b", {"feature": "Chimney", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 3, "c", {"feature": "Clear glass guard and railing system", "maximum_height_above_maximum_roof": "2 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 4, "d", {"feature": "Clock tower or bell tower", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 5, "e", {"feature": "Communication tower required to support uses and activities in the building", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 6, "f", {"feature": "Cooling Tower", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 7, "g", {"feature": "Elevator enclosure", "maximum_height_above_maximum_roof": "6.0 m", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 8, "h", {"feature": "Flag pole", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 9, "i", {"feature": "Heating, ventilation, and air conditioning equipment and enclosure", "maximum_height_above_maximum_roof": "5.5 m", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 10, "j", {"feature": "Helipad on a hospital roof", "maximum_height_above_maximum_roof": "4.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 11, "k", {"feature": "High-plume laboratory exhaust fan", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 12, "l", {"feature": "Hard landscaping or soft landscaping", "maximum_height_above_maximum_roof": "4.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 13, "m", {"feature": "Lighting Rod", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 14, "n", {"feature": "Mechanical Penthouse", "maximum_height_above_maximum_roof": "5.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 15, "o", {"feature": "Parapet", "maximum_height_above_maximum_roof": "2 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 16, "p", {"feature": "Rooftop Cupola", "maximum_height_above_maximum_roof": "4.5 m", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 17, "q", {"feature": "Rooftop Greenhouse", "maximum_height_above_maximum_roof": "6.0 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 18, "r", {"feature": "Skylight", "maximum_height_above_maximum_roof": "1.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 19, "s", {"feature": "Solar collector", "maximum_height_above_maximum_roof": "4.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 20, "t", {"feature": "Spire, steeple, minaret, and similar features", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 21, "u", {"feature": "Staircase or staircase enclosure", "maximum_height_above_maximum_roof": "4.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": "3 m"}),
                    make_labeled_table_row(table_id_value, 22, "v", {"feature": "Windscreen", "maximum_height_above_maximum_roof": "4.5 m", "roof_coverage_restriction": "", "minimum_setback_from_roof_edge": ""}),
                    make_labeled_table_row(table_id_value, 23, "w", {"feature": "Window cleaning Platform", "maximum_height_above_maximum_roof": "Unlimited", "roof_coverage_restriction": "YES", "minimum_setback_from_roof_edge": ""}),
                ],
                "citations": {"pdf_page_start": 25, "pdf_page_end": 25, "bylaw_page_start": 21, "bylaw_page_end": 21},
            },
        )
        changed = True

    section_3_16 = find_raw_section(sections, "3.16")
    section_3_19 = find_raw_section(sections, "3.19")
    if section_3_16 and section_3_19:
        tail = "pump-out facility that is permanently connected to the municipal sewer system that is available for use at all times, and complies with all applicable Federal and Provincial Environmental Protection Acts and Regulations."
        moved_2_clauses: list[dict[str, Any]] = []
        kept_3_16 = []
        for clause in section_3_16.get("clauses_raw") or []:
            if clause.get("clause_id") == "doc-general-provisions-clause-3-16-4":
                clause["clause_text_raw"] = clean_text((clause.get("clause_text_raw") or "").replace(tail, ""))
                kept_3_16.append(clause)
            elif clause.get("clause_id") in {f"doc-general-provisions-clause-3-16-4-{label}" for label in "defgh"}:
                reparent_clause(clause, "3.19", "doc-general-provisions-clause-3-19-2", "2")
                moved_2_clauses.append(clause)
            else:
                kept_3_16.append(clause)
        section_3_16["clauses_raw"] = kept_3_16
        for clause in section_3_19.get("clauses_raw") or []:
            if clause.get("clause_id") == "doc-general-provisions-clause-3-19-2-c":
                clause["clause_text_raw"] = "Floating structures must be permanently connected to the municipal sewer system by means of a marina sewage collection system, or are moored at a marina that has a sewage " + tail
            elif clause.get("clause_id") in {f"doc-general-provisions-clause-3-19-2-{label}" for label in "defg"}:
                reparent_clause(clause, "3.19", "doc-general-provisions-clause-3-19-3", "3")
        if moved_2_clauses:
            clauses = section_3_19.get("clauses_raw") or []
            insert_at = next((index + 1 for index, clause in enumerate(clauses) if clause.get("clause_id") == "doc-general-provisions-clause-3-19-2-c"), 6)
            section_3_19["clauses_raw"] = clauses[:insert_at] + moved_2_clauses + clauses[insert_at:]
        ordered_prefix = [
            "doc-general-provisions-clause-3-19",
            "doc-general-provisions-clause-3-19-1",
            "doc-general-provisions-clause-3-19-2",
            *[f"doc-general-provisions-clause-3-19-2-{label}" for label in "abcdefghi"],
            "doc-general-provisions-clause-3-19-3",
            *[f"doc-general-provisions-clause-3-19-3-{label}" for label in "abcdefg"],
            "doc-general-provisions-clause-3-19-4",
        ]
        order_lookup = {clause_id_value: index for index, clause_id_value in enumerate(ordered_prefix)}
        section_3_19["clauses_raw"].sort(
            key=lambda clause: (order_lookup.get(clause.get("clause_id"), len(order_lookup)), clause.get("source_order", 0))
        )
        resequence_clauses(section_3_16)
        resequence_clauses(section_3_19)
        changed = True

    section_4_5 = find_raw_section(sections, "4.5")
    if section_4_5 and not find_raw_section(sections, "4.6"):
        section_4_5["clauses_raw"][3]["clause_text_raw"] = section_4_5["clauses_raw"][3]["clause_text_raw"].replace(" 4.6 ACCESSORY DWELLING UNITS, ATTACHED", "")
        moved = section_4_5["clauses_raw"][4:]
        section_4_5["clauses_raw"] = section_4_5["clauses_raw"][:4]
        last_decimal: str | None = None
        for clause in moved:
            label = clean_text(clause.get("clause_label_raw"))
            if label.startswith("."):
                last_decimal = label.strip(".")
                reparent_clause(clause, "4.6", None)
            else:
                reparent_clause(clause, "4.6", f"doc-general-provisions-clause-4-6-{last_decimal}", last_decimal)
        new_section = {
            **section_4_5,
            "section_id": "doc-general-provisions-section-4-6",
            "section_label_raw": "4.6",
            "section_title_raw": "ACCESSORY DWELLING UNITS, ATTACHED",
            "source_order": section_4_5.get("source_order", 5) + 1,
            "clauses_raw": moved,
            "tables_raw": [],
        }
        insert_at = sections.index(section_4_5) + 1
        sections.insert(insert_at, new_section)
        for index, section in enumerate(sections, start=1):
            section["source_order"] = index
        resequence_clauses(section_4_5)
        resequence_clauses(new_section)
        changed = True

    section_4_7 = find_raw_section(sections, "4.7")
    if section_4_7:
        if merge_section_title_clause(section_4_7, "(DETACHED)"):
            changed = True
        table_id_value = "doc-general-provisions-table-4-7-3-a"
        replace_section_table(
            section_4_7,
            {
                "table_id": table_id_value,
                "table_title_raw": "Table 4.1 Detached ADU Requirements",
                "source_order": 15,
                "columns_raw": general_provisions_table_columns([("row_label", ""), ("requirement", "Requirement"), ("condition", "Condition")]),
                "rows_raw": [
                    make_labeled_table_row(table_id_value, 1, "a", {"requirement": "Rear Setback", "condition": "min. 1.5 m"}),
                    make_labeled_table_row(table_id_value, 2, "b", {"requirement": "Side Setback", "condition": "min. 1.5 m"}),
                    make_labeled_table_row(table_id_value, 3, "c", {"requirement": "Floor Area", "condition": "max. 80 m2"}),
                    make_labeled_table_row(table_id_value, 4, "d", {"requirement": "Height", "condition": "max. 7 m"}),
                    make_labeled_table_row(table_id_value, 5, "e", {"requirement": "Distance between Buildings", "condition": "min. 2 m"}),
                ],
                "citations": {"pdf_page_start": 34, "pdf_page_end": 34, "bylaw_page_start": 30, "bylaw_page_end": 30},
            },
        )
        changed = True

    section_4_11 = find_raw_section(sections, "4.11")
    if section_4_11:
        table_id_value = "doc-general-provisions-table-4-11-1-c"
        replace_section_table(
            section_4_11,
            {
                "table_id": table_id_value,
                "table_title_raw": "Table 4.2 Regulations for Tourist Accommodations",
                "source_order": 5,
                "columns_raw": general_provisions_table_columns(
                    [("row_label", ""), ("zone_designation", "Zone Designation"), ("bedrooms_permitted", "# of Bedrooms Permitted")]
                ),
                "rows_raw": [
                    make_labeled_table_row(table_id_value, 1, "a", {"zone_designation": "RN, RM, and HR Zones", "bedrooms_permitted": "Up to four (4) bedrooms"}),
                    make_labeled_table_row(table_id_value, 2, "b", {"zone_designation": "GC, GN, DC, DN, DMU, and DW Zones", "bedrooms_permitted": "Four (4) bedrooms are permitted for the first 370 m2 (3,982.8 ft2) of lot area, and for every additional bedroom over four (4) the lot must be increased by 100 m2 (1076.4 ft2), up to a maximum of 7 bedrooms."}),
                ],
                "citations": {"pdf_page_start": 37, "pdf_page_end": 37, "bylaw_page_start": 33, "bylaw_page_end": 33},
            },
        )
        changed = True

    for label, suffix in {
        "3.1": "BUILDINGS",
        "4.6": "ATTACHED",
        "4.14": "GAS BARS",
        "4.16": "ZONES",
        "4.17": "A SEWAGE LAGOON OR TREATMENT PLANT",
        "5.4": "MANAGEMENT",
        "5.6": "CONFEDERATION TRAIL",
        "5.8": "WATERCOURSES AND WETLANDS",
        "7.3": "OF LOTS",
        "7.4": "SUBDIVISION",
        "7.8": "SUBDIVISION",
        "7.10": "SERVICES:",
        "7.12": "CONVEYANCE OF PUBLIC SERVICES",
        "7.13": "REQUIREMENTS",
    }.items():
        section = find_raw_section(sections, label)
        if section and merge_section_title_clause(section, suffix):
            changed = True

    section_6_3 = find_raw_section(sections, "6.3")
    if section_6_3 and section_6_3.get("section_title_raw") == "NEIGHBOURING HERITAGE":
        clauses = section_6_3.get("clauses_raw") or []
        if clauses and str(clauses[0].get("clause_text_raw") or "").startswith("RESOURCES "):
            clauses[0]["clause_text_raw"] = clean_text(clauses[0]["clause_text_raw"].removeprefix("RESOURCES "))
            section_6_3["section_title_raw"] = "NEIGHBOURING HERITAGE RESOURCES"
            changed = True

    section_7_3 = find_raw_section(sections, "7.3")
    if section_7_3:
        order = {"doc-general-provisions-clause-7-3-2": 0, **{f"doc-general-provisions-clause-7-3-2-{label}": i for i, label in enumerate("abcdefghi", start=1)}}
        section_7_3["clauses_raw"].sort(key=lambda clause: (order.get(clause.get("clause_id"), -1), clause.get("source_order", 0)))
        resequence_clauses(section_7_3)
        changed = True

    section_7_4 = find_raw_section(sections, "7.4")
    section_7_5 = find_raw_section(sections, "7.5")
    if section_7_4 and section_7_5:
        moved = []
        kept = []
        for clause in section_7_4.get("clauses_raw") or []:
            if clause.get("clause_id") in {f"doc-general-provisions-clause-7-4-2-c-{roman}" for roman in ["iv", "v", "vi", "vii", "viii", "ix"]}:
                clause["clause_id"] = clause["clause_id"].replace("clause-7-4-2-c", "clause-7-5-1-e")
                clause["parent_clause_id"] = "doc-general-provisions-clause-7-5-1-e"
                moved.append(clause)
            else:
                kept.append(clause)
        if moved:
            section_7_4["clauses_raw"] = kept
            insert_at = next((index + 1 for index, clause in enumerate(section_7_5.get("clauses_raw") or []) if clause.get("clause_id") == "doc-general-provisions-clause-7-5-1-e-iii"), 8)
            section_7_5["clauses_raw"] = section_7_5["clauses_raw"][:insert_at] + moved + section_7_5["clauses_raw"][insert_at:]
            resequence_clauses(section_7_4)
            resequence_clauses(section_7_5)
            changed = True

    section_7_9 = find_raw_section(sections, "7.9")
    if section_7_9 and not find_raw_section(sections, "7.10"):
        clauses_7_9: list[dict[str, Any]] = []
        clauses_7_10: list[dict[str, Any]] = []
        clauses_7_11: list[dict[str, Any]] = []
        segment = "7.9"
        for clause in section_7_9.get("clauses_raw") or []:
            text = clause.get("clause_text_raw") or ""
            if "7.10 WATER, SEWER, AND OTHER SERVICES:" in text or "7.10  WATER, SEWER, AND OTHER SERVICES:" in text:
                clause["clause_text_raw"] = clean_text(re.split(r"7\.10\s+WATER, SEWER, AND OTHER SERVICES:", text, maxsplit=1)[0])
                clauses_7_9.append(clause)
                segment = "7.10"
                continue
            if segment == "7.10" and clause.get("clause_label_raw") == ".1" and clauses_7_10:
                segment = "7.11"
            if "7.11  LAND FOR PUBLIC PURPOSES (LPP)" in text:
                clause["clause_text_raw"] = clean_text(text.split("7.11  LAND FOR PUBLIC PURPOSES (LPP)", 1)[0])
                segment = "7.11"
            if segment == "7.10":
                reparent_clause(clause, "7.10", None)
                clauses_7_10.append(clause)
            elif segment == "7.11":
                label = clean_text(clause.get("clause_label_raw"))
                parent = "doc-general-provisions-clause-7-11-1" if label.startswith("(") else None
                parent_decimal = "1" if label.startswith("(") else None
                reparent_clause(clause, "7.11", parent, parent_decimal)
                clauses_7_11.append(clause)
            else:
                clauses_7_9.append(clause)
        if clauses_7_10 or clauses_7_11:
            section_7_9["clauses_raw"] = clauses_7_9
            new_sections = []
            if clauses_7_10:
                new_7_10 = {**section_7_9, "section_id": "doc-general-provisions-section-7-10", "section_label_raw": "7.10", "section_title_raw": "WATER, SEWER, AND OTHER SERVICES", "clauses_raw": clauses_7_10, "tables_raw": []}
                resequence_clauses(new_7_10)
                new_sections.append(new_7_10)
            if clauses_7_11:
                new_7_11 = {**section_7_9, "section_id": "doc-general-provisions-section-7-11", "section_label_raw": "7.11", "section_title_raw": "LAND FOR PUBLIC PURPOSES (LPP)", "clauses_raw": clauses_7_11, "tables_raw": []}
                resequence_clauses(new_7_11)
                new_sections.append(new_7_11)
            insert_at = sections.index(section_7_9) + 1
            sections[insert_at:insert_at] = new_sections
            for index, section in enumerate(sections, start=1):
                section["source_order"] = index
            resequence_clauses(section_7_9)
            changed = True

    section_5_2 = find_raw_section(sections, "5.2")
    if section_5_2:
        clause_5_2_2 = next((clause for clause in section_5_2.get("clauses_raw") or [] if clause.get("clause_id") == "doc-general-provisions-clause-5-2-2"), None)
        if clause_5_2_2 and " a) " in clause_5_2_2.get("clause_text_raw", ""):
            clause_5_2_2["clause_text_raw"] = "In all other zones nothing in this bylaw shall prevent the use of an undersized lot with respect to minimum lot area or frontage provided that:"
            cite = clause_5_2_2.get("citations")
            section_5_2["clauses_raw"].extend(
                [
                    {"clause_id": "doc-general-provisions-clause-5-2-2-a", "clause_label_raw": "(a)", "clause_text_raw": "The use of such lot is permitted in the zone in which such lot is located;", "parent_clause_id": "doc-general-provisions-clause-5-2-2", "source_order": 3, "citations": cite},
                    {"clause_id": "doc-general-provisions-clause-5-2-2-b", "clause_label_raw": "(b)", "clause_text_raw": "All other standards of the zone are maintained.", "parent_clause_id": "doc-general-provisions-clause-5-2-2", "source_order": 4, "citations": cite},
                ]
            )
            resequence_clauses(section_5_2)
            changed = True

    if changed:
        raw_data["tables_raw"] = [
            {"table_id": table["table_id"], "section_id": section["section_id"]}
            for section in sections
            for table in section.get("tables_raw") or []
        ]
        rebuild_clause_refs(data)
        refresh_source_unit_text_from_raw(data)
    return changed


def repair_charlottetown_draft_parking_sections(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    section_8_3 = find_raw_section(sections, "8.3")
    section_8_4 = find_raw_section(sections, "8.4")
    if section_8_3 and section_8_4:
        moved = []
        kept = []
        for clause in section_8_3.get("clauses_raw") or []:
            if clause.get("clause_id") in {
                "doc-general-provisions-clause-8-3-4",
                "doc-general-provisions-clause-8-3-5",
            }:
                new_label = clause["clause_id"].rsplit("-", 1)[-1]
                clause["clause_id"] = f"doc-general-provisions-clause-8-4-{new_label}"
                moved.append(clause)
            else:
                kept.append(clause)
        if moved:
            section_8_3["clauses_raw"] = kept
            section_8_4["clauses_raw"].extend(moved)
            section_8_4["clauses_raw"].sort(key=lambda clause: int(clean_text(clause.get("clause_label_raw", "")).strip(".") or 0))
            resequence_clauses(section_8_3)
            resequence_clauses(section_8_4)
            changed = True

    section_8_4 = find_raw_section(sections, "8.4")
    if section_8_4:
        for clause in section_8_4.get("clauses_raw") or []:
            if clause.get("clause_id") == "doc-general-provisions-clause-8-4-5":
                text = clause.get("clause_text_raw") or ""
                clause["clause_text_raw"] = clean_text(text.split(" Clubs, Educational Facilities", 1)[0])
                changed = True

    section_8_5 = find_raw_section(sections, "8.5")
    if section_8_5:
        section_8_5["clauses_raw"] = [
            clause for clause in section_8_5.get("clauses_raw") or [] if clause.get("clause_label_raw") != "section"
        ]
        for clause in section_8_5.get("clauses_raw") or []:
            if clause.get("clause_id") == "doc-general-provisions-clause-8-5-2-f":
                clause["clause_text_raw"] = (
                    "A land use buffer, satisfactory to the Development Officer, consisting of a 1 m wide landscape "
                    "treatment, a fence and/or mature trees (spaced no more than 6.1 m apart), or both, shall be "
                    "provided where a parking lot abuts a residential zone or a building occupied for residential use "
                    "in a commercial zone;"
                )
                changed = True
        resequence_clauses(section_8_5)

    section_8_7 = find_raw_section(sections, "8.7")
    if section_8_7:
        merge_section_title_clause(section_8_7, "STANDARDS")
        for clause in section_8_7.get("clauses_raw") or []:
            if clause.get("clause_id") == "doc-general-provisions-clause-8-7-1-c":
                clause["clause_text_raw"] = "An accessible curb cut or mountable curb where curbs are present"
                changed = True

    section_8_8 = find_raw_section(sections, "8.8")
    if section_8_8:
        for clause in section_8_8.get("clauses_raw") or []:
            if clause.get("clause_id") == "doc-general-provisions-clause-8-8-2":
                clause["clause_text_raw"] = (
                    "For all semi detached and duplex homes, no more than 50% of the area of the front or flankage "
                    "yard shall be dedicated to driveways or parking;"
                )
                changed = True
            elif clause.get("clause_id") == "doc-general-provisions-clause-8-8-6":
                clause["clause_text_raw"] = (
                    "Porte cochere's or driveway drop-offs for multi-unit dwellings entries are permitted between "
                    "the building and the street with 2 temporary parking stalls."
                )
                changed = True

    section_8_12 = find_raw_section(sections, "8.12")
    if section_8_12 and not find_raw_section(sections, "8.13"):
        clauses_8_12 = []
        clauses_8_13 = []
        clauses_8_14 = []
        segment = "8.12"
        for clause in section_8_12.get("clauses_raw") or []:
            clause_id = clause.get("clause_id")
            text = clause.get("clause_text_raw") or ""
            if clause_id == "doc-general-provisions-clause-8-12-3-b":
                clause["clause_text_raw"] = "At least 0.9 m apart for other types of rack."
                clauses_8_12.append(clause)
                segment = "8.13"
                continue
            if clause_id == "doc-general-provisions-clause-8-12-3":
                clause["clause_text_raw"] = (
                    "Parking stalls shall be no less than 0.6 m (2 ft) long and 1.2 m (3.9 ft) high, "
                    "and have an associated aisle of 1.5 m in width."
                )
                reparent_clause(clause, "8.13", None)
                clauses_8_13.append(clause)
                segment = "8.14"
                continue
            if clause_id == "doc-general-provisions-clause-8-12-1-a":
                clause["clause_text_raw"] = (
                    "Be located outside of a building in a location that is visible and accessible from the street, "
                    "within 20 m of a main door;"
                )
                reparent_clause(clause, "8.14", "doc-general-provisions-clause-8-14-1", "1")
                clauses_8_14.append(clause)
                continue
            if clause_id == "doc-general-provisions-clause-8-12-1-c":
                reparent_clause(clause, "8.14", "doc-general-provisions-clause-8-14-1", "1")
                clauses_8_14.append(clause)
                continue
            if clause_id == "doc-general-provisions-clause-8-12-1":
                clause["clause_text_raw"] = "Class B bicycle parking shall:"
                reparent_clause(clause, "8.14", None)
                clauses_8_14.append(clause)
                segment = "8.14"
                continue
            if clause_id == "doc-general-provisions-clause-8-12-1-d":
                clause["clause_text_raw"] = "Within a covered parking garage area reserved for bicycles; or"
            if segment == "8.13":
                if clause.get("clause_label_raw") in {"(b)", "(c)"} and clause_id in {
                    "doc-general-provisions-clause-8-12-1-b",
                    "doc-general-provisions-clause-8-12-1-c",
                }:
                    reparent_clause(clause, "8.14", "doc-general-provisions-clause-8-14-1", "1")
                    clauses_8_14.append(clause)
                    segment = "8.14"
                else:
                    reparent_clause(clause, "8.13", None if clause.get("clause_label_raw", "").startswith(".") else "doc-general-provisions-clause-8-13-1", "1")
                    clauses_8_13.append(clause)
            elif segment == "8.14":
                reparent_clause(clause, "8.14", None if clause.get("clause_label_raw", "").startswith(".") else "doc-general-provisions-clause-8-14-1", "1")
                clauses_8_14.append(clause)
            else:
                clauses_8_12.append(clause)
        if clauses_8_13 or clauses_8_14:
            section_8_12["clauses_raw"] = clauses_8_12
            new_sections = []
            if clauses_8_13:
                new_8_13 = {**section_8_12, "section_id": "doc-general-provisions-section-8-13", "section_label_raw": "8.13", "section_title_raw": "BICYCLE PARKING (CLASS A)", "clauses_raw": clauses_8_13, "tables_raw": []}
                resequence_clauses(new_8_13)
                new_sections.append(new_8_13)
            if clauses_8_14:
                new_8_14 = {**section_8_12, "section_id": "doc-general-provisions-section-8-14", "section_label_raw": "8.14", "section_title_raw": "BICYCLE PARKING (CLASS B)", "clauses_raw": clauses_8_14, "tables_raw": []}
                resequence_clauses(new_8_14)
                new_sections.append(new_8_14)
            insert_at = sections.index(section_8_12) + 1
            sections[insert_at:insert_at] = new_sections
            for index, section in enumerate(sections, start=1):
                section["source_order"] = index
            resequence_clauses(section_8_12)
            changed = True

    section_8_12 = find_raw_section(sections, "8.12")
    if section_8_12:
        cite = (section_8_12.get("clauses_raw") or [{}])[0].get("citations") or section_8_12.get("citations")

        def parking_clause(section_label: str, suffix: str, label: str, text: str, parent: str | None = None) -> dict[str, Any]:
            return {
                "clause_id": f"doc-general-provisions-clause-{slugify(section_label)}-{slugify(suffix)}",
                "clause_label_raw": label,
                "clause_text_raw": text,
                "parent_clause_id": parent,
                "source_order": 0,
                "citations": cite,
            }

        section_8_12["clauses_raw"] = [
            parking_clause("8.12", "1", ".1", "The minimum required bicycle parking spaces shall be provided in accordance with the bicycle parking requirements in Table 8.5. Decimal results shall be rounded up."),
            parking_clause("8.12", "2", ".2", "Notwithstanding the ratios required for class A and B bike parking, class A bike parking can be provided at a higher than the recommended percentage to meet the bike parking requirements up to 100%."),
            parking_clause("8.12", "3", ".3", "Bicycle parking racks shall be required to be spaced"),
            parking_clause("8.12", "3-a", "(a)", "At least 0.45 m apart for a vertical rack or two-tier rack with a lift assist, or", "doc-general-provisions-clause-8-12-3"),
            parking_clause("8.12", "3-b", "(b)", "At least 0.9 m apart for other types of rack.", "doc-general-provisions-clause-8-12-3"),
        ]
        section_8_13 = {
            **section_8_12,
            "section_id": "doc-general-provisions-section-8-13",
            "section_label_raw": "8.13",
            "section_title_raw": "BICYCLE PARKING (CLASS A)",
            "clauses_raw": [
                parking_clause("8.13", "1", ".1", "Class A bicycle parking shall be located:"),
                parking_clause("8.13", "1-a", "(a)", "Within a room that is dedicated to the storage of bicycles;", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-b", "(b)", "Within a roofed bicycle cage outside of a building;", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-c", "(c)", "Within an enclosed bicycle locker outside of a building;", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-d", "(d)", "Within a covered parking garage area reserved for bicycles; or", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-e", "(e)", "Within a resident storage unit located in an indoor parking area that is associated with a multi-unit dwelling use.", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-f", "(f)", "On the ground floor of the building; or", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-g", "(g)", "Within one storey of a ground floor and be:", "doc-general-provisions-clause-8-13-1"),
                parking_clause("8.13", "1-g-i", "i)", "Accessible from a ground floor with ramps, which are protected from motor vehicle traffic, or", "doc-general-provisions-clause-8-13-1-g"),
                parking_clause("8.13", "1-g-ii", "ii)", "Accessible from a ground floor by elevator.", "doc-general-provisions-clause-8-13-1-g"),
                parking_clause("8.13", "2", ".2", "Any Class A bicycle storage shall be secured against unauthorized entry."),
                parking_clause("8.13", "3", ".3", "Parking stalls shall be no less than 0.6 m (2 ft) long and 1.2 m (3.9 ft) high, and have an associated aisle of 1.5 m in width."),
            ],
            "tables_raw": [],
        }
        section_8_14 = {
            **section_8_12,
            "section_id": "doc-general-provisions-section-8-14",
            "section_label_raw": "8.14",
            "section_title_raw": "BICYCLE PARKING (CLASS B)",
            "clauses_raw": [
                parking_clause("8.14", "1", ".1", "Class B bicycle parking shall:"),
                parking_clause("8.14", "1-a", "(a)", "Be located outside of a building in a location that is visible and accessible from the street, within 20 m of a main door;", "doc-general-provisions-clause-8-14-1"),
                parking_clause("8.14", "1-b", "(b)", "Be surfaced with a hard material such as asphalt, concrete, or unit pavers;", "doc-general-provisions-clause-8-14-1"),
                parking_clause("8.14", "1-c", "(c)", "Include galvanized, powder coated or stainless steel racks spaced 0.90 m width apart with a clear bike parking length of 1.8 m.", "doc-general-provisions-clause-8-14-1"),
            ],
            "tables_raw": [],
        }
        sections[:] = [section for section in sections if section.get("section_label_raw") not in {"8.13", "8.14"}]
        insert_at = sections.index(section_8_12) + 1
        sections[insert_at:insert_at] = [section_8_13, section_8_14]
        for index, section in enumerate(sections, start=1):
            section["source_order"] = index
            resequence_clauses(section)
        changed = True

    if changed:
        raw_data["tables_raw"] = [
            {"table_id": table["table_id"], "section_id": section["section_id"]}
            for section in sections
            for table in section.get("tables_raw") or []
        ]
        rebuild_clause_refs(data)
        refresh_source_unit_text_from_raw(data)
    return changed


def repair_charlottetown_draft_signage_sections(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    if metadata.get("document_type") != "general_provisions":
        return False

    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    section_9_10 = find_raw_section(sections, "9.10")
    section_9_11 = find_raw_section(sections, "9.11")
    section_9_12 = find_raw_section(sections, "9.12")
    if not (section_9_10 and section_9_11 and section_9_12):
        return False

    awning_general = (
        "Signs shall be affixed to, or painted on an Awning / Canopy that is securely attached to a building wall "
        "that abuts a street; Signs shall be attached to an Awning / Canopy that may extends a maximum of 1 m "
        "(3.3 ft) over a sidewalk or public Right-of-way; Signs shall be attached to an Awning / Canopy that is "
        "located below the bottom of the second Storey windows; Signs shall be attached to an Awning / Canopy that "
        "provides a minimum clearance of 2.2 m (7.2 ft) over a sidewalk and 3 m (9.8 ft) over a Parking Space or "
        "traffic lane; The owner of a Sign that extends over a public Right-of-way shall: • Carry liability "
        "insurance that names the City as a third party and provides a minimum coverage of $1,000,000; and • Enter "
        "into an encroachment agreement with the City to Permit said Sign; and • Signs erected in the 500 Lot Area "
        "or on a Heritage Resource shall adhere to the Sign design criteria."
    )
    projecting_general = (
        "Signs shall have a maximum of two parallel Sign Faces; Signs shall be erected on a building wall that abuts "
        "a street or the Business Premise's interior parking lot; Signs shall have a minimum clearance of 2.2 m "
        "(7.2 ft) from the ground; Signs and their supporting structures shall extend a maximum of 1.1 m (3.6 ft) "
        "from the building wall. No Sign shall extend over a side property line or the roof of a building; "
        "Supporting structures shall be designed in proportion to the size of the Sign; The owner of a Sign that "
        "extends over a public Right-of-way shall carry liability insurance that names the City as a third party and "
        "provides a minimum coverage of $1,000,000; and Enter into an encroachment agreement with the City."
    )

    def signage_clause(section: dict[str, Any], label: str, text: str) -> dict[str, Any]:
        section_label = section["section_label_raw"]
        suffix = clean_text(label).strip(".") or "section"
        cid = (
            f"doc-general-provisions-clause-{slugify(section_label)}"
            if label == "section"
            else f"doc-general-provisions-clause-{slugify(section_label)}-{slugify(suffix)}"
        )
        return {
            "clause_id": cid,
            "clause_label_raw": label,
            "clause_text_raw": text,
            "parent_clause_id": None,
            "source_order": 1,
            "citations": citation(section.get("citations")),
        }

    def signage_table(section: dict[str, Any], table_number: str, title: str, rows: list[tuple[str, str, str]]) -> dict[str, Any]:
        table = {
            "table_id": f"doc-general-provisions-table-{slugify(table_number)}",
            "table_title_raw": title,
            "source_order": 1,
            "columns_raw": general_provisions_table_columns(
                [
                    ("zone", "Zone"),
                    ("dimensions", "Dimensions"),
                    ("general_provisions", "General Provisions"),
                ]
            ),
            "rows_raw": [],
            "citations": citation(section.get("citations")),
        }
        for row_order, (zone, dimensions, general_provisions) in enumerate(rows, start=1):
            table["rows_raw"].append(
                {
                    "row_id": f"{table['table_id']}-row-{row_order}",
                    "source_order": row_order,
                    "cells_raw": [
                        {"cell_id": f"{table['table_id']}-row-{row_order}-zone", "column_id": "zone", "cell_text_raw": zone},
                        {
                            "cell_id": f"{table['table_id']}-row-{row_order}-dimensions",
                            "column_id": "dimensions",
                            "cell_text_raw": dimensions,
                        },
                        {
                            "cell_id": f"{table['table_id']}-row-{row_order}-general-provisions",
                            "column_id": "general_provisions",
                            "cell_text_raw": general_provisions,
                        },
                    ],
                }
            )
        return table

    section_9_10["clauses_raw"] = [
        signage_clause(
            section_9_10,
            ".1",
            "If the Development Agreement specifically notes any signage requirements that do not meet the "
            "requirements of this bylaw, the DA shall supersede this bylaw; otherwise these signage requirements "
            "shall be met.",
        )
    ]
    section_9_10["tables_raw"] = []

    section_9_11["clauses_raw"] = [
        signage_clause(
            section_9_11,
            ".1",
            "Awning / Canopy Signs shall adhere to the following provisions in Table 9.1:",
        )
    ]
    section_9_11["tables_raw"] = [
        signage_table(
            section_9_11,
            "9.1",
            "Table 9.1 Awning/Canopy Table",
            [
                (
                    "500 Lot Area (Excluding DN Zone)",
                    "Sign Area shall not exceed 40% of the Awning / Canopy upon which it is attached.",
                    awning_general,
                ),
                (
                    "Any other Mixed Use Residential/ Commercial, Institutional, Open Space or Employment/ Industrial Zone",
                    "Sign Area shall not exceed 60% of the Awning / Canopy upon which it is attached.",
                    awning_general,
                ),
            ],
        )
    ]

    section_9_12["clauses_raw"] = [
        signage_clause(
            section_9_12,
            ".1",
            "Projecting signs shall adhere to the following provisions in Table 9.2:",
        )
    ]
    section_9_12["tables_raw"] = [
        signage_table(
            section_9_12,
            "9.2",
            "Table 9.2 Projecting Sign Table",
            [
                ("500 Lot Area (Excluding DN Zone)", "Sign Area shall not exceed 1 m2 (10.8 ft2) per Sign Face.", projecting_general),
                (
                    "Any other Mixed Use Residential/ Commercial, Institutional, Open Space or Employment/ Industrial Zone",
                    "Sign Area shall not exceed 2 m2 (21.5 ft2) per Sign Face.",
                    projecting_general,
                ),
                (
                    "Designated heritage resource",
                    "When erected on a designated heritage resource, Sign Area shall not exceed 1 m2 (10.8 ft2) per sign face.",
                    projecting_general,
                ),
            ],
        )
    ]

    raw_data["tables_raw"] = [
        {"table_id": table["table_id"], "section_id": section["section_id"]}
        for section in sections
        for table in section.get("tables_raw") or []
    ]
    for section in (section_9_10, section_9_11, section_9_12):
        rebuild_content_refs({"raw_data": {"sections_raw": [section]}})
    rebuild_clause_refs(data)
    refresh_source_unit_text_from_raw(data)
    return True


DRAFT_GENERAL_PROVISIONS_REVIEWED_REQUIREMENT_CLAUSES = {
    "doc-design-standards-clause-6-8-3",
    "doc-design-standards-clause-6-8-8",
    "doc-design-standards-clause-6-8-8-a",
    "doc-design-standards-clause-6-8-8-b",
    "doc-design-standards-clause-6-8-8-d",
    "doc-general-provisions-clause-3-4-2-b",
    "doc-general-provisions-clause-3-4-2-c",
    "doc-general-provisions-clause-3-9-1-a",
    "doc-general-provisions-clause-3-13-1",
    "doc-general-provisions-clause-4-6-3-d",
    "doc-general-provisions-clause-4-6-5",
    "doc-general-provisions-clause-4-7-2-d",
    "doc-general-provisions-clause-4-13-2-b",
    "doc-general-provisions-clause-4-17-1",
    "doc-general-provisions-clause-4-18-2",
    "doc-general-provisions-clause-4-18-3",
    "doc-general-provisions-clause-5-4-3-a",
    "doc-general-provisions-clause-5-4-3-b",
    "doc-general-provisions-clause-5-5-1",
    "doc-general-provisions-clause-8-4-4",
    "doc-general-provisions-clause-8-4-5",
    "doc-general-provisions-clause-8-5-2-f",
    "doc-general-provisions-clause-8-6-1-a",
    "doc-general-provisions-clause-8-6-1-e",
    "doc-general-provisions-clause-8-7-1",
    "doc-general-provisions-clause-8-7-2",
    "doc-general-provisions-clause-8-8-6",
    "doc-general-provisions-clause-8-12-3-a",
    "doc-general-provisions-clause-8-12-3-b",
    "doc-general-provisions-clause-8-13-3",
    "doc-general-provisions-clause-8-14-1-a",
    "doc-general-provisions-clause-8-14-1-c",
    "doc-general-provisions-clause-9-3-1-c-ii",
    "doc-general-provisions-clause-9-21-1-c-i",
    "doc-general-provisions-clause-9-21-1-c-ii",
    "doc-general-provisions-clause-9-21-1-c-iii",
    "doc-general-provisions-clause-9-21-1-c-iv",
    "doc-general-provisions-clause-9-22-6-f",
    "doc-general-provisions-clause-7-3-2-g",
    "doc-general-provisions-clause-7-4-1-e-xvii",
    "doc-other-clause-2-3-1-c-vi",
    "doc-other-clause-2-8-5-a",
}


def promote_reviewed_draft_general_provisions_requirements(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    changed = False
    for requirement in (data.get("structured_data") or {}).get("other_requirements") or []:
        clause_ids = {
            ref.get("source_ref_id")
            for ref in requirement.get("source_refs") or []
            if ref.get("source_ref_type") == "clause"
        }
        if clause_ids & DRAFT_GENERAL_PROVISIONS_REVIEWED_REQUIREMENT_CLAUSES:
            if requirement.get("confidence") != "high":
                requirement["confidence"] = "high"
                changed = True
    return changed


DRAFT_ZONE_REVIEWED_REQUIREMENT_CLAUSES = {
    "zone-dms-clause-14-4-1",
    "zone-dms-clause-14-5-9-b",
    "zone-dms-clause-14-5-9-c",
    "zone-dms-clause-14-5-11",
    "zone-dms-clause-14-5-13",
    "zone-dmu-clause-15-3-2",
    "zone-dmu-clause-15-4-1",
    "zone-dmu-clause-15-5-3-a",
    "zone-dmu-clause-15-5-10",
    "zone-dw-clause-17-5-1",
    "zone-dw-clause-17-5-3",
    "zone-dw-clause-17-5-8-ffe",
    "zone-dw-clause-17-5-9",
    "zone-dw-clause-17-6-1",
    "zone-dw-clause-17-7-10-b",
    "zone-dw-clause-17-7-12",
    "zone-dw-clause-17-7-14",
    "zone-bp-clause-18-5-9-b",
    "zone-bp-clause-18-6-7-a",
    "zone-bp-clause-18-6-10",
    "zone-bp-clause-18-6-13",
    "zone-c-clause-27-4-2",
    "zone-dc-clause-13-4-1",
    "zone-dc-clause-13-5-12",
    "zone-dc-clause-13-5-14",
    "zone-dc-clause-13-6-5",
    "zone-dn-clause-16-4-3-b",
    "zone-dn-clause-16-5-5",
    "zone-gn-clause-23-5-11",
    "zone-hi-clause-20-5-5",
    "zone-hi-clause-20-6-3",
    "zone-hi-clause-20-6-3-a",
    "zone-p-clause-21-5-3",
    "zone-p-clause-21-6-1-b",
    "zone-i-clause-24-5-8-b",
    "zone-i-clause-24-6-10",
    "zone-i-clause-24-6-13",
    "zone-i-clause-24-6-13-a",
    "zone-rn-clause-10-1",
    "zone-rn-clause-10-3-1-a",
    "zone-rn-clause-10-4-2-c",
    "zone-rn-clause-10-6-2",
    "zone-rh-clause-12-4-4-c",
    "zone-rm-clause-11-4-7-c",
    "zone-rm-clause-11-6-6",
}


def promote_reviewed_draft_zone_requirements(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    changed = False
    for requirement in (data.get("structured_data") or {}).get("other_requirements") or []:
        clause_ids = {
            ref.get("source_ref_id")
            for ref in requirement.get("source_refs") or []
            if ref.get("source_ref_type") == "clause"
        }
        if clause_ids & DRAFT_ZONE_REVIEWED_REQUIREMENT_CLAUSES:
            if requirement.get("confidence") != "high":
                requirement["confidence"] = "high"
                changed = True
    return changed


def repair_draft_dmu_landscape_clause(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "DMU" or not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    changed = False
    raw_data = data.get("raw_data") or {}
    for source_unit in raw_data.get("source_units") or []:
        text = source_unit.get("text_raw")
        if isinstance(text, str) and "See Section 6.8-6.9 1.5 m" in text:
            source_unit["text_raw"] = text.replace("See Section 6.8-6.9 1.5 m", "See Section 6.8-6.9")
            changed = True
    for section in raw_data.get("sections_raw") or []:
        for clause in section.get("clauses_raw") or []:
            if clause.get("clause_id") == "zone-dmu-clause-15-6-1" and clause.get("clause_text_raw") == "See Section 6.8-6.9 1.5 m":
                clause["clause_text_raw"] = "See Section 6.8-6.9"
                changed = True
    return changed


def repair_reviewed_draft_zone_clause_text(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    zone_code = metadata.get("zone_code")
    structured = data.get("structured_data") or {}
    changed = False
    if zone_code == "BP":
        for requirement in structured.get("other_requirements") or []:
            if requirement.get("requirement_id") == "zone-bp-req-zone-bp-clause-18-6-13":
                text = "Properties that abut residential uses shall include a 3 m wide landscape buffer along the abutting property line that includes:"
                if requirement.get("requirement_text_raw") != text:
                    requirement["requirement_text_raw"] = text
                    changed = True
    if zone_code == "RN":
        for requirement in structured.get("other_requirements") or []:
            if requirement.get("requirement_id") == "zone-rn-req-zone-rn-clause-10-6-2":
                text = "All driveways shall be hard surfaced with asphalt, concrete or unit pavers. Loose gravel or soil is not permitted."
                if requirement.get("requirement_text_raw") != text:
                    requirement["requirement_text_raw"] = text
                    changed = True
                if requirement.get("numeric_value_refs"):
                    requirement["numeric_value_refs"] = []
                    changed = True
        numeric_values = structured.get("numeric_values") or []
        filtered = [
            value
            for value in numeric_values
            if value.get("numeric_value_id") != "zone-rn-num-zone-rn-clause-10-6-2-1"
        ]
        if len(filtered) != len(numeric_values):
            structured["numeric_values"] = filtered
            changed = True
    return changed


def repair_reviewed_draft_general_provisions_clause_text(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if not str(metadata.get("bylaw_name") or "").startswith("Draft Zoning"):
        return False
    structured = data.get("structured_data") or {}
    bad_text = " 6.0 m Road Right-of-Way Sidewalk Road"
    changed = False
    raw_data = data.get("raw_data") or {}
    for source_unit in raw_data.get("source_units") or []:
        text = source_unit.get("text_raw")
        if isinstance(text, str) and bad_text in text:
            source_unit["text_raw"] = text.replace(bad_text, "")
            changed = True
    for section in raw_data.get("sections_raw") or []:
        for clause in section.get("clauses_raw") or []:
            text = clause.get("clause_text_raw")
            if clause.get("clause_id") == "doc-general-provisions-clause-3-9-1-a" and isinstance(text, str) and bad_text in text:
                clause["clause_text_raw"] = text.replace(bad_text, "")
                changed = True
    for requirement in structured.get("other_requirements") or []:
        if requirement.get("requirement_id") == "doc-general-provisions-source-req-doc-general-provisions-clause-3-9-1-a":
            text = "When a building or structure is accessory to construction in progress, such as a work or construction camp, Modular Dwelling, sales or rental Office, tool or maintenance shed and scaffold."
            if requirement.get("requirement_text_raw") != text:
                requirement["requirement_text_raw"] = text
                changed = True
            if requirement.get("numeric_value_refs"):
                requirement["numeric_value_refs"] = []
                changed = True
    numeric_values = structured.get("numeric_values") or []
    filtered = [
        value
        for value in numeric_values
        if value.get("numeric_value_id") != "doc-general-provisions-source-num-doc-general-provisions-clause-3-9-1-a-1"
    ]
    if len(filtered) != len(numeric_values):
        structured["numeric_values"] = filtered
        changed = True
    return changed


def repair_general_provisions_tables(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("document_type") not in {"general_provisions", "design_standards"}:
        return False
    if repair_charlottetown_draft_general_provisions_tables(data):
        return True
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    section_4_1 = next((section for section in sections if section.get("section_id") == "doc-general-provisions-section-4-1"), None)
    if section_4_1:
        table_id_value = "doc-general-provisions-table-4-1-2-accessory-buildings"
        table = {
            "table_id": table_id_value,
            "table_title_raw": "4.1.2 Accessory Building Regulations",
            "source_order": 1,
            "columns_raw": general_provisions_table_columns(
                [
                    ("row_label", ""),
                    ("lot_area", "Lot Area"),
                    ("accessory_buildings_permitted", "# of Accessory Buildings permitted"),
                    ("total_building_footprint_maximum", "Total Building Footprint (maximum)"),
                    ("height_maximum", "Height (maximum)"),
                ]
            ),
            "rows_raw": [
                make_labeled_table_row(
                    table_id_value,
                    1,
                    "a",
                    {
                        "lot_area": "0 to 0.499 Acres (0 to 21,779sq ft)",
                        "accessory_buildings_permitted": "Two",
                        "total_building_footprint_maximum": "10% of the Lot Area, up to a maximum of 69.68sq m (750sq ft)",
                        "height_maximum": "5.3m (17.5ft)",
                    },
                ),
                make_labeled_table_row(
                    table_id_value,
                    2,
                    "b",
                    {
                        "lot_area": "0.5 to 0.99 Acres (21,780sq ft to 43,559sq ft)",
                        "accessory_buildings_permitted": "Two",
                        "total_building_footprint_maximum": "78.97sq m (850sq ft)",
                        "height_maximum": "6.1m (20ft)",
                    },
                ),
                make_labeled_table_row(
                    table_id_value,
                    3,
                    "c",
                    {
                        "lot_area": "1 Acre or more (43,560sq ft or more)",
                        "accessory_buildings_permitted": "Three",
                        "total_building_footprint_maximum": "111.48sq m (1,200sq ft); however, no Accessory Building shall exceed 78.97sq m (850sq ft)",
                        "height_maximum": "6.1m (20ft)",
                    },
                ),
            ],
            "citations": {
                "pdf_page_start": 33,
                "pdf_page_end": 33,
                "bylaw_page_start": 33,
                "bylaw_page_end": 33,
            },
        }
        replace_section_table(section_4_1, table)
        remove_clause_id_range(
            section_4_1,
            {
                "doc-general-provisions-clause-4-1-2-a",
                "doc-general-provisions-clause-4-1-2-b",
                "doc-general-provisions-clause-4-1-2-c",
            },
        )
        changed = True

    section_4_2 = next((section for section in sections if section.get("section_id") == "doc-general-provisions-section-4-2"), None)
    if section_4_2:
        table_id_value = "doc-general-provisions-table-4-2-2-projecting-structures"
        table = {
            "table_id": table_id_value,
            "table_title_raw": "4.2.2 Projecting Structures",
            "source_order": 1,
            "columns_raw": general_provisions_table_columns(
                [
                    ("row_label", ""),
                    ("structure", "Structure"),
                    ("yard_projection_permitted", "Yard in which projection is permitted"),
                    ("maximum_projection_into_yard", "Maximum projection into Yard"),
                    ("minimum_distance_from_lot_line", "Minimum distance from Lot Line"),
                ]
            ),
            "rows_raw": [
                make_labeled_table_row(table_id_value, 1, "a", {"structure": "Canopy, Awning", "yard_projection_permitted": "Front Yard, Rear Yard, Flankage Yard", "maximum_projection_into_yard": "1.0 m (3.3 ft)", "minimum_distance_from_lot_line": "0.3 m (1.0 ft)"}),
                make_labeled_table_row(table_id_value, 2, "b", {"structure": "Cornice, eave, gutter, chimney, pilaster, and footing", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "0.6 m (2.0 ft)", "minimum_distance_from_lot_line": "0.3 m (1.0 ft)"}),
                make_labeled_table_row(table_id_value, 3, "c", {"structure": "Balcony", "yard_projection_permitted": "Side Yard, Flankage Yard, Rear Yard", "maximum_projection_into_yard": "1.2 m (3.9 ft)", "minimum_distance_from_lot_line": "1.0 m (3.3 ft)"}),
                make_labeled_table_row(table_id_value, 4, "d", {"structure": "Bay window", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "0.6 m (2.0 ft)", "minimum_distance_from_lot_line": "1.0 m (3.3 ft)"}),
                make_labeled_table_row(table_id_value, 5, "e", {"structure": "Ramp", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "1.83 m (6 ft)", "minimum_distance_from_lot_line": "1.0 m (3.3 ft)"}),
                make_labeled_table_row(table_id_value, 6, "f", {"structure": "Exterior staircase (landing and stairs connecting to the First Storey)", "yard_projection_permitted": "All Yards", "maximum_projection_into_yard": "1.83m (6 ft)", "minimum_distance_from_lot_line": "6.0 m (19.7 ft) from the Front Lot Line and Flankage Lot Line; 1.2 m (3.9 ft) from the Side or Rear Lot Line"}),
                make_labeled_table_row(table_id_value, 7, "g", {"structure": "Exterior staircase (fire escape and any stairs extending beyond the First Storey)", "yard_projection_permitted": "Side Yard, Rear Yard", "maximum_projection_into_yard": "1.2 m (3.9 ft)", "minimum_distance_from_lot_line": "1.2 m (3.9 ft)"}),
                make_labeled_table_row(table_id_value, 8, "h", {"structure": "Deck 0.3 m (1.0 ft) or more above Grade", "yard_projection_permitted": "Rear Yard, Flankage Yard, Side Yard", "maximum_projection_into_yard": "Same as minimum Side Yard for the Building, except in R-1L R-1S, R-1N, R-2 and R-2S Zones where the Setback is 4.6 m (15.1 ft) from the Rear Lot Line", "minimum_distance_from_lot_line": ""}),
                make_labeled_table_row(table_id_value, 9, "i", {"structure": "Deck at Grade or less than 0.3 m (1.0 ft)", "yard_projection_permitted": "Rear Yard, Flankage Yard, Side Yard", "maximum_projection_into_yard": "", "minimum_distance_from_lot_line": "1.0 m (3.3 ft)"}),
                make_labeled_table_row(table_id_value, 10, "j", {"structure": "Deck at Grade or less than 0.3 m (1.0 ft)", "yard_projection_permitted": "Front Yard", "maximum_projection_into_yard": "1.83m (6 ft)", "minimum_distance_from_lot_line": "2.0 m (6.6 ft)"}),
                make_labeled_table_row(table_id_value, 11, "k", {"structure": "Porch", "yard_projection_permitted": "Front Yard, Flankage Yard, Rear Yard", "maximum_projection_into_yard": "1.5 m (4.9 ft)", "minimum_distance_from_lot_line": "1.0 m (3.3 ft)"}),
            ],
            "citations": {
                "pdf_page_start": 34,
                "pdf_page_end": 35,
                "bylaw_page_start": 34,
                "bylaw_page_end": 35,
            },
        }
        replace_section_table(section_4_2, table)
        remove_clause_id_range(
            section_4_2,
            {f"doc-general-provisions-clause-4-2-2-{label}" for label in "abcdefghijk"},
        )
        changed = True

    if changed:
        raw_data["tables_raw"] = [
            {"table_id": table["table_id"], "section_id": section["section_id"]}
            for section in sections
            for table in section.get("tables_raw") or []
        ]
        rebuild_clause_refs(data)
        refresh_source_unit_text_from_raw(data)
    return changed


def repair_general_provisions_sign_permit_hierarchy(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("document_type") != "general_provisions":
        return False
    raw_data = data.get("raw_data") or {}
    section = next(
        (
            item
            for item in raw_data.get("sections_raw") or []
            if item.get("section_id") == "doc-general-provisions-section-47-2"
        ),
        None,
    )
    if not section:
        return False
    parent_id = "doc-general-provisions-clause-47-2-1"
    clauses = section.get("clauses_raw") or []
    if any(clause.get("clause_id") == f"{parent_id}-c-i" for clause in clauses):
        return False

    repaired: list[dict[str, Any]] = []
    changed = False
    active_parent: str | None = None
    active_n_parent: str | None = None
    for clause in clauses:
        cid = str(clause.get("clause_id") or "")
        label = str(clause.get("clause_label_raw") or "")
        text = str(clause.get("clause_text_raw") or "")
        if not cid.startswith(parent_id):
            repaired.append(clause)
            continue
        if cid == f"{parent_id}-c":
            active_parent = f"{parent_id}-c"
            repaired.append(clause)
            continue
        if cid == f"{parent_id}-n":
            active_parent = f"{parent_id}-n"
            if " a) " in text:
                n_text, n_a_text = text.split(" a) ", 1)
                clause["clause_text_raw"] = clean_text(n_text)
                n_a = dict(clause)
                n_a["clause_id"] = f"{parent_id}-n-a"
                n_a["clause_label_raw"] = "a"
                n_a["clause_text_raw"] = clean_text(n_a_text)
                n_a["parent_clause_id"] = f"{parent_id}-n"
                repaired.append(clause)
                repaired.append(n_a)
                active_n_parent = f"{parent_id}-n-a"
                changed = True
                continue
            repaired.append(clause)
            continue
        if cid == f"{parent_id}-t":
            active_parent = f"{parent_id}-t"
            active_n_parent = None
            repaired.append(clause)
            continue
        if cid == f"{parent_id}-u":
            active_parent = f"{parent_id}-u"
            active_n_parent = None
            repaired.append(clause)
            continue
        nested_label = False
        if label in {"i", "ii", "iii", "iv", "v", "vi"}:
            if active_parent == f"{parent_id}-c":
                clause["clause_id"] = f"{parent_id}-c-{label}"
                clause["parent_clause_id"] = f"{parent_id}-c"
                changed = True
                nested_label = True
            elif active_parent == f"{parent_id}-n":
                if label == "iii" and " b) " in text:
                    before_b, n_b_text = text.split(" b) ", 1)
                    clause["clause_text_raw"] = clean_text(before_b)
                    clause["clause_id"] = f"{parent_id}-n-a-iii"
                    clause["parent_clause_id"] = f"{parent_id}-n-a"
                    repaired.append(clause)
                    n_b = dict(clause)
                    n_b["clause_id"] = f"{parent_id}-n-b"
                    n_b["clause_label_raw"] = "b"
                    n_b["clause_text_raw"] = clean_text(n_b_text)
                    n_b["parent_clause_id"] = f"{parent_id}-n"
                    repaired.append(n_b)
                    active_n_parent = f"{parent_id}-n-b"
                    changed = True
                    continue
                if active_n_parent:
                    clause["clause_id"] = f"{active_n_parent}-{label}"
                    clause["parent_clause_id"] = active_n_parent
                    changed = True
                    nested_label = True
            elif active_parent in {f"{parent_id}-t", f"{parent_id}-u"}:
                clause["clause_id"] = f"{active_parent}-{label}"
                clause["parent_clause_id"] = active_parent
                if active_parent == f"{parent_id}-u" and label == "vi":
                    active_parent = None
                changed = True
                nested_label = True
        if label in {"d", "e", "f", "g", "h", "j", "k", "l", "m", "o", "p", "q", "r", "s", "v"} and not nested_label:
            active_parent = None
            active_n_parent = None
        repaired.append(clause)

    if not changed:
        return False
    for order, clause in enumerate(repaired, start=1):
        clause["source_order"] = order
    section["clauses_raw"] = repaired
    rebuild_clause_refs(data)
    refresh_source_unit_text_from_raw(data)
    return True


def apply_general_provisions_sign_permit_numeric_context(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("document_metadata") or {}
    if metadata.get("document_type") != "general_provisions":
        return data
    structured = data.get("structured_data") or {}
    for value in structured.get("numeric_values") or []:
        numeric_id = value.get("numeric_value_id")
        if numeric_id == "doc-general-provisions-source-num-doc-general-provisions-clause-47-2-1-u-iii-1":
            value["measure_type"] = "length"
            for alternative in value.get("alternative_values") or []:
                alternative["measure_type"] = "length"
        elif numeric_id == "doc-general-provisions-source-num-doc-general-provisions-clause-47-2-1-u-iii-2":
            value["measure_type"] = "height"
            for alternative in value.get("alternative_values") or []:
                alternative["measure_type"] = "height"
    return data


def repair_r3_lodging_houses_table(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "R-3":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    section = next(
        (
            item
            for item in sections
            if item.get("section_title_raw") == "REGULATIONS FOR LODGING HOUSES AND GROUP HOMES"
        ),
        None,
    )
    if not section or not section.get("tables_raw"):
        return False
    table = section["tables_raw"][0]
    if table.get("table_id") != "zone-r-3-table-regulations-for-lodging-houses-and-group-homes":
        return False
    table_id_value = table["table_id"]
    table["rows_raw"] = [
        make_table_row(
            table_id_value,
            1,
            "1",
            "Lot Area (Minimum)",
            {"interior_lot": "325 sq. m (3,498.3 sq. ft)", "corner_lot": "395 sq. m (4,251.9 sq. ft)"},
        ),
        make_table_row(
            table_id_value,
            2,
            "2",
            "Lot Frontage (Minimum)",
            {"interior_lot": "10.6 m (34.8 ft)", "corner_lot": "15 m (49.2 ft)"},
        ),
        make_table_row(
            table_id_value,
            3,
            "3",
            "Front Yard (Minimum)",
            {"interior_lot": "6.0 m (19.7 ft)", "corner_lot": "6.0 m (19.7 ft)"},
        ),
        make_table_row(
            table_id_value,
            4,
            "4",
            "Rear Yard (Minimum)",
            {"interior_lot": "6.0 m (19.7 ft)", "corner_lot": "6.0 m (19.7 ft)"},
        ),
        make_table_row(
            table_id_value,
            5,
            "5",
            "Side Yard (Minimum)",
            {"interior_lot": "1.8 m (6 ft)", "corner_lot": "1.83 m (6 ft)"},
        ),
        make_table_row(
            table_id_value,
            6,
            "6",
            "Flankage Yard (Minimum)",
            {"interior_lot": "", "corner_lot": "6.0 m (19.7 ft)"},
        ),
        make_table_row(
            table_id_value,
            7,
            "7",
            "Height (Maximum)",
            {"interior_lot": "12.0 m (39.4 ft)", "corner_lot": "12.0 m (39.4 ft)"},
        ),
    ]
    parent_clause_id_value = "zone-r-3-clause-16-4-room-count"
    room_clauses = [
        {
            "clause_id": parent_clause_id_value,
            "clause_label_raw": "",
            "clause_text_raw": "The number of rooms is determined by the following:",
            "parent_clause_id": None,
            "source_order": 1,
            "citations": {"pdf_page_start": 73, "pdf_page_end": 73, "bylaw_page_start": 73, "bylaw_page_end": 73},
        },
        {
            "clause_id": "zone-r-3-clause-16-4-room-count-a",
            "clause_label_raw": "a",
            "clause_text_raw": "For the first 325 sq. m (3,498.3 sq. ft.) for an interior lot and 395 sq. m (4,251.7 sq. ft.) for a corner lot of Lot Area, four (4) bedrooms are permitted;",
            "parent_clause_id": parent_clause_id_value,
            "source_order": 2,
            "citations": {"pdf_page_start": 73, "pdf_page_end": 73, "bylaw_page_start": 73, "bylaw_page_end": 73},
        },
        {
            "clause_id": "zone-r-3-clause-16-4-room-count-b",
            "clause_label_raw": "b",
            "clause_text_raw": "For every additional bedroom or lodging room over four (4) bedrooms or lodging rooms, the Lot area must be increased by 90 sq. m (968.7 sq. ft.) thereof.",
            "parent_clause_id": parent_clause_id_value,
            "source_order": 3,
            "citations": {"pdf_page_start": 73, "pdf_page_end": 73, "bylaw_page_start": 73, "bylaw_page_end": 73},
        },
    ]
    existing = [
        clause
        for clause in section.get("clauses_raw") or []
        if not str(clause.get("clause_id") or "").startswith(parent_clause_id_value)
    ]
    section["clauses_raw"] = [*existing, *room_clauses]
    source_units = raw_data.get("source_units") or []
    if source_units:
        source_units[0]["text_raw"] = "\n".join(
            clause["clause_text_raw"]
            for raw_section in sections
            for clause in raw_section.get("clauses_raw") or []
        )
    rebuild_clause_refs(data)
    return True


def repair_r3_section_structure(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "R-3":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    section_16_2 = next((section for section in sections if section.get("section_id") == "zone-r-3-section-2"), None)
    if section_16_2:
        section_16_2["section_id"] = "zone-r-3-section-16-2"
        section_16_2["section_label_raw"] = "16.2"
        changed = True

    section_16_3 = next((section for section in sections if section.get("section_id") == "zone-r-3-section-3"), None)
    split_title_section = next((section for section in sections if section.get("section_id") == "zone-r-3-section-16-3"), None)
    if section_16_3:
        section_16_3["section_id"] = "zone-r-3-section-16-3"
        section_16_3["section_label_raw"] = "16.3"
        if not str(section_16_3.get("section_title_raw") or "").endswith("DWELLINGS"):
            section_16_3["section_title_raw"] = clean_text(f"{section_16_3.get('section_title_raw') or ''} DWELLINGS")
        if split_title_section:
            section_16_3["tables_raw"] = sorted(
                [*section_16_3.get("tables_raw", []), *split_title_section.get("tables_raw", [])],
                key=lambda table: table.get("source_order", 0),
            )
            for index, table in enumerate(section_16_3["tables_raw"], start=1):
                table["source_order"] = index
        page_72 = {"pdf_page_start": 72, "pdf_page_end": 72, "bylaw_page_start": 72, "bylaw_page_end": 72}
        clause_16_3_8_id = "zone-r-3-clause-16-3-8"
        clauses = [
            {
                "clause_id": clause_16_3_8_id,
                "clause_label_raw": "16.3.8",
                "clause_text_raw": "Regulations for Townhouses, Stacked and Block Townhouse Dwellings include:",
                "parent_clause_id": None,
                "source_order": 1,
                "citations": page_72,
            },
            {
                "clause_id": "zone-r-3-clause-16-3-8-a",
                "clause_label_raw": "a",
                "clause_text_raw": "Where Dwelling Units are to be subdivided, an Easement in favour of the central units for access to the Rear Yards from the Street shall be provided.",
                "parent_clause_id": clause_16_3_8_id,
                "source_order": 2,
                "citations": page_72,
            },
            {
                "clause_id": "zone-r-3-clause-16-3-8-b",
                "clause_label_raw": "b",
                "clause_text_raw": "A maximum of 8 consecutive Dwelling Units",
                "parent_clause_id": clause_16_3_8_id,
                "source_order": 3,
                "citations": page_72,
            },
            {
                "clause_id": "zone-r-3-clause-16-3-8-c",
                "clause_label_raw": "c",
                "clause_text_raw": "Where 8 consecutive Dwelling Units are proposed, individual Dwelling Units shall not exceed 6.5 m (21.3 ft) in width.",
                "parent_clause_id": clause_16_3_8_id,
                "source_order": 4,
                "citations": page_72,
            },
        ]
        existing = [
            clause
            for clause in section_16_3.get("clauses_raw") or []
            if not str(clause.get("clause_id") or "").startswith(clause_16_3_8_id)
        ]
        section_16_3["clauses_raw"] = [*existing, *clauses]
        changed = True

    if split_title_section:
        sections[:] = [section for section in sections if section is not split_title_section]
        changed = True

    section_16_4 = next(
        (
            section
            for section in sections
            if section.get("section_title_raw") == "REGULATIONS FOR LODGING HOUSES AND GROUP HOMES"
        ),
        None,
    )
    if section_16_4 and section_16_4.get("section_id") == "zone-r-3-section-5":
        section_16_4["section_id"] = "zone-r-3-section-16-4"
        section_16_4["section_label_raw"] = "16.4"
        changed = True

    if changed:
        for index, section in enumerate(sections, start=1):
            section["source_order"] = index
        raw_data["tables_raw"] = [
            {"table_id": table["table_id"], "section_id": section["section_id"]}
            for section in sections
            for table in section.get("tables_raw") or []
        ]
        rebuild_clause_refs(data)
        refresh_source_unit_text_from_raw(data)
    return changed


def repair_r3t_section_structure(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "R-3T":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    section_17_2 = next((section for section in sections if section.get("section_id") == "zone-r-3t-section-2"), None)
    split_title_section = next((section for section in sections if section.get("section_id") == "zone-r-3t-section-17-2"), None)
    if section_17_2:
        section_17_2["section_id"] = "zone-r-3t-section-17-2"
        section_17_2["section_label_raw"] = "17.2"
        if not str(section_17_2.get("section_title_raw") or "").endswith("DWELLINGS"):
            section_17_2["section_title_raw"] = clean_text(f"{section_17_2.get('section_title_raw') or ''} DWELLINGS")
        if split_title_section:
            section_17_2["tables_raw"] = sorted(
                [*section_17_2.get("tables_raw", []), *split_title_section.get("tables_raw", [])],
                key=lambda table: table.get("source_order", 0),
            )
            for index, table in enumerate(section_17_2["tables_raw"], start=1):
                table["source_order"] = index
        page_75 = {"pdf_page_start": 75, "pdf_page_end": 75, "bylaw_page_start": 75, "bylaw_page_end": 75}
        clause_17_2_1_id = "zone-r-3t-clause-17-2-1"
        clauses = [
            {
                "clause_id": clause_17_2_1_id,
                "clause_label_raw": "17.2.1",
                "clause_text_raw": "Regulations for Townhouses, Stacked and Block Townhouse Dwellings include:",
                "parent_clause_id": None,
                "source_order": 1,
                "citations": page_75,
            },
            {
                "clause_id": "zone-r-3t-clause-17-2-1-a",
                "clause_label_raw": "a",
                "clause_text_raw": "Where Dwelling Units are to be subdivided, an Easement in favour of the central units for access to the Rear Yards from the Street shall be provided.",
                "parent_clause_id": clause_17_2_1_id,
                "source_order": 2,
                "citations": page_75,
            },
            {
                "clause_id": "zone-r-3t-clause-17-2-1-b",
                "clause_label_raw": "b",
                "clause_text_raw": "A maximum of 8 consecutive Dwelling Units",
                "parent_clause_id": clause_17_2_1_id,
                "source_order": 3,
                "citations": page_75,
            },
            {
                "clause_id": "zone-r-3t-clause-17-2-1-c",
                "clause_label_raw": "c",
                "clause_text_raw": "Where 8 consecutive Dwelling Units are proposed, individual Dwelling Units shall not exceed 6.5 m (21.3 ft) in width.",
                "parent_clause_id": clause_17_2_1_id,
                "source_order": 4,
                "citations": page_75,
            },
        ]
        existing = [
            clause
            for clause in section_17_2.get("clauses_raw") or []
            if not str(clause.get("clause_id") or "").startswith(clause_17_2_1_id)
        ]
        section_17_2["clauses_raw"] = [*existing, *clauses]
        changed = True

    if split_title_section:
        sections[:] = [section for section in sections if section is not split_title_section]
        changed = True

    section_17_3 = next(
        (
            section
            for section in sections
            if section.get("section_title_raw") == "REGULATIONS FOR LODGING HOUSES AND GROUP HOMES"
        ),
        None,
    )
    if section_17_3:
        section_17_3["section_id"] = "zone-r-3t-section-17-3"
        section_17_3["section_label_raw"] = "17.3"
        page_75 = {"pdf_page_start": 75, "pdf_page_end": 75, "bylaw_page_start": 75, "bylaw_page_end": 75}
        parent_clause_id_value = "zone-r-3t-clause-17-3-room-count"
        room_clauses = [
            {
                "clause_id": parent_clause_id_value,
                "clause_label_raw": "",
                "clause_text_raw": "The number of rooms is determined by the following:",
                "parent_clause_id": None,
                "source_order": 1,
                "citations": page_75,
            },
            {
                "clause_id": "zone-r-3t-clause-17-3-room-count-a",
                "clause_label_raw": "a",
                "clause_text_raw": "For the first 325 sq. m (3,498.3 sq. ft.) for an interior lot and 395 sq. m (4,251.7 sq. ft.) for a corner lot of Lot Area, four (4) bedrooms are permitted;",
                "parent_clause_id": parent_clause_id_value,
                "source_order": 2,
                "citations": page_75,
            },
            {
                "clause_id": "zone-r-3t-clause-17-3-room-count-b",
                "clause_label_raw": "b",
                "clause_text_raw": "For every additional bedroom or lodging room over four (4) bedrooms or lodging rooms, the Lot area must be increased by 90 sq. m (968.7 sq. ft.) thereof.",
                "parent_clause_id": parent_clause_id_value,
                "source_order": 3,
                "citations": page_75,
            },
        ]
        existing = [
            clause
            for clause in section_17_3.get("clauses_raw") or []
            if not str(clause.get("clause_id") or "").startswith(parent_clause_id_value)
        ]
        section_17_3["clauses_raw"] = [*existing, *room_clauses]
        changed = True

    if changed:
        for index, section in enumerate(sections, start=1):
            section["source_order"] = index
        raw_data["tables_raw"] = [
            {"table_id": table["table_id"], "section_id": section["section_id"]}
            for section in sections
            for table in section.get("tables_raw") or []
        ]
        rebuild_clause_refs(data)
        refresh_source_unit_text_from_raw(data)
    return changed


def repair_dc_bonus_height_section(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "DC":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    section = next((item for item in sections if item.get("section_id") == "zone-dc-section-32-3"), None)
    if not section:
        return False
    page_97 = {"pdf_page_start": 97, "pdf_page_end": 97, "bylaw_page_start": 97, "bylaw_page_end": 97}
    page_98 = {"pdf_page_start": 98, "pdf_page_end": 98, "bylaw_page_start": 98, "bylaw_page_end": 98}
    clauses = [
        ("zone-dc-clause-32-3-1", "32.3.1", "Properties in the DC Zone are eligible for a Bonus Height subject to the following regulations:", None, page_97),
        ("zone-dc-clause-32-3-1-a", "a", "A bonus of up to a maximum Building Height of 32.5m (106.6ft).", "zone-dc-clause-32-3-1", page_97),
        ("zone-dc-clause-32-3-1-b", "b", "Lot dimensions:", "zone-dc-clause-32-3-1", page_97),
        ("zone-dc-clause-32-3-1-b-i", "i", "Minimum Lot Frontage of 18.3 m (60 ft) and minimum Lot Depth of 30.m (98.4ft) for a Building Height up to 21.3 m (69.9 ft).", "zone-dc-clause-32-3-1-b", page_97),
        ("zone-dc-clause-32-3-1-b-ii", "ii", "Minimum Lot Frontage of 41 m (135 ft) and minimum Lot Depth of 36m (118ft) for Buildings taller than 21.3 m (69.9 ft).", "zone-dc-clause-32-3-1-b", page_97),
        ("zone-dc-clause-32-3-1-c", "c", "Parking Structures are ineligible for a Bonus Height.", "zone-dc-clause-32-3-1", page_97),
        ("zone-dc-clause-32-3-2", "32.3.2", "Massing for Buildings up to 21.3 m (69.9 ft):", None, page_97),
        ("zone-dc-clause-32-3-2-a", "a", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dc-clause-32-3-2", page_97),
        ("zone-dc-clause-32-3-2-a-i", "i", "A minimum 3.0m (9.8ft) Stepback from the base Building on the front façade.", "zone-dc-clause-32-3-2-a", page_97),
        ("zone-dc-clause-32-3-2-a-ii", "ii", "A minimum 5.5m (18ft) Side Yard Setback or Stepback to ensure adequate separation distances of the upper levels from adjacent properties that may also be eligible for a Height bonus.", "zone-dc-clause-32-3-2-a", page_97),
        ("zone-dc-clause-32-3-2-a-iii", "iii", "A 45-degree angular planes originating from the top of the flank or rear façade of the base Building that faces abutting properties.", "zone-dc-clause-32-3-2-a", page_97),
        ("zone-dc-clause-32-3-3", "32.3.3", "Massing for buildings greater than 21.3 m (69.9 ft):", None, page_97),
        ("zone-dc-clause-32-3-3-a", "a", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dc-clause-32-3-3", page_97),
        ("zone-dc-clause-32-3-3-a-i", "i", "A minimum 6.0m (19.7ft) Stepback above the base Building or above that portion of the Building that is taller than 21.3 m (69.9 ft) on the front façade.", "zone-dc-clause-32-3-3-a", page_97),
        ("zone-dc-clause-32-3-3-b", "b", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dc-clause-32-3-3", page_97),
        ("zone-dc-clause-32-3-3-b-i", "i", "A maximum gross floor plate size of 750 sq m (8,072.9 sq ft);", "zone-dc-clause-32-3-3-b", page_97),
        ("zone-dc-clause-32-3-3-b-ii", "ii", "A minimum 10m (32.8ft) interior Yard Setbacks; and", "zone-dc-clause-32-3-3-b", page_97),
        ("zone-dc-clause-32-3-3-b-iii", "iii", "A maximum 25.0m (82ft) Building width addressing the Street.", "zone-dc-clause-32-3-3-b", page_97),
        ("zone-dc-clause-32-3-4", "32.3.4", "Where bonus heights are considered on properties subject to a Landmark View Plane as identified in the Official Plan, the additional heights shall not be visible over Province House from the vantage of a pedestrian (1.7m or 5.8ft) facing north on Great George Street at any point between Richmond Street and Dorchester Street.", None, page_98),
        ("zone-dc-clause-32-3-5", "32.3.5", "Bonus Height applications are subject to the provisions in the Bonus Height Applications Section of this by-law.", None, page_98),
    ]
    section["clauses_raw"] = [
        {
            "clause_id": clause_id_value,
            "clause_label_raw": label,
            "clause_text_raw": text,
            "parent_clause_id": parent_clause_id,
            "source_order": order,
            "citations": cite,
        }
        for order, (clause_id_value, label, text, parent_clause_id, cite) in enumerate(clauses, start=1)
    ]
    source_units = raw_data.get("source_units") or []
    if source_units:
        source_units[0]["text_raw"] = "\n".join(
            clause["clause_text_raw"]
            for raw_section in sections
            for clause in raw_section.get("clauses_raw") or []
        )
    rebuild_clause_refs(data)
    return True


def repair_dms_bonus_height_section(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "DMS":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    section = next((item for item in sections if item.get("section_id") == "zone-dms-section-31-3"), None)
    if not section:
        return False
    page_95 = {"pdf_page_start": 95, "pdf_page_end": 95, "bylaw_page_start": 95, "bylaw_page_end": 95}
    clauses = [
        ("zone-dms-clause-31-3-1", "31.3.1", "Properties in the DC Zone are eligible for a Bonus Height subject to the following regulations:", None, page_95),
        ("zone-dms-clause-31-3-1-a", "a", "A bonus of up to a maximum Building Height of 32.5m (106.6ft).", "zone-dms-clause-31-3-1", page_95),
        ("zone-dms-clause-31-3-1-b", "b", "Lot dimensions:", "zone-dms-clause-31-3-1", page_95),
        ("zone-dms-clause-31-3-1-b-i", "i", "Minimum Lot Frontage of 18.3 m (60 ft) and minimum Lot Depth of 30.m (98.4ft) for a Building Height up to 21.3 m (69.9 ft).", "zone-dms-clause-31-3-1-b", page_95),
        ("zone-dms-clause-31-3-1-b-ii", "ii", "Minimum Lot Frontage of 41 m (135 ft) and minimum Lot Depth of 36m (118ft) for Buildings taller than 21.3 m (69.9 ft).", "zone-dms-clause-31-3-1-b", page_95),
        ("zone-dms-clause-31-3-1-c", "c", "Parking Structures are ineligible for a Bonus Height.", "zone-dms-clause-31-3-1", page_95),
        ("zone-dms-clause-31-3-2", "31.3.2", "Massing for Buildings up to 21.3 m (69.9 ft):", None, page_95),
        ("zone-dms-clause-31-3-2-a", "a", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dms-clause-31-3-2", page_95),
        ("zone-dms-clause-31-3-2-a-i", "i", "A minimum 3.0m (9.8ft) Stepback from the base Building on the front façade.", "zone-dms-clause-31-3-2-a", page_95),
        ("zone-dms-clause-31-3-2-a-ii", "ii", "A minimum 5.5m (18ft) Side Yard Setback or Stepback to ensure adequate separation distances of the upper levels from adjacent properties that may also be eligible for a Height bonus.", "zone-dms-clause-31-3-2-a", page_95),
        ("zone-dms-clause-31-3-2-a-iii", "iii", "A 45-degree angular planes originating from the top of the flank or rear façade of the base Building that faces abutting properties.", "zone-dms-clause-31-3-2-a", page_95),
        ("zone-dms-clause-31-3-3", "31.3.3", "Massing for buildings greater than 21.3 m (69.9 ft):", None, page_95),
        ("zone-dms-clause-31-3-3-a", "a", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dms-clause-31-3-3", page_95),
        ("zone-dms-clause-31-3-3-a-i", "i", "A minimum 6.0m (19.7ft) Stepback above the base Building or above that portion of the Building that is taller than 21.3 m (69.9 ft) on the front façade.", "zone-dms-clause-31-3-3-a", page_95),
        ("zone-dms-clause-31-3-3-b", "b", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dms-clause-31-3-3", page_95),
        ("zone-dms-clause-31-3-3-b-i", "i", "A maximum gross floor plate size of 750 sq m (8,072.9 sq ft);", "zone-dms-clause-31-3-3-b", page_95),
        ("zone-dms-clause-31-3-3-b-ii", "ii", "A minimum 10m (32.8ft) interior Yard Setbacks; and", "zone-dms-clause-31-3-3-b", page_95),
        ("zone-dms-clause-31-3-3-b-iii", "iii", "A maximum 25.0m (82ft) Building width addressing the Street.", "zone-dms-clause-31-3-3-b", page_95),
        ("zone-dms-clause-31-3-4", "31.3.4", "Where bonus heights are considered on properties subject to a Landmark View Plane as identified in the Official Plan, the additional heights shall not be visible over Province House from the vantage of a pedestrian (1.7m or 5.8ft) facing north on Great George Street at any point between Richmond Street and Dorchester Street.", None, page_95),
        ("zone-dms-clause-31-3-5", "31.3.5", "Bonus Height applications are subject to the provisions in the Bonus Height Applications Section of this by-law.", None, page_95),
    ]
    section["clauses_raw"] = [
        {
            "clause_id": clause_id_value,
            "clause_label_raw": label,
            "clause_text_raw": text,
            "parent_clause_id": parent_clause_id,
            "source_order": order,
            "citations": cite,
        }
        for order, (clause_id_value, label, text, parent_clause_id, cite) in enumerate(clauses, start=1)
    ]
    source_units = raw_data.get("source_units") or []
    if source_units:
        source_units[0]["text_raw"] = "\n".join(
            clause["clause_text_raw"]
            for raw_section in sections
            for clause in raw_section.get("clauses_raw") or []
        )
    rebuild_clause_refs(data)
    return True


def repair_wf_bonus_height_section(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "WF":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    section = next((item for item in sections if item.get("section_id") == "zone-wf-section-34-4"), None)
    if not section:
        return False
    page_102 = {"pdf_page_start": 102, "pdf_page_end": 102, "bylaw_page_start": 102, "bylaw_page_end": 102}
    page_103 = {"pdf_page_start": 103, "pdf_page_end": 103, "bylaw_page_start": 103, "bylaw_page_end": 103}
    page_104 = {"pdf_page_start": 104, "pdf_page_end": 104, "bylaw_page_start": 104, "bylaw_page_end": 104}
    clauses = [
        ("zone-wf-clause-34-4-1", "34.4.1", "Properties in the DWF Zone are eligible for a Bonus Height subject to the following regulations.", None, page_102),
        ("zone-wf-clause-34-4-1-a", "a", "The maximum Height as specified on Map D may be exceeded to the maximum bonus Height as specified on Map E.", "zone-wf-clause-34-4-1", page_102),
        ("zone-wf-clause-34-4-1-a-i", "i", "A bonus of up to a maximum Building Height of 24.5m (80.4 ft) for properties fronting on Water St.", "zone-wf-clause-34-4-1-a", page_102),
        ("zone-wf-clause-34-4-1-a-ii", "ii", "A bonus of up to a maximum Building Height of 32.5m (106.6 ft) for all other properties.", "zone-wf-clause-34-4-1-a", page_103),
        ("zone-wf-clause-34-4-1-b", "b", "Parking Structures are ineligible for a Bonus Height.", "zone-wf-clause-34-4-1", page_103),
        ("zone-wf-clause-34-4-2", "34.4.2", "Massing for buildings up to 21.3 m (69.9 ft):", None, page_103),
        ("zone-wf-clause-34-4-2-a", "a", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-wf-clause-34-4-2", page_103),
        ("zone-wf-clause-34-4-2-a-i", "i", "A minimum 3.0m (9.8ft) Stepback from the base Building on the front façade.", "zone-wf-clause-34-4-2-a", page_103),
        ("zone-wf-clause-34-4-2-a-ii", "ii", "A minimum 5.5m (18ft) Side Yard Setback or Stepback to ensure adequate separation distances of the upper levels from adjacent properties that may also be eligible for a Height bonus.", "zone-wf-clause-34-4-2-a", page_103),
        ("zone-wf-clause-34-4-2-a-iii", "iii", "A 45-degree angular planes originating from the top of the flank or rear façade of the base Building that faces abutting properties.", "zone-wf-clause-34-4-2-a", page_103),
        ("zone-wf-clause-34-4-3", "34.4.3", "Massing for Buildings greater than 21.3 m (69.9 ft):", None, page_103),
        ("zone-wf-clause-34-4-3-a", "a", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-wf-clause-34-4-3", page_103),
        ("zone-wf-clause-34-4-3-a-i", "i", "A minimum 6.0m (19.7ft) Stepback above the base Building or above that portion of the Building that is taller than 21.3 m (69.9 ft) on the front façade.", "zone-wf-clause-34-4-3-a", page_103),
        ("zone-wf-clause-34-4-3-b", "b", "The portion of the Building above 21.3 m (69.9 ft) shall have:", "zone-wf-clause-34-4-3", page_103),
        ("zone-wf-clause-34-4-3-b-i", "i", "A maximum gross floor plate size of 750 sq m (8,072.9 sq ft);", "zone-wf-clause-34-4-3-b", page_103),
        ("zone-wf-clause-34-4-3-b-ii", "ii", "A minimum 10m (32.8 ft) interior Yard Setbacks; and", "zone-wf-clause-34-4-3-b", page_103),
        ("zone-wf-clause-34-4-3-b-iii", "iii", "A maximum 25.0m (82 ft) Building width addressing the Street.", "zone-wf-clause-34-4-3-b", page_103),
        ("zone-wf-clause-34-4-4", "34.4.4", "Bonus Height applications are subject to the provisions in the Bonus Height Applications Section of this by-law.", None, page_103),
        ("zone-wf-clause-34-4-5", "34.4.5", "Map D: Maximum Height", None, page_103),
        ("zone-wf-clause-34-4-6", "34.4.6", "16.5 m (54.1 ft) 24.5 m (80.4 ft)", None, page_103),
        ("zone-wf-clause-34-4-7", "34.4.7", "Map E: Maximum Bonus Height", None, page_104),
    ]
    section["clauses_raw"] = [
        {
            "clause_id": clause_id_value,
            "clause_label_raw": label,
            "clause_text_raw": text,
            "parent_clause_id": parent_clause_id,
            "source_order": order,
            "citations": cite,
        }
        for order, (clause_id_value, label, text, parent_clause_id, cite) in enumerate(clauses, start=1)
    ]
    source_units = raw_data.get("source_units") or []
    if source_units:
        source_units[0]["text_raw"] = "\n".join(
            clause["clause_text_raw"]
            for raw_section in sections
            for clause in raw_section.get("clauses_raw") or []
        )
    rebuild_clause_refs(data)
    return True


def repair_rm_table_clauses(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("document_type") != "zone":
        return False
    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    for section in sections:
        clauses = section.get("clauses_raw") or []
        if not clauses:
            continue
        children_by_parent: dict[str, list[dict[str, Any]]] = {}
        for clause in clauses:
            parent_clause_id = clause.get("parent_clause_id")
            if parent_clause_id:
                children_by_parent.setdefault(parent_clause_id, []).append(clause)

        for parent in list(clauses):
            parent_clause_id = parent.get("clause_id") or ""
            child_clauses = sorted(
                children_by_parent.get(parent_clause_id, []),
                key=lambda item: table_row_label_sort_key(item.get("clause_label_raw")),
            )
            if len(child_clauses) < 2:
                continue
            if not all(re.fullmatch(r"\([a-z0-9.]+\)", clean_text(child.get("clause_label_raw")), re.IGNORECASE) for child in child_clauses):
                continue

            rows_raw = []
            for row_order, child in enumerate(child_clauses, start=1):
                cell_text = clean_text(child.get("clause_text_raw"))
                match = TABLE_ROW_VALUE_RE.search(cell_text)
                if not match:
                    rows_raw = []
                    break
                requirement = clean_text(cell_text[: match.start(1)])
                value = clean_text(cell_text[match.start(1) :])
                if not requirement or not value:
                    rows_raw = []
                    break
                table_id_value = parent_clause_id.replace("-clause-", "-table-")
                rows_raw.append(
                    make_labeled_table_row(
                        table_id_value,
                        row_order,
                        clean_text(child.get("clause_label_raw")),
                        {"requirement": requirement, "value": value},
                    )
                )
            if not rows_raw:
                continue

            table_id_value = parent_clause_id.replace("-clause-", "-table-")
            table = {
                "table_id": table_id_value,
                "table_title_raw": f"{clean_text(section.get('section_label_raw'))}{clean_text(parent.get('clause_label_raw'))}",
                "source_order": parent.get("source_order", 0) + 1,
                "columns_raw": general_provisions_table_columns(
                    [
                        ("row_label", "clause_label_raw"),
                        ("requirement", "clause_name"),
                        ("value", ""),
                    ]
                ),
                "rows_raw": rows_raw,
                "citations": citation(parent.get("citations")),
            }
            replace_section_table(section, table)
            remove_clause_id_range(section, {child.get("clause_id") for child in child_clauses})
            changed = True

        if metadata.get("zone_code") == "RM":
            clause_by_id = {clause.get("clause_id"): clause for clause in section.get("clauses_raw") or []}
            parent_11_3_2 = clause_by_id.get("zone-rm-clause-11-3-2")
            if parent_11_3_2:
                footnote_id = "zone-rm-clause-11-3-2-note-shared"
                if not any(clause.get("clause_id") == footnote_id for clause in section.get("clauses_raw") or []):
                    repaired = []
                    inserted = False
                    for clause in section.get("clauses_raw") or []:
                        repaired.append(clause)
                        if clause.get("clause_id") == "zone-rm-clause-11-3-2":
                            repaired.append(
                                {
                                    "clause_id": footnote_id,
                                    "clause_label_raw": "",
                                    "clause_text_raw": "* 'shared' includes the shared walls of a townhouse or semi.",
                                    "parent_clause_id": "zone-rm-clause-11-3-2",
                                    "source_order": clause.get("source_order", 0) + 1,
                                    "citations": citation(parent_11_3_2.get("citations")),
                                }
                            )
                            inserted = True
                    if inserted:
                        for order, clause in enumerate(repaired, start=1):
                            clause["source_order"] = order
                        section["clauses_raw"] = repaired
                        changed = True

    if not changed:
        return False
    rebuild_content_refs(data)
    rebuild_clause_refs(data)
    refresh_source_unit_text_from_raw(data)
    return True


def repair_draft_rn_rh_phase4_layout_regressions(data: dict[str, Any]) -> bool:
    metadata = data.get("document_metadata") or {}
    if metadata.get("document_type") != "zone":
        return False
    zone_code = metadata.get("zone_code")
    if zone_code not in {"RN", "RH"}:
        return False

    raw_data = data.get("raw_data") or {}
    sections = raw_data.get("sections_raw") or []
    changed = False

    if zone_code == "RN":
        section_10_4 = find_raw_section(sections, "10.4")
        if section_10_4:
            for table in section_10_4.get("tables_raw") or []:
                if table.get("table_id") != "zone-rn-table-10-4-7":
                    continue
                for row in table.get("rows_raw") or []:
                    if row.get("row_id") != "zone-rn-table-10-4-7-row-7":
                        continue
                    for cell in row.get("cells_raw") or []:
                        if cell.get("column_id") == "value" and cell.get("cell_text_raw") != "max. 40%":
                            cell["cell_text_raw"] = "max. 40%"
                            changed = True

        section_10_6 = find_raw_section(sections, "10.6")
        if section_10_6:
            for clause in section_10_6.get("clauses_raw") or []:
                if clause.get("clause_id") != "zone-rn-clause-10-6-2":
                    continue
                text = "All driveways shall be hard surfaced with asphalt, concrete or unit pavers. Loose gravel or soil is not permitted."
                if clause.get("clause_text_raw") != text:
                    clause["clause_text_raw"] = text
                    changed = True

    if zone_code == "RH":
        section_12_3 = find_raw_section(sections, "12.3")
        if section_12_3:
            keep_ids = {
                "zone-rh-clause-12-3-1",
                "zone-rh-clause-12-3-1-a",
                "zone-rh-clause-12-3-1-b",
                "zone-rh-clause-12-3-1-c",
                "zone-rh-clause-12-3-1-d",
                "zone-rh-clause-12-3-1-e",
                "zone-rh-clause-12-3-1-f",
                "zone-rh-clause-12-3-1-g",
                "zone-rh-clause-12-3-1-h",
                "zone-rh-clause-12-3-2",
                "zone-rh-clause-12-3-3",
            }
            clauses = []
            seen_ids: set[str] = set()
            for clause in section_12_3.get("clauses_raw") or []:
                clause_id_value = clause.get("clause_id")
                if clause_id_value not in keep_ids or clause_id_value in seen_ids:
                    changed = True
                    continue
                clauses.append(clause)
                seen_ids.add(clause_id_value)
            if len(clauses) != len(section_12_3.get("clauses_raw") or []):
                section_12_3["clauses_raw"] = clauses
                resequence_clauses(section_12_3)

            table_12_3_2_id = "zone-rh-table-12-3-2"
            table_12_3_3_id = "zone-rh-table-12-3-3"
            replace_section_table(
                section_12_3,
                {
                    "table_id": table_12_3_2_id,
                    "table_title_raw": "12.3.2",
                    "source_order": 11,
                    "columns_raw": general_provisions_table_columns(
                        [
                            ("row_label", "clause_label_raw"),
                            ("requirement", "clause_name"),
                            ("value", ""),
                        ]
                    ),
                    "rows_raw": [
                        make_labeled_table_row(table_12_3_2_id, 1, "(a)", {"requirement": "Lot Area", "value": "min. 1,100 m2"}),
                        make_labeled_table_row(table_12_3_2_id, 2, "(b)", {"requirement": "Frontage", "value": "min. 20 m for multi"}),
                        make_labeled_table_row(table_12_3_2_id, 3, "(c)", {"requirement": "Front Yard Setback", "value": "min. 6 m"}),
                        make_labeled_table_row(table_12_3_2_id, 4, "(d)", {"requirement": "Flankage Yard Setback", "value": "min. 6 m"}),
                        make_labeled_table_row(table_12_3_2_id, 5, "(e)", {"requirement": "Side Yard Setback", "value": "min. 3 m for cluster, 6 m for multi"}),
                        make_labeled_table_row(table_12_3_2_id, 6, "(f)", {"requirement": "Rear Yard Setback", "value": "min. 6 m"}),
                        make_labeled_table_row(table_12_3_2_id, 7, "(g)", {"requirement": "Coverage", "value": "max. 50%, 60% if half or more the parking is underground"}),
                    ],
                    "citations": citation({"pdf_page_start": 102, "pdf_page_end": 102, "bylaw_page_start": 98, "bylaw_page_end": 98}),
                },
            )
            replace_section_table(
                section_12_3,
                {
                    "table_id": table_12_3_3_id,
                    "table_title_raw": "12.3.3",
                    "source_order": 13,
                    "columns_raw": general_provisions_table_columns(
                        [
                            ("row_label", "clause_label_raw"),
                            ("requirement", "clause_name"),
                            ("value", ""),
                        ]
                    ),
                    "rows_raw": [
                        make_labeled_table_row(table_12_3_3_id, 1, "(a)", {"requirement": "Coverage", "value": "max. 60%"}),
                        make_labeled_table_row(table_12_3_3_id, 2, "(b)", {"requirement": "Footprint / building", "value": "max. 800 m2"}),
                        make_labeled_table_row(table_12_3_3_id, 3, "(c)", {"requirement": "Buildings", "value": "max. 4 buildings per cluster per lot"}),
                        make_labeled_table_row(table_12_3_3_id, 4, "(d)", {"requirement": "Separation between units", "value": "min. 6 m"}),
                        make_labeled_table_row(table_12_3_3_id, 5, "(e)", {"requirement": "Central garden area", "value": "min. 35 m2 / building"}),
                    ],
                    "citations": citation({"pdf_page_start": 102, "pdf_page_end": 102, "bylaw_page_start": 98, "bylaw_page_end": 98}),
                },
            )
            changed = True

        section_12_4 = find_raw_section(sections, "12.4")
        if section_12_4:
            for clause in section_12_4.get("clauses_raw") or []:
                if clause.get("clause_id") != "zone-rh-clause-12-4":
                    continue
                text = "Flaglots are permitted with no less than 6 m frontage as long as all other site and building requirements are met in Section 12.3.2 for both the flaglot and main lot."
                if clause.get("clause_text_raw") != text:
                    clause["clause_text_raw"] = text
                    changed = True

    if not changed:
        return False
    rebuild_content_refs(data)
    rebuild_clause_refs(data)
    refresh_source_unit_text_from_raw(data)
    return True


TABLE_CONTENT_ANCHORS = {
    "doc-general-provisions-table-4-1-2-accessory-buildings": "doc-general-provisions-clause-4-1-2",
    "doc-general-provisions-table-4-2-2-projecting-structures": "doc-general-provisions-clause-4-2-2",
    "zone-rm-table-11-3-2": "zone-rm-clause-11-3-2",
    "zone-rm-table-11-3-3": "zone-rm-clause-11-3-3",
    "zone-rh-table-12-3-2": "zone-rh-clause-12-3-2",
    "zone-rh-table-12-3-3": "zone-rh-clause-12-3-3",
}

TABLE_CONTENT_BEFORE_CLAUSES = {
    "zone-r-3-table-16-3",
    "zone-r-3-table-regulations-for-lodging-houses-and-group-homes",
    "zone-r-3t-table-17-2",
    "zone-r-3t-table-regulations-for-lodging-houses-and-group-homes",
}


def rebuild_content_refs(data: dict[str, Any]) -> dict[str, Any]:
    raw_data = data.get("raw_data") or {}
    for section in raw_data.get("sections_raw") or []:
        clauses = sorted(section.get("clauses_raw") or [], key=lambda item: item.get("source_order", 0))
        tables = sorted(section.get("tables_raw") or [], key=lambda item: item.get("source_order", 0))
        tables_by_anchor: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            table_id_value = table.get("table_id") or ""
            anchor = TABLE_CONTENT_ANCHORS.get(table_id_value)
            if anchor is None and "-table-" in table_id_value:
                anchor = table_id_value.replace("-table-", "-clause-")
            if anchor:
                tables_by_anchor.setdefault(anchor, []).append(table)
        added_table_ids: set[str] = set()
        refs: list[dict[str, Any]] = []

        for table in tables:
            if table.get("table_id") in TABLE_CONTENT_BEFORE_CLAUSES:
                refs.append({"content_type": "table", "content_id": table["table_id"]})
                added_table_ids.add(table["table_id"])

        for clause in clauses:
            refs.append({"content_type": "clause", "content_id": clause["clause_id"]})
            for table in tables_by_anchor.get(clause["clause_id"], []):
                refs.append({"content_type": "table", "content_id": table["table_id"]})
                added_table_ids.add(table["table_id"])

        for table in tables:
            if table["table_id"] not in added_table_ids:
                refs.append({"content_type": "table", "content_id": table["table_id"]})

        section["content_refs"] = [
            {**ref, "source_order": index}
            for index, ref in enumerate(refs, start=1)
        ]
    return data


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
    rebuild_content_refs(data)
    return data


def section_in_allowed_sources(label: str, allowed_source_sections: set[str]) -> bool:
    if not allowed_source_sections:
        return True
    label = clean_text(label)
    if not label:
        return False
    return any(label == allowed or label.startswith(f"{allowed}.") for allowed in allowed_source_sections)


def filter_legacy_sections_by_source_sections(legacy: dict[str, Any], source_sections: list[str] | None) -> dict[str, Any]:
    allowed = {str(section) for section in source_sections or []}
    if not allowed:
        return legacy
    filtered = dict(legacy)
    filtered["sections"] = [
        section
        for section in legacy.get("sections") or []
        if section_in_allowed_sources(str(section.get("section_label_raw") or ""), allowed)
    ]
    return filtered


def filter_raw_sections_by_source_sections(data: dict[str, Any], source_sections: list[str] | None) -> dict[str, Any]:
    allowed = {str(section) for section in source_sections or []}
    if not allowed:
        return data
    raw_data = data.setdefault("raw_data", {})
    raw_data["sections_raw"] = [
        section
        for section in raw_data.get("sections_raw") or []
        if section_in_allowed_sources(str(section.get("section_label_raw") or ""), allowed)
    ]
    section_ids = {section.get("section_id") for section in raw_data.get("sections_raw") or []}
    table_ids = {
        table.get("table_id")
        for section in raw_data.get("sections_raw") or []
        for table in section.get("tables_raw") or []
    }
    raw_data["tables_raw"] = [
        table
        for table in raw_data.get("tables_raw") or []
        if table.get("section_id") in section_ids and table.get("table_id") in table_ids
    ]
    if raw_data.get("source_units"):
        raw_data["source_units"][0]["text_raw"] = "\n".join(
            clause["clause_text_raw"]
            for section in raw_data.get("sections_raw") or []
            for clause in section.get("clauses_raw") or []
        )
    rebuild_clause_refs(data)
    valid_clause_ids = {
        clause.get("clause_id")
        for section in raw_data.get("sections_raw") or []
        for clause in section.get("clauses_raw") or []
    }
    structured = data.setdefault("structured_data", base_structured_data())

    def keep_item_with_source_refs(item: dict[str, Any]) -> bool:
        clause_refs = {
            ref.get("source_ref_id")
            for ref in item.get("source_refs") or []
            if ref.get("source_ref_type") == "clause"
        }
        return not clause_refs or bool(clause_refs & valid_clause_ids)

    for key in ("terms", "uses", "numeric_values", "requirements", "other_requirements"):
        structured[key] = [item for item in structured.get(key) or [] if keep_item_with_source_refs(item)]
    structured["zone_relationships"] = [
        item for item in structured.get("zone_relationships") or [] if item.get("source_clause_ref") in valid_clause_ids
    ]
    structured["cross_references"] = [
        item for item in structured.get("cross_references") or [] if item.get("source_clause_ref") in valid_clause_ids
    ]
    data["review_flags"] = [flag for flag in data.get("review_flags") or [] if keep_item_with_source_refs(flag)]
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


def apply_dc_bonus_height_context(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "DC":
        return data
    structured = data.get("structured_data") or {}
    contextual_clause_ids = {
        "zone-dc-clause-32-3-2",
        "zone-dc-clause-32-3-3",
        "zone-dc-clause-32-3-3-b",
    }

    def sourced_from(req: dict[str, Any], clause_id_value: str) -> bool:
        return any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") == clause_id_value
            for ref in req.get("source_refs") or []
        )

    structured["other_requirements"] = [
        req
        for req in structured.get("other_requirements") or []
        if not any(sourced_from(req, clause_id_value) for clause_id_value in contextual_clause_ids)
    ]
    structured["numeric_values"] = [
        value
        for value in structured.get("numeric_values") or []
        if not any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") in contextual_clause_ids
            for ref in value.get("source_refs") or []
        )
    ]
    conditions_by_clause = {
        "zone-dc-clause-32-3-2-a-i": [
            ("building_height_range", "Massing for Buildings up to 21.3 m (69.9 ft):", "zone-dc-clause-32-3-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dc-clause-32-3-2-a"),
        ],
        "zone-dc-clause-32-3-2-a-ii": [
            ("building_height_range", "Massing for Buildings up to 21.3 m (69.9 ft):", "zone-dc-clause-32-3-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dc-clause-32-3-2-a"),
        ],
        "zone-dc-clause-32-3-2-a-iii": [
            ("building_height_range", "Massing for Buildings up to 21.3 m (69.9 ft):", "zone-dc-clause-32-3-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dc-clause-32-3-2-a"),
        ],
        "zone-dc-clause-32-3-3-a-i": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dc-clause-32-3-3"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dc-clause-32-3-3-a"),
        ],
        "zone-dc-clause-32-3-3-b-i": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dc-clause-32-3-3"),
            ("building_portion", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dc-clause-32-3-3-b"),
        ],
        "zone-dc-clause-32-3-3-b-ii": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dc-clause-32-3-3"),
            ("building_portion", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dc-clause-32-3-3-b"),
        ],
        "zone-dc-clause-32-3-3-b-iii": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dc-clause-32-3-3"),
            ("building_portion", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dc-clause-32-3-3-b"),
        ],
    }
    for req in structured.get("requirements") or []:
        clause_id_value = next(
            (
                ref.get("source_ref_id")
                for ref in req.get("source_refs") or []
                if ref.get("source_ref_type") == "clause"
            ),
            None,
        )
        if clause_id_value not in conditions_by_clause:
            continue
        req.setdefault("applicability", {})["conditions"] = [
            {
                "condition_type": condition_type,
                "condition_text_raw": condition_text,
                "source_refs": [source_ref("clause", source_clause_id)],
            }
            for condition_type, condition_text, source_clause_id in conditions_by_clause[clause_id_value]
        ]
    return data


def apply_dms_bonus_height_context(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "DMS":
        return data
    structured = data.get("structured_data") or {}
    contextual_clause_ids = {
        "zone-dms-clause-31-3-2",
        "zone-dms-clause-31-3-3",
        "zone-dms-clause-31-3-3-b",
    }

    def sourced_from(req: dict[str, Any], clause_id_value: str) -> bool:
        return any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") == clause_id_value
            for ref in req.get("source_refs") or []
        )

    structured["other_requirements"] = [
        req
        for req in structured.get("other_requirements") or []
        if not any(sourced_from(req, clause_id_value) for clause_id_value in contextual_clause_ids)
    ]
    structured["numeric_values"] = [
        value
        for value in structured.get("numeric_values") or []
        if not any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") in contextual_clause_ids
            for ref in value.get("source_refs") or []
        )
    ]
    conditions_by_clause = {
        "zone-dms-clause-31-3-2-a-i": [
            ("building_height_range", "Massing for Buildings up to 21.3 m (69.9 ft):", "zone-dms-clause-31-3-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dms-clause-31-3-2-a"),
        ],
        "zone-dms-clause-31-3-2-a-ii": [
            ("building_height_range", "Massing for Buildings up to 21.3 m (69.9 ft):", "zone-dms-clause-31-3-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dms-clause-31-3-2-a"),
        ],
        "zone-dms-clause-31-3-2-a-iii": [
            ("building_height_range", "Massing for Buildings up to 21.3 m (69.9 ft):", "zone-dms-clause-31-3-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dms-clause-31-3-2-a"),
        ],
        "zone-dms-clause-31-3-3-a-i": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dms-clause-31-3-3"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-dms-clause-31-3-3-a"),
        ],
        "zone-dms-clause-31-3-3-b-i": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dms-clause-31-3-3"),
            ("building_portion", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dms-clause-31-3-3-b"),
        ],
        "zone-dms-clause-31-3-3-b-ii": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dms-clause-31-3-3"),
            ("building_portion", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dms-clause-31-3-3-b"),
        ],
        "zone-dms-clause-31-3-3-b-iii": [
            ("building_height_range", "Massing for buildings greater than 21.3 m (69.9 ft):", "zone-dms-clause-31-3-3"),
            ("building_portion", "The portion of the Building above 21.3 m (70 ft) shall have:", "zone-dms-clause-31-3-3-b"),
        ],
    }
    for req in structured.get("requirements") or []:
        clause_id_value = next(
            (
                ref.get("source_ref_id")
                for ref in req.get("source_refs") or []
                if ref.get("source_ref_type") == "clause"
            ),
            None,
        )
        if clause_id_value not in conditions_by_clause:
            continue
        req.setdefault("applicability", {})["conditions"] = [
            {
                "condition_type": condition_type,
                "condition_text_raw": condition_text,
                "source_refs": [source_ref("clause", source_clause_id)],
            }
            for condition_type, condition_text, source_clause_id in conditions_by_clause[clause_id_value]
        ]
    return data


def apply_wf_bonus_height_context(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "WF":
        return data
    structured = data.get("structured_data") or {}
    contextual_clause_ids = {
        "zone-wf-clause-34-4-2",
        "zone-wf-clause-34-4-3",
        "zone-wf-clause-34-4-3-b",
        "zone-wf-clause-34-4-5",
        "zone-wf-clause-34-4-6",
        "zone-wf-clause-34-4-7",
    }

    def sourced_from(req: dict[str, Any], clause_id_value: str) -> bool:
        return any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") == clause_id_value
            for ref in req.get("source_refs") or []
        )

    structured["other_requirements"] = [
        req
        for req in structured.get("other_requirements") or []
        if not any(sourced_from(req, clause_id_value) for clause_id_value in contextual_clause_ids)
    ]
    structured["numeric_values"] = [
        value
        for value in structured.get("numeric_values") or []
        if not any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") in contextual_clause_ids
            for ref in value.get("source_refs") or []
        )
    ]
    conditions_by_clause = {
        "zone-wf-clause-34-4-2-a-i": [
            ("building_height_range", "Massing for buildings up to 21.3 m (69.9 ft):", "zone-wf-clause-34-4-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-wf-clause-34-4-2-a"),
        ],
        "zone-wf-clause-34-4-2-a-ii": [
            ("building_height_range", "Massing for buildings up to 21.3 m (69.9 ft):", "zone-wf-clause-34-4-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-wf-clause-34-4-2-a"),
        ],
        "zone-wf-clause-34-4-2-a-iii": [
            ("building_height_range", "Massing for buildings up to 21.3 m (69.9 ft):", "zone-wf-clause-34-4-2"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-wf-clause-34-4-2-a"),
        ],
        "zone-wf-clause-34-4-3-a-i": [
            ("building_height_range", "Massing for Buildings greater than 21.3 m (69.9 ft):", "zone-wf-clause-34-4-3"),
            ("bonus_height_component", "The components above the base Building that are a bonus in Height shall be subject to:", "zone-wf-clause-34-4-3-a"),
        ],
        "zone-wf-clause-34-4-3-b-i": [
            ("building_height_range", "Massing for Buildings greater than 21.3 m (69.9 ft):", "zone-wf-clause-34-4-3"),
            ("building_portion", "The portion of the Building above 21.3 m (69.9 ft) shall have:", "zone-wf-clause-34-4-3-b"),
        ],
        "zone-wf-clause-34-4-3-b-ii": [
            ("building_height_range", "Massing for Buildings greater than 21.3 m (69.9 ft):", "zone-wf-clause-34-4-3"),
            ("building_portion", "The portion of the Building above 21.3 m (69.9 ft) shall have:", "zone-wf-clause-34-4-3-b"),
        ],
        "zone-wf-clause-34-4-3-b-iii": [
            ("building_height_range", "Massing for Buildings greater than 21.3 m (69.9 ft):", "zone-wf-clause-34-4-3"),
            ("building_portion", "The portion of the Building above 21.3 m (69.9 ft) shall have:", "zone-wf-clause-34-4-3-b"),
        ],
    }
    for req in structured.get("requirements") or []:
        clause_id_value = next(
            (
                ref.get("source_ref_id")
                for ref in req.get("source_refs") or []
                if ref.get("source_ref_type") == "clause"
            ),
            None,
        )
        if clause_id_value not in conditions_by_clause:
            continue
        req.setdefault("applicability", {})["conditions"] = [
            {
                "condition_type": condition_type,
                "condition_text_raw": condition_text,
                "source_refs": [source_ref("clause", source_clause_id)],
            }
            for condition_type, condition_text, source_clause_id in conditions_by_clause[clause_id_value]
        ]
    return data


def apply_cda_development_concept_plan_context(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "CDA":
        return data
    structured = data.get("structured_data") or {}
    clause_id_value = "zone-cda-clause-44-3-2"
    requirement_id = "zone-cda-req-zone-cda-clause-44-3-2"
    numeric_id = "zone-cda-num-zone-cda-clause-44-3-2-1"
    text = (
        "A Lot that is less than 1.2 hectares (3 acres) and existed prior to the effective date of "
        "this by-law may submit a Development Concept Plan."
    )
    structured["numeric_values"] = [
        value
        for value in structured.get("numeric_values") or []
        if value.get("numeric_value_id") != numeric_id
    ]
    structured["numeric_values"].append(
        {
            "numeric_value_id": numeric_id,
            "value_raw": "1.2 hectares (3 acres)",
            "value": 1.2,
            "unit": "ha",
            "measure_type": "area",
            "comparator": "less_than",
            "alternative_values": [
                {
                    "value_raw": "3 acres",
                    "value": 3,
                    "unit": "acre",
                    "measure_type": "area",
                }
            ],
            "source_refs": [source_ref("clause", clause_id_value)],
            "confidence": "high",
        }
    )
    structured["other_requirements"] = [
        req
        for req in structured.get("other_requirements") or []
        if req.get("requirement_id") != requirement_id
    ]
    structured["requirements"] = [
        req
        for req in structured.get("requirements") or []
        if req.get("requirement_id") != requirement_id
    ]
    structured["requirements"].append(
        {
            "requirement_id": requirement_id,
            "requirement_type": "process_requirement",
            "requirement_category": "development_concept_plan_eligibility",
            "requirement_label_raw": "44.3.2",
            "requirement_text_raw": text,
            "applicability": {
                "conditions": [
                    {
                        "condition_type": "pre_existing_lot",
                        "condition_text_raw": "existed prior to the effective date of this by-law",
                        "source_refs": [source_ref("clause", clause_id_value)],
                    }
                ]
            },
            "numeric_value_refs": [numeric_id],
            "term_refs": [],
            "source_refs": [source_ref("clause", clause_id_value)],
            "confidence": "high",
        }
    )
    for group in structured.get("regulation_groups") or []:
        refs = group.setdefault("requirement_refs", [])
        if requirement_id not in refs:
            refs.append(requirement_id)
    return data


def apply_pz_land_use_buffer_context(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("document_metadata") or {}
    if metadata.get("zone_code") != "PZ":
        return data
    structured = data.get("structured_data") or {}
    numeric_ids = {
        "zone-pz-num-zone-pz-clause-37-2-2-1",
        "zone-pz-num-zone-pz-clause-37-2-4-1",
    }
    requirement_ids = (
        "zone-pz-req-zone-pz-clause-37-2-4",
        "zone-pz-req-zone-pz-clause-37-2-2",
    )
    structured["numeric_values"] = [
        value
        for value in structured.get("numeric_values") or []
        if value.get("numeric_value_id") not in numeric_ids
    ]
    structured["numeric_values"].extend(
        [
            {
                "numeric_value_id": "zone-pz-num-zone-pz-clause-37-2-2-1",
                "value_raw": "5m (16.4 ft)",
                "value": 5,
                "unit": "m",
                "measure_type": "length",
                "comparator": "at_least",
                "alternative_values": [
                    {
                        "value_raw": "16.4 ft",
                        "value": 16.4,
                        "unit": "ft",
                        "measure_type": "length",
                    }
                ],
                "source_refs": [source_ref("clause", "zone-pz-clause-37-2-2")],
                "confidence": "high",
            },
            {
                "numeric_value_id": "zone-pz-num-zone-pz-clause-37-2-4-1",
                "value_raw": "8m (26.2 ft)",
                "value": 8,
                "unit": "m",
                "measure_type": "length",
                "comparator": "exact",
                "alternative_values": [
                    {
                        "value_raw": "26.2 ft",
                        "value": 26.2,
                        "unit": "ft",
                        "measure_type": "length",
                    }
                ],
                "source_refs": [source_ref("clause", "zone-pz-clause-37-2-4")],
                "confidence": "high",
            },
        ]
    )
    structured["other_requirements"] = [
        req
        for req in structured.get("other_requirements") or []
        if req.get("requirement_id") not in requirement_ids
    ]
    structured["requirements"] = [
        req
        for req in structured.get("requirements") or []
        if req.get("requirement_id") not in requirement_ids
    ]
    structured["requirements"].extend(
        [
            {
                "requirement_id": "zone-pz-req-zone-pz-clause-37-2-2",
                "requirement_type": "dimensional_standard",
                "requirement_category": "land_use_buffer_width",
                "requirement_label_raw": "37.2.2",
                "requirement_text_raw": "Development within the Port Zone shall require a Land Use Buffer from adjacent Buildings of no less than 5m (16.4 ft) in width.",
                "applicability": {"conditions": []},
                "numeric_value_refs": ["zone-pz-num-zone-pz-clause-37-2-2-1"],
                "term_refs": [],
                "source_refs": [source_ref("clause", "zone-pz-clause-37-2-2")],
                "confidence": "high",
            },
            {
                "requirement_id": "zone-pz-req-zone-pz-clause-37-2-4",
                "requirement_type": "environmental_requirement",
                "requirement_category": "land_use_buffer_planting_frequency",
                "requirement_label_raw": "37.2.4",
                "requirement_text_raw": "The Land Use Buffer shall be planted with street trees and shrubs at a frequency of one tree for every 8m 26.2 ft) of length along the boundary line.",
                "applicability": {
                    "conditions": [
                        {
                            "condition_type": "source_typo_interpretation",
                            "condition_text_raw": "The source text `8m 26.2 ft)` is interpreted as `8m (26.2 ft)`.",
                            "source_refs": [source_ref("clause", "zone-pz-clause-37-2-4")],
                        }
                    ]
                },
                "numeric_value_refs": ["zone-pz-num-zone-pz-clause-37-2-4-1"],
                "term_refs": [],
                "source_refs": [source_ref("clause", "zone-pz-clause-37-2-4")],
                "confidence": "high",
            },
        ]
    )
    for group in structured.get("regulation_groups") or []:
        refs = group.setdefault("requirement_refs", [])
        for requirement_id in requirement_ids:
            if requirement_id not in refs:
                refs.append(requirement_id)
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
            "content_refs": [],
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
        rebuild_content_refs({"raw_data": {"sections_raw": [raw_section]}})
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


def area_unit_code(raw: str) -> str:
    normalized = clean_text(raw).lower().rstrip(".")
    if normalized in {"hectare", "hectares"}:
        return "ha"
    return unit_code(raw)


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
    if unit in {"storey", "bedroom", "building", "dwelling_unit", "unit", "parking_space", "seat", "room", "sign"}:
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


def measurement_source_text(text: str) -> str:
    return re.sub(
        r"\b[A-Za-z-]+\s+\((\d+(?:,\d{3})*(?:\.\d+)?)\)\s+(bedrooms?)\b",
        r"\1 \2",
        text,
        flags=re.IGNORECASE,
    )


GENERAL_PROVISIONS_COLUMN_REQUIREMENT_TABLES = {
    "doc-general-provisions-table-3-1-2",
    "doc-general-provisions-table-3-2-1",
    "doc-general-provisions-table-4-1-2-accessory-buildings",
    "doc-general-provisions-table-4-2-2-projecting-structures",
}

TABLE_DESCRIPTOR_COLUMNS_BY_TABLE = {
    "doc-general-provisions-table-3-2-1": {"structure", "yard_projection_permitted"},
    "doc-general-provisions-table-3-6-1": {"feature"},
    "doc-general-provisions-table-4-11-1-c": {"zone_designation"},
}


def row_cell_text(row: dict[str, Any], column_id: str) -> str:
    return next((cell.get("cell_text_raw") or "" for cell in row.get("cells_raw") or [] if cell.get("column_id") == column_id), "")


def is_reviewable_non_numeric_cell(table_id_value: str, cell_text: str) -> bool:
    normalized = cell_text.strip().lower()
    if normalized in {"n/a", "na"}:
        return False
    if table_id_value == "doc-general-provisions-table-3-6-1" and normalized in {"yes", "unlimited"}:
        return False
    return bool(cell_text)


def column_requirement_context(table_id_value: str, row: dict[str, Any], column_id: str, column_label: str, cell_text: str) -> str:
    if table_id_value == "doc-general-provisions-table-3-1-2":
        lot_area = row_cell_text(row, "lot_area")
        return clean_text(f"{column_label} Lot Area {lot_area} {cell_text}")
    if table_id_value == "doc-general-provisions-table-3-2-1":
        structure = row_cell_text(row, "structure")
        yards = row_cell_text(row, "yard_projection_permitted")
        return clean_text(f"{column_label} Structure {structure} Yard {yards} {cell_text}")
    if table_id_value == "doc-general-provisions-table-4-1-2-accessory-buildings":
        lot_area = row_cell_text(row, "lot_area")
        return clean_text(f"{column_label} Lot Area {lot_area} {cell_text}")
    if table_id_value == "doc-general-provisions-table-4-2-2-projecting-structures":
        structure = row_cell_text(row, "structure")
        yards = row_cell_text(row, "yard_projection_permitted")
        return clean_text(f"{column_label} Structure {structure} Yard {yards} {cell_text}")
    return clean_text(f"{column_label} {cell_text}")


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
        table_id_value = table.get("table_id", "")
        if cell["column_id"] in {"row_number", "row_label", "requirement", "condition"}:
            continue
        if cell["column_id"] in TABLE_DESCRIPTOR_COLUMNS_BY_TABLE.get(table_id_value, set()):
            continue
        if table_id_value in GENERAL_PROVISIONS_COLUMN_REQUIREMENT_TABLES:
            if cell["column_id"] in {"accessory_buildings_permitted"}:
                continue
            row_label = column.get("column_label_raw", "")
            condition_text = row_cell_text(row, "row_label")
            context_text = column_requirement_context(
                table_id_value,
                row,
                cell["column_id"],
                row_label,
                cell["cell_text_raw"],
            )
            source_text = measurement_source_text(cell["cell_text_raw"])
            matches = list(TABLE_MEASUREMENT_RE.finditer(source_text))
            records = grouped_numeric_records(
                matches,
                f"{prefix}-num-{slugify(row['row_id'])}-{slugify(cell['column_id'])}",
                context_text,
                source_text,
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
                            "applies_to_lot_contexts": [],
                            "conditions": [
                                {"condition_type": "table_row_label", "condition_text_raw": condition_text}
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
            elif is_reviewable_non_numeric_cell(table_id_value, cell["cell_text_raw"]):
                review_flags.append(
                    make_review_flag(
                        f"{prefix}-flag-unparsed-table-value-{slugify(cell['cell_id'])}",
                        "numeric_value_review",
                        f"Table cell value was preserved but not normalized: {cell['cell_text_raw']}",
                        [source_ref("table_cell", cell["cell_id"])],
                    )
                )
            continue
        row_label = next((c["cell_text_raw"] for c in row["cells_raw"] if c["column_id"] == "requirement"), "")
        condition_text = next((c["cell_text_raw"] for c in row["cells_raw"] if c["column_id"] == "condition"), "")
        context_text = clean_text(f"{row_label} {condition_text} {column.get('column_label_raw', '')} {cell['cell_text_raw']}")
        source_text = measurement_source_text(cell["cell_text_raw"])
        matches = list(TABLE_MEASUREMENT_RE.finditer(source_text))
        records = grouped_numeric_records(
            matches,
            f"{prefix}-num-{slugify(row['row_id'])}-{slugify(cell['column_id'])}",
            context_text,
            source_text,
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
        elif is_reviewable_non_numeric_cell(table_id_value, cell["cell_text_raw"]):
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


def is_document_reference_clause(text: str) -> bool:
    lowered = clean_text(text).lower()
    if is_zone_reference_clause(text):
        return True
    if referenced_zone_codes(text) and (
        "permitted in" in lowered
        or "subject to" in lowered
        or "excluding" in lowered
        or "zone" in lowered
        or "regulations" in lowered
    ):
        return True
    return any(
        phrase in lowered
        for phrase in (
            "environmental protection act",
            "regulations of the zone",
            "subject to the regulations therein",
            "subject to regulations therein",
            "approved by council",
        )
    )


def build_document_reference_structures(
    data: dict[str, Any],
    candidate_clause_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    prefix = ((data.get("raw_data") or {}).get("source_units") or [{}])[0].get("source_unit_id") or "document"
    document_ref_id = prefix.removesuffix("-source")
    clauses = raw_clause_lookup((data.get("raw_data") or {}).get("sections_raw") or [])
    terms = []
    relationships = []
    reference_clause_ids: set[str] = set()
    relationship_keys: set[tuple[str, str, str]] = set()
    for clause_id, clause in clauses.items():
        if clause_id not in candidate_clause_ids:
            continue
        raw_text = strip_list_punctuation(clause.get("clause_text_raw") or "")
        if not is_document_reference_clause(raw_text):
            continue
        target_zone_codes = referenced_zone_codes(raw_text)
        reference_clause_ids.add(clause_id)
        normalized_targets = "_".join(code_key(code) for code in target_zone_codes) or slugify(clause_id)
        terms.append(
            {
                "term_id": f"{prefix}-term-reference-{slugify(clause_id)}",
                "term_raw": raw_text,
                "term_normalized": f"document_reference_{normalized_targets}",
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
                        "source_ref": source_ref("document", document_ref_id),
                        "target_ref": source_ref("zone", target_zone_code),
                        "scope": "document_reference_clause",
                        "source_clause_ref": clause_id,
                        "join_behavior": "include_target_values" if relationship_type.startswith("inherits_") else "reference_only",
                        "confidence": "high",
                    }
                )
    return terms, relationships, reference_clause_ids


def apply_document_reference_model(data: dict[str, Any]) -> dict[str, Any]:
    structured = data.setdefault("structured_data", base_structured_data())
    candidate_clause_ids = {
        ref.get("source_ref_id")
        for term in structured.get("terms") or []
        if term.get("confidence") == "needs_review"
        for ref in term.get("source_refs") or []
        if ref.get("source_ref_type") == "clause"
    }
    candidate_clause_ids.update(
        ref.get("source_ref_id")
        for flag in data.get("review_flags") or []
        if flag.get("review_type") == "code_table_match_review"
        for ref in flag.get("source_refs") or []
        if ref.get("source_ref_type") == "clause"
    )
    candidate_clause_ids.discard(None)
    reference_terms, relationships, reference_clause_ids = build_document_reference_structures(data, candidate_clause_ids)
    structured["zone_relationships"] = [
        relationship
        for relationship in structured.get("zone_relationships") or []
        if relationship.get("scope") != "document_reference_clause"
    ]
    structured["cross_references"] = [
        relationship
        for relationship in structured.get("cross_references") or []
        if relationship.get("scope") != "document_reference_clause"
    ]
    if not reference_clause_ids:
        return data
    filtered_terms = []
    for term in structured.get("terms") or []:
        source_clause_ids = {
            ref.get("source_ref_id")
            for ref in term.get("source_refs") or []
            if ref.get("source_ref_type") == "clause"
        }
        if source_clause_ids and source_clause_ids <= reference_clause_ids:
            continue
        filtered_terms.append(term)
    existing_term_ids = {term["term_id"] for term in filtered_terms}
    for term in reference_terms:
        if term["term_id"] not in existing_term_ids:
            filtered_terms.append(term)
            existing_term_ids.add(term["term_id"])
    structured["terms"] = filtered_terms
    existing_relationship_ids = {
        relationship.get("relationship_id")
        for relationship in (structured.get("zone_relationships") or []) + (structured.get("cross_references") or [])
    }
    for relationship in relationships:
        if relationship["relationship_id"] not in existing_relationship_ids:
            structured["zone_relationships"].append(relationship)
            existing_relationship_ids.add(relationship["relationship_id"])
    data["review_flags"] = [
        flag
        for flag in data.get("review_flags") or []
        if not any(
            ref.get("source_ref_type") == "clause" and ref.get("source_ref_id") in reference_clause_ids
            for ref in flag.get("source_refs") or []
        )
    ]
    return data


def apply_zone_reference_model(data: dict[str, Any]) -> dict[str, Any]:
    if (data.get("document_metadata") or {}).get("document_type") != "zone":
        return apply_document_reference_model(data)
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
            repair_dc_bonus_height_section(data)
            repair_dms_bonus_height_section(data)
            repair_wf_bonus_height_section(data)
            repair_mur_mixed_density_section(data)
            repair_r3_lodging_houses_table(data)
            repair_r3_section_structure(data)
            repair_r3t_section_structure(data)
            reset_review_flags(data)
            refresh_schema_numeric_values(data)
            apply_dc_bonus_height_context(data)
            apply_dms_bonus_height_context(data)
            apply_wf_bonus_height_context(data)
            apply_cda_development_concept_plan_context(data)
            apply_pz_land_use_buffer_context(data)
            repair_reviewed_draft_zone_clause_text(data)
            promote_reviewed_draft_zone_requirements(data)
            write_json(path, apply_zone_reference_model(refresh_schema_terms(normalizer, strip_unreviewed_term_codes(data))))
            continue
        transformed = transform_zone(normalizer, data)
        rebuild_schema_tables_from_pdf(pdf_doc, transformed)
        repair_dc_bonus_height_section(transformed)
        repair_dms_bonus_height_section(transformed)
        repair_wf_bonus_height_section(transformed)
        repair_mur_mixed_density_section(transformed)
        repair_r3_lodging_houses_table(transformed)
        repair_r3_section_structure(transformed)
        repair_r3t_section_structure(transformed)
        refresh_schema_numeric_values(transformed)
        apply_dc_bonus_height_context(transformed)
        apply_dms_bonus_height_context(transformed)
        apply_wf_bonus_height_context(transformed)
        apply_cda_development_concept_plan_context(transformed)
        apply_pz_land_use_buffer_context(transformed)
        repair_reviewed_draft_zone_clause_text(transformed)
        promote_reviewed_draft_zone_requirements(transformed)
        write_json(path, transformed)

    for item in manifest.get("document_files", []):
        path = OUT / item["file"]
        if not path.exists():
            continue
        data = read_json(path)
        document_type = item.get("document_type") or (data.get("document_metadata") or {}).get("document_type")
        if {"raw_data", "structured_data", "review_flags"}.issubset(data):
            if document_type == "definitions":
                continue
            if document_type in {"general_provisions", "design_standards"}:
                filter_raw_sections_by_source_sections(data, item.get("source_sections"))
            rebuild_clause_refs(data)
            rebuild_schema_tables_from_pdf(pdf_doc, data)
            repair_general_provisions_tables(data)
            repair_charlottetown_draft_parking_sections(data)
            repair_general_provisions_sign_permit_hierarchy(data)
            repair_dc_bonus_height_section(data)
            repair_dms_bonus_height_section(data)
            repair_wf_bonus_height_section(data)
            repair_mur_mixed_density_section(data)
            repair_r3_lodging_houses_table(data)
            repair_r3_section_structure(data)
            repair_r3t_section_structure(data)
            reset_review_flags(data)
            refresh_schema_numeric_values(data)
            apply_general_provisions_sign_permit_numeric_context(data)
            apply_dc_bonus_height_context(data)
            apply_dms_bonus_height_context(data)
            apply_wf_bonus_height_context(data)
            apply_cda_development_concept_plan_context(data)
            apply_pz_land_use_buffer_context(data)
            promote_reviewed_draft_general_provisions_requirements(data)
            repair_reviewed_draft_general_provisions_clause_text(data)
            write_json(path, apply_zone_reference_model(refresh_schema_terms(normalizer, strip_unreviewed_term_codes(data))))
            continue
        if document_type == "definitions":
            write_json(path, transform_definitions(normalizer, data))
        elif document_type in {"general_provisions", "design_standards"}:
            transformed = transform_sections_doc(
                normalizer,
                filter_legacy_sections_by_source_sections(data, item.get("source_sections")),
                document_type,
            )
            repair_general_provisions_tables(transformed)
            repair_charlottetown_draft_parking_sections(transformed)
            repair_general_provisions_sign_permit_hierarchy(transformed)
            reset_review_flags(transformed)
            refresh_schema_numeric_values(transformed)
            apply_general_provisions_sign_permit_numeric_context(transformed)
            promote_reviewed_draft_general_provisions_requirements(transformed)
            repair_reviewed_draft_general_provisions_clause_text(transformed)
            write_json(path, apply_zone_reference_model(refresh_schema_terms(normalizer, transformed)))

    for item in manifest.get("supporting_files", []):
        path = OUT / item["file"]
        if not path.exists():
            continue
        data = read_json(path)
        if {"raw_data", "structured_data", "review_flags"}.issubset(data):
            rebuild_clause_refs(data)
            rebuild_schema_tables_from_pdf(pdf_doc, data)
            repair_dc_bonus_height_section(data)
            repair_dms_bonus_height_section(data)
            repair_wf_bonus_height_section(data)
            repair_mur_mixed_density_section(data)
            repair_r3_lodging_houses_table(data)
            repair_r3_section_structure(data)
            repair_r3t_section_structure(data)
            reset_review_flags(data)
            refresh_schema_numeric_values(data)
            apply_dc_bonus_height_context(data)
            apply_dms_bonus_height_context(data)
            apply_wf_bonus_height_context(data)
            apply_cda_development_concept_plan_context(data)
            apply_pz_land_use_buffer_context(data)
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

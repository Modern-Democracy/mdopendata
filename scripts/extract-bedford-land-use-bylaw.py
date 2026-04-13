from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "bedford-land-use-bylaw.pdf"
OUTPUT_ROOT = ROOT / "data" / "zoning" / "bedford"

JURISDICTION = "Halifax Regional Municipality"
BYLAW_NAME = "Bedford Land Use By-law"
SOURCE_DOCUMENT_PATH = "docs/bedford-land-use-bylaw.pdf"

BYLAW_PAGE_RE = re.compile(r"Bedford Land Use By-law Page\s+(\d+)", re.IGNORECASE)
MAIN_DEFINITION_RE = re.compile(r"^(.+?)\s+-\s+(means|includes)\s+(.*)$", re.IGNORECASE)
FALLBACK_DEFINITION_RE = re.compile(r"^([A-Z][A-Za-z0-9/,'(). \-]+?)\s+(means|includes)\s+(.*)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^([A-Z]{0,4}-?\d+[A-Z]?(?:\.\d+)?)\.?\s+(.*)$")
SUBCLAUSE_RE = re.compile(r"^(?:\(([A-Za-z0-9.]+)\)|([A-Za-z0-9.]+))[\).]\s+(.*)$")
MAIN_ZONE_HEADER_RE = re.compile(r"PART\s+([0-9A-Z.]+):\s+(.+?)\s+(ZONE|DISTRICT)\b", re.IGNORECASE)
PART_RE = re.compile(r"^PART\s+([0-9A-Z.]+):\s*(.*)$", re.IGNORECASE)
SCHEDULE_RE = re.compile(r"^(SCHEDULE\s+[A-Z0-9-]+|Schedule\s+[A-Z0-9-]+)\s*:\s*(.*)$")
APPENDIX_RE = re.compile(r"^(APPENDIX\s+[A-Z0-9-]+|Appendix\s+[A-Z0-9-]+)\s*:\s*(.*)$")
PG_CHAPTER_RE = re.compile(r"^Part\s+[IVX]+,\s+Chapter\s+(\d+):\s+(.*)$", re.IGNORECASE)
PG_FOOTNOTE_RE = re.compile(r"^([①②③④⑤⑥⑦])\s+(.*)$")

PG_ZONE_ORDER = ["BW-CDD2", "BW-CDD1", "BW-CEN", "BW-HR2", "BW-HR1", "BW-LDR", "BW-CH", "BW-PCF", "BW-CON"]
PG_ZONE_LABELS = {
    "BW-CDD2": "Bedford West Comprehensive Development District 2",
    "BW-CDD1": "Bedford West Comprehensive Development District 1",
    "BW-CEN": "Bedford West Centre",
    "BW-HR2": "Bedford West Higher-Order Residential 2",
    "BW-HR1": "Bedford West Higher-Order Residential 1",
    "BW-LDR": "Bedford West Low-Density Residential",
    "BW-CH": "Bedford West Cluster Housing",
    "BW-PCF": "Bedford West Park and Community Facility",
    "BW-CON": "Bedford West Conservation",
}
PG_TABLE_SYMBOLS = set("①②③④⑤⑥⑦")


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return value.rstrip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def repair_split_uppercase_words(value: str) -> str:
    replacements = {
        "COMPREHENS IVE": "COMPREHENSIVE",
    }
    repaired = value
    for source, target in replacements.items():
        repaired = repaired.replace(source, target)
    return repaired


def normalize_clause_path(label: str) -> list[str] | None:
    cleaned = compact_space(label).replace(" ", "")
    match = re.fullmatch(r"([A-Z]{0,4}-?\d+[A-Z]?)(\([A-Za-z0-9.]+\))*", cleaned)
    if not match:
        return None
    root = re.match(r"^[A-Z]{0,4}-?\d+[A-Z]?", cleaned)
    if not root:
        return None
    path = [root.group(0)]
    roman_tokens = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
    for token in re.findall(r"\(([A-Za-z0-9.]+)\)", cleaned):
        if "." in token:
            return None
        if token in roman_tokens:
            path.append(token)
        elif re.fullmatch(r"[a-z]{2,}", token):
            path.extend(list(token))
        else:
            path.append(token)
    return path


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_pages() -> list[dict]:
    reader = PdfReader(str(SOURCE_PDF))
    pages: list[dict] = []
    for pdf_page, page in enumerate(reader.pages, start=1):
        text = normalize_line(page.extract_text() or "")
        layout_text = normalize_line(page.extract_text(extraction_mode="layout") or "")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        layout_lines = [line.rstrip() for line in layout_text.splitlines() if line.strip()]
        match = BYLAW_PAGE_RE.search(text)
        bylaw_page = int(match.group(1)) if match else None
        pages.append(
            {
                "pdf_page": pdf_page,
                "bylaw_page": bylaw_page,
                "text": text,
                "layout_text": layout_text,
                "lines": lines,
                "layout_lines": layout_lines,
            }
        )
    return pages


def page_index_for_bylaw_page(pages: list[dict], bylaw_page: int) -> int:
    for index, page in enumerate(pages):
        if page["bylaw_page"] == bylaw_page:
            return index
    raise ValueError(f"Missing bylaw page {bylaw_page}")


def is_heading_like(line: str) -> bool:
    cleaned = compact_space(line)
    if not cleaned:
        return False
    if cleaned.startswith("PG-"):
        return False
    letters = re.sub(r"[^A-Za-z]", "", cleaned)
    if len(letters) < 4:
        return False
    if cleaned.endswith(":"):
        return True
    return cleaned == cleaned.upper()


def body_lines(pages: list[dict], start: int, end: int, header_prefixes: tuple[str, ...] = ()) -> list[str]:
    collected: list[str] = []
    for page_offset, page in enumerate(pages[start : end + 1]):
        page_lines = list(page["lines"])
        if page_offset == 0 and header_prefixes:
            trimmed: list[str] = []
            skipping = True
            for line in page_lines:
                if skipping and (line.startswith(header_prefixes) or is_heading_like(line) or line == "ZONE"):
                    continue
                skipping = False
                trimmed.append(line)
            page_lines = trimmed
        for line in page_lines:
            if BYLAW_PAGE_RE.search(line):
                continue
            collected.append(line)
    return collected


def page_ranges_by_heading(
    pages: list[dict],
    start: int,
    end: int,
    matcher: re.Pattern[str],
    scan_lines: int = 12,
) -> list[tuple[int, int, re.Match[str]]]:
    starts: list[tuple[int, re.Match[str]]] = []
    for index in range(start, end + 1):
        scan = pages[index]["lines"][:scan_lines]
        match = None
        for line in scan:
            match = matcher.search(line)
            if match:
                break
        if match is None:
            joined = compact_space(" ".join(scan))
            match = matcher.search(joined)
        if match:
            starts.append((index, match))
    ranges: list[tuple[int, int, re.Match[str]]] = []
    for position, (index, match) in enumerate(starts):
        next_index = end
        if position + 1 < len(starts):
            next_index = starts[position + 1][0] - 1
        ranges.append((index, next_index, match))
    return ranges


def parse_definitions(pages: list[dict], start: int, end: int) -> list[dict]:
    rows: list[dict] = []
    current: dict | None = None
    for page in pages[start : end + 1]:
        for line in page["lines"]:
            if BYLAW_PAGE_RE.search(line) or line.startswith("PART "):
                continue
            match = MAIN_DEFINITION_RE.match(line) or FALLBACK_DEFINITION_RE.match(line)
            if match and len(match.group(1).split()) <= 18:
                if current is not None:
                    rows.append(current)
                current = {
                    "term_raw": compact_space(match.group(1).strip(" -")),
                    "text_parts": [f"{match.group(2).lower()} {match.group(3)}"],
                    "pdf_page_start": page["pdf_page"],
                    "pdf_page_end": page["pdf_page"],
                    "bylaw_page_start": page["bylaw_page"],
                    "bylaw_page_end": page["bylaw_page"],
                }
                continue
            if current is not None:
                current["text_parts"].append(line)
                current["pdf_page_end"] = page["pdf_page"]
                current["bylaw_page_end"] = page["bylaw_page"]
    if current is not None:
        rows.append(current)

    definitions = []
    for index, row in enumerate(rows, start=1):
        definition_text = compact_space(" ".join(row["text_parts"]))
        definitions.append(
            {
                "entry_index": index,
                "term_raw": row["term_raw"],
                "definition_text": definition_text,
                "status": "active",
                "definition_key": slugify(row["term_raw"]).replace("-", "_"),
                "citations": {
                    "pdf_page_start": row["pdf_page_start"],
                    "pdf_page_end": row["pdf_page_end"],
                    "bylaw_page_start": row["bylaw_page_start"],
                    "bylaw_page_end": row["bylaw_page_end"],
                },
            }
        )
    return definitions


def parse_numbered_sections(lines: list[str], citations: dict) -> tuple[list[dict], set[str]]:
    sections: list[dict] = []
    current: dict | None = None
    pending_review: set[str] = set()
    for line in lines:
        match = SECTION_RE.match(line)
        if match and not line.startswith("("):
            if current is not None:
                sections.append(current)
            current = {
                "section_label_raw": match.group(1),
                "title_label_raw": match.group(2),
                "text_parts": [match.group(2)],
                "provisions": [],
                "citations": dict(citations),
            }
            if normalize_clause_path(match.group(1)) is None:
                pending_review.add(match.group(1))
            continue
        if current is None:
            continue
        submatch = SUBCLAUSE_RE.match(line)
        if submatch:
            provision_label = submatch.group(1) or submatch.group(2)
            current["provisions"].append(
                {
                    "provision_label_raw": provision_label,
                    "text": compact_space(submatch.group(3)),
                    "status": "repealed" if "repealed" in submatch.group(3).lower() else "active",
                    "citations": dict(citations),
                }
            )
        else:
            current["text_parts"].append(line)
    if current is not None:
        sections.append(current)

    payload = []
    for order_index, section in enumerate(sections, start=1):
        section_text = compact_space(" ".join(section["text_parts"]))
        payload.append(
            {
                "order_index": order_index,
                "section_label_raw": section["section_label_raw"],
                "title_label_raw": section["title_label_raw"],
                "citations": section["citations"],
                "provisions": section["provisions"]
                or [
                    {
                        "provision_label_raw": section["section_label_raw"],
                        "text": section_text,
                        "status": "repealed" if "repealed" in section_text.lower() else "active",
                        "citations": section["citations"],
                    }
                ],
            }
        )
    return payload, pending_review


def infer_use_type(text: str) -> str:
    lowered = text.lower()
    if "accessory" in lowered:
        return "accessory_use"
    if any(token in lowered for token in ("dwelling", "suite", "housing", "bedroom rental")):
        return "residential_use"
    if any(token in lowered for token in ("school", "library", "hospital", "religious", "institution")):
        return "institutional_or_open_space_use"
    if any(token in lowered for token in ("park", "recreation", "playground", "club")):
        return "recreation_use"
    return "principal_use"


def split_zone_intro(lines: list[str]) -> tuple[list[dict], list[str]]:
    permitted: list[dict] = []
    remainder: list[str] = []
    in_permitted_block = False
    for line in lines:
        lowered = line.lower()
        if "following uses" in lowered:
            in_permitted_block = True
            remainder.append(line)
            continue
        if in_permitted_block and is_heading_like(line):
            in_permitted_block = False
        if in_permitted_block:
            match = SUBCLAUSE_RE.match(line)
            if match:
                label = match.group(1) or match.group(2)
                text = compact_space(match.group(3))
                permitted.append(
                    {
                        "clause_label_raw": label,
                        "clause_path": normalize_clause_path(f"0({label})"),
                        "use_type": infer_use_type(text),
                        "use_name": text.rstrip(";."),
                        "status": "repealed" if "repealed" in text.lower() else "active",
                    }
                )
                continue
        remainder.append(line)
    return permitted, remainder


def build_text_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    for line in lines:
        if BYLAW_PAGE_RE.search(line):
            continue
        if is_heading_like(line):
            if current is not None:
                blocks.append(current)
            current = {"heading_context_raw": compact_space(line), "text_parts": []}
            continue
        if current is None:
            current = {"heading_context_raw": None, "text_parts": []}
        current["text_parts"].append(line)
    if current is not None:
        blocks.append(current)

    payload = []
    for block in blocks:
        text = compact_space(" ".join(block["text_parts"]))
        if block["heading_context_raw"] is None and not text:
            continue
        payload.append({"heading_context_raw": block["heading_context_raw"], "text": text})
    return payload


def infer_zone_code_and_name(part_title: str) -> tuple[str, str]:
    repaired_title = repair_split_uppercase_words(part_title)
    all_codes = re.findall(r"\(([A-Z0-9-]+)\)", repaired_title)
    code = all_codes[-1] if all_codes else slugify(part_title).upper().replace("-", "_")
    if not all_codes:
        code = slugify(repaired_title).upper().replace("-", "_")
    zone_name = compact_space(re.sub(r"\([A-Z0-9-]+\)\s*$", "", repaired_title).strip(" -"))
    return code, zone_name


def build_main_zone_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict]:
    part_id = match.group(1)
    part_title = compact_space(match.group(2))
    zone_code, zone_name = infer_zone_code_and_name(part_title)
    lines = body_lines(pages, start, end, ("PART ",))
    permitted_uses, remainder = split_zone_intro(lines)
    citations = {
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }
    requirement_sections, pending_review = parse_numbered_sections(remainder, citations)
    text_blocks = build_text_blocks(remainder)
    payload = {
        "document_metadata": {
            "jurisdiction": JURISDICTION,
            "bylaw_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "zone_code": zone_code,
            "zone_name": zone_name,
            "part_label_raw": f"PART {part_id}",
        },
        "normalization_policy": {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": ["21(e)", "21(ea)", "21(ea)(1)"],
            "pending_review_clause_patterns": sorted(pending_review),
        },
        "permitted_uses": permitted_uses,
        "requirement_sections": requirement_sections,
        "content_blocks": text_blocks,
        "open_issues": (
            [
                {
                    "issue_type": "normalization_review",
                    "description": "Clause patterns listed in pending_review_clause_patterns were preserved raw because their hierarchy normalization is not yet approved in this repository context.",
                }
            ]
            if pending_review
            else []
        ),
        "citations": {"zone_section": citations},
    }
    return slugify(zone_code), payload


def build_appendix_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict, dict | None]:
    label = compact_space(match.group(1))
    title = compact_space(match.group(2)) or None
    text = compact_space(" ".join(body_lines(pages, start, end)))
    slug = slugify(label)
    metadata = {
        "jurisdiction": JURISDICTION,
        "bylaw_name": BYLAW_NAME,
        "source_document_path": SOURCE_DOCUMENT_PATH,
        "appendix_label_raw": label,
        "title_label_raw": title,
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }
    map_reference = None
    if len(text) < 240 or any(token in (title or "").lower() for token in ("zoning map", "wetlands", "archaeological", "boundaries")):
        feature_class = "site_specific_area"
        lowered = (title or "").lower()
        if "wetland" in lowered:
            feature_class = "wetland_area"
        elif "archaeological" in lowered:
            feature_class = "archaeological_constraint_area"
        map_reference = {
            "reference_type": "appendix_map",
            "source_label_raw": f"{label}: {title}" if title else label,
            "feature_key": slugify(f"{label} {title or ''}"),
            "feature_class": feature_class,
            "pdf_page_start": pages[start]["pdf_page"],
            "pdf_page_end": pages[end]["pdf_page"],
            "bylaw_page_start": pages[start]["bylaw_page"],
            "bylaw_page_end": pages[end]["bylaw_page"],
            "planned_postgis_target": "spatial_features.geom",
            "appendix_file": f"{slug}.json",
        }
    return slug, {"appendix_metadata": metadata, "content_text": text}, map_reference


def build_schedule_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict, dict | None]:
    label = compact_space(match.group(1))
    title = compact_space(match.group(2)) or None
    text = compact_space(" ".join(body_lines(pages, start, end)))
    line_count = sum(len(page["lines"]) for page in pages[start : end + 1])
    is_map_plate = len(text) < 220 or line_count < 12 or any(token in (title or "").lower() for token in ("zone boundaries", "precinct", "transportation reserve", "concept plan"))
    metadata = {
        "jurisdiction": JURISDICTION,
        "bylaw_name": BYLAW_NAME,
        "source_document_path": SOURCE_DOCUMENT_PATH,
        "schedule_label_raw": label,
        "title_label_raw": title,
        "document_type": "schedule_map_plate" if is_map_plate else "schedule_text",
        "status": "repealed" if "repealed" in text.lower() else "active",
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }
    slug = slugify(label)
    if is_map_plate:
        map_reference = {
            "reference_type": "schedule_map",
            "source_label_raw": f"{label}: {title}" if title else label,
            "feature_key": slugify(f"{label} {title or ''}"),
            "feature_class": "transportation_reserve" if "transportation reserve" in (title or "").lower() else "site_specific_area",
            "pdf_page_start": pages[start]["pdf_page"],
            "pdf_page_end": pages[end]["pdf_page"],
            "bylaw_page_start": pages[start]["bylaw_page"],
            "bylaw_page_end": pages[end]["bylaw_page"],
            "planned_postgis_target": "spatial_features.geom",
            "schedule_file": f"schedules/{slug}.json",
        }
        return slug, {"schedule_metadata": metadata, "map_reference": map_reference}, map_reference

    sections, pending_review = parse_numbered_sections(body_lines(pages, start, end), metadata)
    return (
        slug,
        {
            "schedule_metadata": metadata,
            "normalization_policy": {
                "clause_labels_preserved_raw": True,
                "approved_hierarchy_examples": ["21(e)", "21(ea)", "21(ea)(1)"],
                "pending_review_clause_patterns": sorted(pending_review),
            },
            "sections": sections,
            "content_text": text if not sections else None,
        },
        None,
    )


def parse_pg_footnotes(lines: list[str]) -> dict[str, str]:
    notes: dict[str, str] = {}
    current_symbol: str | None = None
    for line in lines:
        match = PG_FOOTNOTE_RE.match(compact_space(line))
        if match:
            current_symbol = match.group(1)
            notes[current_symbol] = match.group(2)
            continue
        if current_symbol is not None:
            notes[current_symbol] = compact_space(f"{notes[current_symbol]} {line}")
    return notes


def wrapped_label_pending(label: str) -> bool:
    lowered = label.lower()
    return (
        label.count("(") > label.count(")")
        or label.endswith(("-", "/", "("))
        or lowered.endswith((" of", " and", " or", " above", " within", " prohibited"))
    )


def should_merge_pending_label(previous: str, current: str) -> bool:
    return wrapped_label_pending(previous) or current[:1].islower()


def normalize_permission_symbols(symbols: list[str]) -> list[str]:
    normalized = []
    for symbol in symbols:
        normalized.append("permitted" if symbol == "\uf098" else symbol)
    return normalized


def parse_pg_table_rows(pages: list[dict], start: int, end: int) -> tuple[list[dict], dict[str, str]]:
    lines: list[str] = []
    for page in pages[start : end + 1]:
        lines.extend(page["layout_lines"])

    header_line = next(line for line in lines if "CDD2" in line and "PCF" in line and "CON" in line)
    column_starts = [match.start() for match in re.finditer(r"CDD2|CDD1|CEN|HR2|HR1|LDR|CH|PCF|CON", header_line)]
    label_end = column_starts[0]
    row_entries: list[dict] = []
    current_category: str | None = None
    pending_label: str | None = None
    last_entry: dict | None = None
    footnotes_start = next(index for index, line in enumerate(lines) if compact_space(line).startswith("① "))
    table_lines = lines[:footnotes_start]
    footnotes = parse_pg_footnotes(lines[footnotes_start:])

    for raw_line in table_lines:
        if "Table PG-1:" in raw_line or "Bedford Land Use By-law" in raw_line:
            continue
        if not raw_line.strip():
            continue
        label = compact_space(raw_line[:label_end].replace("\uf020", " ").strip())
        if "CDD2" in raw_line and "PCF" in raw_line and "CON" in raw_line:
            continue
        if label and label == label.upper() and label not in PG_ZONE_ORDER and "BW-" not in label:
            current_category = label
            pending_label = None
            last_entry = None
            continue
        cell_symbols: list[list[str]] = []
        for index, start_pos in enumerate(column_starts):
            end_pos = column_starts[index + 1] if index + 1 < len(column_starts) else len(raw_line)
            chunk = raw_line[start_pos:end_pos]
            symbols = [char for char in chunk if char in PG_TABLE_SYMBOLS]
            cell_symbols.append(symbols)
        has_symbols = any(symbols for symbols in cell_symbols)
        if label and has_symbols:
            full_label = label
            if pending_label and should_merge_pending_label(pending_label, label):
                full_label = compact_space(f"{pending_label} {label}")
            pending_label = None
            last_entry = {"category_raw": current_category, "use_name": full_label, "cells": cell_symbols}
            row_entries.append(last_entry)
            continue
        if label and not has_symbols:
            if pending_label and should_merge_pending_label(pending_label, label):
                pending_label = compact_space(f"{pending_label} {label}")
            elif wrapped_label_pending(label):
                pending_label = label
            else:
                pending_label = None
            continue
        if not label and has_symbols and pending_label:
            last_entry = {"category_raw": current_category, "use_name": pending_label, "cells": cell_symbols}
            row_entries.append(last_entry)
            pending_label = None
            continue
        if not label and has_symbols and last_entry is not None:
            last_entry["cells"] = [existing + extra for existing, extra in zip(last_entry["cells"], cell_symbols, strict=True)]
            continue

    return row_entries, footnotes


def build_pg_zone_payloads(pages: list[dict]) -> dict[str, dict]:
    row_entries, footnotes = parse_pg_table_rows(
        pages,
        page_index_for_bylaw_page(pages, 164),
        page_index_for_bylaw_page(pages, 166),
    )
    citations = {
        "pdf_page_start": pages[page_index_for_bylaw_page(pages, 161)]["pdf_page"],
        "pdf_page_end": pages[page_index_for_bylaw_page(pages, 166)]["pdf_page"],
        "bylaw_page_start": 161,
        "bylaw_page_end": 166,
    }
    zone_payloads: dict[str, dict] = {}
    for zone_code in PG_ZONE_ORDER:
        zone_payloads[zone_code] = {
            "document_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
                "zone_code": zone_code,
                "zone_name": PG_ZONE_LABELS[zone_code],
                "source_schedule": "Schedule PG: Planned Growth Schedule",
            },
            "normalization_policy": {
                "clause_labels_preserved_raw": True,
                "approved_hierarchy_examples": ["21(e)", "21(ea)", "21(ea)(1)"],
                "pending_review_clause_patterns": [],
            },
            "permitted_uses": [],
            "prohibitions": [],
            "zone_specific_requirements": [],
            "shared_requirement_references": [],
            "citations": {"permitted_uses_table": citations},
        }

    for row in row_entries:
        if row["category_raw"] == "PROHIBITED IN ALL ZONES":
            for zone_code in PG_ZONE_ORDER:
                zone_payloads[zone_code]["prohibitions"].append(
                    {
                        "summary": row["use_name"],
                        "source_category_raw": row["category_raw"],
                        "citations": citations,
                    }
                )
            continue
        for zone_code, symbols in zip(PG_ZONE_ORDER, row["cells"], strict=True):
            if not symbols:
                continue
            permission_symbols = normalize_permission_symbols(symbols)
            conditions = [footnotes[symbol] for symbol in symbols if symbol in footnotes]
            zone_payloads[zone_code]["permitted_uses"].append(
                {
                    "use_name": row["use_name"],
                    "use_type": infer_use_type(row["use_name"]),
                    "source_category_raw": row["category_raw"],
                    "permission_symbols": permission_symbols,
                    "conditions": conditions,
                    "status": "active",
                    "citations": citations,
                }
            )

    chapter_ranges = page_ranges_by_heading(
        pages,
        page_index_for_bylaw_page(pages, 188),
        page_index_for_bylaw_page(pages, 243),
        PG_CHAPTER_RE,
    )
    for start, end, match in chapter_ranges:
        chapter_title = compact_space(match.group(2))
        chapter_slug = slugify(chapter_title)
        chapter_lines = body_lines(pages, start, end)
        chapter_sections, pending_review = parse_numbered_sections(
            chapter_lines,
            {
                "pdf_page_start": pages[start]["pdf_page"],
                "pdf_page_end": pages[end]["pdf_page"],
                "bylaw_page_start": pages[start]["bylaw_page"],
                "bylaw_page_end": pages[end]["bylaw_page"],
            },
        )
        chapter_ref = {
            "chapter_title_raw": chapter_title,
            "chapter_slug": chapter_slug,
            "citations": {
                "pdf_page_start": pages[start]["pdf_page"],
                "pdf_page_end": pages[end]["pdf_page"],
                "bylaw_page_start": pages[start]["bylaw_page"],
                "bylaw_page_end": pages[end]["bylaw_page"],
            },
        }
        if "BW -CDD2" in chapter_title or "BW-CDD2" in chapter_title:
            target_zones = ["BW-CDD2"]
        elif "BW -CDD1" in chapter_title or "BW-CDD1" in chapter_title:
            target_zones = ["BW-CDD1"]
        elif "BW -CEN" in chapter_title or "BW-CEN" in chapter_title:
            target_zones = ["BW-CEN"]
        elif "BW -HR2 and BW-HR1" in chapter_title or "BW-HR2 and BW-HR1" in chapter_title:
            target_zones = ["BW-HR2", "BW-HR1"]
        elif "BW -LDR" in chapter_title or "BW-LDR" in chapter_title:
            target_zones = ["BW-LDR"]
        elif "BW -CH" in chapter_title or "BW-CH" in chapter_title:
            target_zones = ["BW-CH"]
        elif "BW -PCF" in chapter_title or "BW-PCF" in chapter_title:
            target_zones = ["BW-PCF"]
        elif "BW -CON" in chapter_title or "BW-CON" in chapter_title:
            target_zones = ["BW-CON"]
        else:
            target_zones = PG_ZONE_ORDER
        for zone_code in target_zones:
            zone_payloads[zone_code]["zone_specific_requirements"].append(
                {
                    "chapter_title_raw": chapter_title,
                    "sections": chapter_sections,
                    "pending_review_clause_patterns": sorted(pending_review),
                }
            )
            zone_payloads[zone_code]["shared_requirement_references"].append(chapter_ref)

    shared_ranges = page_ranges_by_heading(
        pages,
        page_index_for_bylaw_page(pages, 228),
        page_index_for_bylaw_page(pages, 302),
        PART_RE,
    )
    for start, end, match in shared_ranges:
        part_title = compact_space(match.group(2))
        if part_title.startswith("DEFINITIONS"):
            continue
        ref = {
            "part_label_raw": f"PART {match.group(1)}",
            "title_label_raw": part_title,
            "citations": {
                "pdf_page_start": pages[start]["pdf_page"],
                "pdf_page_end": pages[end]["pdf_page"],
                "bylaw_page_start": pages[start]["bylaw_page"],
                "bylaw_page_end": pages[end]["bylaw_page"],
            },
        }
        for zone_code in PG_ZONE_ORDER:
            zone_payloads[zone_code]["shared_requirement_references"].append(ref)
    return zone_payloads


def build_planned_growth_schedule_payload(pages: list[dict]) -> dict:
    part_ranges = page_ranges_by_heading(
        pages,
        page_index_for_bylaw_page(pages, 147),
        page_index_for_bylaw_page(pages, 325),
        PART_RE,
    )
    parts = []
    for start, end, match in part_ranges:
        parts.append(
            {
                "part_label_raw": f"PART {match.group(1)}",
                "title_label_raw": compact_space(match.group(2)),
                "pdf_page_start": pages[start]["pdf_page"],
                "pdf_page_end": pages[end]["pdf_page"],
                "bylaw_page_start": pages[start]["bylaw_page"],
                "bylaw_page_end": pages[end]["bylaw_page"],
            }
        )
    return {
        "document_metadata": {
            "jurisdiction": JURISDICTION,
            "bylaw_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "document_type": "planned_growth_schedule",
        },
        "parts": parts,
        "notes": [
            "Permitted uses for Bedford West zones were parsed from Table PG-1 using PDF layout extraction.",
            "Zone-specific built form chapters were attached to the corresponding Bedford West zone JSON files.",
        ],
    }


def main() -> None:
    pages = read_pages()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    (OUTPUT_ROOT / "zones").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "schedules").mkdir(parents=True, exist_ok=True)

    definitions_start = page_index_for_bylaw_page(pages, 2)
    definitions_end = page_index_for_bylaw_page(pages, 19)
    part5_start = page_index_for_bylaw_page(pages, 28)
    part5_end = page_index_for_bylaw_page(pages, 58)
    main_zone_start = page_index_for_bylaw_page(pages, 59)
    main_zone_end = page_index_for_bylaw_page(pages, 120)
    appendix_start = page_index_for_bylaw_page(pages, 121)
    appendix_g_end = page_index_for_bylaw_page(pages, 135)
    schedule_pg_page = page_index_for_bylaw_page(pages, 136)
    pg_appendix_start = page_index_for_bylaw_page(pages, 320)
    final_schedule_start = page_index_for_bylaw_page(pages, 328)

    write_json(
        OUTPUT_ROOT / "definitions.json",
        {
            "document_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
                "document_type": "definitions",
            },
            "source_section": {
                "section_range_raw": "Part 2",
                "title_label_raw": "DEFINITIONS",
                "pdf_page_start": pages[definitions_start]["pdf_page"],
                "pdf_page_end": pages[definitions_end]["pdf_page"],
                "bylaw_page_start": pages[definitions_start]["bylaw_page"],
                "bylaw_page_end": pages[definitions_end]["bylaw_page"],
            },
            "definitions": parse_definitions(pages, definitions_start, definitions_end),
        },
    )

    general_sections, pending_review = parse_numbered_sections(
        body_lines(pages, part5_start, part5_end, ("PART ",)),
        {
            "pdf_page_start": pages[part5_start]["pdf_page"],
            "pdf_page_end": pages[part5_end]["pdf_page"],
            "bylaw_page_start": pages[part5_start]["bylaw_page"],
            "bylaw_page_end": pages[part5_end]["bylaw_page"],
        },
    )
    write_json(
        OUTPUT_ROOT / "general-provisions.json",
        {
            "document_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
                "document_type": "general_provisions",
            },
            "source_section": {
                "section_range_raw": "Part 5",
                "title_label_raw": "GENERAL PROVISIONS FOR ALL ZONES",
                "pdf_page_start": pages[part5_start]["pdf_page"],
                "pdf_page_end": pages[part5_end]["pdf_page"],
                "bylaw_page_start": pages[part5_start]["bylaw_page"],
                "bylaw_page_end": pages[part5_end]["bylaw_page"],
            },
            "normalization_policy": {
                "clause_labels_preserved_raw": True,
                "normalized_paths_applied": False,
                "pending_review_clause_patterns": sorted(pending_review),
            },
            "sections": general_sections,
        },
    )

    maps: list[dict] = []
    main_zone_ranges = page_ranges_by_heading(pages, main_zone_start, main_zone_end, MAIN_ZONE_HEADER_RE)
    for start, end, match in main_zone_ranges:
        slug, payload = build_main_zone_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "zones" / f"{slug}.json", payload)

    for start, end, match in page_ranges_by_heading(pages, page_index_for_bylaw_page(pages, 84), page_index_for_bylaw_page(pages, 98), SCHEDULE_RE):
        slug, payload, map_reference = build_schedule_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "schedules" / f"{slug}.json", payload)
        if map_reference is not None:
            maps.append(map_reference)

    for start, end, match in page_ranges_by_heading(pages, appendix_start, appendix_g_end, APPENDIX_RE):
        slug, payload, map_reference = build_appendix_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / f"{slug}.json", payload)
        if map_reference is not None:
            maps.append(map_reference)

    write_json(
        OUTPUT_ROOT / "schedule-pg.json",
        {
            "schedule_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
                "schedule_label_raw": "SCHEDULE PG",
                "title_label_raw": "PLANNED GROWTH SCHEDULE",
                "document_type": "embedded_schedule_document",
                "pdf_page_start": pages[schedule_pg_page]["pdf_page"],
                "pdf_page_end": pages[schedule_pg_page]["pdf_page"],
                "bylaw_page_start": pages[schedule_pg_page]["bylaw_page"],
                "bylaw_page_end": pages[schedule_pg_page]["bylaw_page"],
            }
        },
    )

    write_json(OUTPUT_ROOT / "planned-growth-schedule.json", build_planned_growth_schedule_payload(pages))

    pg_zone_payloads = build_pg_zone_payloads(pages)
    for zone_code, payload in pg_zone_payloads.items():
        write_json(OUTPUT_ROOT / "zones" / f"{slugify(zone_code)}.json", payload)

    for start, end, match in page_ranges_by_heading(pages, pg_appendix_start, page_index_for_bylaw_page(pages, 325), APPENDIX_RE):
        slug, payload, map_reference = build_appendix_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / f"{slug}.json", payload)
        if map_reference is not None:
            maps.append(map_reference)

    for start, end, match in page_ranges_by_heading(pages, final_schedule_start, page_index_for_bylaw_page(pages, 334), SCHEDULE_RE):
        slug, payload, map_reference = build_schedule_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "schedules" / f"{slug}.json", payload)
        if map_reference is not None:
            maps.append(map_reference)

    write_json(
        OUTPUT_ROOT / "maps.json",
        {
            "document_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "references": maps,
        },
    )
    write_json(
        OUTPUT_ROOT / "spatial-features-needed.json",
        {
            "document_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "spatial_features_needed": [
                {
                    "feature_key": ref["feature_key"],
                    "feature_class": ref["feature_class"],
                    "source_type": "schedule_digitization",
                    "reason": f"Derived from {ref['source_label_raw']}.",
                }
                for ref in maps
            ],
        },
    )


if __name__ == "__main__":
    main()

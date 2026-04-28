from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover - environment guard
    fitz = None

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "charlottetown" / "charlottetown-zoning-bylaw-draft_2026-04-09.pdf"
OUT = ROOT / "data" / "zoning" / "charlottetown-draft"
ZONES_OUT = OUT / "zones"

APPROVED_HIERARCHY_EXAMPLES = [
    "21(e)",
    "21(ea)",
    "21(ea)(1)",
    "20(1)(a.1)",
]

ZONES = [
    {"part": 10, "code": "RN", "name": "Neighbourhood", "bylaw_start": 87},
    {"part": 11, "code": "RM", "name": "Medium Density Residential", "bylaw_start": 93},
    {"part": 12, "code": "RH", "name": "High Order Residential", "bylaw_start": 97},
    {"part": 13, "code": "DC", "name": "Downtown Core", "bylaw_start": 101},
    {"part": 14, "code": "DMS", "name": "Downtown Main Street", "bylaw_start": 105},
    {"part": 15, "code": "DMU", "name": "Downtown Mixed Use", "bylaw_start": 109},
    {"part": 16, "code": "DN", "name": "Downtown Neighbourhood", "bylaw_start": 113},
    {"part": 17, "code": "DW", "name": "Downtown Waterfront", "bylaw_start": 117},
    {"part": 18, "code": "BP", "name": "Business Park", "bylaw_start": 121},
    {"part": 19, "code": "AP", "name": "Airport Periphery", "bylaw_start": 127},
    {"part": 20, "code": "HI", "name": "Heavy Industrial", "bylaw_start": 131},
    {"part": 21, "code": "P", "name": "Port", "bylaw_start": 135},
    {"part": 22, "code": "GC", "name": "Growth Corridor", "bylaw_start": 137},
    {"part": 23, "code": "GN", "name": "Growth Node", "bylaw_start": 143},
    {"part": 24, "code": "I", "name": "Institutional", "bylaw_start": 149},
    {"part": 25, "code": "PPS", "name": "Parks & Public Spaces", "bylaw_start": 153},
    {"part": 26, "code": "POS", "name": "Privately-owned Open Spaces", "bylaw_start": 155},
    {"part": 27, "code": "C", "name": "Conservation", "bylaw_start": 157},
    {"part": 28, "code": "EG", "name": "Eastern Gateway", "bylaw_start": 159},
    {"part": 29, "code": "UE", "name": "Urban Expansion", "bylaw_start": 161},
]

PHASE4_BROAD_REVIEWED_ZONE_CODES = {
    "AP",
    "BP",
    "C",
    "DC",
    "DMS",
    "DMU",
    "DN",
    "DW",
    "EG",
    "GC",
    "GN",
    "HI",
    "I",
    "P",
    "POS",
    "PPS",
    "RH",
    "RM",
    "RN",
    "UE",
}

PHASE4_LAYOUT_REVIEWED_ZONE_CODES = {
    "RH",
    "RM",
    "RN",
}

SUPPORTING_PARTS = [
    {
        "part": 1,
        "slug": "administration",
        "document_type": "administration",
        "title": "Administration & Operation",
        "bylaw_start": 1,
        "bylaw_end": 4,
    },
    {
        "part": 2,
        "slug": "permit-applications-processes",
        "document_type": "permit_applications_processes",
        "title": "Permit Applications & Processes",
        "bylaw_start": 5,
        "bylaw_end": 16,
    },
    {
        "part": 3,
        "slug": "general-provisions-buildings-structures",
        "document_type": "general_provisions",
        "title": "General Provisions for Buildings & Structures",
        "bylaw_start": 17,
        "bylaw_end": 26,
    },
    {
        "part": 4,
        "slug": "general-provisions-land-use",
        "document_type": "general_provisions",
        "title": "General Provisions for Land Use",
        "bylaw_start": 27,
        "bylaw_end": 36,
    },
    {
        "part": 5,
        "slug": "general-provisions-lots-site-design",
        "document_type": "general_provisions",
        "title": "General Provisions for Lots & Site Design",
        "bylaw_start": 37,
        "bylaw_end": 42,
    },
    {
        "part": 6,
        "slug": "design-standards-500-lot-area",
        "document_type": "design_standards",
        "title": "Design Standards for 500 Lot Area",
        "bylaw_start": 43,
        "bylaw_end": 46,
    },
    {
        "part": 7,
        "slug": "general-provisions-subdividing-land",
        "document_type": "general_provisions",
        "title": "General Provisions Subdividing Land",
        "bylaw_start": 47,
        "bylaw_end": 60,
    },
    {
        "part": 8,
        "slug": "general-provisions-parking",
        "document_type": "general_provisions",
        "title": "General Provisions for Parking",
        "bylaw_start": 61,
        "bylaw_end": 70,
    },
    {
        "part": 9,
        "slug": "general-provisions-signage",
        "document_type": "general_provisions",
        "title": "General Provisions For Signage",
        "bylaw_start": 71,
        "bylaw_end": 86,
    },
]

PHASE4_BROAD_REVIEWED_SUPPORTING_SLUGS = {
    "administration",
    "design-standards-500-lot-area",
    "general-provisions-buildings-structures",
    "general-provisions-land-use",
    "general-provisions-lots-site-design",
    "general-provisions-parking",
    "general-provisions-signage",
    "general-provisions-subdividing-land",
    "permit-applications-processes",
}

SCHEDULES = [
    {
        "label": "Schedule A",
        "slug": "schedule-a-land-use-zoning-map",
        "title": "Land Use Zoning Map",
        "reference_type": "schedule_map",
        "feature_class": "zoning_map",
        "bylaw_start": 193,
        "bylaw_end": 193,
    },
    {
        "label": "Schedule B",
        "slug": "schedule-b-downtown-height-schedule",
        "title": "Downtown Height Schedule",
        "reference_type": "schedule_map",
        "feature_class": "height_schedule",
        "bylaw_start": 194,
        "bylaw_end": 194,
    },
    {
        "label": "Schedule C",
        "slug": "schedule-c-street-hierarchy-schedule",
        "title": "Street Hierarchy Schedule",
        "reference_type": "schedule_map",
        "feature_class": "street_hierarchy_schedule",
        "bylaw_start": 195,
        "bylaw_end": 195,
    },
    {
        "label": "Schedule D",
        "slug": "schedule-d-hillsborough-height-schedule",
        "title": "Hillsborough Height Schedule",
        "reference_type": "schedule_map",
        "feature_class": "height_schedule",
        "bylaw_start": 196,
        "bylaw_end": 196,
    },
]


def pdf_page_for_bylaw_page(bylaw_page: int) -> int:
    return bylaw_page + 4


def clean_text(text: str) -> str:
    replacements = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def is_noise_line(line: str, zone: dict) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped == "CITY OF CHARLOTTETOWN":
        return True
    if stripped.startswith("ZONING & DEVELOPMENT BYLAW"):
        return True
    if stripped.startswith("Draft in progress"):
        return True
    if stripped == "THIS PAGE HAS INTENTIONALLY BEEN LEFT BLANK":
        return True
    if re.fullmatch(r"\d+", stripped):
        return True
    if re.fullmatch(r"\d+\s+\|\s+.*", stripped):
        return True
    if stripped.endswith("| " + zone["name"].upper()):
        return True
    return False


def zone_pages(zone: dict, next_bylaw_start: int | None) -> tuple[int, int, int, int]:
    bylaw_start = zone["bylaw_start"]
    bylaw_end = (next_bylaw_start - 1) if next_bylaw_start else 162
    return pdf_page_for_bylaw_page(bylaw_start), pdf_page_for_bylaw_page(bylaw_end), bylaw_start, bylaw_end


def citation_for_range(bylaw_start: int, bylaw_end: int) -> dict:
    return {
        "pdf_page_start": pdf_page_for_bylaw_page(bylaw_start),
        "pdf_page_end": pdf_page_for_bylaw_page(bylaw_end),
        "bylaw_page_start": bylaw_start,
        "bylaw_page_end": bylaw_end,
    }


def extract_zone_lines(reader: PdfReader, zone: dict, next_bylaw_start: int | None) -> tuple[list[dict], str]:
    pdf_start, pdf_end, _, _ = zone_pages(zone, next_bylaw_start)
    page_texts = []
    for pdf_page in range(pdf_start, pdf_end + 1):
        lines = extract_clean_lines_for_page(reader, pdf_page)
        kept = [line for line in lines if not is_noise_line(line, zone)]
        page_texts.append({"pdf_page": pdf_page, "text": "\n".join(kept)})
    combined = "\n".join(page["text"] for page in page_texts if page["text"])
    return page_texts, combined


def extract_page_texts(reader: PdfReader, bylaw_start: int, bylaw_end: int) -> list[dict]:
    page_texts = []
    for bylaw_page in range(bylaw_start, bylaw_end + 1):
        pdf_page = pdf_page_for_bylaw_page(bylaw_page)
        lines = [line.strip() for line in extract_clean_lines_for_page(reader, pdf_page) if line.strip()]
        kept = []
        for line in lines:
            if line == "CITY OF CHARLOTTETOWN":
                continue
            if line.startswith("ZONING & DEVELOPMENT BYLAW"):
                continue
            if line.startswith("Draft in progress"):
                continue
            if re.fullmatch(r"\d+", line):
                continue
            if re.fullmatch(r"\d+\s+\|\s+.*", line):
                continue
            kept.append(line)
        page_texts.append({"pdf_page": pdf_page, "bylaw_page": bylaw_page, "text": "\n".join(kept)})
    return page_texts


SECTION_OR_PROVISION_RE = re.compile(
    r"^(?:\d+\.\d+(?:\s|$)|\.\d+(?:\s|$)|\([a-z]{1,3}\)(?:\s|$)|[ivxlcdm]+\)(?:\s|$))",
    re.IGNORECASE,
)


def _fitz_block_rows(pdf_page: int) -> list[dict]:
    if fitz is None:
        return []
    doc = fitz.open(SOURCE)
    try:
        page = doc.load_page(pdf_page - 1)
        rows = []
        for block in page.get_text("blocks"):
            x0, y0, x1, y1, text, *_ = block
            cleaned = clean_text(text)
            if not cleaned:
                continue
            rows.append({"x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1), "text": cleaned})
        rows.sort(key=lambda row: (round(row["y0"], 1), round(row["x0"], 1)))
        return rows
    finally:
        doc.close()


def _is_structural_block(text: str) -> bool:
    first = (text.splitlines() or [""])[0].strip()
    if not first:
        return False
    if PART_RE.match(first) or ZONE_TITLE_RE.match(first):
        return True
    return bool(SECTION_OR_PROVISION_RE.match(first))


def _is_caption_block(text: str) -> bool:
    first = (text.splitlines() or [""])[0].strip()
    return bool(re.match(r"^(?:Table|Figure)\b", first, re.IGNORECASE))


def _is_short_fragment(text: str) -> bool:
    flat = " ".join(text.split())
    words = flat.split()
    return len(words) <= 12 and not re.search(r"[.;:]$", flat)


def _column_groups(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], bool]:
    midpoint = 306.0
    gutter = 24.0
    left = [row for row in rows if row["x1"] <= midpoint + gutter]
    right = [row for row in rows if row["x0"] >= midpoint - gutter]
    spanning = [row for row in rows if row not in left and row not in right]
    two_column = len(left) >= 4 and len(right) >= 4 and len(spanning) <= max(len(left), len(right))
    return (
        sorted(spanning, key=lambda row: (round(row["y0"], 1), round(row["x0"], 1))),
        sorted(left, key=lambda row: (round(row["y0"], 1), round(row["x0"], 1))),
        sorted(right, key=lambda row: (round(row["y0"], 1), round(row["x0"], 1))),
        two_column,
    )


def _filter_column_rows(rows: list[dict]) -> list[dict]:
    filtered = [row for row in rows if not _is_caption_block(row["text"]) and not row["text"].lstrip().startswith("*")]
    if not filtered:
        return []
    first_structural = next((idx for idx, row in enumerate(filtered) if _is_structural_block(row["text"])), None)
    if first_structural is None:
        return [row for row in filtered if not _is_short_fragment(row["text"])]
    leading = filtered[:first_structural]
    core = filtered[first_structural:]
    core = [
        *[row for row in leading if not _is_short_fragment(row["text"])],
        *core,
    ]
    last_structural = next((idx for idx in range(len(core) - 1, -1, -1) if _is_structural_block(core[idx]["text"])), None)
    if last_structural is None:
        return core
    trailing = core[last_structural + 1 :]
    return [
        *core[: last_structural + 1],
        *[row for row in trailing if not _is_short_fragment(row["text"])],
    ]


def _suppress_layout_artifacts(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    spanning, left, right, two_column = _column_groups(rows)
    spanning = _filter_column_rows(spanning)
    left = _filter_column_rows(left)
    right = _filter_column_rows(right)
    if not two_column:
        return sorted([*spanning, *left, *right], key=lambda row: (round(row["y0"], 1), round(row["x0"], 1)))
    return [*spanning, *left, *right]


def _merge_label_lines(lines: list[str], merge_wrapped_section_titles: bool = False) -> list[str]:
    merged: list[str] = []
    idx = 0
    while idx < len(lines):
        current = lines[idx].strip()
        if not current:
            idx += 1
            continue
        next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else None
        if next_line:
            if merge_wrapped_section_titles and re.fullmatch(r"\d+\.\d+(?:\s+[A-Z][A-Z0-9 '&/,\-]+)?", current):
                title_parts = [current]
                lookahead = idx + 1
                while lookahead < len(lines):
                    candidate = lines[lookahead].strip()
                    if not re.fullmatch(r"[A-Z][A-Z0-9 '&/,\-]+", candidate):
                        break
                    title_parts.append(candidate)
                    lookahead += 1
                if len(title_parts) > 1:
                    merged.append(" ".join(title_parts))
                    idx = lookahead
                    continue
            if re.fullmatch(r"\d+\.\d+", current) and re.fullmatch(r"[A-Z][A-Z0-9 '&/,\-]+", next_line):
                merged.append(f"{current} {next_line}")
                idx += 2
                continue
            if re.fullmatch(r"\.\d+", current) or re.fullmatch(r"\([a-z]{1,3}\)", current, re.IGNORECASE):
                merged.append(f"{current} {next_line}")
                idx += 2
                continue
        merged.append(current)
        idx += 1
    return merged


def extract_clean_lines_for_page(reader: PdfReader, pdf_page: int) -> list[str]:
    rows = _fitz_block_rows(pdf_page)
    if rows:
        if pdf_page in {7, 15, 19}:
            rows = [
                row
                for row in rows
                if not re.fullmatch(r"\d+\s+ZONING & DEVELOPMENT BYL AW.*", row["text"].replace("\n", " "))
                and not re.fullmatch(r"CIT Y OF CHARLOTTETOWN\s+\d+\s+\|.*", row["text"].replace("\n", " "))
            ]
            left = [row for row in rows if row["x0"] < 306.0]
            right = [row for row in rows if row["x0"] >= 306.0]
            ordered_rows = [
                *sorted(left, key=lambda row: (round(row["y0"], 1), round(row["x0"], 1))),
                *sorted(right, key=lambda row: (round(row["y0"], 1), round(row["x0"], 1))),
            ]
        else:
            ordered_rows = _suppress_layout_artifacts(rows)
        lines = []
        for row in ordered_rows:
            lines.extend(line.strip() for line in row["text"].splitlines() if line.strip())
        if lines:
            return _merge_label_lines(lines, merge_wrapped_section_titles=pdf_page in {7, 8, 9, 13, 15})
    text = clean_text(reader.pages[pdf_page - 1].extract_text() or "")
    return _merge_label_lines(
        [line.strip() for line in text.splitlines() if line.strip()],
        merge_wrapped_section_titles=pdf_page in {7, 8, 9, 13, 15},
    )


SECTION_RE = re.compile(r"^(?P<label>\d+\.\d+)\s+(?P<title>[A-Z][A-Z0-9 '&/,\-]+)$")
PART_RE = re.compile(r"^PART\s+\d+")
ZONE_TITLE_RE = re.compile(r"^[A-Z]{1,4}(?:-[A-Z]+)?\s+-\s+")
PROVISION_RE = re.compile(r"^(?P<label>\.\d+|\([a-z]{1,3}\)|[ivx]+\))\s*(?P<text>.*)$", re.IGNORECASE)


def split_sections(page_texts: list[dict], zone: dict, next_bylaw_start: int | None) -> tuple[list[dict], list[dict]]:
    sections: dict[str, dict] = {}
    current_label = None
    unassigned: list[str] = []

    for page in page_texts:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        first_heading_index = None
        first_heading = None
        for idx, line in enumerate(lines):
            match = SECTION_RE.match(line)
            if match:
                first_heading_index = idx
                first_heading = match
                break

        if first_heading_index and first_heading:
            leading = [
                line
                for line in lines[:first_heading_index]
                if not PART_RE.match(line) and not ZONE_TITLE_RE.match(line)
            ]
            if leading:
                if current_label is None:
                    unassigned.extend(leading)
                else:
                    sections.setdefault(
                        current_label,
                        {"section_label_raw": current_label, "title_label_raw": "", "lines": []},
                    )
                    sections[current_label]["lines"].extend(leading)

        for idx, line in enumerate(lines):
            if first_heading_index is not None and idx < first_heading_index:
                continue
            if PART_RE.match(line) or ZONE_TITLE_RE.match(line):
                continue
            match = SECTION_RE.match(line)
            if match:
                label = re.sub(r"\s+", "", match.group("label"))
                title = match.group("title").strip()
                current_label = label
                sections.setdefault(label, {"section_label_raw": label, "title_label_raw": title, "lines": []})
                if title and not sections[label]["title_label_raw"]:
                    sections[label]["title_label_raw"] = title
                continue
            if current_label is None:
                unassigned.append(line)
            else:
                sections[current_label]["lines"].append(line)

    def sort_key(item: dict) -> tuple[int, int]:
        left, right = item["section_label_raw"].split(".", 1)
        return int(left), int(right)

    ordered = sorted(sections.values(), key=sort_key)
    content_blocks = []
    if unassigned:
        if "bylaw_end" in zone:
            block_citation = citation_for_range(zone["bylaw_start"], zone["bylaw_end"])
        else:
            block_citation = citation_for_zone(zone, next_bylaw_start)
        content_blocks.append(
            {
                "heading_context_raw": f"PART {zone['part']} {zone['code']} - unassigned extracted text",
                "text": " ".join(unassigned),
                "citations": block_citation,
            }
        )
    return ordered, content_blocks


def section_page_lookup(page_texts: list[dict], section_label: str, section_title: str, zone: dict, next_bylaw_start: int | None) -> int:
    compact_label = section_label.replace(".", r"\s*\.\s*")
    pattern = re.compile(rf"^\s*{compact_label}\s+{re.escape(section_title)}\s*$", re.MULTILINE)
    for page in page_texts:
        if pattern.search(page["text"]):
            return page["pdf_page"]
    fallback = re.compile(rf"^\s*{compact_label}\b", re.MULTILINE)
    for page in page_texts:
        if fallback.search(page["text"]):
            return page["pdf_page"]
    return citation_for_zone(zone, next_bylaw_start)["pdf_page_start"]


def citation_for_zone(zone: dict, next_bylaw_start: int | None) -> dict:
    pdf_start, pdf_end, bylaw_start, bylaw_end = zone_pages(zone, next_bylaw_start)
    return {
        "pdf_page_start": pdf_start,
        "pdf_page_end": pdf_end,
        "bylaw_page_start": bylaw_start,
        "bylaw_page_end": bylaw_end,
    }


def citation_for_page(pdf_page: int) -> dict:
    bylaw_page = pdf_page - 4
    return {
        "pdf_page_start": pdf_page,
        "pdf_page_end": pdf_page,
        "bylaw_page_start": bylaw_page,
        "bylaw_page_end": bylaw_page,
    }


def source_section_for_part(part: dict) -> dict:
    citation = citation_for_range(part["bylaw_start"], part["bylaw_end"])
    return {
        "section_range_raw": f"PART {part['part']}",
        "title_label_raw": part["title"],
        **citation,
    }


def repair_supporting_part_section_assignments(part: dict, raw_sections: list[dict], content_blocks: list[dict]) -> None:
    """Apply targeted PDF text-order repairs for reviewed draft supporting parts."""
    if not content_blocks:
        return

    block_text = " ".join(clean_text(block.get("text")) for block in content_blocks)
    sections_by_label = {section.get("section_label_raw"): section for section in raw_sections}

    if part["slug"] == "general-provisions-buildings-structures":
        section = sections_by_label.get("3.1")
        if section and block_text.startswith("(d) Separation:"):
            section["lines"].extend(
                [
                    "(d) Separation: the minimum distance between any building on a lot shall be 2.4 m (8 ft).",
                    "(e) Accessory buildings are prohibited from containing a basement or any below grade construction.",
                    "(f) A boat house and/or boat dock may be built to the water's edge, subject to the regulations of the provincial Environmental Protection Act; and",
                    "(g) A toll booth or security booth may be erected at the entrance of any parking lot that exceeds 20 cars.",
                ]
            )
            content_blocks.clear()
        return

    if part["slug"] == "general-provisions-signage":
        section_9_1 = sections_by_label.get("9.1")
        section_9_2 = sections_by_label.get("9.2")
        if section_9_1 and section_9_2 and block_text.startswith("The purpose of this section is to regulate signage"):
            tail_lines = section_9_1.get("lines") or []
            if tail_lines:
                section_9_2.setdefault("lines", []).extend(tail_lines)
            section_9_1["lines"] = [block_text]
            content_blocks.clear()
        return

    if part["slug"] in {"general-provisions-lots-site-design", "design-standards-500-lot-area"}:
        header_footer = {
            "ZONING & DEVELOPMENT BYL AW General Provisions for Lots & Site Design |",
            "ZONING & DEVELOPMENT BYL AW Design Standards for 500 Lot Area |",
        }
        if block_text in header_footer:
            content_blocks.clear()


def parse_provisions(lines: list[str], citation: dict) -> tuple[list[dict], set[str]]:
    provisions = []
    pending_label = "section"
    pending_text: list[str] = []
    patterns: set[str] = set()

    def flush() -> None:
        nonlocal pending_label, pending_text
        text = " ".join(part.strip() for part in pending_text if part.strip()).strip()
        if text:
            provisions.append(
                {
                    "provision_label_raw": pending_label,
                    "text": text,
                    "status": "active",
                    "citations": citation,
                }
            )
        pending_text = []

    for line in lines:
        match = PROVISION_RE.match(line)
        if match:
            flush()
            pending_label = match.group("label")
            if pending_label.startswith("."):
                patterns.add("dot_numeric_provision_labels")
            elif pending_label.startswith("("):
                patterns.add("parenthesized_alpha_clause_labels")
            elif pending_label.endswith(")"):
                patterns.add("roman_numeral_trailing_parenthesis_clause_labels")
            pending_text = [match.group("text").strip()]
        else:
            pending_text.append(line)
    flush()
    return provisions, patterns


def extract_permitted_uses(section: dict, zone: dict, section_citation: dict) -> list[dict]:
    title = section["title_label_raw"] or ""
    if "PERMITTED USE" not in title:
        return []

    uses = []
    condition_text = None
    in_first_list = False
    site_plan = "SITE PLAN" in title
    for provision in section.get("provisions", []):
        label = provision["provision_label_raw"]
        text = provision["text"]
        if label == ".1":
            condition_text = text
            in_first_list = True
            if "following use" not in text.lower() and "uses permitted" not in text.lower():
                uses.append(
                    {
                        "clause_label_raw": label,
                        "use_type": "site_plan_approval_use" if site_plan else "permitted_use",
                        "use_name": text,
                        "status": "active",
                        "conditions": title,
                        "citations": provision.get("citations", section_citation),
                    }
                )
            continue
        if label.startswith(".") and label != ".1":
            in_first_list = False
            if title.endswith("AS OF RIGHT") and text:
                uses.append(
                    {
                        "clause_label_raw": label,
                        "use_type": "permitted_use",
                        "use_name": text,
                        "status": "active",
                        "conditions": title,
                        "citations": provision.get("citations", section_citation),
                    }
                )
            continue
        if in_first_list and label.startswith("("):
            uses.append(
                {
                    "clause_label_raw": label,
                    "use_type": "site_plan_approval_use" if site_plan else "permitted_use",
                    "use_name": text.rstrip(";"),
                    "status": "active",
                    "conditions": condition_text,
                    "citations": provision.get("citations", section_citation),
                }
            )
    return uses


REFERENCE_RE = re.compile(
    r"\b(?P<kind>Section|Sections|Schedule|Table|Part|Official Plan|Development Agreement)\s+"
    r"(?P<label>[A-Za-z0-9.\-]+)?",
    re.IGNORECASE,
)


def extract_shared_references(requirement_sections: list[dict]) -> list[dict]:
    references = []
    seen = set()
    for section in requirement_sections:
        for provision in section.get("provisions", []):
            text = provision.get("text", "")
            for match in REFERENCE_RE.finditer(text):
                kind = match.group("kind")
                label = (match.group("label") or "").strip()
                key = (kind.lower(), label, text)
                if key in seen:
                    continue
                seen.add(key)
                references.append(
                    {
                        "part_label_raw": label if kind.lower() == "part" else None,
                        "chapter_title_raw": None,
                        "chapter_slug": None,
                        "title_label_raw": f"{kind} {label}".strip(),
                        "citations": provision.get("citations", section.get("citations")),
                        "source_text": text,
                    }
                )
    return references


def build_supporting_part_doc(reader: PdfReader, part: dict) -> dict:
    page_texts = extract_page_texts(reader, part["bylaw_start"], part["bylaw_end"])
    raw_sections, content_blocks = split_sections(
        page_texts,
        {
            "part": part["part"],
            "code": part["slug"],
            "name": part["title"],
            "bylaw_start": part["bylaw_start"],
            "bylaw_end": part["bylaw_end"],
        },
        None,
    )
    repair_supporting_part_section_assignments(part, raw_sections, content_blocks)
    sections = []
    pending_patterns: set[str] = set()
    for index, section in enumerate(raw_sections, start=1):
        page = section_page_lookup(
            page_texts,
            section["section_label_raw"],
            section["title_label_raw"],
            {"bylaw_start": part["bylaw_start"]},
            None,
        )
        section_citation = citation_for_page(page)
        provisions, patterns = parse_provisions(section["lines"], section_citation)
        pending_patterns.update(patterns)
        sections.append(
            {
                "order_index": index,
                "section_label_raw": section["section_label_raw"],
                "title_label_raw": section["title_label_raw"],
                "citations": section_citation,
                "provisions": provisions,
            }
        )

    open_issues = []
    broad_reviewed = part["slug"] in PHASE4_BROAD_REVIEWED_SUPPORTING_SLUGS
    if not broad_reviewed:
        open_issues.append(
            {
                "issue_type": "extraction_review",
                "description": "PDF text order was extracted with pypdf; verify section order, column flow, and table layout before normalization.",
            }
        )
    if content_blocks:
        open_issues.append(
            {
                "issue_type": "section_assignment_review",
                "description": "Some extracted text was not safely assigned to a labeled section and is preserved in content_blocks.",
            }
        )
    if not broad_reviewed and any(re.search(r"\b(Table|Figure|Schedule)\b", page["text"]) for page in page_texts):
        open_issues.append(
            {
                "issue_type": "table_parsing_review",
                "description": "The source section contains table, figure, or schedule text. Values are preserved as extracted text and require source PDF layout review before normalization.",
            }
        )

    return {
        "document_metadata": {
            "jurisdiction": "City of Charlottetown",
            "bylaw_name": "Draft Zoning & Development Bylaw",
            "source_document_path": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf",
            "document_type": part["document_type"],
            "draft_date_raw": "April 7, 2026",
        },
        "source_section": source_section_for_part(part),
        "normalization_policy": {
            "clause_labels_preserved_raw": True,
            "normalized_paths_applied": False,
            "pending_review_clause_patterns": sorted(pending_patterns),
        },
        "sections": sections,
        "shared_requirement_references": extract_shared_references(sections),
        "content_blocks": content_blocks,
        "open_issues": open_issues,
    }


def definition_key(term: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", term.strip().lower()).strip("_")
    return re.sub(r"_+", "_", key)


def build_definitions_doc(reader: PdfReader) -> dict:
    bylaw_start = 163
    bylaw_end = 192
    page_texts = extract_page_texts(reader, bylaw_start, bylaw_end)
    raw_pages = []
    definitions = []
    candidate_re = re.compile(r"(?P<term>[A-Z][A-Za-z0-9 '&/(),\-]{1,90}?)\s+means\s+", re.MULTILINE)

    for page in page_texts:
        text = page["text"]
        raw_pages.append(
            {
                "heading_context_raw": "PART 30 DEFINITIONS",
                "text": text,
                "citations": citation_for_page(page["pdf_page"]),
            }
        )
        matches = list(candidate_re.finditer(text))
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            term = " ".join(match.group("term").split())
            definition_text = " ".join(text[start:end].split())
            if len(term) > 80 or len(definition_text) < 8:
                continue
            definitions.append(
                {
                    "entry_index": len(definitions) + 1,
                    "term_raw": term,
                    "definition_text": definition_text,
                    "status": "active",
                    "definition_key": definition_key(term),
                    "citations": citation_for_page(page["pdf_page"]),
                }
            )

    return {
        "document_metadata": {
            "jurisdiction": "City of Charlottetown",
            "bylaw_name": "Draft Zoning & Development Bylaw",
            "source_document_path": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf",
            "document_type": "definitions",
            "draft_date_raw": "April 7, 2026",
        },
        "source_section": {
            "section_range_raw": "PART 30",
            "title_label_raw": "DEFINITIONS",
            **citation_for_range(bylaw_start, bylaw_end),
        },
        "definitions": definitions,
        "content_blocks": raw_pages,
        "open_issues": [
            {
                "issue_type": "definition_parsing_review",
                "description": "Definitions were parsed from pypdf text using term-plus-means patterns and are also preserved by page in content_blocks for QA.",
            }
        ],
    }


def build_schedule_doc(reader: PdfReader, schedule: dict) -> dict:
    page_texts = extract_page_texts(reader, schedule["bylaw_start"], schedule["bylaw_end"])
    blocks = [
        {
            "heading_context_raw": f"{schedule['label']}: {schedule['title']}",
            "text": page["text"],
            "citations": citation_for_page(page["pdf_page"]),
        }
        for page in page_texts
    ]
    return {
        "document_metadata": {
            "jurisdiction": "City of Charlottetown",
            "bylaw_name": "Draft Zoning & Development Bylaw",
            "source_document_path": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf",
            "document_type": "schedule",
            "schedule_label_raw": schedule["label"],
            "draft_date_raw": "April 7, 2026",
        },
        "source_section": {
            "section_label_raw": schedule["label"],
            "title_label_raw": schedule["title"],
            **citation_for_range(schedule["bylaw_start"], schedule["bylaw_end"]),
        },
        "content_blocks": blocks,
        "open_issues": [
            {
                "issue_type": "spatial_extraction_review",
                "description": "Schedule map text was extracted from the PDF, but map geometry and cartographic symbols were not vectorized in this source JSON pass.",
            }
        ],
    }


def build_maps_doc() -> dict:
    references = []
    for schedule in SCHEDULES:
        citation = citation_for_range(schedule["bylaw_start"], schedule["bylaw_end"])
        references.append(
            {
                "reference_type": schedule["reference_type"],
                "source_label_raw": f"{schedule['label']}: {schedule['title']}",
                "feature_key": schedule["slug"],
                "feature_class": schedule["feature_class"],
                **citation,
                "planned_postgis_target": "spatial_features.geom",
                "schedule_file": f"schedules/{schedule['slug']}.json",
            }
        )
    return {
        "document_name": "Draft Zoning & Development Bylaw",
        "source_document_path": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf",
        "references": references,
    }


def build_zone_doc(reader: PdfReader, zone: dict, next_bylaw_start: int | None) -> dict:
    page_texts, text = extract_zone_lines(reader, zone, next_bylaw_start)
    raw_sections, content_blocks = split_sections(page_texts, zone, next_bylaw_start)
    zone_citation = citation_for_zone(zone, next_bylaw_start)
    requirement_sections = []
    permitted_uses = []
    pending_patterns: set[str] = set()
    open_issues = []
    broad_reviewed = zone["code"] in PHASE4_BROAD_REVIEWED_ZONE_CODES
    if not broad_reviewed:
        open_issues.append(
            {
                "issue_type": "extraction_review",
                "description": "PDF text order and figure/table text were extracted with pypdf; verify section order, column flow, and page layout before normalization.",
            }
        )

    for index, section in enumerate(raw_sections, start=1):
        page = section_page_lookup(page_texts, section["section_label_raw"], section["title_label_raw"], zone, next_bylaw_start)
        section_citation = citation_for_page(page)
        provisions, patterns = parse_provisions(section["lines"], section_citation)
        pending_patterns.update(patterns)
        req_section = {
            "order_index": index,
            "section_label_raw": section["section_label_raw"],
            "title_label_raw": section["title_label_raw"],
            "citations": section_citation,
            "provisions": provisions,
        }
        if any(re.search(r"\b(Table|Figure|Schedule)\b", line) for line in section["lines"]):
            req_section["layout_artifacts_present"] = True
        requirement_sections.append(req_section)
        permitted_uses.extend(extract_permitted_uses(req_section, zone, section_citation))

    if not broad_reviewed and re.search(r"\b(Table|Figure|Schedule)\b", text):
        open_issues.append(
            {
                "issue_type": "table_parsing_review",
                "description": "The zone contains table, figure, or schedule text. Values are preserved as extracted text and require source PDF layout review before normalization.",
            }
        )

    if content_blocks:
        open_issues.append(
            {
                "issue_type": "zone_boundary_review",
                "description": "Some extracted text was not safely assigned to a labeled section and is preserved in content_blocks.",
            }
        )

    if not permitted_uses:
        open_issues.append(
            {
                "issue_type": "permitted_use_extraction_review",
                "description": "No discrete permitted-use list items were detected by the extractor for this zone.",
            }
        )

    if zone["code"] in {"RN", "RM", "RH"} and zone["code"] not in PHASE4_LAYOUT_REVIEWED_ZONE_CODES:
        open_issues.append(
            {
                "issue_type": "layout_order_review",
                "description": "The source PDF places some dimensional and figure text before or beside related section headings in extracted text; verify provision assignment against the visual PDF.",
            }
        )

    return {
        "document_metadata": {
            "jurisdiction": "City of Charlottetown",
            "bylaw_name": "Draft Zoning & Development Bylaw",
            "source_document_path": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf",
            "zone_code": zone["code"],
            "zone_name": zone["name"],
            "part_label_raw": f"PART {zone['part']}",
            "chapter_heading_raw": f"PART {zone['part']} {zone['code']} - {zone['name']}",
            "draft_date_raw": "April 7, 2026",
        },
        "normalization_policy": {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": APPROVED_HIERARCHY_EXAMPLES,
            "pending_review_clause_patterns": sorted(pending_patterns),
        },
        "permitted_uses": permitted_uses,
        "requirement_sections": requirement_sections,
        "zone_specific_requirements": [],
        "shared_requirement_references": extract_shared_references(requirement_sections),
        "content_blocks": content_blocks,
        "open_issues": open_issues,
        "citations": {"zone_section": zone_citation},
    }


def write_readme(manifest: dict) -> None:
    readme = f"""# Charlottetown Draft Zoning & Development Bylaw extraction

Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`.

This folder contains a non-normalized source extraction for the City of Charlottetown draft Zoning & Development Bylaw dated April 7, 2026. The extraction is intended for a later normalization pass. It preserves raw provision labels, raw legal text, citations, and review issues.

## Organization

- `zones/*.json`: one file per zone or zoning district from Parts 10 through 29.
- Top-level supporting files: administration, permit applications, general provisions, design standards, definitions, and maps.
- `schedules/*.json`: one file per extracted schedule map from Schedules A-D.
- `source-manifest.json`: inventory of extracted zones, source pages, and known limits.
- `extraction-notes.md`: reproducibility notes and QA guidance.

## Extraction status

- Zone part scope: Parts 10-29, bylaw pages 87-162.
- Supporting part scope: Parts 1-9 and Part 30, plus Schedules A-D.
- Zone count: {manifest["zone_count"]}.
- PDF page numbers and visible bylaw page numbers are recorded separately.
- Dimensional requirements are preserved as text in `requirement_sections`. They are not normalized into database-ready dimensional records.
- Clause labels such as `.1`, `(a)`, and `i)` are preserved exactly as extracted and listed in `pending_review_clause_patterns` when encountered.

## Known limits

- PDF text order does not always match visual order around columns, tables, figures, and schedules.
- Table and figure labels are preserved for review and are not converted into normalized rows.
- Schedule maps are not spatially extracted in this source JSON pass.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")


def write_notes() -> None:
    notes = """# Charlottetown draft extraction notes

Extractor: `scripts/extract-charlottetown-draft-zoning-bylaw.py`.

Method:

- Uses `pypdf` text extraction against the draft PDF.
- Uses the table of contents page ranges to split zone parts.
- Uses the table of contents page ranges to split supporting Parts 1-9, Part 30, and Schedules A-D.
- Parses labeled sections such as `10.3 PERMITTED USES`.
- Parses raw provision labels that appear at line starts: `.1`, `(a)`, and roman labels such as `i)`.
- Extracts permitted uses only from sections whose titles contain `PERMITTED USE`.

QA checks recommended before normalization:

- Compare each zone's `requirement_sections` against the visual PDF where `table_parsing_review` or `layout_order_review` is present.
- Verify that table/figure text has not shifted between adjacent provisions.
- Verify unassigned text in `content_blocks` for RN, RM, and any other zone with `zone_boundary_review`.
- Confirm whether raw label patterns `.1`, `(a)`, and `i)` should be added to the approved hierarchy policy for this bylaw.
- Review definition entries against `definitions.json` content blocks before relying on term boundaries.
- Review schedule files against the PDF maps before any spatial normalization.
"""
    (OUT / "extraction-notes.md").write_text(notes, encoding="utf-8")


def main() -> None:
    reader = PdfReader(str(SOURCE))
    ZONES_OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "schedules").mkdir(parents=True, exist_ok=True)
    zone_entries = []
    for idx, zone in enumerate(ZONES):
        next_start = ZONES[idx + 1]["bylaw_start"] if idx + 1 < len(ZONES) else None
        doc = build_zone_doc(reader, zone, next_start)
        filename = zone["code"].lower().replace("/", "-") + ".json"
        (ZONES_OUT / filename).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        citation = doc["citations"]["zone_section"]
        zone_entries.append(
            {
                "part": zone["part"],
                "zone_code": zone["code"],
                "zone_name": zone["name"],
                "file": f"zones/{filename}",
                "pdf_page_start": citation["pdf_page_start"],
                "pdf_page_end": citation["pdf_page_end"],
                "bylaw_page_start": citation["bylaw_page_start"],
                "bylaw_page_end": citation["bylaw_page_end"],
                "permitted_use_count": len(doc["permitted_uses"]),
                "requirement_section_count": len(doc["requirement_sections"]),
            }
        )

    supporting_entries = []
    for part in SUPPORTING_PARTS:
        doc = build_supporting_part_doc(reader, part)
        filename = f"{part['slug']}.json"
        (OUT / filename).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        citation = doc["source_section"]
        supporting_entries.append(
            {
                "part": part["part"],
                "document_type": part["document_type"],
                "title": part["title"],
                "file": filename,
                "pdf_page_start": citation["pdf_page_start"],
                "pdf_page_end": citation["pdf_page_end"],
                "bylaw_page_start": citation["bylaw_page_start"],
                "bylaw_page_end": citation["bylaw_page_end"],
                "section_count": len(doc["sections"]),
            }
        )

    definitions_doc = build_definitions_doc(reader)
    (OUT / "definitions.json").write_text(json.dumps(definitions_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    supporting_entries.append(
        {
            "part": 30,
            "document_type": "definitions",
            "title": "DEFINITIONS",
            "file": "definitions.json",
            "pdf_page_start": definitions_doc["source_section"]["pdf_page_start"],
            "pdf_page_end": definitions_doc["source_section"]["pdf_page_end"],
            "bylaw_page_start": definitions_doc["source_section"]["bylaw_page_start"],
            "bylaw_page_end": definitions_doc["source_section"]["bylaw_page_end"],
            "definition_count": len(definitions_doc["definitions"]),
        }
    )

    schedule_entries = []
    for schedule in SCHEDULES:
        doc = build_schedule_doc(reader, schedule)
        filename = f"schedules/{schedule['slug']}.json"
        (OUT / filename).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        citation = doc["source_section"]
        schedule_entries.append(
            {
                "schedule_label_raw": schedule["label"],
                "title": schedule["title"],
                "file": filename,
                "pdf_page_start": citation["pdf_page_start"],
                "pdf_page_end": citation["pdf_page_end"],
                "bylaw_page_start": citation["bylaw_page_start"],
                "bylaw_page_end": citation["bylaw_page_end"],
            }
        )
    (OUT / "maps.json").write_text(json.dumps(build_maps_doc(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = {
        "source_document_path": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf",
        "extracted_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "extractor": "scripts/extract-charlottetown-draft-zoning-bylaw.py",
        "bylaw_name": "Draft Zoning & Development Bylaw",
        "jurisdiction": "City of Charlottetown",
        "draft_date_raw": "April 7, 2026",
        "source_page_count": len(reader.pages),
        "zone_count": len(zone_entries),
        "zones": zone_entries,
        "supporting_documents": supporting_entries,
        "schedules": schedule_entries,
        "known_limits": [
            "pypdf text order can differ from visual PDF order around columns, tables, figures, and schedules.",
            "Tables, figures, and dimensional requirements are preserved as source text and require QA before normalization.",
            "Schedule maps are not spatially extracted in this source JSON pass.",
        ],
    }
    (OUT / "source-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(manifest)
    write_notes()


if __name__ == "__main__":
    main()

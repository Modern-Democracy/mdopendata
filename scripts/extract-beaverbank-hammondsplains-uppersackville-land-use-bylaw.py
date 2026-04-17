from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "beaverbank-hammondsplains-uppersackville-land-use-bylaw.pdf"
OUTPUT_ROOT = ROOT / "data" / "zoning" / "beaverbank-hammondsplains-uppersackville"

JURISDICTION = "Halifax Regional Municipality"
BYLAW_NAME = "Land Use By-law for Beaver Bank, Hammonds Plains and Upper Sackville"
SOURCE_DOCUMENT_PATH = "docs/beaverbank-hammondsplains-uppersackville-land-use-bylaw.pdf"

BYLAW_PAGE_RE = re.compile(r"Beaver Bank, Hammonds Plains and Upper Sackville LUB Page\s+(\d+)", re.IGNORECASE)
DEFINITION_RE = re.compile(r"^([0-9]+(?:\.[0-9A-Z]+)*)\s+(.*)$")
SECTION_RE = re.compile(r"^([0-9]+[A-Z]?(?:\.[0-9A-Z]+)*)[\).]?\s+(.*)$")
SUBCLAUSE_RE = re.compile(r"^(?:\(([A-Za-z0-9.]+)\)|([A-Za-z0-9.]+)[\).])\s+(.*)$")
MAIN_ZONE_HEADER_RE = re.compile(r"^PART\s+([0-9A-Z]+):?\s*(.+?\bZONE(?:\s*\([^)]*\))?)$", re.IGNORECASE)
PART_RE = re.compile(r"^PART\s+([0-9A-Z]+):?\s*(.*)$", re.IGNORECASE)
SCHEDULE_RE = re.compile(r"^(SCHEDULE\s+[A-Z0-9-]+|Schedule\s+[A-Z0-9-]+)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^(APPENDIX\s+[A-Z0-9-]+|Appendix\s+[A-Z0-9-]+)\s*:\s*(.*)$", re.IGNORECASE)


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return value.rstrip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


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
    letters = re.sub(r"[^A-Za-z]", "", cleaned)
    if len(letters) < 4:
        return False
    if cleaned.endswith(":"):
        return True
    return cleaned == cleaned.upper()


def body_rows(
    pages: list[dict],
    start: int,
    end: int,
    header_prefixes: tuple[str, ...] = (),
    skip_heading_like_on_first_page: bool = True,
) -> list[tuple[dict, str]]:
    rows: list[tuple[dict, str]] = []
    for page_offset, page in enumerate(pages[start : end + 1]):
        page_lines = list(page["lines"])
        if page_offset == 0 and header_prefixes:
            trimmed: list[str] = []
            skipping = True
            for line in page_lines:
                if BYLAW_PAGE_RE.search(line):
                    continue
                if skipping and (
                    line.startswith(header_prefixes)
                    or (skip_heading_like_on_first_page and (is_heading_like(line) or line == "ZONE"))
                ):
                    continue
                skipping = False
                trimmed.append(line)
            page_lines = trimmed
        for line in page_lines:
            if BYLAW_PAGE_RE.search(line):
                continue
            rows.append((page, line))
    return rows


def page_ranges_by_heading(
    pages: list[dict],
    start: int,
    end: int,
    matcher: re.Pattern[str],
    scan_lines: int = 12,
) -> list[tuple[int, int, re.Match[str]]]:
    starts: list[tuple[int, re.Match[str]]] = []
    for index in range(start, end + 1):
        scan = [line for line in pages[index]["lines"][:scan_lines] if not BYLAW_PAGE_RE.search(line)]
        match = None
        for line in scan:
            match = matcher.search(line)
            if match:
                break
        if match is None:
            for line_count in range(2, len(scan) + 1):
                joined = compact_space(" ".join(scan[:line_count]))
                match = matcher.search(joined)
                if match:
                    break
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
    entries: list[dict] = []
    current: dict | None = None
    for page, line in body_rows(pages, start, end):
        if line.startswith("PART "):
            continue
        match = DEFINITION_RE.match(line)
        if match:
            if current is not None:
                entries.append(current)
            current = {
                "section_label_raw": match.group(1),
                "text_parts": [match.group(2)],
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
        entries.append(current)

    payload = []
    for index, entry in enumerate(entries, start=1):
        text = compact_space(" ".join(entry["text_parts"]))
        lowered = text.lower()
        split_index = lowered.find(" means ")
        marker = " means "
        if split_index == -1:
            split_index = lowered.find(" includes ")
            marker = " includes "
        if split_index == -1:
            term_raw = text
            definition_text = text
        else:
            term_raw = text[:split_index].strip(" -")
            definition_text = text[split_index + len(marker) :].strip()
        payload.append(
            {
                "entry_index": index,
                "section_label_raw": entry["section_label_raw"],
                "term_raw": term_raw,
                "definition_text": definition_text,
                "status": "deleted" if "deleted" in text.lower() else "active",
                "citations": {
                    "pdf_page_start": entry["pdf_page_start"],
                    "pdf_page_end": entry["pdf_page_end"],
                    "bylaw_page_start": entry["bylaw_page_start"],
                    "bylaw_page_end": entry["bylaw_page_end"],
                },
                "definition_key": slugify(term_raw).replace("-", "_"),
            }
        )
    return payload


def parse_numbered_sections(rows: list[tuple[dict, str]]) -> tuple[list[dict], set[str]]:
    sections: list[dict] = []
    current: dict | None = None
    pending_review: set[str] = set()
    for page, line in rows:
        match = SECTION_RE.match(line)
        if match and not line.startswith("("):
            label = match.group(1)
            if current is not None:
                sections.append(current)
            current = {
                "section_label_raw": label,
                "title_label_raw": compact_space(match.group(2)),
                "text_parts": [compact_space(match.group(2))],
                "provisions": [],
                "citations": {
                    "pdf_page_start": page["pdf_page"],
                    "pdf_page_end": page["pdf_page"],
                    "bylaw_page_start": page["bylaw_page"],
                    "bylaw_page_end": page["bylaw_page"],
                },
            }
            if normalize_clause_path(label) is None:
                pending_review.add(label)
            continue
        if current is None:
            continue
        submatch = SUBCLAUSE_RE.match(line)
        if submatch:
            provision_label = submatch.group(1) or submatch.group(2)
            text = compact_space(submatch.group(3))
            current["provisions"].append(
                {
                    "provision_label_raw": provision_label,
                    "clause_path": None,
                    "text": text,
                    "status": "deleted" if "deleted" in text.lower() else ("repealed" if "repealed" in text.lower() else "active"),
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
            )
        else:
            current["text_parts"].append(line)
        current["citations"]["pdf_page_end"] = page["pdf_page"]
        current["citations"]["bylaw_page_end"] = page["bylaw_page"]
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
                        "status": "deleted" if "deleted" in section_text.lower() else ("repealed" if "repealed" in section_text.lower() else "active"),
                        "citations": section["citations"],
                    }
                ],
            }
        )
    return payload, pending_review


def infer_use_type(text: str, source_category: str | None = None) -> str:
    lowered = text.lower()
    category = (source_category or "").lower()
    if "accessory" in lowered:
        return "accessory_use"
    if "open space" in category or "park" in lowered or "playground" in lowered or "recreation" in lowered:
        return "recreation_use"
    if "institutional" in category or "institutional" in lowered:
        return "institutional_or_open_space_use"
    if any(token in lowered for token in ("dwelling", "suite", "housing", "bedroom rental")):
        return "residential_use"
    return "principal_use"


def looks_like_category_header(line: str) -> bool:
    cleaned = compact_space(line).strip(":")
    lowered = cleaned.lower()
    if lowered in {
        "residential uses",
        "other uses",
        "existing uses",
        "resource uses",
        "open space uses",
        "institutional uses",
        "commercial uses",
    }:
        return True
    return False


def should_merge_use_line(previous: str, current: str) -> bool:
    previous_clean = compact_space(previous)
    current_clean = compact_space(current)
    if not previous_clean:
        return False
    if current_clean.startswith("("):
        return True
    if current_clean[:1].islower():
        return True
    if previous_clean.endswith(("-", "/", "(")):
        return True
    if current_clean[:1].isdigit():
        return True
    first_word = current_clean.split()[0]
    if first_word in {"Area", "Service", "Subject", "dwelling", "permitted", "services"}:
        return True
    return False


def split_zone_intro(rows: list[tuple[dict, str]]) -> tuple[list[dict], list[tuple[dict, str]]]:
    permitted: list[dict] = []
    remainder: list[tuple[dict, str]] = []
    in_permitted_block = False
    waiting_for_following_line = False
    current_use: dict | None = None
    current_category: str | None = None

    def flush_current_use() -> None:
        nonlocal current_use
        if current_use is None:
            return
        current_use["use_name"] = compact_space(" ".join(current_use.pop("text_parts"))).rstrip(";.")
        permitted.append(current_use)
        current_use = None

    for index, (page, line) in enumerate(rows):
        lowered = compact_space(line).lower()
        next_line = rows[index + 1][1] if index + 1 < len(rows) else None
        if "except for the following:" in lowered or "except for the following uses" in lowered:
            flush_current_use()
            waiting_for_following_line = False
            in_permitted_block = True
            remainder.append((page, line))
            continue
        if "except for the" in lowered or lowered.endswith("except for"):
            waiting_for_following_line = True
            remainder.append((page, line))
            continue
        if waiting_for_following_line and lowered in {"following:", "the following:"}:
            flush_current_use()
            waiting_for_following_line = False
            in_permitted_block = True
            remainder.append((page, line))
            continue
        waiting_for_following_line = False
        if in_permitted_block and SECTION_RE.match(line):
            flush_current_use()
            in_permitted_block = False
        if in_permitted_block:
            if looks_like_category_header(line) and not (
                lowered == "open space uses" and next_line is not None and SECTION_RE.match(next_line)
            ):
                flush_current_use()
                current_category = compact_space(line).strip(":")
                continue
            submatch = SUBCLAUSE_RE.match(line)
            if submatch:
                flush_current_use()
                label = submatch.group(1) or submatch.group(2)
                text = compact_space(submatch.group(3))
                current_use = {
                    "clause_label_raw": label,
                    "clause_path": normalize_clause_path(f"0({label})"),
                    "use_type": infer_use_type(text, current_category),
                    "text_parts": [text],
                    "status": "deleted" if "deleted" in text.lower() else ("repealed" if "repealed" in text.lower() else "active"),
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                    "source_category_raw": current_category,
                }
                continue
            if current_use is not None and should_merge_use_line(" ".join(current_use["text_parts"]), line):
                current_use["text_parts"].append(line)
                current_use["citations"]["pdf_page_end"] = page["pdf_page"]
                current_use["citations"]["bylaw_page_end"] = page["bylaw_page"]
                continue
            flush_current_use()
            text = compact_space(line)
            current_use = {
                "clause_label_raw": None,
                "clause_path": None,
                "use_type": infer_use_type(text, current_category),
                "text_parts": [text],
                "status": "deleted" if "deleted" in text.lower() else ("repealed" if "repealed" in text.lower() else "active"),
                "citations": {
                    "pdf_page_start": page["pdf_page"],
                    "pdf_page_end": page["pdf_page"],
                    "bylaw_page_start": page["bylaw_page"],
                    "bylaw_page_end": page["bylaw_page"],
                },
                "source_category_raw": current_category,
            }
            continue
        remainder.append((page, line))

    flush_current_use()
    return permitted, remainder


def build_text_blocks(rows: list[tuple[dict, str]]) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    for _page, line in rows:
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
    cleaned = compact_space(part_title)
    cleaned = re.sub(r"\s+\((?:RC|NWCC|HECC|Special|Task Force|Municipal Affairs)[^)]*\)\s*$", "", cleaned)
    if cleaned.upper().endswith("ZONE"):
        cleaned = cleaned[:-4].strip()
    cleaned = re.sub(r"^\([^)]*\)\s*", "", cleaned)

    match = re.match(r"^(?:\d{4}\s+)?([A-Z0-9-]+)\s+\((.*?)\)\s*(.*?)$", cleaned)
    if match:
        zone_code = match.group(1)
        zone_name = compact_space(" ".join(part for part in (match.group(2), match.group(3)) if part))
        return zone_code, zone_name

    match = re.match(r"^(.*?)\(([A-Z0-9-]+)\)$", cleaned)
    if match:
        zone_name = compact_space(match.group(1).strip(" -"))
        zone_code = match.group(2)
        return zone_code, zone_name

    all_codes = re.findall(r"\(([A-Z0-9-]+)\)", cleaned)
    if all_codes:
        zone_code = all_codes[-1]
        zone_name = compact_space(re.sub(r"\([A-Z0-9-]+\)\s*$", "", cleaned).strip(" -"))
        return zone_code, zone_name

    tokens = cleaned.split()
    zone_code = tokens[-1]
    zone_name = compact_space(" ".join(tokens[:-1])) if len(tokens) > 1 else cleaned
    return zone_code, zone_name


def build_zone_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict]:
    part_id = match.group(1)
    part_title = compact_space(match.group(2))
    zone_code, zone_name = infer_zone_code_and_name(part_title)
    rows = body_rows(pages, start, end, ("PART ",))
    permitted_uses, remainder = split_zone_intro(rows)
    requirement_sections, pending_review = parse_numbered_sections(remainder)
    citations = {
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }
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
        "content_blocks": build_text_blocks(remainder),
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
    text = compact_space(" ".join(line for _page, line in body_rows(pages, start, end)))
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
    return slug, {"appendix_metadata": metadata, "content_text": text}, None


def build_schedule_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict, dict | None]:
    label = compact_space(match.group(1))
    title = compact_space(match.group(2)) or None
    rows = body_rows(pages, start, end)
    text = compact_space(" ".join(line for _page, line in rows))
    sections, pending_review = parse_numbered_sections(rows)
    line_count = sum(len(page["lines"]) for page in pages[start : end + 1])
    lowered_title = (title or "").lower()
    is_map_plate = not sections and (
        len(text) < 220
        or line_count < 12
        or any(
        token in lowered_title for token in ("wetland", "archaeological", "wind energy", "flood elevation markers", "lands subject to provision", "special planning area")
        )
    )
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
            "feature_class": "wetland_area" if "wetland" in lowered_title else ("archaeological_constraint_area" if "archaeological" in lowered_title else "site_specific_area"),
            "pdf_page_start": pages[start]["pdf_page"],
            "pdf_page_end": pages[end]["pdf_page"],
            "bylaw_page_start": pages[start]["bylaw_page"],
            "bylaw_page_end": pages[end]["bylaw_page"],
            "planned_postgis_target": "spatial_features.geom",
            "schedule_file": f"schedules/{slug}.json",
        }
        return slug, {"schedule_metadata": metadata, "map_reference": map_reference}, map_reference

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


def write_sections_document(
    path: Path,
    *,
    document_type: str,
    section_range_raw: str,
    title_label_raw: str,
    pages: list[dict],
    start: int,
    end: int,
) -> None:
    sections, pending_review = parse_numbered_sections(
        body_rows(pages, start, end, ("PART ",), skip_heading_like_on_first_page=False)
    )
    write_json(
        path,
        {
            "document_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
                "document_type": document_type,
            },
            "source_section": {
                "section_range_raw": section_range_raw,
                "title_label_raw": title_label_raw,
                "pdf_page_start": pages[start]["pdf_page"],
                "pdf_page_end": pages[end]["pdf_page"],
                "bylaw_page_start": pages[start]["bylaw_page"],
                "bylaw_page_end": pages[end]["bylaw_page"],
            },
            "normalization_policy": {
                "clause_labels_preserved_raw": True,
                "normalized_paths_applied": False,
                "pending_review_clause_patterns": sorted(pending_review),
            },
            "sections": sections,
        },
    )


def main() -> None:
    pages = read_pages()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    (OUTPUT_ROOT / "zones").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "schedules").mkdir(parents=True, exist_ok=True)

    definitions_start = page_index_for_bylaw_page(pages, 1)
    definitions_end = page_index_for_bylaw_page(pages, 13)
    general_start = page_index_for_bylaw_page(pages, 19)
    general_end = page_index_for_bylaw_page(pages, 38)
    signs_start = page_index_for_bylaw_page(pages, 39)
    signs_end = page_index_for_bylaw_page(pages, 42)
    zones_start = page_index_for_bylaw_page(pages, 43)
    zones_end = page_index_for_bylaw_page(pages, 117)
    administration_start = page_index_for_bylaw_page(pages, 118)
    administration_end = page_index_for_bylaw_page(pages, 118)
    appendix_start = page_index_for_bylaw_page(pages, 119)
    appendix_end = page_index_for_bylaw_page(pages, 133)
    schedule_start = page_index_for_bylaw_page(pages, 134)
    schedule_end = page_index_for_bylaw_page(pages, 141)

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

    write_sections_document(
        OUTPUT_ROOT / "general-provisions.json",
        document_type="general_provisions",
        section_range_raw="Part 4",
        title_label_raw="GENERAL PROVISIONS FOR ALL ZONES",
        pages=pages,
        start=general_start,
        end=general_end,
    )
    write_sections_document(
        OUTPUT_ROOT / "signs.json",
        document_type="signs",
        section_range_raw="Part 5",
        title_label_raw="SIGNS",
        pages=pages,
        start=signs_start,
        end=signs_end,
    )
    write_sections_document(
        OUTPUT_ROOT / "administration.json",
        document_type="administration",
        section_range_raw="Part 27",
        title_label_raw="ADMINISTRATION",
        pages=pages,
        start=administration_start,
        end=administration_end,
    )

    maps: list[dict] = []
    for start, end, match in page_ranges_by_heading(pages, zones_start, zones_end, MAIN_ZONE_HEADER_RE):
        slug, payload = build_zone_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "zones" / f"{slug}.json", payload)

    for start, end, match in page_ranges_by_heading(pages, appendix_start, appendix_end, APPENDIX_RE):
        slug, payload, _map_reference = build_appendix_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / f"{slug}.json", payload)

    for start, end, match in page_ranges_by_heading(pages, schedule_start, schedule_end, SCHEDULE_RE):
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

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "cole-harbour-westphal-land-use-bylaw.pdf"
OUTPUT_ROOT = ROOT / "data" / "zoning" / "cole-harbour-westphal"

JURISDICTION = "Halifax Regional Municipality"
BYLAW_NAME = "Land Use By-law for Cole Harbour/Westphal"
SOURCE_DOCUMENT_PATH = "docs/cole-harbour-westphal-land-use-bylaw.pdf"

BYLAW_PAGE_RE = re.compile(r"Cole Harbour/Westphal Land Use By-law Page\s+(\d+)", re.IGNORECASE)
SECTION_RE = re.compile(r"^([0-9]+[A-Z]?(?:\.[0-9A-Z]+)*)\s+(.*)$")
SUBCLAUSE_RE = re.compile(r"^\(([A-Za-z0-9.]+)\)\s+(.*)$")
LIST_ITEM_RE = re.compile(r"^([A-Za-z0-9]+)[\).]\s+(.*)$")
DEFINITION_RE = re.compile(r"^(2\.\d+[A-Z]*)\s+(.*)$")
ZONE_PART_RE = re.compile(r"PART\s+([0-9A-Z]+):\s*([A-Z0-9-]+)\s+\((.*?)\)(?:\s+ZONE)?", re.IGNORECASE)
SCHEDULE_RE = re.compile(r"(Schedule\s+[A-Z0-9-]+|SCHEDULE\s+[A-Z0-9-]+)\s*:\s*(.*)$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"(Appendix\s+[A-Z0-9-\"']+|APPENDIX\s+[A-Z0-9-\"']+)\s*:\s*(.*)$", re.IGNORECASE)

USE_CATEGORY_TYPES = {
    "residential uses": "residential_use",
    "community uses": "institutional_or_open_space_use",
    "institutional uses": "institutional_or_open_space_use",
    "park uses": "recreation_use",
    "commercial uses": "principal_use",
    "other uses": "principal_use",
    "resource uses": "principal_use",
    "low-rise residential uses": "residential_use",
    "mid-rise residential uses": "residential_use",
}


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return value.rstrip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def normalize_zone_code(value: str) -> str:
    cleaned = compact_space(value).upper().replace(" ", "")
    replacements = {
        "R-LA": "R-1A",
        "R-L": "R-1",
        "I-L": "I-1",
        "P-L": "P-1",
    }
    return replacements.get(cleaned, cleaned)


def normalize_clause_path(label: str) -> list[str] | None:
    cleaned = compact_space(label).replace(" ", "")
    match = re.fullmatch(r"([0-9]+[A-Z]?)(\([A-Za-z0-9.]+\))*", cleaned)
    if not match:
        return None
    root = re.match(r"^[0-9]+[A-Z]?", cleaned)
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
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        match = BYLAW_PAGE_RE.search(text)
        bylaw_page = int(match.group(1)) if match else None
        pages.append({"pdf_page": pdf_page, "bylaw_page": bylaw_page, "text": text, "lines": lines})
    return pages


def page_index_for_bylaw_page(pages: list[dict], bylaw_page: int) -> int:
    for index, page in enumerate(pages):
        if page["bylaw_page"] == bylaw_page:
            return index
    raise ValueError(f"Missing bylaw page {bylaw_page}")


def citations_for_range(start_page: dict, end_page: dict) -> dict:
    return {
        "pdf_page_start": start_page["pdf_page"],
        "pdf_page_end": end_page["pdf_page"],
        "bylaw_page_start": start_page["bylaw_page"],
        "bylaw_page_end": end_page["bylaw_page"],
    }


def body_lines(pages: list[dict], start: int, end: int) -> list[tuple[dict, str]]:
    rows: list[tuple[dict, str]] = []
    for page in pages[start : end + 1]:
        for line in page["lines"]:
            if BYLAW_PAGE_RE.search(line):
                continue
            rows.append((page, line))
    return rows


def page_ranges_by_heading(
    pages: list[dict],
    start: int,
    end: int,
    matcher: re.Pattern[str],
    *,
    scan_lines: int = 6,
) -> list[tuple[int, int, re.Match[str]]]:
    starts: list[tuple[int, re.Match[str]]] = []
    for index in range(start, end + 1):
        lines = pages[index]["lines"][:scan_lines]
        match = None
        joined = compact_space(" ".join(lines))
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


def merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        cleaned = compact_space(line)
        if not cleaned:
            continue
        if not merged:
            merged.append(cleaned)
            continue
        prev = merged[-1]
        if (
            prev.endswith((",", ";", ":", "-", "("))
            or cleaned[:1].islower()
            or cleaned.startswith(("(", ")", "and ", "or "))
        ):
            merged[-1] = compact_space(prev + " " + cleaned)
        else:
            merged.append(cleaned)
    return merged


def parse_definitions(pages: list[dict], start: int, end: int) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for page, line in body_lines(pages, start, end):
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

    payload: list[dict] = []
    for index, entry in enumerate(entries, start=1):
        text = compact_space(" ".join(entry["text_parts"]))
        split_index = text.lower().find(" means ")
        marker = " means "
        if split_index == -1:
            split_index = text.lower().find(" includes ")
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
                "definition_key": slugify(term_raw).replace("-", "_"),
                "citations": {
                    "pdf_page_start": entry["pdf_page_start"],
                    "pdf_page_end": entry["pdf_page_end"],
                    "bylaw_page_start": entry["bylaw_page_start"],
                    "bylaw_page_end": entry["bylaw_page_end"],
                },
            }
        )
    return payload


def parse_sections(pages: list[dict], start: int, end: int) -> tuple[list[dict], set[str]]:
    sections: list[dict] = []
    current: dict | None = None
    pending_review: set[str] = set()
    for page, line in body_lines(pages, start, end):
        match = SECTION_RE.match(line)
        if match:
            label = match.group(1)
            if current is not None:
                sections.append(current)
            current = {
                "section_label_raw": label,
                "title_label_raw": match.group(2),
                "body_lines": [],
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
        current["body_lines"].append((page, line))
        current["citations"]["pdf_page_end"] = page["pdf_page"]
        current["citations"]["bylaw_page_end"] = page["bylaw_page"]
    if current is not None:
        sections.append(current)

    payload: list[dict] = []
    for index, section in enumerate(sections, start=1):
        provisions: list[dict] = []
        current_provision: dict | None = None
        for page, line in section["body_lines"]:
            submatch = SUBCLAUSE_RE.match(line)
            if submatch:
                if current_provision is not None:
                    provisions.append(current_provision)
                clause_label = submatch.group(1)
                current_provision = {
                    "provision_label_raw": clause_label,
                    "clause_path": normalize_clause_path(f"{section['section_label_raw']}({clause_label})"),
                    "text_parts": [submatch.group(2)],
                    "status": "deleted" if "deleted" in submatch.group(2).lower() else "active",
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
                continue
            if current_provision is not None:
                list_match = LIST_ITEM_RE.match(line)
                if list_match and current_provision["text_parts"]:
                    provisions.append(current_provision)
                    current_provision = {
                        "provision_label_raw": list_match.group(1),
                        "clause_path": None,
                        "text_parts": [list_match.group(2)],
                        "status": "deleted" if "deleted" in list_match.group(2).lower() else "active",
                        "citations": {
                            "pdf_page_start": page["pdf_page"],
                            "pdf_page_end": page["pdf_page"],
                            "bylaw_page_start": page["bylaw_page"],
                            "bylaw_page_end": page["bylaw_page"],
                        },
                    }
                    continue
                current_provision["text_parts"].append(line)
                current_provision["citations"]["pdf_page_end"] = page["pdf_page"]
                current_provision["citations"]["bylaw_page_end"] = page["bylaw_page"]
                continue
        if current_provision is not None:
            provisions.append(current_provision)

        if not provisions:
            text = compact_space(" ".join(line for _, line in section["body_lines"]))
            provisions = [
                {
                    "provision_label_raw": section["section_label_raw"],
                    "text": text,
                    "status": "deleted" if "deleted" in text.lower() else "active",
                    "citations": dict(section["citations"]),
                }
            ]
        else:
            for provision in provisions:
                provision["text"] = compact_space(" ".join(provision.pop("text_parts")))

        payload.append(
            {
                "order_index": index,
                "section_label_raw": section["section_label_raw"],
                "title_label_raw": section["title_label_raw"],
                "citations": section["citations"],
                "provisions": provisions,
            }
        )
    return payload, pending_review


def infer_use_type(text: str, category: str | None = None) -> str:
    lowered = text.lower()
    if category and category.lower() in USE_CATEGORY_TYPES:
        return USE_CATEGORY_TYPES[category.lower()]
    if "accessory" in lowered:
        return "accessory_use"
    if any(token in lowered for token in ("dwelling", "shared housing", "apartment", "townhouse", "rowhouse", "suite", "residential")):
        return "residential_use"
    if any(token in lowered for token in ("park", "playground", "recreation", "golf")):
        return "recreation_use"
    if any(token in lowered for token in ("school", "institution", "museum", "library", "day care", "daycare", "worship", "police", "fire")):
        return "institutional_or_open_space_use"
    return "principal_use"


def parse_permitted_uses(section: dict) -> list[dict]:
    items: list[dict] = []
    current_category: str | None = None
    current_scope: str | None = None
    current_text: str | None = None

    def flush_current() -> None:
        nonlocal current_text
        if not current_text:
            return
        lowered_current = current_text.lower()
        items.append(
            {
                "section_label_raw": section["section_label_raw"],
                "clause_label_raw": None,
                "clause_path": None,
                "use_type": infer_use_type(current_text, current_category),
                "use_name": current_text.rstrip(";."),
                "source_category_raw": current_category,
                "applicability_scope": current_scope,
                "status": "deleted" if "deleted" in lowered_current else "active",
                "citations": dict(section["citations"]),
            }
        )
        current_text = None

    for _, line in section["body_lines"]:
        line = compact_space(line)
        if not line:
            continue
        lowered = line.lower()
        if lowered in USE_CATEGORY_TYPES or lowered in {"commercial parking structures/lots (>20 motor vehicle spaces)"}:
            flush_current()
            current_category = line
            continue
        if lowered.startswith("within sub area "):
            flush_current()
            current_scope = line
            continue
        if lowered.startswith("no development permit shall"):
            continue
        if "except for the following:" in lowered:
            continue
        if lowered == "the following:":
            continue
        if line.endswith(":") and not lowered.startswith(("minimum ", "maximum ")):
            flush_current()
            current_category = line.rstrip(":")
            continue
        if current_text is None:
            current_text = line
            continue
        if current_text.endswith((".", ";")):
            flush_current()
            current_text = line
            continue
        if current_text.endswith(")") and ("(RC-" in current_text or "(CH" in current_text or "(HE" in current_text or "(MC-" in current_text):
            flush_current()
            current_text = line
            continue
        current_text = compact_space(current_text + " " + line)
    flush_current()
    return items


def build_zone_sections_payload(sections: list[dict]) -> list[dict]:
    payload: list[dict] = []
    for index, section in enumerate(sections, start=1):
        provisions = []
        merged = merge_wrapped_lines([line for _, line in section["body_lines"]])
        if merged:
            for provision_index, line in enumerate(merged, start=1):
                provisions.append(
                    {
                        "provision_label_raw": section["section_label_raw"] if len(merged) == 1 else str(provision_index),
                        "text": line,
                        "status": "deleted" if "deleted" in line.lower() else "active",
                        "citations": dict(section["citations"]),
                    }
                )
        else:
            provisions.append(
                {
                    "provision_label_raw": section["section_label_raw"],
                    "text": section["title_label_raw"],
                    "status": "deleted" if "deleted" in section["title_label_raw"].lower() else "active",
                    "citations": dict(section["citations"]),
                }
            )
        payload.append(
            {
                "order_index": index,
                "section_label_raw": section["section_label_raw"],
                "title_label_raw": section["title_label_raw"],
                "citations": dict(section["citations"]),
                "provisions": provisions,
            }
        )
    return payload


def build_zone_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict]:
    zone_code = normalize_zone_code(match.group(2))
    zone_name = compact_space(match.group(3))
    zone_sections, pending_review = parse_raw_zone_sections(pages, start, end)
    permitted_uses: list[dict] = []
    use_specific_standards: list[dict] = []
    for section in zone_sections:
        title = section["title_label_raw"].upper()
        is_mod_subarea_use_section = zone_code == "MOD" and re.fullmatch(r"15A\.1\.[123]", section["section_label_raw"])
        if "USES PERMITTED" in title or is_mod_subarea_use_section:
            section_permitted_uses = parse_permitted_uses(section)
            if is_mod_subarea_use_section:
                scope_match = re.search(r"Sub Area\s+([A-Z])", section["title_label_raw"], re.IGNORECASE)
                scope = f"Sub Area {scope_match.group(1)}" if scope_match else None
                for item in section_permitted_uses:
                    item["applicability_scope"] = scope
            permitted_uses.extend(section_permitted_uses)
            continue
        merged_text = compact_space(" ".join(merge_wrapped_lines([line for _, line in section["body_lines"]])))
        use_specific_standards.append(
            {
                "section_label_raw": section["section_label_raw"],
                "section_path": None,
                "summary": section["title_label_raw"],
                "conditions": [merged_text] if merged_text else [],
                "status": "deleted" if "deleted" in (section["title_label_raw"] + " " + merged_text).lower() else "active",
                "citations": dict(section["citations"]),
            }
        )
        if normalize_clause_path(section["section_label_raw"]) is None:
            pending_review.add(section["section_label_raw"])

    payload = {
        "document_metadata": {
            "jurisdiction": JURISDICTION,
            "bylaw_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "zone_code": zone_code,
            "zone_name": zone_name,
            "zone_section_start": {
                "title_label_raw": compact_space(" ".join(pages[start]["lines"][:3])),
                "pdf_page": pages[start]["pdf_page"],
                "bylaw_page": pages[start]["bylaw_page"],
            },
        },
        "normalization_policy": {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": ["21(e)", "21(ea)", "21(ea)(1)"],
            "pending_review_clause_patterns": sorted(pending_review),
        },
        "permitted_uses": permitted_uses,
        "prohibitions": [],
        "requirements": {},
        "sign_controls": [],
        "use_specific_standards": use_specific_standards,
        "sections": build_zone_sections_payload(zone_sections),
        "spatial_features_needed": [],
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
        "citations": {"zone_section": citations_for_range(pages[start], pages[end])},
    }
    return slugify(zone_code), payload


def parse_raw_zone_sections(pages: list[dict], start: int, end: int) -> tuple[list[dict], set[str]]:
    sections: list[dict] = []
    current: dict | None = None
    pending_review: set[str] = set()
    for page, line in body_lines(pages, start, end):
        if line.upper().startswith("PART "):
            continue
        match = SECTION_RE.match(line)
        if match:
            label = match.group(1)
            if current is not None:
                sections.append(current)
            current = {
                "section_label_raw": label,
                "title_label_raw": match.group(2),
                "body_lines": [],
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
        current["body_lines"].append((page, line))
        current["citations"]["pdf_page_end"] = page["pdf_page"]
        current["citations"]["bylaw_page_end"] = page["bylaw_page"]
    if current is not None:
        sections.append(current)
    return sections, pending_review


def build_map_reference(
    *,
    source_label_raw: str,
    title: str | None,
    slug: str,
    pages: list[dict],
    start: int,
    end: int,
) -> dict:
    display = title or source_label_raw
    lowered = display.lower()
    if "wetland" in lowered:
        feature_class = "wetland_area"
    elif "archaeological" in lowered:
        feature_class = "archaeological_constraint_area"
    elif "wind" in lowered:
        feature_class = "wind_energy_area"
    elif "bonus zoning" in lowered:
        feature_class = "bonus_zoning_area"
    elif "mod" in lowered or "sub area" in lowered:
        feature_class = "subarea_boundary"
    elif "zoning map" in lowered:
        feature_class = "zoning_boundary"
    else:
        feature_class = "site_specific_area"
    return {
        "reference_type": "schedule_map",
        "source_label_raw": f"{source_label_raw}: {title}" if title else source_label_raw,
        "feature_key": slugify(f"{source_label_raw} {display}"),
        "feature_class": feature_class,
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
        "planned_postgis_target": "spatial_features.geom",
        "schedule_file": f"schedules/{slug}.json",
    }


def build_schedule_payload(pages: list[dict], start: int, end: int, label: str, title: str | None) -> tuple[str, dict, dict]:
    slug = slugify(label)
    metadata = {
        "jurisdiction": JURISDICTION,
        "bylaw_name": BYLAW_NAME,
        "source_document_path": SOURCE_DOCUMENT_PATH,
        "schedule_label_raw": label,
        "title_label_raw": title,
        "document_type": "schedule_map_plate",
        "status": "active",
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }
    map_reference = build_map_reference(
        source_label_raw=label,
        title=title,
        slug=slug,
        pages=pages,
        start=start,
        end=end,
    )
    payload = {
        "schedule_metadata": metadata,
        "map_reference": {
            "source_label_raw": map_reference["source_label_raw"],
            "feature_key": map_reference["feature_key"],
            "feature_class": map_reference["feature_class"],
            "planned_postgis_target": "spatial_features.geom",
            "extraction_status": "map_plate_only",
        },
    }
    return slug, payload, map_reference


def build_appendix_payload(pages: list[dict], start: int, end: int, label: str, title: str) -> tuple[str, dict, dict | None]:
    slug = slugify(label.replace('"', ""))
    text = compact_space(" ".join(line for _, line in body_lines(pages, start, end)))
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
    if len(text) < 180:
        map_reference = build_map_reference(
            source_label_raw=label,
            title=title,
            slug=slug,
            pages=pages,
            start=start,
            end=end,
        )
        return (
            slug,
            {
                "appendix_metadata": metadata,
                "map_reference": {
                    "source_label_raw": map_reference["source_label_raw"],
                    "feature_key": map_reference["feature_key"],
                    "feature_class": map_reference["feature_class"],
                    "planned_postgis_target": "spatial_features.geom",
                    "extraction_status": "map_plate_only",
                },
            },
            map_reference,
        )
    return slug, {"appendix_metadata": metadata, "content_text": text}, None


def write_document_sections(path: Path, *, document_type: str, section_range_raw: str, title: str, pages: list[dict], start: int, end: int) -> None:
    sections, pending_review = parse_sections(pages, start, end)
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
                "title_label_raw": title,
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
    zones_start = page_index_for_bylaw_page(pages, 15)
    general_start = page_index_for_bylaw_page(pages, 20)
    signs_start = page_index_for_bylaw_page(pages, 44)
    first_zone_start = page_index_for_bylaw_page(pages, 47)
    administration_start = page_index_for_bylaw_page(pages, 110)
    appendix_a_start = page_index_for_bylaw_page(pages, 112)
    appendix_g_start = page_index_for_bylaw_page(pages, 120)
    schedule_a1_start = page_index_for_bylaw_page(pages, 128)

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
                "pdf_page_end": pages[zones_start - 1]["pdf_page"],
                "bylaw_page_start": pages[definitions_start]["bylaw_page"],
                "bylaw_page_end": pages[zones_start - 1]["bylaw_page"],
            },
            "definitions": parse_definitions(pages, definitions_start, zones_start - 1),
        },
    )

    write_document_sections(
        OUTPUT_ROOT / "general-provisions.json",
        document_type="general_provisions",
        section_range_raw="Part 4",
        title="GENERAL PROVISIONS FOR ALL ZONES",
        pages=pages,
        start=general_start,
        end=signs_start - 1,
    )
    write_document_sections(
        OUTPUT_ROOT / "signs.json",
        document_type="signs",
        section_range_raw="Part 5",
        title="SIGNS",
        pages=pages,
        start=signs_start,
        end=first_zone_start - 1,
    )
    write_document_sections(
        OUTPUT_ROOT / "administration.json",
        document_type="administration",
        section_range_raw="Part 25",
        title="ADMINISTRATION",
        pages=pages,
        start=administration_start,
        end=appendix_a_start - 1,
    )

    maps: list[dict] = []

    schedule_a_slug, schedule_a_payload, schedule_a_map = build_schedule_payload(
        pages,
        7,
        7,
        "SCHEDULE A",
        "Cole Harbour/Westphal Zoning Map",
    )
    write_json(OUTPUT_ROOT / "schedules" / f"{schedule_a_slug}.json", schedule_a_payload)
    maps.append(schedule_a_map)

    for start, end, match in page_ranges_by_heading(pages, first_zone_start, administration_start - 1, ZONE_PART_RE):
        slug, payload = build_zone_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "zones" / f"{slug}.json", payload)

    appendix_ranges = page_ranges_by_heading(pages, appendix_a_start, schedule_a1_start - 1, APPENDIX_RE)
    for start, end, match in appendix_ranges:
        label = compact_space(match.group(1).replace('"', ""))
        title = compact_space(match.group(2))
        slug, payload, map_reference = build_appendix_payload(pages, start, end, label, title)
        write_json(OUTPUT_ROOT / f"{slug}.json", payload)
        if map_reference is not None:
            maps.append(map_reference)

    schedule_ranges = page_ranges_by_heading(pages, schedule_a1_start, len(pages) - 1, SCHEDULE_RE)
    for start, end, match in schedule_ranges:
        label = compact_space(match.group(1))
        title = compact_space(match.group(2))
        slug, payload, map_reference = build_schedule_payload(pages, start, end, label, title)
        write_json(OUTPUT_ROOT / "schedules" / f"{slug}.json", payload)
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

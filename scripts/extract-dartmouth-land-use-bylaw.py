from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "dartmouth-land-use-bylaw.pdf"
OUTPUT_ROOT = ROOT / "data" / "zoning" / "dartmouth"


BYLAW_PAGE_RE = re.compile(r"Dartmouth Land Use By-law Page\s+(\d+)")
DEFINITION_RE = re.compile(r"^\(([A-Za-z0-9.]+)\)\s+(.*)$")
CLAUSE_RE = re.compile(r"^([0-9]+[A-Z]?(?:\s*\([A-Za-z0-9.]+\))*(?:\.[0-9]+)?)\.?\s+(.*)$")
SUBCLAUSE_RE = re.compile(r"^\(([A-Za-z0-9.]+)\)\s+(.*)$")
PART_RE = re.compile(r"PART\s+[A-Z0-9]+(?::)?\s+([A-Z0-9-]+)\s+\((.*?)\)\s+ZONE", re.IGNORECASE)
SCHEDULE_RE = re.compile(r"^(SCHEDULE\s+[A-Z0-9()\-]+)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^(Appendix\s+[A-Z0-9()\-]+)\s*:\s*(.*)$", re.IGNORECASE)


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    return value.replace("\u00a0", " ").rstrip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


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
            if re.fullmatch(r"(?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\.\d+", token):
                path.append(token)
                continue
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
    pages = []
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


def parse_definitions(pages: list[dict], start: int, end: int, section_label_raw: str) -> list[dict]:
    rows = []
    current = None
    for page in pages[start : end + 1]:
        for line in page["lines"]:
            match = DEFINITION_RE.match(line)
            if match:
                if current is not None:
                    rows.append(current)
                current = {
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
        rows.append(current)

    definitions = []
    for index, row in enumerate(rows, start=1):
        text = compact_space(" ".join(row["text_parts"]))
        marker = " means "
        split_index = text.lower().find(marker)
        if split_index == -1:
            marker = " includes "
            split_index = text.lower().find(marker)
        term_raw = text if split_index == -1 else text[:split_index].strip(" -")
        definition_text = text if split_index == -1 else text[split_index + 1 :].strip()
        definitions.append(
            {
                "entry_index": index,
                "section_label_raw": section_label_raw,
                "term_raw": term_raw,
                "definition_text": definition_text,
                "status": "active",
                "citations": {
                    "pdf_page_start": row["pdf_page_start"],
                    "pdf_page_end": row["pdf_page_end"],
                    "bylaw_page_start": row["bylaw_page_start"],
                    "bylaw_page_end": row["bylaw_page_end"],
                },
                "definition_key": slugify(term_raw).replace("-", "_"),
            }
        )
    return definitions


def parse_general_provisions(pages: list[dict], start: int, end: int) -> list[dict]:
    sections = []
    current = None
    for page in pages[start : end + 1]:
        for line in page["lines"]:
            match = CLAUSE_RE.match(line)
            if match and not line.startswith("("):
                if current is not None:
                    sections.append(current)
                current = {
                    "section_label_raw": match.group(1),
                    "text_parts": [match.group(2)],
                    "pdf_page_start": page["pdf_page"],
                    "pdf_page_end": page["pdf_page"],
                    "bylaw_page_start": page["bylaw_page"],
                    "bylaw_page_end": page["bylaw_page"],
                    "provisions": [],
                }
                continue
            if current is None:
                continue
            submatch = SUBCLAUSE_RE.match(line)
            if submatch:
                current["provisions"].append(
                    {
                        "provision_label_raw": submatch.group(1),
                        "text": submatch.group(2),
                        "status": "repealed" if "repealed" in submatch.group(2).lower() else "active",
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
            current["pdf_page_end"] = page["pdf_page"]
            current["bylaw_page_end"] = page["bylaw_page"]
    if current is not None:
        sections.append(current)

    payload = []
    for index, section in enumerate(sections, start=1):
        text = compact_space(" ".join(section["text_parts"]))
        payload.append(
            {
                "order_index": index,
                "section_label_raw": section["section_label_raw"],
                "title_label_raw": section["text_parts"][0] if section["text_parts"] else None,
                "citations": {
                    "pdf_page_start": section["pdf_page_start"],
                    "pdf_page_end": section["pdf_page_end"],
                    "bylaw_page_start": section["bylaw_page_start"],
                    "bylaw_page_end": section["bylaw_page_end"],
                },
                "provisions": section["provisions"]
                or [
                    {
                        "provision_label_raw": section["section_label_raw"],
                        "heading_context_raw": None,
                        "text": text,
                        "status": "repealed" if "repealed" in text.lower() else "active",
                        "citations": {
                            "pdf_page_start": section["pdf_page_start"],
                            "pdf_page_end": section["pdf_page_end"],
                            "bylaw_page_start": section["bylaw_page_start"],
                            "bylaw_page_end": section["bylaw_page_end"],
                        },
                    }
                ],
            }
        )
    return payload


def page_ranges_by_heading(pages: list[dict], start: int, end: int, matcher) -> list[tuple[int, int, re.Match[str]]]:
    starts: list[tuple[int, re.Match[str]]] = []
    for index in range(start, end + 1):
        match = None
        for line in pages[index]["lines"][:8]:
            match = matcher.match(line)
            if match:
                break
        if match is None:
            header = compact_space(" ".join(pages[index]["lines"][:8]))
            match = matcher.search(header)
        if match:
            starts.append((index, match))
    ranges = []
    for position, (index, match) in enumerate(starts):
        next_index = end
        if position + 1 < len(starts):
            next_index = starts[position + 1][0] - 1
        ranges.append((index, next_index, match))
    return ranges


def parse_subclauses(lines: list[str], parent_label: str, citation_page: dict) -> list[dict]:
    items = []
    current = None
    for line in lines:
        match = SUBCLAUSE_RE.match(line)
        if match:
            current = {
                "clause_label_raw": f"{parent_label}({match.group(1)})",
                "text_parts": [match.group(2)],
                "citations": {
                    "pdf_page_start": citation_page["pdf_page"],
                    "pdf_page_end": citation_page["pdf_page"],
                    "bylaw_page_start": citation_page["bylaw_page"],
                    "bylaw_page_end": citation_page["bylaw_page"],
                },
            }
            items.append(current)
            continue
        if current is not None:
            current["text_parts"].append(line)
    for item in items:
        item["text"] = compact_space(" ".join(item.pop("text_parts")))
        item["status"] = "repealed" if "repealed" in item["text"].lower() else "active"
        item["clause_path"] = normalize_clause_path(item["clause_label_raw"])
    return items


def infer_use_type(text: str) -> str:
    lowered = text.lower()
    if "accessory" in lowered:
        return "accessory_use"
    if any(token in lowered for token in ("dwelling", "shared housing", "apartment", "duplex")):
        return "residential_use"
    if any(token in lowered for token in ("school", "library", "museum", "worship")):
        return "institutional_or_open_space_use"
    if any(token in lowered for token in ("park", "playground", "golf", "club")):
        return "recreation_use"
    return "principal_use"


def build_zone_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict]:
    zone_code = match.group(1).upper()
    zone_name = compact_space(match.group(2))
    blocks = []
    current = None
    pending_review: set[str] = set()
    for page in pages[start : end + 1]:
        for line in page["lines"]:
            match_clause = CLAUSE_RE.match(line)
            if match_clause and not line.startswith("("):
                if current is not None:
                    blocks.append(current)
                current = {
                    "section_label_raw": match_clause.group(1),
                    "text_parts": [match_clause.group(2)],
                    "lines": [],
                    "page": page,
                    "pdf_page_end": page["pdf_page"],
                    "bylaw_page_end": page["bylaw_page"],
                }
                continue
            if current is None:
                continue
            current["lines"].append(line)
            current["text_parts"].append(line)
            current["pdf_page_end"] = page["pdf_page"]
            current["bylaw_page_end"] = page["bylaw_page"]
    if current is not None:
        blocks.append(current)

    permitted_uses = []
    prohibitions = []
    dimensional_controls = []
    other_requirements = []
    sign_controls = []
    use_specific_standards = []

    for block in blocks:
        label = block["section_label_raw"]
        text = compact_space(" ".join(block["text_parts"]))
        lowered = text.lower()
        section_path = normalize_clause_path(label)
        if section_path is None:
            pending_review.add(label)
        subclauses = parse_subclauses(block["lines"], label, block["page"])
        for entry in subclauses:
            if entry["clause_path"] is None:
                pending_review.add(entry["clause_label_raw"])

        if "following uses only shall be permitted" in lowered or "shall be permitted in" in lowered:
            for entry in subclauses or [{
                "clause_label_raw": label,
                "clause_path": section_path,
                "text": text,
                "status": "repealed" if "repealed" in lowered else "active",
                "citations": {
                    "pdf_page_start": block["page"]["pdf_page"],
                    "pdf_page_end": block["pdf_page_end"],
                    "bylaw_page_start": block["page"]["bylaw_page"],
                    "bylaw_page_end": block["bylaw_page_end"],
                },
            }]:
                permitted_uses.append(
                    {
                        "clause_label_raw": entry["clause_label_raw"],
                        "clause_path": entry.get("clause_path"),
                        "use_type": infer_use_type(entry["text"]),
                        "use_name": entry["text"].rstrip(";."),
                        "status": entry["status"],
                        "citations": entry["citations"],
                    }
                )
            continue

        if lowered.startswith("no ") or " shall not " in lowered or "no development" in lowered:
            prohibitions.append(
                {
                    "section_label_raw": label,
                    "section_path": section_path,
                    "rule_type": "development_prohibition" if "no development" in lowered else "use_prohibition",
                    "summary": text,
                    "citations": {
                        "pdf_page_start": block["page"]["pdf_page"],
                        "pdf_page_end": block["pdf_page_end"],
                        "bylaw_page_start": block["page"]["bylaw_page"],
                        "bylaw_page_end": block["bylaw_page_end"],
                    },
                }
            )
            continue

        if "sign" in lowered:
            sign_controls.append({"section_label_raw": label, "section_path": section_path, "text": text})
            continue

        if any(token in lowered for token in ("minimum", "maximum", "setback", "yard", "lot area", "lot frontage", "parking", "landscaping", "requirements")):
            target = dimensional_controls if any(token in lowered for token in ("minimum", "maximum", "setback", "yard", "lot area", "lot frontage")) else other_requirements
            for entry in subclauses or [{"clause_label_raw": label, "clause_path": section_path, "text": text, "status": "active", "citations": {"pdf_page_start": block["page"]["pdf_page"], "pdf_page_end": block["pdf_page_end"], "bylaw_page_start": block["page"]["bylaw_page"], "bylaw_page_end": block["bylaw_page_end"]}}]:
                target.append(
                    {
                        "section_label_raw": entry["clause_label_raw"],
                        "section_path": entry.get("clause_path"),
                        "rule_type": "other_requirement",
                        "text": entry["text"],
                        "status": entry["status"],
                        "citations": entry["citations"],
                    }
                )
            continue

        use_specific_standards.append(
            {
                "section_label_raw": label,
                "section_path": section_path,
                "text": text,
                "status": "repealed" if "repealed" in lowered else "active",
            }
        )

    payload = {
        "document_metadata": {
            "jurisdiction": "Halifax Regional Municipality",
            "bylaw_name": "Dartmouth Land Use By-law",
            "source_document_path": "docs/dartmouth-land-use-bylaw.pdf",
            "zone_code": zone_code,
            "zone_name": zone_name,
            "zone_section_start": {
                "title_label_raw": compact_space(" ".join(pages[start]["lines"][:2])),
                "pdf_page": pages[start]["pdf_page"],
                "bylaw_page": pages[start]["bylaw_page"],
            },
        },
        "normalization_policy": {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": ["21(e)", "21(ea)", "21(ea)(1)"],
            "pending_review_clause_patterns": sorted(pending_review),
        },
        "general_context": {
            "zone_class_reference": {"section_label_raw": "31", "summary": f"{zone_code} is an established class of use zone."},
            "general_boundary_rule_refs": ["30", "31"],
        },
        "permitted_uses": permitted_uses,
        "prohibitions": prohibitions,
        "requirements": {"dimensional_controls": dimensional_controls, "other_requirements": other_requirements},
        "sign_controls": sign_controls,
        "use_specific_standards": use_specific_standards,
        "spatial_features_needed": [],
        "open_issues": ([{"issue_type": "normalization_review", "description": "Clause patterns listed in pending_review_clause_patterns were preserved raw because their hierarchy normalization is not yet approved in this repository context."}] if pending_review else []),
        "citations": {"zone_section": {"pdf_page_start": pages[start]["pdf_page"], "pdf_page_end": pages[end]["pdf_page"], "bylaw_page_start": pages[start]["bylaw_page"], "bylaw_page_end": pages[end]["bylaw_page"]}},
    }
    if zone_code == "BCDD" and len(payload["permitted_uses"]) >= 8:
        reviewed_labels = [
            ("54(a)(i)", ["54", "a", "i"]),
            ("54(a)(ii)", ["54", "a", "ii"]),
            ("54(a)(ii.5)", ["54", "a", "ii.5"]),
            ("54(a)(iii)", ["54", "a", "iii"]),
            ("54(a)(iv)", ["54", "a", "iv"]),
            ("54(a)(v)", ["54", "a", "v"]),
            ("54(a)(vi)", ["54", "a", "vi"]),
            ("54(b)", ["54", "b"]),
        ]
        for entry, (label_raw, clause_path) in zip(payload["permitted_uses"], reviewed_labels, strict=False):
            entry["clause_label_raw"] = label_raw
            entry["clause_path"] = clause_path
        payload["normalization_policy"]["pending_review_clause_patterns"] = []
        payload["open_issues"] = []
    return slugify(zone_code), payload


def build_schedule_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict, dict | None]:
    label = match.group(1).upper()
    title = match.group(2).strip() or None
    text = compact_space(" ".join(line for page in pages[start : end + 1] for line in page["lines"]))
    line_count = sum(len(page["lines"]) for page in pages[start : end + 1])
    is_map_plate = len(text) < 220 or ("repealed" not in text.lower() and line_count < 10)
    slug = slugify(label)
    metadata = {
        "jurisdiction": "Halifax Regional Municipality",
        "bylaw_name": "Dartmouth Land Use By-law",
        "source_document_path": "docs/dartmouth-land-use-bylaw.pdf",
        "schedule_label_raw": label,
        "title_label_raw": title,
        "document_type": "schedule_map_plate" if is_map_plate else "schedule_text",
        "status": "repealed" if "repealed" in text.lower() else "active",
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }
    if is_map_plate:
        display = title or label
        map_reference = {
            "reference_type": "schedule_map",
            "source_label_raw": f"{label}: {display}" if title else label,
            "feature_key": slugify(f"{label} {display}"),
            "feature_class": "wetland_area" if "wetland" in display.lower() else ("archaeological_constraint_area" if "archaeological" in display.lower() else "site_specific_area"),
            "pdf_page_start": pages[start]["pdf_page"],
            "pdf_page_end": pages[end]["pdf_page"],
            "bylaw_page_start": pages[start]["bylaw_page"],
            "bylaw_page_end": pages[end]["bylaw_page"],
            "planned_postgis_target": "spatial_features.geom",
            "schedule_file": f"schedules/{slug}.json",
        }
        return slug, {
            "schedule_metadata": metadata,
            "map_reference": {
                "source_label_raw": map_reference["source_label_raw"],
                "feature_key": map_reference["feature_key"],
                "feature_class": map_reference["feature_class"],
                "planned_postgis_target": "spatial_features.geom",
                "extraction_status": "map_plate_only",
            },
        }, map_reference

    provisions = []
    current = None
    for page in pages[start : end + 1]:
        for line in page["lines"][1:]:
            clause = CLAUSE_RE.match(line)
            if clause:
                if current is not None:
                    provisions.append(current)
                current = {"provision_label_raw": clause.group(1), "text_parts": [clause.group(2)]}
                continue
            if current is not None:
                current["text_parts"].append(line)
    if current is not None:
        provisions.append(current)
    for provision in provisions:
        provision["text"] = compact_space(" ".join(provision.pop("text_parts")))
        provision["status"] = "repealed" if "repealed" in provision["text"].lower() else "active"
    return slug, {"schedule_metadata": metadata, "provisions": provisions}, None


def build_appendix_payload(pages: list[dict], start: int, end: int, match: re.Match[str]) -> tuple[str, dict]:
    label = match.group(1)
    title = match.group(2)
    return slugify(label), {
        "appendix_metadata": {
            "jurisdiction": "Halifax Regional Municipality",
            "bylaw_name": "Dartmouth Land Use By-law",
            "source_document_path": "docs/dartmouth-land-use-bylaw.pdf",
            "appendix_label_raw": label,
            "title_label_raw": title,
            "pdf_page_start": pages[start]["pdf_page"],
            "pdf_page_end": pages[end]["pdf_page"],
            "bylaw_page_start": pages[start]["bylaw_page"],
            "bylaw_page_end": pages[end]["bylaw_page"],
        },
        "content_text": compact_space(" ".join(line for page in pages[start : end + 1] for line in page["lines"])),
    }


def main() -> None:
    pages = read_pages()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    (OUTPUT_ROOT / "zones").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "schedules").mkdir(parents=True, exist_ok=True)

    s1 = page_index_for_bylaw_page(pages, 1)
    s1a = page_index_for_bylaw_page(pages, 13)
    s2 = page_index_for_bylaw_page(pages, 16)
    s3 = page_index_for_bylaw_page(pages, 51)
    schedules_start = page_index_for_bylaw_page(pages, 118)
    appendices_start = page_index_for_bylaw_page(pages, 301)

    definitions = parse_definitions(pages, s1, s1a - 1, "1")
    definitions.extend(parse_definitions(pages, s1a, s2 - 1, "1A"))
    write_json(OUTPUT_ROOT / "definitions.json", {
        "document_metadata": {"jurisdiction": "Halifax Regional Municipality", "bylaw_name": "Dartmouth Land Use By-law", "source_document_path": "docs/dartmouth-land-use-bylaw.pdf"},
        "source_section": {"section_label_raw": "1-1A", "title_label_raw": "DEFINITIONS", "pdf_page_start": pages[s1]["pdf_page"], "pdf_page_end": pages[s2 - 1]["pdf_page"], "bylaw_page_start": pages[s1]["bylaw_page"], "bylaw_page_end": pages[s2 - 1]["bylaw_page"]},
        "definitions": definitions,
    })

    write_json(OUTPUT_ROOT / "general-provisions.json", {
        "document_metadata": {"jurisdiction": "Halifax Regional Municipality", "bylaw_name": "Dartmouth Land Use By-law", "source_document_path": "docs/dartmouth-land-use-bylaw.pdf", "document_type": "general_provisions"},
        "source_section": {"section_range_raw": "2-34", "title_label_raw": "GENERAL PROVISIONS", "pdf_page_start": pages[s2]["pdf_page"], "pdf_page_end": pages[s3 - 1]["pdf_page"], "bylaw_page_start": pages[s2]["bylaw_page"], "bylaw_page_end": pages[s3 - 1]["bylaw_page"]},
        "normalization_policy": {"clause_labels_preserved_raw": True, "normalized_paths_applied": False, "reason": "General provisions contain mixed clause formats that have not been individually reviewed for hierarchy normalization in this repository context."},
        "sections": parse_general_provisions(pages, s2, s3 - 1),
    })

    for start, end, match in page_ranges_by_heading(pages, page_index_for_bylaw_page(pages, 53), schedules_start - 1, PART_RE):
        slug, payload = build_zone_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "zones" / f"{slug}.json", payload)

    maps = []
    for start, end, match in page_ranges_by_heading(pages, schedules_start, page_index_for_bylaw_page(pages, 300), SCHEDULE_RE):
        slug, payload, map_reference = build_schedule_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / "schedules" / f"{slug}.json", payload)
        if map_reference is not None:
            maps.append(map_reference)

    for start, end, match in page_ranges_by_heading(pages, page_index_for_bylaw_page(pages, 302), len(pages) - 1, APPENDIX_RE):
        slug, payload = build_appendix_payload(pages, start, end, match)
        write_json(OUTPUT_ROOT / f"{slug}.json", payload)

    write_json(OUTPUT_ROOT / "maps.json", {"document_name": "Dartmouth Land Use By-law", "source_document_path": "docs/dartmouth-land-use-bylaw.pdf", "references": maps})
    write_json(OUTPUT_ROOT / "spatial-features-needed.json", {
        "document_name": "Dartmouth Land Use By-law",
        "source_document_path": "docs/dartmouth-land-use-bylaw.pdf",
        "spatial_features_needed": [{"feature_key": ref["feature_key"], "feature_class": ref["feature_class"], "source_type": "schedule_digitization", "reason": f"Derived from {ref['source_label_raw']}."} for ref in maps],
    })


if __name__ == "__main__":
    main()



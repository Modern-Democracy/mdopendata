from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

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


def extract_zone_lines(reader: PdfReader, zone: dict, next_bylaw_start: int | None) -> tuple[list[dict], str]:
    pdf_start, pdf_end, _, _ = zone_pages(zone, next_bylaw_start)
    page_texts = []
    for pdf_page in range(pdf_start, pdf_end + 1):
        text = reader.pages[pdf_page - 1].extract_text() or ""
        text = clean_text(text)
        lines = [line.strip() for line in text.splitlines()]
        kept = [line for line in lines if not is_noise_line(line, zone)]
        page_texts.append({"pdf_page": pdf_page, "text": "\n".join(kept)})
    combined = "\n".join(page["text"] for page in page_texts if page["text"])
    return page_texts, combined


SECTION_RE = re.compile(r"^(?P<label>\d+\.\d+)\s+(?P<title>[A-Z][A-Z0-9 '&/\-]+)$")
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
                unassigned.extend(leading)

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
        content_blocks.append(
            {
                "heading_context_raw": f"PART {zone['part']} {zone['code']} - unassigned extracted text",
                "text": " ".join(unassigned),
                "citations": citation_for_zone(zone, next_bylaw_start),
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


def build_zone_doc(reader: PdfReader, zone: dict, next_bylaw_start: int | None) -> dict:
    page_texts, text = extract_zone_lines(reader, zone, next_bylaw_start)
    raw_sections, content_blocks = split_sections(page_texts, zone, next_bylaw_start)
    zone_citation = citation_for_zone(zone, next_bylaw_start)
    requirement_sections = []
    permitted_uses = []
    pending_patterns: set[str] = set()
    open_issues = [
        {
            "issue_type": "extraction_review",
            "description": "PDF text order and figure/table text were extracted with pypdf; verify section order, column flow, and page layout before normalization.",
        }
    ]

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

    if re.search(r"\b(Table|Figure|Schedule)\b", text):
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

    if zone["code"] in {"RN", "RM", "RH"}:
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
- `source-manifest.json`: inventory of extracted zones, source pages, and known limits.
- `extraction-notes.md`: reproducibility notes and QA guidance.

## Extraction status

- Zone part scope: Parts 10-29, bylaw pages 87-162.
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
- Parses labeled sections such as `10.3 PERMITTED USES`.
- Parses raw provision labels that appear at line starts: `.1`, `(a)`, and roman labels such as `i)`.
- Extracts permitted uses only from sections whose titles contain `PERMITTED USE`.

QA checks recommended before normalization:

- Compare each zone's `requirement_sections` against the visual PDF where `table_parsing_review` or `layout_order_review` is present.
- Verify that table/figure text has not shifted between adjacent provisions.
- Verify unassigned text in `content_blocks` for RN, RM, and any other zone with `zone_boundary_review`.
- Confirm whether raw label patterns `.1`, `(a)`, and `i)` should be added to the approved hierarchy policy for this bylaw.
"""
    (OUT / "extraction-notes.md").write_text(notes, encoding="utf-8")


def main() -> None:
    reader = PdfReader(str(SOURCE))
    ZONES_OUT.mkdir(parents=True, exist_ok=True)
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

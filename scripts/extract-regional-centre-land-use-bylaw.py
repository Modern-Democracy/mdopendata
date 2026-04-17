from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "regional-centre-land-use-bylaw.pdf"
OUTPUT_ROOT = ROOT / "data" / "zoning" / "regional-centre"

JURISDICTION = "Halifax Regional Municipality"
BYLAW_NAME = "Regional Centre Land Use By-law"
SOURCE_DOCUMENT_PATH = "docs/regional-centre-land-use-bylaw.pdf"

BYLAW_PAGE_RE = re.compile(r"Regional Centre Land Use By-law\s*\|\s*(\d+)", re.IGNORECASE)
PART_RE = re.compile(r"^Part\s+([IVX]+):\s*(.*)$", re.IGNORECASE)
CHAPTER_RE = re.compile(r"^Part\s+([IVX]+),\s*Chapter\s+(\d+):\s*(.*)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)?[A-Z]?)\s+(?:\(([A-Za-z0-9.]+)\)\s*)?(.*)$")
SUBCLAUSE_RE = re.compile(r"^\(([A-Za-z0-9.]+)\)\s*(.*)$")
DEFINITION_RE = re.compile(r"^\((\d+(?:\.\d+)?)\)\s*(.*)$")
ZONE_LINE_RE = re.compile(r"^\(([A-Za-z0-9.]+)\)\s+(.+?)\s+\(([A-Z0-9-]+)\)[;.]?(?:\s+and)?$")
TABLE_RE = re.compile(r"^Table\s+(1[A-D]):\s*(.*)$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^Appendix\s+(\d+):\s*(.*)$", re.IGNORECASE)
AMENDMENT_ROW_RE = re.compile(r"^(\d+)\s+(.*)$")

APPROVED_HIERARCHY_EXAMPLES = [
    "21(e)",
    "21(ea)",
    "21(ea)(1)",
    "76(4.2)(e)",
    "30(2)(ah.5)",
    "499(47.5)",
    "76.5(1)",
    "94.5(1)(a)",
]

ROMAN_TOKENS = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
BLACK_DOT = "\uf098"
BLANK_MARK = "\uf020"
PERMISSION_SYMBOLS = set("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛")
ZONE_TABLE_CODES = {
    "DD",
    "DH",
    "CEN-2",
    "CEN-1",
    "COR",
    "HR-2",
    "HR-1",
    "ER-3",
    "ER-2",
    "ER-1",
    "CH-2",
    "CH-1",
    "CLI",
    "LI",
    "HRI",
    "INS",
    "UC-2",
    "UC-1",
    "DND",
    "H",
    "PCF",
    "RPK",
    "WA",
    "CDD-2",
    "CDD-1",
    "HCD-SV",
}
LAND_USE_CATEGORIES = {
    "Residential",
    "Commercial",
    "Urban agriculture",
    "Institutional",
    "Industrial",
    "Park and community facilities",
    "Water access",
    "Military",
    "Other",
    "Prohibited in all zones",
}
TABLE_CONFIGS = {
    "Table 1A": {
        "title": "Permitted uses by zone (DD, DH, CEN-2, CEN-1, COR, HR-2, and HR-1)",
        "bylaw_pages": (46, 48),
        "zones": ["DD", "DH", "CEN-2", "CEN-1", "COR", "HR-2", "HR-1"],
        "centers": [266.0, 307.5, 349.0, 390.5, 432.0, 473.1, 514.5],
    },
    "Table 1B": {
        "title": "Permitted uses by zone (ER-3, ER-2, ER-1, CH-2, and CH-1)",
        "bylaw_pages": (49, 51),
        "zones": ["ER-3", "ER-2", "ER-1", "CH-2", "CH-1"],
        "centers": [312.1, 368.8, 418.4, 461.4, 511.0],
    },
    "Table 1C": {
        "title": "Permitted uses by zone (CLI, LI, HRI, INS, UC-2, UC-1, DND, H, PCF, RPK, and WA)",
        "bylaw_pages": (52, 54),
        "zones": ["CLI", "LI", "HRI", "INS", "UC-2", "UC-1", "DND", "H", "PCF", "RPK", "WA"],
        "centers": [209.3, 234.4, 261.4, 293.7, 325.8, 358.1, 390.3, 422.5, 454.7, 487.0, 519.2],
    },
    "Table 1D": {
        "title": "Permitted uses by zone (HCD-SV)",
        "bylaw_pages": (55, 57),
        "zones": ["HCD-SV"],
        "centers": [277.1],
    },
}


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    value = value.replace("By- law", "By-law").replace("By- Law", "By-Law")
    return value.rstrip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_pages() -> list[dict]:
    reader = PdfReader(str(SOURCE_PDF))
    pages = []
    for pdf_page, page in enumerate(reader.pages, start=1):
        text = normalize_line(page.extract_text() or "")
        raw_lines = [normalize_line(line.strip()) for line in text.splitlines() if line.strip()]
        bylaw_page = None
        match = BYLAW_PAGE_RE.search(text)
        if match:
            bylaw_page = int(match.group(1))
        lines = [line for line in raw_lines if not BYLAW_PAGE_RE.fullmatch(line)]
        pages.append({"pdf_page": pdf_page, "bylaw_page": bylaw_page, "text": text, "lines": lines})
    return pages


def page_index_for_bylaw_page(pages: list[dict], bylaw_page: int) -> int:
    for index, page in enumerate(pages):
        if page["bylaw_page"] == bylaw_page:
            return index
    raise ValueError(f"By-law page not found: {bylaw_page}")


def citations(pages: list[dict], start: int, end: int) -> dict:
    return {
        "pdf_page_start": pages[start]["pdf_page"],
        "pdf_page_end": pages[end]["pdf_page"],
        "bylaw_page_start": pages[start]["bylaw_page"],
        "bylaw_page_end": pages[end]["bylaw_page"],
    }


def normalize_clause_path(label: str) -> list[str] | None:
    cleaned = compact_space(label).replace(" ", "")
    root_match = re.match(r"^(\d+(?:\.\d+)?[A-Z]?)(.*)$", cleaned)
    if not root_match:
        return None
    root = root_match.group(1)
    rest = root_match.group(2)
    if rest and not re.fullmatch(r"(?:\([A-Za-z0-9.]+\))+", rest):
        return None
    path = [root]
    for token in re.findall(r"\(([A-Za-z0-9.]+)\)", rest):
        if "." in token:
            path.append(token)
        elif token in ROMAN_TOKENS:
            path.append(token)
        elif re.fullmatch(r"[a-z]{2,}", token):
            path.extend(list(token))
        else:
            path.append(token)
    return path


def clause_depth(token: str, stack: list[tuple[int, str]], previous_text: str | None = None) -> int:
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return 1
    if token in ROMAN_TOKENS and stack and stack[-1][0] >= 3:
        return 3
    if token in ROMAN_TOKENS and stack and stack[-1][0] == 2 and (previous_text or "").rstrip().endswith(":"):
        return 3
    return 2


def make_clause_label(root: str, stack: list[tuple[int, str]]) -> str:
    return root + "".join(f"({token})" for _, token in stack)


def clean_heading_lines(lines: list[str]) -> str | None:
    cleaned = []
    for line in lines:
        if line.lower().startswith("part "):
            continue
        if line in {"Introduction"}:
            continue
        cleaned.append(line)
    return compact_space(" ".join(cleaned)) or None


def should_start_section(label: str, current_sort: float | None) -> bool:
    if not re.fullmatch(r"\d+(?:\.\d+)?[A-Z]?", label):
        return False
    number_match = re.match(r"\d+(?:\.\d+)?", label)
    if not number_match:
        return False
    value = float(number_match.group(0))
    if current_sort is None:
        return 1 <= value <= 600
    return current_sort <= value <= current_sort + 5


def parse_numbered_sections(pages: list[dict], start: int, end: int) -> tuple[list[dict], set[str]]:
    sections: list[dict] = []
    pending_heading: list[str] = []
    current_section: dict | None = None
    current_provision: dict | None = None
    current_root: str | None = None
    current_sort: float | None = None
    stack: list[tuple[int, str]] = []
    pending_patterns: set[str] = set()

    def finish_provision() -> None:
        nonlocal current_provision
        if current_provision is None:
            return
        current_provision["text"] = compact_space(" ".join(current_provision.pop("text_parts")))
        current_provision["status"] = "repealed" if "repealed" in current_provision["text"].lower() else "active"
        current_provision = None

    def finish_section() -> None:
        nonlocal current_section
        finish_provision()
        if current_section is not None:
            sections.append(current_section)
            current_section = None

    for page_index in range(start, end + 1):
        page = pages[page_index]
        for line in page["lines"]:
            if not line or PART_RE.match(line) or CHAPTER_RE.match(line):
                continue
            section_match = SECTION_RE.match(line)
            if section_match and should_start_section(section_match.group(1), current_sort):
                finish_section()
                label = section_match.group(1)
                token = section_match.group(2)
                text = compact_space(section_match.group(3))
                current_root = label
                current_sort = float(re.match(r"\d+(?:\.\d+)?", label).group(0))
                stack = []
                title = clean_heading_lines(pending_heading) or text[:100] or None
                pending_heading = []
                current_section = {
                    "order_index": len(sections) + 1,
                    "section_label_raw": label,
                    "title_label_raw": title,
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                    "provisions": [],
                }
                if token:
                    depth = clause_depth(token, stack)
                    stack = [(depth, token)]
                    clause_label = make_clause_label(label, stack)
                else:
                    clause_label = label
                path = normalize_clause_path(clause_label)
                if path is None and clause_label != label:
                    pending_patterns.add(clause_label)
                current_provision = {
                    "provision_label_raw": clause_label,
                    "clause_path": path,
                    "heading_context_raw": title,
                    "text_parts": [text] if text else [],
                    "status": "active",
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
                current_section["provisions"].append(current_provision)
                continue
            sub_match = SUBCLAUSE_RE.match(line)
            if sub_match and current_section is not None and current_root is not None:
                token = sub_match.group(1)
                previous_text = None
                if current_provision is not None and current_provision.get("text_parts"):
                    previous_text = compact_space(" ".join(current_provision["text_parts"]))
                finish_provision()
                depth = clause_depth(token, stack, previous_text)
                stack = [item for item in stack if item[0] < depth]
                stack.append((depth, token))
                clause_label = make_clause_label(current_root, stack)
                path = normalize_clause_path(clause_label)
                if path is None:
                    pending_patterns.add(clause_label)
                current_provision = {
                    "provision_label_raw": clause_label,
                    "clause_path": path,
                    "heading_context_raw": current_section.get("title_label_raw"),
                    "text_parts": [compact_space(sub_match.group(2))] if sub_match.group(2) else [],
                    "status": "active",
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
                current_section["provisions"].append(current_provision)
                continue
            if current_provision is not None:
                current_provision["text_parts"].append(line)
                current_provision["citations"]["pdf_page_end"] = page["pdf_page"]
                current_provision["citations"]["bylaw_page_end"] = page["bylaw_page"]
                if current_section is not None:
                    current_section["citations"]["pdf_page_end"] = page["pdf_page"]
                    current_section["citations"]["bylaw_page_end"] = page["bylaw_page"]
            else:
                pending_heading.append(line)

    finish_section()
    return sections, pending_patterns


def find_chapter_ranges(pages: list[dict], start: int, end: int) -> list[dict]:
    ranges: list[dict] = []
    for index in range(start, end + 1):
        lines = pages[index]["lines"]
        if not lines:
            continue
        first = lines[0]
        match = CHAPTER_RE.match(first)
        if not match:
            continue
        title_lines = [match.group(3)]
        for line in lines[1:5]:
            if SECTION_RE.match(line) or line in {"Introduction"}:
                break
            title_lines.append(line)
        ranges.append(
            {
                "start": index,
                "part_label_raw": f"Part {match.group(1)}",
                "chapter_label_raw": f"Chapter {match.group(2)}",
                "title_label_raw": compact_space(" ".join(title_lines)),
            }
        )
    for offset, item in enumerate(ranges):
        item["end"] = (ranges[offset + 1]["start"] - 1) if offset + 1 < len(ranges) else end
    return ranges


def parse_definitions(pages: list[dict], start: int, end: int) -> list[dict]:
    definitions: list[dict] = []
    current: dict | None = None

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        text = compact_space(" ".join(current.pop("text_parts")))
        term_match = re.match(r"(.+?)\s+(means|includes)\s+(.*)$", text, re.IGNORECASE)
        repealed_match = re.match(r"(.+?)\s+Repealed\b(.*)$", text, re.IGNORECASE)
        if term_match:
            current["term_raw"] = compact_space(term_match.group(1))
            current["definition_text"] = compact_space(term_match.group(2) + " " + term_match.group(3))
            current["status"] = "active"
        elif repealed_match:
            current["term_raw"] = compact_space(repealed_match.group(1))
            current["definition_text"] = compact_space("Repealed" + repealed_match.group(2))
            current["status"] = "repealed"
        else:
            current["term_raw"] = text.split(" means ", 1)[0][:120]
            current["definition_text"] = text
            current["status"] = "active"
        current["definition_key"] = slugify(current["term_raw"])
        definitions.append(current)
        current = None

    for page_index in range(start, end + 1):
        page = pages[page_index]
        for line in page["lines"]:
            if PART_RE.match(line) or CHAPTER_RE.match(line) or line.startswith("Diagram "):
                continue
            if line.startswith("499 "):
                continue
            match = DEFINITION_RE.match(line)
            if match:
                finish()
                label = f"499({match.group(1)})"
                current = {
                    "entry_index": len(definitions) + 1,
                    "section_label_raw": label,
                    "clause_label_raw": label,
                    "clause_path": normalize_clause_path(label),
                    "text_parts": [compact_space(match.group(2))] if match.group(2) else [],
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
            elif current is not None:
                current["text_parts"].append(line)
                current["citations"]["pdf_page_end"] = page["pdf_page"]
                current["citations"]["bylaw_page_end"] = page["bylaw_page"]
    finish()
    return definitions


def extract_zones(pages: list[dict]) -> list[dict]:
    zones: list[dict] = []
    seen: set[str] = set()
    for page_index in range(page_index_for_bylaw_page(pages, 32), page_index_for_bylaw_page(pages, 36) + 1):
        page = pages[page_index]
        for line in page["lines"]:
            match = ZONE_LINE_RE.match(line)
            if not match:
                continue
            code = match.group(3)
            if code not in ZONE_TABLE_CODES or code in seen:
                continue
            seen.add(code)
            zones.append(
                {
                    "zone_code": code,
                    "zone_name": compact_space(match.group(2)),
                    "source_clause_label_raw": f"30(1)({match.group(1)})",
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
            )
    return zones


def join_positioned_text(parts: list[str]) -> str:
    text = ""
    for part in parts:
        part = normalize_line(part).strip()
        if not part:
            continue
        if part == "-":
            text = text.rstrip() + "-"
        elif text.endswith("-"):
            text += part
        elif text:
            text += " " + part
        else:
            text = part
    return compact_space(text)


def positioned_page_rows(reader: PdfReader, page_index: int) -> list[dict]:
    items: list[dict] = []

    def visitor(text, cm, tm, font_dict, font_size) -> None:
        value = normalize_line(text.strip("\n"))
        if not value.strip():
            return
        items.append({"x": float(tm[4]), "y": float(tm[5]), "text": value})

    reader.pages[page_index].extract_text(visitor_text=visitor)
    rows: list[dict] = []
    for item in sorted(items, key=lambda candidate: -candidate["y"]):
        row = next((candidate for candidate in rows if abs(candidate["y"] - item["y"]) <= 3.0), None)
        if row is None:
            rows.append({"y": item["y"], "items": [item]})
        else:
            row["items"].append(item)
            row["y"] = (row["y"] * (len(row["items"]) - 1) + item["y"]) / len(row["items"])
    for row in rows:
        row["items"].sort(key=lambda candidate: candidate["x"])
        row["text"] = join_positioned_text([item["text"] for item in row["items"]])
    return sorted(rows, key=lambda candidate: -candidate["y"])


def nearest_zone_for_x(x: float, zones: list[str], centers: list[float]) -> str:
    distances = [(abs(x - center), zone) for zone, center in zip(zones, centers)]
    return min(distances, key=lambda item: item[0])[1]


def symbols_by_zone(row: dict, zones: list[str], centers: list[float]) -> dict[str, list[str]]:
    cells: dict[str, list[str]] = {zone: [] for zone in zones}
    first_center = min(centers)
    for item in row["items"]:
        if item["x"] < first_center - 20:
            continue
        zone_code = nearest_zone_for_x(item["x"], zones, centers)
        for char in item["text"]:
            if char == BLANK_MARK:
                continue
            if char in PERMISSION_SYMBOLS:
                cells[zone_code].append(char)
    return {zone: symbols for zone, symbols in cells.items() if symbols}


def table_left_text(row: dict, first_center: float) -> str:
    return join_positioned_text([item["text"] for item in row["items"] if item["x"] < first_center - 20])


def permission_status(symbols: list[str]) -> str:
    if any(symbol != BLACK_DOT for symbol in symbols):
        return "permitted_with_conditions"
    return "permitted"


def footnote_conditions(symbols: list[str], footnotes: dict[str, dict]) -> list[str]:
    conditions: list[str] = []
    for symbol in symbols:
        if symbol == BLACK_DOT:
            continue
        footnote = footnotes.get(symbol)
        if footnote and footnote.get("text"):
            conditions.append(footnote["text"])
    return conditions


def clean_table_text(value: str) -> str:
    for symbol in PERMISSION_SYMBOLS:
        value = value.replace(symbol, " ")
    return compact_space(value.replace(BLANK_MARK, " "))


def layout_column_positions(line: str, zones: list[str]) -> list[int] | None:
    positions: list[int] = []
    start = 0
    for zone in zones:
        position = line.find(zone, start)
        if position < 0:
            return None
        positions.append(position)
        start = position + len(zone)
    return positions


def split_layout_cells(line: str, positions: list[int], zones: list[str]) -> tuple[str, dict[str, list[str]]]:
    left_cut = max(0, positions[0] - 2)
    left_text = clean_table_text(line[:left_cut])
    cells: dict[str, list[str]] = {}
    boundaries = [max(0, positions[0] - 2)]
    for left, right in zip(positions, positions[1:]):
        boundaries.append((left + right) // 2)
    boundaries.append(len(line))
    for index, zone in enumerate(zones):
        cell_text = line[boundaries[index] : boundaries[index + 1]]
        symbols = [char for char in cell_text if char in PERMISSION_SYMBOLS]
        if symbols:
            cells[zone] = symbols
    return left_text, cells


def parse_permitted_use_tables(pages: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    tables: list[dict] = []
    rows_by_zone: dict[str, list[dict]] = {code: [] for code in ZONE_TABLE_CODES}
    reader = PdfReader(str(SOURCE_PDF))

    for table_label, config in TABLE_CONFIGS.items():
        zones = config["zones"]
        centers = config["centers"]
        start = page_index_for_bylaw_page(pages, config["bylaw_pages"][0])
        end = page_index_for_bylaw_page(pages, config["bylaw_pages"][1])
        table = {
            "table_label_raw": table_label,
            "title_label_raw": config["title"],
            "columns": [{"zone_code": zone_code} for zone_code in zones],
            "citations": citations(pages, start, end),
            "rows": [],
            "footnotes": [],
        }
        tables.append(table)
        current_category: str | None = None
        current_row: dict | None = None
        current_footnote: dict | None = None
        footnotes_by_symbol: dict[str, dict] = {}
        positions: list[int] | None = None

        def finish_row() -> None:
            nonlocal current_row
            if current_row is None:
                return
            current_row["use_name_raw"] = compact_space(" ".join(current_row.pop("name_parts")))
            table["rows"].append(current_row)
            current_row = None

        def finish_footnote() -> None:
            nonlocal current_footnote
            if current_footnote is None:
                return
            current_footnote["text"] = compact_space(" ".join(current_footnote.pop("text_parts")))
            table["footnotes"].append(current_footnote)
            footnotes_by_symbol[current_footnote["symbol_raw"]] = current_footnote
            current_footnote = None

        for page_index in range(start, end + 1):
            page = pages[page_index]
            layout_text = reader.pages[page_index].extract_text(extraction_mode="layout") or ""
            for raw_line in layout_text.splitlines():
                full_text = normalize_line(raw_line.rstrip())
                stripped = full_text.strip()
                if not stripped or BYLAW_PAGE_RE.search(stripped) or stripped.startswith("Table "):
                    continue
                header_positions = layout_column_positions(full_text, zones)
                if header_positions is not None:
                    candidate_category = clean_table_text(full_text[: header_positions[0]])
                    if candidate_category in LAND_USE_CATEGORIES:
                        finish_row()
                        positions = header_positions
                        current_category = candidate_category
                        continue
                if positions is None:
                    continue
                left_text, cells = split_layout_cells(full_text, positions, zones)
                if left_text in LAND_USE_CATEGORIES:
                    finish_row()
                    current_category = left_text
                    continue
                first_char = stripped[0]
                if first_char in PERMISSION_SYMBOLS and first_char != BLACK_DOT:
                    finish_row()
                    finish_footnote()
                    current_footnote = {
                        "symbol_raw": first_char,
                        "text_parts": [stripped[1:].strip()],
                        "citations": {
                            "pdf_page_start": page["pdf_page"],
                            "pdf_page_end": page["pdf_page"],
                            "bylaw_page_start": page["bylaw_page"],
                            "bylaw_page_end": page["bylaw_page"],
                        },
                    }
                    continue
                if current_footnote is not None:
                    current_footnote["text_parts"].append(full_text)
                    current_footnote["citations"]["pdf_page_end"] = page["pdf_page"]
                    current_footnote["citations"]["bylaw_page_end"] = page["bylaw_page"]
                    continue
                if current_category is None or not left_text:
                    continue
                if current_row is None:
                    current_row = {
                        "category_raw": current_category,
                        "name_parts": [],
                        "cells": [],
                        "source_lines_raw": [],
                        "citations": {
                            "pdf_page_start": page["pdf_page"],
                            "pdf_page_end": page["pdf_page"],
                            "bylaw_page_start": page["bylaw_page"],
                            "bylaw_page_end": page["bylaw_page"],
                        },
                    }
                elif not current_row["cells"] and cells:
                    current_name = compact_space(" ".join(current_row["name_parts"]))
                    is_continuation = (
                        left_text.startswith("(")
                        or not re.search(r"\buse\b", current_name, re.IGNORECASE)
                        or re.match(r"^(of|on|date|coming|from|to|and|or)\b", left_text, re.IGNORECASE)
                    )
                    if not is_continuation:
                        finish_row()
                        current_row = {
                            "category_raw": current_category,
                            "name_parts": [],
                            "cells": [],
                            "source_lines_raw": [],
                            "citations": {
                                "pdf_page_start": page["pdf_page"],
                                "pdf_page_end": page["pdf_page"],
                                "bylaw_page_start": page["bylaw_page"],
                                "bylaw_page_end": page["bylaw_page"],
                            },
                        }
                elif current_row["cells"] and cells:
                    finish_row()
                    current_row = {
                        "category_raw": current_category,
                        "name_parts": [],
                        "cells": [],
                        "source_lines_raw": [],
                        "citations": {
                            "pdf_page_start": page["pdf_page"],
                            "pdf_page_end": page["pdf_page"],
                            "bylaw_page_start": page["bylaw_page"],
                            "bylaw_page_end": page["bylaw_page"],
                        },
                    }
                elif current_row["cells"] and not cells and not re.fullmatch(r"use\b.*", left_text, re.IGNORECASE):
                    finish_row()
                    current_row = {
                        "category_raw": current_category,
                        "name_parts": [],
                        "cells": [],
                        "source_lines_raw": [],
                        "citations": {
                            "pdf_page_start": page["pdf_page"],
                            "pdf_page_end": page["pdf_page"],
                            "bylaw_page_start": page["bylaw_page"],
                            "bylaw_page_end": page["bylaw_page"],
                        },
                    }
                current_row["name_parts"].append(left_text)
                current_row["source_lines_raw"].append(full_text)
                current_row["citations"]["pdf_page_end"] = page["pdf_page"]
                current_row["citations"]["bylaw_page_end"] = page["bylaw_page"]
                for zone_code, symbols in cells.items():
                    current_row["cells"].append(
                        {
                            "zone_code": zone_code,
                            "permission_symbols_raw": symbols,
                            "permission_status": permission_status(symbols),
                            "footnote_symbols_raw": [symbol for symbol in symbols if symbol != BLACK_DOT],
                        }
                    )
        finish_row()
        finish_footnote()

        for row_index, row in enumerate(table["rows"], start=1):
            for cell in row["cells"]:
                symbols = cell["permission_symbols_raw"]
                conditions = footnote_conditions(symbols, footnotes_by_symbol)
                rows_by_zone[cell["zone_code"]].append(
                    {
                        "clause_label_raw": table["table_label_raw"],
                        "clause_path": None,
                        "use_type": slugify(row["category_raw"]).replace("-", "_") or "permitted_use",
                        "use_name": row["use_name_raw"],
                        "status": "active",
                        "permission_symbols_raw": symbols,
                        "permission_status": cell["permission_status"],
                        "footnote_symbols_raw": cell["footnote_symbols_raw"],
                        "conditions": conditions,
                        "table_label_raw": table["table_label_raw"],
                        "table_row_index": row_index,
                        "link_method": "table_cell_coordinate_mapping",
                        "citations": row["citations"],
                    }
                )
    return tables, rows_by_zone


def build_zone_payload(
    zone: dict,
    permitted_uses: list[dict],
    table_refs: list[dict],
    provisions: list[dict] | None = None,
    extra_context: dict | None = None,
) -> dict:
    code = zone["zone_code"]
    return {
        "document_metadata": {
            "jurisdiction": JURISDICTION,
            "bylaw_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "zone_code": code,
            "zone_name": zone["zone_name"],
            "part_label_raw": "Part II",
            "zone_established_by": {
                "clause_label_raw": zone["source_clause_label_raw"],
                "pdf_page": zone["citations"]["pdf_page_start"],
                "bylaw_page": zone["citations"]["bylaw_page_start"],
            },
            "zone_section_start": {
                "title_label_raw": f"{code} Zone",
                "pdf_page": 32,
                "bylaw_page": 32,
            },
        },
        "normalization_policy": {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": APPROVED_HIERARCHY_EXAMPLES,
            "pending_review_clause_patterns": [],
            "table_column_positions_preserved": True,
            "reason": "Permitted-use table entries are mapped from pypdf text coordinates to the declared zone columns.",
        },
        "general_context": {
            "zone_class_reference": {
                "section_label_raw": zone["source_clause_label_raw"],
                "summary": f"{code} is established by Section 30.",
            },
            "permitted_use_table_refs": table_refs,
            **(extra_context or {}),
        },
        "permitted_uses": permitted_uses,
        "provisions": provisions or [],
        "citations": zone["citations"],
    }


def section_lookup(sections: list[dict]) -> dict[str, dict]:
    return {section["section_label_raw"]: section for section in sections}


def provision_lookup(section: dict) -> dict[str, dict]:
    return {provision["provision_label_raw"]: provision for provision in section.get("provisions", [])}


def cdd_use(
    *,
    clause: dict,
    use_name: str,
    source_zone_code: str | None,
    conditions: list[str],
    use_type: str = "inherited_permitted_use",
) -> dict:
    item = {
        "clause_label_raw": clause["provision_label_raw"],
        "clause_path": clause.get("clause_path"),
        "use_type": use_type,
        "use_name": use_name,
        "status": clause.get("status") or "active",
        "conditions": conditions,
        "link_method": "section_text_inherited_zone_permission",
        "citations": clause.get("citations"),
    }
    if source_zone_code:
        item["source_zone_code"] = source_zone_code
        item["linked_sections"] = [source_zone_code]
    return item


def clean_cdd_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace(" Uses in a Transportation Reserve", "").strip()


def cdd_provision(clause: dict, provision_kind: str) -> dict:
    return {
        "provision_label_raw": clause["provision_label_raw"],
        "clause_path": clause.get("clause_path"),
        "provision_kind": provision_kind,
        "text": clean_cdd_text(clause.get("text")),
        "status": clause.get("status"),
        "citations": clause.get("citations"),
    }


def build_cdd_zone_content(chapter_sections: list[dict]) -> dict[str, dict]:
    sections = section_lookup(chapter_sections)
    section34 = sections.get("34")
    section35 = sections.get("35")
    content: dict[str, dict] = {}
    if section34:
        clauses = provision_lookup(section34)
        base = clauses["34(1)"]
        conditions = [
            clean_cdd_text(base["text"]),
            clean_cdd_text(clauses["34(2)"]["text"]),
            clean_cdd_text(clauses["34(2)(a)"]["text"]),
            clean_cdd_text(clauses["34(2)(a)(i)"]["text"]),
            clean_cdd_text(clauses["34(2)(a)(ii)"]["text"]),
            clean_cdd_text(clauses["34(2)(b)"]["text"]),
            clean_cdd_text(clauses["34(2)(b)(i)"]["text"]),
            clean_cdd_text(clauses["34(2)(b)(ii)"]["text"]),
        ]
        content["CDD-2"] = {
            "permitted_uses": [
                cdd_use(
                    clause=base,
                    use_name="commercial uses permitted in the CEN-2 zone",
                    source_zone_code="CEN-2",
                    conditions=conditions,
                ),
                cdd_use(
                    clause=base,
                    use_name="institutional uses permitted in the CEN-2 zone",
                    source_zone_code="CEN-2",
                    conditions=conditions,
                ),
            ],
            "provisions": [cdd_provision(clause, "cdd_development_condition") for clause in clauses.values()],
            "extra_context": {
                "inherited_permission_source": {
                    "section_label_raw": "34(1)",
                    "source_zone_code": "CEN-2",
                    "summary": "CDD-2 permits commercial and institutional uses permitted in the CEN-2 zone, subject to Section 490 and Section 34 development limits.",
                }
            },
        }
    if section35:
        clauses = provision_lookup(section35)
        base_existing = clauses["35(1)(a)"]
        base_er2 = clauses["35(1)(b)"]
        conditions = [
            clean_cdd_text(clauses["35(1)"]["text"]),
            clean_cdd_text(clauses["35(2)"]["text"]),
            clean_cdd_text(clauses["35(2)(a)"]["text"]),
            clean_cdd_text(clauses["35(2)(a)(i)"]["text"]),
            clean_cdd_text(clauses["35(2)(a)(ii)"]["text"]),
            clean_cdd_text(clauses["35(2)(b)"]["text"]),
            clean_cdd_text(clauses["35(2)(i)"]["text"]),
            clean_cdd_text(clauses["35(2)(ii)"]["text"]),
        ]
        content["CDD-1"] = {
            "permitted_uses": [
                cdd_use(
                    clause=base_existing,
                    use_name="existing uses",
                    source_zone_code=None,
                    conditions=conditions,
                    use_type="existing_permitted_use",
                ),
                cdd_use(
                    clause=base_er2,
                    use_name="uses permitted in the ER-2 zone",
                    source_zone_code="ER-2",
                    conditions=conditions,
                ),
            ],
            "provisions": [cdd_provision(clause, "cdd_development_condition") for clause in clauses.values()],
            "extra_context": {
                "inherited_permission_source": {
                    "section_label_raw": "35(1)",
                    "source_zone_code": "ER-2",
                    "summary": "CDD-1 permits existing uses and uses permitted in the ER-2 zone, subject to Section 491 and Section 35 development limits.",
                }
            },
        }
    return content


def build_appendix_payload(pages: list[dict], start: int, end: int, label: str, title: str) -> dict:
    lines = [line for page in pages[start : end + 1] for line in page["lines"]]
    return {
        "document_metadata": {
            "jurisdiction": JURISDICTION,
            "bylaw_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "document_type": "appendix",
            "appendix_label_raw": f"Appendix {label}",
            "title_label_raw": title,
        },
        "source_section": {
            "section_label_raw": f"Appendix {label}",
            "title_label_raw": title,
            **citations(pages, start, end),
        },
        "content_text": compact_space(" ".join(lines)),
    }


def build_amendment_history(pages: list[dict], start: int, end: int) -> dict:
    entries: list[dict] = []
    current: dict | None = None
    for page_index in range(start, end + 1):
        page = pages[page_index]
        for line in page["lines"]:
            if line in {"Schedules", "Regional Centre Land Use By-Law"}:
                continue
            if line in {"Amendment", "Number", "Policy / Maps Subject", "Council", "Adoption", "Effective", "Date"}:
                continue
            match = AMENDMENT_ROW_RE.match(line)
            if match:
                if current is not None:
                    current["text"] = compact_space(" ".join(current.pop("text_parts")))
                    entries.append(current)
                current = {
                    "amendment_number_raw": match.group(1),
                    "text_parts": [match.group(2)],
                    "citations": {
                        "pdf_page_start": page["pdf_page"],
                        "pdf_page_end": page["pdf_page"],
                        "bylaw_page_start": page["bylaw_page"],
                        "bylaw_page_end": page["bylaw_page"],
                    },
                }
            elif current is not None:
                current["text_parts"].append(line)
                current["citations"]["pdf_page_end"] = page["pdf_page"]
                current["citations"]["bylaw_page_end"] = page["bylaw_page"]
    if current is not None:
        current["text"] = compact_space(" ".join(current.pop("text_parts")))
        entries.append(current)
    return {
        "document_metadata": {
            "jurisdiction": JURISDICTION,
            "bylaw_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "document_type": "amendment_history",
            "schedule_label_raw": "Schedules",
        },
        "source_section": {
            "section_label_raw": "Schedules",
            "title_label_raw": "Amendment history",
            **citations(pages, start, end),
        },
        "provisions": [
            {
                "provision_label_raw": entry["amendment_number_raw"],
                "text": entry["text"],
                "status": "active",
                "citations": entry["citations"],
            }
            for entry in entries
        ],
    }


def main() -> None:
    pages = read_pages()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    (OUTPUT_ROOT / "zones").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "schedules").mkdir(parents=True, exist_ok=True)

    part_i_start = page_index_for_bylaw_page(pages, 8)
    definitions_start = page_index_for_bylaw_page(pages, 380)
    appendix_start = page_index_for_bylaw_page(pages, 435)
    schedules_start = page_index_for_bylaw_page(pages, 453)

    pending_patterns: set[str] = set()
    chapter_sections_by_file: dict[str, list[dict]] = {}
    for chapter in find_chapter_ranges(pages, part_i_start, definitions_start - 1):
        sections, chapter_pending = parse_numbered_sections(pages, chapter["start"], chapter["end"])
        pending_patterns.update(chapter_pending)
        if not sections:
            continue
        filename = f"{slugify(chapter['part_label_raw'])}-{slugify(chapter['chapter_label_raw'])}.json"
        chapter_sections_by_file[filename] = sections
        write_json(
            OUTPUT_ROOT / filename,
            {
                "document_metadata": {
                    "jurisdiction": JURISDICTION,
                    "bylaw_name": BYLAW_NAME,
                    "source_document_path": SOURCE_DOCUMENT_PATH,
                    "document_type": "general_provisions",
                    "part_label_raw": chapter["part_label_raw"],
                    "chapter_label_raw": chapter["chapter_label_raw"],
                },
                "source_section": {
                    "section_range_raw": f"{sections[0]['section_label_raw']}-{sections[-1]['section_label_raw']}",
                    "title_label_raw": chapter["title_label_raw"],
                    **citations(pages, chapter["start"], chapter["end"]),
                },
                "normalization_policy": {
                    "clause_labels_preserved_raw": True,
                    "approved_hierarchy_examples": APPROVED_HIERARCHY_EXAMPLES,
                    "pending_review_clause_patterns": sorted(chapter_pending),
                },
                "sections": sections,
            },
        )

    definitions = parse_definitions(pages, definitions_start, appendix_start - 1)
    write_json(
        OUTPUT_ROOT / "definitions.json",
        {
            "document_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
            },
            "source_section": {
                "section_label_raw": "499",
                "title_label_raw": "Definitions",
                **citations(pages, definitions_start, appendix_start - 1),
            },
            "normalization_policy": {
                "clause_labels_preserved_raw": True,
                "approved_hierarchy_examples": APPROVED_HIERARCHY_EXAMPLES,
                "pending_review_clause_patterns": [],
            },
            "definitions": definitions,
        },
    )

    zones = extract_zones(pages)
    table_payloads, permitted_by_zone = parse_permitted_use_tables(pages)
    cdd_content = build_cdd_zone_content(chapter_sections_by_file.get("part-ii-chapter-2.json", []))
    write_json(
        OUTPUT_ROOT / "permitted-use-tables.json",
        {
            "document_metadata": {
                "jurisdiction": JURISDICTION,
                "bylaw_name": BYLAW_NAME,
                "source_document_path": SOURCE_DOCUMENT_PATH,
                "document_type": "permitted_use_tables",
            },
            "normalization_policy": {
                "clause_labels_preserved_raw": True,
                "table_column_positions_preserved": True,
                "reason": "Tables 1A-1D are parsed by pypdf text coordinates using the declared zone columns.",
            },
            "tables": table_payloads,
        },
    )
    table_refs_by_zone: dict[str, list[dict]] = {code: [] for code in ZONE_TABLE_CODES}
    for table in table_payloads:
        for code in ZONE_TABLE_CODES:
            if code in table["title_label_raw"] or (table["table_label_raw"] == "Table 1D" and code == "HCD-SV"):
                table_refs_by_zone[code].append(
                    {
                        "table_label_raw": table["table_label_raw"],
                        "title_label_raw": table["title_label_raw"],
                        "citations": table["citations"],
                    }
                )
    for zone in zones:
        slug = slugify(zone["zone_code"])
        zone_cdd_content = cdd_content.get(zone["zone_code"], {})
        write_json(
            OUTPUT_ROOT / "zones" / f"{slug}.json",
            build_zone_payload(
                zone,
                permitted_by_zone.get(zone["zone_code"], []) + zone_cdd_content.get("permitted_uses", []),
                table_refs_by_zone.get(zone["zone_code"], []),
                provisions=zone_cdd_content.get("provisions"),
                extra_context=zone_cdd_content.get("extra_context"),
            ),
        )

    appendix_ranges = []
    for index in range(appendix_start, schedules_start):
        for line in pages[index]["lines"][:4]:
            match = APPENDIX_RE.match(line)
            if match:
                appendix_ranges.append({"start": index, "label": match.group(1), "title": match.group(2)})
                break
    for offset, appendix in enumerate(appendix_ranges):
        end = appendix_ranges[offset + 1]["start"] - 1 if offset + 1 < len(appendix_ranges) else schedules_start - 1
        write_json(
            OUTPUT_ROOT / f"appendix-{appendix['label']}.json",
            build_appendix_payload(pages, appendix["start"], end, appendix["label"], appendix["title"]),
        )

    write_json(OUTPUT_ROOT / "schedules" / "amendment-history.json", build_amendment_history(pages, schedules_start, len(pages) - 1))
    write_json(
        OUTPUT_ROOT / "maps.json",
        {
            "document_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "references": [],
            "notes": [
                "The PDF contains schedule references but does not include zoning map plates as extractable schedule pages.",
            ],
        },
    )
    write_json(
        OUTPUT_ROOT / "spatial-features-needed.json",
        {
            "document_name": BYLAW_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "spatial_features_needed": [
                {
                    "feature_key": "regional_centre_schedule_maps",
                    "feature_class": "zoning_schedule_map",
                    "source_type": "external_schedule_digitization",
                    "reason": "The by-law text references schedules for zones, special areas, height precincts, setbacks, view planes, and related spatial controls, but the source PDF does not include map plates as extractable schedule pages.",
                }
            ],
        },
    )
    if pending_patterns:
        write_json(
            OUTPUT_ROOT / "pending-clause-patterns.json",
            {
                "document_metadata": {
                    "jurisdiction": JURISDICTION,
                    "bylaw_name": BYLAW_NAME,
                    "source_document_path": SOURCE_DOCUMENT_PATH,
                    "document_type": "pending_clause_patterns",
                },
                "pending_review_clause_patterns": sorted(pending_patterns),
            },
        )


if __name__ == "__main__":
    main()

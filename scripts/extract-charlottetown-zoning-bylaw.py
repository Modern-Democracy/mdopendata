from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fitz
except ModuleNotFoundError:  # pragma: no cover - supports lighter repo Python envs.
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "charlottetown" / "charlottetown-zoning-bylaw.pdf"
OUT = ROOT / "data" / "zoning" / "charlottetown"
ZONES_OUT = OUT / "zones"
TEMPLATE = ROOT / "templates" / "charlottetown-zone.json"


APPROVED_HIERARCHY_EXAMPLES = [
    "21(e)",
    "21(ea)",
    "21(ea)(1)",
    "20(1)(a.1)",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return re.sub(r"_+", "_", value)


def zone_title_from_heading(metadata: dict[str, Any]) -> str:
    heading = metadata.get("chapter_heading_raw") or ""
    part = str(metadata.get("part_label_raw") or "")
    title = re.sub(rf"^\s*{re.escape(part)}\s+", "", heading).strip()
    return title or metadata.get("zone_name") or ""


def infer_section_label(chapter: str, title: str, order_index: int, existing: str | None) -> str | None:
    if existing:
        return existing
    title_upper = (title or "").upper()
    if "PERMITTED USE" in title_upper and order_index == 1:
        return f"{chapter}.1"
    if "REGULATIONS" in title_upper:
        return f"{chapter}.{order_index}"
    if "ACCESSORY AND SECONDARY" in title_upper:
        return f"{chapter}.{order_index}"
    if chapter and order_index:
        return f"{chapter}.{order_index}"
    return None


def label_for_raw(label: str | None) -> str | None:
    if not label:
        return label
    if re.fullmatch(r"[a-z]+", label, flags=re.IGNORECASE):
        return f"{label}."
    return label


def clean_clause_text(text: str | None) -> str:
    return " ".join((text or "").split())


def build_raw_clauses(provisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    current_parent: dict[str, Any] | None = None
    for provision in provisions:
        label = provision.get("provision_label_raw") or provision.get("clause_label_raw")
        text = clean_clause_text(provision.get("text"))
        raw_clause = {
            "clause_label_raw": label_for_raw(label),
            "clause_text_raw": text,
        }
        if re.fullmatch(r"[a-z]+", str(label or ""), flags=re.IGNORECASE) and current_parent is not None:
            current_parent.setdefault("clauses_raw", []).append(raw_clause)
            continue
        clauses.append(raw_clause)
        current_parent = raw_clause if re.fullmatch(r"\d+(?:\.\d+)+", str(label or "")) else None
    return clauses


def split_table_headings(raw_headings: list[str] | None) -> list[str]:
    if not raw_headings:
        return []
    joined = " ".join(raw_headings).strip()
    known = [
        "Interior/Corner Lots",
        "Interior Lot Corner Lot",
        "Interior Lot Corner Lots",
        "Interior Lots Corner Lots",
        "Townhouse Stacked Townhouse",
        "End-on Sites Front on Sites",
    ]
    if joined in known:
        if joined == "Interior/Corner Lots":
            return ["Interior/Corner Lots"]
        if joined == "Townhouse Stacked Townhouse":
            return ["Townhouse", "Stacked Townhouse"]
        if joined == "End-on Sites Front on Sites":
            return ["End-on Sites", "Front on Sites"]
        return ["Interior Lot", "Corner Lot"]
    if " Interior " in f" {joined} " and " Corner " in f" {joined} ":
        return ["Interior Lot", "Corner Lot"]
    return [joined] if joined else []


def page_words_by_pdf_page(doc: Any, pdf_page: int) -> list[tuple[float, float, float, float, str]]:
    page = doc[pdf_page - 1]
    return [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]


def find_heading_y(words: list[tuple[float, float, float, float, str]], title: str) -> float | None:
    target = re.sub(r"[^A-Z0-9]+", " ", title.upper()).strip()
    if not target:
        return None
    target_prefix = " ".join(target.split()[:4])
    rows: dict[int, list[tuple[float, str]]] = {}
    for x0, y0, _x1, _y1, word in words:
        if x0 < 90:
            continue
        rows.setdefault(round(y0), []).append((x0, word))
    for y, row_words in rows.items():
        line = " ".join(word for _x, word in sorted(row_words))
        normalized = re.sub(r"[^A-Z0-9]+", " ", line.upper()).strip()
        if target in normalized or (target_prefix and target_prefix in normalized):
            return float(y)
    return None


def group_words_into_rows(words: list[tuple[float, float, float, float, str]]) -> list[list[tuple[float, str]]]:
    rows: list[tuple[float, list[tuple[float, str]]]] = []
    for x0, y0, _x1, _y1, word in sorted(words, key=lambda item: (item[1], item[0])):
        if not rows or abs(rows[-1][0] - y0) > 4:
            rows.append((y0, [(x0, word)]))
        else:
            rows[-1][1].append((x0, word))
    return [row for _y, row in rows]


def table_rows_from_words(
    table_words: list[tuple[float, float, float, float, str]],
    headings: list[str],
) -> list[dict[str, Any]]:
    data_rows: list[list[tuple[float, str]]] = []
    current: list[tuple[float, str]] = []
    for row in group_words_into_rows(table_words):
        row_text = " ".join(word for _x, word in row)
        if re.search(r"\b\d+\.\d+\.\d+\b", row_text) or re.search(r"\bREGULATIONS FOR\b", row_text):
            if current:
                data_rows.append(current)
            break
        first_word = row[0][1] if row else ""
        if re.fullmatch(r"\d+", first_word) and row[0][0] < 130:
            if current:
                data_rows.append(current)
            current = list(row)
        elif current:
            current.extend(row)
        elif headings and any(heading.split()[0] in row_text for heading in headings):
            continue
    if current:
        data_rows.append(current)

    rows = []
    for row in data_rows:
        number_tokens = [word for x, word in row if x < 130 and re.fullmatch(r"\d+", word)]
        number = number_tokens[0] if number_tokens else ""
        label = " ".join(word for x, word in row if 130 <= x < 315).strip()
        cells = [{"cell_text_raw": number}, {"cell_text_raw": label}]
        if len(headings) <= 1:
            cells.append({"cell_text_raw": " ".join(word for x, word in row if x >= 315).strip()})
        else:
            cells.append({"cell_text_raw": " ".join(word for x, word in row if 315 <= x < 420).strip()})
            cells.append({"cell_text_raw": " ".join(word for x, word in row if x >= 420).strip()})
        if number or label or any(cell["cell_text_raw"] for cell in cells[2:]):
            rows.append({"cells_raw": cells})
    return rows


def parse_table_from_pdf(
    doc: Any,
    section: dict[str, Any],
    next_section: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if doc is None:
        return None
    citation = section.get("citations") or {}
    pdf_start = citation.get("pdf_page_start")
    pdf_end = citation.get("pdf_page_end") or pdf_start
    if not pdf_start:
        return None
    words = page_words_by_pdf_page(doc, int(pdf_start))
    y_start = find_heading_y(words, section.get("title_label_raw") or "")
    if y_start is None:
        return None
    y_end = None
    if next_section:
        next_page = (next_section.get("citations") or {}).get("pdf_page_start")
        if next_page == pdf_start:
            y_end = find_heading_y(words, next_section.get("title_label_raw") or "")
    if y_end is None:
        y_end = 760.0

    headings = split_table_headings(section.get("table_column_headings_raw"))
    columns = [{"column_label_raw": ""}, {"column_label_raw": ""}]
    columns.extend({"column_label_raw": heading} for heading in headings)

    rows = []
    for pdf_page in range(int(pdf_start), int(pdf_end) + 1):
        page_words = page_words_by_pdf_page(doc, pdf_page)
        page_y_start = y_start + 10 if pdf_page == int(pdf_start) else 60.0
        page_y_end = y_end - 3 if pdf_page == int(pdf_end) else 720.0
        table_words = [
            word
            for word in page_words
            if page_y_start <= word[1] <= page_y_end and 100 <= word[0] <= 560
        ]
        rows.extend(table_rows_from_words(table_words, headings))

    deduped_rows = []
    seen_rows = set()
    for row in rows:
        key = tuple(cell.get("cell_text_raw") or "" for cell in row.get("cells_raw", []))
        if key in seen_rows:
            continue
        seen_rows.add(key)
        deduped_rows.append(row)
    rows = deduped_rows

    if not rows:
        return None
    return {"clause_columns_raw": columns, "clause_rows_raw": rows}


def fallback_table_from_provisions(section: dict[str, Any]) -> dict[str, Any] | None:
    headings = split_table_headings(section.get("table_column_headings_raw"))
    if not headings:
        return None
    rows = []
    for provision in section.get("provisions", []):
        label = provision.get("provision_label_raw") or ""
        text = clean_clause_text(provision.get("text"))
        rows.append({"cells_raw": [{"cell_text_raw": label}, {"cell_text_raw": text}]})
    return {
        "clause_columns_raw": [{"column_label_raw": ""}, {"column_label_raw": ""}]
        + [{"column_label_raw": heading} for heading in headings],
        "clause_rows_raw": rows,
    }


def merge_heading_continuations(sections: list[dict[str, Any]], chapter: str) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index = 0
    while index < len(sections):
        section = dict(sections[index])
        next_section = dict(sections[index + 1]) if index + 1 < len(sections) else None
        inferred = infer_section_label(
            chapter,
            section.get("title_label_raw") or "",
            section.get("order_index") or index + 1,
            section.get("section_label_raw"),
        )
        if (
            next_section
            and not section.get("provisions")
            and not section.get("section_label_raw")
            and next_section.get("section_label_raw") == inferred
        ):
            section["section_label_raw"] = next_section.get("section_label_raw")
            section["title_label_raw"] = clean_clause_text(
                f"{section.get('title_label_raw') or ''} {next_section.get('title_label_raw') or ''}"
            )
            section["provisions"] = next_section.get("provisions", [])
            section["table_column_headings_raw"] = next_section.get("table_column_headings_raw")
            left = section.get("citations") or {}
            right = next_section.get("citations") or {}
            section["citations"] = {
                "pdf_page_start": left.get("pdf_page_start") or right.get("pdf_page_start"),
                "pdf_page_end": right.get("pdf_page_end") or left.get("pdf_page_end"),
                "bylaw_page_start": left.get("bylaw_page_start") or right.get("bylaw_page_start"),
                "bylaw_page_end": right.get("bylaw_page_end") or left.get("bylaw_page_end"),
            }
            merged.append(section)
            index += 2
            continue
        merged.append(section)
        index += 1
    return merged


def assign_section_label(chapter: str, section: dict[str, Any], next_number: int) -> tuple[str | None, int]:
    existing = section.get("section_label_raw")
    if existing:
        match = re.fullmatch(rf"{re.escape(chapter)}\.(\d+)", str(existing))
        return existing, int(match.group(1)) + 1 if match else next_number + 1
    return f"{chapter}.{next_number}" if chapter else None, next_number + 1


def build_raw_sections(doc: Any, legacy: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = legacy.get("document_metadata") or {}
    chapter = str(metadata.get("part_label_raw") or "")
    sections = merge_heading_continuations(legacy.get("requirement_sections") or legacy.get("sections") or [], chapter)
    raw_sections = []
    next_number = 1
    for index, section in enumerate(sections):
        title = section.get("title_label_raw") or section.get("section_title_raw") or ""
        section_label, next_number = assign_section_label(chapter, section, next_number)
        next_section = sections[index + 1] if index + 1 < len(sections) else None
        raw_section = {
            "section_label_raw": section_label,
            "section_title_raw": title,
        }
        table = parse_table_from_pdf(doc, section, next_section) or fallback_table_from_provisions(section)
        if table and "REGULATIONS" in title.upper():
            raw_section["clause_table_raw"] = table
        else:
            raw_section["clauses_raw"] = build_raw_clauses(section.get("provisions", []))
        raw_sections.append(raw_section)
    return raw_sections


MEASUREMENT_RE = re.compile(
    r"^\s*(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>[A-Za-z. ]+?)"
    r"(?:\s*\((?P<alt_value>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<alt_unit>[^)]+)\))?\s*$"
)


def parse_number(value: str | None) -> float | int | None:
    if value is None:
        return None
    parsed = float(value.replace(",", ""))
    return int(parsed) if parsed.is_integer() else parsed


def parse_measurement(text: str) -> dict[str, Any]:
    text = clean_clause_text(text)
    if not text:
        return {"value": None, "unit": None, "alternative_value": None, "alternative_unit": None, "source_text": ""}
    match = MEASUREMENT_RE.match(text)
    if not match:
        return {"value": None, "unit": None, "alternative_value": None, "alternative_unit": None, "source_text": text}
    return {
        "value": parse_number(match.group("value")),
        "unit": clean_clause_text(match.group("unit")).rstrip(".") if match.group("unit") else None,
        "alternative_value": parse_number(match.group("alt_value")),
        "alternative_unit": clean_clause_text(match.group("alt_unit")) if match.group("alt_unit") else None,
    }


def normalize_regulation_tables(raw_sections: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for section in raw_sections:
        if "REGULATIONS" not in (section.get("section_title_raw") or "").upper():
            continue
        table = section.get("clause_table_raw")
        if not table:
            continue
        column_labels = [c.get("column_label_raw") or "" for c in table.get("clause_columns_raw", [])]
        value_columns = column_labels[2:]
        section_key = slugify(section.get("section_title_raw") or "regulations")
        section_output: dict[str, Any] = {}
        for row in table.get("clause_rows_raw", []):
            cells = [cell.get("cell_text_raw") or "" for cell in row.get("cells_raw", [])]
            if len(cells) < 3:
                continue
            row_key = slugify(cells[1] or cells[0])
            for offset, column_label in enumerate(value_columns, start=2):
                lot_key = slugify(column_label or "value")
                section_output.setdefault(lot_key, {})[row_key] = parse_measurement(cells[offset] if offset < len(cells) else "")
        output[section_key] = section_output
    if len(output) == 1 and "regulations_for_permitted_uses" in output:
        return output["regulations_for_permitted_uses"]
    return output


def strip_trailing_list_punctuation(text: str) -> str:
    return clean_clause_text(text).rstrip(";").removesuffix(" and").strip()


def build_structured_zone_data(legacy: dict[str, Any], raw_sections: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = legacy.get("document_metadata") or {}
    permitted = []
    accessory = []
    for use in legacy.get("permitted_uses", []):
        name = strip_trailing_list_punctuation(use.get("use_name") or "")
        if not name:
            continue
        if use.get("use_type") == "accessory_or_secondary_use":
            accessory.append(name)
        else:
            permitted.append({"use_name": name, "use_status": "permitted"})
    return {
        "zone_code": metadata.get("zone_code"),
        "zone_name": zone_title_from_heading(metadata),
        "permitted_uses": permitted,
        "regulations_for_permitted_uses": normalize_regulation_tables(raw_sections),
        "accessory_and_secondary_uses": accessory,
    }


def transform_zone(doc: Any, legacy: dict[str, Any]) -> dict[str, Any]:
    metadata = legacy.get("document_metadata") or {}
    raw_sections = build_raw_sections(doc, legacy)
    output = dict(legacy)
    output["raw_data"] = {
        "zone_label_raw": str(metadata.get("part_label_raw") or ""),
        "zone_title_raw": zone_title_from_heading(metadata),
        "sections_raw": raw_sections,
    }
    output["structured_data"] = build_structured_zone_data(legacy, raw_sections)
    output.setdefault(
        "normalization_policy",
        {
            "clause_labels_preserved_raw": True,
            "approved_hierarchy_examples": APPROVED_HIERARCHY_EXAMPLES,
            "pending_review_clause_patterns": [],
        },
    )
    return output


def raw_section_from_section(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "section_label_raw": section.get("section_label_raw"),
        "section_title_raw": section.get("title_label_raw"),
        "clauses_raw": [
            {
                "clause_label_raw": label_for_raw(provision.get("provision_label_raw") or provision.get("clause_label_raw")),
                "clause_text_raw": clean_clause_text(provision.get("text")),
            }
            for provision in section.get("provisions", [])
        ],
    }


def transform_non_zone(legacy: dict[str, Any]) -> dict[str, Any]:
    output = dict(legacy)
    source = legacy.get("source_section") or {}
    sections = legacy.get("sections") or []
    content_blocks = legacy.get("content_blocks") or []
    output["raw_data"] = {
        "document_label_raw": source.get("section_range_raw") or (legacy.get("document_metadata") or {}).get("part_label_raw"),
        "document_title_raw": source.get("title_label_raw") or (legacy.get("document_metadata") or {}).get("title_label_raw"),
        "sections_raw": [raw_section_from_section(section) for section in sections],
        "content_blocks_raw": content_blocks,
    }
    structured: dict[str, Any] = {}
    if legacy.get("definitions"):
        structured["definitions"] = legacy["definitions"]
    if sections:
        structured["provisions"] = [
            {
                "section_label_raw": section.get("section_label_raw"),
                "section_title_raw": section.get("title_label_raw"),
                "clause_label_raw": provision.get("provision_label_raw") or provision.get("clause_label_raw"),
                "clause_text": clean_clause_text(provision.get("text")),
                "status": provision.get("status"),
            }
            for section in sections
            for provision in section.get("provisions", [])
        ]
    output["structured_data"] = structured
    return output


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)
    if fitz is None:
        raise RuntimeError(
            "PyMuPDF is required for coordinate-aware Charlottetown table extraction. "
            "Install pymupdf in the active Python environment or run with the bundled workspace Python."
        )

    manifest_path = OUT / "source-manifest.json"
    manifest = read_json(manifest_path)
    doc = fitz.open(SOURCE)

    for zone in manifest.get("zones", []):
        path = OUT / zone["file"]
        legacy = read_json(path)
        write_json(path, transform_zone(doc, legacy))

    for item in manifest.get("document_files", []) + manifest.get("supporting_files", []):
        path = OUT / item["file"]
        if path.exists():
            write_json(path, transform_non_zone(read_json(path)))

    readme = OUT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    note = (
        "\n## Template extraction update\n\n"
        "- Zone files now include `raw_data` using `templates/charlottetown-zone.json` as the structural pattern.\n"
        "- Zone files now include `structured_data` for normalized querying while preserving legacy top-level fields for importer compatibility.\n"
        "- Non-zone files now include `raw_data` and `structured_data` envelopes for source reproduction and query-oriented extraction.\n"
    )
    if "## Template extraction update" not in readme_text:
        readme.write_text(readme_text.rstrip() + note, encoding="utf-8")

    manifest["extracted_at_local"] = datetime.now().replace(microsecond=0).isoformat()
    manifest["extractor"] = "scripts/extract-charlottetown-zoning-bylaw.py; PyMuPDF-assisted template enrichment"
    limits = manifest.setdefault("known_limits", [])
    new_limit = "Template raw_data preserves section labels and tables where extractable; complex tables still require PDF QA for exact column alignment."
    if new_limit not in limits:
        limits.append(new_limit)
    write_json(manifest_path, manifest)


if __name__ == "__main__":
    main()

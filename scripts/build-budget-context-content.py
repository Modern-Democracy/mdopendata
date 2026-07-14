"""Build and optionally import canonical budget sections, contextual facts, and guides."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]
BUDGET_ROOT = ROOT / "data" / "budget" / "charlottetown"
OUTPUT_PATH = BUDGET_ROOT / "context-content.json"
REPORT_PATH = BUDGET_ROOT / "context-content-apply-report.json"
STRATEGIC_PDF = ROOT / "docs" / "charlottetown" / "Strategic Plan 2022 to 2026_FINAL.pdf"
STRATEGIC_RAW = BUDGET_ROOT / "strategic-plan-2022-2026" / "raw-pages"

EDITIONS = {
    "2024-2025": "docs/charlottetown/budget/2024-2025 Financial Plan Capital and Operational Budgets.pdf",
    "2025-2026": "docs/charlottetown/budget/2025-2026 Financial Plan Capital and Operational Budgets.pdf",
    "2026-2027": "docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf",
}

GUIDES = (
    {
        "key": "municipal-budget-cycle",
        "title": "How a municipal budget is prepared",
        "body": "A municipal budget is an annual financial plan. Administration and departments estimate the cost of maintaining services, identify proposed changes, and prepare operating and capital plans. Council reviews the plans, may amend them, and adopts the final budget through the municipality's required public process.",
    },
    {
        "key": "operating-budget",
        "title": "Operating budget",
        "body": "The operating budget covers recurring services and day-to-day municipal activities. It records expected revenue and expenses for the fiscal period, including staffing, utilities, maintenance, public safety, administration, grants, fees, taxes, and transfers.",
    },
    {
        "key": "capital-budget",
        "title": "Capital budget",
        "body": "The capital budget covers long-lived assets and major projects. It separates gross project cost, external or partner funding, financing, and the net municipal amount. A capital allocation authorizes a budget; it does not establish that the money has already been spent.",
    },
    {
        "key": "municipal-budget-funding",
        "title": "How municipal budgets are funded",
        "body": "Municipal funding commonly combines property taxes, user rates and fees, grants and transfers, reserve funds, and borrowing. The available sources and legal rules vary by municipality and jurisdiction. Source-specific rates, assessments, grants, debt, and funding deductions remain separate from this general explanation.",
    },
)

DEPARTMENT_PAGES = {
    "2024-2025": (
        (20, "Economic, Tourism and Cultural Development", "economic-tourism-cultural-development", "operating.economic-tourism-cultural-development"),
        (23, "Environment and Sustainability", "environment-sustainability", "operating.environment-sustainability"),
        (25, "Finance", "finance", "operating.finance"),
        (27, "Charlottetown Fire Department", "fire-emergency-preparedness", "operating.fire"),
        (29, "Human Resources", "human-resources", "operating.human-resources"),
        (31, "Mayor and Council", "mayor-council", "operating.mayor-council"),
        (33, "Parks and Recreation", "parks-recreation", "operating.parks-recreation"),
        (36, "Planning and Heritage", "planning-heritage", "operating.planning-heritage"),
        (38, "Charlottetown Police Services", "police", "operating.police"),
        (40, "Public Works", "public-works", "operating.public-works"),
        (42, "Water and Sewer Utility", "water-sewer", "operating.water-sewer"),
    ),
    "2025-2026": (
        (21, "Office of the Chief Administrative Officer", "chief-administrative-office", "operating.city-government"),
        (22, "Communications", "communications", "operating.city-government"),
        (23, "Information Technology", "information-technology", "operating.city-government"),
        (30, "Economic, Tourism and Cultural Development", "economic-tourism-cultural-development", "operating.economic-tourism-cultural-development"),
        (37, "Environment and Sustainability", "environment-sustainability", "operating.environment-sustainability"),
        (42, "Finance", "finance", "operating.finance"),
        (47, "Charlottetown Fire Department and Emergency Services", "fire-emergency-preparedness", "operating.fire"),
        (52, "Human Resources", "human-resources", "operating.human-resources"),
        (56, "Mayor and Council", "mayor-council", "operating.mayor-council"),
        (60, "Parks and Recreation", "parks-recreation", "operating.parks-recreation"),
        (71, "Planning and Heritage", "planning-heritage", "operating.planning-heritage"),
        (76, "Charlottetown Police Services", "police", "operating.police"),
        (82, "Public Works", "public-works", "operating.public-works"),
        (88, "Water and Sewer Utility", "water-sewer", "operating.water-sewer"),
    ),
    "2026-2027": (
        (25, "Office of the Chief Administrative Officer", "chief-administrative-office", "operating.city-government"),
        (26, "Communications", "communications", "operating.city-government"),
        (27, "Information Technology", "information-technology", "operating.city-government"),
        (34, "Economic, Tourism and Cultural Development", "economic-tourism-cultural-development", "operating.economic-tourism-cultural-development"),
        (42, "Environment and Sustainability", "environment-sustainability", "operating.environment-sustainability"),
        (47, "Finance", "finance", "operating.finance"),
        (51, "Charlottetown Fire Department", "fire-emergency-preparedness", "operating.fire"),
        (56, "Human Resources", "human-resources", "operating.human-resources"),
        (61, "Mayor and Council", "mayor-council", "operating.mayor-council"),
        (65, "Parks and Recreation", "parks-recreation", "operating.parks-recreation"),
        (75, "Planning and Heritage", "planning-heritage", "operating.planning-heritage"),
        (81, "Charlottetown Police Services", "police", "operating.police"),
        (86, "Public Works", "public-works", "operating.public-works"),
        (93, "Charlottetown Water and Sewer", "water-sewer", "operating.water-sewer"),
    ),
}

MULTI_DEPARTMENT_PAGES = {
    "2024-2025": (
        (17, "Office of the Chief Administrative Officer", "Infrastructure and Asset Management", "chief-administrative-office"),
        (17, "Infrastructure and Asset Management", None, "infrastructure-asset-management"),
        (18, "Communications", "Information Technology", "communications"),
        (18, "Information Technology", None, "information-technology"),
    ),
}

PREAMBLE_PAGES = {
    "2024-2025": ((3, "About Charlottetown"), (4, "Finance Committee chair's introduction"), (8, "Budget priorities"), (12, "Budget timeline and engagement")),
    "2025-2026": ((4, "About Charlottetown"), (5, "Finance Committee chair's introduction"), (9, "Budget priorities"), (12, "Municipal services")),
    "2026-2027": ((4, "About Charlottetown and land acknowledgement"), (5, "Finance Committee chair's introduction"), (9, "Budget process and priorities"), (11, "Engagement and legislative framework"), (12, "Capital-city context and service pressures"), (13, "Service demand and infrastructure pressures"), (14, "Municipal services"), (15, "Funding and taxation in Charlottetown"), (16, "Innovation Task Force")),
}

DEPARTMENT_STRUCTURE = (
    ("city-government", "City Government"),
    ("economic-tourism-cultural-development", "Economic, Tourism and Cultural Development"),
    ("environment-sustainability", "Environment and Sustainability"),
    ("finance", "Finance"),
    ("fire", "Charlottetown Fire Department"),
    ("human-resources", "Human Resources"),
    ("mayor-council", "Mayor and Council"),
    ("parks-recreation", "Parks and Recreation"),
    ("planning-heritage", "Planning and Heritage"),
    ("police", "Charlottetown Police Services"),
    ("public-works", "Public Works"),
    ("water-sewer", "Charlottetown Water and Sewer"),
)

CAPITAL_STRUCTURE = (
    ("environment-sustainability", "Environment and Sustainability"),
    ("fire", "Charlottetown Fire Department"),
    ("information-technology", "Information Technology"),
    ("parks-recreation", "Parks and Recreation"),
    ("police", "Charlottetown Police Services"),
    ("public-works", "Public Works"),
    ("water-sewer", "Charlottetown Water and Sewer"),
    ("eastlink-centre", "Eastlink Centre"),
    ("bell-aliant-centre", "Bell Aliant Centre"),
)

APPENDIX_STRUCTURE = (
    "Schedule of Property Taxes",
    "Fiscal Services - Schedule of Long Term Debt",
    "Water and Sewer - Schedule of Long Term Debt",
)

RANGES = {
    "2024-2025": {
        "front": (1, 2), "introduction": (3, 5), "strategic": (6, 7), "overview": (8, 12), "operating": (13, 43),
        "capital": (44, 76), "appendices": (None, None), "back": (88, 88),
        "departments": ((17, 19), (20, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32), (33, 35), (36, 37), (38, 39), (40, 41), (42, 43)),
        "facilities": ((77, 87, "Eastlink Centre and Bell Aliant Centre"),),
        "capital_programs": ((46, 47), (49, 51), (48, 48), (52, 59), (60, 61), (62, 69), (72, 76), (71, 71), (70, 70)),
        "appendix_items": (),
    },
    "2025-2026": {
        "front": (1, 3), "introduction": (4, 6), "strategic": (7, 8), "overview": (9, 12), "operating": (13, 106),
        "capital": (107, 143), "appendices": (144, 149), "back": (150, 150),
        "departments": ((21, 29), (30, 36), (37, 41), (42, 46), (47, 51), (52, 55), (56, 59), (60, 70), (71, 75), (76, 81), (82, 87), (88, 95)),
        "facilities": ((97, 101, "Eastlink Centre"), (102, 106, "Bell Aliant Centre")),
        "capital_programs": ((109, 111), (113, 115), (112, 112), (116, 120), (121, 121), (122, 135), (136, 140), (142, 142), (143, 143)),
        "appendix_items": ((144, 145, "Schedule of Property Taxes"), (146, 147, "Fiscal Services - Schedule of Long Term Debt"), (148, 149, "Water and Sewer - Schedule of Long Term Debt")),
    },
    "2026-2027": {
        "front": (1, 3), "introduction": (4, 6), "strategic": (7, 8), "overview": (9, 17), "operating": (18, 108),
        "capital": (109, 147), "appendices": (148, 153), "back": (154, 154),
        "departments": ((25, 33), (34, 41), (42, 46), (47, 50), (51, 55), (56, 60), (61, 64), (65, 74), (75, 80), (81, 85), (86, 92), (93, 100)),
        "facilities": ((101, 104, "Eastlink Centre"), (105, 108, "Bell Aliant Centre")),
        "capital_programs": ((111, 116), (117, 119), (120, 121), (122, 126), (127, 132), (133, 143), (144, 144), (145, 146), (147, 147)),
        "appendix_items": ((148, 149, "Schedule of Property Taxes"), (150, 151, "Fiscal Services - Schedule of Long Term Debt"), (152, 153, "Water and Sewer - Schedule of Long Term Debt")),
    },
}


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"), os.environ.get("PGDATABASE", "mdopendata"),
    )


def repair_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    try:
        if any(token in value for token in ("â€", "â€™", "Ã")):
            value = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    value = value.replace("\x0c", "").replace("\u00ad", "").replace("�•", "•")
    replacements = {
        "â€™": "’", "â€˜": "‘", "â€œ": "“", "â€": "”", "â€“": "–", "â€”": "—",
        "â€¢": "•", "Â·": "·", "Â©": "©", "Â®": "®", "Â ": " ",
    }
    for broken, corrected in replacements.items():
        value = value.replace(broken, corrected)
    return re.sub(r"[ \t]+\n", "\n", value).strip()


def raw_page(edition: str, page: int) -> str:
    path = BUDGET_ROOT / edition / "raw-pages" / f"page-{page:03d}.txt"
    return repair_text(path.read_text(encoding="utf-8"))


def clean_page_body(text: str, title: str) -> str:
    lines = text.splitlines()
    while lines and (not lines[-1].strip() or re.fullmatch(r"\d+", lines[-1].strip())):
        lines.pop()
    compact = "\n".join(lines).strip()
    title_words = title.lower().split()[:2]
    if compact and title_words and all(word in compact.splitlines()[0].lower() for word in title_words):
        compact = "\n".join(compact.splitlines()[1:]).strip()
    return re.sub(r"\n{3,}", "\n\n", compact)


def looks_like_heading(text: str) -> bool:
    words = text.split()
    if not text or len(text) > 90 or len(words) > 12 or re.search(r"[.!?;:]$", text):
        return False
    if re.match(r"^\d+[.)]\s+", text) or not any(character.isalpha() for character in text):
        return False
    significant = [word.strip("&/()–—-'’\"") for word in words if word.strip("&/()–—-'’\"")]
    title_like = sum(word[:1].isupper() or word.casefold() in {"and", "of", "the", "vs."} for word in significant)
    return bool(significant) and title_like / len(significant) >= 0.65


def list_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for raw_line in lines:
        item = re.sub(r"^(?:[•▪◦*-]|\d+[.)])\s*", "", raw_line.strip())
        if not item:
            continue
        if items and item[:1].islower():
            items[-1] = f"{items[-1]} {item}"
        else:
            items.append(item)
    return [re.sub(r"\s+", " ", item).strip() for item in items]


def structured_blocks(text: str, kind: str = "narrative", drop_headings: tuple[str, ...] = ()) -> list[dict]:
    raw_lines = repair_text(text).splitlines()
    while raw_lines and (not raw_lines[-1].strip() or re.fullmatch(r"\d+", raw_lines[-1].strip())):
        raw_lines.pop()
    if kind == "attribute":
        return [{"type": "paragraph", "text": re.sub(r"\s+", " ", " ".join(raw_lines)).strip()}]
    if kind == "list":
        return [{"type": "unordered_list", "items": list_items(raw_lines)}]

    indents = [len(line) - len(line.lstrip()) for line in raw_lines if line.strip()]
    base_indent = Counter(indents).most_common(1)[0][0] if indents else 0
    ignored = {heading.casefold() for heading in drop_headings}
    blocks: list[dict] = []
    paragraph: list[str] = []
    active_list: str | None = None
    active_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append({"type": "paragraph", "text": re.sub(r"\s+", " ", " ".join(paragraph)).strip()})
            paragraph.clear()

    def flush_list() -> None:
        nonlocal active_list
        if active_items:
            blocks.append({"type": active_list or "unordered_list", "items": active_items.copy()})
            active_items.clear()
        active_list = None

    for raw_line in raw_lines:
        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip())
        if not stripped:
            flush_paragraph()
            flush_list()
            continue
        if stripped.casefold() in ignored:
            flush_paragraph()
            flush_list()
            continue
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        inferred_bullet = indent >= base_indent + 3 and not ordered
        if ordered or inferred_bullet:
            flush_paragraph()
            desired_type = "ordered_list" if ordered else "unordered_list"
            if active_list and active_list != desired_type:
                flush_list()
            active_list = desired_type
            item = ordered.group(1) if ordered else re.sub(r"^[•▪◦*-]\s*", "", stripped)
            if active_items and item[:1].islower():
                active_items[-1] = f"{active_items[-1]} {item}"
            else:
                active_items.append(item)
            continue
        flush_list()
        if looks_like_heading(stripped):
            flush_paragraph()
            blocks.append({"type": "heading", "level": 4, "text": stripped})
        else:
            paragraph.append(stripped)
    flush_paragraph()
    flush_list()
    return [block for block in blocks if block.get("text") or block.get("items")]


def blocks_text(blocks: list[dict]) -> str:
    values: list[str] = []
    for block in blocks:
        if block["type"] in {"heading", "paragraph"}:
            values.append(block["text"])
        else:
            values.extend(block["items"])
    return "\n\n".join(values)


def department_blocks(text: str, subject: str) -> list[tuple[str, str, str]]:
    lines = text.splitlines()
    while lines and (not lines[-1].strip() or re.fullmatch(r"\d+", lines[-1].strip())):
        lines.pop()
    subject_index = next((index for index, line in enumerate(lines) if line.strip().casefold() == subject.casefold()), None)
    if subject_index is not None:
        lines = lines[subject_index + 1:]
    while lines and (not lines[0].strip() or re.fullmatch(r"\d+", lines[0].strip()) or lines[0].strip().casefold() == "city government"):
        lines.pop(0)
    markers = {
        "summary": {"summary", "department summary"},
        "services": {"services provided", "programs and services provided"},
        "highlights": {"budget highlights"},
    }
    positions: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        normalized = re.sub(r"\s+", " ", line.strip().lower())
        for key, labels in markers.items():
            if normalized in labels:
                positions.append((index, key))
                break
    if not positions:
        return [("Department Summary", "narrative", repair_text(text))]
    result = []
    titles = {"summary": "Department Summary", "services": "Programs and Services Provided", "highlights": "Budget Highlights"}
    if positions and positions[0][0] > 0:
        leading = "\n".join(lines[:positions[0][0]]).strip()
        if leading:
            result.append(("Department Summary", "narrative", leading))
    for offset, (start, key) in enumerate(positions):
        end = positions[offset + 1][0] if offset + 1 < len(positions) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        if body:
            result.append((titles[key], "narrative" if key == "summary" else "list", body))
    return result


def page_segment(text: str, start_heading: str, end_heading: str | None) -> str:
    start = text.casefold().find(start_heading.casefold())
    if start < 0:
        raise RuntimeError(f"Missing department heading: {start_heading}")
    end = text.casefold().find(end_heading.casefold(), start + len(start_heading)) if end_heading else len(text)
    if end_heading and end < 0:
        raise RuntimeError(f"Missing department boundary: {end_heading}")
    return text[start:end]


def section_rows(edition: str) -> list[dict]:
    spec = RANGES[edition]
    basis = "table_of_contents" if edition != "2024-2025" else "source_headings"
    rows = [
        ("front-matter", None, "front_matter", "Budget document", 0, 0, *spec["front"]),
        ("introduction", None, "introduction", "Introduction", 1, 10, *spec["introduction"]),
        ("strategic-plan", None, "strategic_plan", "Strategic Plan", 2, 20, *spec["strategic"]),
        ("budget-overview", None, "budget_overview", "Budget Overview", 3, 30, *spec["overview"]),
        ("operating-budget", None, "operating_budget", "Operating Budget", 4, 40, *spec["operating"]),
        ("capital-budget", None, "capital_budget", "Capital Budget", 5, 50, *spec["capital"]),
        ("appendices", None, "appendices", "Appendices", 6, 60, *spec["appendices"]),
        ("back-matter", None, "back_matter", "Document information", 7, 70, *spec["back"]),
    ]
    for index, ((key, title), page_range) in enumerate(zip(DEPARTMENT_STRUCTURE, spec["departments"], strict=True), 1):
        rows.append((f"operating.{key}", "operating-budget", "department", title, 100 + index, index, *page_range))
    for index, (start, end, title) in enumerate(spec["facilities"], 20):
        key = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        rows.append((f"operating.{key}", "operating-budget", "facility", title, 100 + index, index, start, end))
    for index, ((key, title), page_range) in enumerate(zip(CAPITAL_STRUCTURE, spec["capital_programs"], strict=True), 1):
        rows.append((f"capital.{key}", "capital-budget", "capital_program", title, 200 + index, index, *page_range))
    appendix_items = spec["appendix_items"] or tuple((None, None, title) for title in APPENDIX_STRUCTURE)
    for index, (start, end, title) in enumerate(appendix_items, 1):
        key = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        rows.append((f"appendix.{key}", "appendices", "appendix", title, 300 + index, index, start, end))
    return [
        {"key": key, "parent": parent, "role": role, "title": title, "source_order": source_order,
         "display_order": display_order, "start_page": start, "end_page": end,
         "mapping_basis": "editorial" if start is None else basis}
        for key, parent, role, title, source_order, display_order, start, end in rows
    ]


def extract_strategic_pages() -> list[str]:
    result = subprocess.run(["pdftotext", "-layout", str(STRATEGIC_PDF), "-"], check=True, capture_output=True)
    text = result.stdout.decode("utf-8", errors="replace")
    pages = [repair_text(page) for page in text.split("\x0c")]
    if pages and not pages[-1]:
        pages.pop()
    if len(pages) != 15:
        raise RuntimeError(f"Expected 15 Strategic Plan pages, found {len(pages)}")
    STRATEGIC_RAW.mkdir(parents=True, exist_ok=True)
    for number, page in enumerate(pages, 1):
        (STRATEGIC_RAW / f"page-{number:03d}.txt").write_text(page + "\n", encoding="utf-8")
    return pages


def build_payload() -> dict:
    strategic_pages = extract_strategic_pages()
    facts: list[dict] = []
    for edition in EDITIONS:
        for page, title in PREAMBLE_PAGES[edition]:
            page_body = clean_page_body(raw_page(edition, page), title)
            blocks = structured_blocks(page_body, drop_headings=("Budget Overview",))
            facts.append({
                "key": f"{edition}-p{page:03d}-context", "edition": edition, "source_page": page,
                "section": "budget-overview" if "Budget" in title or page >= 8 else "introduction",
                "kind": "narrative", "title": title, "body": blocks_text(blocks), "blocks": blocks,
                "organization_unit_key": None,
            })
        for page, subject, org_key, section in DEPARTMENT_PAGES[edition]:
            for order, (title, kind, body) in enumerate(department_blocks(raw_page(edition, page), subject), 1):
                blocks = structured_blocks(body, kind)
                facts.append({
                    "key": f"{edition}-p{page:03d}-{order}", "edition": edition, "source_page": page,
                    "section": section, "kind": kind, "title": f"{subject}: {title}",
                    "body": blocks_text(blocks), "blocks": blocks,
                    "organization_unit_key": org_key,
                })
        for page, subject, end_heading, org_key in MULTI_DEPARTMENT_PAGES.get(edition, ()):
            segment = page_segment(raw_page(edition, page), subject, end_heading)
            for order, (title, kind, body) in enumerate(department_blocks(segment, subject), 1):
                blocks = structured_blocks(body, kind)
                facts.append({
                    "key": f"{edition}-p{page:03d}-{org_key}-{order}", "edition": edition, "source_page": page,
                    "section": "operating.city-government", "kind": kind, "title": f"{subject}: {title}",
                    "body": blocks_text(blocks), "blocks": blocks,
                    "organization_unit_key": org_key,
                })
    strategic_facts = []
    for page in range(6, 14):
        text = strategic_pages[page - 1]
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = next((line for line in lines if not re.fullmatch(r"\d+", line) and len(line) < 90), f"Strategic Plan page {page}")
        strategic_body = clean_page_body(text, title)
        blocks = structured_blocks(strategic_body, drop_headings=(title,))
        strategic_facts.append({"key": f"strategic-plan-p{page:03d}", "source_page": page, "kind": "narrative", "title": title, "body": blocks_text(blocks), "blocks": blocks})
    payload = {
        "schema_version": 1,
        "canonical_pattern": "2026-2027",
        "strategic_plan": {
            "path": str(STRATEGIC_PDF.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(STRATEGIC_PDF.read_bytes()).hexdigest(),
            "page_count": len(strategic_pages),
            "facts": strategic_facts,
        },
        "guides": list(GUIDES),
        "editions": {edition: {"source_path": path, "sections": section_rows(edition)} for edition, path in EDITIONS.items()},
        "facts": facts,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def ensure_org_units(cur: psycopg.Cursor) -> dict[str, int]:
    cur.execute("SELECT id FROM budget.reporting_entity WHERE slug='city-of-charlottetown' ORDER BY id LIMIT 1")
    city_entity = int(cur.fetchone()[0])
    required = {
        "city-government": "City Government", "chief-administrative-office": "Office of the Chief Administrative Officer",
        "infrastructure-asset-management": "Infrastructure and Asset Management",
        "communications": "Communications", "information-technology": "Information Technology",
        "economic-tourism-cultural-development": "Economic, Tourism and Cultural Development", "environment-sustainability": "Environment and Sustainability",
        "finance": "Finance", "fire-emergency-preparedness": "Fire and Emergency Preparedness", "human-resources": "Human Resources",
        "mayor-council": "Mayor and Council", "parks-recreation": "Parks and Recreation", "planning-heritage": "Planning and Heritage",
        "police": "Charlottetown Police Services", "public-works": "Public Works",
    }
    ids: dict[str, int] = {}
    for key, name in required.items():
        cur.execute("SELECT id FROM budget.organization_unit WHERE reporting_entity_id=%s AND unit_key=%s ORDER BY effective_from DESC,id DESC LIMIT 1", (city_entity, key))
        row = cur.fetchone()
        if row:
            ids[key] = int(row[0])
        else:
            cur.execute("INSERT INTO budget.organization_unit (reporting_entity_id,unit_key,display_name,unit_type,effective_from) VALUES (%s,%s,%s,'department','2024-04-01') RETURNING id", (city_entity, key, name))
            ids[key] = int(cur.fetchone()[0])
    parent = ids["city-government"]
    cur.execute("UPDATE budget.organization_unit SET parent_id=%s WHERE id=ANY(%s) AND parent_id IS NULL", (parent, [ids["chief-administrative-office"], ids["communications"], ids["information-technology"]]))
    return ids


def numeric_value(raw: str) -> float:
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if cleaned in {"", "-"}:
        return 0.0
    return float(cleaned)


def import_2026_appendix_observations(
    cur: psycopg.Cursor, municipality_id: int, document_id: int, section_ids: dict[tuple[str, str], int]
) -> tuple[int, int | None]:
    cur.execute("SELECT id FROM budget.reporting_entity WHERE municipality_id=%s AND slug='city-of-charlottetown' ORDER BY id LIMIT 1", (municipality_id,))
    city_entity_id = int(cur.fetchone()[0])
    cur.execute("SELECT primary_fiscal_period_id FROM budget.budget_edition WHERE document_id=%s", (document_id,))
    fiscal_period_id = int(cur.fetchone()[0])
    for code, name in (("assessment", "Assessment"), ("rate", "Rate"), ("tax_revenue", "Tax revenue")):
        cur.execute("INSERT INTO budget.amount_type (code,display_name) VALUES (%s,%s) ON CONFLICT (code) DO UPDATE SET display_name=EXCLUDED.display_name", (code, name))
    cur.execute("SELECT id,code FROM budget.amount_type")
    amount_types = {code: int(identifier) for identifier, code in cur.fetchall()}
    cur.execute("SELECT id,code FROM budget.measure_unit")
    units = {code: int(identifier) for identifier, code in cur.fetchall()}

    def table_context(table_key: str, roles: list[str], raw_labels: dict[str, str] | None = None) -> tuple[int, dict[str, int]]:
        cur.execute("SELECT id FROM budget.source_table WHERE document_id=%s AND table_key=%s", (document_id, table_key))
        table_id = int(cur.fetchone()[0])
        periods = {}
        for index, role in enumerate(roles):
            cur.execute("SELECT id FROM budget.source_table_column WHERE source_table_id=%s AND column_index=%s", (table_id, index))
            column_id = int(cur.fetchone()[0])
            cur.execute(
                """INSERT INTO budget.document_period
                   (document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order,review_status)
                   VALUES (%s,%s,%s,%s,%s,%s,'approved')
                   ON CONFLICT (document_id,source_table_column_id,period_role) DO UPDATE
                   SET raw_column_label=EXCLUDED.raw_column_label,column_order=EXCLUDED.column_order,review_status='approved'
                   RETURNING id""",
                (document_id, fiscal_period_id, column_id, f"appendix_{role}",
                 (raw_labels or {}).get(role, role.replace("_", " ").title()), index),
            )
            periods[role] = int(cur.fetchone()[0])
        return table_id, periods

    def ensure_statement(key: str, kind: str, title: str, table_id: int) -> int:
        cur.execute(
            """INSERT INTO budget.statement (document_id,reporting_entity_id,statement_key,statement_kind,title,source_table_id)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (document_id,statement_key) DO UPDATE
               SET statement_kind=EXCLUDED.statement_kind,title=EXCLUDED.title,source_table_id=EXCLUDED.source_table_id RETURNING id""",
            (document_id, city_entity_id, key, kind, title, table_id),
        )
        return int(cur.fetchone()[0])

    def insert_observation(statement_id: int, source_row_id: int, source_cell_id: int, line_key: str, row_order: int,
                           raw_label: str, aggregation_role: str, amount_code: str, unit_code: str,
                           value: float, document_period_id: int, section_id: int) -> int:
        cur.execute(
            """INSERT INTO budget.line_item
               (statement_id,line_key,row_order,raw_label,display_label,line_kind,aggregation_role,source_row_id)
               VALUES (%s,%s,%s,%s,%s,'appendix_line',%s,%s)
               ON CONFLICT (statement_id,line_key) DO UPDATE SET raw_label=EXCLUDED.raw_label,display_label=EXCLUDED.display_label,
                 aggregation_role=EXCLUDED.aggregation_role,source_row_id=EXCLUDED.source_row_id RETURNING id""",
            (statement_id, line_key, row_order, raw_label, raw_label, aggregation_role, source_row_id),
        )
        line_item_id = int(cur.fetchone()[0])
        state = "reported_zero" if value == 0 else "reported"
        cur.execute(
            """SELECT id FROM budget.financial_observation
               WHERE line_item_id=%s AND document_period_id=%s AND amount_type_id=%s AND measure_unit_id=%s""",
            (line_item_id, document_period_id, amount_types[amount_code], units[unit_code]),
        )
        existing = cur.fetchone()
        if existing:
            observation_id = int(existing[0])
        else:
            cur.execute(
                """INSERT INTO budget.financial_observation
                   (line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_state,is_reported,review_status)
                   VALUES (%s,%s,%s,%s,%s,%s,true,'approved') RETURNING id""",
                (line_item_id, document_period_id, amount_types[amount_code], units[unit_code], value, state),
            )
            observation_id = int(cur.fetchone()[0])
        cur.execute("INSERT INTO budget.financial_observation_source (observation_id,source_cell_id,source_role,source_order) VALUES (%s,%s,'reported_value',0) ON CONFLICT DO NOTHING", (observation_id, source_cell_id))
        cur.execute(
            """INSERT INTO budget.document_section_observation (observation_id,document_section_id,mapping_basis,review_status)
               VALUES (%s,%s,'source_page','approved') ON CONFLICT (observation_id) DO UPDATE
               SET document_section_id=EXCLUDED.document_section_id,mapping_basis='source_page',review_status='approved'""",
            (observation_id, section_id),
        )
        return observation_id

    added_ids: list[int] = []
    tax_table_id, tax_periods = table_context("ctown_budget_2026_2027_p149", ["assessment", "rate", "tax_revenue"])
    tax_statement_id = ensure_statement("appendix-property-tax-statement", "tax_assessment_rate", "Appendix 1 - Schedule of Property Taxes", tax_table_id)
    cur.execute(
        """SELECT r.id,r.row_index,r.raw_text,r.raw_label,
                  (SELECT c.id FROM budget.source_table_cell c JOIN budget.source_table_column col ON col.id=c.source_table_column_id
                    WHERE c.source_row_id=r.id ORDER BY col.column_index LIMIT 1) AS source_cell_id
             FROM budget.source_table_row r WHERE r.source_table_id=%s ORDER BY r.row_index""", (tax_table_id,),
    )
    current_group = "Property Taxes"
    tax_pattern = re.compile(r"^\s*(.+?)\s+\$?([\d,]+)\s+x\s+\$?([\d.]+)\s+per\s+\$100\s+\$\s*([\d,]+)\s*$", re.IGNORECASE)
    single_pattern = re.compile(r"^\s*(.*?)\s*\$\s*([\d,]+)\s*$")
    for source_row_id, row_index, raw_text, raw_label, source_cell_id in cur.fetchall():
        match = tax_pattern.match(raw_text)
        if match:
            item_label, assessment, rate, revenue = match.groups()
            base_key = f"row-{row_index:03d}-{re.sub(r'[^a-z0-9]+','-',current_group.casefold()).strip('-')}"
            added_ids.extend([
                insert_observation(tax_statement_id, source_row_id, source_cell_id, f"{base_key}-assessment", row_index, item_label.strip(), "detail", "assessment", "cad", numeric_value(assessment), tax_periods["assessment"], section_ids[("2026-2027", "appendix.schedule-of-property-taxes")]),
                insert_observation(tax_statement_id, source_row_id, source_cell_id, f"{base_key}-rate", row_index, item_label.strip(), "detail", "rate", "cad_per_100_assessed", numeric_value(rate), tax_periods["rate"], section_ids[("2026-2027", "appendix.schedule-of-property-taxes")]),
                insert_observation(tax_statement_id, source_row_id, source_cell_id, f"{base_key}-revenue", row_index, item_label.strip(), "detail", "tax_revenue", "cad", numeric_value(revenue), tax_periods["tax_revenue"], section_ids[("2026-2027", "appendix.schedule-of-property-taxes")]),
            ])
            continue
        single = single_pattern.match(raw_text)
        if single:
            item_label, revenue = single.groups()
            item_label = item_label.strip() or f"Total {current_group}"
            role = "total" if "total" in item_label.casefold() else "subtotal"
            added_ids.append(insert_observation(tax_statement_id, source_row_id, source_cell_id, f"row-{row_index:03d}-revenue", row_index, item_label, role, "tax_revenue", "cad", numeric_value(revenue), tax_periods["tax_revenue"], section_ids[("2026-2027", "appendix.schedule-of-property-taxes")]))
            continue
        heading = (raw_label or raw_text).strip()
        if heading and row_index > 3 and not re.search(r"operating budget|city of charlottetown", heading, re.IGNORECASE):
            current_group = heading.rstrip(":")

    debt_table_id, debt_periods = table_context(
        "ctown_budget_2026_2027_p151", ["balance", "principal", "interest"],
        {"balance": "2026 Balance", "principal": "2026/2027 Principal", "interest": "2026/2027 Interest"},
    )
    debt_statement_id = ensure_statement("appendix-city-debt-statement", "debt", "Appendix 2 - Fiscal Services - Schedule of Long Term Debt", debt_table_id)
    cur.execute(
        """SELECT r.id,r.row_index,r.raw_text,
                  (SELECT c.id FROM budget.source_table_cell c JOIN budget.source_table_column col ON col.id=c.source_table_column_id
                    WHERE c.source_row_id=r.id ORDER BY col.column_index LIMIT 1) AS source_cell_id
             FROM budget.source_table_row r WHERE r.source_table_id=%s ORDER BY r.row_index""", (debt_table_id,),
    )
    debt_pattern = re.compile(r"^\s*(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+|-)\s*$")
    debt_section_id = section_ids[("2026-2027", "appendix.fiscal-services-schedule-of-long-term-debt")]
    for source_row_id, row_index, raw_text, source_cell_id in cur.fetchall():
        match = debt_pattern.match(raw_text)
        if not match:
            total = single_pattern.match(raw_text)
            if total and "Total Interest and Principal" in raw_text:
                label, value = total.groups()
                added_ids.append(insert_observation(debt_statement_id, source_row_id, source_cell_id, f"row-{row_index:03d}-total", row_index, label.strip(), "total", "budget", "cad", numeric_value(value), debt_periods["principal"], debt_section_id))
            continue
        instrument_label, balance, principal, interest = match.groups()
        role = "total" if instrument_label.casefold().startswith("total") else "detail"
        base_key = f"row-{row_index:03d}"
        observation_ids = {
            "balance": insert_observation(debt_statement_id, source_row_id, source_cell_id, f"{base_key}-balance", row_index, instrument_label.strip(), role, "balance", "cad", numeric_value(balance), debt_periods["balance"], debt_section_id),
            "principal": insert_observation(debt_statement_id, source_row_id, source_cell_id, f"{base_key}-principal", row_index, instrument_label.strip(), role, "principal", "cad", numeric_value(principal), debt_periods["principal"], debt_section_id),
            "interest": insert_observation(debt_statement_id, source_row_id, source_cell_id, f"{base_key}-interest", row_index, instrument_label.strip(), role, "interest", "cad", numeric_value(interest), debt_periods["interest"], debt_section_id),
        }
        added_ids.extend(observation_ids.values())
        if role == "detail":
            cur.execute("SELECT id FROM budget.debt_instrument WHERE reporting_entity_id=%s AND raw_label=%s ORDER BY id LIMIT 1", (city_entity_id, instrument_label.strip()))
            row = cur.fetchone()
            if row:
                instrument_id = int(row[0])
            else:
                maturity = re.search(r"Maturing\s+(\d{4})", instrument_label, re.IGNORECASE)
                cur.execute("INSERT INTO budget.debt_instrument (reporting_entity_id,raw_label,normalized_label,maturity_date,effective_from) VALUES (%s,%s,%s,%s,'2026-04-01') RETURNING id", (city_entity_id, instrument_label.strip(), instrument_label.strip(), f"{maturity.group(1)}-03-31" if maturity else None))
                instrument_id = int(cur.fetchone()[0])
            for measure, observation_id in observation_ids.items():
                cur.execute("INSERT INTO budget.debt_observation (observation_id,debt_instrument_id,debt_measure) VALUES (%s,%s,%s) ON CONFLICT (observation_id) DO UPDATE SET debt_instrument_id=EXCLUDED.debt_instrument_id,debt_measure=EXCLUDED.debt_measure", (observation_id, instrument_id, measure))

    cur.execute("SELECT id,status FROM budget.publication_snapshot WHERE municipality_id=%s AND release_label='charlottetown-three-year-context-v2'", (municipality_id,))
    snapshot = cur.fetchone()
    new_snapshot_id = int(snapshot[0]) if snapshot else None
    if not snapshot:
        cur.execute("SELECT id,taxonomy_version,source_document_ids FROM budget.publication_snapshot WHERE municipality_id=%s AND status='published' ORDER BY id DESC LIMIT 1", (municipality_id,))
        prior_snapshot_id, taxonomy_version, source_document_ids = cur.fetchone()
        cur.execute("INSERT INTO budget.publication_snapshot (municipality_id,release_label,taxonomy_version,source_document_ids,status) VALUES (%s,'charlottetown-three-year-context-v2',%s,%s,'draft') RETURNING id", (municipality_id, taxonomy_version, source_document_ids))
        new_snapshot_id = int(cur.fetchone()[0])
        cur.execute("INSERT INTO budget.publication_observation (snapshot_id,observation_id) SELECT %s,observation_id FROM budget.publication_observation WHERE snapshot_id=%s", (new_snapshot_id, prior_snapshot_id))
        cur.executemany("INSERT INTO budget.publication_observation (snapshot_id,observation_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", [(new_snapshot_id, identifier) for identifier in sorted(set(added_ids))])
        cur.execute("SELECT category_taxonomy_version,rationale,authorized_by FROM budget.publication_snapshot_taxonomy_revision WHERE snapshot_id=%s", (prior_snapshot_id,))
        revision = cur.fetchone()
        if revision:
            cur.execute("INSERT INTO budget.publication_snapshot_taxonomy_revision (snapshot_id,category_taxonomy_version,rationale,authorized_by) VALUES (%s,%s,%s,%s)", (new_snapshot_id, revision[0], "Breaking budget content and observation redesign; " + revision[1], revision[2]))
        cur.execute("UPDATE budget.publication_snapshot SET status='published' WHERE id=%s", (new_snapshot_id,))
    return len(set(added_ids)), new_snapshot_id


def apply_display_column_labels(cur: psycopg.Cursor, document_ids: dict[str, int]) -> int:
    mappings = {
        ("2025-2026", "2025-2026-tax_assessment_rate-p145"): {
            1: "Assessment", 2: "Rate", 4: "Tax Revenue",
        },
        ("2025-2026", "2025-2026-debt_schedule-p147"): {
            1: "2025 Balance", 2: "2025/2026 Principal", 3: "2025/2026 Interest",
        },
        ("2025-2026", "2025-2026-debt_schedule-p149"): {
            1: "2025 Balance", 2: "2025/2026 Principal", 3: "2025/2026 Interest",
        },
        ("2026-2027", "appendix-water-sewer-debt-statement"): {
            1: "2026 Balance", 2: "2026/27 Principal", 3: "2026/27 Interest",
        },
    }
    updated = 0
    for (edition, statement_key), labels in mappings.items():
        for column_order, raw_label in labels.items():
            cur.execute(
                """UPDATE budget.document_period dp SET raw_column_label=%s
                    WHERE dp.document_id=%s AND dp.column_order=%s AND EXISTS (
                      SELECT 1 FROM budget.financial_observation o
                      JOIN budget.line_item li ON li.id=o.line_item_id
                      JOIN budget.statement s ON s.id=li.statement_id
                      WHERE o.document_period_id=dp.id AND s.statement_key=%s
                    )""",
                (raw_label, document_ids[edition], column_order, statement_key),
            )
            updated += cur.rowcount
    return updated


def apply_payload(cur: psycopg.Cursor, payload: dict) -> dict[str, int]:
    cur.execute("SELECT to_regclass('budget.financial_observation'),to_regclass('budget.document_section')")
    if any(value is None for value in cur.fetchone()):
        raise RuntimeError("Migration 028 must be applied before importing contextual content")
    cur.execute("SELECT id FROM budget.municipality WHERE slug='charlottetown'")
    municipality_id = int(cur.fetchone()[0])
    org_ids = ensure_org_units(cur)
    document_ids: dict[str, int] = {}
    for edition, record in payload["editions"].items():
        cur.execute("SELECT id FROM budget.source_document WHERE local_path=%s", (record["source_path"],))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Budget source document is not registered: {edition}")
        document_ids[edition] = int(row[0])

    strategic = payload["strategic_plan"]
    cur.execute(
        """INSERT INTO budget.source_document (municipality_id,title,document_kind,local_path,sha256,page_count,status)
           VALUES (%s,%s,'strategic_plan',%s,%s,%s,'reviewed')
           ON CONFLICT (sha256) DO UPDATE SET title=EXCLUDED.title,local_path=EXCLUDED.local_path,page_count=EXCLUDED.page_count,status='reviewed'
           RETURNING id""",
        (municipality_id, "City of Charlottetown Strategic Plan 2022 to 2026", strategic["path"], strategic["sha256"], strategic["page_count"]),
    )
    strategic_document_id = int(cur.fetchone()[0])
    strategic_page_ids = {}
    for page in range(1, strategic["page_count"] + 1):
        text_path = str((STRATEGIC_RAW / f"page-{page:03d}.txt").relative_to(ROOT)).replace("\\", "/")
        cur.execute(
            """INSERT INTO budget.source_page (document_id,pdf_page_number,text_path,extraction_method,extractor_version,extraction_confidence,review_status)
               VALUES (%s,%s,%s,'embedded_text','pdftotext-layout-v1',1,'approved')
               ON CONFLICT (document_id,pdf_page_number) DO UPDATE SET text_path=EXCLUDED.text_path,review_status='approved'
               RETURNING id""", (strategic_document_id, page, text_path),
        )
        strategic_page_ids[page] = int(cur.fetchone()[0])

    section_ids: dict[tuple[str, str], int] = {}
    for edition, record in payload["editions"].items():
        document_id = document_ids[edition]
        for section in record["sections"]:
            parent_id = section_ids.get((edition, section["parent"])) if section["parent"] else None
            cur.execute(
                """INSERT INTO budget.document_section
                   (document_id,parent_id,section_key,canonical_role,title,source_order,display_order,start_page,end_page,mapping_basis,review_status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'approved')
                   ON CONFLICT (document_id,section_key) DO UPDATE SET parent_id=EXCLUDED.parent_id,canonical_role=EXCLUDED.canonical_role,
                     title=EXCLUDED.title,source_order=EXCLUDED.source_order,display_order=EXCLUDED.display_order,start_page=EXCLUDED.start_page,
                     end_page=EXCLUDED.end_page,mapping_basis=EXCLUDED.mapping_basis,review_status='approved'
                   RETURNING id""",
                (document_id, parent_id, section["key"], section["role"], section["title"], section["source_order"],
                 section["display_order"], section["start_page"], section["end_page"], section["mapping_basis"]),
            )
            section_ids[(edition, section["key"])] = int(cur.fetchone()[0])

    section_observation_count = 0
    for edition, document_id in document_ids.items():
        cur.execute("DELETE FROM budget.document_section_observation dso USING budget.financial_observation o, budget.line_item li, budget.statement s WHERE dso.observation_id=o.id AND o.line_item_id=li.id AND li.statement_id=s.id AND s.document_id=%s", (document_id,))
        cur.execute(
            """WITH candidates AS (
                 SELECT o.id AS observation_id,ds.id AS document_section_id,
                        row_number() OVER (PARTITION BY o.id ORDER BY (ds.parent_id IS NOT NULL) DESC,
                          (ds.end_page-ds.start_page) ASC,ds.display_order,ds.id) AS candidate_order
                   FROM budget.financial_observation o
                   JOIN budget.line_item li ON li.id=o.line_item_id
                   JOIN budget.statement s ON s.id=li.statement_id
                   JOIN budget.financial_observation_source observation_source ON observation_source.observation_id=o.id
                   JOIN budget.source_table_cell source_cell ON source_cell.id=observation_source.source_cell_id
                   JOIN budget.source_table_row source_row ON source_row.id=source_cell.source_row_id
                   JOIN budget.source_table_page stp ON stp.source_table_id=source_row.source_table_id
                   JOIN budget.source_page sp ON sp.id=stp.source_page_id
                   JOIN budget.document_section ds ON ds.document_id=s.document_id
                    AND sp.pdf_page_number BETWEEN ds.start_page AND ds.end_page
                  WHERE s.document_id=%s AND ds.review_status='approved'
               )
               INSERT INTO budget.document_section_observation (observation_id,document_section_id,mapping_basis,review_status)
               SELECT observation_id,document_section_id,'source_page','approved' FROM candidates WHERE candidate_order=1
               ON CONFLICT (observation_id) DO UPDATE SET document_section_id=EXCLUDED.document_section_id,
                 mapping_basis=EXCLUDED.mapping_basis,review_status='approved'""",
            (document_id,),
        )
        section_observation_count += cur.rowcount
        cur.execute(
            """INSERT INTO budget.document_section_observation (observation_id,document_section_id,mapping_basis,review_status)
               SELECT o.id,ds.id,'statement_kind','approved'
                 FROM budget.financial_observation o JOIN budget.line_item li ON li.id=o.line_item_id
                 JOIN budget.statement s ON s.id=li.statement_id
                 JOIN budget.document_section ds ON ds.document_id=s.document_id AND ds.section_key=CASE
                   WHEN s.statement_kind LIKE 'capital%%' THEN 'capital-budget'
                   WHEN s.statement_kind IN ('tax_assessment_rate','debt','debt_schedule') THEN 'appendices'
                   ELSE 'operating-budget' END
                WHERE s.document_id=%s AND NOT EXISTS (SELECT 1 FROM budget.document_section_observation x WHERE x.observation_id=o.id)
               ON CONFLICT (observation_id) DO NOTHING""",
            (document_id,),
        )
        section_observation_count += cur.rowcount

    guide_ids = {}
    for guide in payload["guides"]:
        cur.execute(
            """INSERT INTO budget.editorial_guide (guide_key,version,title,body_markdown,review_status)
               VALUES (%s,1,%s,%s,'approved') ON CONFLICT (guide_key,version) DO UPDATE
               SET title=EXCLUDED.title,body_markdown=EXCLUDED.body_markdown,review_status='approved' RETURNING id""",
            (guide["key"], guide["title"], guide["body"]),
        )
        guide_ids[guide["key"]] = int(cur.fetchone()[0])
    for edition in payload["editions"]:
        section_id = section_ids[(edition, "budget-overview")]
        for order, guide in enumerate(payload["guides"], 1):
            cur.execute(
                """INSERT INTO budget.document_section_guide (document_section_id,editorial_guide_id,display_order)
                   VALUES (%s,%s,%s) ON CONFLICT (document_section_id,editorial_guide_id) DO UPDATE SET display_order=EXCLUDED.display_order""",
                (section_id, guide_ids[guide["key"]], order),
            )

    fact_count = 0
    for record in payload["facts"]:
        document_id = document_ids[record["edition"]]
        cur.execute("SELECT id FROM budget.source_page WHERE document_id=%s AND pdf_page_number=%s", (document_id, record["source_page"]))
        source_page_id = int(cur.fetchone()[0])
        organization_unit_id = org_ids.get(record["organization_unit_key"] or "")
        cur.execute(
            """INSERT INTO budget.fact
               (municipality_id,source_document_id,fact_key,fact_kind,title,body_text,content_json,organization_unit_id,review_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'approved')
               ON CONFLICT (source_document_id,fact_key) DO UPDATE SET fact_kind=EXCLUDED.fact_kind,title=EXCLUDED.title,
                 body_text=EXCLUDED.body_text,content_json=EXCLUDED.content_json,organization_unit_id=EXCLUDED.organization_unit_id,review_status='approved'
               RETURNING id""",
            (municipality_id, document_id, record["key"], record["kind"], record["title"], record["body"],
             Jsonb({"blocks": record["blocks"]}), organization_unit_id),
        )
        fact_id = int(cur.fetchone()[0])
        cur.execute("INSERT INTO budget.fact_source (fact_id,source_page_id,source_role,source_order) VALUES (%s,%s,'primary',0) ON CONFLICT DO NOTHING", (fact_id, source_page_id))
        section_id = section_ids[(record["edition"], record["section"])]
        cur.execute("SELECT COALESCE(max(display_order),0)+1 FROM budget.document_section_fact WHERE document_section_id=%s AND fact_id<>%s", (section_id, fact_id))
        display_order = int(cur.fetchone()[0])
        cur.execute("INSERT INTO budget.document_section_fact (document_section_id,fact_id,display_order) VALUES (%s,%s,%s) ON CONFLICT (document_section_id,fact_id) DO UPDATE SET display_order=EXCLUDED.display_order", (section_id, fact_id, display_order))
        fact_count += 1

    strategic_fact_ids = []
    for order, record in enumerate(strategic["facts"], 1):
        cur.execute(
            """INSERT INTO budget.fact (municipality_id,source_document_id,fact_key,fact_kind,title,body_text,content_json,effective_from,effective_to,review_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,'2022-01-01','2026-12-31','approved')
               ON CONFLICT (source_document_id,fact_key) DO UPDATE SET title=EXCLUDED.title,body_text=EXCLUDED.body_text,
                 content_json=EXCLUDED.content_json,review_status='approved' RETURNING id""",
            (municipality_id, strategic_document_id, record["key"], record["kind"], record["title"], record["body"],
             Jsonb({"blocks": record["blocks"]})),
        )
        fact_id = int(cur.fetchone()[0])
        strategic_fact_ids.append(fact_id)
        cur.execute("INSERT INTO budget.fact_source (fact_id,source_page_id,source_role,source_order) VALUES (%s,%s,'primary',0) ON CONFLICT DO NOTHING", (fact_id, strategic_page_ids[record["source_page"]]))
        for edition in payload["editions"]:
            section_id = section_ids[(edition, "strategic-plan")]
            cur.execute("INSERT INTO budget.document_section_fact (document_section_id,fact_id,display_order) VALUES (%s,%s,%s) ON CONFLICT (document_section_id,fact_id) DO UPDATE SET display_order=EXCLUDED.display_order", (section_id, fact_id, order))
        fact_count += 1

    project_fact_count = 0
    cur.execute(
        """SELECT p.id,p.capital_project_id,p.document_id,p.field_key,p.raw_value,p.normalized_value,
                  COALESCE(p.source_page_id,profile_page.source_page_id),
                  poa.organization_unit_id
             FROM budget.capital_project_profile p
             JOIN budget.budget_edition be ON be.document_id=p.document_id
             LEFT JOIN LATERAL (
               SELECT sp.id AS source_page_id FROM budget.source_table_row r
               JOIN budget.source_table_page stp ON stp.source_table_id=r.source_table_id
               JOIN budget.source_page sp ON sp.id=stp.source_page_id
               WHERE r.id=p.source_row_id ORDER BY stp.page_order LIMIT 1
             ) profile_page ON true
             LEFT JOIN LATERAL (SELECT organization_unit_id FROM budget.project_organization_assignment a
               WHERE a.capital_project_id=p.capital_project_id AND a.assignment_status='approved' ORDER BY a.id LIMIT 1) poa ON true
            WHERE p.review_status='approved' ORDER BY p.document_id,p.capital_project_id,p.field_key"""
    )
    title_map = {"title": "Project title", "project": "Project", "department": "Department", "description": "Project Description", "strategic_alignment": "Strategic Alignment"}
    document_to_edition = {value: key for key, value in document_ids.items()}
    for profile_id, project_id, document_id, field_key, raw_value, normalized_value, source_page_id, organization_unit_id in cur.fetchall():
        value = normalized_value or raw_value
        if not value or not value.strip():
            cur.execute(
                "DELETE FROM budget.fact WHERE source_document_id=%s AND fact_key=%s",
                (document_id, f"project-profile-{profile_id}"),
            )
            continue
        kind = "narrative" if field_key == "description" else ("list" if field_key == "strategic_alignment" else "attribute")
        blocks = structured_blocks(value, kind)
        cur.execute(
            """INSERT INTO budget.fact
               (municipality_id,source_document_id,fact_key,fact_kind,title,body_text,content_json,organization_unit_id,capital_project_id,review_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'approved')
               ON CONFLICT (source_document_id,fact_key) DO UPDATE SET fact_kind=EXCLUDED.fact_kind,title=EXCLUDED.title,
                 body_text=EXCLUDED.body_text,content_json=EXCLUDED.content_json,organization_unit_id=EXCLUDED.organization_unit_id,
                 capital_project_id=EXCLUDED.capital_project_id,review_status='approved' RETURNING id""",
            (municipality_id, document_id, f"project-profile-{profile_id}", kind, title_map.get(field_key, field_key.replace("_", " ").title()),
             blocks_text(blocks), Jsonb({"profile_field": field_key, "raw_value": raw_value,
                                        "normalized_value": normalized_value, "blocks": blocks}), organization_unit_id, project_id),
        )
        fact_id = int(cur.fetchone()[0])
        if source_page_id:
            cur.execute("INSERT INTO budget.fact_source (fact_id,source_page_id,source_role,source_order) VALUES (%s,%s,'primary',0) ON CONFLICT DO NOTHING", (fact_id, source_page_id))
        section_id = section_ids[(document_to_edition[int(document_id)], "capital-budget")]
        cur.execute("SELECT COALESCE(max(display_order),0)+1 FROM budget.document_section_fact WHERE document_section_id=%s AND fact_id<>%s", (section_id, fact_id))
        display_order = int(cur.fetchone()[0])
        cur.execute("INSERT INTO budget.document_section_fact (document_section_id,fact_id,display_order) VALUES (%s,%s,%s) ON CONFLICT (document_section_id,fact_id) DO UPDATE SET display_order=EXCLUDED.display_order", (section_id, fact_id, display_order))
        project_fact_count += 1

    project_department_count = 0
    department_targets = {
        "environment and sustainability": "environment-sustainability",
        "enivronment and sustainability": "environment-sustainability",
        "charlottetown fire department": "fire-emergency-preparedness",
        "parks and recreation": "parks-recreation",
        "charlottetown police services": "police",
        "public works": "public-works",
        "water and sewer utility": "water-sewer",
    }
    cur.execute(
        """SELECT p.document_id,p.capital_project_id,cp.reporting_entity_id,sp.id,sp.pdf_page_number
             FROM budget.capital_project_profile p JOIN budget.capital_project cp ON cp.id=p.capital_project_id
             JOIN budget.source_table_row r ON r.id=p.source_row_id
             JOIN budget.source_table_page stp ON stp.source_table_id=r.source_table_id
             JOIN budget.source_page sp ON sp.id=stp.source_page_id
            WHERE p.review_status='approved'
              AND NOT EXISTS (SELECT 1 FROM budget.capital_project_profile existing_department
                WHERE existing_department.document_id=p.document_id AND existing_department.capital_project_id=p.capital_project_id
                  AND existing_department.field_key='department' AND existing_department.review_status='approved')
            GROUP BY p.document_id,p.capital_project_id,cp.reporting_entity_id,sp.id,sp.pdf_page_number
            ORDER BY p.document_id,sp.pdf_page_number"""
    )
    for document_id, project_id, reporting_entity_id, source_page_id, page_number in cur.fetchall():
        edition = document_to_edition[int(document_id)]
        text = raw_page(edition, int(page_number))
        match = re.search(r"Department:\s*(.+?)(?=\n\s*Project:)", text, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        raw_department = re.sub(r"\s+", " ", match.group(1)).strip()
        target_key = department_targets.get(raw_department.casefold())
        if not target_key:
            continue
        organization_unit_id = org_ids.get(target_key)
        if target_key == "water-sewer":
            cur.execute("SELECT id FROM budget.organization_unit WHERE reporting_entity_id=%s AND unit_key='water-sewer' ORDER BY effective_from DESC,id DESC LIMIT 1", (reporting_entity_id,))
            row = cur.fetchone()
            if row:
                organization_unit_id = int(row[0])
            else:
                cur.execute("INSERT INTO budget.organization_unit (reporting_entity_id,unit_key,display_name,unit_type,effective_from) VALUES (%s,'water-sewer','Charlottetown Water and Sewer','department','2024-04-01') RETURNING id", (reporting_entity_id,))
                organization_unit_id = int(cur.fetchone()[0])
        cur.execute(
            """INSERT INTO budget.fact
               (municipality_id,source_document_id,fact_key,fact_kind,title,body_text,content_json,organization_unit_id,capital_project_id,review_status)
               VALUES (%s,%s,%s,'attribute','Department',%s,%s,%s,%s,'approved')
               ON CONFLICT (source_document_id,fact_key) DO UPDATE SET body_text=EXCLUDED.body_text,content_json=EXCLUDED.content_json,
                 organization_unit_id=EXCLUDED.organization_unit_id,capital_project_id=EXCLUDED.capital_project_id,review_status='approved'
               RETURNING id""",
            (municipality_id, document_id, f"project-department-{project_id}", raw_department,
             Jsonb({"profile_field": "department", "raw_value": raw_department,
                    "blocks": [{"type": "paragraph", "text": raw_department}]}), organization_unit_id, project_id),
        )
        fact_id = int(cur.fetchone()[0])
        cur.execute("INSERT INTO budget.fact_source (fact_id,source_page_id,source_role,source_order) VALUES (%s,%s,'primary',0) ON CONFLICT DO NOTHING", (fact_id, source_page_id))
        section_id = section_ids[(edition, "capital-budget")]
        cur.execute("SELECT COALESCE(max(display_order),0)+1 FROM budget.document_section_fact WHERE document_section_id=%s AND fact_id<>%s", (section_id, fact_id))
        cur.execute("INSERT INTO budget.document_section_fact (document_section_id,fact_id,display_order) VALUES (%s,%s,%s) ON CONFLICT (document_section_id,fact_id) DO UPDATE SET display_order=EXCLUDED.display_order", (section_id, fact_id, int(cur.fetchone()[0])))
        if organization_unit_id:
            source_key = f"{document_id}|{project_id}|{raw_department}"
            cur.execute("SELECT id FROM budget.normalization_decision WHERE source_entity_type='capital_project_profile_department' AND source_entity_key=%s AND target_entity_type='organization_unit' AND target_entity_id=%s ORDER BY id LIMIT 1", (source_key, organization_unit_id))
            decision = cur.fetchone()
            if decision:
                decision_id = int(decision[0])
            else:
                cur.execute("INSERT INTO budget.normalization_decision (source_entity_type,source_entity_key,target_entity_type,target_entity_id,decision,rationale,reviewer,decided_at) VALUES ('capital_project_profile_department',%s,'organization_unit',%s,'approved','Exact Department field from the capital project profile.','project-owner-breaking-budget-redesign-2026-07-13',now()) RETURNING id", (source_key, organization_unit_id))
                decision_id = int(cur.fetchone()[0])
            cur.execute(
                """INSERT INTO budget.project_organization_assignment
                   (capital_project_id,organization_unit_id,assignment_status,mapping_basis,normalization_decision_id,rationale)
                   VALUES (%s,%s,'approved','profile_department',%s,'Exact Department field from the capital project profile.')
                   ON CONFLICT (capital_project_id,organization_unit_id) DO UPDATE SET assignment_status='approved',
                     mapping_basis='profile_department',normalization_decision_id=EXCLUDED.normalization_decision_id,rationale=EXCLUDED.rationale""",
                (project_id, organization_unit_id, decision_id),
            )
        project_department_count += 1

    appendix_observations, publication_snapshot_id = import_2026_appendix_observations(
        cur, municipality_id, document_ids["2026-2027"], section_ids
    )
    display_column_labels = apply_display_column_labels(cur, document_ids)
    return {
        "sections": len(section_ids),
        "section_observations": section_observation_count,
        "source_facts": fact_count,
        "project_facts": project_fact_count,
        "project_department_facts": project_department_count,
        "appendix_observations": appendix_observations,
        "publication_snapshot_id": publication_snapshot_id,
        "display_column_labels": display_column_labels,
        "guides": len(guide_ids),
        "strategic_document_id": strategic_document_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    payload = build_payload()
    report = {"artifact": str(OUTPUT_PATH.relative_to(ROOT)).replace("\\", "/"), "fact_count": len(payload["facts"]), "applied": False}
    if args.apply:
        with psycopg.connect(db_url()) as connection, connection.cursor() as cur:
            report.update(apply_payload(cur, payload))
            connection.commit()
        report["applied"] = True
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

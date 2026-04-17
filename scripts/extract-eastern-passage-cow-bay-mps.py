from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "eastern-passage-cow-bay-municipal-planning-strategy.pdf"
OUTPUT_ROOT = ROOT / "data" / "municipal-planning-strategy" / "eastern-passage-cow-bay"
SECTION_DIR = OUTPUT_ROOT / "sections"
PDF_TO_MPS_PAGE_OFFSET = 8


@dataclass(frozen=True)
class SectionSpec:
    slug: str
    section_label_raw: str
    title_label_raw: str
    pdf_page_start: int
    pdf_page_end: int
    section_type: str
    status: str = "active"


SECTION_SPECS = [
    SectionSpec("introduction", "INTRODUCTION", "INTRODUCTION", 9, 9, "introduction"),
    SectionSpec("section-i", "SECTION I", "SECTION I", 10, 10, "citywide"),
    SectionSpec("plan-area-profile", "SECTION I", "PLAN AREA PROFILE", 11, 19, "citywide"),
    SectionSpec(
        "environmental-health-services",
        "SECTION II",
        "ENVIRONMENTAL HEALTH SERVICES",
        20,
        30,
        "citywide",
    ),
    SectionSpec(
        "environmental-protection",
        "SECTION II",
        "ENVIRONMENTAL PROTECTION - (RC-Jan 27/98;M-Apr 27/98)",
        31,
        36,
        "citywide",
    ),
    SectionSpec("transportation-services", "SECTION II", "TRANSPORTATION SERVICES", 37, 42, "citywide"),
    SectionSpec("recreation", "SECTION II", "RECREATION", 43, 43, "citywide"),
    SectionSpec("education", "SECTION II", "EDUCATION", 44, 45, "citywide"),
    SectionSpec(
        "protection-and-emergency-services",
        "SECTION II",
        "PROTECTION AND EMERGENCY SERVICES",
        46,
        47,
        "citywide",
    ),
    SectionSpec(
        "social-housing-and-rehabilitation",
        "SECTION II",
        "SOCIAL HOUSING AND REHABILITATION",
        48,
        48,
        "citywide",
    ),
    SectionSpec(
        "construction-and-demolition-waste-management-strategy",
        "SECTION II",
        "CONSTRUCTION AND DEMOLITION WASTE MANAGEMENT STRATEGY (RC-Sep 10/02;E-Nov 9/02)",
        49,
        53,
        "citywide",
    ),
    SectionSpec(
        "infrastructure-charges",
        "SECTION II",
        "INFRASTRUCTURE CHARGES (RC-Jul 2/02;E-Aug 17/02)",
        54,
        57,
        "citywide",
    ),
    SectionSpec(
        "interim-growth-management",
        "SECTION II",
        "INTERIM GROWTH MANAGEMENT (RC-Apr 13/04;E-Apr 22/04)",
        58,
        65,
        "citywide",
    ),
    SectionSpec("land-use-intent", "SECTION III", "LAND USE INTENT", 66, 67, "citywide"),
    SectionSpec(
        "urban-residential-designation",
        "SECTION III",
        "URBAN RESIDENTIAL DESIGNATION",
        68,
        81,
        "citywide",
    ),
    SectionSpec(
        "morris-russell-lake-secondary-planning-strategy",
        "SECTION III",
        "MORRIS-RUSSELL LAKE SECONDARY PLANNING STRATEGY",
        82,
        96,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "rural-area-designation",
        "SECTION III",
        "RURAL AREA DESIGNATION (RC-Jan 27/98;M-Apr 27/98)",
        97,
        101,
        "citywide",
    ),
    SectionSpec(
        "commercial-designation",
        "SECTION III",
        "COMMERCIAL DESIGNATION",
        102,
        106,
        "citywide",
    ),
    SectionSpec(
        "industrial-mix-designation",
        "SECTION III",
        "INDUSTRIAL MIX DESIGNATION",
        107,
        107,
        "citywide",
    ),
    SectionSpec(
        "industrial-designation",
        "SECTION III",
        "INDUSTRIAL DESIGNATION",
        108,
        110,
        "citywide",
    ),
    SectionSpec(
        "community-facility-designation",
        "SECTION III",
        "COMMUNITY FACILITY DESIGNATION",
        111,
        112,
        "citywide",
    ),
    SectionSpec(
        "special-area-designation",
        "SECTION III",
        "SPECIAL AREA DESIGNATION",
        113,
        115,
        "citywide",
    ),
    SectionSpec(
        "plan-amendment-designation",
        "SECTION III",
        "PLAN AMENDMENT DESIGNATION",
        116,
        116,
        "citywide",
    ),
    SectionSpec("implementation", "IMPLEMENTATION", "IMPLEMENTATION", 117, 122, "implementation"),
    SectionSpec(
        "schedule-1-1948-shore-road",
        "Schedule 1",
        "Schedule 1: 1948 Shore Road (RC-Sep 11/12; E-Oct 6/12)",
        123,
        123,
        "appendix",
    ),
    SectionSpec(
        "appendix-a-urban-road-classification-system",
        "APPENDIX A",
        "APPENDIX A: URBAN ROAD CLASSIFICATION SYSTEM",
        124,
        125,
        "appendix",
    ),
    SectionSpec("amendments", "AMENDMENTS", "MUNICIPAL PLANNING STRATEGY - EASTERN PASSAGE/COW BAY AMENDMENTS", 126, 127, "appendix"),
]


MAP_FEATURE_CLASS_RULES = [
    ("future_land_use_area", ["generalized future land use", "future land use and transportation plan"]),
    ("planning_area_boundary", ["regional context", "service boundary"]),
    ("transportation_corridor", ["transportation", "urban road classification"]),
    ("environmental_constraint_area", ["environmental constraints"]),
    ("municipal_service_area", ["trunk sewerage", "water service district"]),
    ("development_sub_area", ["secondary plan"]),
    ("site_specific_plan_area", ["1948 shore road"]),
]


HEADING_PREFIXES = (
    "SECTION ",
    "Map ",
    "MAP ",
    "Schedule ",
    "SCHEDULE ",
    "Objective",
    "Objectives",
    "Policy ",
)


POLICY_LABEL_RE = re.compile(r"^((?:\d+[A-Z]?)(?:\.\d+[A-Z]?)*\.?[A-Z]?)[.)]?\s+(.*)$")
POLICY_NAMED_RE = re.compile(
    r"^(Policy\s+(?=[A-Za-z0-9/.-]*[A-Za-z])[A-Za-z0-9/.-]+(?:\([0-9A-Za-z.]+\))*(?:\s*-\s*[A-Za-z0-9]+)?)\s*:?\s*(.*)$"
)
POLICY_CODE_RE = re.compile(r"^([A-Z]{1,6}(?:/[A-Z]{1,6})?-\d+[A-Za-z]*(?:\([A-Za-z0-9.]+\))*)(?:\s+(.*))?$")
INLINE_POLICY_CODE_RE = re.compile(r"([A-Z]{1,6}(?:/[A-Z]{1,6})?-\d+[A-Za-z]*(?:\([A-Za-z0-9.]+\))*)\s+")
LIST_POLICY_RE = re.compile(r"^([0-9A-Z.,\sand()/-]+?)\s+[.-]\s+(Repealed.*|Deleted.*)$", re.IGNORECASE)
SUBCLAUSE_RE = re.compile(r"^(-|\([A-Za-z0-9.]+\)|[A-Za-z0-9.]+\)|[0-9]+[.)])\s+(.*)$")
MAP_CAPTION_RE = re.compile(r"^(Map|MAP)\s+\d+[A-Za-z()/-]*:|^Schedule\s+(?:[A-Za-z0-9-]+|[IVXLC]+):")
TOPIC_HEADING_RE = re.compile(r"^\d+[A-Z]?\.\s+[A-Z][A-Z0-9 ,&'()/.-]+$")
UPPERCASE_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 /&,'()-.:-]+$")
TITLE_HEADING_RE = re.compile(r"^(?:[A-Z][A-Za-z0-9'&/-]*)(?:\s+[A-Z][A-Za-z0-9'&/-]*){0,12}:?$")
FOOTNOTE_START_RE = re.compile(r"^\d+\s+\d+\s+.+$")
INLINE_SUBCLAUSE_RE = re.compile(r"(?:(?<=^)|(?<=\s)|(?<=;))(\([A-Za-z0-9.]+\)|[A-Za-z0-9.]+\)|[0-9]+[.)])\s+")

SECTION_POLICY_PREFIXES = {
    "environmental-health-services": {"E"},
    "environmental-protection": {"EP"},
    "construction-and-demolition-waste-management-strategy": {"SW"},
    "infrastructure-charges": {"IC"},
    "interim-growth-management": {"IGM"},
    "transportation-services": {"TR"},
    "recreation": {"REC"},
    "education": {"ED"},
    "protection-and-emergency-services": {"PS"},
    "social-housing-and-rehabilitation": {"SH"},
    "urban-residential-designation": {"UR"},
    "morris-russell-lake-secondary-planning-strategy": {"ML"},
    "rural-area-designation": {"RA"},
    "commercial-designation": {"COM"},
    "industrial-mix-designation": {"IMD"},
    "industrial-designation": {"IND"},
    "community-facility-designation": {"CF"},
    "special-area-designation": {"SA"},
    "plan-amendment-designation": {"PA"},
    "implementation": {"IM"},
}

ADDITIONAL_MAP_REFERENCES = [
    ("Map 1", "Generalized Future Land Use Map (RC-Jan 27/98;M-Apr 27/98)", "future_land_use_area", 9),
    ("Map 2", "Trunk Sewerage System", "municipal_service_area", 9),
    ("Map 2a", "Water Service Districts (C-Aug 29/94;M-Oct 21/94)", "municipal_service_area", 9),
    ("Map 3", "Transportation", "transportation_corridor", 9),
    ("Map 4", "Environmental Constraints (RC-Jan 27/98;M-Apr 27/98)", "environmental_constraint_area", 9),
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    cleaned = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return cleaned.rstrip()


def canonicalize_section_label(value: str) -> str:
    return compact_space(normalize_line(value)).replace("&", "AND")


def split_embedded_policy_code_lines(line: str) -> list[str]:
    return [line]


def mps_page_from_pdf_page(pdf_page: int) -> int | None:
    if pdf_page <= PDF_TO_MPS_PAGE_OFFSET:
        return None
    return pdf_page - PDF_TO_MPS_PAGE_OFFSET


def extract_lines(reader: PdfReader) -> list[dict]:
    rows: list[dict] = []
    for pdf_page, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        for raw_line in raw_text.splitlines():
            line = normalize_line(raw_line).strip()
            if not line:
                continue
            if re.match(r"^Eastern Passage/Cow Bay Municipal Planning Strategy Page \d+$", line):
                continue
            if re.fullmatch(r"Page \d+", line):
                continue
            if line.startswith("APPENDIX A") and pdf_page == 124:
                rows.append({"pdf_page": pdf_page, "mps_page": mps_page_from_pdf_page(pdf_page), "text": line})
                continue
            if FOOTNOTE_START_RE.match(line) and pdf_page not in {121, 122, 123, 124}:
                if re.search(r"\bCouncil\b", line) or re.search(r"\b199\d\b|\b20\d{2}\b", line):
                    continue
            for segment in split_embedded_policy_code_lines(line):
                rows.append(
                    {
                        "pdf_page": pdf_page,
                        "mps_page": mps_page_from_pdf_page(pdf_page),
                        "text": segment,
                    }
                )
    return rows


def section_rows(lines: list[dict], spec: SectionSpec) -> list[dict]:
    rows = [row for row in lines if spec.pdf_page_start <= row["pdf_page"] <= spec.pdf_page_end]
    if spec.slug == "implementation":
        for index, row in enumerate(rows):
            if canonicalize_section_label(row["text"]).startswith("Schedule 1"):
                return rows[:index]
            if canonicalize_section_label(row["text"]).startswith("APPENDIX A"):
                return rows[:index]
    if spec.slug == "transportation-services":
        for index, row in enumerate(rows):
            if canonicalize_section_label(row["text"]) == canonicalize_section_label(spec.title_label_raw):
                return rows[index:]
    return rows


def classify_policy_type(section_type: str, text: str) -> str:
    normalized = text.lower()
    if "repealed" in normalized:
        return "repealed"
    if "deleted" in normalized:
        return "deleted"
    if section_type == "implementation":
        return "implementation_policy"
    if "generalized future land use map" in normalized or "map " in normalized:
        return "map_interpretation_policy"
    if "designation" in normalized or "designated" in normalized:
        return "designation_policy"
    if "development agreement" in normalized and "shall consider" in normalized:
        return "development_agreement_criteria"
    return "policy_statement"


def extract_modality(text: str) -> str | None:
    normalized = text.lower()
    for token in ("shall", "should", "may"):
        if re.search(rf"\b{token}\b", normalized):
            return token
    return None


def feature_class_for_label(label: str) -> str:
    normalized = label.lower()
    for feature_class, hints in MAP_FEATURE_CLASS_RULES:
        if any(hint in normalized for hint in hints):
            return feature_class
    return "policy_map_reference"


def looks_like_title_heading(text: str) -> bool:
    if text.startswith(HEADING_PREFIXES):
        return False
    if len(text) > 90 or len(text.split()) > 12:
        return False
    if text.endswith(".") and not text.endswith(")."):
        return False
    return bool(TITLE_HEADING_RE.match(text))


def normalize_policy_reference(label: str) -> str:
    value = compact_space(label.replace("Policy ", "").replace("Policies ", ""))
    value = value.replace("-l", "-1").replace("-I", "-1")
    return value.rstrip(":")


def policy_prefix(label: str) -> str:
    normalized = normalize_policy_reference(label)
    return normalized.split("-", 1)[0]


def policy_number(label: str) -> int | None:
    normalized = normalize_policy_reference(label)
    match = re.match(r"^[A-Z]{1,6}/?[A-Z]{0,6}-(\d+)", normalized)
    if not match:
        return None
    return int(match.group(1))


def is_policy_label_allowed(spec: SectionSpec, label: str) -> bool:
    allowed = SECTION_POLICY_PREFIXES.get(spec.slug)
    if not allowed:
        return True
    return policy_prefix(label) in allowed


def split_map_label_text(text: str) -> tuple[str, str]:
    if ":" in text:
        label, rest = text.split(":", 1)
        return compact_space(label + ":"), compact_space(rest)
    return compact_space(text), ""


def extract_inline_subclauses(text: str) -> list[tuple[str, str]]:
    matches = list(INLINE_SUBCLAUSE_RE.finditer(text))
    if not matches:
        return []
    results: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        clause_label = match.group(1)
        clause_text = compact_space(text[start:end].strip(" ;"))
        if clause_text:
            results.append((clause_label, clause_text))
    return results


def parse_map_reference(row: dict, spec: SectionSpec) -> dict:
    source_label_raw, title = split_map_label_text(row["text"])
    reference_type = "schedule" if source_label_raw.lower().startswith("schedule ") else "map"
    feature_class = feature_class_for_label(source_label_raw + " " + title)
    target = "spatial_features.geom" if feature_class.endswith(("_area", "_boundary")) or feature_class == "transportation_corridor" else "spatial_features.attributes"
    return {
        "feature_key": slugify(f"{source_label_raw.rstrip(':')} {title}"),
        "reference_type": reference_type,
        "feature_class": feature_class,
        "source_label_raw": source_label_raw,
        "title_text": title,
        "pdf_page_start": row["pdf_page"],
        "pdf_page_end": row["pdf_page"],
        "mps_page_start": row["mps_page"],
        "mps_page_end": row["mps_page"],
        "section_label_raw": spec.section_label_raw,
        "section_slug": spec.slug,
        "planned_postgis_target": target,
    }


def spatial_backlog_entries(refs: list[dict], spec: SectionSpec) -> list[dict]:
    entries = []
    for ref in refs:
        entries.append(
            {
                "feature_key": ref["feature_key"],
                "feature_class": ref["feature_class"],
                "source_document_page": ref["pdf_page_start"],
                "source_label_raw": ref["source_label_raw"],
                "reason": (
                    "Referenced by the Eastern Passage/Cow Bay Municipal Planning Strategy and "
                    "required for later PostGIS linkage between policy text and mapped planning areas."
                ),
                "planned_postgis_target": ref["planned_postgis_target"],
                "section_label_raw": spec.section_label_raw,
                "section_slug": spec.slug,
                "source_type": "manual_or_vector_digitization_backlog",
            }
        )
    return entries


def additional_map_references() -> list[dict]:
    refs = []
    for source_label_raw, title, feature_class, pdf_page in ADDITIONAL_MAP_REFERENCES:
        target = "spatial_features.geom" if feature_class.endswith(("_area", "_boundary")) or feature_class == "transportation_corridor" else "spatial_features.attributes"
        refs.append(
            {
                "feature_key": slugify(f"{source_label_raw} {title}"),
                "reference_type": "map",
                "feature_class": feature_class,
                "source_label_raw": source_label_raw,
                "title_text": title,
                "pdf_page_start": pdf_page,
                "pdf_page_end": pdf_page,
                "mps_page_start": mps_page_from_pdf_page(pdf_page),
                "mps_page_end": mps_page_from_pdf_page(pdf_page),
                "section_label_raw": "INTRODUCTION",
                "section_slug": "introduction",
                "planned_postgis_target": target,
            }
        )
    return refs


def additional_spatial_backlog_entries(refs: list[dict]) -> list[dict]:
    entries = []
    for ref in refs:
        entries.append(
            {
                "feature_key": ref["feature_key"],
                "feature_class": ref["feature_class"],
                "source_document_page": ref["pdf_page_start"],
                "source_label_raw": ref["source_label_raw"],
                "reason": (
                    "Referenced as a legal map by the Eastern Passage/Cow Bay Municipal Planning Strategy and "
                    "required for later PostGIS linkage between policy text and mapped planning areas."
                ),
                "planned_postgis_target": ref["planned_postgis_target"],
                "section_label_raw": ref["section_label_raw"],
                "section_slug": ref["section_slug"],
                "source_type": "manual_or_vector_digitization_backlog",
            }
        )
    return entries


def parse_section_content(spec: SectionSpec, rows: list[dict]) -> dict:
    if spec.section_type == "appendix":
        context_text = compact_space(" ".join(row["text"] for row in rows))
        maps = [parse_map_reference(row, spec) for row in rows if MAP_CAPTION_RE.match(row["text"])]
        context_blocks = []
        if context_text:
            context_blocks.append(
                {
                    "text": context_text,
                    "topic": None,
                    "pdf_page_start": spec.pdf_page_start,
                    "pdf_page_end": spec.pdf_page_end,
                    "mps_page_start": mps_page_from_pdf_page(spec.pdf_page_start),
                    "mps_page_end": mps_page_from_pdf_page(spec.pdf_page_end),
                }
            )
        return {
            "context_blocks": context_blocks,
            "objectives": [],
            "policies": [],
            "policy_subclauses": [],
            "map_references": [ref for ref in maps if ref["reference_type"] == "map"],
            "schedule_references": [ref for ref in maps if ref["reference_type"] == "schedule"],
            "spatial_features_needed": spatial_backlog_entries(maps, spec),
            "open_issues": [],
            "citations": {
                "pdf_page_start": spec.pdf_page_start,
                "pdf_page_end": spec.pdf_page_end,
                "mps_page_start": mps_page_from_pdf_page(spec.pdf_page_start),
                "mps_page_end": mps_page_from_pdf_page(spec.pdf_page_end),
            },
        }
    context_blocks: list[dict] = []
    objectives: list[dict] = []
    policies: list[dict] = []
    policy_subclauses: list[dict] = []
    maps: list[dict] = []
    open_issues: list[dict] = []

    current_context: list[dict] = []
    current_record: dict | None = None
    current_topic = ""

    def flush_context() -> None:
        nonlocal current_context
        if not current_context:
            return
        text = compact_space(" ".join(row["text"] for row in current_context))
        context_blocks.append(
            {
                "text": text,
                "topic": current_topic or None,
                "pdf_page_start": current_context[0]["pdf_page"],
                "pdf_page_end": current_context[-1]["pdf_page"],
                "mps_page_start": current_context[0]["mps_page"],
                "mps_page_end": current_context[-1]["mps_page"],
            }
        )
        current_context = []

    def flush_record() -> None:
        nonlocal current_record
        if current_record is None:
            return
        lines = current_record["lines"]
        if not lines:
            current_record = None
            return
        text = compact_space(" ".join(line["text"] for line in lines if line["text"]))
        record = {
            "label_raw": current_record["label_raw"],
            "text": text,
            "topic": current_topic or None,
            "pdf_page_start": lines[0]["pdf_page"],
            "pdf_page_end": lines[-1]["pdf_page"],
            "mps_page_start": lines[0]["mps_page"],
            "mps_page_end": lines[-1]["mps_page"],
        }
        if current_record["record_kind"] == "objective":
            objectives.append(record)
        else:
            policy_label_raw = normalize_policy_reference(current_record["label_raw"])
            policy = {
                "policy_label_raw": policy_label_raw,
                "policy_type": classify_policy_type(spec.section_type, text),
                "modality": extract_modality(text),
                **record,
            }
            policies.append(policy)
            for line in lines:
                clause_match = SUBCLAUSE_RE.match(line["text"])
                if clause_match:
                    clause_label_raw = clause_match.group(1)
                    clause_text = compact_space(clause_match.group(2))
                    policy_subclauses.append(
                        {
                            "policy_label_raw": policy_label_raw,
                            "clause_label_raw": clause_label_raw,
                            "clause_text": clause_text,
                            "modality": extract_modality(clause_text),
                            "topic": current_topic or None,
                            "pdf_page_start": line["pdf_page"],
                            "pdf_page_end": line["pdf_page"],
                            "mps_page_start": line["mps_page"],
                            "mps_page_end": line["mps_page"],
                        }
                    )
            for clause_label_raw, clause_text in extract_inline_subclauses(text):
                policy_subclauses.append(
                    {
                        "policy_label_raw": policy_label_raw,
                        "clause_label_raw": clause_label_raw,
                        "clause_text": clause_text,
                        "modality": extract_modality(clause_text),
                        "topic": current_topic or None,
                        "pdf_page_start": lines[0]["pdf_page"],
                        "pdf_page_end": lines[-1]["pdf_page"],
                        "mps_page_start": lines[0]["mps_page"],
                        "mps_page_end": lines[-1]["mps_page"],
                    }
                )
        current_record = None

    def set_topic(row: dict) -> None:
        nonlocal current_topic
        flush_context()
        flush_record()
        current_topic = row["text"]

    for row in rows:
        text = row["text"]
        canonical_text = canonicalize_section_label(text)
        if canonical_text in {
            canonicalize_section_label(spec.section_label_raw),
            canonicalize_section_label(spec.title_label_raw),
            "OBJECTIVES AND POLICIES",
            "IMPLEMENTATION POLICIES",
            "INTRODUCTION",
        }:
            flush_context()
            flush_record()
            continue
        if MAP_CAPTION_RE.match(text):
            flush_context()
            flush_record()
            maps.append(parse_map_reference(row, spec))
            continue
        if text.endswith(" OBJECTIVE") or text.endswith(" OBJECTIVES"):
            flush_context()
            flush_record()
            current_record = {"record_kind": "objective", "label_raw": text, "lines": []}
            continue
        if POLICY_NAMED_RE.match(text):
            match = POLICY_NAMED_RE.match(text)
            assert match is not None
            label = match.group(1)
            rest = match.group(2).strip()
            if policy_prefix(label) != "IGM" or rest.startswith((",", ".")):
                if current_record:
                    current_record["lines"].append(row)
                else:
                    current_context.append(row)
                continue
            if not is_policy_label_allowed(spec, label):
                if current_record:
                    current_record["lines"].append(row)
                else:
                    current_context.append(row)
                continue
            flush_context()
            flush_record()
            lines = [{**row, "text": rest}] if rest else [{**row, "text": ""}]
            current_record = {"record_kind": "policy", "label_raw": label, "lines": lines}
            continue
        if POLICY_CODE_RE.match(text):
            match = POLICY_CODE_RE.match(text)
            assert match is not None
            label = match.group(1)
            if current_record and policy_prefix(label) == policy_prefix(current_record["label_raw"]):
                label_number = policy_number(label)
                current_number = policy_number(current_record["label_raw"])
                if label_number is not None and current_number is not None and label_number < current_number:
                    current_record["lines"].append(row)
                    continue
            if not is_policy_label_allowed(spec, label):
                if current_record:
                    current_record["lines"].append(row)
                else:
                    current_context.append(row)
                continue
            flush_context()
            flush_record()
            rest = (match.group(2) or "").strip()
            lines = [{**row, "text": rest}] if rest else [{**row, "text": ""}]
            current_record = {"record_kind": "policy", "label_raw": label, "lines": lines}
            continue
        if UPPERCASE_HEADING_RE.match(text) and text not in {"OBJECTIVE", "OBJECTIVES"} and len(text) <= 120:
            if current_record:
                flush_record()
            current_context.append(row)
            continue
        if TOPIC_HEADING_RE.match(text):
            set_topic(row)
            continue
        if looks_like_title_heading(text):
            if current_record:
                flush_record()
            current_context.append(row)
            continue
        if text == "Policy Statements":
            if current_record:
                flush_record()
            current_context.append(row)
            continue
        if text.startswith("Objective") or text.startswith("Objectives"):
            flush_context()
            flush_record()
            current_record = {
                "record_kind": "objective",
                "label_raw": "Objective" if text.startswith("Objective") else "Objectives",
                "lines": [row],
            }
            continue
        if LIST_POLICY_RE.match(text):
            flush_context()
            flush_record()
            match = LIST_POLICY_RE.match(text)
            assert match is not None
            if not re.search(r"\d", match.group(1)):
                current_context.append(row)
                continue
            current_record = {
                "record_kind": "policy",
                "label_raw": compact_space(match.group(1)),
                "lines": [{**row, "text": match.group(2)}],
            }
            continue
        if current_record:
            current_record["lines"].append(row)
            continue
        current_context.append(row)

    flush_record()
    flush_context()

    for policy in policies:
        if re.search(r"\b\d+[A-Z]?(?:\.\d+[A-Z]?)+\b", policy["policy_label_raw"]):
            open_issues.append(
                {
                    "issue_type": "identifier_normalization_pending_review",
                    "section_label_raw": spec.section_label_raw,
                    "example_label_raw": policy["policy_label_raw"],
                    "reason": "MPS dotted policy identifiers are preserved raw in v1.",
                }
            )
            break

    return {
        "context_blocks": context_blocks,
        "objectives": objectives,
        "policies": policies,
        "policy_subclauses": policy_subclauses,
        "map_references": [ref for ref in maps if ref["reference_type"] == "map"],
        "schedule_references": [ref for ref in maps if ref["reference_type"] == "schedule"],
        "spatial_features_needed": spatial_backlog_entries(maps, spec),
        "open_issues": open_issues,
        "citations": {
            "pdf_page_start": spec.pdf_page_start,
            "pdf_page_end": spec.pdf_page_end,
            "mps_page_start": mps_page_from_pdf_page(spec.pdf_page_start),
            "mps_page_end": mps_page_from_pdf_page(spec.pdf_page_end),
        },
    }


def section_payload(spec: SectionSpec, parsed: dict) -> dict:
    return {
        "section_metadata": {
            "jurisdiction": "Halifax Regional Municipality",
            "document_name": "Eastern Passage/Cow Bay Municipal Planning Strategy",
            "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
            "section_label_raw": spec.section_label_raw,
            "title_label_raw": spec.title_label_raw,
            "section_slug": spec.slug,
            "section_type": spec.section_type,
            "status": spec.status,
            "pdf_page_start": spec.pdf_page_start,
            "pdf_page_end": spec.pdf_page_end,
            "mps_page_start": mps_page_from_pdf_page(spec.pdf_page_start),
            "mps_page_end": mps_page_from_pdf_page(spec.pdf_page_end),
        },
        "normalization_policy": {
            "policy_identifiers_preserved_raw": True,
            "normalized_paths_applied": False,
            "reason": "Dotted and mixed-format MPS policy identifiers have not been approved for hierarchy normalization in this repository context.",
        },
        **parsed,
    }


def document_payload(reader: PdfReader, sections: list[dict], maps: list[dict], backlog: list[dict]) -> dict:
    return {
        "document_metadata": {
            "jurisdiction": "Halifax Regional Municipality",
            "document_name": "Eastern Passage/Cow Bay Municipal Planning Strategy",
            "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
            "document_type": "official_plan_text",
            "effective_through": "2024-06-13",
            "page_count_pdf": len(reader.pages),
            "mps_page_offset_from_pdf": PDF_TO_MPS_PAGE_OFFSET,
            "metadata": {key.lstrip("/"): value for key, value in (reader.metadata or {}).items()},
        },
        "normalization_policy": {
            "policy_identifiers_preserved_raw": True,
            "normalized_paths_applied": False,
            "status": "pending_review_mps_dotted_identifier",
            "reason": "The repository has approved zoning clause normalization only. MPS dotted policy identifiers remain raw in v1.",
        },
        "ingestion_mapping": {
            "document_json_to_documents": "documents",
            "page_citations_to_document_pages": "document_pages",
            "extracted_policy_text_to_text_spans": "text_spans",
            "atomic_policy_controls_to_land_use_rules": "land_use_rules",
            "citywide_or_area_specific_links_to_rule_applicability": "rule_applicability",
            "digitized_map_features_to_spatial_features": "spatial_features",
        },
        "section_inventory": sections,
        "map_reference_count": len(maps),
        "spatial_feature_backlog_count": len(backlog),
    }


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    reader = PdfReader(str(SOURCE_PDF))
    lines = extract_lines(reader)

    SECTION_DIR.mkdir(parents=True, exist_ok=True)

    section_inventory = []
    all_maps: list[dict] = []
    all_backlog: list[dict] = []
    all_open_issues: list[dict] = [
        {
            "issue_type": "identifier_normalization_pending_review",
            "example_labels_raw": ["UR-4A", "Policy IGM-1"],
            "reason": "These MPS policy identifiers are approved as single unit terms. Other reviewed parenthetical examples are preserved raw in v1 pending a later normalized path field.",
        },
        {
            "issue_type": "table_of_contents_outline_absent",
            "reason": "The PDF does not expose bookmark outline entries through PyPDF, so section ranges are seeded from the text table of contents and page inspection.",
        },
    ]

    for spec in SECTION_SPECS:
        parsed = parse_section_content(spec, section_rows(lines, spec))
        payload = section_payload(spec, parsed)
        output_path = SECTION_DIR / f"{spec.slug}.json"
        write_json(output_path, payload)
        section_inventory.append(
            {
                "section_label_raw": spec.section_label_raw,
                "title_label_raw": spec.title_label_raw,
                "section_slug": spec.slug,
                "section_type": spec.section_type,
                "status": spec.status,
                "pdf_page_start": spec.pdf_page_start,
                "pdf_page_end": spec.pdf_page_end,
                "mps_page_start": mps_page_from_pdf_page(spec.pdf_page_start),
                "mps_page_end": mps_page_from_pdf_page(spec.pdf_page_end),
                "section_file": f"sections/{spec.slug}.json",
                "objective_count": len(payload["objectives"]),
                "policy_count": len(payload["policies"]),
                "policy_subclause_count": len(payload["policy_subclauses"]),
            }
        )
        all_maps.extend(payload["map_references"])
        all_maps.extend(payload["schedule_references"])
        all_backlog.extend(payload["spatial_features_needed"])
        all_open_issues.extend(payload["open_issues"])

    legal_maps = additional_map_references()
    all_maps.extend(legal_maps)
    all_backlog.extend(additional_spatial_backlog_entries(legal_maps))

    write_json(OUTPUT_ROOT / "document.json", document_payload(reader, section_inventory, all_maps, all_backlog))
    write_json(
        OUTPUT_ROOT / "maps.json",
        {
            "document_name": "Eastern Passage/Cow Bay Municipal Planning Strategy",
            "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
            "references": all_maps,
        },
    )
    write_json(
        OUTPUT_ROOT / "spatial-features-needed.json",
        {
            "document_name": "Eastern Passage/Cow Bay Municipal Planning Strategy",
            "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
            "spatial_features_needed": all_backlog,
        },
    )
    write_json(OUTPUT_ROOT / "open-issues.json", {"open_issues": all_open_issues})


if __name__ == "__main__":
    main()

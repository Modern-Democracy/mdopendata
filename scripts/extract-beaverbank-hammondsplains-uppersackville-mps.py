from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "beaverbank-hammondsplains-uppersackville-municipal-planning-strategy.pdf"
OUTPUT_ROOT = ROOT / "data" / "municipal-planning-strategy" / "beaverbank-hammondsplains-uppersackville"
SECTION_DIR = OUTPUT_ROOT / "sections"
PDF_TO_MPS_PAGE_OFFSET = 5
DOCUMENT_NAME = "Beaver Bank, Hammonds Plains and Upper Sackville Municipal Planning Strategy"
SOURCE_DOCUMENT_PATH = str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/")


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
    SectionSpec("introduction", "INTRODUCTION", "INTRODUCTION", 6, 7, "introduction"),
    SectionSpec("regional-context", "SECTION I", "REGIONAL CONTEXT", 8, 12, "citywide"),
    SectionSpec("plan-area-profile", "SECTION I", "PLAN AREA PROFILE", 13, 18, "citywide"),
    SectionSpec("land-use-intent", "SECTION II", "LAND USE INTENT", 19, 21, "citywide"),
    SectionSpec(
        "residential-growth-management",
        "SECTION II",
        "RESIDENTIAL GROWTH MANAGEMENT",
        22,
        24,
        "citywide",
    ),
    SectionSpec("mixed-use-designations", "SECTION II", "MIXED USE DESIGNATIONS", 25, 50, "citywide"),
    SectionSpec("residential-designation", "SECTION II", "RESIDENTIAL DESIGNATION", 51, 58, "citywide"),
    SectionSpec(
        "the-glen-arbour-integrated-golf-course-and-residential-community",
        "SECTION II",
        "THE GLEN ARBOUR INTEGRATED GOLF COURSE AND RESIDENTIAL COMMUNITY (RC-Apr 24/01;E-Jun 9/01)",
        59,
        64,
        "citywide",
    ),
    SectionSpec(
        "the-bedford-west-secondary-planning-strategy",
        "SECTION II",
        "THE BEDFORD WEST SECONDARY PLANNING STRATEGY (RC-Jun 2/09;EJun 27/09)",
        65,
        88,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "upper-hammonds-plains-community-designation",
        "SECTION II",
        "UPPER HAMMONDS PLAINS COMMUNITY DESIGNATION (RC-Jan 10/23;E-Feb 3/23)",
        89,
        95,
        "citywide",
    ),
    SectionSpec(
        "hammonds-plains-commercial-designation",
        "SECTION II",
        "HAMMONDS PLAINS COMMERCIAL DESIGNATION (RC-Feb 9/10;E-Apr 3/10)",
        96,
        97,
        "citywide",
    ),
    SectionSpec("rural-resource-designation", "SECTION II", "RURAL RESOURCE DESIGNATION", 98, 104, "citywide"),
    SectionSpec("watershed-designation", "SECTION II", "WATERSHED DESIGNATION", 105, 106, "citywide"),
    SectionSpec(
        "former-regional-sanitary-landfill-site-designation",
        "SECTION II",
        "FORMER REGIONAL SANITARY LANDFILL SITE DESIGNATION",
        107,
        109,
        "citywide",
    ),
    SectionSpec("provincial-park-designation", "SECTION II", "PROVINCIAL PARK DESIGNATION", 110, 110, "citywide"),
    SectionSpec("springfield-lake-designation", "SECTION II", "SPRINGFIELD LAKE DESIGNATION", 111, 114, "citywide"),
    SectionSpec("floodplain-designation", "SECTION II", "FLOODPLAIN DESIGNATION (RC-Apr29/25;E-May26/25)", 115, 120, "citywide"),
    SectionSpec(
        "infrastructure-charges",
        "SECTION II",
        "INFRASTRUCTURE CHARGES (RC-Jul 2/02;E-Aug 17/02)",
        121,
        124,
        "citywide",
    ),
    SectionSpec(
        "interim-growth-management",
        "SECTION II",
        "INTERIM GROWTH MANAGEMENT (RC-Apr 13/04;E-Apr 22/04)",
        125,
        132,
        "citywide",
    ),
    SectionSpec(
        "environmental-health-services",
        "SECTION III",
        "ENVIRONMENTAL HEALTH SERVICES",
        133,
        142,
        "citywide",
    ),
    SectionSpec(
        "construction-and-demolition-waste-management-strategy",
        "SECTION III",
        "CONSTRUCTION AND DEMOLITION WASTE MANAGEMENT STRATEGY (RC-Sep 10/02;E-Nov 9/02)",
        143,
        147,
        "citywide",
    ),
    SectionSpec("transportation-and-utilities", "SECTION III", "TRANSPORTATION AND UTILITIES", 148, 153, "citywide"),
    SectionSpec("recreation", "SECTION III", "RECREATION", 154, 157, "citywide"),
    SectionSpec("education", "SECTION III", "EDUCATION", 158, 160, "citywide"),
    SectionSpec("protection-services", "SECTION III", "PROTECTION SERVICES", 161, 162, "citywide"),
    SectionSpec("heritage", "SECTION III", "HERITAGE (RC-Mar 26/02;E-Apr 25/02)", 163, 163, "citywide"),
    SectionSpec("implementation", "SECTION IV", "IMPLEMENTATION", 164, 172, "implementation"),
    SectionSpec(
        "amendments-beaver-bank-hammonds-plains-upper-sackville",
        "MUNICIPAL PLANNING STRATEGY AMENDMENTS - BEAVER BANK, HAMMONDS PLAINS, UPPER SACKVILLE",
        "MUNICIPAL PLANNING STRATEGY AMENDMENTS - BEAVER BANK, HAMMONDS PLAINS, UPPER SACKVILLE",
        173,
        176,
        "appendix",
    ),
    SectionSpec(
        "schedule-p-17a-lands-of-the-r-1b-zone-monarch-rivendale-subdivision",
        "SCHEDULE P-17A: LANDS OF THE R-1b ZONE (MONARCH/RIVENDALE SUBDIVISION) (RC-Sep 13/11;E-Oct 19/11)",
        "SCHEDULE P-17A: LANDS OF THE R-1b ZONE (MONARCH/RIVENDALE SUBDIVISION) (RC-Sep 13/11;E-Oct 19/11)",
        177,
        177,
        "appendix",
    ),
]


MAP_FEATURE_CLASS_RULES = [
    ("future_land_use_area", ["generalized future land use", "land use designation"]),
    ("planning_area_boundary", ["study area", "plan area"]),
    ("watershed_area", ["watershed"]),
    ("municipal_service_area", ["water service", "sanitary sewer", "service boundary"]),
    ("transportation_corridor", ["transportation", "street network", "road access"]),
    ("development_sub_area", ["development sub-areas"]),
    ("community_concept_plan_area", ["community concept plan"]),
]


POLICY_NAMED_RE = re.compile(
    r"^(Policy\s+(?=[A-Za-z0-9/.-]*[A-Za-z])[A-Za-z0-9/.-]+(?:\([0-9A-Za-z.]+\))*(?:\s*-\s*[A-Za-z0-9]+)?)\s*:?\s*(.*)$"
)
POLICY_CODE_RE = re.compile(
    r"^([A-Za-z]{1,8}(?:/[A-Za-z]{1,8})?-\d+[A-Za-z]*(?:\.[A-Za-z0-9]+)*(?:\([A-Za-z0-9.]+\))*)(?:\s+(.*))?$"
)
LIST_POLICY_RE = re.compile(r"^([0-9A-Z.,\sand()/-]+?)\s+[.-]\s+(Repealed.*|Deleted.*)$", re.IGNORECASE)
SUBCLAUSE_RE = re.compile(r"^(-|\([A-Za-z0-9.]+\)|[A-Za-z0-9.]+\)|[0-9]+[.)])\s+(.*)$")
MAP_CAPTION_RE = re.compile(
    r"^(?:(?:Map|MAP)\s+[A-Za-z0-9(),/-]+:|(?:Schedule|SCHEDULE|SCHECULE)\s+[A-Za-z0-9(),/-]+:)"
)
TOPIC_HEADING_RE = re.compile(r"^\d+[A-Z]?\.\s+[A-Z][A-Z0-9 ,&'()/.-]+$")
UPPERCASE_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 /&,'()\-.:;]+$")
TITLE_HEADING_RE = re.compile(r"^(?:[A-Z][A-Za-z0-9'&/=+-]*)(?:\s+[A-Z][A-Za-z0-9'&/=+.-]*){0,14}:?$")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    cleaned = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    cleaned = cleaned.replace("\u2018", "'").replace("\u00a0", " ").replace("=s", "'s")
    cleaned = cleaned.replace("Aprotected area@", '"protected area"')
    return cleaned.rstrip()


def mps_page_from_pdf_page(pdf_page: int) -> int | None:
    if pdf_page <= PDF_TO_MPS_PAGE_OFFSET:
        return None
    return pdf_page - PDF_TO_MPS_PAGE_OFFSET


def extract_modality(text: str) -> str | None:
    normalized = f" {text.lower()} "
    for token in ("shall", "should", "may"):
        if f" {token} " in normalized:
            return token
    return None


def classify_policy_type(section_type: str, text: str) -> str:
    normalized = text.lower()
    if "repealed" in normalized:
        return "repealed"
    if "deleted" in normalized:
        return "deleted"
    if section_type == "implementation":
        return "implementation_policy"
    if "development agreement" in normalized and "shall have regard" in normalized:
        return "development_agreement_criteria"
    if "designation" in normalized or "designated" in normalized:
        return "designation_policy"
    if "map " in normalized or "schedule " in normalized:
        return "map_interpretation_policy"
    return "policy_statement"


def is_reference_continuation_text(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped:
        return True
    if stripped[0].islower() or stripped[0] in ";,.)":
        return True
    if stripped.lower().startswith("to "):
        return True
    lowered = f" {text.lower()} "
    if any(token in lowered for token in (" shall ", " should ", " may ")):
        return False
    return True


def feature_class_for_label(title_text: str) -> str:
    normalized = title_text.lower()
    for feature_class, needles in MAP_FEATURE_CLASS_RULES:
        if any(needle in normalized for needle in needles):
            return feature_class
    return "plan_reference_map"


def extract_lines(reader: PdfReader) -> list[dict]:
    rows: list[dict] = []
    header_re = re.compile(r"^Beaver Bank, Hammonds Plains and Upper Sackville MPS Page \d+$")
    for pdf_page, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        for raw_line in raw_text.splitlines():
            line = normalize_line(raw_line).strip()
            if not line:
                continue
            if header_re.match(line) or re.fullmatch(r"Page \d+", line):
                continue
            rows.append(
                {
                    "pdf_page": pdf_page,
                    "mps_page": mps_page_from_pdf_page(pdf_page),
                    "text": line,
                }
            )
    return rows


def section_rows(lines: list[dict], spec: SectionSpec) -> list[dict]:
    rows = [row for row in lines if spec.pdf_page_start <= row["pdf_page"] <= spec.pdf_page_end]
    titles = {
        compact_space(spec.title_label_raw),
        compact_space(spec.section_label_raw),
        compact_space(spec.title_label_raw.split(" (")[0]),
    }
    for index, row in enumerate(rows):
        text = compact_space(row["text"])
        if text in titles or any(text.startswith(title) for title in titles if title):
            return rows[index:]
    return rows


def looks_like_title_heading(text: str) -> bool:
    compact = compact_space(text)
    if len(compact) > 120 or not TITLE_HEADING_RE.match(compact):
        return False
    if extract_modality(compact):
        return False
    return compact == compact.title() or compact.isupper() or compact.endswith(":")


def parse_map_reference(row: dict, spec: SectionSpec) -> dict:
    text = compact_space(row["text"])
    match = re.match(
        r"^((?:(?:Map|MAP)\s+[A-Za-z0-9(),/-]+:|(?:Schedule|SCHEDULE|SCHECULE)\s+[A-Za-z0-9(),/-]+:))\s*(.*)$",
        text,
    )
    assert match is not None
    source_label_raw = compact_space(match.group(1))
    title_text = compact_space(match.group(2))
    reference_type = "schedule" if source_label_raw.lower().startswith(("schedule", "schecule")) else "map"
    feature_key = slugify(f"{source_label_raw} {title_text}")
    return {
        "feature_key": feature_key,
        "reference_type": reference_type,
        "feature_class": feature_class_for_label(title_text),
        "source_label_raw": source_label_raw,
        "title_text": title_text,
        "pdf_page_start": row["pdf_page"],
        "pdf_page_end": row["pdf_page"],
        "mps_page_start": row["mps_page"],
        "mps_page_end": row["mps_page"],
        "section_label_raw": spec.title_label_raw,
        "section_slug": spec.slug,
        "planned_postgis_target": "spatial_features",
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
                    "Referenced by the Beaver Bank, Hammonds Plains and Upper Sackville Municipal Planning "
                    "Strategy and required for later PostGIS linkage between policy text and mapped planning areas."
                ),
                "planned_postgis_target": ref["planned_postgis_target"],
                "section_label_raw": spec.title_label_raw,
                "section_slug": spec.slug,
                "source_type": "manual_or_vector_digitization_backlog",
            }
        )
    return entries


def build_context_block(context_rows: list[dict], topic: str | None) -> dict | None:
    if not context_rows:
        return None
    return {
        "text": compact_space(" ".join(row["text"] for row in context_rows)),
        "topic": topic,
        "pdf_page_start": context_rows[0]["pdf_page"],
        "pdf_page_end": context_rows[-1]["pdf_page"],
        "mps_page_start": context_rows[0]["mps_page"],
        "mps_page_end": context_rows[-1]["mps_page"],
    }


def append_subclauses(
    policy_label_raw: str,
    lines: list[dict],
    topic: str | None,
    sink: list[dict],
) -> None:
    current: dict | None = None
    for row in lines:
        match = SUBCLAUSE_RE.match(row["text"])
        if match:
            if current:
                sink.append(current)
            current = {
                "policy_label_raw": policy_label_raw,
                "subclause_label_raw": match.group(1),
                "text": compact_space(match.group(2)),
                "topic": topic,
                "pdf_page_start": row["pdf_page"],
                "pdf_page_end": row["pdf_page"],
                "mps_page_start": row["mps_page"],
                "mps_page_end": row["mps_page"],
            }
            continue
        if current:
            current["text"] = compact_space(f"{current['text']} {row['text']}")
            current["pdf_page_end"] = row["pdf_page"]
            current["mps_page_end"] = row["mps_page"]
    if current:
        sink.append(current)


def build_objective(record: dict, topic: str | None) -> dict:
    lines = record["lines"]
    text = compact_space(" ".join(row["text"] for row in lines))
    return {
        "label_raw": record["label_raw"],
        "text": text,
        "topic": topic,
        "pdf_page_start": lines[0]["pdf_page"],
        "pdf_page_end": lines[-1]["pdf_page"],
        "mps_page_start": lines[0]["mps_page"],
        "mps_page_end": lines[-1]["mps_page"],
    }


def build_policy(record: dict, spec: SectionSpec, topic: str | None, subclauses: list[dict]) -> dict:
    lines = record["lines"]
    append_subclauses(record["label_raw"], lines, topic, subclauses)
    text = compact_space(" ".join(row["text"] for row in lines))
    return {
        "policy_label_raw": record["label_raw"],
        "policy_type": classify_policy_type(spec.section_type, text),
        "modality": extract_modality(text),
        "label_raw": record["display_label_raw"],
        "text": text,
        "topic": topic,
        "pdf_page_start": lines[0]["pdf_page"],
        "pdf_page_end": lines[-1]["pdf_page"],
        "mps_page_start": lines[0]["mps_page"],
        "mps_page_end": lines[-1]["mps_page"],
    }


def repair_springfield_lake_policies(policies: list[dict]) -> list[dict]:
    repaired: list[dict] = []
    for policy in policies:
        if policy["policy_label_raw"] != "P-68" or "P-69 " not in policy["text"]:
            repaired.append(policy)
            continue
        prefix, remainder = policy["text"].split("P-69 ", 1)
        policy["text"] = compact_space(prefix)
        repaired.append(policy)

        if "P-70 Deleted" in remainder:
            p69_body, tail = remainder.split("P-70 Deleted", 1)
            p69 = {
                **policy,
                "policy_label_raw": "P-69",
                "label_raw": "P-69",
                "policy_type": "policy_statement",
                "modality": extract_modality(p69_body),
                "text": compact_space(p69_body),
                "pdf_page_start": 113,
                "pdf_page_end": 113,
                "mps_page_start": 108,
                "mps_page_end": 108,
            }
            p70 = {
                **policy,
                "policy_label_raw": "P-70",
                "label_raw": "P-70",
                "policy_type": "deleted",
                "modality": None,
                "text": "Deleted",
                "pdf_page_start": 113,
                "pdf_page_end": 113,
                "mps_page_start": 108,
                "mps_page_end": 108,
            }
            repaired.extend([p69, p70])
        else:
            repaired.append(
                {
                    **policy,
                    "policy_label_raw": "P-69",
                    "label_raw": "P-69",
                    "policy_type": "policy_statement",
                    "modality": extract_modality(remainder),
                    "text": compact_space(remainder),
                    "pdf_page_start": 113,
                    "pdf_page_end": 113,
                    "mps_page_start": 108,
                    "mps_page_end": 108,
                }
            )
    return repaired


def extract_policy_from_rows(rows: list[dict], label: str, stop_labels: tuple[str, ...]) -> dict | None:
    start_index: int | None = None
    collected: list[dict] = []
    for index, row in enumerate(rows):
        text = compact_space(row["text"])
        if start_index is None and text.startswith(f"{label} "):
            start_index = index
            collected.append({**row, "text": compact_space(text[len(label) :])})
            continue
        if start_index is None:
            continue
        if any(text.startswith(f"{stop} ") for stop in stop_labels):
            break
        collected.append(row)
    if not collected:
        return None
    text = compact_space(" ".join(row["text"] for row in collected))
    return {
        "policy_label_raw": label,
        "policy_type": "deleted" if "deleted" in text.lower() else "policy_statement",
        "modality": extract_modality(text),
        "label_raw": label,
        "text": "Deleted" if text.lower() == "deleted" else text,
        "topic": None,
        "pdf_page_start": collected[0]["pdf_page"],
        "pdf_page_end": collected[-1]["pdf_page"],
        "mps_page_start": collected[0]["mps_page"],
        "mps_page_end": collected[-1]["mps_page"],
    }


def parse_section_content(spec: SectionSpec, rows: list[dict]) -> dict:
    if spec.section_type == "appendix":
        refs = [parse_map_reference(row, spec) for row in rows if MAP_CAPTION_RE.match(compact_space(row["text"]))]
        context_rows = [row for row in rows if not MAP_CAPTION_RE.match(compact_space(row["text"]))]
        context_block = build_context_block(context_rows, None)
        return {
            "context_blocks": [context_block] if context_block else [],
            "objectives": [],
            "policies": [],
            "policy_subclauses": [],
            "map_references": [ref for ref in refs if ref["reference_type"] == "map"],
            "schedule_references": [ref for ref in refs if ref["reference_type"] == "schedule"],
            "spatial_features_needed": spatial_backlog_entries(refs, spec),
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
    topic: str | None = None

    def flush_context() -> None:
        nonlocal current_context
        block = build_context_block(current_context, topic)
        if block:
            context_blocks.append(block)
        current_context = []

    def flush_record() -> None:
        nonlocal current_record
        if not current_record:
            return
        if current_record["record_kind"] == "objective":
            objectives.append(build_objective(current_record, topic))
        else:
            policies.append(build_policy(current_record, spec, topic, policy_subclauses))
        current_record = None

    for row in rows:
        text = compact_space(row["text"])
        if not text:
            continue
        if MAP_CAPTION_RE.match(text):
            flush_context()
            flush_record()
            maps.append(parse_map_reference(row, spec))
            continue
        if text in {"Policy Statements", "Policy Intent"}:
            flush_context()
            flush_record()
            current_context.append(row)
            continue
        if TOPIC_HEADING_RE.match(text):
            flush_context()
            flush_record()
            topic = text
            continue
        if text.endswith(" OBJECTIVE") or text.endswith(" OBJECTIVES") or text in {"Objective", "Objectives", "Objectives:"}:
            flush_context()
            flush_record()
            current_record = {"record_kind": "objective", "label_raw": text.rstrip(":"), "lines": [row]}
            if text not in {"Objective", "Objectives", "Objectives:"}:
                continue
        if text.startswith("Objective") or text.startswith("Objectives"):
            flush_context()
            flush_record()
            current_record = {"record_kind": "objective", "label_raw": "Objective" if text.startswith("Objective") else "Objectives", "lines": [row]}
            continue

        named_match = POLICY_NAMED_RE.match(text)
        code_match = POLICY_CODE_RE.match(text)
        list_match = LIST_POLICY_RE.match(text)

        if named_match:
            label = compact_space(named_match.group(1).replace(":", "")).rstrip(".")
            body = compact_space(named_match.group(2))
            if current_record and current_record["record_kind"] == "policy" and is_reference_continuation_text(body):
                continuation = f"Policy {label}"
                if body:
                    continuation = f"{continuation} {body}"
                current_record["lines"].append({**row, "text": continuation})
                continue
            flush_context()
            flush_record()
            current_record = {
                "record_kind": "policy",
                "label_raw": label.replace("Policy ", "", 1),
                "display_label_raw": label,
                "lines": [{**row, "text": body}] if body else [row],
            }
            continue
        if code_match:
            label = compact_space(code_match.group(1)).rstrip(".")
            body = compact_space(code_match.group(2) or "")
            if current_record and current_record["record_kind"] == "policy" and label == "P-73" and body.startswith("are approached"):
                current_record["lines"].append({**row, "text": f"{label} {body}"})
                continue
            if current_record and current_record["record_kind"] == "policy" and is_reference_continuation_text(body):
                continuation = label
                if body:
                    continuation = f"{continuation} {body}"
                current_record["lines"].append({**row, "text": continuation})
                continue
            flush_context()
            flush_record()
            current_record = {
                "record_kind": "policy",
                "label_raw": label,
                "display_label_raw": label,
                "lines": [{**row, "text": body}] if body else [row],
            }
            continue
        if list_match:
            flush_context()
            flush_record()
            current_record = {
                "record_kind": "policy",
                "label_raw": compact_space(list_match.group(1)),
                "display_label_raw": compact_space(list_match.group(1)),
                "lines": [{**row, "text": compact_space(list_match.group(2))}],
            }
            continue
        if current_record:
            current_record["lines"].append(row)
            continue

        if (
            UPPERCASE_HEADING_RE.match(text)
            and text not in {spec.section_label_raw, spec.title_label_raw}
            and len(text) <= 120
        ) or looks_like_title_heading(text):
            flush_context()
            current_context.append(row)
            continue

        current_context.append(row)

    flush_record()
    flush_context()

    for policy in policies:
        if re.search(r"\b[A-Za-z]{1,8}-\d+[A-Za-z]*(?:\.[A-Za-z0-9]+)+", policy["policy_label_raw"]):
            open_issues.append(
                {
                    "issue_type": "identifier_normalization_pending_review",
                    "section_label_raw": spec.title_label_raw,
                    "example_label_raw": policy["policy_label_raw"],
                    "reason": "MPS dotted policy identifiers are preserved raw in v1.",
                }
            )
            break

    if spec.slug == "springfield-lake-designation":
        policies = repair_springfield_lake_policies(policies)
        existing = {policy["policy_label_raw"] for policy in policies}
        p69 = extract_policy_from_rows(rows, "P-69", ("P-70",))
        p70 = extract_policy_from_rows(rows, "P-70", ("P-71",))
        insert_at = next((idx + 1 for idx, policy in enumerate(policies) if policy["policy_label_raw"] == "P-68"), 1)
        additions = []
        if p69 and "P-69" not in existing:
            additions.append(p69)
        if p70 and "P-70" not in existing:
            additions.append(p70)
        if additions:
            policies[insert_at:insert_at] = additions

    refs = maps
    return {
        "context_blocks": context_blocks,
        "objectives": objectives,
        "policies": policies,
        "policy_subclauses": policy_subclauses,
        "map_references": [ref for ref in refs if ref["reference_type"] == "map"],
        "schedule_references": [ref for ref in refs if ref["reference_type"] == "schedule"],
        "spatial_features_needed": spatial_backlog_entries(refs, spec),
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
            "document_name": DOCUMENT_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
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
            "document_name": DOCUMENT_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "document_type": "official_plan_text",
            "effective_through": "2025-05-26",
            "page_count_pdf": len(reader.pages),
            "mps_page_offset_from_pdf": PDF_TO_MPS_PAGE_OFFSET,
            "metadata": {key.lstrip("/"): value for key, value in (reader.metadata or {}).items()},
        },
        "normalization_policy": {
            "policy_identifiers_preserved_raw": True,
            "normalized_paths_applied": False,
            "status": "pending_review_mps_dotted_identifier",
            "reason": "The repository has approved zoning clause normalization only. MPS dotted and mixed-format policy identifiers remain raw in v1.",
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
            "example_labels_raw": ["P-47(c)", "P-79A.8", "P-79B.18", "BW-31A", "SW-6"],
            "reason": "MPS dotted and mixed-format policy identifiers are not approved for normalized hierarchy handling in this repository.",
        },
        {
            "issue_type": "table_of_contents_outline_absent",
            "reason": "The PDF does not expose bookmark outline entries through PyPDF, so section ranges are seeded from the text table of contents and page inspection.",
        },
        {
            "issue_type": "primary-maps-not-embedded-in-source-pdf",
            "example_labels_raw": ["MAP 1A, 1B, 1C, 1D, 1E, 1F - Generalized Future Land Use", "MAP 2 - Transportation"],
            "reason": "The main generalized future land use maps and transportation map are referenced as separate map files and are not embedded as caption pages in this PDF.",
        },
    ]

    for spec in SECTION_SPECS:
        parsed = parse_section_content(spec, section_rows(lines, spec))
        payload = section_payload(spec, parsed)
        write_json(SECTION_DIR / f"{spec.slug}.json", payload)
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

    write_json(OUTPUT_ROOT / "document.json", document_payload(reader, section_inventory, all_maps, all_backlog))
    write_json(
        OUTPUT_ROOT / "maps.json",
        {"document_name": DOCUMENT_NAME, "source_document_path": SOURCE_DOCUMENT_PATH, "references": all_maps},
    )
    write_json(
        OUTPUT_ROOT / "spatial-features-needed.json",
        {
            "document_name": DOCUMENT_NAME,
            "source_document_path": SOURCE_DOCUMENT_PATH,
            "spatial_features_needed": all_backlog,
        },
    )
    write_json(OUTPUT_ROOT / "open-issues.json", {"open_issues": all_open_issues})


if __name__ == "__main__":
    main()

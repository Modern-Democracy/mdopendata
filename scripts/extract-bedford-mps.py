from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "bedford-municipal-planning-strategy.pdf"
OUTPUT_ROOT = ROOT / "data" / "municipal-planning-strategy" / "bedford"
SECTION_DIR = OUTPUT_ROOT / "sections"
PDF_TO_MPS_PAGE_OFFSET = 5


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
    SectionSpec("introduction", "INTRODUCTION", "INTRODUCTION", 6, 8, "introduction"),
    SectionSpec(
        "community-participation",
        "COMMUNITY PARTICIPATION",
        "COMMUNITY PARTICIPATION",
        9,
        11,
        "citywide",
    ),
    SectionSpec(
        "heritage-and-community-development",
        "HERITAGE AND COMMUNITY DEVELOPMENT",
        "HERITAGE AND COMMUNITY DEVELOPMENT",
        12,
        16,
        "citywide",
    ),
    SectionSpec("residential", "RESIDENTIAL", "RESIDENTIAL", 17, 37, "citywide"),
    SectionSpec("transportation", "TRANSPORTATION", "TRANSPORTATION", 38, 44, "citywide"),
    SectionSpec("commercial", "COMMERCIAL", "COMMERCIAL", 45, 63, "citywide"),
    SectionSpec(
        "waterfront-development",
        "WATERFRONT DEVELOPMENT",
        "WATERFRONT DEVELOPMENT",
        64,
        72,
        "citywide",
    ),
    SectionSpec("industrial", "INDUSTRIAL", "INDUSTRIAL", 73, 77, "citywide"),
    SectionSpec("institutional", "INSTITUTIONAL", "INSTITUTIONAL", 78, 82, "citywide"),
    SectionSpec(
        "the-bedford-south-secondary-planning-strategy",
        "THE BEDFORD SOUTH SECONDARY PLANNING STRATEGY (RC-Ju 9/09;E-Aug 31/09)",
        "THE BEDFORD SOUTH SECONDARY PLANNING STRATEGY (RC-Ju 9/09;E-Aug 31/09)",
        83,
        103,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "the-bedford-west-secondary-planning-strategy",
        "THE BEDFORD WEST SECONDARY PLANNING STRATEGY (RC-Jun 2/09;E-Jun 27/09)",
        "THE BEDFORD WEST SECONDARY PLANNING STRATEGY (RC-Jun 2/09;E-Jun 27/09)",
        104,
        148,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "parks-and-recreation",
        "PARKS AND RECREATION",
        "PARKS AND RECREATION",
        149,
        158,
        "citywide",
    ),
    SectionSpec("environment", "ENVIRONMENT", "ENVIRONMENT", 159, 178, "citywide"),
    SectionSpec(
        "construction-and-demolition-waste-management-strategy",
        "CONSTRUCTION AND DEMOLITION WASTE MANAGEMENT STRATEGY (RC-Sep 10/02;E-Nov 9/02)",
        "CONSTRUCTION AND DEMOLITION WASTE MANAGEMENT STRATEGY (RC-Sep 10/02;E-Nov 9/02)",
        179,
        183,
        "citywide",
    ),
    SectionSpec(
        "infrastructure-charges",
        "INFRASTRUCTURE CHARGES (RC-Sep 10/02;E-Nov 9/02)",
        "INFRASTRUCTURE CHARGES (RC-Sep 10/02;E-Nov 9/02)",
        184,
        187,
        "citywide",
    ),
    SectionSpec(
        "interim-growth-management",
        "INTERIM GROWTH MANAGEMENT (Deleted: RC-Jun 27/06;E-Aug 26/06)",
        "INTERIM GROWTH MANAGEMENT (Deleted: RC-Jun 27/06;E-Aug 26/06)",
        187,
        187,
        "repealed_section",
        "repealed",
    ),
    SectionSpec("implementation", "IMPLEMENTATION", "IMPLEMENTATION", 188, 197, "implementation"),
]


MAP_FEATURE_CLASS_RULES = [
    ("future_land_use_area", ["generalized future land use", "land use designation"]),
    ("planning_area_boundary", ["planning areas", "area plan boundary", "study area"]),
    ("site_specific_plan_area", ["overview map", "neighbourhood plan", "interchange node"]),
    ("environmental_constraint_area", ["environmental sensitivity"]),
    ("flood_plain_area", ["flood plain", "floodplains"]),
    ("watershed_area", ["watershed"]),
    ("transportation_corridor", ["proposed street network", "street hierarchy", "transportation system"]),
    ("development_sub_area", ["development areas", "development sub-areas", "density allocations"]),
    ("municipal_service_area", ["water service", "sanitary sewer", "sewersheds"]),
    ("community_concept_plan_area", ["community concept plan"]),
    ("density_allocation_area", ["density allocations"]),
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
POLICY_CODE_RE = re.compile(r"^([A-Za-z]{1,6}(?:/[A-Za-z]{1,6})?-\d+[A-Za-z]*(?:\([A-Za-z0-9.]+\))*)(?:\s+(.*))?$")
INLINE_POLICY_CODE_RE = re.compile(r"([A-Za-z]{1,6}(?:/[A-Za-z]{1,6})?-\d+[A-Za-z]*(?:\([A-Za-z0-9.]+\))*)\s+")
LIST_POLICY_RE = re.compile(r"^([0-9A-Z.,\sand()/-]+?)\s+[.-]\s+(Repealed.*|Deleted.*)$", re.IGNORECASE)
SUBCLAUSE_RE = re.compile(r"^(-|\([A-Za-z0-9.]+\)|[A-Za-z0-9.]+\)|[0-9]+[.)])\s+(.*)$")
MAP_CAPTION_RE = re.compile(r"^(Map|MAP)\s+\d+[A-Za-z()/-]*:|^Schedule\s+(?:[IVXLC]+|[A-Za-z0-9-]+):")
TOPIC_HEADING_RE = re.compile(r"^\d+[A-Z]?\.\s+[A-Z][A-Z0-9 ,&'()/.-]+$")
UPPERCASE_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 /&,'()-.:-]+$")
TITLE_HEADING_RE = re.compile(r"^(?:[A-Z][A-Za-z0-9'&/-]*)(?:\s+[A-Z][A-Za-z0-9'&/-]*){0,10}:?$")
FOOTNOTE_START_RE = re.compile(r"^\d+\s+\d+\s+Report to Mayor Fitzgerald and Members of Halifax Regional Council\b")
GENERIC_FOOTNOTE_START_RE = re.compile(r"^\d+\s{2,}[A-Z]")
INLINE_SUBCLAUSE_RE = re.compile(r"(?:(?<=^)|(?<=\s)|(?<=;))(\([A-Za-z0-9.]+\)|[A-Za-z0-9.]+\)|[0-9]+[.)])\s+")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    cleaned = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    cleaned = cleaned.replace("\u00a0", " ")
    return cleaned.rstrip()


def canonicalize_section_label(value: str) -> str:
    return compact_space(normalize_line(value)).replace("&", "AND")


def split_embedded_policy_code_lines(line: str) -> list[str]:
    starts: list[int] = []
    for match in INLINE_POLICY_CODE_RE.finditer(line):
        prefix = line[: match.start()]
        if prefix.endswith(("Map ", "MAP ")):
            continue
        if match.start() != 0:
            if not prefix.endswith(("Policy ", ": ", "; ")):
                continue
        starts.append(match.start())
    if not starts:
        return [line]
    segments: list[str] = []
    if starts[0] > 0:
        prefix = compact_space(line[: starts[0]])
        if prefix:
            segments.append(prefix)
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(line)
        segment = compact_space(line[start:end])
        if segment:
            segments.append(segment)
    return segments


def mps_page_from_pdf_page(pdf_page: int) -> int | None:
    if pdf_page <= PDF_TO_MPS_PAGE_OFFSET:
        return None
    return pdf_page - PDF_TO_MPS_PAGE_OFFSET


def extract_lines(reader: PdfReader) -> list[dict]:
    rows: list[dict] = []
    for pdf_page, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        skip_footnote = False
        for raw_line in raw_text.splitlines():
            line = normalize_line(raw_line).strip()
            if not line:
                continue
            if re.match(r"^[A-Za-z ]+(?:Municipal Planning Strategy|MPS)\s+Page \d+$", line):
                continue
            if re.fullmatch(r"Page \d+", line):
                continue
            if skip_footnote:
                if line.startswith("Dated ") or " Dated " in line or re.search(r"\b\d{4}\.$", line):
                    skip_footnote = False
                continue
            if FOOTNOTE_START_RE.match(line) or GENERIC_FOOTNOTE_START_RE.match(line):
                skip_footnote = True
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
    if spec.slug == "interim-growth-management":
        for index, row in enumerate(rows):
            if canonicalize_section_label(row["text"]) == canonicalize_section_label(spec.section_label_raw):
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
    return "plan_reference_map"


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


def should_start_new_policy(label: str, body: str, current_record: dict | None, next_text: str | None) -> bool:
    if current_record is None or current_record["record_kind"] != "policy":
        return True
    if re.fullmatch(r"[A-Z]{1,3}", label):
        return False
    if body and body[0].islower():
        return False
    if next_text and not next_text.startswith(("Policy ", "Map ", "MAP ", "Schedule ", "SCHEDULE ")):
        if len(body.split()) <= 3 and not re.search(r"\bshall\b|\bmay\b|\bshould\b", body.lower()):
            return False
    return True


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
    feature_key = slugify(f"{source_label_raw.rstrip(':')} {title}")
    return {
        "feature_key": feature_key,
        "reference_type": reference_type,
        "feature_class": feature_class_for_label(source_label_raw + " " + title),
        "source_label_raw": source_label_raw,
        "title_text": title,
        "pdf_page_start": row["pdf_page"],
        "pdf_page_end": row["pdf_page"],
        "mps_page_start": row["mps_page"],
        "mps_page_end": row["mps_page"],
        "section_label_raw": spec.section_label_raw,
        "section_slug": spec.slug,
        "planned_postgis_target": "spatial_features",
    }


def parse_section_content(spec: SectionSpec, rows: list[dict]) -> dict:
    if spec.slug == "interim-growth-management":
        return {
            "context_blocks": [],
            "objectives": [],
            "policies": [],
            "policy_subclauses": [],
            "map_references": [],
            "schedule_references": [],
            "spatial_features_needed": [],
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

    for index, row in enumerate(rows):
        text = row["text"]
        next_text = rows[index + 1]["text"] if index + 1 < len(rows) else None

        if canonicalize_section_label(text) in {
            canonicalize_section_label(spec.section_label_raw),
            canonicalize_section_label(spec.title_label_raw),
            "OBJECTIVES AND POLICIES",
            "IMPLEMENTATION POLICIES",
            "INTRODUCTION",
        }:
            flush_context()
            flush_record()
            continue
        if MAP_CAPTION_RE.match(text) and not text.startswith("Map 1 in the ongoing"):
            flush_context()
            flush_record()
            maps.append(parse_map_reference(row, spec))
            continue
        if text.endswith(" OBJECTIVE") or text.endswith(" OBJECTIVES"):
            flush_context()
            flush_record()
            current_record = {
                "record_kind": "objective",
                "label_raw": text,
                "lines": [],
            }
            continue
        if POLICY_NAMED_RE.match(text):
            flush_context()
            flush_record()
            match = POLICY_NAMED_RE.match(text)
            assert match is not None
            label = match.group(1)
            rest = match.group(2).strip()
            lines = [{**row, "text": rest}] if rest else [{**row, "text": ""}]
            current_record = {"record_kind": "policy", "label_raw": label, "lines": lines}
            continue
        if POLICY_CODE_RE.match(text):
            flush_context()
            flush_record()
            match = POLICY_CODE_RE.match(text)
            assert match is not None
            label = match.group(1)
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


def spatial_backlog_entries(refs: list[dict], spec: SectionSpec) -> list[dict]:
    entries = []
    for ref in refs:
        reason = (
            "Referenced by the Bedford Municipal Planning Strategy and required for "
            "later PostGIS linkage between policy text and mapped planning areas."
        )
        entries.append(
            {
                "feature_key": ref["feature_key"],
                "feature_class": ref["feature_class"],
                "source_document_page": ref["pdf_page_start"],
                "source_label_raw": ref["source_label_raw"],
                "reason": reason,
                "planned_postgis_target": ref["planned_postgis_target"],
                "section_label_raw": spec.section_label_raw,
                "section_slug": spec.slug,
                "source_type": "manual_or_vector_digitization_backlog",
            }
        )
    return entries


def section_payload(spec: SectionSpec, parsed: dict) -> dict:
    return {
        "section_metadata": {
            "jurisdiction": "Halifax Regional Municipality",
            "document_name": "Bedford Municipal Planning Strategy",
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
            "document_name": "Bedford Municipal Planning Strategy",
            "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
            "document_type": "official_plan_text",
            "effective_through": "2026-02-02",
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
            "example_labels_raw": ["1.2.7", "2A.2.1", "2.12A", "2.1 (a)", "Policy BW-41A(A)"],
            "reason": "MPS dotted and mixed-format policy identifiers are not approved for normalized hierarchy handling in this repository.",
        },
        {
            "issue_type": "table_of_contents_outline_absent",
            "reason": "The PDF does not expose bookmark outline entries through PyPDF2, so section ranges are seeded from the text table of contents and page inspection.",
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

    map_payload = {
        "document_name": "Bedford Municipal Planning Strategy",
        "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "references": all_maps,
    }
    spatial_payload = {
        "document_name": "Bedford Municipal Planning Strategy",
        "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "spatial_features_needed": all_backlog,
    }
    document = document_payload(reader, section_inventory, all_maps, all_backlog)

    write_json(OUTPUT_ROOT / "document.json", document)
    write_json(OUTPUT_ROOT / "maps.json", map_payload)
    write_json(OUTPUT_ROOT / "spatial-features-needed.json", spatial_payload)
    write_json(OUTPUT_ROOT / "open-issues.json", {"open_issues": all_open_issues})


if __name__ == "__main__":
    main()

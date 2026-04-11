from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "halifaxmps-eff-26feb02-minorrev2025-02922-toclinked.pdf"
OUTPUT_ROOT = ROOT / "data" / "municipal-planning-strategy" / "halifax-mainland"
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
    SectionSpec("introduction", "INTRODUCTION", "INTRODUCTION", 9, 10, "introduction"),
    SectionSpec(
        "section-i-basic-approach-and-overall-objective",
        "SECTION I",
        "BASIC APPROACH AND OVERALL OBJECTIVE",
        11,
        11,
        "citywide",
    ),
    SectionSpec(
        "section-ii-city-wide-objectives-and-policies",
        "SECTION II",
        "CITY-WIDE OBJECTIVES AND POLICIES",
        12,
        54,
        "citywide",
    ),
    SectionSpec(
        "section-v-south-end-area-plan-objectives-and-policies",
        "SECTION V",
        "SOUTH END AREA PLAN OBJECTIVES AND POLICIES",
        55,
        55,
        "repealed_section",
        "repealed",
    ),
    SectionSpec(
        "section-vi-peninsula-centre-area-plan-objectives-and-policies",
        "SECTION VI",
        "PENINSULA CENTRE AREA PLAN OBJECTIVES AND POLICIES",
        55,
        55,
        "repealed_section",
        "repealed",
    ),
    SectionSpec(
        "section-vii-fairview-area-secondary-planning-strategy-objectives-and-policies",
        "SECTION VII",
        "FAIRVIEW AREA SECONDARY PLANNING STRATEGY OBJECTIVES AND POLICIES",
        56,
        68,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "section-viii-bedford-highway-secondary-planning-strategy-objectives-and-policies",
        "SECTION VIII",
        "BEDFORD HIGHWAY SECONDARY PLANNING STRATEGY OBJECTIVES AND POLICIES",
        69,
        95,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "section-x-mainland-south-secondary-planning-strategy-objectives-and-policies",
        "SECTION X",
        "MAINLAND SOUTH SECONDARY PLANNING STRATEGY OBJECTIVES AND POLICIES",
        96,
        126,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "section-xi-peninsula-north-secondary-planning-strategy",
        "SECTION XI",
        "PENINSULA NORTH SECONDARY PLANNING STRATEGY",
        127,
        127,
        "repealed_section",
        "repealed",
    ),
    SectionSpec(
        "section-xii-quinpool-road-commercial-area-plan-objectives-and-policies",
        "SECTION XII",
        "QUINPOOL ROAD COMMERCIAL AREA PLAN OBJECTIVES AND POLICIES",
        127,
        127,
        "repealed_section",
        "repealed",
    ),
    SectionSpec(
        "section-xiii-western-common-area-plan-objectives-and-policies",
        "SECTION XIII",
        "WESTERN COMMON AREA PLAN OBJECTIVES AND POLICIES",
        127,
        131,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "section-xiv-the-wentworth-secondary-planning-strategy",
        "SECTION XIV",
        "THE WENTWORTH SECONDARY PLANNING STRATEGY",
        132,
        157,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "section-xv-the-bedford-west-secondary-planning-strategy",
        "SECTION XV",
        "THE BEDFORD WEST SECONDARY PLANNING STRATEGY",
        158,
        193,
        "secondary_planning_strategy",
    ),
    SectionSpec(
        "section-xvi-site-specific-policies-in-keeping-with-the-june-2017-centre-plan-document",
        "SECTION XVI",
        "SITE-SPECIFIC POLICIES IN KEEPING WITH THE JUNE 2017 CENTRE PLAN DOCUMENT",
        194,
        194,
        "repealed_section",
        "repealed",
    ),
    SectionSpec(
        "implementation-policies",
        "IMPLEMENTATION POLICIES",
        "IMPLEMENTATION POLICIES",
        194,
        217,
        "implementation",
    ),
]


MAP_FEATURE_CLASS_RULES = [
    ("future_land_use_area", ["generalized future land use"]),
    ("planning_area_boundary", ["planning areas", "area plan boundary", "study area"]),
    ("site_specific_plan_area", ["overview map", "neighbourhood plan", "interchange node"]),
    ("environmental_constraint_area", ["environmental sensitivity"]),
    ("flood_plain_area", ["flood plain"]),
    ("watershed_area", ["watershed"]),
    ("transportation_corridor", ["principal streets", "street hierarchy", "transportation system"]),
    ("development_sub_area", ["development sub-areas"]),
    ("municipal_service_area", ["water service", "sanitary sewer", "sewersheds"]),
    ("community_concept_plan_area", ["community concept plan"]),
    ("density_allocation_area", ["density allocations"]),
]


HEADING_PREFIXES = (
    "SECTION ",
    "Map ",
    "Schedule ",
    "Objective",
    "Objectives",
    "Policy ",
)


POLICY_LABEL_RE = re.compile(r"^((?:\d+[A-Z]?)(?:\.\d+[A-Z]?)*\.?[A-Z]?)\s+(.*)$")
POLICY_NAMED_RE = re.compile(
    r"^(Policy\s+[A-Z0-9]+(?:\.\d+[A-Z]?)*(?:\s*-\s*[A-Z0-9]+)?)\s*:?\s*(.*)$"
)
LIST_POLICY_RE = re.compile(r"^([0-9A-Z.,\sand()]+?)\s+[.-]\s+(Repealed.*|Deleted.*)$", re.IGNORECASE)
SUBCLAUSE_RE = re.compile(r"^(\([A-Za-z0-9.]+\)|[A-Za-z0-9.]+\))\s+(.*)$")
MAP_CAPTION_RE = re.compile(r"^(Map|Schedule)\s+[A-Za-z0-9() -]+\s*:")
TOPIC_HEADING_RE = re.compile(r"^\d+[A-Z]?\.\s+[A-Z][A-Z0-9 ,&'()/.-]+$")
UPPERCASE_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 /&,'()-]+$")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value: str) -> str:
    cleaned = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    cleaned = cleaned.replace("\u00a0", " ")
    return cleaned.rstrip()


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
            if re.match(r"^Halifax Municipal Planning Strategy\s+Page \d+$", line):
                continue
            if re.fullmatch(r"Page \d+", line):
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
    if spec.slug == "implementation-policies":
        for index, row in enumerate(rows):
            if row["text"] == "IMPLEMENTATION POLICIES":
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
    for feature_class, needles in MAP_FEATURE_CLASS_RULES:
        if any(needle in normalized for needle in needles):
            return feature_class
    return "policy_map_reference"


def planned_postgis_target(feature_class: str) -> str:
    if feature_class.endswith("_area") or feature_class.endswith("_boundary") or feature_class in {
        "development_sub_area",
        "community_concept_plan_area",
        "density_allocation_area",
    }:
        return "spatial_features.geom"
    if feature_class == "transportation_corridor":
        return "spatial_features.geom"
    return "spatial_features.attributes"


def gather_map_refs(lines: Iterable[dict], section_slug: str | None = None) -> list[dict]:
    refs: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for row in lines:
        text = row["text"]
        if not MAP_CAPTION_RE.match(text):
            continue
        key = (text, row["pdf_page"])
        if key in seen:
            continue
        seen.add(key)
        ref_type = "map" if text.startswith("Map ") else "schedule"
        refs.append(
            {
                "reference_type": ref_type,
                "source_label_raw": text,
                "feature_key": slugify(text),
                "feature_class": feature_class_for_label(text),
                "pdf_page_start": row["pdf_page"],
                "pdf_page_end": row["pdf_page"],
                "mps_page_start": row["mps_page"],
                "mps_page_end": row["mps_page"],
                "planned_postgis_target": planned_postgis_target(feature_class_for_label(text)),
                "section_slug": section_slug,
            }
        )
    return refs


def parse_section_content(spec: SectionSpec, rows: list[dict]) -> dict:
    maps = gather_map_refs(rows, spec.slug)
    objectives: list[dict] = []
    policies: list[dict] = []
    policy_subclauses: list[dict] = []
    context_blocks: list[dict] = []
    open_issues: list[dict] = []

    if spec.status != "active" and spec.section_type == "repealed_section":
        text = " ".join(row["text"] for row in rows)
        context_blocks.append(
            {
                "block_type": "section_status",
                "text": compact_space(text),
                "citations": {
                    "pdf_page_start": spec.pdf_page_start,
                    "pdf_page_end": spec.pdf_page_end,
                    "mps_page_start": mps_page_from_pdf_page(spec.pdf_page_start),
                    "mps_page_end": mps_page_from_pdf_page(spec.pdf_page_end),
                },
            }
        )
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

    current_context: list[dict] = []
    current_record: dict | None = None
    objective_index = 0
    policy_index = 0

    def flush_context() -> None:
        nonlocal current_context
        if not current_context:
            return
        context_blocks.append(
            {
                "block_type": "narrative_context",
                "text": compact_space(" ".join(item["text"] for item in current_context)),
                "citations": {
                    "pdf_page_start": current_context[0]["pdf_page"],
                    "pdf_page_end": current_context[-1]["pdf_page"],
                    "mps_page_start": current_context[0]["mps_page"],
                    "mps_page_end": current_context[-1]["mps_page"],
                },
            }
        )
        current_context = []

    def flush_record() -> None:
        nonlocal current_record, objective_index, policy_index
        if not current_record:
            return
        text = compact_space(" ".join(line["text"] for line in current_record["lines"]))
        citations = {
            "pdf_page_start": current_record["lines"][0]["pdf_page"],
            "pdf_page_end": current_record["lines"][-1]["pdf_page"],
            "mps_page_start": current_record["lines"][0]["mps_page"],
            "mps_page_end": current_record["lines"][-1]["mps_page"],
        }
        if current_record["record_kind"] == "objective":
            objective_index += 1
            objective = {
                "objective_index": objective_index,
                "objective_label_raw": current_record["label_raw"],
                "text": text,
                "status": "active",
                "citations": citations,
            }
            objectives.append(objective)
        else:
            policy_index += 1
            policy_type = classify_policy_type(spec.section_type, text)
            policy = {
                "policy_index": policy_index,
                "policy_label_raw": current_record["label_raw"],
                "normalized_path": None,
                "normalization_status": "pending_review_mps_dotted_identifier",
                "policy_type": policy_type,
                "status": "active" if policy_type not in {"repealed", "deleted"} else policy_type,
                "modality": extract_modality(text),
                "text": text,
                "citations": citations,
            }
            policies.append(policy)
            for line in current_record["lines"]:
                match = SUBCLAUSE_RE.match(line["text"])
                if not match:
                    continue
                clause_label_raw = match.group(1)
                clause_text = match.group(2)
                policy_subclauses.append(
                    {
                        "parent_policy_label_raw": current_record["label_raw"],
                        "clause_label_raw": clause_label_raw,
                        "normalized_path": None,
                        "normalization_status": "pending_review_mps_dotted_identifier",
                        "text": compact_space(clause_text),
                        "modality": extract_modality(clause_text),
                        "citations": {
                            "pdf_page_start": line["pdf_page"],
                            "pdf_page_end": line["pdf_page"],
                            "mps_page_start": line["mps_page"],
                            "mps_page_end": line["mps_page"],
                        },
                    }
                )
        current_record = None

    for row in rows:
        text = row["text"]
        if MAP_CAPTION_RE.match(text):
            if current_record:
                flush_record()
            current_context.append(row)
            continue
        if text.startswith("SECTION ") and text != spec.section_label_raw and spec.section_type != "repealed_section":
            if current_record:
                flush_record()
            continue
        if text.startswith(spec.section_label_raw) or text == spec.title_label_raw:
            current_context.append(row)
            continue
        if (
            UPPERCASE_HEADING_RE.match(text)
            and text not in {"OBJECTIVE", "OBJECTIVES"}
            and len(text) <= 90
        ):
            if current_record:
                flush_record()
            current_context.append(row)
            continue
        if TOPIC_HEADING_RE.match(text):
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
        if POLICY_NAMED_RE.match(text):
            flush_context()
            flush_record()
            match = POLICY_NAMED_RE.match(text)
            assert match is not None
            label = match.group(1)
            rest = match.group(2).strip()
            first_line = {**row, "text": rest} if rest else row
            current_record = {"record_kind": "policy", "label_raw": label, "lines": [first_line]}
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
        match = POLICY_LABEL_RE.match(text)
        if match and not text.startswith("Map "):
            flush_context()
            flush_record()
            label = match.group(1).rstrip(".")
            body = match.group(2)
            current_record = {
                "record_kind": "policy",
                "label_raw": label,
                "lines": [{**row, "text": body}],
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
            "Referenced by the Halifax Mainland Municipal Planning Strategy and required for "
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
            "document_name": "Halifax Municipal Planning Strategy",
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
            "document_name": "Halifax Municipal Planning Strategy",
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
            "example_labels_raw": ["1.2.7", "2A.2.1", "2.12A", "2.1 (a)", "Policy EP-4"],
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
        "document_name": "Halifax Municipal Planning Strategy",
        "source_document_path": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "references": all_maps,
    }
    spatial_payload = {
        "document_name": "Halifax Municipal Planning Strategy",
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

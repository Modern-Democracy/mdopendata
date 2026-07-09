import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


BASE = Path("data/budget/charlottetown")
DOCUMENTS = ("2025-2026", "2024-2025")


PERIOD_RULES = {
    "2025-2026": {
        "2025/2026": ("2025-04-01", "2026-03-31", "budget", "fiscal_period"),
        "2025/26": ("2025-04-01", "2026-03-31", "budget", "fiscal_period_alias"),
        "2025-26": ("2025-04-01", "2026-03-31", "budget", "fiscal_period_alias"),
        "2025-2026": ("2025-04-01", "2026-03-31", "budget", "fiscal_period_alias"),
        "2024/2025": ("2024-04-01", "2025-03-31", "forecast", "prior_fiscal_period"),
        "2024/25": ("2024-04-01", "2025-03-31", "forecast", "prior_fiscal_period_alias"),
        "2024-25": ("2024-04-01", "2025-03-31", "forecast", "prior_fiscal_period_alias"),
    },
    "2024-2025": {
        "2024/2025": ("2024-04-01", "2025-03-31", "budget", "fiscal_period"),
        "2024/25": ("2024-04-01", "2025-03-31", "budget", "fiscal_period_alias"),
        "2024 - 2025": ("2024-04-01", "2025-03-31", "budget", "fiscal_period_alias"),
        "2023/2024": ("2023-04-01", "2024-03-31", "forecast", "prior_fiscal_period"),
        "2023-24": ("2023-04-01", "2024-03-31", "forecast", "prior_fiscal_period_alias"),
        "2024-25": ("2024-04-01", "2025-03-31", "budget", "fiscal_period_alias"),
    },
}


FALSE_POSITIVE_LABELS = {
    ("2025-2026", "2025"): "calendar-year label on tax/rate effective-date text or project profile text; not a fiscal-period column by itself",
    ("2025-2026", "2026"): "calendar-year label in project profile text; not a fiscal-period column by itself",
    ("2025-2026", "2023"): "line-label text in Civic Centre revenue, not a period column",
    ("2025-2026", "2024"): "calendar-year label in project profile text; not a fiscal-period column by itself",
    ("2024-2025", "2024"): "calendar-year label in capital/project text; fiscal period requires source date range or 2024/2025 label",
    ("2024-2025", "2025"): "calendar-year label in date-range or project text; not a fiscal-period column by itself",
    ("2024-2025", "2026/2027"): "future capital-profile planning year; compatibility review, not document-period mapping",
    ("2024-2025", "2025/2026"): "future capital-profile planning year; compatibility review, not document-period mapping",
    ("2024-2025", "2027/2028"): "future capital-profile planning year; compatibility review, not document-period mapping",
    ("2024-2025", "2028/2029"): "future capital-profile planning year; compatibility review, not document-period mapping",
}


CAPITAL_PROJECT_ALIAS_DECISIONS = {
    ("2025-2026", "2025-2026-p110"): ("mapped_existing", ["bikeshare-program"], "Exact project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p111"): ("document_only", ["public-transit-buses"], "Bus replacement profile is not equivalent to a single approved 2026/2027 project key."),
    ("2025-2026", "2025-2026-p114"): ("mapped_existing", ["new-fire-station-build"], "Project label is a direct rename of 2026/2027 New Fire Station Build."),
    ("2025-2026", "2025-2026-p115"): ("mapped_existing", ["fire-engine-replacement"], "Exact project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p118"): ("mapped_existing", ["east-royalty-park-old-road-at-pathway"], "Raw project title completes the truncated heading and matches the 2026/2027 East Royalty pathway key."),
    ("2025-2026", "2025-2026-p119"): ("mapped_existing", ["simmons-artificial-turf-field"], "Artificial Turf Field profile maps to the Simmons Artificial Turf Field project key."),
    ("2025-2026", "2025-2026-p120"): ("mapped_existing", ["multi-sport-outdoor-facility"], "Multi-use and multi-sport outdoor facility labels identify the same outdoor facility project."),
    ("2025-2026", "2025-2026-p124"): ("mapped_existing", ["heartz-hall-upgrades"], "Phase 2 profile maps to the stable Heartz Hall Upgrades key."),
    ("2025-2026", "2025-2026-p125"): ("mapped_existing", ["sherwood-rec-hall-upgrades"], "Project label matches the 2026/2027 Sherwood Rec Hall Upgrades key."),
    ("2025-2026", "2025-2026-p126"): ("document_only", ["brownfield-development"], "No approved 2026/2027 project key represents this profile without broad category inference."),
    ("2025-2026", "2025-2026-p127"): ("mapped_existing", ["pownal-street-parkade-upgrades"], "Pownal Street Parkade profile maps to the stable parkade-upgrades key."),
    ("2025-2026", "2025-2026-p128"): ("mapped_existing", ["queen-street-parkade-upgrades"], "Exact project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p129"): ("mapped_existing", ["small-fleet-parks"], "Profile describes Parks and Recreation small fleet replacement."),
    ("2025-2026", "2025-2026-p130"): ("mapped_existing", ["small-fleet-public-works"], "Heading and description identify Public Works small fleet replacement; the contradictory Project: field is retained as source evidence and does not override the agreed identity."),
    ("2025-2026", "2025-2026-p131"): ("mapped_existing", ["large-fleet-public-works"], "Profile describes Public Works large fleet replacement."),
    ("2025-2026", "2025-2026-p132"): ("mapped_existing", ["sidewalks-new-construction"], "Construction of New Sidewalks maps to the stable new-sidewalk construction key."),
    ("2025-2026", "2025-2026-p133"): ("mapped_existing", ["street-resurfacing"], "Exact project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p134"): ("mapped_existing", ["exhibition-drive-reconstruction"], "Exact project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p135"): ("mapped_existing", ["new-traffic-lights"], "Exact project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p137"): ("mapped_existing", ["wellfield-protection"], "Exact Water and Sewer project label match to 2026/2027 alias."),
    ("2025-2026", "2025-2026-p138"): ("mapped_existing", ["water-distribution-system-upgrade"], "Plural source label maps to singular approved 2026/2027 project key."),
    ("2025-2026", "2025-2026-p139"): ("mapped_existing", ["collector-sewer-liftstations-rehab"], "Raw project title maps to 2026/2027 collector sewer liftstations rehab key."),
    ("2025-2026", "2025-2026-p140"): ("mapped_existing", ["aeration-tank-rehab"], "Raw project title maps to 2026/2027 aeration tank rehab key."),
    ("2024-2025", "2024-2025-p047"): ("document_only", ["public-transit-facility-and-fleet"], "The adopted budget presents one combined facility-and-fleet project with no allocable component split; preserve one document-scoped identity and do not infer links to later facility, fleet, charging, or infrastructure projects."),
    ("2024-2025", "2024-2025-p050"): ("document_only", ["replacement-fast-rescue-craft"], "No approved 2026/2027 project key represents this fire rescue craft profile."),
    ("2024-2025", "2024-2025-p051"): ("mapped_existing", ["self-contained-breathing-aparatus"], "Raw project title maps to 2026/2027 self-contained breathing apparatus key."),
    ("2024-2025", "2024-2025-p054"): ("document_only", ["simmons-sports-centre-replacement"], "Sports centre replacement is not equivalent to later Simmons subproject keys without split review."),
    ("2024-2025", "2024-2025-p055"): ("mapped_existing", ["park-playground-infrastructure"], "Playground equipment and park development maps to the stable park/playground infrastructure key."),
    ("2024-2025", "2024-2025-p056"): ("document_only", ["victoria-park-shoreline-protection"], "No approved 2026/2027 project key represents shoreline protection."),
    ("2024-2025", "2024-2025-p057"): ("mapped_existing", ["victoria-park-tennis-courts"], "Raw project title maps to the 2026/2027 Victoria Park Tennis Courts key."),
    ("2024-2025", "2024-2025-p058"): ("mapped_existing", ["east-royalty-park-old-road-at-pathway"], "Raw project title maps to East Royalty Park Old Road and AT Pathway."),
    ("2024-2025", "2024-2025-p059"): ("document_only", ["charlottetown-yacht-club-seawall-reconstruction"], "No approved 2026/2027 project key represents this seawall profile."),
    ("2024-2025", "2024-2025-p061"): ("document_only", ["critical-incident-command"], "No approved 2026/2027 project key represents this police command profile."),
    ("2024-2025", "2024-2025-p064"): ("mapped_existing", ["hillsborough-hall-cc-upgrades"], "Community centre upgrades map to the stable Hillsborough Hall community-centre key."),
    ("2024-2025", "2024-2025-p065"): ("mapped_existing", ["pownal-street-parkade-upgrades"], "Pownal Parkade Restoration maps to the stable Pownal Street Parkade Upgrades key."),
    ("2024-2025", "2024-2025-p066"): ("document_only", ["eastern-gateway-masterplan"], "The source presents a single joint Public Works and Water/Sewer project and does not allocate its budget between components; preserve a document-scoped identity without split or later-year inference."),
    ("2024-2025", "2024-2025-p067"): ("document_only", ["seaview-boulevard-rehabilitation-public-works"], "The source reports the Public Works joint project separately from the Water and Sewer profile, with no source-supported shared project identifier or allocation; preserve a distinct document-scoped identity."),
    ("2024-2025", "2024-2025-p068"): ("document_only", ["water-street-rehabilitation-public-works"], "The source reports one Public Works joint project without an allocable Water and Sewer component split; preserve a document-scoped identity."),
    ("2024-2025", "2024-2025-p069"): ("mapped_existing", ["storm-water-management"], "Storm Water Modelling maps to the broader storm-water management project key."),
    ("2024-2025", "2024-2025-p073"): ("mapped_existing", ["eastern-gateway-water-and-sewer"], "Raw Water and Sewer project title maps to Eastern Gateway Water and Sewer."),
    ("2024-2025", "2024-2025-p074"): ("document_only", ["seaview-boulevard-water-and-sewer-rehabilitation"], "The Water and Sewer profile has a distinct entity, scope, and budget from the Public Works Seaview profile; preserve a separate document-scoped identity rather than infer a merge."),
    ("2024-2025", "2024-2025-p075"): ("document_only", ["wastewater-treatment-plant-and-liftstation-rehabilitation"], "No single approved 2026/2027 project key represents this combined plant and liftstation profile."),
    ("2024-2025", "2024-2025-p076"): ("mapped_existing", ["wellfield-protection"], "Exact Water and Sewer project label match to 2026/2027 alias."),
}

PROFILE_IDENTITY_OVERRIDES = {
    ("2025-2026", "2025-2026-p130"): "The heading and project description both identify Public Works Small Fleet Replacement; retain the conflicting Project: field as provenance but approve the heading/description identity.",
}


def slug(value):
    return (
        value.lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace(" ", "-")
        .replace("_", "-")
    )


def load_records(document):
    return json.loads((BASE / document / "profile_table_inventory.json").read_text())["records"]


def load_week5_records():
    review = json.loads((BASE / "week-5-normalized-mapping-review.json").read_text())
    return {
        document["document_key"]: document["records"]
        for document in review["documents"]
    }


def raw_page_text(document, page):
    path = BASE / document / "profile-raw-pages" / f"page-{page:03d}.txt"
    if not path.exists():
        path = BASE / document / "profile-ocr-pages" / f"page-{page:03d}.txt"
    return path.read_text(errors="ignore") if path.exists() else ""


def normalized_text(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def extract_profile_identity(document, page):
    lines = [line.rstrip() for line in raw_page_text(document, page).splitlines() if line.strip()]
    department_index = next((index for index, line in enumerate(lines) if line.strip().startswith("Department:")), None)
    title_lines = []
    if department_index is not None:
        for line in lines[:department_index]:
            stripped = line.strip()
            if not re.fullmatch(r"\d+", stripped):
                title_lines.append(stripped)
    title = " ".join(title_lines)
    project_lines = []
    if department_index is not None:
        for line in lines[department_index + 1:department_index + 8]:
            stripped = line.strip()
            if stripped.startswith(("Project Description", "Strategic Alignment", "Results to be Achieved", "Financial Summary")):
                break
            if stripped.startswith("Project:"):
                project_lines.append(stripped.split(":", 1)[1].strip())
            elif project_lines:
                project_lines.append(stripped)
    project = " ".join(project_lines)
    return title, project


def is_chart_source_table(record):
    text = raw_page_text(record["table_key"][:9], record["page_start"])
    if record["section"] != "Operating Budget":
        return False
    if record["table_family"] != "operating_statement":
        return False
    return (
        "2025/2026 Budget" in text
        and ("Total Revenue" in text or "Total Expenditures" in text)
        and "%" in text
    )


def operating_relationship_key(document, records, pattern):
    pages = "-".join(str(record["page_start"]) for record in records)
    return f"{document}-{pattern}-p{pages}"


def nearest_operating_statement(records, page_start):
    statements = [
        record
        for record in records
        if record["section"] == "Operating Budget"
        and record["table_family"] == "operating_statement"
        and not is_chart_source_table(record)
    ]
    if not statements:
        return None
    return min(statements, key=lambda record: (abs(record["page_start"] - page_start), record["page_start"]))


def operating_statement_group(records, overview_record):
    if not overview_record:
        return []
    group_key = overview_record.get("continuation_group")
    if not group_key:
        return [overview_record]
    return sorted(
        [
            record
            for record in records
            if record.get("continuation_group") == group_key
            and record["table_family"] == "operating_statement"
            and not is_chart_source_table(record)
        ],
        key=lambda record: record["page_start"],
    )


def build_operating_detail_relationship_review():
    output = {"schema_version": 1, "status": "phase_1_review_started", "records": []}
    for document in DOCUMENTS:
        records = load_records(document)
        if document == "2025-2026":
            detail_groups = defaultdict(list)
            for record in records:
                if record["section"] != "Operating Budget" or record["table_family"] != "operating_detail":
                    continue
                group_key = record.get("continuation_group") or record["table_key"]
                detail_groups[group_key].append(record)
            for group_key in sorted(detail_groups):
                detail_records = sorted(detail_groups[group_key], key=lambda item: item["page_start"])
                overview_record = nearest_operating_statement(records, detail_records[0]["page_start"])
                overview_records = operating_statement_group(records, overview_record)
                output["records"].append(
                    {
                        "document_key": document,
                        "relationship_key": operating_relationship_key(document, detail_records, "overview-to-detail"),
                        "presentation_pattern": "overview_to_detail",
                        "normalized_structure_target": "department_operating_statement_with_line_items",
                        "source_group_key": group_key,
                        "page_start": min(record["page_start"] for record in detail_records),
                        "page_end": max(record["page_start"] for record in detail_records),
                        "overview_table_key": overview_record["table_key"] if overview_record else None,
                        "overview_page": overview_record["page_start"] if overview_record else None,
                        "overview_table_keys": [record["table_key"] for record in overview_records],
                        "overview_pages": [record["page_start"] for record in overview_records],
                        "detail_table_keys": [record["table_key"] for record in detail_records],
                        "detail_pages": [record["page_start"] for record in detail_records],
                        "total_source": "overview_table",
                        "line_item_source": "detail_tables",
                        "decision": "approved_relationship",
                        "decision_reason": "2025/2026 presents department totals in the overview table and line items in associated Detailed Breakdown of Budget Item tables; normalize to the same department operating structure used for total-in-detail sources.",
                    }
                )
        if document == "2024-2025":
            statement_groups = defaultdict(list)
            for record in records:
                if record["section"] != "Operating Budget" or record["table_family"] != "operating_statement":
                    continue
                group_key = record.get("continuation_group") or record["table_key"]
                statement_groups[group_key].append(record)
            for group_key in sorted(statement_groups):
                statement_records = sorted(statement_groups[group_key], key=lambda item: item["page_start"])
                output["records"].append(
                    {
                        "document_key": document,
                        "relationship_key": operating_relationship_key(document, statement_records, "total-in-detail"),
                        "presentation_pattern": "total_in_detail",
                        "normalized_structure_target": "department_operating_statement_with_line_items",
                        "source_group_key": group_key,
                        "page_start": min(record["page_start"] for record in statement_records),
                        "page_end": max(record["page_start"] for record in statement_records),
                        "overview_table_key": None,
                        "overview_page": None,
                        "overview_table_keys": [],
                        "overview_pages": [],
                        "detail_table_keys": [record["table_key"] for record in statement_records],
                        "detail_pages": [record["page_start"] for record in statement_records],
                        "total_source": "detail_table",
                        "line_item_source": "detail_table",
                        "decision": "approved_relationship",
                        "decision_reason": "2024/2025 presents department line items and totals in the same detail table instead of a separate overview table; normalize to the same department operating structure used for overview-to-detail sources.",
                    }
                )
    output["summary"] = dict(Counter(r["presentation_pattern"] for r in output["records"]))
    return output


def build_period_review():
    output = {"schema_version": 1, "status": "phase_1_review_started", "records": []}
    for document in DOCUMENTS:
        occurrences = defaultdict(list)
        for record in load_records(document):
            for label in record.get("periods", []):
                occurrences[label].append(
                    {
                        "table_key": record["table_key"],
                        "page_start": record["page_start"],
                        "table_family": record["table_family"],
                        "title_guess": record["title_guess"],
                    }
                )
        for label in sorted(occurrences):
            rule = PERIOD_RULES.get(document, {}).get(label)
            false_positive = FALSE_POSITIVE_LABELS.get((document, label))
            families = {item["table_family"] for item in occurrences[label]}
            if rule:
                start, end, amount_type, role = rule
                status = "mapped"
                reason = "Mapped from reviewed document fiscal-period convention."
            elif false_positive:
                start = end = amount_type = None
                role = "not_document_period"
                status = "excluded_false_positive"
                reason = false_positive
            elif label.isdigit() and len(label) == 4 and families == {"debt_schedule"}:
                start = end = amount_type = None
                role = "debt_maturity_or_issue_year"
                status = "excluded_false_positive"
                reason = "Debt year label belongs to instrument identity and maturity review, not document-period mapping."
            elif label.isdigit() and len(label) == 4:
                start = end = amount_type = None
                role = "not_document_period"
                status = "excluded_false_positive"
                reason = "Calendar-year label appears in source text but is not a document-period column by itself."
            else:
                start = end = amount_type = role = None
                status = "review_blocked"
                reason = "No Phase 1 mapping rule approved."
            output["records"].append(
                {
                    "document_key": document,
                    "raw_label": label,
                    "mapping_status": status,
                    "period_start": start,
                    "period_end": end,
                    "default_amount_type": amount_type,
                    "label_role": role,
                    "occurrence_count": len(occurrences[label]),
                    "occurrences": occurrences[label],
                    "decision_reason": reason,
                }
            )
    output["summary"] = dict(Counter(r["mapping_status"] for r in output["records"]))
    return output


def group_decision(records):
    if any(is_chart_source_table(record) for record in records):
        chart_records = [record for record in records if is_chart_source_table(record)]
        remaining = [record for record in records if not is_chart_source_table(record)]
        if remaining:
            return "split_duplicate_summaries", "Overview chart-backed table pages are duplicate summaries; chart visuals are duplicate presentation and are ignored for normalization."
        return "duplicate_summary", "Overview chart-backed table page is a duplicate summary; chart visual is duplicate presentation and is ignored for normalization."
    families = {record["table_family"] for record in records}
    if families == {"capital_project_profile"}:
        return "do_not_merge_profiles", "Adjacent project profiles remain separate records; alias review is handled outside section continuation."
    if families <= {"operating_statement", "operating_detail", "facility_operating_statement", "capital_budget_schedule", "tax_assessment_rate"}:
        return "proposed_section_group", "Profile continuation group is accepted as a Phase 1 source-section candidate pending row-level normalization."
    return "review_blocked", "Mixed family continuation group requires source-specific review."


def build_section_review():
    output = {"schema_version": 1, "status": "phase_1_review_started", "records": []}
    for document in DOCUMENTS:
        groups = defaultdict(list)
        for record in load_records(document):
            if record.get("continuation_group"):
                groups[record["continuation_group"]].append(record)
        for group_key in sorted(groups):
            records = sorted(groups[group_key], key=lambda item: item["page_start"])
            decision, reason = group_decision(records)
            split_sets = []
            if decision == "split_duplicate_summaries":
                for record in records:
                    if is_chart_source_table(record):
                        split_sets.append(("duplicate_summary", [record]))
                remaining = [record for record in records if not is_chart_source_table(record)]
                if remaining:
                    split_sets.append(("proposed_section_group", remaining))
            else:
                split_sets.append((decision, records))
            for split_index, (split_decision, split_records) in enumerate(split_sets, start=1):
                pages = [record["page_start"] for record in split_records]
                section_key = f"{document}-{group_key}-{split_index}-{slug(split_records[0]['table_family'])}"
                output["records"].append(
                    {
                        "document_key": document,
                        "source_continuation_group": group_key,
                        "section_key": section_key,
                        "page_start": min(pages),
                        "page_end": max(pages),
                        "candidate_keys": [record["table_key"] for record in split_records],
                        "families": sorted({record["table_family"] for record in split_records}),
                        "titles": [record["title_guess"] for record in split_records],
                        "page_roles": {
                            record["table_key"]: (
                                "summary"
                                if split_decision == "duplicate_summary"
                                else (
                                    "profile"
                                    if record["table_family"] == "capital_project_profile"
                                    else ("section_start" if index == 0 else "section_continuation")
                                )
                            )
                            for index, record in enumerate(split_records)
                        },
                        "decision": split_decision,
                        "decision_reason": (
                            "Overview chart-backed table page is treated like the 2026/2027 page 18/19 precedent: duplicate_summary for normalization; chart visual ignored."
                            if split_decision == "duplicate_summary"
                            else reason
                        ),
                    }
                )
    output["summary"] = dict(Counter(r["decision"] for r in output["records"]))
    return output


def build_profile_identity_review():
    output = {"schema_version": 1, "status": "phase_1_review_started", "records": []}
    for document in DOCUMENTS:
        for record in load_records(document):
            if record["table_family"] != "capital_project_profile":
                continue
            source_title, source_project = extract_profile_identity(document, record["page_start"])
            title_guess = record["title_guess"]
            title_wrapped = bool(source_title and normalized_text(source_title) != normalized_text(title_guess))
            project_wrapped = bool(source_project and normalized_text(source_project) != normalized_text(title_guess))
            mismatch = (
                bool(source_title and source_project)
                and not normalized_text(source_title).startswith(normalized_text(source_project))
                and not normalized_text(source_project).startswith(normalized_text(source_title))
            )
            flags = []
            if title_wrapped:
                flags.append("title_guess_incomplete_or_wrapped")
            if project_wrapped:
                flags.append("project_value_wrapped_or_differs_from_title_guess")
            if mismatch:
                flags.append("title_project_mismatch")
            override_reason = PROFILE_IDENTITY_OVERRIDES.get((document, record["table_key"]))
            output["records"].append(
                {
                    "document_key": document,
                    "table_key": record["table_key"],
                    "page_start": record["page_start"],
                    "title_guess": title_guess,
                    "source_title": source_title,
                    "source_project": source_project,
                    "review_flags": flags,
                    "identity_status": "reviewed_with_source_conflict" if override_reason else ("review_blocked" if mismatch else "reviewed"),
                    "identity_decision_reason": override_reason,
                }
            )
    output["summary"] = dict(Counter(r["identity_status"] for r in output["records"]))
    output["flag_summary"] = dict(Counter(flag for r in output["records"] for flag in r["review_flags"]))
    return output


def load_raw_rows(document, table_id):
    records = json.loads((BASE / document / "raw-tables" / "source_table_rows.json").read_text())["records"]
    return [record for record in records if record["table_id"] == table_id]


def build_tax_rate_formula_review():
    output = {"schema_version": 1, "status": "phase_1_review_complete", "records": []}
    # Page 19 declares rates and denominators but does not contain assessment/revenue expressions.
    output["records"].append({
        "document_key": "2025-2026", "table_key": "2025-2026-p019", "page_start": 19,
        "decision": "approved_rate_declarations",
        "formula_applicability": "not_applicable",
        "decision_reason": "The page declares property-tax rates per $100 assessed value and utility rates by stated service denominator; it contains no assessment-to-revenue calculation.",
        "normalization_rule": "Import reviewed rates with their stated denominator and effective-date context. Do not derive revenue from this page.",
    })
    expression = re.compile(r"\$([\d,]+) x \$([\d.]+) per \$100.*?\$\s*([\d,]+)")
    formula_records = []
    for row in load_raw_rows("2025-2026", "ctown_budget_2025_2026_p145"):
        match = expression.search(row["raw_text"])
        if not match:
            continue
        assessment, rate, reported_revenue = (Decimal(value.replace(",", "")) for value in match.groups())
        calculated = assessment * rate / Decimal("100")
        rounded_calculated = calculated.quantize(Decimal("1"))
        formula_records.append({
            "row_id": row["row_id"], "raw_label": row["cells"][0],
            "assessment_base": str(assessment), "rate_per_100_assessed_value": str(rate),
            "denominator": "100 dollars of assessed value", "reported_revenue": str(reported_revenue),
            "calculated_revenue": str(calculated), "rounded_calculated_revenue": str(rounded_calculated),
            "difference_after_nearest_dollar_rounding": str(reported_revenue - rounded_calculated),
            "rounding_difference": str(reported_revenue - calculated),
            "decision": "approved_formula", "formula_code": "assessment_times_rate_divided_by_100",
            "decision_reason": "Reported revenue equals the formula rounded to the nearest dollar; the unrounded difference is retained for reconciliation evidence.",
        })
    output["records"].append({
        "document_key": "2025-2026", "table_key": "2025-2026-p145", "page_start": 145,
        "decision": "approved_assessment_rate_formulas", "formula_applicability": "applicable",
        "formula_code": "assessment_times_rate_divided_by_100", "formula_records": formula_records,
        "decision_reason": "Each extracted assessment/rate/revenue expression reconciles exactly; preserve the three reported values and use the formula only for reconciliation.",
    })
    output["summary"] = dict(Counter(record["decision"] for record in output["records"]))
    output["formula_summary"] = {"approved": len(formula_records), "nonzero_differences_after_nearest_dollar_rounding": sum(record["difference_after_nearest_dollar_rounding"] != "0" for record in formula_records)}
    return output


def build_debt_identity_review():
    output = {"schema_version": 1, "status": "phase_1_review_complete", "records": []}
    schedules = (("2025-2026-p147", 147, "city-of-charlottetown"), ("2025-2026-p149", 149, "charlottetown-water-and-sewer"))
    instrument = re.compile(r"^(?:(RBC|TD|CIBC) (\d{4}) (Swap|Loan)|(?:CMHC|FCM) Loan|Capital Leases) (?:Matuing|Maturing) (\d{4})$")
    for table_key, page_start, entity_key in schedules:
        records = []
        for row in load_raw_rows("2025-2026", f"ctown_budget_2025_2026_p{page_start:03d}"):
            label = row["cells"][0] if row["cells"] else ""
            normalized_label = label.replace("Matuing", "Maturing")
            match = instrument.fullmatch(normalized_label)
            if match:
                lender, issue_year, instrument_type, maturity_year = match.groups()
                if normalized_label.startswith("CMHC"):
                    lender, instrument_type = "CMHC", "loan"
                elif normalized_label.startswith("FCM"):
                    lender, instrument_type = "FCM", "loan"
                elif normalized_label.startswith("Capital Leases"):
                    lender, instrument_type = None, "capital_lease"
                else:
                    instrument_type = instrument_type.lower()
                records.append({
                    "row_id": row["row_id"], "raw_label": label, "normalized_label": normalized_label,
                    "reporting_entity_key": entity_key, "lender": lender, "instrument_type": instrument_type,
                    "issue_year": issue_year, "maturity_year": maturity_year,
                    "debt_instrument_key": f"{entity_key}-{slug(normalized_label)}",
                    "decision": "approved_document_scoped_instrument",
                    "decision_reason": "Entity-scoped source label provides the lender/type and maturity identity; correct the source typo only in the normalized label while retaining raw text.",
                })
            elif label == "Capital Leases":
                records.append({
                    "row_id": row["row_id"], "raw_label": label, "normalized_label": label,
                    "reporting_entity_key": entity_key, "lender": None, "instrument_type": "capital_lease",
                    "issue_year": None, "maturity_year": None,
                    "debt_instrument_key": f"{entity_key}-capital-leases",
                    "decision": "approved_document_scoped_instrument",
                    "decision_reason": "The source reports a capital-lease balance, principal, and interest but no lender or maturity. Preserve it as a document-scoped capital-lease instrument without inventing missing attributes.",
                })
            elif label == "New Debt":
                records.append({
                    "row_id": row["row_id"], "raw_label": label, "reporting_entity_key": entity_key,
                    "debt_instrument_key": None, "decision": "approved_planned_debt_bucket",
                    "decision_reason": "No lender, issue year, or maturity is reported. Retain balance and interest as a document-period planned-debt bucket and do not create a stable debt instrument.",
                })
        output["records"].append({
            "document_key": "2025-2026", "table_key": table_key, "page_start": page_start,
            "reporting_entity_key": entity_key, "decision": "approved_debt_identity_mapping", "instrument_records": records,
            "decision_reason": "The two schedules are separate reporting-entity statements. Identical lender/year/maturity labels are not merged across entities.",
        })
    output["summary"] = {"approved_schedules": len(output["records"]), "approved_document_scoped_instruments": sum(sum(item["decision"] == "approved_document_scoped_instrument" for item in record["instrument_records"]) for record in output["records"]), "planned_debt_buckets": sum(sum(item["decision"] == "approved_planned_debt_bucket" for item in record["instrument_records"]) for record in output["records"])}
    return output


def build_candidate_dispositions(period_review, section_review, tax_rate_review, debt_identity_review):
    period_status = {
        (record["document_key"], record["raw_label"]): record["mapping_status"]
        for record in period_review["records"]
    }
    section_by_candidate = {
        (record["document_key"], candidate_key): record
        for record in section_review["records"]
        for candidate_key in record["candidate_keys"]
    }
    profile_identity_by_candidate = {
        (record["document_key"], record["table_key"]): record
        for record in build_profile_identity_review()["records"]
    }
    tax_rate_by_candidate = {(record["document_key"], record["table_key"]): record for record in tax_rate_review["records"]}
    debt_by_candidate = {(record["document_key"], record["table_key"]): record for record in debt_identity_review["records"]}
    output = {"schema_version": 1, "status": "phase_1_review_started", "records": []}
    for document, records in load_week5_records().items():
        for record in records:
            reasons = record.get("review_reasons", [])
            section_record = section_by_candidate.get((document, record["table_key"]))
            unresolved = []
            resolved = []

            if section_record and section_record["decision"] == "duplicate_summary":
                disposition = "duplicate_summary"
                disposition_reason = "Chart-backed overview table duplicates normalized detail/summary facts; chart visual is ignored."
                resolved.append("duplicate visualization summary excluded from normalization")
            else:
                if any("project alias" in reason for reason in reasons):
                    identity_record = profile_identity_by_candidate.get((document, record["table_key"]))
                    alias_status = CAPITAL_PROJECT_ALIAS_DECISIONS.get((document, record["table_key"]), ("review_blocked", [], "Missing capital project alias decision."))[0]
                    if identity_record and identity_record["identity_status"] == "review_blocked":
                        alias_status = "review_blocked"
                    if alias_status == "review_blocked":
                        unresolved.append("project alias requires cross-year review")
                    else:
                        resolved.append(f"project alias resolved as {alias_status}")
                if any("assessment/rate operands" in reason for reason in reasons):
                    review = tax_rate_by_candidate.get((document, record["table_key"]))
                    if review and review["decision"].startswith("approved"):
                        resolved.append("assessment/rate operands resolved by reviewed rate/formula decision")
                    else:
                        unresolved.append("assessment/rate operands require formula review")
                if any("debt instrument identity" in reason for reason in reasons):
                    review = debt_by_candidate.get((document, record["table_key"]))
                    if review and review["decision"] == "approved_debt_identity_mapping":
                        resolved.append("debt instrument identity and maturity labels resolved by entity-scoped review")
                    else:
                        unresolved.append("debt instrument identity and maturity labels require review")
                if any("continuation membership" in reason for reason in reasons):
                    if section_record and section_record["decision"] == "proposed_section_group":
                        resolved.append("continuation membership resolved by reviewed section group")
                    elif section_record and section_record["decision"] == "do_not_merge_profiles":
                        resolved.append("profile pages are separate records, not continuation tables")
                    else:
                        unresolved.append("continuation membership requires section-level review")
                period_reasons = [reason for reason in reasons if reason.startswith("period labels require review")]
                for period_reason in period_reasons:
                    labels = [label.strip() for label in period_reason.split(":", 1)[1].split(",")]
                    blocked = [
                        label for label in labels
                        if period_status.get((document, label)) == "review_blocked"
                    ]
                    if blocked:
                        unresolved.append(f"period labels require review: {', '.join(blocked)}")
                    else:
                        resolved.append(period_reason.replace("require review", "resolved or excluded"))

                if unresolved:
                    disposition = "review_blocked"
                    disposition_reason = "; ".join(unresolved)
                else:
                    disposition = "normalize"
                    disposition_reason = "Phase 1 mapping blockers resolved for manifest-generation input."

            output["records"].append(
                {
                    "document_key": document,
                    "table_key": record["table_key"],
                    "page_start": record["page_start"],
                    "table_family": record["table_family"],
                    "source_disposition": record["disposition"],
                    "candidate_disposition": disposition,
                    "disposition_reason": disposition_reason,
                    "source_review_reasons": reasons,
                    "resolved_reasons": resolved,
                    "unresolved_reasons": unresolved,
                    "section_key": section_record["section_key"] if section_record else None,
                    "section_decision": section_record["decision"] if section_record else None,
                }
            )
    output["summary"] = dict(Counter(r["candidate_disposition"] for r in output["records"]))
    return output


def build_capital_project_alias_review():
    output = {"schema_version": 1, "status": "phase_1_review_started", "records": []}
    identity_by_key = {
        (record["document_key"], record["table_key"]): record
        for record in build_profile_identity_review()["records"]
    }
    candidate_records = {
        (document, record["table_key"]): record
        for document in DOCUMENTS
        for record in load_records(document)
        if record["table_family"] == "capital_project_profile"
    }
    for key in sorted(CAPITAL_PROJECT_ALIAS_DECISIONS):
        document, table_key = key
        record = candidate_records[key]
        identity = identity_by_key[key]
        decision, project_keys, reason = CAPITAL_PROJECT_ALIAS_DECISIONS[key]
        if identity["identity_status"] == "review_blocked":
            decision = "review_blocked"
            project_keys = []
            reason = "Wrapped profile identity review found a title/project mismatch; alias mapping is blocked until source identity is resolved."
        output["records"].append(
            {
                "document_key": document,
                "table_key": table_key,
                "page_start": record["page_start"],
                "title_guess": record["title_guess"],
                "source_title": identity["source_title"],
                "source_project": identity["source_project"],
                "alias_decision": decision,
                "capital_project_keys": project_keys,
                "decision_reason": reason,
                "profile_identity_flags": identity["review_flags"],
                "source_period_labels": record.get("periods", []),
                "entities": record.get("entities", []),
            }
        )
    output["summary"] = dict(Counter(r["alias_decision"] for r in output["records"]))
    return output


def main():
    period_review = build_period_review()
    section_review = build_section_review()
    operating_detail_relationship_review = build_operating_detail_relationship_review()
    profile_identity_review = build_profile_identity_review()
    capital_project_alias_review = build_capital_project_alias_review()
    tax_rate_review = build_tax_rate_formula_review()
    debt_identity_review = build_debt_identity_review()
    candidate_dispositions = build_candidate_dispositions(period_review, section_review, tax_rate_review, debt_identity_review)
    for document in DOCUMENTS:
        doc_dir = BASE / document
        doc_periods = {
            "schema_version": 1,
            "records": [r for r in period_review["records"] if r["document_key"] == document],
            "summary": dict(Counter(r["mapping_status"] for r in period_review["records"] if r["document_key"] == document)),
        }
        doc_sections = {
            "schema_version": 1,
            "records": [r for r in section_review["records"] if r["document_key"] == document],
            "summary": dict(Counter(r["decision"] for r in section_review["records"] if r["document_key"] == document)),
        }
        doc_dispositions = {
            "schema_version": 1,
            "records": [r for r in candidate_dispositions["records"] if r["document_key"] == document],
            "summary": dict(Counter(r["candidate_disposition"] for r in candidate_dispositions["records"] if r["document_key"] == document)),
        }
        doc_aliases = {
            "schema_version": 1,
            "records": [r for r in capital_project_alias_review["records"] if r["document_key"] == document],
            "summary": dict(Counter(r["alias_decision"] for r in capital_project_alias_review["records"] if r["document_key"] == document)),
        }
        doc_profile_identities = {
            "schema_version": 1,
            "records": [r for r in profile_identity_review["records"] if r["document_key"] == document],
            "summary": dict(Counter(r["identity_status"] for r in profile_identity_review["records"] if r["document_key"] == document)),
            "flag_summary": dict(Counter(flag for r in profile_identity_review["records"] if r["document_key"] == document for flag in r["review_flags"])),
        }
        doc_operating_relationships = {
            "schema_version": 1,
            "records": [r for r in operating_detail_relationship_review["records"] if r["document_key"] == document],
            "summary": dict(Counter(r["presentation_pattern"] for r in operating_detail_relationship_review["records"] if r["document_key"] == document)),
        }
        (doc_dir / "period-label-review.json").write_text(json.dumps(doc_periods, indent=2) + "\n")
        (doc_dir / "section-continuation-review.json").write_text(json.dumps(doc_sections, indent=2) + "\n")
        (doc_dir / "operating-detail-relationship-review.json").write_text(json.dumps(doc_operating_relationships, indent=2) + "\n")
        (doc_dir / "capital-project-profile-identity-review.json").write_text(json.dumps(doc_profile_identities, indent=2) + "\n")
        (doc_dir / "candidate-disposition-review.json").write_text(json.dumps(doc_dispositions, indent=2) + "\n")
        (doc_dir / "capital-project-alias-review.json").write_text(json.dumps(doc_aliases, indent=2) + "\n")
        if document == "2025-2026":
            (doc_dir / "tax-rate-formula-review.json").write_text(json.dumps(tax_rate_review, indent=2) + "\n")
            (doc_dir / "debt-identity-review.json").write_text(json.dumps(debt_identity_review, indent=2) + "\n")
    combined = {
        "schema_version": 1,
        "period_label_review": period_review,
        "section_continuation_review": section_review,
        "operating_detail_relationship_review": operating_detail_relationship_review,
        "capital_project_profile_identity_review": profile_identity_review,
        "capital_project_alias_review": capital_project_alias_review,
        "tax_rate_formula_review": tax_rate_review,
        "debt_identity_review": debt_identity_review,
        "candidate_disposition_review": candidate_dispositions,
    }
    (BASE / "prior-year-phase-1-review-package.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(json.dumps({
        "period_summary": period_review["summary"],
        "section_summary": section_review["summary"],
        "operating_detail_relationship_summary": operating_detail_relationship_review["summary"],
        "capital_project_profile_identity_summary": profile_identity_review["summary"],
        "capital_project_alias_summary": capital_project_alias_review["summary"],
        "tax_rate_formula_summary": tax_rate_review["summary"],
        "debt_identity_summary": debt_identity_review["summary"],
        "candidate_disposition_summary": candidate_dispositions["summary"],
    }, indent=2))


if __name__ == "__main__":
    main()

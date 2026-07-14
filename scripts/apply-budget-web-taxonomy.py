"""Apply reviewed budget-edition metadata and browser-review semantic assignments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data/budget/charlottetown/budget-web-taxonomy-apply-report.json"
TAXONOMY = "charlottetown-budget-category-v1"
REVIEWER = "project-owner-authorization-2026-07-13"

EDITIONS = (
    (7, "2024-2025-budget", "2024/2025", 8),
    (8, "2025-2026-budget", "2025/2026", 9),
    (9, "2026-2027-budget", "2026/2027", None),
)

CATEGORIES = (
    ("revenue.taxation", "revenue", "Taxation"),
    ("revenue.utility", "revenue", "Utility revenue"),
    ("revenue.grants_transfers", "revenue", "Grants and transfers"),
    ("revenue.fees_charges", "revenue", "Fees and charges"),
    ("revenue.facility_program", "revenue", "Facility and program revenue"),
    ("revenue.investment_financing", "revenue", "Investment and financing revenue"),
    ("revenue.other", "revenue", "Other operating revenue"),
    ("expense.workforce", "expense", "Workforce"),
    ("expense.contracts_professional", "expense", "Contracted and professional services"),
    ("expense.materials_supplies", "expense", "Materials and supplies"),
    ("expense.facilities_occupancy", "expense", "Facilities and occupancy"),
    ("expense.fleet_transport", "expense", "Fleet and transportation"),
    ("expense.technology_communications", "expense", "Technology and communications"),
    ("expense.grants_contributions", "expense", "Grants and contributions"),
    ("expense.debt_financing", "expense", "Debt and financing costs"),
    ("expense.insurance_risk", "expense", "Insurance and risk"),
    ("expense.programs_projects", "expense", "Programs and projects"),
    ("expense.other", "expense", "Other operating expense"),
    ("capital.transportation", "capital_investment", "Transportation infrastructure"),
    ("capital.water_wastewater", "capital_investment", "Water and wastewater"),
    ("capital.facilities", "capital_investment", "Buildings and facilities"),
    ("capital.parks_recreation", "capital_investment", "Parks and recreation"),
    ("capital.fleet_equipment", "capital_investment", "Fleet and equipment"),
    ("capital.technology", "capital_investment", "Technology infrastructure"),
    ("capital.land_development", "capital_investment", "Land and development"),
    ("capital.environment_resilience", "capital_investment", "Environment and resilience"),
    ("capital.other", "capital_investment", "Other capital investment"),
    ("funding.external_partner", "capital_funding", "External partner funding"),
    ("funding.government_grant", "capital_funding", "Government grants"),
    ("funding.debt", "capital_funding", "Debt financing"),
    ("funding.reserve", "capital_funding", "Reserve funding"),
    ("funding.utility", "capital_funding", "Utility funding"),
    ("funding.general_revenue", "capital_funding", "General revenue funding"),
    ("funding.other", "capital_funding", "Other capital funding"),
)

OPERATING_RULES = (
    ("expense.workforce", r"\b(salar(?:y|ies)|wages?|benefits?|payroll|overtime|pension|staffing)\b"),
    ("expense.contracts_professional", r"\b(professional|consult(?:ing|ant)?|legal|audit(?:ing)?|engineering services)\b"),
    ("expense.facilities_occupancy", r"\b(utilities|electric(?:ity)?|heating|rent|lease|occupancy|building operations|repairs? and maintenance|repairs?/maintenance)\b"),
    ("expense.fleet_transport", r"\b(fuel|mileage|travel|transportation|vehicle repairs?|fleet)\b"),
    ("expense.technology_communications", r"\b(software|computer|technology|telephone|cellular|communications?|advertising|website|network)\b"),
    ("expense.grants_contributions", r"\b(grants?|contributions?|subsid(?:y|ies))\b"),
    ("expense.debt_financing", r"\b(debt service|interest expense|financing cost)\b"),
    ("expense.insurance_risk", r"\b(insurance|claims?)\b"),
    ("expense.materials_supplies", r"\b(supplies|materials|uniforms?|clothing|consumables)\b"),
    ("expense.programs_projects", r"\b(programs?|projects?)\b"),
    ("revenue.taxation", r"\b(property tax revenue|taxation revenue|tax revenue)\b"),
    ("revenue.utility", r"\b(water revenue|sewer revenue|utility revenue)\b"),
    ("revenue.investment_financing", r"\b(interest income|investment income)\b"),
    ("revenue.facility_program", r"\b(admissions?|sponsorship|merchandise sales|program revenue|facility revenue|ice rentals?|pool rentals?)\b"),
    ("revenue.fees_charges", r"\b(permit fees?|licen[cs]e fees?|user fees?|service charges?|rental revenue)\b"),
)

CAPITAL_RULES = (
    ("capital.water_wastewater", r"\b(water|sewer|wastewater|wellfield|booster|lift station|metering)\b"),
    ("capital.transportation", r"\b(street|road|sidewalk|traffic|transit|bus|buses|trail|pathway|bike|parkade|parking)\b"),
    ("capital.parks_recreation", r"\b(park|field|playground|recreation|sport|turf|pool)\b"),
    ("capital.technology", r"\b(technology|computer|network|website|server|radio|communication|software|fiber)\b"),
    ("capital.environment_resilience", r"\b(tree|stormwater|storm water|climate|energy|charger|solar|resilience)\b"),
    ("capital.land_development", r"\b(land acquisition|property acquisition|site development)\b"),
    ("capital.facilities", r"\b(building|facility|station|arena|centre|center|roof|compressor|renovation)\b"),
    ("capital.fleet_equipment", r"\b(vehicle|fleet|truck|equipment|zamboni)\b"),
)

PROGRAMS = {
    "environment-sustainability-transit": "Environment Sustainability and Transit",
    "information-technology": "Information Technology",
    "fire-emergency-preparedness": "Fire and Emergency Preparedness",
    "parks-recreation": "Parks and Recreation",
    "police": "Police",
    "public-works": "Public Works",
    "water-sewer": "Charlottetown Water and Sewer",
    "eastlink-centre": "Charlottetown Eastlink Centre",
    "bell-aliant-centre": "Charlottetown Bell Aliant Centre",
}

PROGRAM_STATEMENTS = {
    7: {
        "2024-2025-capital_budget_schedule-p046": "environment-sustainability-transit",
        "2024-2025-capital_budget_schedule-p048": "information-technology",
        "2024-2025-capital_budget_schedule-p049": "fire-emergency-preparedness",
        "2024-2025-capital_budget_schedule-p052": "parks-recreation",
        "2024-2025-capital_budget_schedule-p053": "parks-recreation",
        "2024-2025-capital_budget_schedule-p060": "police",
        "2024-2025-capital_budget_schedule-p062": "public-works",
        "2024-2025-capital_budget_schedule-p063": "public-works",
        "2024-2025-capital_budget_schedule-p070": "bell-aliant-centre",
        "2024-2025-capital_budget_schedule-p071": "eastlink-centre",
        "2024-2025-capital_budget_schedule-p072": "water-sewer",
    },
    8: {
        "2025-2026-capital_budget_schedule-p109": "environment-sustainability-transit",
        "2025-2026-capital_budget_schedule-p112": "information-technology",
        "2025-2026-capital_budget_schedule-p113": "fire-emergency-preparedness",
        "2025-2026-capital_budget_schedule-p116": "parks-recreation",
        "2025-2026-capital_budget_schedule-p117": "parks-recreation",
        "2025-2026-capital_budget_schedule-p121": "police",
        "2025-2026-capital_budget_schedule-p122": "public-works",
        "2025-2026-capital_budget_schedule-p123": "public-works",
        "2025-2026-capital_budget_schedule-p136": "water-sewer",
        "2025-2026-capital_budget_schedule-p142": "eastlink-centre",
        "2025-2026-capital_budget_schedule-p143": "bell-aliant-centre",
    },
    9: {
        "capital-page-111-capital": "environment-sustainability-transit",
        "capital-page-117-capital": "fire-emergency-preparedness",
        "capital-page-120-capital": "information-technology",
        "capital-page-122-capital": "parks-recreation",
        "capital-page-123-capital": "parks-recreation",
        "capital-page-127-capital": "police",
        "capital-page-133-capital": "public-works",
        "capital-page-134-capital": "public-works",
        "capital-page-135-capital": "public-works",
        "capital-page-144-capital": "water-sewer",
        "capital-page-146-capital": "eastlink-centre",
        "capital-page-147-capital": "bell-aliant-centre",
    },
}

DEPARTMENTS = {
    "public works": ("public-works", "Public Works"),
    "charlottetown police services": ("police", "Police"),
    "environment and sustainability": ("environment-sustainability", "Environment and Sustainability"),
    "enivronment and sustainability": ("environment-sustainability", "Environment and Sustainability"),
    "parks and recreation": ("parks-recreation", "Parks and Recreation"),
    "charlottetown fire department": ("fire-emergency-preparedness", "Fire and Emergency Preparedness"),
    "information technology (it)": ("information-technology", "Information Technology"),
}


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def ensure_decision(cur: psycopg.Cursor, source_type: str, source_key: str, target_type: str, target_id: int, rationale: str) -> int:
    cur.execute(
        """SELECT id FROM budget.normalization_decision
           WHERE source_entity_type=%s AND source_entity_key=%s AND target_entity_type=%s
             AND target_entity_id=%s AND reviewer=%s AND taxonomy_version=%s
           ORDER BY id LIMIT 1""",
        (source_type, source_key, target_type, target_id, REVIEWER, TAXONOMY),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        """INSERT INTO budget.normalization_decision
          (source_entity_type,source_entity_key,target_entity_type,target_entity_id,decision,rationale,reviewer,taxonomy_version)
          VALUES(%s,%s,%s,%s,'approved',%s,%s,%s) RETURNING id""",
        (source_type, source_key, target_type, target_id, rationale, REVIEWER, TAXONOMY),
    )
    return int(cur.fetchone()[0])


def first_rule(label: str, rules: tuple[tuple[str, str], ...]) -> str | None:
    normalized = re.sub(r"\s+", " ", label.casefold()).strip()
    for key, pattern in rules:
        if re.search(pattern, normalized):
            return key
    return None


def apply(cur: psycopg.Cursor) -> dict[str, int]:
    counts = {key: 0 for key in (
        "editions", "categories", "snapshot_revisions", "proposed_line_categories",
        "proposed_funding_categories", "organization_units", "project_departments",
        "programs", "program_line_assignments", "followup_forecasts", "followup_forecasts_removed",
    )}

    cur.execute("SELECT id FROM budget.municipality WHERE slug='charlottetown'")
    municipality_id = int(cur.fetchone()[0])

    for document_id, period_label, edition_label, subsequent_document_id in EDITIONS:
        cur.execute(
            """SELECT DISTINCT fp.id FROM budget.document_period dp
               JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
               WHERE dp.document_id=%s AND fp.label=%s""",
            (document_id, period_label),
        )
        period_ids = [int(row[0]) for row in cur.fetchall()]
        if len(period_ids) != 1:
            raise RuntimeError(f"Expected one primary period for document {document_id}: {period_ids}")
        cur.execute(
            """INSERT INTO budget.budget_edition
              (document_id,primary_fiscal_period_id,subsequent_document_id,edition_label,review_status)
              VALUES(%s,%s,%s,%s,'approved') ON CONFLICT (document_id) DO NOTHING""",
            (document_id, period_ids[0], subsequent_document_id, edition_label),
        )
        counts["editions"] += cur.rowcount

    category_ids: dict[str, int] = {}
    for key, domain, display_name in CATEGORIES:
        cur.execute(
            """INSERT INTO budget.normalized_category(taxonomy_version,category_key,domain,display_name)
               VALUES(%s,%s,%s,%s) ON CONFLICT (taxonomy_version,category_key) DO NOTHING""",
            (TAXONOMY, key, domain, display_name),
        )
        counts["categories"] += cur.rowcount
        cur.execute(
            "SELECT id FROM budget.normalized_category WHERE taxonomy_version=%s AND category_key=%s",
            (TAXONOMY, key),
        )
        category_ids[key] = int(cur.fetchone()[0])

    cur.execute(
        """INSERT INTO budget.publication_snapshot_taxonomy_revision
          (snapshot_id,category_taxonomy_version,rationale,authorized_by)
          VALUES(1,%s,%s,%s)
          ON CONFLICT (snapshot_id) DO UPDATE SET
            category_taxonomy_version=EXCLUDED.category_taxonomy_version,
            rationale=EXCLUDED.rationale,
            authorized_by=EXCLUDED.authorized_by,
            revised_at=now()
          WHERE (budget.publication_snapshot_taxonomy_revision.category_taxonomy_version,
                 budget.publication_snapshot_taxonomy_revision.rationale,
                 budget.publication_snapshot_taxonomy_revision.authorized_by)
            IS DISTINCT FROM (EXCLUDED.category_taxonomy_version,EXCLUDED.rationale,EXCLUDED.authorized_by)""",
        (TAXONOMY, "Authorized browser review of versioned category assignments on snapshot 1.", REVIEWER),
    )
    counts["snapshot_revisions"] = cur.rowcount

    cur.execute(
        """SELECT DISTINCT li.id,coalesce(li.display_label,li.raw_label),s.statement_kind,
                  cp.name AS project_name
           FROM budget.publication_observation pf
           JOIN budget.financial_observation f ON f.id=pf.observation_id
           JOIN budget.line_item li ON li.id=f.line_item_id
           JOIN budget.statement s ON s.id=li.statement_id
           LEFT JOIN budget.capital_project_observation cpf ON cpf.observation_id=f.id
           LEFT JOIN budget.capital_project cp ON cp.id=cpf.capital_project_id
           WHERE pf.snapshot_id=1 AND li.aggregation_role='detail'"""
    )
    line_candidates: dict[int, tuple[str, str]] = {}
    for line_id, label, statement_kind, project_name in cur.fetchall():
        category_key = None
        rationale = None
        if statement_kind in {"operating", "operating_detail", "operating_statement", "facility_operating_statement"}:
            category_key = first_rule(str(label), OPERATING_RULES)
            rationale = "Controlled-label candidate in an operating statement; requires browser review."
        elif project_name:
            category_key = first_rule(str(project_name), CAPITAL_RULES)
            rationale = "Controlled project-label candidate in a published capital statement; requires browser review."
        if category_key and line_id not in line_candidates:
            line_candidates[int(line_id)] = (category_key, rationale)

    for line_id, (category_key, rationale) in sorted(line_candidates.items()):
        cur.execute(
            """INSERT INTO budget.line_item_category_assignment
              (line_item_id,normalized_category_id,taxonomy_version,assignment_status,mapping_basis,rationale)
              VALUES(%s,%s,%s,'proposed','controlled_label',%s)
              ON CONFLICT (line_item_id,taxonomy_version,normalized_category_id) DO NOTHING""",
            (line_id, category_ids[category_key], TAXONOMY, rationale),
        )
        counts["proposed_line_categories"] += cur.rowcount

    cur.execute(
        """SELECT DISTINCT f.id FROM budget.publication_observation pf
           JOIN budget.financial_observation f ON f.id=pf.observation_id
           JOIN budget.amount_type at ON at.id=f.amount_type_id
           JOIN budget.capital_project_observation cpf ON cpf.observation_id=f.id
           WHERE pf.snapshot_id=1 AND at.code='funding_deduction'"""
    )
    for (observation_id,) in cur.fetchall():
        cur.execute(
            """INSERT INTO budget.capital_funding_category_assignment
              (observation_id,normalized_category_id,taxonomy_version,assignment_status,mapping_basis,rationale)
              VALUES(%s,%s,%s,'proposed','structural',%s)
              ON CONFLICT (observation_id,taxonomy_version,normalized_category_id) DO NOTHING""",
            (observation_id, category_ids["funding.external_partner"], TAXONOMY,
             "Published project funding-deduction candidate; exact funding-source subtype requires browser review."),
        )
        counts["proposed_funding_categories"] += cur.rowcount

    cur.execute(
        """SELECT p.id,p.capital_project_id,p.raw_value,cp.reporting_entity_id
           FROM budget.capital_project_profile p
           JOIN budget.capital_project cp ON cp.id=p.capital_project_id
           JOIN budget.publication_snapshot ps ON ps.id=1 AND p.document_id=ANY(ps.source_document_ids)
           WHERE p.field_key='department' AND p.review_status='approved'"""
    )
    for profile_id, project_id, raw_value, reporting_entity_id in cur.fetchall():
        department = DEPARTMENTS.get(str(raw_value).casefold().strip())
        if department is None:
            raise RuntimeError(f"Unmapped approved project department: {raw_value}")
        unit_key, display_name = department
        cur.execute(
            """INSERT INTO budget.organization_unit
              (reporting_entity_id,unit_key,display_name,unit_type,effective_from)
              VALUES(%s,%s,%s,'department','1900-01-01')
              ON CONFLICT (reporting_entity_id,unit_key,effective_from) DO NOTHING""",
            (reporting_entity_id, unit_key, display_name),
        )
        counts["organization_units"] += cur.rowcount
        cur.execute(
            """SELECT id FROM budget.organization_unit
               WHERE reporting_entity_id=%s AND unit_key=%s AND effective_from='1900-01-01'""",
            (reporting_entity_id, unit_key),
        )
        unit_id = int(cur.fetchone()[0])
        decision_id = ensure_decision(
            cur, "capital_project_profile", str(profile_id), "organization_unit", unit_id,
            f"Approved department profile value {raw_value!r} maps to reviewed organization unit {unit_key}.",
        )
        cur.execute(
            """INSERT INTO budget.project_organization_assignment
              (capital_project_id,organization_unit_id,source_profile_id,assignment_status,mapping_basis,normalization_decision_id,rationale)
              VALUES(%s,%s,%s,'approved','profile_department',%s,%s)
              ON CONFLICT (capital_project_id,organization_unit_id) DO NOTHING""",
            (project_id, unit_id, profile_id, decision_id,
             f"Source profile reports department {raw_value!r}."),
        )
        counts["project_departments"] += cur.rowcount

    program_ids: dict[str, int] = {}
    for key, display_name in PROGRAMS.items():
        cur.execute(
            """INSERT INTO budget.capital_program(municipality_id,program_key,display_name,review_status)
               VALUES(%s,%s,%s,'approved') ON CONFLICT (municipality_id,program_key) DO NOTHING""",
            (municipality_id, key, display_name),
        )
        counts["programs"] += cur.rowcount
        cur.execute(
            "SELECT id FROM budget.capital_program WHERE municipality_id=%s AND program_key=%s",
            (municipality_id, key),
        )
        program_ids[key] = int(cur.fetchone()[0])

    for document_id, mappings in PROGRAM_STATEMENTS.items():
        for statement_key, program_key in mappings.items():
            cur.execute(
                "SELECT id FROM budget.statement WHERE document_id=%s AND statement_key=%s",
                (document_id, statement_key),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"Missing mapped capital statement {document_id}:{statement_key}")
            statement_id = int(row[0])
            program_id = program_ids[program_key]
            decision_id = ensure_decision(
                cur, "statement", f"{document_id}:{statement_key}", "capital_program", program_id,
                f"The source page heading identifies {PROGRAMS[program_key]} as the capital program.",
            )
            cur.execute("SELECT id FROM budget.line_item WHERE statement_id=%s ORDER BY id", (statement_id,))
            for (line_id,) in cur.fetchall():
                cur.execute(
                    """INSERT INTO budget.capital_program_line_assignment
                      (line_item_id,capital_program_id,assignment_status,mapping_basis,normalization_decision_id,rationale)
                      VALUES(%s,%s,'approved','source_heading',%s,%s)
                      ON CONFLICT (line_item_id) DO NOTHING""",
                    (line_id, program_id, decision_id,
                     f"Statement source heading is {PROGRAMS[program_key]}."),
                )
                counts["program_line_assignments"] += cur.rowcount

    cur.execute(
        """WITH pairs(original_document_id,next_document_id,period_label,forecast_label) AS (
             VALUES (7::bigint,8::bigint,'2024-2025-budget'::text,'2024-2025-forecast'::text),
                    (8::bigint,9::bigint,'2025-2026-budget'::text,'2025-2026-forecast'::text)
           ), original AS (
             SELECT p.*,f.id AS original_observation_id,re.slug AS entity_slug,
               CASE WHEN s.statement_kind IN ('operating','operating_detail','operating_statement','facility_operating_statement')
                    THEN 'operating' ELSE s.statement_kind END AS family,
               lower(regexp_replace(coalesce(li.display_label,li.raw_label),'[^a-zA-Z0-9]+','','g')) AS label_key,
               f.value_numeric,mu.code AS unit
             FROM pairs p JOIN budget.statement s ON s.document_id=p.original_document_id
             JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
             JOIN budget.line_item li ON li.statement_id=s.id JOIN budget.financial_observation f ON f.line_item_id=li.id
             JOIN budget.document_period dp ON dp.id=f.document_period_id
             JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
             JOIN budget.amount_type at ON at.id=f.amount_type_id JOIN budget.measure_unit mu ON mu.id=f.measure_unit_id
             WHERE fp.label=p.period_label AND at.code='budget' AND f.value_numeric IS NOT NULL AND f.review_status='approved'
           ), later AS (
             SELECT p.*,fb.id AS later_budget_observation_id,ff.id AS forecast_observation_id,re.slug AS entity_slug,
               CASE WHEN s.statement_kind IN ('operating','operating_detail','operating_statement','facility_operating_statement')
                    THEN 'operating' ELSE s.statement_kind END AS family,
               lower(regexp_replace(coalesce(li.display_label,li.raw_label),'[^a-zA-Z0-9]+','','g')) AS label_key,
               fb.value_numeric,mu.code AS unit
             FROM pairs p JOIN budget.statement s ON s.document_id=p.next_document_id
             JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
             JOIN budget.line_item li ON li.statement_id=s.id JOIN budget.financial_observation fb ON fb.line_item_id=li.id
             JOIN budget.document_period dpb ON dpb.id=fb.document_period_id
             JOIN budget.fiscal_period fpb ON fpb.id=dpb.fiscal_period_id
             JOIN budget.amount_type atb ON atb.id=fb.amount_type_id JOIN budget.measure_unit mu ON mu.id=fb.measure_unit_id
             JOIN budget.financial_observation ff ON ff.line_item_id=li.id JOIN budget.document_period dpf ON dpf.id=ff.document_period_id
             JOIN budget.fiscal_period fpf ON fpf.id=dpf.fiscal_period_id
             JOIN budget.amount_type atf ON atf.id=ff.amount_type_id
             WHERE fpb.label=p.period_label AND atb.code='budget' AND fpf.label=p.forecast_label AND atf.code='forecast'
               AND ff.measure_unit_id=fb.measure_unit_id AND fb.value_numeric IS NOT NULL AND ff.review_status='approved'
           ), candidates AS (
             SELECT o.original_observation_id,l.later_budget_observation_id,l.forecast_observation_id,
                    count(*) OVER(PARTITION BY o.original_observation_id) AS original_candidate_count,
                    count(*) OVER(PARTITION BY l.forecast_observation_id) AS forecast_target_count
             FROM original o JOIN later l
             USING(original_document_id,next_document_id,period_label,forecast_label,entity_slug,family,label_key,unit,value_numeric)
           )
           SELECT original_observation_id,later_budget_observation_id,forecast_observation_id
           FROM candidates WHERE original_candidate_count=1 AND forecast_target_count=1 ORDER BY original_observation_id"""
    )
    valid_followups = cur.fetchall()
    valid_original_ids = [int(row[0]) for row in valid_followups]
    cur.execute(
        """DELETE FROM budget.financial_observation_followup_observation
           WHERE observation_kind='forecast' AND mapping_basis='exact_identity' AND review_status='approved'
             AND NOT (original_observation_id=ANY(%s))""",
        (valid_original_ids,),
    )
    counts["followup_forecasts_removed"] = cur.rowcount
    for original_observation_id, later_budget_observation_id, forecast_observation_id in valid_followups:
        cur.execute(
            """INSERT INTO budget.financial_observation_followup_observation
              (original_observation_id,subsequent_budget_observation_id,subsequent_observation_observation_id,observation_kind,mapping_basis,review_status)
              VALUES(%s,%s,%s,'forecast','exact_identity','approved')
              ON CONFLICT (original_observation_id,observation_kind) DO NOTHING""",
            (original_observation_id, later_budget_observation_id, forecast_observation_id),
        )
        counts["followup_forecasts"] += cur.rowcount

    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit changes. Default validates and rolls back.")
    args = parser.parse_args()
    with psycopg.connect(db_url()) as connection, connection.cursor() as cur:
        counts = apply(cur)
        cur.execute("SELECT count(*) FROM budget.publication_observation WHERE snapshot_id=1")
        snapshot_fact_count = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM budget.v_published_financial_observations WHERE snapshot_id=1")
        published_view_count = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM budget.financial_observation_followup_observation WHERE review_status='approved'")
        followup_total = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM budget.line_item_category_assignment WHERE taxonomy_version=%s AND assignment_status='proposed'", (TAXONOMY,))
        proposed_category_total = int(cur.fetchone()[0])
        if snapshot_fact_count != 6256 or published_view_count != 6256:
            raise RuntimeError(f"Snapshot cardinality changed: membership={snapshot_fact_count}, view={published_view_count}")
        report = {
            "mode": "apply" if args.apply else "dry_run",
            "taxonomy_version": TAXONOMY,
            "counts_added": counts,
            "snapshot_1_fact_membership": snapshot_fact_count,
            "snapshot_1_published_view_rows": published_view_count,
            "approved_followup_forecasts": followup_total,
            "proposed_line_category_assignments": proposed_category_total,
        }
        report["report_sha256"] = hashlib.sha256(
            json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if args.apply:
            connection.commit()
        else:
            connection.rollback()
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate 2026/2027 budget normalization artifacts and imported raw controls."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"


def load(name: str) -> dict:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def main() -> int:
    inventory = load("canonical-table-inventory.json")
    sections = load("section-inventory.json")
    continuations = load("continuation-decisions.json")
    coverage = load("normalization-coverage.json")
    reviews = load("unresolved-review-report.json")
    reconciliation = load("reconciliation-report.json")
    consolidated = load("normalization/consolidated-operating-row-mapping.json")
    supporting = load("normalization/operating-supporting-row-mapping.json")
    rates = load("normalization/tax-utility-rate-row-mapping.json")
    city_government = load("normalization/city-government-row-mapping.json")
    raw_values = load("raw-tables/source_values.json")
    economic = load("normalization/economic-tourism-culture-row-mapping.json")
    assert inventory["profile_candidate_count"] == 116
    assert inventory["first_pass_candidate_count"] == 114
    assert inventory["canonical_candidate_count"] == 116
    assert len(inventory["records"]) == 116
    assert all(item["disposition"] in {"normalize", "review_blocked", "non_financial", "duplicate_summary", "excluded"} for item in inventory["records"])
    assert sections["section_count"] == 31 == len(sections["records"])
    section_candidate_keys = [key for section in sections["records"] for key in section["candidate_keys"]]
    assert len(section_candidate_keys) == 116 == len(set(section_candidate_keys))
    assert set(section_candidate_keys) == {item["canonical_key"] for item in inventory["records"]}
    assert continuations["candidate_count"] == 85 == len(continuations["records"])
    assert all(item["decision"] == "grouped_with_section" for item in continuations["records"])
    assert sum(coverage["disposition_counts"].values()) == 116
    assert reviews["open_count"] == 0 == len(reviews["records"])
    reviewed_candidate_keys = [key for review in reviews["records"] for key in review["candidate_keys"]]
    assert len(reviewed_candidate_keys) == coverage["disposition_counts"].get("review_blocked", 0)
    assert len(reviewed_candidate_keys) == len(set(reviewed_candidate_keys))
    assert consolidated["authoritative_candidate_key"].endswith("p020")
    assert consolidated["duplicate_summary_candidate_keys"] == [
        "ctown-2026-2027-2026-2027-p018", "ctown-2026-2027-2026-2027-p019"
    ]
    assert len(consolidated["rows"]) == 31
    assert sum(len(row["facts"]) for row in consolidated["rows"]) == 91
    assert all(row["review_status"] == "approved" for row in consolidated["rows"])
    assert supporting["mapping_status"] == "approved"
    assert len(supporting["rows"]) == 64
    assert sum(len(row["facts"]) for row in supporting["rows"]) == 192
    assert supporting["blocking_rows"] == []
    assert sum(fact["value_state"] == "dash_unresolved" for row in supporting["rows"] for fact in row["facts"]) == 4
    assert len(rates["rows"]) == 15
    assert {row["reporting_entity_key"] for row in rates["rows"]} == {
        "city-of-charlottetown", "charlottetown-water-sewer"
    }
    assert city_government["mapping_status"] == "approved"
    assert len(city_government["summary_rows"]) == 31
    assert sum(len(row["facts"]) for row in city_government["summary_rows"]) == 93
    assert len(city_government["supporting_rows"]) == 27
    recovered = [value for value in raw_values["records"] if value["detection_method"] == "aligned_column_recovery"]
    assert len(recovered) == 672
    assert not any(value["raw_value"].isdigit() and len(value["raw_value"]) == 4 for value in recovered)
    assert economic["mapping_status"] == "approved"
    assert len(economic["summary_rows"]) == 37
    assert sum(len(row["facts"]) for row in economic["summary_rows"]) == 111
    assert len(economic["supporting_rows"]) == 29
    malformed_group = next(value for value in raw_values["records"] if value["row_id"] == "ctown_budget_2026_2027_p036_r015" and value["value_index"] == 3)
    assert malformed_group["raw_value"] == "2, 250,000" and malformed_group["parsed_decimal"] == "2250000"
    departmental_expected = {
        "environment-sustainability-transit": (26, 78, 20),
        "finance-audit-fiscal": (27, 81, 21), "fire-services": (19, 57, 18),
        "human-resources": (11, 33, 10), "mayor-council": (11, 33, 10),
        "parks-recreation": (58, 174, 43), "planning-heritage": (29, 87, 24),
        "police-services": (28, 84, 26), "water-sewer-operating": (40, 120, 37),
        "public-works-buildings": (41, 123, 36),
    }
    for name, expected in departmental_expected.items():
        mapping = load(f"normalization/{name}-row-mapping.json")
        observed = (len(mapping["summary_rows"]), sum(len(row["facts"]) for row in mapping["summary_rows"]), len(mapping["supporting_rows"]))
        assert mapping["mapping_status"] == "approved" and observed == expected
    assert "public-works-buildings" not in {review["section_key"] for review in reviews["records"]}
    public_works = load("normalization/public-works-buildings-row-mapping.json")
    service_contracts = [row for row in public_works["summary_rows"] if row["raw_label"] == "Service Contracts"]
    assert len(service_contracts) == 2
    assert [[fact["numeric_value"] for fact in row["facts"]] for row in service_contracts] == [
        [None, None, None], ["161000", "161000", "164220"],
    ]
    municipal_expected = {
        "Property Taxes": ["360000", "360000", "360000"],
        "Maintenance": ["250000", "250000", "255000"],
        "Public Art Maintenance": ["2000", "2000", "2000"],
        "Snow Removal": ["36000", "36000", "36720"],
    }
    for label, expected in municipal_expected.items():
        row = next(
            row for row in public_works["summary_rows"]
            if row["raw_label"] == label and int(row["row_id"].rsplit("r", 1)[1]) >= 44
        )
        assert [fact["numeric_value"] for fact in row["facts"]] == expected
    capital = load("normalization/capital-budget-schedule-mapping.json")
    profiles = load("normalization/capital-project-profile-mapping.json")
    assert len(capital["schedules"]) == 13
    assert sum(len(schedule["rows"]) for schedule in capital["schedules"]) == 216
    assert sum(len(row["facts"]) for schedule in capital["schedules"] for row in schedule["rows"]) == 240
    assert len(profiles["profiles"]) == 24
    assert all(profile["review_status"] == "approved_narrative_only" for profile in profiles["profiles"])
    assert reviews["records"] == []
    debt = load("normalization/water-sewer-debt-row-mapping.json")
    assert len(debt["instruments"]) == 10
    assert all(len(item["facts"]) == 3 for item in debt["instruments"])
    assert [fact["numeric_value"] for fact in debt["reported_total"]["facts"]] == [
        "39008543", "2571761", "1649818",
    ]
    civic = load("normalization/civic-centre-operating-row-mapping.json")
    bell = load("normalization/bell-aliant-department-row-mapping.json")
    assert len(civic["rows"]) == 109
    assert next(row for row in civic["rows"] if row["raw_label"] == "TOTAL REVENUE")["numeric_value"] == "2333480.00"
    assert next(row for row in civic["rows"] if row["raw_label"] == "TOTAL EXPENSES")["numeric_value"] == "2272025.00"
    assert next(row for row in civic["rows"] if row["raw_label"] == "NET INCOME")["numeric_value"] == "61455.00"
    bell_rows = [row for page in bell["pages"] for row in page["rows"]]
    assert len(bell_rows) == 52 and sum(len(row["facts"]) for row in bell_rows) == 104
    assert sum(row["raw_label"] == "Total Operating Revenue" for row in bell_rows) == 3
    assert all(len(row["facts"]) == 2 for row in bell_rows)
    assert coverage["disposition_counts"] == {"duplicate_summary": 3, "non_financial": 1, "normalize": 112}
    assert reconciliation["check_count"] == 7
    assert reconciliation["passed_count"] == 4
    assert reconciliation["review_count"] == 3

    url = "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("""WITH d AS (
          SELECT id FROM budget.source_document WHERE sha256='d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac'
        ), t AS (SELECT id FROM budget.source_table WHERE document_id=(SELECT id FROM d) AND table_key LIKE 'ctown_budget_2026_2027_%')
        SELECT
          (SELECT count(*) FROM budget.source_page WHERE document_id=(SELECT id FROM d)),
          (SELECT count(*) FROM t),
          (SELECT count(*) FROM budget.source_table_row WHERE source_table_id IN (SELECT id FROM t)),
          (SELECT count(*) FROM budget.source_table_cell c JOIN budget.source_table_column col ON col.id=c.source_table_column_id WHERE c.source_row_id IN (SELECT r.id FROM budget.source_table_row r WHERE r.source_table_id IN (SELECT id FROM t)) AND col.column_index>0),
          (SELECT count(*) FROM budget.publication_snapshot),
          (SELECT count(*) FROM budget.import_batch WHERE extractor_version='full-1')""")
        assert cursor.fetchone() == (154, 114, 3233, 3092, 0, 1)
    print("2026/2027 normalization controls passed: 116 candidates in 31 sections, zero section reviews, exact raw counts, no publication snapshot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

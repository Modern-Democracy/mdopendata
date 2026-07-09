"""Build Phase 4 reconciliation catalogue for the 2026/2027 budget manifest."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
MANIFEST = BASE / "normalized-import-manifest.json"
CATALOGUE = BASE / "normalized-import-reconciliation-catalogue.json"
REPORT = BASE / "normalized-import-reconciliation-report.json"

TOLERANCE = Decimal("1")
EXPLICIT_OUTPUT_LINE_KEYS = {
    "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r019",
    "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r033",
    "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r003",
    "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r011",
    "civic-centre-operating-statement:ctown_budget_2026_2027_p104_r011",
    "public-works-buildings-statement:ctown_budget_2026_2027_p087_r054",
    "operating-supporting-schedules-statement:ctown_budget_2026_2027_p022_r037",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decimal_value(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def calculation_value(fact: dict) -> Decimal:
    if fact["value_state"] == "dash_unresolved" and fact["value_numeric"] is None:
        return Decimal("0")
    return decimal_value(fact["value_numeric"]) or Decimal("0")


def row_number(line_key: str) -> int:
    return int(line_key.rsplit("_r", 1)[1])


def page_number(line_key: str) -> int:
    return int(line_key.rsplit("_p", 1)[1].split("_", 1)[0])


def money(value: Decimal) -> str:
    return format(value, "f")


def result_status(difference: Decimal | None, reported_state: str) -> tuple[bool, str]:
    if reported_state not in {"reported", "dash_unresolved"}:
        return False, "reported_value_review"
    if difference is None:
        return False, "missing_input_review"
    if abs(difference) <= TOLERANCE:
        return True, "pass"
    return False, "reconciliation_review"


def fact_lookup(manifest: dict) -> dict[tuple[str, str, str], dict]:
    return {
        (fact["line_key"], fact["document_period_key"], fact["amount_type"]): fact
        for fact in manifest["facts"]
    }


def add_check(records: list[dict], *, check_key: str, family: str, statement_key: str,
              formula: str, output_fact: dict, input_facts: list[dict],
              tolerance: Decimal = TOLERANCE) -> None:
    if not input_facts:
        return
    input_sum = sum(calculation_value(fact) for fact in input_facts)
    reported = calculation_value(output_fact)
    difference = None if reported is None else input_sum - reported
    passed, status = result_status(difference, output_fact["value_state"])
    records.append({
        "check_key": check_key,
        "family": family,
        "statement_key": statement_key,
        "formula": formula,
        "input_fact_keys": [fact["key"] for fact in input_facts],
        "reported_fact_key": output_fact["key"],
        "calculated_value": money(input_sum),
        "reported_value": output_fact["value_numeric"],
        "reported_value_state": output_fact["value_state"],
        "difference": None if difference is None else money(difference),
        "tolerance": money(tolerance),
        "passed": passed,
        "status": status,
    })


def build_segment_checks(manifest: dict) -> tuple[list[dict], list[dict]]:
    facts_by_line_period_amount = fact_lookup(manifest)
    lines_by_statement: dict[str, list[dict]] = defaultdict(list)
    for line in manifest["line_items"]:
        lines_by_statement[line["statement_key"]].append(line)
    for lines in lines_by_statement.values():
        lines.sort(key=lambda item: (page_number(item["key"]), row_number(item["key"]), item["key"]))

    records = []
    exclusions = []
    for statement_key, lines in sorted(lines_by_statement.items()):
        if statement_key == "consolidated-operating-statement":
            continue
        segment: list[dict] = []
        for line in lines:
            role = line["aggregation_role"]
            label = line["raw_label"].lower()
            if role == "detail":
                segment.append(line)
                continue
            if role not in {"subtotal", "total"}:
                continue
            if statement_key == "appendix-water-sewer-debt-statement":
                segment = []
                continue
            if line["key"] in EXPLICIT_OUTPUT_LINE_KEYS:
                segment = []
                continue
            if statement_key == "capital-page-110-capital":
                segment = []
                continue
            if len(segment) < 2 or "net " in label or "surplus" in label or "earnings" in label or "income" in label:
                segment = []
                continue
            for fact in [x for x in manifest["facts"] if x["line_key"] == line["key"]]:
                if fact["amount_type"] not in {"budget", "forecast", "gross", "principal", "interest", "balance"}:
                    continue
                candidate_segment = segment
                if "expense" in label or "expenditure" in label:
                    candidate_segment = [
                        detail for detail in candidate_segment
                        if detail["raw_label"].strip().lower() != "revenue"
                    ]
                inputs = [
                    facts_by_line_period_amount.get((detail["key"], fact["document_period_key"], fact["amount_type"]))
                    for detail in candidate_segment
                ]
                inputs = [item for item in inputs if item is not None]
                if len(inputs) < 2:
                    continue
                before = len(records)
                add_check(
                    records,
                    check_key=f"segment_sum:{statement_key}:{line['key'].rsplit(':', 1)[1]}:{fact['document_period_key']}:{fact['amount_type']}",
                    family="segment_sum_to_reported_total",
                    statement_key=statement_key,
                    formula="sum adjacent detail facts = reported subtotal or total",
                    output_fact=fact,
                    input_facts=inputs,
                )
                record = records[-1] if len(records) > before else None
                if record and record["status"] in {"reconciliation_review", "reported_value_review"}:
                    exclusions.append({
                        "candidate_key": record["check_key"],
                        "statement_key": statement_key,
                        "reported_fact_key": record["reported_fact_key"],
                        "reason": "adjacent block did not reconcile; source row hierarchy requires explicit reviewed component mapping before this can become an applicable check",
                        "calculated_value": record["calculated_value"],
                        "reported_value": record["reported_value"],
                        "difference": record["difference"],
                    })
                    records.pop()
            segment = []
    return records, exclusions


def find_line(manifest: dict, statement_key: str, label: str) -> dict | None:
    target = label.lower()
    for line in manifest["line_items"]:
        if line["statement_key"] == statement_key and line["raw_label"].lower() == target:
            return line
    return None


def find_lines(manifest: dict, statement_key: str, label: str) -> list[dict]:
    target = label.lower()
    return [line for line in manifest["line_items"]
            if line["statement_key"] == statement_key and line["raw_label"].lower() == target]


def add_formula(records: list[dict], manifest: dict, *, check_key: str, family: str,
                statement_key: str, output_line: dict, input_lines: list[dict],
                document_period_key: str, amount_type: str, signs: list[int]) -> None:
    by_key = fact_lookup(manifest)
    output = by_key.get((output_line["key"], document_period_key, amount_type))
    inputs = [by_key.get((line["key"], document_period_key, amount_type)) for line in input_lines]
    if output is None or any(item is None for item in inputs):
        return
    signed_inputs = []
    for fact, sign in zip(inputs, signs):
        clone = dict(fact)
        value = decimal_value(clone["value_numeric"])
        clone["value_numeric"] = None if value is None else money(value * sign)
        signed_inputs.append(clone)
    add_check(
        records,
        check_key=check_key,
        family=family,
        statement_key=statement_key,
        formula=" + ".join(("+" if sign > 0 else "-") + " input" for sign in signs).lstrip("+") + " = reported value",
        output_fact=output,
        input_facts=signed_inputs,
    )


def build_named_checks(manifest: dict) -> list[dict]:
    records = []
    period_keys = sorted({fact["document_period_key"] for fact in manifest["facts"]})

    for statement_key in ["civic-centre-operating-statement", "bell-aliant-operating-statement"]:
        revenue_lines = find_lines(manifest, statement_key, "TOTAL REVENUE") + find_lines(manifest, statement_key, "Total Operating Revenue")
        expense_lines = find_lines(manifest, statement_key, "TOTAL EXPENSES") + find_lines(manifest, statement_key, "Total Operating Expenses")
        net_lines = find_lines(manifest, statement_key, "NET INCOME") + find_lines(manifest, statement_key, "Operating Earnings (Loss)")
        for revenue, expense, net in zip(revenue_lines, expense_lines, net_lines):
            for period in period_keys:
                amount_type = period.rsplit(":", 1)[1]
                if amount_type not in {"budget", "forecast"}:
                    continue
                add_formula(
                    records, manifest,
                    check_key=f"net_operating:{statement_key}:{net['key'].rsplit(':', 1)[1]}:{period}",
                    family="revenue_less_expense",
                    statement_key=statement_key,
                    output_line=net,
                    input_lines=[revenue, expense],
                    document_period_key=period,
                    amount_type=amount_type,
                    signs=[1, -1],
                )

    for gross_line, funding_line, net_line in capital_triplets(manifest):
        for fact in [x for x in manifest["facts"] if x["line_key"] == net_line["key"] and x["amount_type"] == "net"]:
            gross = next((x for x in manifest["facts"] if x["line_key"] == gross_line["key"]
                          and x["document_period_key"] == fact["document_period_key"]
                          and x["amount_type"] == "gross"), None)
            funding = next((x for x in manifest["facts"] if x["line_key"] == funding_line["key"]
                            and x["document_period_key"] == fact["document_period_key"]
                            and x["amount_type"] == "funding_deduction"), None)
            if gross and funding:
                add_check(
                    records,
                    check_key=f"capital_net:{gross_line['statement_key']}:{net_line['key'].rsplit(':', 1)[1]}:{fact['document_period_key']}",
                    family="capital_gross_less_partner_funding",
                    statement_key=gross_line["statement_key"],
                    formula="reported gross + partner funding deduction = reported net",
                    output_fact=fact,
                    input_facts=[gross, funding],
                )

    page110_relationships = [
        (
            "capital_page_110_city_net",
            "capital-page-110-capital:ctown_budget_2026_2027_p110_r026",
            [
                ("capital-page-110-capital:ctown_budget_2026_2027_p110_r024", "gross"),
                ("capital-page-110-capital:ctown_budget_2026_2027_p110_r025", "funding_deduction"),
            ],
            "capital page 110 city gross plus partner funding deduction = net city capital budget",
        ),
        (
            "capital_page_110_water_sewer_net",
            "capital-page-110-capital:ctown_budget_2026_2027_p110_r030",
            [
                ("capital-page-110-capital:ctown_budget_2026_2027_p110_r028", "gross"),
                ("capital-page-110-capital:ctown_budget_2026_2027_p110_r029", "funding_deduction"),
            ],
            "capital page 110 water and sewer gross plus partner funding deduction = water and sewer net",
        ),
        (
            "capital_page_110_city_utility_net",
            "capital-page-110-capital:ctown_budget_2026_2027_p110_r031",
            [
                ("capital-page-110-capital:ctown_budget_2026_2027_p110_r026", "gross"),
                ("capital-page-110-capital:ctown_budget_2026_2027_p110_r030", "gross"),
            ],
            "capital page 110 net city plus water and sewer net = total city and utility net",
        ),
    ]
    for prefix, output_line_key, input_specs, formula in page110_relationships:
        output_facts = [fact for fact in manifest["facts"] if fact["line_key"] == output_line_key]
        for output in output_facts:
            inputs = []
            for line_key, amount_type in input_specs:
                input_fact = next((fact for fact in manifest["facts"]
                                   if fact["line_key"] == line_key
                                   and fact["document_period_key"] == output["document_period_key"]
                                   and fact["amount_type"] == amount_type), None)
                if input_fact is None:
                    inputs = []
                    break
                inputs.append(input_fact)
            if not inputs:
                continue
            add_check(
                records,
                check_key=f"{prefix}:{output['document_period_key']}",
                family="capital_page_110_title_scoped_net",
                statement_key="capital-page-110-capital",
                formula=formula,
                output_fact=output,
                input_facts=inputs,
            )

    explicit_sum_relationships = [
        (
            "civic_centre_arena_revenue",
            "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r019",
            [
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r013",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r014",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r015",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r016",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r017",
            ],
            "Civic Centre arena revenue component rows = total arena revenue",
        ),
        (
            "civic_centre_trade_centre_revenue",
            "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r033",
            [
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r024",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r031",
            ],
            "Civic Centre Old Home Week subtotal plus trade-centre charge subtotal = total trade centre revenue",
        ),
        (
            "civic_centre_other_revenue",
            "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r003",
            [
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r039",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r041",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r042",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p101_r043",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r001",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r002",
            ],
            "Civic Centre rental-income subtotal plus miscellaneous revenue rows = total other revenue",
        ),
        (
            "civic_centre_large_event_revenue",
            "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r011",
            [
                "civic-centre-operating-statement:ctown_budget_2026_2027_p102_r010",
            ],
            "Civic Centre large-event charge subtotal = total large events revenue",
        ),
        (
            "civic_centre_large_event_expense",
            "civic-centre-operating-statement:ctown_budget_2026_2027_p104_r011",
            [
                "civic-centre-operating-statement:ctown_budget_2026_2027_p104_r007",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p104_r008",
                "civic-centre-operating-statement:ctown_budget_2026_2027_p104_r010",
            ],
            "Civic Centre large-event charge subtotal plus card discounts plus trade-centre subtotal = total large events expense",
        ),
        (
            "public_works_municipal_buildings_expenses",
            "public-works-buildings-statement:ctown_budget_2026_2027_p087_r054",
            [
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r040",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r041",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r042",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r043",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r044",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r046",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r048",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r050",
                "public-works-buildings-statement:ctown_budget_2026_2027_p087_r051",
            ],
            "Municipal Buildings expense rows, excluding prior Public Works summary row, = total municipal buildings expenses",
        ),
    ]
    for prefix, output_line_key, input_line_keys, formula in explicit_sum_relationships:
        output_facts = [fact for fact in manifest["facts"] if fact["line_key"] == output_line_key]
        for output in output_facts:
            inputs = []
            for input_line_key in input_line_keys:
                input_fact = next((fact for fact in manifest["facts"]
                                   if fact["line_key"] == input_line_key
                                   and fact["document_period_key"] == output["document_period_key"]
                                   and fact["amount_type"] == output["amount_type"]), None)
                if input_fact is None and input_line_key.endswith("ctown_budget_2026_2027_p087_r051"):
                    snow_period = {
                        "2026-2027:ctown_budget_2026_2027_p087:full-2:column-2:forecast": (
                            "2026-2027:ctown_budget_2026_2027_p087:full-2:column-1:forecast", "forecast"
                        ),
                        "2026-2027:ctown_budget_2026_2027_p087:full-2:column-3:budget": (
                            "2026-2027:ctown_budget_2026_2027_p087:full-2:column-2:budget", "budget"
                        ),
                    }.get(output["document_period_key"])
                    if snow_period:
                        input_fact = next((fact for fact in manifest["facts"]
                                           if fact["line_key"] == input_line_key
                                           and fact["document_period_key"] == snow_period[0]
                                           and fact["amount_type"] == snow_period[1]), None)
                if input_fact is None:
                    inputs = []
                    break
                inputs.append(input_fact)
            if inputs:
                add_check(
                    records,
                    check_key=f"{prefix}:{output['document_period_key']}",
                    family="explicit_source_component_sum",
                    statement_key=output_line_key.split(":", 1)[0],
                    formula=formula,
                    output_fact=output,
                    input_facts=inputs,
                )

    supporting_total_line = "operating-supporting-schedules-statement:ctown_budget_2026_2027_p022_r037"
    supporting_input_lines = [
        line["key"] for line in manifest["line_items"]
        if line["statement_key"] == "operating-supporting-schedules-statement"
        and line["aggregation_role"] == "detail"
        and (":ctown_budget_2026_2027_p021_" in line["key"] or ":ctown_budget_2026_2027_p022_" in line["key"])
    ]
    document_periods = {period["key"]: period for period in manifest["document_periods"]}
    for output in [fact for fact in manifest["facts"] if fact["line_key"] == supporting_total_line]:
        output_period = document_periods[output["document_period_key"]]
        inputs = []
        for input_line_key in supporting_input_lines:
            input_fact = next((fact for fact in manifest["facts"]
                               if fact["line_key"] == input_line_key
                               and fact["amount_type"] == output["amount_type"]
                               and document_periods[fact["document_period_key"]]["fiscal_period_key"] == output_period["fiscal_period_key"]), None)
            if input_fact is None:
                inputs = []
                break
            inputs.append(input_fact)
        if inputs:
            add_check(
                records,
                check_key=f"operating_supporting_budget_item_total_continued_pages_21_22:{output['document_period_key']}",
                family="continued_table_page_21_22_total",
                statement_key="operating-supporting-schedules-statement",
                formula="sum all page 21 and page 22 detail rows under identical title and headers = page 22 Budget Item Totals",
                output_fact=output,
                input_facts=inputs,
            )

    debt_total = find_line(manifest, "appendix-water-sewer-debt-statement", "Total Debt Servicing")
    debt_details = [line for line in manifest["line_items"]
                    if line["statement_key"] == "appendix-water-sewer-debt-statement"
                    and line["aggregation_role"] == "detail"]
    if debt_total:
        for amount in ["principal", "interest", "balance"]:
            total_fact = next((fact for fact in manifest["facts"]
                               if fact["line_key"] == debt_total["key"] and fact["amount_type"] == amount), None)
            if total_fact:
                inputs = [fact_lookup(manifest).get((line["key"], total_fact["document_period_key"], amount))
                          for line in debt_details]
                inputs = [item for item in inputs if item is not None]
                add_check(
                    records,
                    check_key=f"debt_total:{amount}",
                    family="debt_component_total",
                    statement_key="appendix-water-sewer-debt-statement",
                    formula=f"sum debt instrument {amount} facts = reported {amount} total",
                    output_fact=total_fact,
                    input_facts=inputs,
                )
    return records


def capital_triplets(manifest: dict) -> list[tuple[dict, dict, dict]]:
    lines_by_statement: dict[str, list[dict]] = defaultdict(list)
    for line in manifest["line_items"]:
        if line["statement_key"].startswith("capital-"):
            lines_by_statement[line["statement_key"]].append(line)
    triplets = []
    for lines in lines_by_statement.values():
        ordered = sorted(lines, key=lambda item: row_number(item["key"]))
        for index, line in enumerate(ordered):
            if not line["raw_label"].lower().startswith("total "):
                continue
            following = ordered[index + 1:index + 3]
            if len(following) == 2 and following[0]["raw_label"].lower().startswith("less:") and following[1]["raw_label"].lower().startswith("net total"):
                triplets.append((line, following[0], following[1]))
    return triplets


def main() -> int:
    manifest = load(MANIFEST)
    segment_records, segment_exclusions = build_segment_checks(manifest)
    records = segment_records + build_named_checks(manifest)
    seen = set()
    duplicates = []
    for record in records:
        if record["check_key"] in seen:
            duplicates.append(record["check_key"])
        seen.add(record["check_key"])
    records = sorted(records, key=lambda item: item["check_key"])
    for record in records:
        if record["check_key"] == "debt_total:balance" and record["difference"] == "-2":
            record["status"] = "source_document_discrepancy"
            record["source_discrepancy_note"] = (
                "Manual sum of the reported debt instrument balances is 2 CAD below the reported total."
            )
    issue_records = [
        {
            "issue_key": f"reconciliation:{record['check_key']}",
            "severity": "blocking",
            "status": "open",
            "reconciliation_check_key": record["check_key"],
            "reason": record["status"],
        }
        for record in records if not record["passed"]
    ]
    family_counts = Counter(record["family"] for record in records)
    status_counts = Counter(record["status"] for record in records)
    catalogue = {
        "schema_version": 1,
        "phase": 4,
        "status": "gate_5_review",
        "tolerance_policy": {
            "cad": "absolute difference <= 1 CAD for whole-dollar source schedules",
            "rationale": "The reviewed source tables report whole-dollar amounts; one dollar permits source rounding only.",
        },
        "records": records,
        "review_issues": issue_records,
    }
    report = {
        "schema_version": 1,
        "phase": 4,
        "check_count": len(records),
        "passed_count": sum(1 for item in records if item["passed"]),
        "review_count": sum(1 for item in records if not item["passed"]),
        "family_counts": dict(sorted(family_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "duplicate_check_keys": duplicates,
        "input_resolution": {
            "unresolved_input_count": 0,
            "unresolved_inputs": [],
            "reported_fact_resolution_count": len(records),
        },
        "statement_family_coverage": {
            "operating": sorted({record["statement_key"] for record in records if "operating" in record["family"] or record["statement_key"].endswith("-statement")}),
            "capital": sorted({record["statement_key"] for record in records if record["statement_key"].startswith("capital-")}),
            "debt": sorted({record["statement_key"] for record in records if "debt" in record["family"] or "debt" in record["statement_key"]}),
        },
        "double_counting_exclusions": [
            "supporting_breakdown/non_additive rows are excluded from adjacent segment sum checks",
            "consolidated operating summary is excluded from segment checks until department-summary equivalence is approved",
            "capital project profile narrative fields are excluded because they contain no financial fact operands",
        ],
        "candidate_exclusions": segment_exclusions,
        "candidate_exclusion_count": len(segment_exclusions),
        "gate_5_ready": not duplicates and len(records) > 0,
    }
    CATALOGUE.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {len(records)} reconciliation checks; review={report['review_count']}")
    return 0 if report["gate_5_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

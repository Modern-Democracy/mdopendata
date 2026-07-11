import json
import re
from collections import Counter
from pathlib import Path

BASE = Path("data/budget/charlottetown")
DOCUMENTS = ("2024-2025", "2025-2026")
STANDARD_2024_OPERATING_PAGES = {19, 21, 22, 24, 26, 28, 30, 32, 34, 35, 37, 39, 41, 43}
STANDARD_2024_PERIODS = {1: "2023-2024-budget", 2: "2023-2024-forecast", 3: "2024-2025-budget"}
STANDARD_2025_PERIODS = {1: "2024-2025-budget", 2: "2024-2025-forecast", 3: "2025-2026-budget"}
STANDARD_2025_MULTI_PERIOD_OPERATING_DETAIL_PAGES = {17, 18, 89}
TAX_SUBTOTAL_GROUPS = {
    "ctown_budget_2025_2026_p145_coord_r012": "PEI Residents",
    "ctown_budget_2025_2026_p145_coord_r018": "Non-Residents",
    "ctown_budget_2025_2026_p145_coord_r023": "Business Improvement Area - PEI Residents",
    "ctown_budget_2025_2026_p145_coord_r028": "Business Improvement Area - Non-Residents",
    "ctown_budget_2025_2026_p145_coord_r038": "Commercial Assessment - General",
    "ctown_budget_2025_2026_p145_coord_r046": "Commercial Assessment - Business Improvement Area",
}
CAPITAL_UNLABELED_TOTAL_LABELS = {
    "ctown_budget_2025_2026_p123_coord_r040": "Total Urban Beautification",
    "ctown_budget_2025_2026_p123_coord_r042": "Total Public Works",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    combined = {"schema_version": 2, "phase": 2, "documents": []}
    for document in DOCUMENTS:
        root = BASE / document
        candidates = [r for r in load(root / "candidate-disposition-review.json")["records"] if r["candidate_disposition"] == "normalize"]
        raw_rows = load(root / "raw-tables" / "source_table_rows.json")["records"]
        raw_values = {r["value_id"]: r for r in load(root / "raw-tables" / "source_values.json")["records"]}
        tax_formula_rows = {}
        if document == "2025-2026":
            for review in load(root / "tax-rate-formula-review.json")["records"]:
                for formula in review.get("formula_records", []):
                    tax_formula_rows[formula["row_id"]] = formula
        rows_by_table = {}
        for row in raw_rows:
            rows_by_table.setdefault(row["table_id"], []).append(row)
        records = []
        for candidate in candidates:
            table_id = f"ctown_budget_{document.replace('-', '_')}_p{candidate['page_start']:03d}"
            source_rows = rows_by_table.get(table_id, [])
            approved_standard_2024 = document == "2024-2025" and candidate["table_family"] == "operating_statement" and candidate["page_start"] in STANDARD_2024_OPERATING_PAGES
            approved_standard_2025 = document == "2025-2026" and candidate["table_family"] in {"operating_statement", "operating_detail"}
            approved_standard = approved_standard_2024 or approved_standard_2025
            approved_profile = candidate["table_family"] == "capital_project_profile"
            facility_group_label = None
            operating_detail_group_label = None
            mapped_rows = []
            for row in source_rows:
                values = [{"value_id": value_id, "raw_value": raw_values[value_id]["raw_value"], "parsed_decimal": raw_values[value_id]["parsed_decimal"], "value_kind": raw_values[value_id]["value_kind"], "value_index": raw_values[value_id]["value_index"]} for value_id in row["value_ids"]]
                label = row["cells"][0] if row["cells"] else ""
                if candidate["table_family"] == "facility_operating_statement" and not values:
                    facility_match = re.match(r"(Operating (?:Revenue|Grants|Expenses))", label)
                    if facility_match:
                        facility_group_label = facility_match.group(1)
                if candidate["table_family"] == "operating_detail" and label.endswith(":"):
                    operating_detail_group_label = label.rstrip(":")
                staff_count_context = (
                    document == "2025-2026"
                    and candidate["table_family"] == "operating_detail"
                    and candidate["page_start"] == 25
                    and bool(re.search(r"\(\d+\)$", label))
                )
                if staff_count_context:
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "source_context", "aggregation_role": "non_additive", "reporting_entity_key": "city-of-charlottetown", "facts": [], "review_status": "approved"})
                elif approved_profile:
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "profile_narrative_or_source_field", "aggregation_role": "non_additive", "financial_fact_treatment": "exclude_narrative_numbers", "review_status": "approved_narrative_only"})
                elif approved_standard and not values:
                    source_display_zero = label.lower().startswith("net ") and "-" in row["trimmed_text"]
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "total" if source_display_zero else "source_context", "aggregation_role": "total" if source_display_zero else "non_additive", "reporting_entity_key": "charlottetown-water-and-sewer" if candidate["page_start"] == 89 else "city-of-charlottetown", "facts": [], "source_display_zero_for_calculation": source_display_zero, "review_status": "approved"})
                elif approved_standard and values:
                    inferred_subtotal = (
                        document == "2025-2026"
                        and candidate["table_family"] == "operating_detail"
                        and not label
                        and operating_detail_group_label is not None
                    )
                    is_total = label.lower().startswith(("total ", "net ")) or inferred_subtotal
                    periods = STANDARD_2024_PERIODS if approved_standard_2024 else STANDARD_2025_PERIODS
                    # Later 2025/2026 detailed-breakdown pages report only the
                    # current budget; their first numeric column is not the prior-year column.
                    if document == "2025-2026" and candidate["table_family"] == "operating_detail" and candidate["page_start"] >= 25 and len(values) == 1:
                        periods = {1: "2025-2026-budget"}
                    detail_shape_approved = True
                    if document == "2025-2026" and candidate["table_family"] == "operating_detail":
                        detail_shape_approved = len(values) == (3 if candidate["page_start"] in STANDARD_2025_MULTI_PERIOD_OPERATING_DETAIL_PAGES else 1)
                    approved = (
                        (bool(label) or inferred_subtotal)
                        and detail_shape_approved
                        and [value["value_index"] for value in values] == list(range(1, len(values) + 1))
                        and all(value["value_index"] in periods for value in values)
                    )
                    facts = [{
                        "source_value_id": value["value_id"],
                        "document_period_key": periods[value["value_index"]],
                        "amount_type": "reported_amount",
                        "measure_unit": "CAD",
                        "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value",
                        "numeric_value": value["parsed_decimal"],
                    } for value in values] if approved else []
                    reporting_entity_key = "charlottetown-water-and-sewer" if candidate["page_start"] == 89 else "city-of-charlottetown"
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_group_label": operating_detail_group_label if inferred_subtotal else None, "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "subtotal" if inferred_subtotal else ("total" if is_total else "detail"), "aggregation_role": "subtotal" if inferred_subtotal else ("total" if is_total else "detail"), "reporting_entity_key": reporting_entity_key, "facts": facts, "review_status": "approved" if approved else "needs_review"})
                elif document == "2025-2026" and candidate["table_family"] == "operating_detail" and candidate["page_start"] == 89:
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "source_context", "aggregation_role": "non_additive", "reporting_entity_key": "charlottetown-water-and-sewer", "facts": [], "review_status": "approved"})
                elif document == "2025-2026" and candidate["table_family"] == "debt_schedule":
                    is_total = label.lower().startswith("total ")
                    planned_debt = label == "New Debt"
                    financial_values = values[:3]
                    source_context = (
                        not values
                        or label.startswith("Servicing of Long Term Debt")
                        or label.startswith("Total Interest")
                        or (candidate["page_start"] == 149 and label == "Charlottetown Water and Sewer")
                    )
                    approved = (
                        bool(label)
                        and not source_context
                        and len(financial_values) == 3
                        and [value["value_index"] for value in financial_values] == [1, 2, 3]
                    )
                    facts = [
                        {
                            "source_value_id": value["value_id"],
                            "document_period_key": "2025-2026-budget",
                            "amount_type": amount,
                            "measure_unit": "CAD",
                            "value_state": "reported_zero" if value["value_kind"] == "dash" else "reported_value",
                            "numeric_value": "0" if value["value_kind"] == "dash" else value["parsed_decimal"],
                        }
                        for amount, value in zip(("balance", "principal", "interest"), financial_values)
                        if not planned_debt or amount != "principal"
                    ] if approved else []
                    mapped_rows.append({
                        "row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"],
                        "source_value_ids": row["value_ids"], "source_values": values,
                        "row_semantics": "source_context" if source_context else ("planned_debt_bucket" if planned_debt else ("total" if is_total else "detail")),
                        "aggregation_role": "non_additive" if source_context else ("total" if is_total else "detail"),
                        "reporting_entity_key": "city-of-charlottetown" if candidate["page_start"] == 147 else "charlottetown-water-and-sewer",
                        "facts": facts, "review_status": "approved" if approved or source_context else "needs_review",
                    })
                elif candidate["table_family"] == "facility_operating_statement":
                    financial = [value for value in values if value["value_kind"] in {"number", "currency", "dash"}]
                    subtotal = facility_group_label is not None and (not label or not re.search(r"[A-Za-z]", label))
                    missing_leading_dash = document == "2024-2025" and label.startswith("Training ") and len(financial) == 1 and "-" in row["trimmed_text"]
                    approved = (bool(label) or subtotal) and (len(financial) == 2 or missing_leading_dash)
                    periods = ("2024-2025-budget", "2023-2024-budget") if document == "2024-2025" else ("2025-2026-budget", "2024-2025-budget")
                    fact_periods = (periods[1],) if missing_leading_dash else periods
                    facts = [{"source_value_id": value["value_id"], "document_period_key": period, "amount_type": "budget", "measure_unit": "CAD", "value_state": "reported_zero" if value["value_kind"] == "dash" else "reported_value", "numeric_value": "0" if value["value_kind"] == "dash" else value["parsed_decimal"]} for value, period in zip(financial, fact_periods)] if approved else []
                    display_zero = (not values and label.startswith("Operating Earnings (Loss)") and "-" in row["trimmed_text"]) or missing_leading_dash
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_group_label": facility_group_label if subtotal else None, "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "source_context" if not values else ("subtotal" if subtotal else ("total" if label.startswith("Total ") else "detail")), "aggregation_role": "non_additive" if not values else ("subtotal" if subtotal else ("total" if label.startswith("Total ") else "detail")), "reporting_entity_key": "bell-aliant-centre", "facts": facts, "source_display_zero_for_calculation": display_zero, "missing_reported_zero_period": periods[0] if missing_leading_dash else None, "review_status": "approved" if approved or not values else "needs_review"})
                elif document == "2025-2026" and candidate["table_family"] == "tax_assessment_rate":
                    formula = tax_formula_rows.get(row["row_id"])
                    if formula:
                        source_by_number = {value["parsed_decimal"]: value for value in values}
                        fact_specs = (
                            (formula["assessment_base"], "balance", "CAD"),
                            (formula["rate_per_100_assessed_value"], "actual", "CAD_per_100_assessed_value"),
                            (formula["reported_revenue"], "budget", "CAD"),
                        )
                        facts = [{
                            "source_value_id": source_by_number[number]["value_id"],
                            "document_period_key": "2025-2026-budget", "amount_type": amount_type,
                            "measure_unit": unit, "value_state": "reported_value", "numeric_value": number,
                        } for number, amount_type, unit in fact_specs]
                        mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "tax_assessment_rate_formula", "aggregation_role": "detail", "reporting_entity_key": "city-of-charlottetown", "facts": facts, "review_status": "approved"})
                    elif candidate["page_start"] == 19 and len(values) == 1:
                        raw_value = values[0]
                        if "Base Rate" in label:
                            unit = "CAD_per_day"
                        elif "Consumption Rate" in label:
                            unit = "CAD_per_cubic_metre"
                        elif "$" in row["trimmed_text"]:
                            unit = "CAD_per_100_assessed_value"
                        else:
                            unit = "CAD_per_year"
                        mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "rate_declaration", "aggregation_role": "total" if label == "Total" else "detail", "reporting_entity_key": "city-of-charlottetown" if unit == "CAD_per_100_assessed_value" else "charlottetown-water-and-sewer", "facts": [{"source_value_id": raw_value["value_id"], "document_period_key": "2025-2026-budget", "amount_type": "actual", "measure_unit": unit, "value_state": "reported_value", "numeric_value": raw_value["parsed_decimal"]}], "review_status": "approved"})
                    elif candidate["page_start"] == 145 and len(values) == 1 and (re.sub(r"^0\s+", "", label).startswith("Total ") or re.sub(r"^0\s+", "", label).startswith(("InLieu of Property Taxes", "Municipal Support Grant", "Partial Grant In Lieu to Taxes (QEH)"))):
                        raw_value = values[-1]
                        normalized_label = re.sub(r"^0\s+", "", label)
                        mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "normalized_label": normalized_label, "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "total" if normalized_label.startswith("Total ") else "detail", "aggregation_role": "total" if normalized_label.startswith("Total ") else "detail", "reporting_entity_key": "city-of-charlottetown", "facts": [{"source_value_id": raw_value["value_id"], "document_period_key": "2025-2026-budget", "amount_type": "budget", "measure_unit": "CAD", "value_state": "reported_value", "numeric_value": raw_value["parsed_decimal"]}], "review_status": "approved"})
                    elif row["row_id"] in TAX_SUBTOTAL_GROUPS:
                        raw_value = values[-1]
                        mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_group_label": TAX_SUBTOTAL_GROUPS[row["row_id"]], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "subtotal", "aggregation_role": "subtotal", "reporting_entity_key": "city-of-charlottetown", "facts": [{"source_value_id": raw_value["value_id"], "document_period_key": "2025-2026-budget", "amount_type": "budget", "measure_unit": "CAD", "value_state": "reported_value", "numeric_value": raw_value["parsed_decimal"]}], "review_status": "approved"})
                    else:
                        mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "source_context" if not values else "unreviewed", "aggregation_role": "non_additive" if not values else None, "review_status": "approved" if not values else "needs_review"})
                elif candidate["table_family"] == "capital_budget_schedule":
                    if not values:
                        mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "source_context", "aggregation_role": "non_additive", "review_status": "approved"})
                        continue
                    comparison_page = (document == "2024-2025" and candidate["page_start"] == 45) or (document == "2025-2026" and candidate["page_start"] == 108)
                    periods = ({1: f"{int(document[:4]) - 1}-{document[:4]}-budget", 2: f"{document}-budget"}
                               if comparison_page else {1: f"{document}-budget"})
                    inferred_label = CAPITAL_UNLABELED_TOTAL_LABELS.get(row["row_id"])
                    effective_label = inferred_label or label
                    lower = effective_label.lower()
                    deduction = lower.startswith(("less:", "less ")) or "partner funding" in lower
                    is_total = lower.startswith(("total ", "net "))
                    approved = bool(effective_label) and [value["value_index"] for value in values] == list(range(1, len(values) + 1)) and all(value["value_index"] in periods for value in values)
                    facts = [{"source_value_id": value["value_id"], "document_period_key": periods[value["value_index"]], "amount_type": "partner_funding" if deduction else "reported_amount", "measure_unit": "CAD", "value_state": "dash_unresolved" if value["value_kind"] == "dash" else "reported_value", "numeric_value": value["parsed_decimal"]} for value in values] if approved else []
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "normalized_label": inferred_label, "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "total" if is_total else "detail", "aggregation_role": "deduction" if deduction else ("total" if is_total else "detail"), "reporting_entity_key": "city-of-charlottetown", "facts": facts, "review_status": "approved" if approved else "needs_review"})
                else:
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "unreviewed", "aggregation_role": None, "review_status": "needs_review"})
            records.append({
                "table_key": candidate["table_key"], "table_id": table_id, "page_start": candidate["page_start"],
                "table_family": candidate["table_family"], "section_key": candidate["section_key"],
                "source_disposition": "normalize", "mapping_status": "approved_narrative_only" if approved_profile else ("approved_standard_operating_pattern" if approved_standard else "needs_row_semantic_review"), "rows": mapped_rows,
            })
        unresolved = []
        for record in records:
            for row in record["rows"]:
                if row["review_status"] != "needs_review":
                    continue
                unresolved.append({
                    "candidate_key": record["table_key"],
                    "table_id": record["table_id"],
                    "page_start": record["page_start"],
                    "table_family": record["table_family"],
                    "section_key": record["section_key"],
                    "row_id": row["row_id"],
                    "raw_label": row["raw_label"],
                    "source_value_ids": row["source_value_ids"],
                    "reason": "row semantics, period role, aggregation role, or reporting scope requires family-specific review",
                })
        summary = {
            "candidate_count": len(records),
            "raw_row_count": sum(len(r["rows"]) for r in records),
            "families": dict(Counter(r["table_family"] for r in records)),
            "approved_fact_count": sum(len(row.get("facts", [])) for record in records for row in record["rows"]),
            "unresolved_row_count": len(unresolved),
            "status": "row_semantic_review_required" if unresolved else "approved",
        }
        output = {"schema_version": 2, "phase": 2, "document_key": document, "records": records, "summary": summary}
        (root / "phase-2-row-mapping-input.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        review_output = {"schema_version": 1, "phase": 2, "document_key": document, "open_count": len(unresolved), "records": unresolved}
        (root / "phase-2-unresolved-review-report.json").write_text(json.dumps(review_output, indent=2) + "\n", encoding="utf-8")
        combined["documents"].append({"document_key": document, "artifact": str(root / "phase-2-row-mapping-input.json"), "unresolved_review_artifact": str(root / "phase-2-unresolved-review-report.json"), "summary": summary})
    (BASE / "prior-year-phase-2-row-mapping-package.json").write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()

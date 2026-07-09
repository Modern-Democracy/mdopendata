import json
from collections import Counter
from pathlib import Path

BASE = Path("data/budget/charlottetown")
DOCUMENTS = ("2024-2025", "2025-2026")
STANDARD_2024_OPERATING_PAGES = {19, 21, 22, 24, 26, 28, 30, 32, 34, 35, 37, 39, 41, 43}
STANDARD_2024_PERIODS = {0: "2023-2024-budget", 1: "2023-2024-forecast", 2: "2024-2025-budget"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    combined = {"schema_version": 1, "phase": 2, "documents": []}
    for document in DOCUMENTS:
        root = BASE / document
        candidates = [r for r in load(root / "candidate-disposition-review.json")["records"] if r["candidate_disposition"] == "normalize"]
        raw_rows = load(root / "raw-tables" / "source_table_rows.json")["records"]
        raw_values = {r["value_id"]: r for r in load(root / "raw-tables" / "source_values.json")["records"]}
        rows_by_table = {}
        for row in raw_rows:
            rows_by_table.setdefault(row["table_id"], []).append(row)
        records = []
        for candidate in candidates:
            table_id = f"ctown_budget_{document.replace('-', '_')}_p{candidate['page_start']:03d}"
            source_rows = rows_by_table.get(table_id, [])
            approved_standard = document == "2024-2025" and candidate["table_family"] == "operating_statement" and candidate["page_start"] in STANDARD_2024_OPERATING_PAGES
            approved_profile = candidate["table_family"] == "capital_project_profile"
            mapped_rows = []
            for row in source_rows:
                values = [{"value_id": value_id, "raw_value": raw_values[value_id]["raw_value"], "parsed_decimal": raw_values[value_id]["parsed_decimal"], "value_kind": raw_values[value_id]["value_kind"], "value_index": raw_values[value_id]["value_index"]} for value_id in row["value_ids"]]
                label = row["cells"][0] if row["cells"] else ""
                if approved_profile:
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "profile_narrative_or_source_field", "aggregation_role": "non_additive", "financial_fact_treatment": "exclude_narrative_numbers", "review_status": "approved_narrative_only"})
                elif approved_standard and values:
                    is_total = label.lower().startswith(("total ", "net "))
                    approved = all(value["value_index"] in STANDARD_2024_PERIODS for value in values)
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "total" if is_total else "detail", "aggregation_role": "total" if is_total else "detail", "reporting_entity_key": "city-of-charlottetown", "period_roles": [STANDARD_2024_PERIODS[value["value_index"]] for value in values] if approved else [], "amount_type": "budget_or_forecast_by_period_role", "measure_unit": "cad", "review_status": "approved" if approved else "needs_review"})
                else:
                    mapped_rows.append({"row_id": row["row_id"], "raw_label": label, "raw_text": row["trimmed_text"], "source_value_ids": row["value_ids"], "source_values": values, "row_semantics": "unreviewed", "aggregation_role": None, "review_status": "needs_review"})
            records.append({
                "table_key": candidate["table_key"], "table_id": table_id, "page_start": candidate["page_start"],
                "table_family": candidate["table_family"], "section_key": candidate["section_key"],
                "source_disposition": "normalize", "mapping_status": "approved_narrative_only" if approved_profile else ("approved_standard_operating_pattern" if approved_standard else "needs_row_semantic_review"), "rows": mapped_rows,
            })
        summary = {"candidate_count": len(records), "raw_row_count": sum(len(r["rows"]) for r in records), "families": dict(Counter(r["table_family"] for r in records)), "status": "row_semantic_review_required"}
        output = {"schema_version": 1, "phase": 2, "document_key": document, "records": records, "summary": summary}
        (root / "phase-2-row-mapping-input.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        combined["documents"].append({"document_key": document, "artifact": str(root / "phase-2-row-mapping-input.json"), "summary": summary})
    (BASE / "prior-year-phase-2-row-mapping-package.json").write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()

"""Build source-supported prior-year reconciliation catalogues."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown"
DOCUMENTS = ("2024-2025", "2025-2026")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def number(value: str | None) -> Decimal:
    return Decimal(value or "0")


def label_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", value.lower().replace("centre", "center")))
    return tokens - {"net", "total", "city", "portion"}


def main() -> int:
    for document in DOCUMENTS:
        root = BASE / document
        manifest = load(root / "normalized-import-manifest.json")
        facts = {item["key"]: item for item in manifest["facts"]}
        lines = {item["key"]: item for item in manifest["line_items"]}
        line_order = {item["key"]: index for index, item in enumerate(manifest["line_items"])}
        facts_by_statement: dict[str, list[dict]] = {}
        for fact in manifest["facts"]:
            statement = lines[fact["line_key"]]["statement_key"]
            facts_by_statement.setdefault(statement, []).append(fact)
        records = []

        for statement, statement_facts in facts_by_statement.items():
            ordered = sorted(statement_facts, key=lambda item: (line_order[item["line_key"]], item["document_period_key"], item["amount_type"]))
            if "capital_budget_schedule" in statement:
                for index, reported in enumerate(ordered):
                    if reported["amount_type"] != "net":
                        continue
                    prior = [item for item in ordered[:index] if item["document_period_key"] == reported["document_period_key"]]
                    gross = next((item for item in reversed(prior) if item["amount_type"] == "gross" and lines[item["line_key"]]["aggregation_role"] == "total"), None)
                    deductions = [item for item in prior if item["amount_type"] == "funding_deduction" and (gross is None or line_order[item["line_key"]] > line_order[gross["line_key"]])]
                    if gross is None or not deductions:
                        continue
                    gross_tokens = label_tokens(lines[gross["line_key"]]["display_label"])
                    net_tokens = label_tokens(lines[reported["line_key"]]["display_label"])
                    if not gross_tokens or len(gross_tokens & net_tokens) / len(gross_tokens | net_tokens) < Decimal("0.6"):
                        continue
                    inputs = [gross, *deductions]
                    calculated = number(gross["value_numeric"]) - sum((abs(number(item["value_numeric"])) for item in deductions), Decimal())
                    difference = calculated - number(reported["value_numeric"])
                    check_key = f"capital_net:{reported['key']}"
                    records.append({
                        "check_key": check_key, "family": "capital_gross_less_partner_funding",
                        "statement_key": statement, "formula": "reported gross + funding deductions = reported net",
                        "input_fact_keys": [item["key"] for item in inputs], "reported_fact_key": reported["key"],
                        "calculated_value": str(calculated), "reported_value": reported["value_numeric"],
                        "reported_value_state": reported["value_state"], "difference": str(difference),
                        "tolerance": "1", "passed": abs(difference) <= 1,
                        "status": "pass" if abs(difference) <= 1 else "review_required",
                    })
            if "debt_schedule" in statement:
                for reported in ordered:
                    line = lines[reported["line_key"]]
                    if line["aggregation_role"] != "total" or reported["amount_type"] == "balance":
                        continue
                    inputs = [item for item in ordered if item["document_period_key"] == reported["document_period_key"] and item["amount_type"] == reported["amount_type"] and lines[item["line_key"]]["aggregation_role"] in {"detail", "planned_debt_bucket"}]
                    if not inputs:
                        continue
                    calculated = sum((number(item["value_numeric"]) for item in inputs), Decimal())
                    difference = calculated - number(reported["value_numeric"])
                    check_key = f"debt_total:{statement}:{reported['amount_type']}"
                    records.append({
                        "check_key": check_key, "family": "debt_instrument_total",
                        "statement_key": statement, "formula": "sum of reported instrument amounts = reported schedule total",
                        "input_fact_keys": [item["key"] for item in inputs], "reported_fact_key": reported["key"],
                        "calculated_value": str(calculated), "reported_value": reported["value_numeric"],
                        "reported_value_state": reported["value_state"], "difference": str(difference),
                        "tolerance": "1", "passed": abs(difference) <= 1,
                        "status": "pass" if abs(difference) <= 1 else "review_required",
                    })

        review_issues = [{
            "issue_key": f"reconciliation:{record['check_key']}", "severity": "blocking", "status": "open",
            "reconciliation_check_key": record["check_key"], "reason": "reported_calculation_variance",
        } for record in records if not record["passed"]]
        catalogue = {
            "schema_version": 1, "phase": 4, "status": "approved" if not review_issues else "review_required",
            "tolerance_policy": {"currency_absolute": "1"}, "records": records, "review_issues": review_issues,
        }
        catalogue["catalogue_hash_without_hash_field"] = canonical_hash(catalogue)
        (root / "normalized-import-reconciliation-catalogue.json").write_text(json.dumps(catalogue, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"document_key": document, "records": len(records), "failed": len(review_issues), "hash": catalogue["catalogue_hash_without_hash_field"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

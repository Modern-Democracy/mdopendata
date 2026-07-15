#!/usr/bin/env python3
"""Build the Gate 5 Batch 04 table-context controlled review queue."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "financial-statements" / "charlottetown"
OUT = DATA / "review-batches"
JSON_OUT = OUT / "table-context-batch-04.json"
MD_OUT = OUT / "table-context-batch-04.md"

PERIOD_REVISIONS = {
    11: {
        "financial_years": ["2024", "2023"],
        "contextual_years": ["2000", "2022", "2025"],
        "basis": "The source assumptions table has March 31, 2024 and March 31, 2023 column headings; OCR omitted 2023.",
    },
    18: {
        "financial_years": ["2024", "2023", "2025", "2026", "2027", "2028", "2029"],
        "contextual_years": ["2015"],
        "basis": "The source includes 2024 and 2023 monetary comparisons and a principal-repayment schedule for 2025 through 2029.",
    },
    46: {
        "financial_years": ["2025", "2024", "2026", "2027", "2028", "2029", "2030"],
        "contextual_years": [],
        "basis": "The source includes a 2025 and 2024 monetary comparison, principal repayments for 2026 through 2030, and lease commitments for 2026 and 2027.",
    },
    94: {
        "financial_years": ["2024", "2023", "2025", "2026", "2027", "2028", "2029"],
        "contextual_years": ["2016", "2054"],
        "basis": "The source has 2024 and 2023 debt-balance columns and principal-repayment rows for 2025 through 2029; 2016 and 2054 occur in agreement or maturity narrative.",
    },
    109: {
        "financial_years": ["2025", "2024", "2026", "2027", "2028", "2029", "2030"],
        "contextual_years": ["2016"],
        "basis": "The source has 2025 and 2024 debt-balance columns and principal-repayment rows for 2026 through 2030; 2016 is agreement narrative.",
    },
}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    registry_path = DATA / "source-document-registry.json"
    period_path = DATA / "period-review.json"
    class_path = DATA / "statement-class-review.json"
    scope_path = DATA / "entity-scope-review.json"
    registry = read_json(registry_path)
    period_review = read_json(period_path)
    class_review = read_json(class_path)
    scope_review = read_json(scope_path)

    for name, artifact in {
        "period": period_review,
        "statement class": class_review,
        "entity scope": scope_review,
    }.items():
        if artifact["status"] != "needs_review" or artifact["counts"]["records"] != 139:
            raise RuntimeError(f"Expected 139 unresolved {name} records")

    documents = {str(item["document_key"]): item for item in registry["documents"]}
    period_by_key = {str(item["table_key"]): item for item in period_review["records"]}
    class_by_key = {str(item["table_key"]): item for item in class_review["records"]}
    scope_by_key = {str(item["table_key"]): item for item in scope_review["records"]}
    if not (set(period_by_key) == set(class_by_key) == set(scope_by_key)):
        raise RuntimeError("Table keys differ across table-context source registers")

    records: list[dict[str, object]] = []
    for record_number, table_key in enumerate(sorted(period_by_key), start=1):
        period = period_by_key[table_key]
        statement = class_by_key[table_key]
        scope = scope_by_key[table_key]
        document_key = str(period["document_key"])
        document = documents[document_key]
        manifest = read_json(DATA / document_key / "table_manifest.json")
        table_by_key = {str(item["table_key"]): item for item in manifest["records"]}
        raw_pages = read_json(DATA / document_key / "raw-tables" / "source_table_pages.json")
        page_by_key = {str(item["table_key"]): item for item in raw_pages["records"]}
        table = table_by_key[table_key]
        raw_page = page_by_key[table_key]

        stable_fields = ("document_key", "pdf_page_number", "page_key", "table_family")
        if any(period[field] != statement[field] or period[field] != scope[field] for field in stable_fields):
            raise RuntimeError(f"Source registers disagree for {table_key}")
        if (
            table["page_number"] != period["pdf_page_number"]
            or raw_page["pdf_page_number"] != period["pdf_page_number"]
            or table["page_key"] != period["page_key"]
            or table["table_family"] != period["table_family"]
        ):
            raise RuntimeError(f"Table evidence mismatch for {table_key}")

        detected_years = [str(value) for value in period["raw_detected_periods"]]
        reporting_year = str(document["reporting_date"])[:4]
        comparative_year = str(int(reporting_year) - 1)
        financial_year_candidates = [
            year for year in (reporting_year, comparative_year) if year in detected_years
        ]
        contextual_year_candidates = [
            year for year in detected_years if year not in {reporting_year, comparative_year}
        ]
        ambiguity_parts = [
            "Detected year tokens do not establish source-column roles or distinguish budget from actual columns."
        ]
        if contextual_year_candidates:
            ambiguity_parts.append(
                "Other detected years may be narrative references, maturity years, schedule dimensions, or OCR artifacts and require exact source review."
            )

        record_number = len(records) + 1
        revision = PERIOD_REVISIONS.get(record_number)
        approved_financial_years = (
            revision["financial_years"] if revision else financial_year_candidates
        )
        approved_contextual_years = (
            revision["contextual_years"] if revision else contextual_year_candidates
        )
        records.append({
            "batch_record_number": record_number,
            "document_key": document_key,
            "series_key": document["series_key"],
            "source_file": document["source_file"],
            "source_sha256": document["sha256"],
            "pdf_page_number": period["pdf_page_number"],
            "printed_page_label": raw_page["printed_page_label"],
            "page_key": period["page_key"],
            "table_key": table_key,
            "manifest_section": table["section"],
            "table_family": period["table_family"],
            "profile_confidence": table["confidence"],
            "profile_rotation_degrees": raw_page["profile_rotation_degrees"],
            "continuation_candidate": table["continuation_candidate"],
            "continuation_of_page_key": table["continuation_of_page_key"],
            "raw_title": statement["raw_title"],
            "raw_detected_years": detected_years,
            "proposed_reporting_date": period["proposed_reporting_date"],
            "proposed_financial_year_candidates": financial_year_candidates,
            "contextual_year_candidates": contextual_year_candidates,
            "source_column_roles_proposed": False,
            "proposed_statement_class": statement["proposed_statement_class"],
            "proposed_reporting_entity_key": scope["proposed_reporting_entity_key"],
            "proposed_consolidation_scope": scope["proposed_consolidation_scope"],
            "cross_entity_addition_allowed": scope["cross_entity_addition_allowed"],
            "exact_ambiguity": " ".join(ambiguity_parts),
            "approved_reporting_date": period["proposed_reporting_date"],
            "approved_financial_years": approved_financial_years,
            "approved_contextual_years": approved_contextual_years,
            "approved_statement_class": statement["proposed_statement_class"],
            "approved_reporting_entity_key": scope["proposed_reporting_entity_key"],
            "approved_consolidation_scope": scope["proposed_consolidation_scope"],
            "approved_cross_entity_addition_allowed": scope["cross_entity_addition_allowed"],
            "period_decision_basis": (
                revision["basis"]
                if revision
                else "Exact source page supports the proposed reporting-year candidates and contextual-year separation."
            ),
            "source_review_method": "visual_review_of_exact_pdf_page_at_130_dpi",
            "decision": "revised_and_approved" if revision else "approved_as_proposed",
            "decision_basis": "visual_comparison_with_exact_source_pdf_page",
            "decision_date": "2026-07-15",
            "review_status": "approved_for_controlled_table_context_application",
        })

    family_counts = Counter(str(item["table_family"]) for item in records)
    payload = {
        "schema_version": 1,
        "artifact_kind": "financial_statement_table_context_review_batch",
        "gate": 5,
        "batch_key": "table_context_batch_04",
        "status": "review_complete",
        "selection_contract": {
            "source_registers": [
                period_path.relative_to(ROOT).as_posix(),
                class_path.relative_to(ROOT).as_posix(),
                scope_path.relative_to(ROOT).as_posix(),
            ],
            "includes_every_table_key": True,
            "review_dimensions": ["period_evidence", "statement_class", "entity_scope"],
            "source_column_roles_deferred": True,
        },
        "source_artifacts": {
            period_path.relative_to(ROOT).as_posix(): sha256(period_path),
            class_path.relative_to(ROOT).as_posix(): sha256(class_path),
            scope_path.relative_to(ROOT).as_posix(): sha256(scope_path),
            registry_path.relative_to(ROOT).as_posix(): sha256(registry_path),
        },
        "counts": {
            "records": len(records),
            "source_pages": len({item["page_key"] for item in records}),
            "documents": len({item["document_key"] for item in records}),
            "tables_with_current_year_candidate": sum(
                str(item["approved_reporting_date"])[:4] in item["approved_financial_years"]
                for item in records
            ),
            "tables_with_comparative_year_candidate": sum(
                str(int(str(item["approved_reporting_date"])[:4]) - 1) in item["approved_financial_years"]
                for item in records
            ),
            "tables_with_contextual_year_candidates": sum(bool(item["approved_contextual_years"]) for item in records),
            "approved_as_proposed": len(records) - len(PERIOD_REVISIONS),
            "revised_and_approved": len(PERIOD_REVISIONS),
            "approved": len(records),
            "needs_review": 0,
        },
        "records_by_table_family": dict(sorted(family_counts.items())),
        "decision_boundary": {
            "approves_table_period_evidence": True,
            "assigns_source_column_roles": False,
            "approves_statement_classes": True,
            "approves_entity_scope": True,
            "approves_normalization": False,
            "writes_database": False,
            "changes_publication": False,
        },
        "records": records,
    }
    write_json(JSON_OUT, payload)

    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "# Gate 5 Batch 04 Table-Context Review",
        "",
        "All 139 financial-statement tables have completed exact period-evidence, statement-class, and entity-scope review.",
        "",
        "Review approved 134 proposals as written and revised five period-evidence proposals. Source-column roles remain unassigned.",
    ]
    page_key = lambda item: (item["document_key"], item["pdf_page_number"])
    for (document_key, pdf_page), page_records_iter in groupby(records, key=page_key):
        page_records = list(page_records_iter)
        printed = page_records[0]["printed_page_label"]
        if printed is None:
            printed = "not captured"
        lines.extend([
            "",
            f"## {document_key} — PDF page {pdf_page} (printed {printed})",
            "",
            "| # | Table key | Section/family | Raw title | Raw detected years | Approved financial years | Approved contextual years | Approved class | Approved entity/scope | Decision | Decision basis |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for item in page_records:
            lines.append(
                f"| {item['batch_record_number']} | `{item['table_key']}` | "
                f"{escape(item['manifest_section'])} / `{item['table_family']}` | {escape(item['raw_title'])} | "
                f"{escape(item['raw_detected_years'])} | {escape(item['approved_financial_years'])} | "
                f"{escape(item['approved_contextual_years'])} | `{item['approved_statement_class']}` | "
                f"`{item['approved_reporting_entity_key']}` / `{item['approved_consolidation_scope']}` | "
                f"`{item['decision']}` | {escape(item['period_decision_basis'])} |"
            )
    lines.extend([
        "",
        "## Boundary",
        "",
        "This batch approves table-level period evidence, statement class, and entity scope. It does not assign source-column roles, approve normalization, write the database, or change publication.",
        "",
        "## Sources",
        "",
        "- `data/financial-statements/charlottetown/period-review.json`",
        "- `data/financial-statements/charlottetown/statement-class-review.json`",
        "- `data/financial-statements/charlottetown/entity-scope-review.json`",
        "- `data/financial-statements/charlottetown/<document-key>/table_manifest.json`",
        "- `data/financial-statements/charlottetown/<document-key>/raw-tables/source_table_pages.json`",
    ])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built Batch 04 with {len(records)} table-context records")


if __name__ == "__main__":
    main()

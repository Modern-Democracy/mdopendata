#!/usr/bin/env python3
"""Build exact, non-approving Gate 5 review registers from raw extraction."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


SCHEMA_VERSION = 1
VALUE_CLASSES = {"amount_candidate", "signed_amount_candidate", "dash_candidate"}
STATEMENT_CLASS_BY_FAMILY = {
    "financial_position": "financial_position",
    "operations": "operations",
    "changes_in_net_debt": "changes_in_net_debt",
    "cash_flow": "cash_flow",
    "changes_in_net_assets_available_for_benefits": "changes_in_net_assets_available_for_benefits",
    "changes_in_pension_obligations": "changes_in_pension_obligations",
    "tangible_capital_assets_schedule": "tangible_capital_assets",
    "segmented_disclosure_schedule": "segmented_disclosure",
    "budget_reconciliation_note": "note_schedule",
    "note_disclosure_table": "note_schedule",
    "financial_schedule": "note_schedule",
}


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def compact_label(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def envelope(kind: str, records: list[dict[str, object]], **extra: object) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": kind,
        "gate": 5,
        "status": "needs_review" if records else "complete_no_candidates",
        "counts": {"records": len(records), "approved": 0, "needs_review": len(records)},
        **extra,
        "records": records,
    }


def locator(row: dict[str, object], table: dict[str, object]) -> dict[str, object]:
    return {
        "document_key": row["document_key"],
        "pdf_page_number": table["page_number"],
        "printed_page_label": table.get("printed_page_label"),
        "page_key": row["page_key"],
        "table_key": row["table_key"],
        "table_family": table["table_family"],
        "row_key": row["row_key"],
        "raw_label": row["raw_label_candidate"] or row["raw_text"],
        "raw_values": row["raw_values"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("data/financial-statements/charlottetown/source-document-registry.json"))
    parser.add_argument("--root", type=Path, default=Path("data/financial-statements/charlottetown"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = Path(__file__).resolve().parent.parent
    data_root = args.root if args.root.is_absolute() else repo / args.root
    registry_path = args.registry if args.registry.is_absolute() else repo / args.registry
    registry = read_json(registry_path)
    documents = registry["documents"]

    rows_by_document: dict[str, list[dict[str, object]]] = {}
    cells_by_document: dict[str, list[dict[str, object]]] = {}
    tables_by_key: dict[str, dict[str, object]] = {}
    table_pages_by_key: dict[str, dict[str, object]] = {}
    for document in documents:
        key = str(document["document_key"])
        document_root = data_root / key
        tables = read_json(document_root / "table_manifest.json")["records"]
        pages = read_json(document_root / "raw-tables" / "source_table_pages.json")["records"]
        rows = read_json(document_root / "raw-tables" / "source_table_rows.json")["records"]
        cells = read_json(document_root / "raw-tables" / "source_table_cells.json")["records"]
        rows_by_document[key] = rows
        cells_by_document[key] = cells
        tables_by_key.update({str(table["table_key"]): table for table in tables})
        table_pages_by_key.update({str(page["table_key"]): page for page in pages})

    period_records: list[dict[str, object]] = []
    statement_records: list[dict[str, object]] = []
    scope_records: list[dict[str, object]] = []
    hierarchy_records: list[dict[str, object]] = []
    sign_records: list[dict[str, object]] = []
    budget_records: list[dict[str, object]] = []
    taxonomy_records: list[dict[str, object]] = []

    document_by_key = {str(document["document_key"]): document for document in documents}
    for table_key in sorted(tables_by_key):
        table = tables_by_key[table_key]
        document = document_by_key[str(table["document_key"])]
        page = table_pages_by_key[table_key]
        base = {
            "document_key": document["document_key"],
            "pdf_page_number": table["page_number"],
            "printed_page_label": page["printed_page_label"],
            "page_key": table["page_key"],
            "table_key": table_key,
            "table_family": table["table_family"],
        }
        period_records.append({
            **base,
            "raw_detected_periods": table["periods"],
            "proposed_reporting_date": document["reporting_date"],
            "decision": None,
            "review_status": "needs_review",
        })
        statement_records.append({
            **base,
            "raw_title": table["title_guess"],
            "proposed_statement_class": STATEMENT_CLASS_BY_FAMILY.get(str(table["table_family"])),
            "decision": None,
            "review_status": "needs_review",
        })
        scope_records.append({
            **base,
            "proposed_reporting_entity_key": document["reporting_entity_key"],
            "proposed_consolidation_scope": document["consolidation_scope"],
            "cross_entity_addition_allowed": False,
            "decision": None,
            "review_status": "needs_review",
        })

    cells_by_key = {
        str(cell["cell_key"]): cell
        for cells in cells_by_document.values()
        for cell in cells
    }
    for document in documents:
        key = str(document["document_key"])
        mapping_records: list[dict[str, object]] = []
        for row in rows_by_document[key]:
            if not row["raw_value_cell_keys"]:
                continue
            table = tables_by_key[str(row["table_key"])]
            located = locator(row, table)
            hierarchy_record = {
                **located,
                "proposed_parent_row_key": None,
                "proposed_line_kind": None,
                "proposed_aggregation_role": None,
                "decision": None,
                "review_status": "needs_review",
            }
            hierarchy_records.append(hierarchy_record)
            mapping_records.append({
                **located,
                "proposed_period_role": None,
                "proposed_statement_class": STATEMENT_CLASS_BY_FAMILY.get(str(table["table_family"])),
                "proposed_parent_row_key": None,
                "proposed_line_kind": None,
                "proposed_aggregation_role": None,
                "proposed_value_states": [],
                "proposed_normalized_category": None,
                "review_blockers": ["period", "hierarchy", "value_state", "taxonomy"],
                "review_status": "needs_review",
            })
            if table["table_family"] == "operations" and len(row["raw_values"]) >= 2:
                budget_records.append({
                    **located,
                    "candidate_type": "document_internal_budget_actual",
                    "proposed_budget_cell_key": None,
                    "proposed_actual_cell_key": None,
                    "decision": None,
                    "review_status": "needs_review",
                })
                taxonomy_records.append({
                    **located,
                    "proposed_taxonomy_version": None,
                    "proposed_category_key": None,
                    "compatibility_requirement": "operations_flow_only",
                    "decision": None,
                    "review_status": "needs_review",
                })
        write_json(
            data_root / key / "mapping-review.json",
            envelope("financial_statement_mapping_review", mapping_records, document_key=key),
        )

        for cell in cells_by_document[key]:
            if cell["token_class"] not in {"signed_amount_candidate", "dash_candidate"}:
                continue
            row = next(row for row in rows_by_document[key] if row["row_key"] == cell["row_key"])
            table = tables_by_key[str(row["table_key"])]
            sign_records.append({
                **locator(row, table),
                "cell_key": cell["cell_key"],
                "raw_cell_text": cell["raw_text"],
                "token_class": cell["token_class"],
                "proposed_value_state": None,
                "proposed_sign": None,
                "decision": None,
                "review_status": "needs_review",
            })

    comparative_records: list[dict[str, object]] = []
    by_series: dict[str, list[dict[str, object]]] = {}
    for document in documents:
        by_series.setdefault(str(document["series_key"]), []).append(document)
    for series_key, series_documents in sorted(by_series.items()):
        ordered = sorted(series_documents, key=lambda item: int(item["series_sequence"]))
        if len(ordered) != 2:
            continue
        earlier, later = ordered
        indexes: list[dict[tuple[str, str], list[dict[str, object]]]] = []
        for document in (earlier, later):
            index: dict[tuple[str, str], list[dict[str, object]]] = {}
            for row in rows_by_document[str(document["document_key"])]:
                if not row["raw_values"]:
                    continue
                table = tables_by_key[str(row["table_key"])]
                label = compact_label(row["raw_label_candidate"])
                if len(label) < 3:
                    continue
                index.setdefault((str(table["table_family"]), label), []).append(row)
            indexes.append(index)
        for signature in sorted(set(indexes[0]) & set(indexes[1])):
            if len(indexes[0][signature]) != 1 or len(indexes[1][signature]) != 1:
                continue
            source_row = indexes[0][signature][0]
            target_row = indexes[1][signature][0]
            comparative_records.append({
                "series_key": series_key,
                "match_basis": "exact_compacted_raw_label_within_table_family",
                "raw_label_match": signature[1],
                "source": locator(source_row, tables_by_key[str(source_row["table_key"])]),
                "target": locator(target_row, tables_by_key[str(target_row["table_key"])]),
                "proposed_relationship_type": "comparative_of",
                "decision": None,
                "review_status": "needs_review",
            })

    entity_relationships = [
        {
            "parent_reporting_entity_key": "city_of_charlottetown",
            "child_reporting_entity_key": "charlottetown_water_and_sewer_corporation",
            "proposed_relationship_type": "consolidated_component",
            "source_document_keys": ["ctown_fs_city_2024_03_31_audited", "ctown_fs_city_2025_03_31_audited"],
            "decision": None,
            "review_status": "needs_review",
        },
        {
            "parent_reporting_entity_key": "city_of_charlottetown",
            "child_reporting_entity_key": "city_of_charlottetown_superannuation_plan",
            "proposed_relationship_type": "related_pension_plan",
            "source_document_keys": ["ctown_fs_city_sa_2023_12_31_audited", "ctown_fs_city_sa_2024_12_31_audited"],
            "decision": None,
            "review_status": "needs_review",
        },
        {
            "parent_reporting_entity_key": "charlottetown_water_and_sewer_corporation",
            "child_reporting_entity_key": "charlottetown_water_and_sewer_corporation_superannuation_plan",
            "proposed_relationship_type": "related_pension_plan",
            "source_document_keys": ["ctown_fs_ws_sa_2023_12_31_audited", "ctown_fs_ws_sa_2024_12_31_audited"],
            "decision": None,
            "review_status": "needs_review",
        },
    ]

    outputs = {
        "period-review.json": envelope("financial_statement_period_review", period_records),
        "statement-class-review.json": envelope("financial_statement_class_review", statement_records),
        "hierarchy-review.json": envelope("financial_statement_hierarchy_review", hierarchy_records),
        "entity-scope-review.json": envelope("financial_statement_entity_scope_review", scope_records),
        "dash-sign-review.json": envelope("financial_statement_dash_sign_review", sign_records),
        "reporting-entity-relationship-review.json": envelope("financial_statement_reporting_entity_relationship_review", entity_relationships),
        "comparative-relationship-review.json": envelope("financial_statement_comparative_relationship_review", comparative_records),
        "budget-equivalence-review.json": envelope("financial_statement_budget_equivalence_review", budget_records),
        "taxonomy-review.json": envelope("financial_statement_taxonomy_review", taxonomy_records),
    }
    for filename, payload in outputs.items():
        write_json(data_root / filename, payload)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "financial_statement_controlled_review_summary",
        "gate": 5,
        "status": "complete_with_review_queue",
        "counts": {
            "documents": len(documents),
            "mapping_rows": sum(len(read_json(data_root / str(document["document_key"]) / "mapping-review.json")["records"]) for document in documents),
            "period_records": len(period_records),
            "statement_class_records": len(statement_records),
            "hierarchy_records": len(hierarchy_records),
            "entity_scope_records": len(scope_records),
            "dash_sign_records": len(sign_records),
            "reporting_entity_relationship_candidates": len(entity_relationships),
            "comparative_relationship_candidates": len(comparative_records),
            "budget_equivalence_candidates": len(budget_records),
            "taxonomy_records": len(taxonomy_records),
            "approved_records": 0,
            "database_writes": 0,
        },
        "records_by_table_family": dict(sorted(Counter(str(record["table_family"]) for record in hierarchy_records).items())),
        "controls": {
            "all_rows_have_exact_source_locators": True,
            "all_candidates_remain_unapproved": True,
            "source_authority_review_reused": "source-authority-review.json",
            "publication_authorized": False,
        },
        "outputs": sorted(outputs),
    }
    write_json(data_root / "gate-5-review-summary.json", summary)
    print(
        f"Built {len(hierarchy_records)} row reviews and {len(comparative_records)} comparative candidates",
        flush=True,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_ROOT = REPO_ROOT / "data" / "zoning" / "charlottetown"
DRAFT_ROOT = REPO_ROOT / "data" / "zoning" / "charlottetown-draft"
IMPORTER_NAME = "scripts/import-charlottetown-zoning.py"
IMPORTER_VERSION = "1"

ALLOWED_STRUCTURED = {
    "terms",
    "uses",
    "numeric_values",
    "requirements",
    "regulation_groups",
    "conditional_rule_groups",
    "zone_relationships",
    "map_layer_references",
    "definitions",
    "cross_references",
    "site_specific_rules",
    "spatial_references",
    "other_requirements",
}
ALLOWED_RAW = {
    "source_units",
    "sections_raw",
    "clause_refs",
    "entries_raw",
    "pages_raw",
    "tables_raw",
    "map_references_raw",
}
SKIP_FILES = {"code-table-match-report.json"}


@dataclass
class Record:
    table: str
    family: str
    natural_key: str
    payload: dict[str, Any]
    links: dict[str, str] = field(default_factory=dict)
    content_hash: str = ""


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def relpath(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def content_hash(payload: dict[str, Any]) -> str:
    clean = drop_volatile(payload)
    return sha256_text(stable_json(clean))


def drop_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: drop_volatile(child)
            for key, child in value.items()
            if key not in {"review_flags", "confidence", "loaded_at", "created_at", "updated_at"}
            and not key.endswith("_id")
        }
    if isinstance(value, list):
        return [drop_volatile(child) for child in value]
    return value


def norm_key(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def citations_of(value: dict[str, Any]) -> dict[str, Any]:
    citations = value.get("citations")
    return citations if isinstance(citations, dict) else {}


def document_family(root: Path) -> str:
    if root == CURRENT_ROOT:
        return "current"
    if root == DRAFT_ROOT:
        return "draft"
    raise ValueError(f"unsupported source root: {root}")


def file_kind(path: Path) -> str:
    parent = path.parent.name
    name = path.name
    if parent == "zones":
        return "zone"
    if parent == "schedules":
        return "schedule"
    if name == "source-manifest.json":
        return "manifest"
    if name == "definitions.json":
        return "definitions"
    if name.startswith("appendix-"):
        return "appendix"
    if name.startswith("general-provisions"):
        return "general_provisions"
    return "document"


def source_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.json"))
        if path.name not in SKIP_FILES and path.name != "source-manifest.json"
    ]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relpath(path)} is not a JSON object")
    return payload


def validate_payload(path: Path, payload: dict[str, Any]) -> tuple[int, int]:
    raw_keys = set((payload.get("raw_data") or {}).keys())
    structured_keys = set((payload.get("structured_data") or {}).keys())
    unknown_raw = raw_keys - ALLOWED_RAW
    unknown_structured = structured_keys - ALLOWED_STRUCTURED
    if unknown_raw or unknown_structured:
        raise ValueError(
            f"{relpath(path)} has unsupported keys raw={sorted(unknown_raw)} structured={sorted(unknown_structured)}"
        )
    review_flags = payload.get("review_flags") or []
    needs_review = count_needs_review(payload)
    if review_flags or needs_review:
        raise ValueError(
            f"{relpath(path)} has non-empty review_flags or confidence needs_review values"
        )
    return len(review_flags), needs_review


def count_needs_review(value: Any) -> int:
    if isinstance(value, dict):
        return int(value.get("confidence") == "needs_review") + sum(
            count_needs_review(child) for child in value.values()
        )
    if isinstance(value, list):
        return sum(count_needs_review(child) for child in value)
    return 0


def revision_label(root: Path, manifest: dict[str, Any] | None) -> str:
    if manifest:
        for key in ("source_sha256", "source_document_sha256", "generated_at", "updated_at"):
            if manifest.get(key):
                return str(manifest[key])
    return f"{document_family(root)}:{sha256_text(root.as_posix())[:12]}"


def doc_metadata(payload: dict[str, Any], family: str) -> dict[str, Any]:
    metadata = payload.get("document_metadata") or {}
    return {
        "jurisdiction": metadata.get("jurisdiction") or "City of Charlottetown",
        "bylaw_name": metadata.get("bylaw_name")
        or ("Draft Zoning & Development Bylaw" if family == "draft" else "Zoning & Development Bylaw"),
        "source_document_path": metadata.get("source_document_path") or "",
        "document_type": metadata.get("document_type"),
        "zone_code": metadata.get("zone_code"),
        "title_raw": metadata.get("zone_title_raw") or metadata.get("document_title_raw") or metadata.get("title_raw"),
    }


def make_record(table: str, family: str, natural_key: str, payload: dict[str, Any], **links: str) -> Record:
    record = Record(table=table, family=family, natural_key=natural_key, payload=payload, links=links)
    record.content_hash = content_hash({"table": table, "payload": payload})
    return record


def collect_records(path: Path, payload: dict[str, Any], family: str, doc_revision_key: str) -> list[Record]:
    metadata = doc_metadata(payload, family)
    source_key = f"{doc_revision_key}|file|{relpath(path)}"
    raw = payload.get("raw_data") or {}
    structured = payload.get("structured_data") or {}
    records: list[Record] = []

    source_file_payload = {
        "repo_relpath": relpath(path),
        "file_kind": file_kind(path),
        "document_type": metadata["document_type"],
        "zone_code": metadata["zone_code"],
        "title_raw": metadata["title_raw"],
        "source_file_hash": sha256_text(path.read_text(encoding="utf-8")),
    }
    records.append(make_record("source_file", "source_file", source_key, source_file_payload))

    part_key = f"{source_key}|part|{metadata['document_type'] or file_kind(path)}|{metadata['zone_code'] or ''}"
    records.append(
        make_record(
            "bylaw_part",
            "bylaw_part",
            part_key,
            {
                "part_label_raw": (payload.get("document_metadata") or {}).get("zone_label_raw"),
                "part_title_raw": metadata["title_raw"],
                "document_type": metadata["document_type"],
                "zone_code": metadata["zone_code"],
                "source_order": 1,
                "citations": citations_of(payload.get("document_metadata") or {}),
            },
            source_file_key=source_key,
        )
    )

    section_keys: dict[str, str] = {}
    table_keys: dict[str, str] = {}
    for unit in raw.get("source_units") or []:
        unit_id = unit.get("source_unit_id") or str(unit.get("source_order") or len(records))
        unit_key = f"{source_key}|source_unit|{unit_id}"
        records.append(
            make_record(
                "source_unit",
                "source_unit",
                unit_key,
                {
                    "source_unit_source_id": unit.get("source_unit_id"),
                    "source_unit_type": unit.get("source_unit_type"),
                    "label_raw": unit.get("label_raw"),
                    "title_raw": unit.get("title_raw"),
                    "text_raw": unit.get("text_raw"),
                    "source_order": unit.get("source_order"),
                    "citations": citations_of(unit),
                },
                source_file_key=source_key,
            )
        )

    for section in raw.get("sections_raw") or []:
        section_id = section.get("section_id") or section.get("section_label_raw") or str(section.get("source_order"))
        section_key = f"{source_key}|section|{section_id}|{section.get('section_label_raw') or ''}"
        section_keys[str(section_id)] = section_key
        records.append(
            make_record(
                "section",
                "section",
                section_key,
                {
                    "section_source_id": section.get("section_id"),
                    "section_label_raw": section.get("section_label_raw"),
                    "section_title_raw": section.get("section_title_raw"),
                    "assigned_topic": assign_topic(metadata["document_type"], section.get("section_title_raw")),
                    "document_type": metadata["document_type"],
                    "zone_code": metadata["zone_code"],
                    "source_order": section.get("source_order"),
                    "citations": citations_of(section),
                },
                source_file_key=source_key,
                bylaw_part_key=part_key,
            )
        )
        for clause in section.get("clauses_raw") or []:
            clause_id = clause.get("clause_id") or clause.get("clause_label_raw") or str(clause.get("source_order"))
            clause_key = f"{section_key}|clause|{clause_id}|{sha256_text(str(clause.get('clause_text_raw') or ''))[:16]}"
            records.append(
                make_record(
                    "clause",
                    "clause",
                    clause_key,
                    {
                        "clause_source_id": clause.get("clause_id"),
                        "parent_clause_source_id": clause.get("parent_clause_id"),
                        "clause_label_raw": clause.get("clause_label_raw"),
                        "clause_path": clause_path(section.get("section_label_raw"), clause.get("clause_label_raw")),
                        "clause_text_raw": clause.get("clause_text_raw"),
                        "source_order": clause.get("source_order"),
                        "citations": citations_of(clause),
                    },
                    source_file_key=source_key,
                    section_key=section_key,
                )
            )
        for table in section.get("tables_raw") or []:
            add_table_records(records, source_key, section_key, table, doc_revision_key)
            table_keys[str(table.get("table_id"))] = f"{section_key}|table|{table.get('table_id') or table.get('source_order')}"

    for table in raw.get("tables_raw") or []:
        add_table_records(records, source_key, "", table, doc_revision_key)

    for entry in raw.get("entries_raw") or []:
        term = entry.get("term_raw") or entry.get("entry_label_raw") or entry.get("label_raw")
        text = entry.get("definition_text_raw") or entry.get("entry_text_raw") or entry.get("text_raw")
        if term and text:
            entry_key = f"{source_key}|definition|{norm_key(term)}|{sha256_text(str(text))[:16]}"
            records.append(
                make_record(
                    "definition",
                    "definition",
                    entry_key,
                    {
                        "term_key": norm_key(term),
                        "term_raw": term,
                        "definition_text_raw": text,
                        "source_order": entry.get("source_order"),
                        "citations": citations_of(entry),
                    },
                    source_file_key=source_key,
                )
            )

    for page in raw.get("pages_raw") or []:
        page_id = page.get("page_id") or page.get("page_number") or page.get("source_order")
        records.append(
            make_record(
                "raw_page",
                "raw_page",
                f"{source_key}|page|{page_id}|{sha256_text(str(page.get('text_raw') or ''))[:16]}",
                {
                    "page_source_id": page.get("page_id"),
                    "page_label_raw": page.get("page_label_raw"),
                    "page_number": page.get("page_number"),
                    "text_raw": page.get("text_raw"),
                    "source_order": page.get("source_order"),
                    "citations": citations_of(page),
                },
                source_file_key=source_key,
            )
        )

    for map_ref in raw.get("map_references_raw") or []:
        map_id = map_ref.get("map_reference_id") or map_ref.get("source_order")
        records.append(
            make_record(
                "raw_map_reference",
                "raw_map_reference",
                f"{source_key}|map_reference|{map_id}|{sha256_text(stable_json(map_ref))[:16]}",
                {
                    "map_reference_source_id": map_ref.get("map_reference_id"),
                    "map_reference_type": map_ref.get("map_reference_type"),
                    "label_raw": map_ref.get("label_raw"),
                    "title_raw": map_ref.get("title_raw"),
                    "text_raw": map_ref.get("text_raw"),
                    "source_order": map_ref.get("source_order"),
                    "citations": citations_of(map_ref),
                },
                source_file_key=source_key,
            )
        )

    for fact_family in sorted(ALLOWED_STRUCTURED):
        for index, item in enumerate(structured.get(fact_family) or [], start=1):
            if not isinstance(item, dict):
                continue
            ref_table, ref_key = resolve_source_ref(item, section_keys, table_keys)
            fact_key = f"{source_key}|structured|{fact_family}|{ref_key or ''}|{index}|{sha256_text(stable_json(drop_volatile(item)))[:16]}"
            records.append(
                make_record(
                    "structured_fact",
                    fact_family,
                    fact_key,
                    {
                        "source_record_table": ref_table,
                        "source_record_key": ref_key,
                        "fact_family": fact_family,
                        "fact_type": item.get("type") or item.get("requirement_type") or item.get("relationship_type"),
                        "raw_label": item.get("label_raw") or item.get("term_raw") or item.get("use_raw"),
                        "raw_text": item.get("text_raw") or item.get("requirement_text_raw") or item.get("description_raw"),
                        "normalized_key": norm_key(item.get("term") or item.get("term_raw") or item.get("use") or item.get("use_raw")),
                        "value_payload": drop_volatile(item),
                        "citations": citations_of(item),
                    },
                    source_file_key=source_key,
                )
            )

    return records


def add_table_records(
    records: list[Record],
    source_key: str,
    section_key: str,
    table: dict[str, Any],
    doc_revision_key: str,
) -> None:
    table_id = table.get("table_id") or table.get("source_order")
    table_key = f"{section_key or source_key}|table|{table_id}"
    records.append(
        make_record(
            "raw_table",
            "raw_table",
            table_key,
            {
                "table_source_id": table.get("table_id"),
                "table_title_raw": table.get("table_title_raw"),
                "source_order": table.get("source_order"),
                "citations": citations_of(table),
            },
            source_file_key=source_key,
            section_key=section_key,
        )
    )
    columns = table.get("columns_raw") or []
    for row_index, row in enumerate(table.get("rows_raw") or [], start=1):
        cells = row.get("cells_raw") if isinstance(row, dict) else None
        if not cells and isinstance(row, dict):
            cells = [
                {"column_id": key, "cell_text_raw": value, "source_order": idx}
                for idx, (key, value) in enumerate(row.items(), start=1)
                if key not in {"source_order", "citations"}
            ]
        for column_index, cell in enumerate(cells or [], start=1):
            column_id = cell.get("column_id")
            column = next((candidate for candidate in columns if candidate.get("column_id") == column_id), {})
            text = cell.get("cell_text_raw")
            cell_key = (
                f"{table_key}|row|{row.get('source_order') or row_index}"
                f"|col|{column_id or ''}|pos|{cell.get('source_order') or column_index}"
                f"|{sha256_text(str(text or ''))[:16]}"
            )
            records.append(
                make_record(
                    "raw_table_cell",
                    "raw_table_cell",
                    cell_key,
                    {
                        "row_order": row.get("source_order") or row_index,
                        "column_order": cell.get("source_order") or column_index,
                        "column_id": column_id,
                        "column_label_raw": column.get("column_label_raw"),
                        "cell_text_raw": text,
                    },
                    source_file_key=source_key,
                    raw_table_key=table_key,
                )
            )


def clause_path(section_label: str | None, clause_label: str | None) -> list[str] | None:
    values = [value for value in (section_label, clause_label) if value]
    return values or None


def assign_topic(document_type: str | None, title: str | None) -> str:
    haystack = f"{document_type or ''} {title or ''}".lower()
    rules = [
        ("definitions", "definitions"),
        ("permit", "process"),
        ("application", "process"),
        ("permitted use", "permitted_uses"),
        ("use", "permitted_uses"),
        ("parking", "parking"),
        ("sign", "signage"),
        ("landscap", "landscaping"),
        ("buffer", "landscaping"),
        ("setback", "lot_requirements"),
        ("yard", "lot_requirements"),
        ("lot", "lot_requirements"),
        ("height", "lot_requirements"),
        ("map", "maps_schedules"),
        ("schedule", "maps_schedules"),
        ("design", "design_standards"),
        ("site specific", "site_specific"),
        ("administration", "administration"),
    ]
    for needle, topic in rules:
        if needle in haystack:
            return topic
    return "other"


def resolve_source_ref(
    item: dict[str, Any],
    section_keys: dict[str, str],
    table_keys: dict[str, str],
) -> tuple[str | None, str | None]:
    refs = item.get("source_refs") or item.get("source_references") or []
    if isinstance(refs, dict):
        refs = [refs]
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        target_id = ref.get("content_id") or ref.get("source_id") or ref.get("section_id") or ref.get("table_id")
        if target_id in section_keys:
            return "section", section_keys[target_id]
        if target_id in table_keys:
            return "raw_table", table_keys[target_id]
    return None, None


def previous_active(conn: psycopg.Connection, table: str, natural_key: str) -> tuple[int, str] | None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {table}_id, content_hash FROM zoning.{table} WHERE natural_key = %s AND is_active",
            (natural_key,),
        )
        row = cur.fetchone()
    return (int(row[0]), str(row[1])) if row else None


def insert_event(
    conn: psycopg.Connection,
    batch_id: int,
    record: Record,
    status: str,
    prior_hash: str | None,
    active_id: int | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO zoning.import_record_event
              (import_batch_id, record_family, natural_key, prior_content_hash, content_hash,
               change_status, active_record_table, active_record_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (batch_id, record.family, record.natural_key, prior_hash, record.content_hash, status, record.table, active_id),
        )


def supersede_previous(conn: psycopg.Connection, table: str, previous_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(f"UPDATE zoning.{table} SET is_active = false WHERE {table}_id = %s", (previous_id,))


def insert_record(
    conn: psycopg.Connection,
    record: Record,
    batch_id: int,
    document_revision_id: int,
    id_maps: dict[str, dict[str, int]],
) -> int:
    payload = record.payload
    source_file_id = id_maps.get("source_file", {}).get(record.links.get("source_file_key", ""))
    section_id = id_maps.get("section", {}).get(record.links.get("section_key", ""))
    bylaw_part_id = id_maps.get("bylaw_part", {}).get(record.links.get("bylaw_part_key", ""))
    raw_table_id = id_maps.get("raw_table", {}).get(record.links.get("raw_table_key", ""))

    with conn.cursor() as cur:
        if record.table == "source_file":
            cur.execute(
                """
                INSERT INTO zoning.source_file
                  (document_revision_id, import_batch_id, repo_relpath, file_kind, document_type,
                   zone_code, title_raw, source_file_hash, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING source_file_id
                """,
                (
                    document_revision_id,
                    batch_id,
                    payload["repo_relpath"],
                    payload["file_kind"],
                    payload["document_type"],
                    payload["zone_code"],
                    payload["title_raw"],
                    payload["source_file_hash"],
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "bylaw_part":
            cur.execute(
                """
                INSERT INTO zoning.bylaw_part
                  (document_revision_id, source_file_id, part_label_raw, part_title_raw, document_type,
                   zone_code, source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING bylaw_part_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    payload["part_label_raw"],
                    payload["part_title_raw"],
                    payload["document_type"],
                    payload["zone_code"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "section":
            cur.execute(
                """
                INSERT INTO zoning.section
                  (document_revision_id, source_file_id, bylaw_part_id, section_source_id,
                   section_label_raw, section_title_raw, assigned_topic, document_type, zone_code,
                   source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING section_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    bylaw_part_id,
                    payload["section_source_id"],
                    payload["section_label_raw"],
                    payload["section_title_raw"],
                    payload["assigned_topic"],
                    payload["document_type"],
                    payload["zone_code"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "clause":
            cur.execute(
                """
                INSERT INTO zoning.clause
                  (document_revision_id, source_file_id, section_id, clause_source_id,
                   parent_clause_source_id, clause_label_raw, clause_path, clause_text_raw,
                   source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING clause_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    section_id,
                    payload["clause_source_id"],
                    payload["parent_clause_source_id"],
                    payload["clause_label_raw"],
                    payload["clause_path"],
                    payload["clause_text_raw"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "definition":
            cur.execute(
                """
                INSERT INTO zoning.definition
                  (document_revision_id, source_file_id, term_key, term_raw, definition_text_raw,
                   source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING definition_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    payload["term_key"],
                    payload["term_raw"],
                    payload["definition_text_raw"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "source_unit":
            cur.execute(
                """
                INSERT INTO zoning.source_unit
                  (document_revision_id, source_file_id, source_unit_source_id, source_unit_type,
                   label_raw, title_raw, text_raw, source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING source_unit_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    payload["source_unit_source_id"],
                    payload["source_unit_type"],
                    payload["label_raw"],
                    payload["title_raw"],
                    payload["text_raw"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "raw_page":
            cur.execute(
                """
                INSERT INTO zoning.raw_page
                  (document_revision_id, source_file_id, page_source_id, page_label_raw, page_number,
                   text_raw, source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING raw_page_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    payload["page_source_id"],
                    payload["page_label_raw"],
                    payload["page_number"],
                    payload["text_raw"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "raw_table":
            cur.execute(
                """
                INSERT INTO zoning.raw_table
                  (document_revision_id, source_file_id, section_id, table_source_id, table_title_raw,
                   source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING raw_table_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    section_id,
                    payload["table_source_id"],
                    payload["table_title_raw"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "raw_table_cell":
            cur.execute(
                """
                INSERT INTO zoning.raw_table_cell
                  (document_revision_id, source_file_id, raw_table_id, row_order, column_order,
                   column_id, column_label_raw, cell_text_raw, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING raw_table_cell_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    raw_table_id,
                    payload["row_order"],
                    payload["column_order"],
                    payload["column_id"],
                    payload["column_label_raw"],
                    payload["cell_text_raw"],
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "raw_map_reference":
            cur.execute(
                """
                INSERT INTO zoning.raw_map_reference
                  (document_revision_id, source_file_id, map_reference_source_id, map_reference_type,
                   label_raw, title_raw, text_raw, source_order, citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING raw_map_reference_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    payload["map_reference_source_id"],
                    payload["map_reference_type"],
                    payload["label_raw"],
                    payload["title_raw"],
                    payload["text_raw"],
                    payload["source_order"],
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        elif record.table == "structured_fact":
            cur.execute(
                """
                INSERT INTO zoning.structured_fact
                  (document_revision_id, source_file_id, source_record_table, source_record_key,
                   fact_family, fact_type, raw_label, raw_text, normalized_key, value_payload,
                   citations, natural_key, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING structured_fact_id
                """,
                (
                    document_revision_id,
                    source_file_id,
                    payload["source_record_table"],
                    payload["source_record_key"],
                    payload["fact_family"],
                    payload["fact_type"],
                    payload["raw_label"],
                    payload["raw_text"],
                    payload["normalized_key"],
                    Jsonb(payload["value_payload"]),
                    Jsonb(payload["citations"]),
                    record.natural_key,
                    record.content_hash,
                ),
            )
        else:
            raise ValueError(f"unsupported table {record.table}")
        return int(cur.fetchone()[0])


def ensure_document_revision(
    conn: psycopg.Connection,
    root: Path,
    manifest: dict[str, Any] | None,
    sample_payload: dict[str, Any],
    batch_id: int,
) -> int:
    family = document_family(root)
    metadata = doc_metadata(sample_payload, family)
    manifest_path = root / "source-manifest.json"
    manifest_hash = sha256_text(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    revision = revision_label(root, manifest)
    natural_key = stable_json(
        {
            "jurisdiction": metadata["jurisdiction"],
            "bylaw_name": metadata["bylaw_name"],
            "source_document_path": metadata["source_document_path"],
            "revision_label": revision,
            "document_family": family,
        }
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO zoning.bylaw_document
              (jurisdiction, bylaw_name, document_family, source_document_path, document_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (jurisdiction, bylaw_name, document_family, source_document_path)
            DO UPDATE SET document_type = EXCLUDED.document_type
            RETURNING bylaw_document_id
            """,
            (
                metadata["jurisdiction"],
                metadata["bylaw_name"],
                family,
                metadata["source_document_path"],
                metadata["document_type"],
            ),
        )
        bylaw_document_id = int(cur.fetchone()[0])
        cur.execute(
            """
            INSERT INTO zoning.document_revision
              (bylaw_document_id, revision_label, source_manifest_path, source_manifest_hash, natural_key)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (natural_key) DO UPDATE
            SET source_manifest_hash = EXCLUDED.source_manifest_hash
            RETURNING document_revision_id
            """,
            (
                bylaw_document_id,
                revision,
                relpath(manifest_path) if manifest_path.exists() else None,
                manifest_hash,
                natural_key,
            ),
        )
        return int(cur.fetchone()[0])


def create_batch(conn: psycopg.Connection, root: Path, manifest: dict[str, Any] | None) -> int:
    manifest_path = root / "source-manifest.json"
    manifest_hash = sha256_text(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO zoning.import_batch
              (document_family, source_root, source_manifest_path, source_manifest_hash, importer_name, importer_version)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING import_batch_id
            """,
            (
                document_family(root),
                relpath(root),
                relpath(manifest_path) if manifest_path.exists() else None,
                manifest_hash,
                IMPORTER_NAME,
                IMPORTER_VERSION,
            ),
        )
        return int(cur.fetchone()[0])


def finish_batch(conn: psycopg.Connection, batch_id: int, status: str, diagnostics: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE zoning.import_batch
            SET completed_at = now(), status = %s, diagnostics = %s
            WHERE import_batch_id = %s
            """,
            (status, Jsonb(diagnostics), batch_id),
        )


def load_root(root: Path, dry_run: bool) -> dict[str, Any]:
    family = document_family(root)
    manifest_path = root / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    paths = source_files(root)
    if not paths:
        raise ValueError(f"no JSON source files under {relpath(root)}")

    all_records: list[Record] = []
    diagnostics: dict[str, Any] = {
        "source_files": len(paths),
        "review_flags": 0,
        "needs_review_confidence": 0,
        "records": {},
    }
    sample_payload = load_json(paths[0])
    doc_revision_key = f"{family}|{revision_label(root, manifest)}"
    for path in paths:
        payload = load_json(path)
        review_count, confidence_count = validate_payload(path, payload)
        diagnostics["review_flags"] += review_count
        diagnostics["needs_review_confidence"] += confidence_count
        records = collect_records(path, payload, family, doc_revision_key)
        all_records.extend(records)

    for record in all_records:
        diagnostics["records"][record.table] = diagnostics["records"].get(record.table, 0) + 1
    if dry_run:
        diagnostics["dry_run"] = True
        return diagnostics

    with psycopg.connect(database_url()) as conn:
        with conn.transaction():
            batch_id = create_batch(conn, root, manifest)
            document_revision_id = ensure_document_revision(conn, root, manifest, sample_payload, batch_id)
            id_maps: dict[str, dict[str, int]] = {}
            seen_keys = {record.natural_key for record in all_records}

            for record in all_records:
                previous = previous_active(conn, record.table, record.natural_key)
                if previous and previous[1] == record.content_hash:
                    id_maps.setdefault(record.table, {})[record.natural_key] = previous[0]
                    insert_event(conn, batch_id, record, "unchanged", previous[1], previous[0])
                    continue
                if previous:
                    supersede_previous(conn, record.table, previous[0])
                    status = "changed"
                    prior_hash = previous[1]
                else:
                    status = "added"
                    prior_hash = None
                new_id = insert_record(conn, record, batch_id, document_revision_id, id_maps)
                id_maps.setdefault(record.table, {})[record.natural_key] = new_id
                insert_event(conn, batch_id, record, status, prior_hash, new_id)

            mark_removed_records(conn, batch_id, family, seen_keys)
            diagnostics["batch_id"] = batch_id
            finish_batch(conn, batch_id, "completed", diagnostics)
    return diagnostics


def mark_removed_records(conn: psycopg.Connection, batch_id: int, family: str, seen_keys: set[str]) -> None:
    tables = [
        "source_file",
        "bylaw_part",
        "section",
        "clause",
        "definition",
        "source_unit",
        "raw_page",
        "raw_table",
        "raw_table_cell",
        "raw_map_reference",
        "structured_fact",
    ]
    for table in tables:
        id_col = f"{table}_id"
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {id_col}, natural_key, content_hash
                FROM zoning.{table}
                WHERE is_active AND natural_key LIKE %s
                """,
                (f"{family}|%",),
            )
            for record_id, natural_key, hash_value in cur.fetchall():
                if natural_key in seen_keys:
                    continue
                cur.execute(f"UPDATE zoning.{table} SET is_active = false WHERE {id_col} = %s", (record_id,))
                cur.execute(
                    """
                    INSERT INTO zoning.import_record_event
                      (import_batch_id, record_family, natural_key, prior_content_hash, content_hash,
                       change_status, active_record_table, active_record_id)
                    VALUES (%s, %s, %s, %s, NULL, 'removed', %s, %s)
                    """,
                    (batch_id, table, natural_key, hash_value, table, record_id),
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Charlottetown current and draft zoning JSON into zoning schema.")
    parser.add_argument("--family", choices=("current", "draft", "both"), default="both")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count records without database writes.")
    args = parser.parse_args()

    roots = []
    if args.family in ("current", "both"):
        roots.append(CURRENT_ROOT)
    if args.family in ("draft", "both"):
        roots.append(DRAFT_ROOT)

    try:
        summaries = {document_family(root): load_root(root, args.dry_run) for root in roots}
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

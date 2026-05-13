from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEETING_ROOT = REPO_ROOT / "data" / "council-meetings" / "charlottetown" / "2026-05-12-regular-council"
IMPORTER_NAME = "scripts/import-council-meeting.py"
IMPORTER_VERSION = "1"


@dataclass(frozen=True)
class StoredRecord:
    table: str
    record_id: int
    natural_key: str
    content_hash: str
    status: str


def database_url(port_override: str | None = None) -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = port_override or os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}?connect_timeout=2"


def connect_database() -> psycopg.Connection:
    if os.environ.get("PGPORT"):
        return psycopg.connect(database_url())
    first_error: Exception | None = None
    for port in ("54329", "55432"):
        try:
            return psycopg.connect(database_url(port))
        except Exception as exc:
            first_error = first_error or exc
    raise first_error or RuntimeError("Could not connect to PostgreSQL")


def relpath(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relpath(path)} is not a JSON object")
    return payload


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
      for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def content_hash(payload: dict[str, Any]) -> str:
    return sha256_text(stable_json(payload))


def norm_key(value: str | None) -> str:
    if not value:
        return "unknown"
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "unknown"


def slug(value: str | None) -> str:
    return norm_key(value).replace("_", "-")


def compact(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def table_id_column(table: str) -> str:
    return f"{table}_id"


def create_batch(conn: psycopg.Connection, root: Path, manifest_hash: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO council.import_batch
              (document_family, source_root, source_manifest_path, source_manifest_hash, importer_name, importer_version)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING import_batch_id
            """,
            (
                "council_meeting",
                relpath(root),
                relpath(root / "meeting.json"),
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
            UPDATE council.import_batch
               SET completed_at = now(), status = %s, diagnostics = %s
             WHERE import_batch_id = %s
            """,
            (status, Jsonb(diagnostics), batch_id),
        )


def previous_active(conn: psycopg.Connection, table: str, natural_key: str) -> tuple[int, str] | None:
    id_column = table_id_column(table)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {id_column}, content_hash FROM council.{table} WHERE natural_key = %s AND is_active",
            (natural_key,),
        )
        row = cur.fetchone()
    return (int(row[0]), str(row[1])) if row else None


def record_event(
    conn: psycopg.Connection,
    batch_id: int,
    family: str,
    natural_key: str,
    prior_hash: str | None,
    new_hash: str | None,
    status: str,
    table: str | None,
    record_id: int | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO council.import_record_event
              (import_batch_id, record_family, natural_key, prior_content_hash, content_hash,
               change_status, active_record_table, active_record_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (batch_id, family, natural_key, prior_hash, new_hash, status, table, record_id),
        )


def insert_row(
    conn: psycopg.Connection,
    table: str,
    payload: dict[str, Any],
    natural_key: str,
    row_hash: str,
) -> int:
    data = dict(payload)
    data["natural_key"] = natural_key
    data["content_hash"] = row_hash
    columns = list(data.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    id_column = table_id_column(table)
    values = [Jsonb(value) if isinstance(value, (dict, list)) else value for value in data.values()]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO council.{table} ({", ".join(columns)})
            VALUES ({placeholders})
            RETURNING {id_column}
            """,
            values,
        )
        return int(cur.fetchone()[0])


def store_record(
    conn: psycopg.Connection,
    batch_id: int,
    table: str,
    family: str,
    natural_key: str,
    payload: dict[str, Any],
) -> StoredRecord:
    row_hash = content_hash({"table": table, "payload": payload})
    existing = previous_active(conn, table, natural_key)
    if existing and existing[1] == row_hash:
        record_event(conn, batch_id, family, natural_key, existing[1], row_hash, "unchanged", table, existing[0])
        return StoredRecord(table, existing[0], natural_key, row_hash, "unchanged")

    if existing:
        id_column = table_id_column(table)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE council.{table} SET is_active = false WHERE {id_column} = %s",
                (existing[0],),
            )
        record_id = insert_row(conn, table, payload, natural_key, row_hash)
        id_column = table_id_column(table)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE council.{table} SET superseded_by_id = %s WHERE {id_column} = %s",
                (record_id, existing[0]),
            )
        status = "changed"
        prior_hash = existing[1]
    else:
        record_id = insert_row(conn, table, payload, natural_key, row_hash)
        status = "added"
        prior_hash = None
    record_event(conn, batch_id, family, natural_key, prior_hash, row_hash, status, table, record_id)
    return StoredRecord(table, record_id, natural_key, row_hash, status)


def mark_removed(conn: psycopg.Connection, batch_id: int, table: str, family: str, seen: set[str]) -> int:
    id_column = table_id_column(table)
    removed = 0
    with conn.cursor() as cur:
        cur.execute(f"SELECT {id_column}, natural_key, content_hash FROM council.{table} WHERE is_active")
        for record_id, natural_key, row_hash in cur.fetchall():
            if natural_key in seen:
                continue
            cur.execute(
                f"UPDATE council.{table} SET is_active = false WHERE {id_column} = %s",
                (record_id,),
            )
            record_event(conn, batch_id, family, natural_key, row_hash, None, "removed", table, int(record_id))
            removed += 1
    return removed


def apply_schema(conn: psycopg.Connection) -> None:
    schema_path = REPO_ROOT / "schema" / "sql" / "council.sql"
    with conn.cursor() as cur:
        cur.execute(schema_path.read_text(encoding="utf-8"))


def api_payload(root: Path, meeting_payload: dict[str, Any], agenda: dict[str, Any], toc: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": relpath(root / "meeting.json"),
        "agendaSource": relpath(root / "agenda.json"),
        "tocSource": relpath(root / "toc.json"),
        "meeting": meeting_payload["meeting"],
        "sourceDocuments": meeting_payload["source_documents"],
        "agendaDocuments": agenda.get("agenda_documents", []),
        "packageDocuments": toc.get("documents", []),
        "documentStructureStandards": toc.get("document_structure_standards", []),
        "pageReproductionOptions": toc.get("page_reproduction_options", []),
        "agendaSections": meeting_payload.get("agenda_sections", []),
        "committeeReports": meeting_payload.get("committee_reports", []),
        "resolutions": meeting_payload.get("resolutions", []),
        "bylawReadings": meeting_payload.get("bylaw_readings", []),
        "planningItems": meeting_payload.get("planning_items", []),
        "audienceWorkflows": meeting_payload.get("audience_workflows", []),
        "reviewFlags": meeting_payload.get("review_flags", []),
    }


def citation_pages(citation: dict[str, Any]) -> tuple[int | None, int | None]:
    start = citation.get("pdf_page_start")
    end = citation.get("pdf_page_end")
    return (int(start) if isinstance(start, int) else None, int(end) if isinstance(end, int) else None)


def store_citations(
    conn: psycopg.Connection,
    batch_id: int,
    source_docs: dict[str, StoredRecord],
    source_pages: dict[tuple[str, int], StoredRecord],
    cited_table: str,
    cited_id: int,
    parent_key: str,
    citations: list[dict[str, Any]],
    seen: set[str],
) -> None:
    for index, citation in enumerate(citations):
        source_key = citation.get("source_document_id")
        source_doc = source_docs.get(str(source_key))
        if not source_doc:
            continue
        page_start, page_end = citation_pages(citation)
        source_page = source_pages.get((str(source_key), page_start)) if page_start else None
        natural = f"council:source_citation:{parent_key}:{index + 1}"
        payload = {
            "source_document_id": source_doc.record_id,
            "source_page_id": source_page.record_id if source_page else None,
            "cited_table": cited_table,
            "cited_id": cited_id,
            "citation_label": citation.get("citation_label"),
            "page_start": page_start,
            "page_end": page_end,
            "text_excerpt": citation.get("text_excerpt"),
            "bbox": citation.get("bbox"),
            "metadata": {"source_payload": citation},
        }
        store_record(conn, batch_id, "source_citation", "source_citation", natural, payload)
        seen.add(natural)


def all_people_from_text(values: list[str | None]) -> list[str]:
    names: list[str] = []
    for value in values:
        text = compact(value)
        if not text:
            continue
        text = re.sub(r"^(Mayor|Deputy Mayor|Councillor)\s+", "", text).strip()
        if text and text not in names:
            names.append(text)
    return names


def import_meeting(root: Path, apply_schema_first: bool = False) -> dict[str, int]:
    meeting_payload = load_json(root / "meeting.json")
    agenda = load_json(root / "agenda.json")
    toc = load_json(root / "toc.json")
    manifest_hash = content_hash({
        "meeting": meeting_payload,
        "agenda": agenda,
        "toc": toc,
    })
    api = api_payload(root, meeting_payload, agenda, toc)
    seen: dict[str, set[str]] = {}

    def track(table: str, record: StoredRecord) -> StoredRecord:
        seen.setdefault(table, set()).add(record.natural_key)
        return record

    with connect_database() as conn:
        if apply_schema_first:
            apply_schema(conn)
        batch_id = create_batch(conn, root, manifest_hash)
        diagnostics: dict[str, int] = {}
        try:
            meeting = meeting_payload["meeting"]
            jurisdiction_key = norm_key(meeting.get("jurisdiction"))
            jurisdiction = track("jurisdiction", store_record(conn, batch_id, "jurisdiction", "jurisdiction", f"council:jurisdiction:{jurisdiction_key}", {
                "jurisdiction_key": jurisdiction_key,
                "name_raw": meeting["jurisdiction"],
                "jurisdiction_type": "municipality",
                "province": "Prince Edward Island",
                "country": "Canada",
                "metadata": {},
            }))

            body_key = norm_key(meeting.get("body"))
            council_body = track("body", store_record(conn, batch_id, "body", "body", f"council:body:{jurisdiction_key}:{body_key}", {
                "jurisdiction_id": jurisdiction.record_id,
                "parent_body_id": None,
                "body_key": body_key,
                "body_type": "council",
                "name_raw": meeting["body"],
                "slug": slug(meeting["body"]),
                "description": None,
                "website_url": None,
                "start_date": None,
                "end_date": None,
                "metadata": {},
            }))

            source_docs: dict[str, StoredRecord] = {}
            for doc in meeting_payload.get("source_documents", []):
                doc_path = REPO_ROOT / doc["repo_relpath"]
                source_hash = doc.get("sha256") or (file_sha256(doc_path) if doc_path.exists() else "")
                natural = f"council:source_document:{jurisdiction_key}:{doc['source_document_id']}:{source_hash}"
                record = track("source_document", store_record(conn, batch_id, "source_document", "source_document", natural, {
                    "jurisdiction_id": jurisdiction.record_id,
                    "import_batch_id": None,
                    "source_document_key": doc["source_document_id"],
                    "document_type": doc["document_type"],
                    "title_raw": doc.get("title_raw") or doc.get("document_type"),
                    "repo_relpath": doc["repo_relpath"],
                    "source_url": None,
                    "mime_type": "application/pdf",
                    "page_count": doc.get("page_count"),
                    "source_file_hash": source_hash,
                    "published_date": meeting.get("date"),
                    "metadata": {"source_payload": doc},
                }))
                source_docs[doc["source_document_id"]] = record

            source_pages: dict[tuple[str, int], StoredRecord] = {}
            raw_root = root / "raw-pages"
            for doc in meeting_payload.get("source_documents", []):
                source_doc = source_docs[doc["source_document_id"]]
                for page in range(1, int(doc.get("page_count") or 0) + 1):
                    raw_path = raw_root / f"{doc['source_document_id']}-page-{page:03d}.txt"
                    text = raw_path.read_text(encoding="utf-8") if raw_path.exists() else None
                    natural = f"council:source_page:{source_doc.natural_key}:{page}"
                    page_record = track("source_page", store_record(conn, batch_id, "source_page", "source_page", natural, {
                        "source_document_id": source_doc.record_id,
                        "page_number": page,
                        "page_label_raw": str(page),
                        "text_raw": text,
                        "width": None,
                        "height": None,
                        "metadata": {"raw_page_relpath": relpath(raw_path) if raw_path.exists() else None},
                    }))
                    source_pages[(doc["source_document_id"], page)] = page_record

            image_root = root / "page-images"
            if image_root.exists():
                for image_path in sorted(image_root.glob("*.png")):
                    match = re.match(r"(.+)-page-(\d+)\.png$", image_path.name)
                    if not match:
                        continue
                    doc_key = match.group(1)
                    page = int(match.group(2))
                    source_doc = source_docs.get(doc_key)
                    source_page = source_pages.get((doc_key, page))
                    if not source_doc:
                        continue
                    natural = f"council:source_asset:{source_doc.natural_key}:page_image:{page}"
                    track("source_asset", store_record(conn, batch_id, "source_asset", "source_asset", natural, {
                        "source_document_id": source_doc.record_id,
                        "source_page_id": source_page.record_id if source_page else None,
                        "asset_type": "page_image",
                        "repo_relpath": relpath(image_path),
                        "mime_type": "image/png",
                        "file_hash": file_sha256(image_path),
                        "width": None,
                        "height": None,
                        "metadata": {"page": page},
                    }))

            meeting_record = track("meeting", store_record(conn, batch_id, "meeting", "meeting", f"council:meeting:{meeting['meeting_id']}", {
                "jurisdiction_id": jurisdiction.record_id,
                "body_id": council_body.record_id,
                "meeting_key": meeting["meeting_id"],
                "meeting_type": meeting.get("meeting_type"),
                "title_raw": meeting["title"],
                "meeting_date": meeting["date"],
                "meeting_time_raw": meeting.get("time"),
                "starts_at": None,
                "ends_at": None,
                "location_raw": meeting.get("location"),
                "livestream_url": meeting.get("livestream_url"),
                "meeting_status": "scheduled",
                "focus": meeting.get("focus"),
                "metadata": {
                    "source_payload": meeting,
                    "api_payload": api,
                    "api_payload_hash": content_hash(api),
                },
            }))

            for doc_key, source_doc in source_docs.items():
                track("meeting_document", store_record(conn, batch_id, "meeting_document", "meeting_document", f"council:meeting_document:{meeting['meeting_id']}:{doc_key}", {
                    "meeting_id": meeting_record.record_id,
                    "source_document_id": source_doc.record_id,
                    "document_role": doc_key,
                    "source_order": 1 if doc_key == "agenda" else 2,
                    "metadata": {},
                }))

            people: dict[str, StoredRecord] = {}
            for name in all_people_from_text([report.get("chair") for report in meeting_payload.get("committee_reports", [])]):
                key = norm_key(name)
                people[key] = track("person", store_record(conn, batch_id, "person", "person", f"council:person:{jurisdiction_key}:{key}", {
                    "jurisdiction_id": jurisdiction.record_id,
                    "person_key": key,
                    "display_name_raw": name,
                    "sort_name": " ".join(reversed(name.split(" "))) if " " in name else name,
                    "slug": slug(name),
                    "given_name": name.split(" ")[0] if " " in name else None,
                    "family_name": name.split(" ")[-1] if " " in name else name,
                    "honorific_raw": None,
                    "email": None,
                    "phone": None,
                    "website_url": None,
                    "metadata": {"source": "committee_report_chair"},
                }))

            for person in people.values():
                track("route_target", store_record(conn, batch_id, "route_target", "route_target", f"council:route_target:elected-official:{person.natural_key}", {
                    "route_name": "elected-official",
                    "path_template": "/elected-official/:slug",
                    "entity_table": "person",
                    "entity_id": person.record_id,
                    "slug": person.natural_key.rsplit(":", 1)[-1].replace("_", "-"),
                    "metadata": {},
                }))

            body_by_name: dict[str, StoredRecord] = {"Council": council_body}
            for report in meeting_payload.get("committee_reports", []):
                name = report["committee_name"]
                key = norm_key(name)
                body = track("body", store_record(conn, batch_id, "body", "body", f"council:body:{jurisdiction_key}:{key}", {
                    "jurisdiction_id": jurisdiction.record_id,
                    "parent_body_id": council_body.record_id,
                    "body_key": key,
                    "body_type": "committee",
                    "name_raw": name,
                    "slug": slug(name),
                    "description": None,
                    "website_url": None,
                    "start_date": None,
                    "end_date": None,
                    "metadata": {"source_payload": report},
                }))
                body_by_name[name] = body
                chair_name = compact(report.get("chair"))
                person = people.get(norm_key(chair_name)) if chair_name else None
                if person:
                    membership_key = f"council:body_membership:{body.natural_key}:{person.natural_key}:chair"
                    track("body_membership", store_record(conn, batch_id, "body_membership", "body_membership", membership_key, {
                        "body_id": body.record_id,
                        "person_id": person.record_id,
                        "office_term_id": None,
                        "role_raw": report.get("chair"),
                        "role_key": "chair",
                        "membership_type": "chair",
                        "start_date": None,
                        "end_date": None,
                        "voting_member": None,
                        "metadata": {"source": "committee_report"},
                    }))

            for index, section in enumerate(meeting_payload.get("agenda_sections", []), start=1):
                natural = f"council:agenda_section:{meeting['meeting_id']}:{section['agenda_section_id']}"
                section_record = track("agenda_section", store_record(conn, batch_id, "agenda_section", "agenda_section", natural, {
                    "meeting_id": meeting_record.record_id,
                    "agenda_section_key": section["agenda_section_id"],
                    "parent_agenda_section_id": None,
                    "label_raw": section.get("label_raw"),
                    "title_raw": section.get("title_raw") or section["agenda_section_id"],
                    "summary": section.get("summary"),
                    "source_order": index,
                    "metadata": {"source_payload": section},
                }))
                store_citations(conn, batch_id, source_docs, source_pages, "agenda_section", section_record.record_id, natural, section.get("citations", []), seen.setdefault("source_citation", set()))

            agenda_section_lookup: dict[str, int] = {}
            with conn.cursor() as cur:
                cur.execute("SELECT agenda_section_id, agenda_section_key FROM council.agenda_section WHERE meeting_id = %s AND is_active", (meeting_record.record_id,))
                agenda_section_lookup = {str(row[1]): int(row[0]) for row in cur.fetchall()}

            def store_business_item(item: dict[str, Any], item_key: str, item_type: str, section_id: int | None, source_order: int) -> tuple[StoredRecord, StoredRecord]:
                title = item.get("title") or item.get("title_raw") or item_key
                business = track("business_item", store_record(conn, batch_id, "business_item", "business_item", f"council:business_item:{jurisdiction_key}:{item_key}", {
                    "jurisdiction_id": jurisdiction.record_id,
                    "lead_body_id": council_body.record_id,
                    "business_item_key": item_key,
                    "business_item_type": item_type,
                    "title_raw": title,
                    "slug": slug(item_key),
                    "summary": item.get("public_summary") or item.get("summary"),
                    "current_stage": item.get("stage"),
                    "status": "active",
                    "opened_date": meeting["date"],
                    "closed_date": None,
                    "metadata": {"source_payload": item},
                }))
                agenda_item = track("agenda_item", store_record(conn, batch_id, "agenda_item", "agenda_item", f"council:agenda_item:{meeting['meeting_id']}:{item_key}", {
                    "meeting_id": meeting_record.record_id,
                    "agenda_section_id": section_id,
                    "business_item_id": business.record_id,
                    "agenda_item_key": item_key,
                    "item_number_raw": None,
                    "item_type": item_type,
                    "title_raw": title,
                    "description": item.get("public_summary") or item.get("summary"),
                    "decision_requested": item.get("decision_requested"),
                    "source_order": source_order,
                    "metadata": {"source_payload": item},
                }))
                track("business_item_event", store_record(conn, batch_id, "business_item_event", "business_item_event", f"council:business_item_event:{business.natural_key}:{meeting['meeting_id']}", {
                    "business_item_id": business.record_id,
                    "meeting_id": meeting_record.record_id,
                    "agenda_item_id": agenda_item.record_id,
                    "body_id": council_body.record_id,
                    "event_key": f"{item_key}:{meeting['meeting_id']}",
                    "event_type": item_type,
                    "event_stage": item.get("stage"),
                    "event_date": meeting["date"],
                    "title_raw": title,
                    "outcome": None,
                    "summary": item.get("decision_requested") or item.get("public_summary"),
                    "source_order": source_order,
                    "metadata": {"source_payload": item},
                }))
                for ref_index, reference in enumerate(item.get("property_references", []), start=1):
                    pids = reference.get("pids") or [None]
                    for pid_index, pid in enumerate(pids, start=1):
                        track("business_item_property", store_record(conn, batch_id, "business_item_property", "business_item_property", f"council:business_item_property:{business.natural_key}:{ref_index}:{pid_index}:{pid or 'none'}", {
                            "business_item_id": business.record_id,
                            "property_label_raw": reference.get("label") or reference.get("address") or (f"PID {pid}" if pid else "Unknown property"),
                            "address_raw": reference.get("address"),
                            "pid": pid,
                            "relationship_type": "subject_property",
                            "metadata": {"source_payload": reference},
                        }))
                amendment = item.get("zoning_amendment")
                if isinstance(amendment, dict):
                    track("business_item_zoning_amendment", store_record(conn, batch_id, "business_item_zoning_amendment", "business_item_zoning_amendment", f"council:business_item_zoning_amendment:{business.natural_key}", {
                        "business_item_id": business.record_id,
                        "bylaw_name_raw": amendment.get("bylaw_name"),
                        "bylaw_amendment_key": item_key,
                        "from_zone_raw": amendment.get("from_zone"),
                        "to_zone_raw": amendment.get("to_zone"),
                        "official_plan_amendment": amendment.get("official_plan_amendment"),
                        "future_land_use_change_raw": amendment.get("future_land_use_change"),
                        "metadata": {"source_payload": amendment},
                    }))
                track("route_target", store_record(conn, batch_id, "route_target", "route_target", f"council:route_target:council-business:{business.natural_key}", {
                    "route_name": "council-business",
                    "path_template": "/council-business/:slug",
                    "entity_table": "business_item",
                    "entity_id": business.record_id,
                    "slug": slug(item_key),
                    "metadata": {},
                }))
                store_citations(conn, batch_id, source_docs, source_pages, "agenda_item", agenda_item.record_id, agenda_item.natural_key, item.get("citations", []), seen.setdefault("source_citation", set()))
                return business, agenda_item

            source_order = 100
            for collection_name, item_type in (("resolutions", "resolution"), ("bylaw_readings", "bylaw_reading"), ("planning_items", "planning_item")):
                for item in meeting_payload.get(collection_name, []):
                    item_key = item.get("item_id") or item.get("planning_item_id")
                    if not item_key:
                        continue
                    source_order += 1
                    store_business_item(item, item_key, item_type, agenda_section_lookup.get(item.get("agenda_section_id")), source_order)

            for index, report in enumerate(meeting_payload.get("committee_reports", []), start=1):
                item_key = report["committee_report_id"]
                body = body_by_name.get(report["committee_name"], council_body)
                agenda_item = track("agenda_item", store_record(conn, batch_id, "agenda_item", "agenda_item", f"council:agenda_item:{meeting['meeting_id']}:{item_key}", {
                    "meeting_id": meeting_record.record_id,
                    "agenda_section_id": None,
                    "business_item_id": None,
                    "agenda_item_key": item_key,
                    "item_number_raw": None,
                    "item_type": "committee_report",
                    "title_raw": report["committee_name"],
                    "description": report.get("summary"),
                    "decision_requested": None,
                    "source_order": 50 + index,
                    "metadata": {"source_payload": report, "body_id": body.record_id},
                }))
                store_citations(conn, batch_id, source_docs, source_pages, "agenda_item", agenda_item.record_id, agenda_item.natural_key, report.get("citations", []), seen.setdefault("source_citation", set()))

            for table in (
                "source_citation", "business_item_zoning_amendment", "business_item_property",
                "business_item_event", "agenda_item", "business_item", "agenda_section",
                "meeting_document", "meeting", "body_membership", "office_term", "person",
                "body", "source_asset", "source_page", "source_document", "jurisdiction",
            ):
                diagnostics[f"{table}_removed"] = mark_removed(conn, batch_id, table, table, seen.get(table, set()))
            for table, keys in seen.items():
                diagnostics[f"{table}_seen"] = len(keys)
            finish_batch(conn, batch_id, "completed", diagnostics)
            conn.commit()
            return diagnostics
        except Exception as exc:
            finish_batch(conn, batch_id, "failed", {"error": str(exc)})
            conn.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Import council meeting JSON into the council schema.")
    parser.add_argument("--meeting-root", type=Path, default=DEFAULT_MEETING_ROOT)
    parser.add_argument("--apply-schema", action="store_true", help="Apply schema/sql/council.sql before import.")
    args = parser.parse_args()
    diagnostics = import_meeting(args.meeting_root.resolve(), apply_schema_first=args.apply_schema)
    print(json.dumps(diagnostics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


IMPORTER_NAME = "seed-help-context"
IMPORTER_VERSION = "1"
PUBLIC_FILTER = "audience = 'public' AND status = 'active' AND review_status = 'release_ready'"


@dataclass
class UpsertResult:
    status: str
    table: str
    record_id: int
    prior_hash: str | None
    content_hash: str
    natural_key: str


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def normalize_key(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")


def payload_hash(record: dict[str, Any], *, exclude: set[str]) -> str:
    return stable_hash({key: value for key, value in record.items() if key not in exclude})


def start_batch(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO help.import_batch (
              source_root,
              importer_name,
              importer_version,
              status,
              diagnostics
            )
            VALUES (%s, %s, %s, 'running', '{}'::jsonb)
            RETURNING import_batch_id
            """,
            ("database", IMPORTER_NAME, IMPORTER_VERSION),
        )
        return int(cur.fetchone()[0])


def finish_batch(conn: psycopg.Connection, batch_id: int, status: str, diagnostics: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE help.import_batch
            SET completed_at = now(),
                status = %s,
                diagnostics = %s::jsonb
            WHERE import_batch_id = %s
            """,
            (status, json.dumps(diagnostics, sort_keys=True), batch_id),
        )


def record_event(conn: psycopg.Connection, batch_id: int, result: UpsertResult) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO help.import_record_event (
              import_batch_id,
              record_family,
              natural_key,
              prior_content_hash,
              content_hash,
              change_status,
              active_record_table,
              active_record_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                batch_id,
                result.table,
                result.natural_key,
                result.prior_hash,
                result.content_hash,
                result.status,
                result.table,
                result.record_id,
            ),
        )


def retire_missing(
    conn: psycopg.Connection,
    *,
    batch_id: int,
    table: str,
    id_column: str,
    natural_key_prefix: str,
    keep_natural_keys: set[str],
) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {id_column}, natural_key, content_hash
            FROM {table}
            WHERE is_active
              AND natural_key LIKE %s
            """,
            (f"{natural_key_prefix}%",),
        )
        rows = cur.fetchall()
        retired = 0
        for row in rows:
            if row["natural_key"] in keep_natural_keys:
                continue
            cur.execute(
                f"UPDATE {table} SET is_active = false WHERE {id_column} = %s",
                (row[id_column],),
            )
            record_event(conn, batch_id, UpsertResult(
                "removed",
                table,
                int(row[id_column]),
                str(row["content_hash"]),
                str(row["content_hash"]),
                str(row["natural_key"]),
            ))
            retired += 1
        return retired


def upsert_row(
    conn: psycopg.Connection,
    *,
    table: str,
    id_column: str,
    record: dict[str, Any],
    batch_id: int,
    hash_exclude: set[str],
) -> UpsertResult:
    natural_key = record["natural_key"]
    content_hash = payload_hash(record, exclude=hash_exclude)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {id_column}, content_hash FROM {table} WHERE natural_key = %s AND is_active",
            (natural_key,),
        )
        prior = cur.fetchone()
        if prior and prior["content_hash"] == content_hash:
            return UpsertResult("unchanged", table, int(prior[id_column]), str(prior["content_hash"]), content_hash, natural_key)
        if prior:
            cur.execute(
                f"UPDATE {table} SET is_active = false WHERE {id_column} = %s",
                (prior[id_column],),
            )

        insert_record = {
            **record,
            "content_hash": content_hash,
            "created_import_batch_id": batch_id,
        }
        columns = list(insert_record)
        placeholders = ", ".join(["%s"] * len(columns))
        cur.execute(
            f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({placeholders})
            RETURNING {id_column}
            """,
            [json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for value in insert_record.values()],
        )
        record_id = int(cur.fetchone()[id_column])
        if prior:
            cur.execute(
                f"UPDATE {table} SET superseded_by_id = %s WHERE {id_column} = %s",
                (record_id, prior[id_column]),
            )
        return UpsertResult("changed" if prior else "added", table, record_id, prior["content_hash"] if prior else None, content_hash, natural_key)


def upsert_code_table(conn: psycopg.Connection, batch_id: int, record: dict[str, Any]) -> int:
    result = upsert_row(
        conn,
        table="help.code_table",
        id_column="code_table_id",
        record=record,
        batch_id=batch_id,
        hash_exclude={"content_hash", "created_import_batch_id"},
    )
    record_event(conn, batch_id, result)
    return result.record_id


def active_code_table_id(conn: psycopg.Connection, table_key: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT code_table_id FROM help.code_table WHERE table_key = %s AND is_active",
            (table_key,),
        )
        return int(cur.fetchone()[0])


def upsert_term(conn: psycopg.Connection, batch_id: int, record: dict[str, Any]) -> int:
    result = upsert_row(
        conn,
        table="help.term",
        id_column="term_id",
        record=record,
        batch_id=batch_id,
        hash_exclude={"content_hash", "created_import_batch_id"},
    )
    record_event(conn, batch_id, result)
    return result.record_id


def upsert_code_value(conn: psycopg.Connection, batch_id: int, record: dict[str, Any]) -> int:
    result = upsert_row(
        conn,
        table="help.code_value",
        id_column="code_value_id",
        record=record,
        batch_id=batch_id,
        hash_exclude={"content_hash", "created_import_batch_id"},
    )
    record_event(conn, batch_id, result)
    return result.record_id


def upsert_context_binding(conn: psycopg.Connection, batch_id: int, record: dict[str, Any]) -> int:
    result = upsert_row(
        conn,
        table="help.context_binding",
        id_column="context_binding_id",
        record=record,
        batch_id=batch_id,
        hash_exclude={"content_hash", "created_import_batch_id"},
    )
    record_event(conn, batch_id, result)
    return result.record_id


def seed_static_code_tables(conn: psycopg.Connection, batch_id: int) -> dict[str, int]:
    tables = [
        {
            "table_key": "zoning.section_topic",
            "display_label": "Zoning section topics",
            "description": "Topic categories assigned to zoning bylaw sections.",
            "source_schema": "zoning",
            "source_table": "section_topic",
        },
        {
            "table_key": "zoning.zone_code_crosswalk",
            "display_label": "Zone code crosswalks",
            "description": "Source-to-target zone code mappings used when source maps and bylaws use different labels.",
            "source_schema": "zoning",
            "source_table": "zone_code_crosswalk",
        },
        {
            "table_key": "council.business_item.status",
            "display_label": "Business item statuses",
            "description": "Lifecycle statuses for municipal business items.",
            "source_schema": "council",
            "source_table": "business_item",
        },
        {
            "table_key": "council.meeting.status",
            "display_label": "Meeting statuses",
            "description": "Lifecycle statuses for council and committee meetings.",
            "source_schema": "council",
            "source_table": "meeting",
        },
        {
            "table_key": "council.vote_member.position",
            "display_label": "Vote member positions",
            "description": "Recorded positions for members in a vote.",
            "source_schema": "council",
            "source_table": "vote_member",
        },
    ]
    ids: dict[str, int] = {}
    for table in tables:
        record = {
            **table,
            "audience": "public",
            "status": "active",
            "review_status": "release_ready",
            "citations": {"source": f"{table['source_schema']}.{table['source_table']}"},
            "metadata": {},
            "natural_key": f"help.code_table|{table['table_key']}",
        }
        upsert_code_table(conn, batch_id, record)
        ids[table["table_key"]] = active_code_table_id(conn, table["table_key"])
    return ids


def seed_zoning_definitions(conn: psycopg.Connection, batch_id: int) -> list[int]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (term_key)
              definition_id, term_key, term_raw, definition_text_raw, citations
            FROM zoning.definition
            WHERE is_active
            ORDER BY term_key, definition_id DESC
            LIMIT 25
            """
        )
        rows = cur.fetchall()
    ids = []
    keep_keys = set()
    for row in rows:
        key = f"zoning.definition.{row['term_key']}"
        natural_key = f"help.term|{key}"
        keep_keys.add(natural_key)
        ids.append(upsert_term(conn, batch_id, {
            "term_key": key,
            "term_type": "business",
            "display_label": row["term_raw"],
            "raw_label": row["term_raw"],
            "short_help": row["definition_text_raw"][:280],
            "long_help": row["definition_text_raw"],
            "audience": "public",
            "status": "active",
            "review_status": "release_ready",
            "source_schema": "zoning",
            "source_table": "definition",
            "source_id": str(row["definition_id"]),
            "citations": row["citations"] or {},
            "metadata": {},
            "natural_key": natural_key,
        }))
    retire_missing(
        conn,
        batch_id=batch_id,
        table="help.term",
        id_column="term_id",
        natural_key_prefix="help.term|zoning.definition.",
        keep_natural_keys=keep_keys,
    )
    return ids


def seed_section_topics(conn: psycopg.Connection, batch_id: int, code_table_id: int) -> list[int]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT topic_key, topic_label, description, status
            FROM zoning.section_topic
            ORDER BY topic_key
            """
        )
        rows = cur.fetchall()
    ids = []
    for index, row in enumerate(rows):
        ids.append(upsert_code_value(conn, batch_id, {
            "code_table_id": code_table_id,
            "value_key": row["topic_key"],
            "raw_value": row["topic_key"],
            "display_label": row["topic_label"],
            "description": row["description"],
            "sort_order": index + 1,
            "audience": "public",
            "status": row["status"] if row["status"] in ("active", "deprecated", "retired") else "active",
            "review_status": "release_ready",
            "source_schema": "zoning",
            "source_table": "section_topic",
            "source_id": row["topic_key"],
            "citations": {"source": "zoning.section_topic"},
            "metadata": {},
            "natural_key": f"help.code_value|zoning.section_topic|{row['topic_key']}",
        }))
    return ids


def seed_zone_crosswalks(conn: psycopg.Connection, batch_id: int, code_table_id: int) -> list[int]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT zone_code_crosswalk_id, context, source_code, target_code, reason, status
            FROM zoning.zone_code_crosswalk
            ORDER BY context, source_code, target_code
            LIMIT 100
            """
        )
        rows = cur.fetchall()
    ids = []
    for index, row in enumerate(rows):
        value_key = f"{row['context']}:{row['source_code']}:{row['target_code']}"
        ids.append(upsert_code_value(conn, batch_id, {
            "code_table_id": code_table_id,
            "value_key": value_key,
            "raw_value": row["source_code"],
            "display_label": f"{row['source_code']} -> {row['target_code']}",
            "description": row["reason"],
            "sort_order": index + 1,
            "audience": "public",
            "status": row["status"] if row["status"] in ("active", "deprecated", "retired") else "active",
            "review_status": "release_ready",
            "source_schema": "zoning",
            "source_table": "zone_code_crosswalk",
            "source_id": str(row["zone_code_crosswalk_id"]),
            "citations": {"source": "zoning.zone_code_crosswalk", "context": row["context"]},
            "metadata": {"context": row["context"], "target_code": row["target_code"]},
            "natural_key": f"help.code_value|zoning.zone_code_crosswalk|{value_key}",
        }))
    return ids


def seed_static_status_values(conn: psycopg.Connection, batch_id: int, code_table_ids: dict[str, int]) -> list[int]:
    values = {
        "council.business_item.status": ["active", "scheduled", "deferred", "adopted", "defeated", "withdrawn", "closed", "superseded", "unknown"],
        "council.meeting.status": ["scheduled", "completed", "cancelled", "postponed", "unknown"],
        "council.vote_member.position": ["for", "against", "abstain", "absent", "conflict", "unknown"],
    }
    ids = []
    for table_key, table_values in values.items():
        for index, raw in enumerate(table_values):
            ids.append(upsert_code_value(conn, batch_id, {
                "code_table_id": code_table_ids[table_key],
                "value_key": raw,
                "raw_value": raw,
                "display_label": raw.replace("_", " ").title(),
                "description": f"`{raw}` value used by {table_key}.",
                "sort_order": index + 1,
                "audience": "public",
                "status": "active",
                "review_status": "release_ready",
                "source_schema": "council",
                "source_table": table_key.split(".")[1],
                "source_id": raw,
                "citations": {"source": table_key},
                "metadata": {},
                "natural_key": f"help.code_value|{table_key}|{raw}",
            }))
    return ids


def seed_context_bindings(conn: psycopg.Connection, batch_id: int) -> list[int]:
    ids = []
    keep_keys = set()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT term_id, term_key
            FROM help.term
            WHERE is_active
              AND term_key LIKE 'zoning.definition.%'
            ORDER BY term_key
            LIMIT 10
            """
        )
        terms = cur.fetchall()
        cur.execute(
            """
            SELECT cv.code_value_id, ct.table_key, cv.value_key
            FROM help.code_value cv
            JOIN help.code_table ct ON ct.code_table_id = cv.code_table_id
            WHERE cv.is_active
              AND ct.is_active
              AND ct.table_key = 'zoning.section_topic'
            ORDER BY cv.sort_order, cv.value_key
            """
        )
        values = cur.fetchall()
    order = 1
    for row in terms:
        natural_key = f"help.context_binding|route:/zoning-comparison|term|{row['term_key']}"
        keep_keys.add(natural_key)
        ids.append(upsert_context_binding(conn, batch_id, {
            "context_key": "route:/zoning-comparison",
            "context_type": "route",
            "term_id": row["term_id"],
            "code_value_id": None,
            "display_order": order,
            "help_variant": "default",
            "audience": "public",
            "status": "active",
            "review_status": "release_ready",
            "metadata": {},
            "natural_key": natural_key,
        }))
        order += 1
    for row in values:
        natural_key = f"help.context_binding|route:/zoning-comparison|code_value|{row['table_key']}|{row['value_key']}"
        keep_keys.add(natural_key)
        ids.append(upsert_context_binding(conn, batch_id, {
            "context_key": "route:/zoning-comparison",
            "context_type": "route",
            "term_id": None,
            "code_value_id": row["code_value_id"],
            "display_order": order,
            "help_variant": "default",
            "audience": "public",
            "status": "active",
            "review_status": "release_ready",
            "metadata": {},
            "natural_key": natural_key,
        }))
        order += 1
    retire_missing(
        conn,
        batch_id=batch_id,
        table="help.context_binding",
        id_column="context_binding_id",
        natural_key_prefix="help.context_binding|route:/zoning-comparison|",
        keep_natural_keys=keep_keys,
    )
    return ids


def main() -> int:
    with psycopg.connect(database_url()) as conn:
        batch_id = start_batch(conn)
        try:
            code_table_ids = seed_static_code_tables(conn, batch_id)
            term_ids = seed_zoning_definitions(conn, batch_id)
            section_topic_ids = seed_section_topics(conn, batch_id, code_table_ids["zoning.section_topic"])
            crosswalk_ids = seed_zone_crosswalks(conn, batch_id, code_table_ids["zoning.zone_code_crosswalk"])
            status_ids = seed_static_status_values(conn, batch_id, code_table_ids)
            binding_ids = seed_context_bindings(conn, batch_id)
            diagnostics = {
                "terms": len(term_ids),
                "section_topics": len(section_topic_ids),
                "zone_crosswalks": len(crosswalk_ids),
                "status_values": len(status_ids),
                "context_bindings": len(binding_ids),
            }
            finish_batch(conn, batch_id, "completed", diagnostics)
            conn.commit()
            print(json.dumps({"import_batch_id": batch_id, **diagnostics}, indent=2))
            return 0
        except Exception as exc:
            finish_batch(conn, batch_id, "failed", {"error": str(exc)})
            conn.commit()
            raise


if __name__ == "__main__":
    raise SystemExit(main())

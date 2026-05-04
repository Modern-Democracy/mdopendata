"""Apply curated override relationships to zoning.structured_fact.

Reads
data/zoning/charlottetown/manual-corrections/override-relationships.json and
inserts each entry as a `cross_references` fact in zoning.structured_fact,
using the same natural-key + content-hash discipline as the bylaw importer
(scripts/import-charlottetown-zoning.py). Re-running with no JSON changes is
a no-op.

The natural key for an override fact is the triple
(source_clause_ref, relationship_type, target_ref.source_ref_id) plus the
document_revision_id. If the JSON entry's content_hash does not match the
active row's content_hash, the active row is marked is_active=false and a
new active row is inserted with superseded_by_id pointing at it.

Usage
-----
    python scripts/apply-charlottetown-override-relationships.py
    python scripts/apply-charlottetown-override-relationships.py --dry-run
    python scripts/apply-charlottetown-override-relationships.py --in <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = (
    REPO_ROOT
    / "data"
    / "zoning"
    / "charlottetown"
    / "manual-corrections"
    / "override-relationships.json"
)
SUPPORTED_SCHEMA_VERSIONS = {1}
IMPORTER_NAME = "scripts/apply-charlottetown-override-relationships.py"
IMPORTER_VERSION = "1"
FACT_FAMILY = "cross_references"


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_artifact(path: Path) -> tuple[list[dict], dict]:
    if not path.exists():
        raise SystemExit(f"Override relationships file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SystemExit(
            f"Unsupported schema_version {schema_version!r}; supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    relationships = payload.get("relationships") or []
    if not isinstance(relationships, list):
        raise SystemExit("Malformed file: 'relationships' must be a list")
    seen: set[tuple] = set()
    for entry in relationships:
        for field in ("relationship_type", "target_ref", "document_family"):
            if not entry.get(field):
                raise SystemExit(f"Relationship missing required field {field!r}: {entry!r}")
        # Source anchor: exactly one of source_clause_ref / source_section_ref /
        # source_file_path. The first two are inherited from the original
        # schema; source_file_path is used for facts attached to a whole source
        # file (e.g. Appendix C, which is loaded as raw pages with no clauses).
        source_anchors = [
            field for field in ("source_clause_ref", "source_section_ref", "source_file_path")
            if entry.get(field)
        ]
        if len(source_anchors) != 1:
            raise SystemExit(
                f"Relationship must have exactly one of source_clause_ref / "
                f"source_section_ref / source_file_path; got {source_anchors}: {entry!r}"
            )
        target = entry["target_ref"]
        if "source_ref_type" not in target or "source_ref_id" not in target:
            raise SystemExit(f"target_ref must have source_ref_type and source_ref_id: {entry!r}")
        natural_key = (
            source_anchors[0],
            entry[source_anchors[0]],
            entry["relationship_type"],
            target["source_ref_type"],
            target["source_ref_id"],
            entry["document_family"],
        )
        if natural_key in seen:
            raise SystemExit(f"Duplicate relationship natural key: {natural_key}")
        seen.add(natural_key)
    return relationships, payload


def get_revision_map(conn: psycopg.Connection) -> dict[str, int]:
    """Map document_family ('current'/'draft') -> latest document_revision_id.

    document_revision is append-only, so the maximum id per bylaw_document is
    the most recent revision.
    """
    sql = """
    SELECT bd.document_family, MAX(dr.document_revision_id) AS revision_id
      FROM zoning.bylaw_document bd
      JOIN zoning.document_revision dr ON dr.bylaw_document_id = bd.bylaw_document_id
     GROUP BY bd.document_family
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = {row[0]: int(row[1]) for row in cur.fetchall()}
    return rows


def ensure_import_batch(conn: psycopg.Connection, document_family: str) -> int:
    sql = """
    INSERT INTO zoning.import_batch
      (document_family, source_root, importer_name, importer_version, status)
    VALUES (%s, %s, %s, %s, 'completed')
    RETURNING import_batch_id
    """
    source_root = "data/zoning/charlottetown/manual-corrections/override-relationships.json"
    with conn.cursor() as cur:
        cur.execute(sql, (document_family, source_root, IMPORTER_NAME, IMPORTER_VERSION))
        return int(cur.fetchone()[0])


def source_ref_for_entry(entry: dict) -> dict:
    """Resolve the entry's source anchor into a {source_ref_type, source_ref_id} pair."""
    if entry.get("source_clause_ref"):
        return {"source_ref_type": "clause", "source_ref_id": entry["source_clause_ref"]}
    if entry.get("source_section_ref"):
        return {"source_ref_type": "section", "source_ref_id": entry["source_section_ref"]}
    if entry.get("source_file_path"):
        return {"source_ref_type": "document", "source_ref_id": entry["source_file_path"]}
    raise SystemExit(f"Entry has no source anchor: {entry!r}")


def build_value_payload(entry: dict) -> dict:
    source_ref = source_ref_for_entry(entry)
    payload: dict[str, Any] = {
        "relationship_type": entry["relationship_type"],
        "source_ref": source_ref,
        "target_ref": dict(entry["target_ref"]),
    }
    if source_ref["source_ref_type"] == "clause":
        # Preserve the legacy field on clause-anchored entries so the
        # original 21 records' content_hash stays stable.
        payload["source_clause_ref"] = entry["source_clause_ref"]
    for optional in ("scope", "join_behavior", "confidence", "notes"):
        if entry.get(optional) is not None:
            payload[optional] = entry[optional]
    return payload


def natural_key(entry: dict, revision_id: int) -> str:
    target = entry["target_ref"]
    src_ref = source_ref_for_entry(entry)
    if src_ref["source_ref_type"] == "clause":
        # Legacy format: keep stable so previously-loaded clause-anchored
        # facts remain unchanged after the multi-anchor refactor.
        return (
            f"override|rev{revision_id}|{src_ref['source_ref_id']}|"
            f"{entry['relationship_type']}|{target['source_ref_type']}|{target['source_ref_id']}"
        )
    return (
        f"override|rev{revision_id}|{src_ref['source_ref_type']}:{src_ref['source_ref_id']}|"
        f"{entry['relationship_type']}|{target['source_ref_type']}:{target['source_ref_id']}"
    )


def upsert_fact(
    conn: psycopg.Connection,
    entry: dict,
    revision_id: int,
    import_batch_id: int,
    *,
    dry_run: bool,
) -> str:
    nat_key = natural_key(entry, revision_id)
    payload = build_value_payload(entry)
    content_hash = sha256_text(stable_json({"table": "structured_fact", "payload": payload}))

    with conn.cursor() as cur:
        # Resolve the source_file_id from the source anchor so the synthetic
        # cross-reference fact still has a NOT-NULL provenance link.
        if entry.get("source_clause_ref"):
            cur.execute(
                """
                SELECT source_file_id FROM zoning.clause
                 WHERE clause_source_id = %s AND document_revision_id = %s AND is_active
                 LIMIT 1
                """,
                (entry["source_clause_ref"], revision_id),
            )
            row = cur.fetchone()
            if not row:
                raise SystemExit(
                    f"Source clause not found: {entry['source_clause_ref']!r} "
                    f"in revision {revision_id}."
                )
            source_record_table, source_record_key = "clause", entry["source_clause_ref"]
        elif entry.get("source_section_ref"):
            cur.execute(
                """
                SELECT source_file_id FROM zoning.section
                 WHERE section_source_id = %s AND document_revision_id = %s AND is_active
                 LIMIT 1
                """,
                (entry["source_section_ref"], revision_id),
            )
            row = cur.fetchone()
            if not row:
                raise SystemExit(
                    f"Source section not found: {entry['source_section_ref']!r} "
                    f"in revision {revision_id}."
                )
            source_record_table, source_record_key = "section", entry["source_section_ref"]
        else:  # source_file_path
            cur.execute(
                """
                SELECT source_file_id FROM zoning.source_file
                 WHERE repo_relpath = %s AND document_revision_id = %s AND is_active
                 LIMIT 1
                """,
                (entry["source_file_path"], revision_id),
            )
            row = cur.fetchone()
            if not row:
                raise SystemExit(
                    f"Source file not found: {entry['source_file_path']!r} "
                    f"in revision {revision_id}."
                )
            source_record_table, source_record_key = "source_file", entry["source_file_path"]
        source_file_id = int(row[0])

        cur.execute(
            """
            SELECT structured_fact_id, content_hash
              FROM zoning.structured_fact
             WHERE natural_key = %s AND is_active
             LIMIT 1
            """,
            (nat_key,),
        )
        existing = cur.fetchone()

        if existing and existing[1] == content_hash:
            return "unchanged"

        if dry_run:
            return "would_update" if existing else "would_insert"

        if existing:
            prior_id = int(existing[0])
            cur.execute(
                "UPDATE zoning.structured_fact SET is_active = false WHERE structured_fact_id = %s",
                (prior_id,),
            )
        else:
            prior_id = None

        cur.execute(
            """
            INSERT INTO zoning.structured_fact
              (document_revision_id, source_file_id, source_record_table, source_record_key,
               fact_family, fact_type, raw_label, raw_text, normalized_key,
               value_payload, citations, natural_key, content_hash, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, true)
            RETURNING structured_fact_id
            """,
            (
                revision_id,
                source_file_id,
                source_record_table,
                source_record_key,
                FACT_FAMILY,
                entry["relationship_type"],
                None,
                entry.get("scope"),
                None,
                Jsonb(payload),
                "{}",
                nat_key,
                content_hash,
            ),
        )
        new_id = int(cur.fetchone()[0])

        if prior_id is not None:
            cur.execute(
                "UPDATE zoning.structured_fact SET superseded_by_id = %s WHERE structured_fact_id = %s",
                (new_id, prior_id),
            )

        cur.execute(
            """
            INSERT INTO zoning.import_record_event
              (import_batch_id, record_family, natural_key,
               prior_content_hash, content_hash, change_status,
               active_record_table, active_record_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                import_batch_id,
                FACT_FAMILY,
                nat_key,
                existing[1] if existing else None,
                content_hash,
                "changed" if existing else "added",
                "structured_fact",
                new_id,
            ),
        )

        return "updated" if existing else "inserted"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_path", type=Path, default=DEFAULT_IN,
                        help=f"Input JSON path (default: {DEFAULT_IN.relative_to(REPO_ROOT).as_posix()})")
    parser.add_argument("--dry-run", action="store_true", help="Report planned changes without writing.")
    args = parser.parse_args()

    relationships, _payload = load_artifact(args.input_path)
    print(f"Loaded {len(relationships)} relationships from {args.input_path.relative_to(REPO_ROOT).as_posix()}")

    counts: dict[str, int] = {}
    with psycopg.connect(database_url()) as conn:
        revision_map = get_revision_map(conn)
        missing_families = sorted({r["document_family"] for r in relationships if r["document_family"] not in revision_map})
        if missing_families:
            raise SystemExit(f"No active document_revision found for families: {missing_families}")

        batch_ids: dict[str, int] = {}
        for entry in relationships:
            family = entry["document_family"]
            revision_id = revision_map[family]
            if args.dry_run:
                import_batch_id = -1
            else:
                if family not in batch_ids:
                    batch_ids[family] = ensure_import_batch(conn, family)
                import_batch_id = batch_ids[family]
            status = upsert_fact(conn, entry, revision_id, import_batch_id, dry_run=args.dry_run)
            counts[status] = counts.get(status, 0) + 1

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

    label_dry = "(dry-run, no changes written) " if args.dry_run else ""
    print(f"{label_dry}Outcome:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()

"""Promote per-PID Appendix C exemptions to `zoning.structured_fact`.

Reads `data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json`
(produced by `scripts/extract-charlottetown-appendix-c-exemptions.py`) and
inserts each entry as a `cross_references` fact with
`relationship_type='applies_to_parcel'` and a `target_ref` of
`{"source_ref_type": "external_source", "source_ref_id": "parcel:<pid>"}`,
following the same natural-key + content-hash discipline as
`scripts/apply-charlottetown-override-relationships.py`.

Re-runs are idempotent: rows whose payload is unchanged are skipped, rows
whose payload changed get superseded with a new active row, and rows
removed from the input are NOT pruned (use the curator workflow for
deliberate retraction).

By default only `confidence='high'` rows are promoted. Pass
`--include-needs-review` to promote everything; the resulting facts will
carry `confidence='needs_review'` in their `value_payload`.

The 14 coarse zone-level `applies_to_parcel` facts created by
`apply-charlottetown-override-relationships.py` are left in place per
backlog Task 3a Open Decision (keep for traceability with their own
`confidence='superseded'` flag managed by the curator).

Usage
-----
    python scripts/apply-charlottetown-appendix-c-exemptions.py
    python scripts/apply-charlottetown-appendix-c-exemptions.py --dry-run
    python scripts/apply-charlottetown-appendix-c-exemptions.py --include-needs-review
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
    REPO_ROOT / "data" / "zoning" / "charlottetown" / "manual-corrections"
    / "appendix-c-exemptions.json"
)
SOURCE_FILE_PATH = (
    "data/zoning/charlottetown/appendix-c-approved-site-specific-exemptions.json"
)
SUPPORTED_SCHEMA_VERSIONS = {1}
IMPORTER_NAME = "scripts/apply-charlottetown-appendix-c-exemptions.py"
IMPORTER_VERSION = "1"
FACT_FAMILY = "cross_references"
FACT_TYPE = "applies_to_parcel"


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


def load_artifact(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Appendix C exemptions file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SystemExit(
            f"Unsupported schema_version {schema_version!r}; supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    exemptions = payload.get("exemptions") or []
    if not isinstance(exemptions, list):
        raise SystemExit("Malformed file: 'exemptions' must be a list")
    return exemptions


def get_current_revision(conn: psycopg.Connection) -> tuple[int, int]:
    """Return (document_revision_id, source_file_id) for the current bylaw's
    latest revision and the Appendix C source_file row inside that revision.
    """
    sql = """
    WITH rev AS (
      SELECT dr.document_revision_id, bd.bylaw_document_id
        FROM zoning.document_revision dr
        JOIN zoning.bylaw_document bd USING (bylaw_document_id)
       WHERE bd.document_family = 'current'
       ORDER BY dr.document_revision_id DESC
       LIMIT 1
    )
    SELECT rev.document_revision_id, sf.source_file_id
      FROM rev
      JOIN zoning.source_file sf
        ON sf.document_revision_id = rev.document_revision_id
       AND sf.repo_relpath = %s
       AND sf.is_active
    """
    with conn.cursor() as cur:
        cur.execute(sql, (SOURCE_FILE_PATH,))
        row = cur.fetchone()
    if not row:
        raise SystemExit(
            f"No active source_file row for {SOURCE_FILE_PATH!r} in the current bylaw revision."
        )
    return int(row[0]), int(row[1])


def ensure_import_batch(conn: psycopg.Connection) -> int:
    sql = """
    INSERT INTO zoning.import_batch
      (document_family, source_root, importer_name, importer_version, status)
    VALUES ('current', %s, %s, %s, 'completed')
    RETURNING import_batch_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            "data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json",
            IMPORTER_NAME, IMPORTER_VERSION,
        ))
        return int(cur.fetchone()[0])


def natural_key(entry: dict[str, Any], revision_id: int) -> str:
    # Include source_page so multiple amendments for the same parcel
    # (e.g. PID 342790 / 199 Grafton Street has separate entries on pages
    # 3, 4, 6) remain distinct rather than overwriting each other.
    return (
        f"appendix_c_exemption|rev{revision_id}|"
        f"{entry['zone_code_at_amendment']}|parcel:{entry['pid']}|"
        f"page:{entry.get('source_page') or 0}"
    )


def build_value_payload(entry: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "relationship_type": FACT_TYPE,
        "source_ref": {
            "source_ref_type": "document",
            "source_ref_id": SOURCE_FILE_PATH,
        },
        "target_ref": {
            "source_ref_type": "external_source",
            "source_ref_id": f"parcel:{entry['pid']}",
        },
        "join_behavior": "override_target_values",
        "scope": (
            f"Appendix C site-specific exemption affecting parcel "
            f"{entry['pid']} ({entry.get('civic_address') or 'address unknown'}) "
            f"within the {entry['zone_code_at_amendment']} zone."
        ),
        "confidence": entry.get("confidence") or "needs_review",
        "appendix_c_row": {
            "zone_code_at_amendment": entry["zone_code_at_amendment"],
            "pid": entry["pid"],
            "civic_address": entry.get("civic_address"),
            "use_added_or_modified": entry.get("use_added_or_modified"),
            "regulation_override_text": entry.get("regulation_override_text"),
            "source_page": entry.get("source_page"),
        },
    }
    if entry.get("notes"):
        payload["notes"] = entry["notes"]
    return payload


def upsert_fact(
    conn: psycopg.Connection,
    entry: dict[str, Any],
    revision_id: int,
    source_file_id: int,
    import_batch_id: int,
    *,
    dry_run: bool,
) -> str:
    if not entry.get("pid"):
        return "skipped_no_pid"
    nat_key = natural_key(entry, revision_id)
    payload = build_value_payload(entry)
    content_hash = sha256_text(stable_json({"table": "structured_fact", "payload": payload}))

    with conn.cursor() as cur:
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
        prior_id = int(existing[0]) if existing else None
        if prior_id is not None:
            cur.execute(
                "UPDATE zoning.structured_fact SET is_active = false WHERE structured_fact_id = %s",
                (prior_id,),
            )
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
                "source_file",
                SOURCE_FILE_PATH,
                FACT_FAMILY,
                FACT_TYPE,
                None,
                payload["scope"],
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
    parser.add_argument("--include-needs-review", action="store_true",
                        help="Promote needs_review rows in addition to high-confidence ones.")
    args = parser.parse_args()

    exemptions = load_artifact(args.input_path)
    selected = [
        entry for entry in exemptions
        if entry.get("confidence") == "high" or args.include_needs_review
    ]
    print(
        f"Loaded {len(exemptions)} entries; promoting {len(selected)} "
        f"({'all confidences' if args.include_needs_review else 'high-confidence only'})."
    )

    counts: dict[str, int] = {}
    with psycopg.connect(database_url()) as conn:
        revision_id, source_file_id = get_current_revision(conn)
        import_batch_id = -1 if args.dry_run else ensure_import_batch(conn)
        for entry in selected:
            status = upsert_fact(conn, entry, revision_id, source_file_id, import_batch_id, dry_run=args.dry_run)
            counts[status] = counts.get(status, 0) + 1
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

    label = "(dry-run, no changes written) " if args.dry_run else ""
    print(f"{label}Outcome:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()

"""Per-revision population audit of the Charlottetown zoning data layer.

Computes structural gap metrics over `zoning.structured_fact`,
`zoning.clause`, `zoning.raw_table`, and friends, and writes one row per
non-zero `(scope, gap_type)` pair into `zoning.coverage_gap`. Rows the
audit creates are stamped `is_audit_generated=true` so the views in
`schema/sql/009_coverage_gap_views.sql` can roll them up.

The audit is idempotent: every run begins by deleting all
`is_audit_generated=true` rows for the revisions it touches, then
re-inserts the current truth. Manual gap rows (`is_audit_generated=false`)
are left alone.

A JSON snapshot is also written under
`data/zoning/charlottetown/audits/<UTC-timestamp>.json` for diffability
across runs.

Usage
-----
    python scripts/audit-charlottetown-population.py
    python scripts/audit-charlottetown-population.py --dry-run
    python scripts/audit-charlottetown-population.py --no-snapshot

The metrics computed here are documented in
`wiki/charlottetown/topics/zoning-data-layer-backlog.md` (Task 1).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = REPO_ROOT / "data" / "zoning" / "charlottetown" / "audits"

# Subset of override-pattern labels (from
# scripts/extract-charlottetown-override-candidates.py) whose presence in a
# clause's text is taken as evidence that an override edge SHOULD exist.
# Pattern labels intentionally NOT counted as gaps:
#   - accessory_use_template (already captured as `uses` facts),
#   - global_standalone / global_all_other / local_foregoing / except_as_provided
#     (no graph target by design).
RELATIONSHIP_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("section_or_clause_ref", re.compile(
        r"\bnotwithstanding\s+(section|sections|clause|clauses|part|parts)\s+\d",
        re.IGNORECASE)),
    ("numeric_ref", re.compile(r"\bnotwithstanding\s+\d+\.\d", re.IGNORECASE)),
    ("category_ref", re.compile(
        r"\bnotwithstanding\s+the\s+[a-z][a-zA-Z\s&,]+(requirements?|provisions?|"
        r"setbacks?|ratios?|height|frontage|area)\b",
        re.IGNORECASE)),
    ("does_not_apply_specific", re.compile(
        r"\b(does|shall)\s+not\s+apply\b", re.IGNORECASE)),
    ("supersedes", re.compile(r"\bsupersedes\b", re.IGNORECASE)),
]


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def revisions(conn: psycopg.Connection) -> list[tuple[int, int, str]]:
    sql = """
    SELECT dr.document_revision_id, bd.bylaw_document_id, bd.document_family
      FROM zoning.document_revision dr
      JOIN zoning.bylaw_document bd USING (bylaw_document_id)
     ORDER BY dr.document_revision_id
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [(int(r[0]), int(r[1]), r[2]) for r in cur.fetchall()]


# Each metric returns a list of dicts:
#   {logical_bylaw_part, total, gap, comparison_effect, extra_notes}
# `total` may be None when the metric has no natural denominator
# (e.g. relationship_in_text_not_extracted is a population over clauses but
# we only count the matched-but-unextracted ones; total is the matched set).


def metric_requirement_without_numeric_value(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    sql = """
    WITH req AS (
      SELECT structured_fact_id,
             value_payload->'numeric_value_refs' AS refs
        FROM zoning.structured_fact
       WHERE is_active AND fact_family='requirements'
         AND document_revision_id=%s
    ),
    nv AS (
      SELECT value_payload->>'numeric_value_id' AS nvid
        FROM zoning.structured_fact
       WHERE is_active AND fact_family='numeric_values'
         AND document_revision_id=%s
    ),
    expanded AS (
      SELECT r.structured_fact_id,
             COALESCE(jsonb_array_length(r.refs),0) AS n_refs,
             COUNT(*) FILTER (WHERE nv.nvid IS NULL) AS unresolved
        FROM req r
   LEFT JOIN LATERAL jsonb_array_elements_text(COALESCE(r.refs,'[]'::jsonb)) AS rid ON true
   LEFT JOIN nv ON nv.nvid = rid
       GROUP BY r.structured_fact_id, r.refs
    )
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE n_refs=0 OR unresolved>0) AS gap
      FROM expanded;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (revision_id, revision_id))
        total, gap = cur.fetchone()
    if not gap:
        return []
    return [{
        "logical_bylaw_part": "requirements",
        "total": int(total),
        "gap": int(gap),
        "comparison_effect": "requirements_without_resolved_numeric_values",
        "extra_notes": None,
    }]


def metric_numeric_value_orphan(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    sql = """
    WITH nv AS (
      SELECT value_payload->>'numeric_value_id' AS nvid
        FROM zoning.structured_fact
       WHERE is_active AND fact_family='numeric_values'
         AND document_revision_id=%s
    ),
    refs AS (
      SELECT DISTINCT jsonb_array_elements_text(value_payload->'numeric_value_refs') AS nvid
        FROM zoning.structured_fact
       WHERE is_active AND fact_family='requirements'
         AND document_revision_id=%s
    )
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE r.nvid IS NULL) AS gap
      FROM nv LEFT JOIN refs r USING (nvid);
    """
    with conn.cursor() as cur:
        cur.execute(sql, (revision_id, revision_id))
        total, gap = cur.fetchone()
    if not gap:
        return []
    return [{
        "logical_bylaw_part": "numeric_values",
        "total": int(total),
        "gap": int(gap),
        "comparison_effect": "numeric_values_unreferenced_by_any_requirement",
        "extra_notes": None,
    }]


def metric_relationship_in_text_not_extracted(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    # Pull every active clause's id + text, scan in Python for override
    # phrasings, then bucket into "matched but already covered" vs
    # "matched and missing".
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT clause_source_id, clause_text_raw
              FROM zoning.clause
             WHERE is_active AND document_revision_id=%s
               AND clause_text_raw IS NOT NULL
            """,
            (revision_id,),
        )
        clauses = cur.fetchall()
        cur.execute(
            """
            SELECT DISTINCT source_record_key
              FROM zoning.structured_fact
             WHERE is_active AND fact_family='cross_references'
               AND document_revision_id=%s
               AND source_record_table='clause'
            """,
            (revision_id,),
        )
        covered = {row[0] for row in cur.fetchall() if row[0]}

    matched = 0
    missing: list[tuple[str, str]] = []
    for clause_id, text in clauses:
        if not text:
            continue
        for label, regex in RELATIONSHIP_PATTERNS:
            if regex.search(text):
                matched += 1
                if clause_id not in covered:
                    missing.append((clause_id, label))
                break
    if not missing:
        return []
    sample = ",".join(f"{cid}:{label}" for cid, label in missing[:5])
    return [{
        "logical_bylaw_part": "clauses",
        "total": matched,
        "gap": len(missing),
        "comparison_effect": "override_phrasings_in_clause_text_with_no_structured_edge",
        "extra_notes": f"sample={sample}",
    }]


def metric_requirement_applicability_missing(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    sql = """
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE
             COALESCE(jsonb_array_length(value_payload->'applicability'->'applies_to_use_terms'),0)=0
             AND COALESCE(jsonb_array_length(value_payload->'applicability'->'applies_to_zone_codes'),0)=0
           ) AS gap
      FROM zoning.structured_fact
     WHERE is_active AND fact_family='requirements'
       AND document_revision_id=%s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (revision_id,))
        total, gap = cur.fetchone()
    if not gap:
        return []
    return [{
        "logical_bylaw_part": "requirements",
        "total": int(total),
        "gap": int(gap),
        "comparison_effect": "requirements_with_no_applicability_predicate",
        "extra_notes": None,
    }]


def metric_map_reference_not_linked(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    sql = """
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE
                NULLIF(value_payload->>'postgis_schema','') IS NULL
             OR NULLIF(value_payload->>'postgis_table','') IS NULL
             OR NULLIF(value_payload->>'postgis_layer_name','') IS NULL
             OR NULLIF(value_payload->>'feature_key','') IS NULL
           ) AS gap
      FROM zoning.structured_fact
     WHERE is_active AND fact_family='map_layer_references'
       AND document_revision_id=%s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (revision_id,))
        total, gap = cur.fetchone()
    if not gap:
        return []
    return [{
        "logical_bylaw_part": "map_layer_references",
        "total": int(total),
        "gap": int(gap),
        "comparison_effect": "map_references_missing_postgis_linkage",
        "extra_notes": None,
    }]


def metric_use_without_term_id(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    sql = """
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE NULLIF(value_payload->>'use_term_id','') IS NULL) AS gap
      FROM zoning.structured_fact
     WHERE is_active AND fact_family='uses'
       AND document_revision_id=%s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (revision_id,))
        total, gap = cur.fetchone()
    if not gap:
        return []
    return [{
        "logical_bylaw_part": "uses",
        "total": int(total),
        "gap": int(gap),
        "comparison_effect": "use_rows_with_no_use_term_id_link",
        "extra_notes": None,
    }]


def metric_raw_table_no_structured_facts(
    conn: psycopg.Connection, revision_id: int
) -> list[dict[str, Any]]:
    sql = """
    WITH all_tables AS (
      SELECT raw_table_id
        FROM zoning.raw_table
       WHERE is_active AND document_revision_id=%s
    ),
    referenced AS (
      SELECT DISTINCT (value_payload->>'raw_table_id')::bigint AS raw_table_id
        FROM zoning.structured_fact
       WHERE is_active AND document_revision_id=%s
         AND value_payload ? 'raw_table_id'
    )
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE r.raw_table_id IS NULL) AS gap
      FROM all_tables a LEFT JOIN referenced r USING (raw_table_id);
    """
    with conn.cursor() as cur:
        cur.execute(sql, (revision_id, revision_id))
        total, gap = cur.fetchone()
    if not gap:
        return []
    return [{
        "logical_bylaw_part": "raw_tables",
        "total": int(total),
        "gap": int(gap),
        "comparison_effect": "raw_tables_with_no_structured_fact_extraction",
        "extra_notes": None,
    }]


METRICS: list[tuple[str, Any]] = [
    ("requirement_without_numeric_value", metric_requirement_without_numeric_value),
    ("numeric_value_orphan", metric_numeric_value_orphan),
    ("relationship_in_text_not_extracted", metric_relationship_in_text_not_extracted),
    ("requirement_applicability_missing", metric_requirement_applicability_missing),
    ("map_reference_not_linked", metric_map_reference_not_linked),
    ("use_without_term_id", metric_use_without_term_id),
    ("raw_table_no_structured_facts", metric_raw_table_no_structured_facts),
]


def write_audit_rows(
    conn: psycopg.Connection,
    bylaw_document_id: int,
    revision_id: int,
    gap_type: str,
    rows: list[dict[str, Any]],
) -> None:
    with conn.cursor() as cur:
        for row in rows:
            notes_parts = [
                f"population_total={row['total']}",
                f"population_gap={row['gap']}",
            ]
            if row.get("extra_notes"):
                notes_parts.append(row["extra_notes"])
            notes = " ".join(notes_parts)
            cur.execute(
                """
                INSERT INTO zoning.coverage_gap
                  (bylaw_document_id, document_revision_id, gap_type,
                   logical_bylaw_part, source_locator, source_file,
                   expected_record_family, comparison_effect, status, notes,
                   is_audit_generated)
                VALUES (%s, %s, %s, %s, NULL, NULL, %s, %s, %s, %s, true)
                """,
                (
                    bylaw_document_id,
                    revision_id,
                    gap_type,
                    row["logical_bylaw_part"],
                    row["logical_bylaw_part"],
                    row["comparison_effect"],
                    "in_progress",
                    notes,
                ),
            )


def run_audit(conn: psycopg.Connection) -> dict[str, Any]:
    revs = revisions(conn)
    snapshot: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "revisions": [],
    }
    for revision_id, bylaw_document_id, family in revs:
        per_rev: dict[str, Any] = {
            "document_revision_id": revision_id,
            "document_family": family,
            "gaps": {},
        }
        # Idempotency: clear prior audit rows for this revision.
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM zoning.coverage_gap "
                "WHERE document_revision_id=%s AND is_audit_generated=true",
                (revision_id,),
            )
        for gap_type, fn in METRICS:
            rows = fn(conn, revision_id)
            per_rev["gaps"][gap_type] = rows
            write_audit_rows(conn, bylaw_document_id, revision_id, gap_type, rows)
        snapshot["revisions"].append(per_rev)
    return snapshot


def print_summary(snapshot: dict[str, Any]) -> None:
    for rev in snapshot["revisions"]:
        print(f"\nRevision {rev['document_revision_id']} ({rev['document_family']}):")
        any_gap = False
        for gap_type, rows in rev["gaps"].items():
            for r in rows:
                any_gap = True
                pct = (
                    f" ({100.0 * r['gap'] / r['total']:.1f}%)"
                    if r["total"] else ""
                )
                print(
                    f"  {gap_type:42s} "
                    f"part={r['logical_bylaw_part']:24s} "
                    f"gap={r['gap']}/{r['total']}{pct}"
                )
        if not any_gap:
            print("  (no gaps)")


def write_snapshot(snapshot: dict[str, Any]) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = (
        dt.datetime.now(dt.timezone.utc)
        .strftime("%Y%m%dT%H%M%SZ")
    )
    path = SNAPSHOT_DIR / f"population-audit-{stamp}.json"
    path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Run all queries and print the summary, but do not "
                             "write coverage_gap rows or a JSON snapshot.")
    parser.add_argument("--no-snapshot", action="store_true",
                        help="Skip writing the JSON snapshot under data/zoning/charlottetown/audits/.")
    args = parser.parse_args()

    with psycopg.connect(database_url()) as conn:
        snapshot = run_audit(conn)
        if args.dry_run:
            conn.rollback()
            print("\n(dry-run, no changes written)")
        else:
            conn.commit()

    print_summary(snapshot)

    if not args.dry_run and not args.no_snapshot:
        path = write_snapshot(snapshot)
        print(f"\nSnapshot: {path.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()

"""Apply versioned section-equivalence decisions to the database.

Reads the JSON file produced by
scripts/export-charlottetown-section-equivalence-decisions.py and stamps
review_status, equivalence_type, and reviewer_notes onto the matching rows in
zoning.section_equivalence. Designed to run after
scripts/generate-charlottetown-section-equivalence.py during a database
standup, so reviewer decisions persist across rebuilds.

Matching is by the natural-key triple
(current_section_key, draft_section_key, candidate_method).

By default, only rows whose current review_status is `candidate` are touched,
making the script idempotent and safe to re-run. Pass --force to overwrite
existing accepted/rejected rows when reconciling diverged datasets.

Usage
-----
    python scripts/apply-charlottetown-section-equivalence-decisions.py
    python scripts/apply-charlottetown-section-equivalence-decisions.py --in <path>
    python scripts/apply-charlottetown-section-equivalence-decisions.py --dry-run
    python scripts/apply-charlottetown-section-equivalence-decisions.py --force
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = (
    REPO_ROOT
    / "data"
    / "zoning"
    / "charlottetown"
    / "manual-corrections"
    / "section-equivalence-decisions.json"
)
SUPPORTED_SCHEMA_VERSIONS = {1}
NATURAL_KEY_FIELDS = ("current_section_key", "draft_section_key", "candidate_method")


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def load_artifact(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Decisions file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SystemExit(
            f"Unsupported schema_version {schema_version!r}; "
            f"this script supports {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    decisions = payload.get("decisions") or []
    if not isinstance(decisions, list):
        raise SystemExit("Decisions file is malformed: 'decisions' must be a list")
    return decisions


def apply_decisions(
    conn: psycopg.Connection,
    decisions: list[dict],
    *,
    force: bool,
    dry_run: bool,
) -> dict[str, int]:
    counts = {"updated": 0, "unchanged": 0, "missing": 0, "skipped_reviewed": 0}
    sql_lookup = """
        SELECT section_equivalence_id, review_status, equivalence_type, reviewer_notes
        FROM zoning.section_equivalence
        WHERE current_section_key = %s
          AND draft_section_key = %s
          AND candidate_method = %s
    """
    sql_update = """
        UPDATE zoning.section_equivalence
           SET review_status = %s,
               equivalence_type = COALESCE(%s, equivalence_type),
               reviewer_notes = %s,
               updated_at = now()
         WHERE section_equivalence_id = %s
    """

    with conn.cursor() as cur:
        for row in decisions:
            for field in NATURAL_KEY_FIELDS:
                if not row.get(field):
                    raise SystemExit(f"Decision is missing required key {field}: {row!r}")

            cur.execute(
                sql_lookup,
                (row["current_section_key"], row["draft_section_key"], row["candidate_method"]),
            )
            existing = cur.fetchone()
            if existing is None:
                counts["missing"] += 1
                continue

            equivalence_id, current_status, current_eq_type, current_notes = existing

            if not force and current_status not in ("candidate", row["review_status"]):
                counts["skipped_reviewed"] += 1
                continue

            target_status = row["review_status"]
            target_eq_type = row.get("equivalence_type")
            target_notes = row.get("reviewer_notes")

            if (
                current_status == target_status
                and (target_eq_type is None or current_eq_type == target_eq_type)
                and current_notes == target_notes
            ):
                counts["unchanged"] += 1
                continue

            if dry_run:
                counts["updated"] += 1
                continue

            cur.execute(
                sql_update,
                (target_status, target_eq_type, target_notes, equivalence_id),
            )
            counts["updated"] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in",
        dest="input_path",
        type=Path,
        default=DEFAULT_IN,
        help=f"Input JSON path (default: {DEFAULT_IN.relative_to(REPO_ROOT).as_posix()})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing accepted/rejected rows. By default only candidate rows are updated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing.",
    )
    args = parser.parse_args()

    decisions = load_artifact(args.input_path)
    print(f"Loaded {len(decisions)} decisions from {args.input_path.relative_to(REPO_ROOT).as_posix()}")

    with psycopg.connect(database_url()) as conn:
        counts = apply_decisions(conn, decisions, force=args.force, dry_run=args.dry_run)
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

    label = "Would update" if args.dry_run else "Updated"
    print(f"{label}: {counts['updated']}")
    print(f"Unchanged: {counts['unchanged']}")
    print(f"Skipped (already reviewed, use --force to override): {counts['skipped_reviewed']}")
    print(f"Missing (no matching row in DB): {counts['missing']}")


if __name__ == "__main__":
    main()

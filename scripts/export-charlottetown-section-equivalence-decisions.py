"""Export reviewed section-equivalence decisions to a versioned JSON file.

The generator (scripts/generate-charlottetown-section-equivalence.py) seeds rows
with review_status='candidate' and preserves any non-candidate row on re-run.
Reviewer decisions (`accepted`, `rejected`) therefore live exclusively in the
database; if the database is dropped or rebuilt elsewhere, the decisions are
lost. This script captures them as a versioned JSON artifact in
data/zoning/charlottetown/manual-corrections/, keyed by stable natural keys so
the companion apply script can re-stamp them onto a fresh database.

Usage
-----
    python scripts/export-charlottetown-section-equivalence-decisions.py
    python scripts/export-charlottetown-section-equivalence-decisions.py --out <path>

Connection settings come from PG* environment variables, defaulting to the local
docker-compose Postgres on port 54329.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = (
    REPO_ROOT
    / "data"
    / "zoning"
    / "charlottetown"
    / "manual-corrections"
    / "section-equivalence-decisions.json"
)
SCHEMA_VERSION = 1


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def fetch_decisions(conn: psycopg.Connection) -> list[dict]:
    sql = """
    SELECT
        current_section_key,
        draft_section_key,
        candidate_method,
        review_status,
        equivalence_type,
        reviewer_notes,
        updated_at
    FROM zoning.section_equivalence
    WHERE review_status IN ('accepted', 'rejected')
    ORDER BY current_section_key, draft_section_key, candidate_method
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [c.name for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    for row in rows:
        if isinstance(row.get("updated_at"), datetime):
            row["updated_at"] = row["updated_at"].astimezone(timezone.utc).isoformat()
    return rows


def write_artifact(path: Path, decisions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "natural_key_fields": [
            "current_section_key",
            "draft_section_key",
            "candidate_method",
        ],
        "decision_count": len(decisions),
        "decisions": decisions,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON path (default: {DEFAULT_OUT.relative_to(REPO_ROOT).as_posix()})",
    )
    args = parser.parse_args()

    with psycopg.connect(database_url()) as conn:
        decisions = fetch_decisions(conn)

    write_artifact(args.out, decisions)
    print(f"Exported {len(decisions)} decisions to {args.out.relative_to(REPO_ROOT).as_posix()}")
    by_status: dict[str, int] = {}
    for row in decisions:
        by_status[row["review_status"]] = by_status.get(row["review_status"], 0) + 1
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()

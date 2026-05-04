"""Discover and classify override-pattern candidate clauses.

Scans zoning.clause for clauses containing override-style phrasing
(notwithstanding / does_not_apply / shall_not_apply / except_as_provided /
supersedes), classifies each by pattern, and emits a JSON review file. The
output is a reproducible audit artifact, not the source of truth: the curated
overrides ship in
data/zoning/charlottetown/manual-corrections/override-relationships.json,
which is consumed by scripts/apply-charlottetown-override-relationships.py.

Usage
-----
    python scripts/extract-charlottetown-override-candidates.py
    python scripts/extract-charlottetown-override-candidates.py --out <path>

Connection settings come from PG* environment variables, defaulting to the
local docker-compose Postgres on port 54329.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    / "override-candidates-review.json"
)
SCHEMA_VERSION = 1


# Pattern -> (regex, classification reason). Order matters; first match wins.
PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "accessory_use_template",
        "Per-zone accessory/secondary use list; already captured as `uses` facts.",
        re.compile(
            r"\bnotwithstanding\s+the\s+requirements,\s+the\s+following\s+are\s+permitted\s+as\s+accessory\s+or\s+secondary\s+uses\b",
            re.IGNORECASE,
        ),
    ),
    (
        "global_standalone",
        "'Notwithstanding any other provision/requirement/section of this by-law' introduces a standalone rule, not a graph edge.",
        re.compile(
            r"\bnotwithstanding\s+(any|the)\s+(other\s+)?(provisions?|requirements?|sections?)\s+of\s+this\s+by-?law\b",
            re.IGNORECASE,
        ),
    ),
    (
        "global_all_other",
        "'Notwithstanding all other sections of this by-law' inside a zone-wide override (e.g. CDA).",
        re.compile(r"\bnotwithstanding\s+all\s+other\s+sections\b", re.IGNORECASE),
    ),
    (
        "local_foregoing",
        "'Notwithstanding the foregoing' refers to the immediately preceding clause; not a graph edge.",
        re.compile(r"\bnotwithstanding\s+(the\s+)?foregoing\b", re.IGNORECASE),
    ),
    (
        "section_or_clause_ref",
        "'Notwithstanding section/clause/part X.Y[.Z]' references a specific section, clause, or part — likely a real cross-reference.",
        re.compile(
            r"\bnotwithstanding\s+(section|sections|clause|clauses|part|parts)\s+\d",
            re.IGNORECASE,
        ),
    ),
    (
        "numeric_ref",
        "'Notwithstanding 7.11.2' or similar bare numeric clause/section reference.",
        re.compile(r"\bnotwithstanding\s+\d+\.\d", re.IGNORECASE),
    ),
    (
        "category_ref",
        "'Notwithstanding the X requirements' references a category of rule that may span multiple zones.",
        re.compile(
            r"\bnotwithstanding\s+the\s+[a-z][a-zA-Z\s&,]+(requirements?|provisions?|setbacks?|ratios?|height|frontage|area)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "does_not_apply_local",
        "'this clause/section shall not apply ...' often self-limits the same clause/section.",
        re.compile(
            r"\b(this\s+(clause|section|provision)|the\s+(parking|preceding))\s+(shall\s+)?not\s+apply\b",
            re.IGNORECASE,
        ),
    ),
    (
        "does_not_apply_specific",
        "'X does not apply to Y' or 'X shall not apply where Y' may name a specific target.",
        re.compile(r"\b(does|shall)\s+not\s+apply\b", re.IGNORECASE),
    ),
    (
        "except_as_provided",
        "'except as provided/otherwise permitted in this bylaw' is usually a phrasing convention with no graph target.",
        re.compile(r"\bexcept\s+as\s+(provided|otherwise)\b", re.IGNORECASE),
    ),
    (
        "supersedes",
        "Explicit 'supersedes' phrasing.",
        re.compile(r"\bsupersedes\b", re.IGNORECASE),
    ),
]


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def classify(text: str) -> tuple[str, str]:
    for label, reason, regex in PATTERNS:
        if regex.search(text):
            return label, reason
    return "uncategorized", "No override pattern matched; flag for human review."


def fetch_candidates(conn: psycopg.Connection) -> list[dict]:
    sql = """
    SELECT document_revision_id, clause_source_id, clause_text_raw
    FROM zoning.clause
    WHERE is_active
      AND (
            clause_text_raw ~* '\\mnotwithstanding\\M'
         OR clause_text_raw ~* '\\m(does|shall)\\s+not\\s+apply\\M'
         OR clause_text_raw ~* '\\mexcept\\s+as\\s+(provided|otherwise)\\M'
         OR clause_text_raw ~* '\\msupersedes\\M'
          )
    ORDER BY document_revision_id, clause_source_id
    """
    rows: list[dict] = []
    with conn.cursor() as cur:
        cur.execute(sql)
        for revision_id, clause_source_id, clause_text in cur.fetchall():
            classification, reason = classify(clause_text)
            rows.append(
                {
                    "document_revision_id": int(revision_id),
                    "clause_source_id": clause_source_id,
                    "classification": classification,
                    "classification_reason": reason,
                    "clause_text_raw": clause_text,
                }
            )
    return rows


def write_artifact(path: Path, rows: list[dict]) -> None:
    by_class: dict[str, int] = {}
    for row in rows:
        by_class[row["classification"]] = by_class.get(row["classification"], 0) + 1
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_count": len(rows),
        "candidate_count_by_classification": dict(sorted(by_class.items())),
        "candidates": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output review file (default: %(default)s)")
    args = parser.parse_args()

    with psycopg.connect(database_url()) as conn:
        rows = fetch_candidates(conn)

    write_artifact(args.out, rows)
    print(f"Wrote {len(rows)} candidates to {args.out.relative_to(REPO_ROOT).as_posix()}")
    by_class: dict[str, int] = {}
    for row in rows:
        by_class[row["classification"]] = by_class.get(row["classification"], 0) + 1
    for label, count in sorted(by_class.items()):
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()

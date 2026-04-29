from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

import psycopg


METHOD = "title_topic_token_v1"

TITLE_FAMILIES = {
    "permitted_uses": {
        "permitted uses",
        "regulations for permitted uses",
        "permitted with conditions",
        "conditional uses",
    },
    "built_form": {
        "built form requirements",
        "development standards",
        "bonus height development standards",
        "lot requirements",
        "yard requirements",
        "setback requirements",
        "building height",
    },
    "landscaping": {
        "landscape requirements",
        "landscaping",
        "land use buffers",
    },
    "signage": {
        "sign",
        "signs",
        "signage",
    },
}


@dataclass(frozen=True)
class Section:
    section_id: int
    natural_key: str
    document_family: str
    document_type: str | None
    zone_code: str | None
    section_label_raw: str | None
    section_title_raw: str | None
    assigned_topic: str | None
    source_order: int | None
    clause_text: str


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def norm_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def tokens(value: str | None) -> set[str]:
    return {part for part in norm_text(value).split(" ") if len(part) > 2}


def ratio(left: str | None, right: str | None) -> float:
    left_norm = norm_text(left)
    right_norm = norm_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def title_family(value: str | None) -> str | None:
    normalized = norm_text(value)
    if not normalized:
        return None
    for family, phrases in TITLE_FAMILIES.items():
        if any(phrase in normalized for phrase in phrases):
            return family
    return None


def compatible_title_family(current: Section, draft: Section) -> bool:
    current_family = title_family(current.section_title_raw)
    draft_family = title_family(draft.section_title_raw)
    return bool(current_family and current_family == draft_family)


def family_sections(conn: psycopg.Connection) -> list[Section]:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH clause_text AS (
              SELECT
                c.section_id,
                string_agg(c.clause_text_raw, ' ' ORDER BY c.source_order) AS text_raw
              FROM zoning.clause c
              WHERE c.is_active
              GROUP BY c.section_id
            ),
            table_text AS (
              SELECT
                rt.section_id,
                string_agg(rtc.cell_text_raw, ' ' ORDER BY rt.source_order, rtc.row_order, rtc.column_order) AS text_raw
              FROM zoning.raw_table rt
              JOIN zoning.raw_table_cell rtc
                ON rtc.raw_table_id = rt.raw_table_id
               AND rtc.is_active
              WHERE rt.is_active
                AND rt.section_id IS NOT NULL
                AND nullif(btrim(rtc.cell_text_raw), '') IS NOT NULL
              GROUP BY rt.section_id
            )
            SELECT
              s.section_id,
              s.natural_key,
              bd.document_family,
              s.document_type,
              s.zone_code,
              s.section_label_raw,
              s.section_title_raw,
              s.assigned_topic,
              s.source_order,
              concat_ws(' ', ct.text_raw, tt.text_raw) AS clause_text
            FROM zoning.section s
            JOIN zoning.document_revision dr
              ON dr.document_revision_id = s.document_revision_id
            JOIN zoning.bylaw_document bd
              ON bd.bylaw_document_id = dr.bylaw_document_id
            LEFT JOIN clause_text ct
              ON ct.section_id = s.section_id
            LEFT JOIN table_text tt
              ON tt.section_id = s.section_id
            WHERE s.is_active
              AND bd.document_family IN ('current', 'draft')
            GROUP BY
              s.section_id,
              s.natural_key,
              bd.document_family,
              s.document_type,
              s.zone_code,
              s.section_label_raw,
              s.section_title_raw,
              s.assigned_topic,
              s.source_order,
              ct.text_raw,
              tt.text_raw
            ORDER BY bd.document_family, s.source_order, s.section_id
            """
        )
        return [Section(*row) for row in cur.fetchall()]


def is_eligible_pair(current: Section, draft: Section) -> bool:
    if current.document_type and draft.document_type and current.document_type != draft.document_type:
        return False
    exact_title = norm_text(current.section_title_raw) == norm_text(draft.section_title_raw)
    if current.zone_code and draft.zone_code and current.zone_code == draft.zone_code:
        return exact_title or compatible_title_family(current, draft)
    if current.zone_code or draft.zone_code:
        return False
    if exact_title:
        return True
    if compatible_title_family(current, draft):
        return True
    if current.assigned_topic and draft.assigned_topic and current.assigned_topic == draft.assigned_topic:
        return ratio(current.section_title_raw, draft.section_title_raw) >= 0.62
    return False


def score_pair(current: Section, draft: Section) -> tuple[float, float, float]:
    title_similarity = ratio(current.section_title_raw, draft.section_title_raw)
    title_token_similarity = jaccard(tokens(current.section_title_raw), tokens(draft.section_title_raw))
    text_similarity = jaccard(tokens(current.clause_text), tokens(draft.clause_text))
    score = max(title_similarity, title_token_similarity * 0.95, text_similarity * 0.75)
    if current.assigned_topic and current.assigned_topic == draft.assigned_topic:
        score += 0.08
    if current.zone_code and current.zone_code == draft.zone_code:
        score += 0.12
    return min(score, 1.0), title_similarity, text_similarity


def equivalence_type(score: float, title_similarity: float, text_similarity: float) -> str:
    if title_similarity >= 0.92 or score >= 0.92:
        return "same_topic"
    if text_similarity >= 0.45 or score >= 0.72:
        return "renamed_or_restructured"
    return "partial_overlap"


def candidate_pairs(sections: list[Section]) -> list[tuple[Section, Section, float, float, float, str]]:
    current_sections = [section for section in sections if section.document_family == "current"]
    draft_sections = [section for section in sections if section.document_family == "draft"]
    candidates: list[tuple[Section, Section, float, float, float, str]] = []

    for current in current_sections:
        scored: list[tuple[float, float, float, Section]] = []
        for draft in draft_sections:
            if not norm_text(current.clause_text) or not norm_text(draft.clause_text):
                continue
            if not is_eligible_pair(current, draft):
                continue
            score, title_similarity, text_similarity = score_pair(current, draft)
            family_match = compatible_title_family(current, draft)
            exact_title = norm_text(current.section_title_raw) == norm_text(draft.section_title_raw)
            strong_match = (
                exact_title
                or title_similarity >= 0.68
                or text_similarity >= 0.32
                or (family_match and score >= 0.50)
            )
            if strong_match:
                scored.append((score, title_similarity, text_similarity, draft))
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        for score, title_similarity, text_similarity, draft in scored[:3]:
            candidates.append(
                (
                    current,
                    draft,
                    score,
                    title_similarity,
                    text_similarity,
                    equivalence_type(score, title_similarity, text_similarity),
                )
            )
    return candidates


def upsert_candidate(
    conn: psycopg.Connection,
    current: Section,
    draft: Section,
    title_similarity: float,
    text_similarity: float,
    eq_type: str,
) -> str:
    topic = current.assigned_topic if current.assigned_topic == draft.assigned_topic else current.assigned_topic or draft.assigned_topic
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT section_equivalence_id, review_status
            FROM zoning.section_equivalence
            WHERE current_section_key = %s
              AND draft_section_key = %s
              AND candidate_method = %s
            """,
            (current.natural_key, draft.natural_key, METHOD),
        )
        existing = cur.fetchone()
        if not existing:
            cur.execute(
                """
                INSERT INTO zoning.section_equivalence (
                  current_section_id,
                  draft_section_id,
                  current_section_key,
                  draft_section_key,
                  candidate_method,
                  title_similarity,
                  text_similarity,
                  assigned_topic,
                  review_status,
                  equivalence_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'candidate', %s)
                """,
                (
                    current.section_id,
                    draft.section_id,
                    current.natural_key,
                    draft.natural_key,
                    METHOD,
                    round(title_similarity, 6),
                    round(text_similarity, 6),
                    topic,
                    eq_type,
                ),
            )
            return "inserted"

        equivalence_id, review_status = existing
        if review_status != "candidate":
            return "preserved_reviewed"
        cur.execute(
            """
            UPDATE zoning.section_equivalence
            SET current_section_id = %s,
                draft_section_id = %s,
                title_similarity = %s,
                text_similarity = %s,
                assigned_topic = %s,
                equivalence_type = %s,
                updated_at = now()
            WHERE section_equivalence_id = %s
            """,
            (
                current.section_id,
                draft.section_id,
                round(title_similarity, 6),
                round(text_similarity, 6),
                topic,
                eq_type,
                equivalence_id,
            ),
        )
        return "updated"


def prune_stale_candidates(
    conn: psycopg.Connection,
    pairs: list[tuple[Section, Section, float, float, float, str]],
) -> int:
    live_pairs = {(current.natural_key, draft.natural_key) for current, draft, *_rest in pairs}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT section_equivalence_id, current_section_key, draft_section_key
            FROM zoning.section_equivalence
            WHERE candidate_method = %s
              AND review_status = 'candidate'
            """,
            (METHOD,),
        )
        stale_ids = [
            row[0]
            for row in cur.fetchall()
            if (row[1], row[2]) not in live_pairs
        ]
        if not stale_ids:
            return 0
        cur.execute(
            "DELETE FROM zoning.section_equivalence WHERE section_equivalence_id = ANY(%s)",
            (stale_ids,),
        )
        return len(stale_ids)


def reset_candidates(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM zoning.section_equivalence WHERE candidate_method = %s",
            (METHOD,),
        )
        return cur.rowcount


def run(dry_run: bool, reset: bool) -> dict[str, int]:
    with psycopg.connect(database_url()) as conn:
        sections = family_sections(conn)
        pairs = candidate_pairs(sections)
        counts = {
            "current_sections": sum(1 for section in sections if section.document_family == "current"),
            "draft_sections": sum(1 for section in sections if section.document_family == "draft"),
            "candidate_pairs": len(pairs),
            "reset_deleted": 0,
            "inserted": 0,
            "updated": 0,
            "preserved_reviewed": 0,
            "pruned_stale": 0,
        }
        if dry_run:
            return counts
        with conn.transaction():
            if reset:
                counts["reset_deleted"] = reset_candidates(conn)
            for current, draft, _score, title_similarity, text_similarity, eq_type in pairs:
                result = upsert_candidate(conn, current, draft, title_similarity, text_similarity, eq_type)
                counts[result] += 1
            counts["pruned_stale"] = prune_stale_candidates(conn, pairs)
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Charlottetown current-vs-draft section-equivalence candidates."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report candidate counts without writing rows.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing rows for this candidate method before inserting regenerated candidates.",
    )
    args = parser.parse_args()
    counts = run(args.dry_run, args.reset)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

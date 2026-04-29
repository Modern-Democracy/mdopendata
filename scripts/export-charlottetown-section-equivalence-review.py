from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg


FIELDS = [
    "review_batch",
    "review_decision",
    "review_decision_source",
    "section_equivalence_id",
    "candidate_method",
    "candidate_topic",
    "db_equivalence_type",
    "db_review_status",
    "title_similarity",
    "text_similarity",
    "current_section_key",
    "current_section_label",
    "current_section_title",
    "current_document_type",
    "current_zone_code",
    "current_citations",
    "current_clause_count",
    "current_text_preview",
    "draft_section_key",
    "draft_section_label",
    "draft_section_title",
    "draft_document_type",
    "draft_zone_code",
    "draft_citations",
    "draft_clause_count",
    "draft_text_preview",
    "reviewer_notes",
    "updated_at",
]


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def export_review(path: Path) -> int:
    sql = """
    WITH section_text AS (
      SELECT
        s.section_id,
        concat_ws(' ', clause_text.text_raw, table_text.text_raw) AS text_raw,
        coalesce(clause_text.item_count, 0) + coalesce(table_text.item_count, 0) AS item_count
      FROM zoning.section s
      LEFT JOIN LATERAL (
        SELECT
          string_agg(c.clause_text_raw, ' ' ORDER BY c.source_order) AS text_raw,
          count(*) AS item_count
        FROM zoning.clause c
        WHERE c.section_id = s.section_id
          AND c.is_active
      ) clause_text ON true
      LEFT JOIN LATERAL (
        SELECT
          string_agg(rtc.cell_text_raw, ' ' ORDER BY rt.source_order, rtc.row_order, rtc.column_order) AS text_raw,
          count(*) AS item_count
        FROM zoning.raw_table rt
        JOIN zoning.raw_table_cell rtc
          ON rtc.raw_table_id = rt.raw_table_id
         AND rtc.is_active
        WHERE rt.section_id = s.section_id
          AND rt.is_active
          AND nullif(btrim(rtc.cell_text_raw), '') IS NOT NULL
      ) table_text ON true
    )
    SELECT
      '2026-04-29-section-equivalence-rerun' AS review_batch,
      'needs_review' AS review_decision,
      'regenerated candidate export after table-text and blank-side repair' AS review_decision_source,
      se.section_equivalence_id,
      se.candidate_method,
      se.assigned_topic AS candidate_topic,
      se.equivalence_type AS db_equivalence_type,
      se.review_status AS db_review_status,
      se.title_similarity,
      se.text_similarity,
      se.current_section_key,
      cs.section_label_raw AS current_section_label,
      cs.section_title_raw AS current_section_title,
      cs.document_type AS current_document_type,
      cs.zone_code AS current_zone_code,
      cs.citations::text AS current_citations,
      cst.item_count AS current_clause_count,
      left(regexp_replace(coalesce(cst.text_raw, ''), '\\s+', ' ', 'g'), 300) AS current_text_preview,
      se.draft_section_key,
      ds.section_label_raw AS draft_section_label,
      ds.section_title_raw AS draft_section_title,
      ds.document_type AS draft_document_type,
      ds.zone_code AS draft_zone_code,
      ds.citations::text AS draft_citations,
      dst.item_count AS draft_clause_count,
      left(regexp_replace(coalesce(dst.text_raw, ''), '\\s+', ' ', 'g'), 300) AS draft_text_preview,
      'Regenerated candidate; prior manual decision reset because accepted set contained mismatches and blank-side comparisons.' AS reviewer_notes,
      se.updated_at
    FROM zoning.section_equivalence se
    JOIN zoning.section cs
      ON cs.section_id = se.current_section_id
    JOIN zoning.section ds
      ON ds.section_id = se.draft_section_id
    JOIN section_text cst
      ON cst.section_id = cs.section_id
    JOIN section_text dst
      ON dst.section_id = ds.section_id
    WHERE se.candidate_method = 'title_topic_token_v1'
    ORDER BY cs.source_order, ds.source_order, se.section_equivalence_id
    """
    count = 0
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(sql)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in cur.fetchall():
                writer.writerow(dict(zip(FIELDS, row)))
                count += 1
    return count


def main() -> None:
    path = Path("data/zoning/charlottetown-draft/review/section-equivalence-review.csv")
    count = export_review(path)
    print(f"exported_rows: {count}")


if __name__ == "__main__":
    main()

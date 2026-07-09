"""Record Phase 7 review decisions approved for Charlottetown 2026/2027 budget QA."""

from __future__ import annotations

import os

import psycopg


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def main() -> int:
    review_key = "reconciliation:debt_total:balance"
    with psycopg.connect(db_url()) as connection:
        with connection.cursor() as cur:
            cur.execute(
                """SELECT id, status
                   FROM budget.review_issue
                  WHERE review_key=%s
                  FOR UPDATE""",
                (review_key,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"Review issue not found: {review_key}")
            issue_id, status = row

            cur.execute(
                """SELECT id
                   FROM budget.review_decision
                  WHERE review_issue_id=%s AND decision_code=%s
                    AND reviewer=%s""",
                (issue_id, "accept_reported_with_warning", "project-owner"),
            )
            decision = cur.fetchone()
            if decision is None:
                cur.execute(
                    """INSERT INTO budget.review_decision
                       (review_issue_id, decision_code, rationale, reviewer)
                       VALUES (%s,%s,%s,%s)""",
                    (
                        issue_id,
                        "accept_reported_with_warning",
                        "Project owner confirmed on 2026-07-09 that the $2 debt balance discrepancy is present in the source document and matches manual calculation.",
                        "project-owner",
                    ),
                )

            if status != "resolved":
                cur.execute(
                    """UPDATE budget.review_issue
                          SET status='resolved', resolved_at=now()
                        WHERE id=%s""",
                    (issue_id,),
                )
        connection.commit()
    print(f"Resolved approved review issue: {review_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

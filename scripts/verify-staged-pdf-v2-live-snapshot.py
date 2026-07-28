#!/usr/bin/env python3
"""Verify the Stage 2 shadow set against a live publication snapshot."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
SHADOW_PATH = BASE / "staged-pdf/v2/stage-2/shadow-observations.json"
MANIFEST_PATH = BASE / "normalized-import-manifest.json"
OUTPUT_PATH = (
    BASE / "staged-pdf/v2/phase-7/live-publication-verification.json"
)
SNAPSHOT_ID = 3
DOCUMENT_ID = 9
NULL_TOKEN = "\\N"
FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def decimal_text(value: Any) -> str:
    if value is None:
        return NULL_TOKEN
    result = format(Decimal(str(value)), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result or "0"


def period_signature(
    record: dict[str, Any],
) -> tuple[str, int, str]:
    natural = record["natural_key"]
    statement = natural["statement_key"]
    if statement == "appendix-property-tax-statement":
        mapping = {
            "assessment": (0, "appendix_assessment"),
            "rate": (1, "appendix_rate"),
            "tax_revenue": (2, "appendix_tax_revenue"),
        }
        column, role = mapping[natural["amount_type"]]
        return "ctown_budget_2026_2027_p149", column, role
    if statement == "appendix-city-debt-statement":
        mapping = {
            "balance": (0, "appendix_balance"),
            "principal": (1, "appendix_principal"),
            "interest": (2, "appendix_interest"),
            "budget": (1, "appendix_principal"),
        }
        column, role = mapping[natural["amount_type"]]
        return "ctown_budget_2026_2027_p151", column, role
    match = re.match(
        r"^2026-2027:(.+):column-(\d+):([^:]+)$",
        natural["document_period_key"],
    )
    if not match:
        raise ValueError(
            f"Unsupported document period: "
            f"{natural['document_period_key']}"
        )
    return match.group(1), int(match.group(2)), match.group(3)


def digest_strings(records: list[str]) -> str:
    body = RECORD_SEPARATOR.join(sorted(records)).encode("utf-8")
    return hashlib.md5(body, usedforsecurity=False).hexdigest()


def expected_summary(
    shadow: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    statements = {
        item["key"]: item for item in manifest["statements"]
    }
    facts = {
        (
            item["line_key"],
            item["document_period_key"],
            item["amount_type"],
            item["measure_unit"],
        ): item["key"]
        for item in manifest["facts"]
    }
    fact_sources = {
        item["fact_key"]: item for item in manifest["fact_sources"]
    }
    semantic_records: list[str] = []
    source_records: list[str] = []
    for record in shadow["records"]:
        natural = record["natural_key"]
        statement_key = natural["statement_key"]
        table_key, column_index, period_role = period_signature(record)
        entity_key = (
            "city-of-charlottetown"
            if statement_key in {
                "appendix-property-tax-statement",
                "appendix-city-debt-statement",
            }
            else statements[statement_key]["reporting_entity_key"]
        )
        fields = [
            statement_key,
            natural["line_key"],
            entity_key,
            table_key,
            str(column_index),
            period_role,
            natural["amount_type"],
            natural["measure_unit"],
            decimal_text(record["value_numeric"]),
            (
                record["value_text"]
                if record["value_text"] is not None
                else NULL_TOKEN
            ),
            record["value_state"],
            record["review_status"],
        ]
        semantic = FIELD_SEPARATOR.join(fields)
        semantic_records.append(semantic)
        if (
            record["baseline_origin"]
            == "approved-normalized-import-manifest"
        ):
            fact_key = facts[(
                natural["line_key"],
                natural["document_period_key"],
                natural["amount_type"],
                natural["measure_unit"],
            )]
            source = fact_sources[fact_key]
            cell_prefix, source_column = source[
                "source_cell_key"
            ].rsplit(":column-", 1)
            source_table, source_row = cell_prefix.rsplit(":", 1)
            source_fields = [
                source_table,
                source_row,
                source_column,
                source["source_role"],
                str(source["source_order"]),
            ]
        else:
            source_fields = [
                record["source"]["table_id"],
                record["source"]["row_id"],
                "0",
                "reported_value",
                "0",
            ]
        source_records.append(
            semantic
            + FIELD_SEPARATOR
            + FIELD_SEPARATOR.join(source_fields)
        )
    return {
        "observation_count": len(semantic_records),
        "distinct_semantic_count": len(set(semantic_records)),
        "digest_algorithm": "md5",
        "semantic_digest": digest_strings(semantic_records),
        "source_link_count": len(source_records),
        "distinct_source_link_count": len(set(source_records)),
        "source_digest": digest_strings(source_records),
    }


def verification_sql() -> str:
    return f"""
WITH snapshot AS (
  SELECT id, release_label, status, source_document_ids
  FROM budget.publication_snapshot
  WHERE id={SNAPSHOT_ID}
),
base AS (
  SELECT
    s.statement_key,
    li.line_key,
    re.slug AS entity_key,
    st.table_key,
    col.column_index,
    dp.period_role,
    at.code AS amount_type,
    mu.code AS measure_unit,
    COALESCE(trim_scale(o.value_numeric)::text, chr(92) || 'N')
      AS value_numeric,
    COALESCE(o.value_text, chr(92) || 'N') AS value_text,
    o.value_state,
    o.review_status,
    o.id AS observation_id
  FROM budget.publication_observation po
  JOIN budget.financial_observation o ON o.id=po.observation_id
  JOIN budget.line_item li ON li.id=o.line_item_id
  JOIN budget.statement s ON s.id=li.statement_id
  JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
  JOIN budget.document_period dp ON dp.id=o.document_period_id
  JOIN budget.source_table_column col
    ON col.id=dp.source_table_column_id
  JOIN budget.source_table st ON st.id=col.source_table_id
  JOIN budget.amount_type at ON at.id=o.amount_type_id
  JOIN budget.measure_unit mu ON mu.id=o.measure_unit_id
  WHERE po.snapshot_id={SNAPSHOT_ID} AND s.document_id={DOCUMENT_ID}
),
semantic AS (
  SELECT observation_id, concat_ws(chr(31),
    statement_key,line_key,entity_key,table_key,column_index::text,
    period_role,amount_type,measure_unit,value_numeric,value_text,
    value_state,review_status
  ) AS canonical_record
  FROM base
),
sources AS (
  SELECT
    semantic.observation_id,
    semantic.canonical_record || chr(31) ||
    concat_ws(chr(31),
      source_table.table_key,
      source_row.row_key,
      source_col.column_index::text,
      fos.source_role,
      fos.source_order::text
    ) AS canonical_record
  FROM semantic
  JOIN budget.financial_observation_source fos
    ON fos.observation_id=semantic.observation_id
  JOIN budget.source_table_cell source_cell
    ON source_cell.id=fos.source_cell_id
  JOIN budget.source_table_row source_row
    ON source_row.id=source_cell.source_row_id
  JOIN budget.source_table source_table
    ON source_table.id=source_row.source_table_id
  JOIN budget.source_table_column source_col
    ON source_col.id=source_cell.source_table_column_id
)
SELECT
  snapshot.id AS snapshot_id,
  snapshot.release_label,
  snapshot.status,
  snapshot.source_document_ids,
  (SELECT count(*) FROM budget.publication_observation
    WHERE snapshot_id={SNAPSHOT_ID}) AS snapshot_observation_count,
  (SELECT count(*) FROM semantic) AS observation_count,
  (SELECT count(DISTINCT canonical_record) FROM semantic)
    AS distinct_semantic_count,
  'md5' AS digest_algorithm,
  (SELECT md5(
    string_agg(canonical_record, chr(30) ORDER BY canonical_record)
  ) FROM semantic) AS semantic_digest,
  (SELECT count(*) FROM sources) AS source_link_count,
  (SELECT count(DISTINCT canonical_record) FROM sources)
    AS distinct_source_link_count,
  (SELECT md5(
    string_agg(canonical_record, chr(30) ORDER BY canonical_record)
  ) FROM sources) AS source_digest,
  (SELECT count(*) FROM semantic
    WHERE NOT EXISTS (
      SELECT 1 FROM sources
      WHERE sources.observation_id=semantic.observation_id
    )) AS observations_without_source
FROM snapshot
GROUP BY snapshot.id,snapshot.release_label,snapshot.status,
         snapshot.source_document_ids
""".strip()


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://{}:{}@{}:{}/{}".format(
            os.environ.get("PGUSER", "mdopendata"),
            os.environ.get("PGPASSWORD", "mdopendata_dev"),
            os.environ.get("PGHOST", "127.0.0.1"),
            os.environ.get("PGPORT", "55432"),
            os.environ.get("PGDATABASE", "mdopendata"),
        ),
    )


def fetch_actual() -> dict[str, Any]:
    with psycopg.connect(
        database_url(), connect_timeout=5
    ) as connection:
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            with connection.cursor() as cursor:
                cursor.execute(verification_sql())
                columns = [item.name for item in cursor.description]
                row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"Snapshot {SNAPSHOT_ID} was not found")
            connection.rollback()
    return dict(zip(columns, row))


def normalize_actual(actual: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (
            int(value)
            if key in {
                "snapshot_id",
                "snapshot_observation_count",
                "observation_count",
                "distinct_semantic_count",
                "source_link_count",
                "distinct_source_link_count",
                "observations_without_source",
            }
            else [int(item) for item in value]
            if key == "source_document_ids"
            else value
        )
        for key, value in actual.items()
    }


def build_report(
    expected: dict[str, Any],
    actual: dict[str, Any],
    shadow: dict[str, Any],
) -> dict[str, Any]:
    actual = normalize_actual(actual)
    controls = {
        "snapshot_is_published": actual["status"] == "published",
        "target_document_is_member": DOCUMENT_ID
        in actual["source_document_ids"],
        "observation_count_matches": (
            actual["observation_count"] == expected["observation_count"]
        ),
        "semantic_keys_are_unique": (
            actual["distinct_semantic_count"]
            == actual["observation_count"]
        ),
        "digest_algorithm_matches": (
            actual["digest_algorithm"] == expected["digest_algorithm"]
        ),
        "semantic_set_matches": (
            actual["semantic_digest"] == expected["semantic_digest"]
        ),
        "source_link_count_matches": (
            actual["source_link_count"] == expected["source_link_count"]
        ),
        "source_links_are_unique": (
            actual["distinct_source_link_count"]
            == actual["source_link_count"]
        ),
        "source_set_matches": (
            actual["source_digest"] == expected["source_digest"]
        ),
        "every_observation_has_source": (
            actual["observations_without_source"] == 0
        ),
    }
    return {
        "schema_version": 1,
        "artifact_type": "live_publication_verification",
        "artifact_key": (
            "ctown-budget-2026-2027:"
            "live-publication-verification:snapshot-3"
        ),
        "document_key": shadow["document_key"],
        "source_sha256": shadow["source_sha256"],
        "snapshot_id": SNAPSHOT_ID,
        "document_id": DOCUMENT_ID,
        "transaction_mode": "read_only",
        "database_write_count": 0,
        "expected": expected,
        "actual": actual,
        "controls": controls,
        "passed": all(controls.values()),
    }


def write_atomic(path: Path, body: bytes) -> str:
    if path.exists():
        return "unchanged" if path.read_bytes() == body else "conflict"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return "created"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow", type=Path, default=SHADOW_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--print-sql", action="store_true")
    parser.add_argument("--expected-only", action="store_true")
    parser.add_argument("--actual-summary-json")
    parser.add_argument("--actual-summary-base64")
    args = parser.parse_args()
    if args.print_sql:
        print(verification_sql())
        return 0
    shadow = load(args.shadow)
    manifest = load(args.manifest)
    expected = expected_summary(shadow, manifest)
    if args.expected_only:
        print(json.dumps(expected, sort_keys=True))
        return 0
    if args.actual_summary_json:
        actual = json.loads(args.actual_summary_json)
    elif args.actual_summary_base64:
        actual = json.loads(
            base64.b64decode(args.actual_summary_base64).decode("utf-8")
        )
    else:
        actual = fetch_actual()
    report = build_report(expected, actual, shadow)
    status = write_atomic(args.output, canonical_bytes(report))
    if status == "conflict":
        raise RuntimeError(
            f"Refusing to replace differing verification: {args.output}"
        )
    print(json.dumps({
        "status": status,
        "output": args.output.relative_to(ROOT).as_posix(),
        "passed": report["passed"],
        "controls": report["controls"],
    }, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Import controlled Charlottetown financial-statement raw extraction artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/financial-statements/charlottetown"
REGISTRY_PATH = DATA / "source-document-registry.json"
EXTRACTOR_VERSION = "charlottetown-financial-statements-raw-v1"
EXPECTED_COUNTS = {
    "source_document": 8,
    "source_page": 188,
    "source_table": 139,
    "source_table_page": 139,
    "source_table_column": 551,
    "source_table_row": 4852,
    "source_table_cell": 10085,
    "import_batch": 8,
}
PROTECTED_TABLES = (
    "financial_observation",
    "publication_observation",
    "publication_snapshot",
)


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"),
        os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"),
        os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, float):
        return format(Decimal(str(value)).normalize(), "f")
    if isinstance(value, (date, datetime)):
        return str(value)
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def load_controlled_artifacts() -> dict[str, Any]:
    registry = read_json(REGISTRY_PATH)
    documents = registry["documents"]
    if len(documents) != EXPECTED_COUNTS["source_document"]:
        raise RuntimeError(f"Expected 8 registry documents, found {len(documents)}")

    result: dict[str, Any] = {"registry": registry, "documents": []}
    all_keys: dict[str, set[str]] = {
        "document": set(), "page": set(), "table": set(), "column": set(), "row": set(), "cell": set()
    }
    totals: Counter[str] = Counter()

    for document in documents:
        key = document["document_key"]
        if key in all_keys["document"]:
            raise RuntimeError(f"Duplicate document key: {key}")
        all_keys["document"].add(key)
        source_path = ROOT / document["source_file"]
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest != document["sha256"]:
            raise RuntimeError(f"PDF hash mismatch: {key}")
        document_root = DATA / key
        pages = read_json(document_root / "page_inventory.json")["records"]
        tables = read_json(document_root / "table_manifest.json")["records"]
        raw_root = document_root / "raw-tables"
        table_pages = read_json(raw_root / "source_table_pages.json")["records"]
        columns = read_json(raw_root / "source_table_columns.json")["records"]
        rows = read_json(raw_root / "source_table_rows.json")["records"]
        cells = read_json(raw_root / "source_table_cells.json")["records"]

        if len(pages) != document["page_count"]:
            raise RuntimeError(f"Page count mismatch: {key}")
        local = {
            "page": {item["page_key"] for item in pages},
            "table": {item["table_key"] for item in tables},
            "column": {item["column_key"] for item in columns},
            "row": {item["row_key"] for item in rows},
            "cell": {item["cell_key"] for item in cells},
        }
        for kind, records in (("page", pages), ("table", tables), ("column", columns), ("row", rows), ("cell", cells)):
            if len(local[kind]) != len(records):
                raise RuntimeError(f"Duplicate {kind} key in {key}")
            overlap = all_keys[kind] & local[kind]
            if overlap:
                raise RuntimeError(f"Cross-document duplicate {kind} key: {sorted(overlap)[0]}")
            all_keys[kind].update(local[kind])
        if {item["page_key"] for item in table_pages} - local["page"]:
            raise RuntimeError(f"Unknown table-page page key: {key}")
        if {item["table_key"] for item in table_pages} != local["table"]:
            raise RuntimeError(f"Table-page coverage mismatch: {key}")
        if {item["table_key"] for item in columns} - local["table"]:
            raise RuntimeError(f"Unknown column table key: {key}")
        if {item["table_key"] for item in rows} - local["table"]:
            raise RuntimeError(f"Unknown row table key: {key}")
        if {item["row_key"] for item in cells} - local["row"]:
            raise RuntimeError(f"Unknown cell row key: {key}")
        column_pairs = {(item["table_key"], item["column_index"]) for item in columns}
        if len(column_pairs) != len(columns):
            raise RuntimeError(f"Duplicate table column index: {key}")
        if {(item["table_key"], item["column_index"]) for item in cells} - column_pairs:
            raise RuntimeError(f"Unknown cell column index: {key}")
        cell_pairs = {(item["row_key"], item["column_index"]) for item in cells}
        if len(cell_pairs) != len(cells):
            raise RuntimeError(f"Duplicate row-column cell: {key}")

        totals.update({
            "source_document": 1,
            "source_page": len(pages),
            "source_table": len(tables),
            "source_table_page": len(table_pages),
            "source_table_column": len(columns),
            "source_table_row": len(rows),
            "source_table_cell": len(cells),
            "import_batch": 1,
        })
        result["documents"].append({
            "registry": document, "pages": pages, "tables": tables, "table_pages": table_pages,
            "columns": columns, "rows": rows, "cells": cells,
        })

    if dict(totals) != EXPECTED_COUNTS:
        raise RuntimeError(f"Artifact count mismatch: expected {EXPECTED_COUNTS}, found {dict(totals)}")
    result["artifact_counts"] = dict(totals)
    result["artifact_sha256"] = canonical_hash({
        "registry": registry,
        "documents": [{name: item[name] for name in ("pages", "tables", "table_pages", "columns", "rows", "cells")}
                      for item in result["documents"]],
    })
    return result


def fetch_counts(cur: psycopg.Cursor) -> dict[str, int]:
    names = tuple(EXPECTED_COUNTS) + PROTECTED_TABLES
    counts: dict[str, int] = {}
    for name in names:
        cur.execute(f"SELECT count(*) FROM budget.{name}")
        counts[name] = int(cur.fetchone()[0])
    return counts


def one(cur: psycopg.Cursor, sql: str, params: tuple[Any, ...]) -> tuple[Any, ...]:
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Expected database row for {params!r}")
    return row


def insert_or_match(
    cur: psycopg.Cursor,
    insert_sql: str,
    insert_params: tuple[Any, ...],
    select_sql: str,
    select_params: tuple[Any, ...],
    expected: tuple[Any, ...],
    label: str,
) -> tuple[int, bool]:
    cur.execute(insert_sql, insert_params)
    inserted = cur.fetchone()
    row = one(cur, select_sql, select_params)
    row_id, actual = int(row[0]), tuple(json_value(value) for value in row[1:])
    normalized_expected = tuple(json_value(value) for value in expected)
    if actual != normalized_expected:
        raise RuntimeError(f"Immutable conflict for {label}: expected {normalized_expected!r}, found {actual!r}")
    return row_id, inserted is not None


def confidence(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)) / Decimal("100")


def import_document(cur: psycopg.Cursor, municipality_id: int, bundle: dict[str, Any], artifact_sha: str) -> Counter[str]:
    document = bundle["registry"]
    document_id, inserted = insert_or_match(
        cur,
        """INSERT INTO budget.source_document
             (municipality_id,title,document_kind,local_path,sha256,page_count,status)
             VALUES(%s,%s,'financial_statement',%s,%s,%s,'extracted')
             ON CONFLICT(sha256) DO NOTHING RETURNING id""",
        (municipality_id, document["source_title"], document["source_file"], document["sha256"], document["page_count"]),
        """SELECT id,municipality_id,title,document_kind,local_path,sha256,page_count,status
             FROM budget.source_document WHERE sha256=%s""",
        (document["sha256"],),
        (municipality_id, document["source_title"], "financial_statement", document["source_file"], document["sha256"], document["page_count"], "extracted"),
        document["document_key"],
    )
    inserted_counts: Counter[str] = Counter({"source_document": int(inserted)})

    page_ids: dict[str, int] = {}
    for page in bundle["pages"]:
        page_confidence = confidence(page.get("ocr_mean_confidence"))
        page_id, was_inserted = insert_or_match(
            cur,
            """INSERT INTO budget.source_page
                 (document_id,pdf_page_number,printed_page_label,section_label,content_type,extraction_method,
                  extractor_version,extraction_confidence,review_status)
                 VALUES(%s,%s,%s,%s,%s,'ocr',%s,%s,'unreviewed')
                 ON CONFLICT(document_id,pdf_page_number) DO NOTHING RETURNING id""",
            (document_id, page["page_number"], page.get("printed_page_label"), page.get("section"),
             page.get("content_type"), EXTRACTOR_VERSION, page_confidence),
            """SELECT id,pdf_page_number,printed_page_label,section_label,content_type,extraction_method,
                      extractor_version,extraction_confidence,review_status
                 FROM budget.source_page WHERE document_id=%s AND pdf_page_number=%s""",
            (document_id, page["page_number"]),
            (page["page_number"], page.get("printed_page_label"), page.get("section"), page.get("content_type"),
             "ocr", EXTRACTOR_VERSION, page_confidence, "unreviewed"),
            page["page_key"],
        )
        page_ids[page["page_key"]] = page_id
        inserted_counts["source_page"] += int(was_inserted)

    table_ids: dict[str, int] = {}
    for table in bundle["tables"]:
        table_id, was_inserted = insert_or_match(
            cur,
            """INSERT INTO budget.source_table
                 (document_id,table_key,raw_title,table_type,extraction_status,review_status)
                 VALUES(%s,%s,%s,%s,'extracted','unreviewed')
                 ON CONFLICT(document_id,table_key) DO NOTHING RETURNING id""",
            (document_id, table["table_key"], table.get("title_guess"), table.get("table_family")),
            """SELECT id,table_key,raw_title,table_type,extraction_status,review_status
                 FROM budget.source_table WHERE document_id=%s AND table_key=%s""",
            (document_id, table["table_key"]),
            (table["table_key"], table.get("title_guess"), table.get("table_family"), "extracted", "unreviewed"),
            table["table_key"],
        )
        table_ids[table["table_key"]] = table_id
        inserted_counts["source_table"] += int(was_inserted)

    for link in bundle["table_pages"]:
        table_id = table_ids[link["table_key"]]
        page_id = page_ids[link["page_key"]]
        cur.execute(
            """INSERT INTO budget.source_table_page(source_table_id,source_page_id,page_order,page_role)
               VALUES(%s,%s,1,'body') ON CONFLICT(source_table_id,source_page_id) DO NOTHING RETURNING source_table_id""",
            (table_id, page_id),
        )
        was_inserted = cur.fetchone() is not None
        row = one(cur, """SELECT page_order,page_role FROM budget.source_table_page
                            WHERE source_table_id=%s AND source_page_id=%s""", (table_id, page_id))
        if tuple(row) != (1, "body"):
            raise RuntimeError(f"Immutable conflict for table page {link['table_key']}")
        inserted_counts["source_table_page"] += int(was_inserted)

    column_ids: dict[tuple[str, int], int] = {}
    for column in bundle["columns"]:
        table_id = table_ids[column["table_key"]]
        column_id, was_inserted = insert_or_match(
            cur,
            """INSERT INTO budget.source_table_column
                 (source_table_id,column_key,column_index,raw_header,column_role,review_status)
                 VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(source_table_id,column_index) DO NOTHING RETURNING id""",
            (table_id, column["column_key"], column["column_index"], column.get("raw_header"),
             column.get("column_role"), column.get("review_status", "unreviewed")),
            """SELECT id,column_key,column_index,raw_header,column_role,review_status
                 FROM budget.source_table_column WHERE source_table_id=%s AND column_index=%s""",
            (table_id, column["column_index"]),
            (column["column_key"], column["column_index"], column.get("raw_header"),
             column.get("column_role"), column.get("review_status", "unreviewed")),
            column["column_key"],
        )
        column_ids[(column["table_key"], column["column_index"])] = column_id
        inserted_counts["source_table_column"] += int(was_inserted)

    row_ids: dict[str, int] = {}
    for row in bundle["rows"]:
        table_id = table_ids[row["table_key"]]
        row_confidence = confidence(row.get("parser_confidence"))
        row_id, was_inserted = insert_or_match(
            cur,
            """INSERT INTO budget.source_table_row
                 (source_table_id,row_key,row_index,raw_text,raw_label,bbox,parser_confidence)
                 VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(source_table_id,row_key) DO NOTHING RETURNING id""",
            (table_id, row["row_key"], row["row_index"], row["raw_text"], row.get("raw_label_candidate"),
             row.get("bbox"), row_confidence),
            """SELECT id,row_key,row_index,raw_text,raw_label,bbox,parser_confidence
                 FROM budget.source_table_row WHERE source_table_id=%s AND row_key=%s""",
            (table_id, row["row_key"]),
            (row["row_key"], row["row_index"], row["raw_text"], row.get("raw_label_candidate"),
             row.get("bbox"), row_confidence),
            row["row_key"],
        )
        row_ids[row["row_key"]] = row_id
        inserted_counts["source_table_row"] += int(was_inserted)

    for cell in bundle["cells"]:
        cell_confidence = confidence(cell.get("parser_confidence"))
        row_id = row_ids[cell["row_key"]]
        column_id = column_ids[(cell["table_key"], cell["column_index"])]
        _, was_inserted = insert_or_match(
            cur,
            """INSERT INTO budget.source_table_cell
                 (source_row_id,source_table_column_id,raw_text,bbox,parse_status,parser_confidence)
                 VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(source_row_id,source_table_column_id) DO NOTHING RETURNING id""",
            (row_id, column_id, cell["raw_text"], cell.get("bbox"), cell.get("parse_status", "unparsed"), cell_confidence),
            """SELECT id,raw_text,bbox,parse_status,parser_confidence
                 FROM budget.source_table_cell WHERE source_row_id=%s AND source_table_column_id=%s""",
            (row_id, column_id),
            (cell["raw_text"], cell.get("bbox"), cell.get("parse_status", "unparsed"), cell_confidence),
            cell["cell_key"],
        )
        inserted_counts["source_table_cell"] += int(was_inserted)

    metrics = {
        "document_key": document["document_key"],
        "artifact_sha256": artifact_sha,
        "pages": len(bundle["pages"]), "tables": len(bundle["tables"]),
        "columns": len(bundle["columns"]), "rows": len(bundle["rows"]), "cells": len(bundle["cells"]),
    }
    cur.execute(
        """INSERT INTO budget.import_batch
             (document_id,source_sha256,extractor_version,completed_at,status,metrics_json)
           SELECT %s,%s,%s,now(),'completed',%s
           WHERE NOT EXISTS (SELECT 1 FROM budget.import_batch
             WHERE document_id=%s AND source_sha256=%s AND extractor_version=%s AND status='completed')
           RETURNING id""",
        (document_id, document["sha256"], EXTRACTOR_VERSION, Jsonb(metrics),
         document_id, document["sha256"], EXTRACTOR_VERSION),
    )
    inserted_counts["import_batch"] += int(cur.fetchone() is not None)
    batch = one(cur, """SELECT metrics_json FROM budget.import_batch
                         WHERE document_id=%s AND source_sha256=%s AND extractor_version=%s AND status='completed'""",
                (document_id, document["sha256"], EXTRACTOR_VERSION))
    if batch[0] != metrics:
        raise RuntimeError(f"Immutable conflict for import batch {document['document_key']}")
    return inserted_counts


def scoped_database_counts(cur: psycopg.Cursor, shas: list[str]) -> dict[str, int]:
    queries = {
        "source_document": "SELECT count(*) FROM budget.source_document WHERE sha256=ANY(%s)",
        "source_page": "SELECT count(*) FROM budget.source_page p JOIN budget.source_document d ON d.id=p.document_id WHERE d.sha256=ANY(%s)",
        "source_table": "SELECT count(*) FROM budget.source_table t JOIN budget.source_document d ON d.id=t.document_id WHERE d.sha256=ANY(%s)",
        "source_table_page": """SELECT count(*) FROM budget.source_table_page tp JOIN budget.source_table t ON t.id=tp.source_table_id
                                JOIN budget.source_document d ON d.id=t.document_id WHERE d.sha256=ANY(%s)""",
        "source_table_column": """SELECT count(*) FROM budget.source_table_column c JOIN budget.source_table t ON t.id=c.source_table_id
                                  JOIN budget.source_document d ON d.id=t.document_id WHERE d.sha256=ANY(%s)""",
        "source_table_row": """SELECT count(*) FROM budget.source_table_row r JOIN budget.source_table t ON t.id=r.source_table_id
                               JOIN budget.source_document d ON d.id=t.document_id WHERE d.sha256=ANY(%s)""",
        "source_table_cell": """SELECT count(*) FROM budget.source_table_cell c JOIN budget.source_table_row r ON r.id=c.source_row_id
                                JOIN budget.source_table t ON t.id=r.source_table_id JOIN budget.source_document d ON d.id=t.document_id
                                WHERE d.sha256=ANY(%s)""",
        "import_batch": """SELECT count(*) FROM budget.import_batch b JOIN budget.source_document d ON d.id=b.document_id
                           WHERE d.sha256=ANY(%s) AND b.extractor_version=%s AND b.status='completed'""",
    }
    result: dict[str, int] = {}
    for name, sql in queries.items():
        params: tuple[Any, ...] = (shas, EXTRACTOR_VERSION) if name == "import_batch" else (shas,)
        result[name] = int(one(cur, sql, params)[0])
    return result


def run(apply: bool) -> dict[str, Any]:
    artifacts = load_controlled_artifacts()
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            baseline = fetch_counts(cur)
            municipality_id = int(one(cur, "SELECT id FROM budget.municipality WHERE slug=%s", ("charlottetown",))[0])
            inserted: Counter[str] = Counter()
            for bundle in artifacts["documents"]:
                inserted.update(import_document(cur, municipality_id, bundle, artifacts["artifact_sha256"]))
            scoped = scoped_database_counts(cur, [item["registry"]["sha256"] for item in artifacts["documents"]])
            if scoped != EXPECTED_COUNTS:
                raise RuntimeError(f"Database count mismatch: expected {EXPECTED_COUNTS}, found {scoped}")
            current = fetch_counts(cur)
            for name in PROTECTED_TABLES:
                if current[name] != baseline[name]:
                    raise RuntimeError(f"Protected table changed: budget.{name}")
            if apply:
                conn.commit()
                status = "committed"
            else:
                conn.rollback()
                status = "rolled_back"
    return {
        "schema_version": 1,
        "artifact_kind": "financial_statement_gate_5_raw_database_import_result",
        "status": status,
        "extractor_version": EXTRACTOR_VERSION,
        "artifact_sha256": artifacts["artifact_sha256"],
        "artifact_counts": artifacts["artifact_counts"],
        "inserted_counts": {name: inserted[name] for name in EXPECTED_COUNTS},
        "scoped_database_counts": scoped,
        "database_counts_before": baseline,
        "database_counts_after_transaction": current,
        "protected_counts_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit inserts. Default is a rollback-only dry run.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.apply)
    payload = json.dumps(result, indent=2, sort_keys=False) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()

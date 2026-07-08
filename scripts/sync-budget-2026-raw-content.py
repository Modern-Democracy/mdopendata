"""Append the current 2026/2027 raw budget artifacts as immutable full-2 records."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown/2026-2027"
DOCUMENT_SHA = "d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac"
VERSION = "full-2"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def db_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("PGUSER", "mdopendata"), os.environ.get("PGPASSWORD", "mdopendata_dev"),
        os.environ.get("PGHOST", "localhost"), os.environ.get("PGPORT", "54329"),
        os.environ.get("PGDATABASE", "mdopendata"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    tables = load(BASE / "table_manifest.json")["records"]
    rows = load(BASE / "raw-tables/source_table_rows.json")["records"]
    values = load(BASE / "raw-tables/source_values.json")["records"]
    values_by_row: dict[str, list[dict]] = {}
    for value in values: values_by_row.setdefault(value["row_id"], []).append(value)

    with psycopg.connect(db_url()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM budget.source_document WHERE sha256=%s", (DOCUMENT_SHA,))
        document = cursor.fetchone()
        if document is None: raise ValueError("Source document is not imported")
        document_id = document[0]
        cursor.execute("SELECT count(*) FROM budget.publication_snapshot")
        if cursor.fetchone()[0] != 0: raise ValueError("Publication snapshots must remain zero")
        cursor.execute("SELECT count(*) FROM budget.source_table WHERE document_id=%s AND table_key LIKE %s",
                       (document_id, f"%:{VERSION}"))
        if cursor.fetchone()[0] != 0: raise ValueError(f"{VERSION} raw tables already exist")
        cursor.execute("SELECT pdf_page_number,id FROM budget.source_page WHERE document_id=%s", (document_id,))
        pages = dict(cursor.fetchall())
        if len(pages) != 154: raise ValueError("Expected 154 imported source pages")

        table_ids = {}
        for table in tables:
            key = f"{table['table_id']}:{VERSION}"
            cursor.execute("""INSERT INTO budget.source_table
              (document_id,table_key,raw_title,table_type,extraction_status,review_status)
              VALUES(%s,%s,%s,%s,'extracted','approved') RETURNING id""",
              (document_id, key, table.get("title"), table["table_type"]))
            table_id = cursor.fetchone()[0]; table_ids[table["table_id"]] = table_id
            for page_number in range(int(table["page_start"]), int(table["page_end"]) + 1):
                cursor.execute("""INSERT INTO budget.source_table_page(source_table_id,source_page_id,page_order,page_role)
                  VALUES(%s,%s,%s,%s)""", (table_id, pages[page_number], page_number-int(table["page_start"])+1,
                  "single_page" if table["page_start"] == table["page_end"] else ("start" if page_number == table["page_start"] else "continuation")))

        columns = {}
        for table_id in table_ids.values():
            for index, role in [(0, "label"), *[(i, "value") for i in range(1, 10)]]:
                cursor.execute("""INSERT INTO budget.source_table_column
                  (source_table_id,column_key,column_index,column_role,review_status)
                  VALUES(%s,%s,%s,%s,'unreviewed') RETURNING id""", (table_id, f"column-{index}", index, role))
                columns[(table_id,index)] = cursor.fetchone()[0]

        row_ids = {}
        for row in rows:
            table_id = table_ids[row["table_id"]]
            row_values = sorted(values_by_row.get(row["row_id"], []), key=lambda x: x["value_index"])
            style = {"physical_line_number": row["physical_line_number"], "indentation_spaces": row["indentation_spaces"],
                     "row_kind": row["row_kind"], "cells": row["cells"],
                     "value_tokens": [{"value_id": v["value_id"], "char_start": v["char_start"], "char_end": v["char_end"], "value_kind": v["value_kind"]} for v in row_values],
                     "bbox_status": "unavailable", "raw_import_version": VERSION}
            cursor.execute("""INSERT INTO budget.source_table_row
              (source_table_id,row_key,row_index,raw_text,raw_label,indent_level,row_style)
              VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
              (table_id,row["row_id"],row["row_index"],row["raw_text"],row["trimmed_text"],row["indentation_spaces"],Jsonb(style)))
            row_id=cursor.fetchone()[0]; row_ids[row["row_id"]]=row_id
            cursor.execute("""INSERT INTO budget.source_table_cell
              (source_row_id,source_table_column_id,raw_text,parsed_text,parse_status)
              VALUES(%s,%s,%s,%s,'parsed')""", (row_id,columns[(table_id,0)],row["trimmed_text"],row["trimmed_text"]))
            for value in row_values:
                index=int(value["value_index"])
                cursor.execute("""INSERT INTO budget.source_table_cell
                  (source_row_id,source_table_column_id,raw_text,parsed_numeric,parse_status)
                  VALUES(%s,%s,%s,%s,%s)""", (row_id,columns[(table_id,index)],value["raw_value"],value.get("parsed_decimal"),
                  "parsed" if value.get("parsed_decimal") is not None else "ambiguous"))

        metrics={"mode":"append_only_full_raw","source_tables":len(tables),"rows":len(rows),"values":len(values),"version":VERSION}
        cursor.execute("""INSERT INTO budget.import_batch
          (document_id,source_sha256,extractor_version,completed_at,status,metrics_json)
          VALUES(%s,%s,%s,now(),'completed',%s)""",(document_id,DOCUMENT_SHA,VERSION,Jsonb(metrics)))
        if args.dry_run: connection.rollback()
        else: connection.commit()
    print(json.dumps({"dry_run":args.dry_run,"source_tables":len(tables),"rows":len(rows),"values":len(values)},sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())

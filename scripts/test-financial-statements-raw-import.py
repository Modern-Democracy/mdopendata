"""Regression tests for the controlled Gate 5 raw database import."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
IMPORTER_PATH = ROOT / "scripts/import-charlottetown-financial-statements-raw.py"
RESULT_PATH = ROOT / "data/financial-statements/charlottetown/gate-5-raw-database-import-result.json"
IDEMPOTENCE_PATH = ROOT / "data/financial-statements/charlottetown/gate-5-raw-database-idempotence-result.json"

spec = importlib.util.spec_from_file_location("financial_statement_raw_import", IMPORTER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load Gate 5 raw importer")
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class FinancialStatementRawImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = importer.load_controlled_artifacts()
        cls.shas = [bundle["registry"]["sha256"] for bundle in cls.artifacts["documents"]]
        cls.conn = psycopg.connect(importer.db_url())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_01_scoped_counts_equal_controlled_artifacts(self) -> None:
        with self.conn.cursor() as cur:
            actual = importer.scoped_database_counts(cur, self.shas)
        self.assertEqual(importer.EXPECTED_COUNTS, actual)

    def test_02_document_and_page_content_matches(self) -> None:
        with self.conn.cursor() as cur:
            for bundle in self.artifacts["documents"]:
                doc = bundle["registry"]
                cur.execute(
                    """SELECT title,document_kind,local_path,page_count,status
                       FROM budget.source_document WHERE sha256=%s""", (doc["sha256"],)
                )
                self.assertEqual(
                    (doc["source_title"], "financial_statement", doc["source_file"], doc["page_count"], "extracted"),
                    cur.fetchone(),
                )
                cur.execute(
                    """SELECT p.pdf_page_number,p.printed_page_label,p.section_label,p.content_type,
                              p.extraction_method,p.extractor_version,p.extraction_confidence,p.review_status
                       FROM budget.source_page p JOIN budget.source_document d ON d.id=p.document_id
                       WHERE d.sha256=%s ORDER BY p.pdf_page_number""", (doc["sha256"],)
                )
                actual = [tuple(importer.json_value(value) for value in row) for row in cur.fetchall()]
                expected = [tuple(importer.json_value(value) for value in (
                    page["page_number"], page.get("printed_page_label"), page.get("section"), page.get("content_type"),
                    "ocr", importer.EXTRACTOR_VERSION, importer.confidence(page.get("ocr_mean_confidence")), "unreviewed"
                )) for page in bundle["pages"]]
                self.assertEqual(expected, actual)

    def test_03_table_and_column_content_matches(self) -> None:
        expected_tables = []
        expected_table_pages = []
        expected_columns = []
        for bundle in self.artifacts["documents"]:
            sha = bundle["registry"]["sha256"]
            expected_tables.extend((sha, table["table_key"], table.get("title_guess"), table.get("table_family"), "extracted", "unreviewed")
                                   for table in bundle["tables"])
            expected_table_pages.extend((sha, link["table_key"], link["pdf_page_number"], 1, "body")
                                        for link in bundle["table_pages"])
            expected_columns.extend((sha, column["table_key"], column["column_key"], column["column_index"],
                                     column.get("raw_header"), column.get("column_role"), column.get("review_status", "unreviewed"))
                                    for column in bundle["columns"])
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT d.sha256,t.table_key,t.raw_title,t.table_type,t.extraction_status,t.review_status
                   FROM budget.source_table t JOIN budget.source_document d ON d.id=t.document_id
                   WHERE d.sha256=ANY(%s) ORDER BY d.sha256,t.table_key""", (self.shas,)
            )
            actual_tables = cur.fetchall()
            cur.execute(
                """SELECT d.sha256,t.table_key,p.pdf_page_number,tp.page_order,tp.page_role
                   FROM budget.source_table_page tp JOIN budget.source_table t ON t.id=tp.source_table_id
                   JOIN budget.source_page p ON p.id=tp.source_page_id JOIN budget.source_document d ON d.id=t.document_id
                   WHERE d.sha256=ANY(%s) ORDER BY d.sha256,t.table_key""", (self.shas,)
            )
            actual_table_pages = cur.fetchall()
            cur.execute(
                """SELECT d.sha256,t.table_key,c.column_key,c.column_index,c.raw_header,c.column_role,c.review_status
                   FROM budget.source_table_column c JOIN budget.source_table t ON t.id=c.source_table_id
                   JOIN budget.source_document d ON d.id=t.document_id WHERE d.sha256=ANY(%s)
                   ORDER BY d.sha256,t.table_key,c.column_index""", (self.shas,)
            )
            actual_columns = cur.fetchall()
        self.assertEqual(sorted(expected_tables), actual_tables)
        self.assertEqual(sorted(expected_table_pages), actual_table_pages)
        self.assertEqual(sorted(expected_columns, key=lambda row: (row[0], row[1], row[3])), actual_columns)

    def test_04_row_content_matches(self) -> None:
        expected = []
        for bundle in self.artifacts["documents"]:
            sha = bundle["registry"]["sha256"]
            expected.extend(tuple(importer.json_value(value) for value in (
                sha, row["table_key"], row["row_key"], row["row_index"], row["raw_text"],
                row.get("raw_label_candidate"), row.get("bbox"), importer.confidence(row.get("parser_confidence"))
            )) for row in bundle["rows"])
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT d.sha256,t.table_key,r.row_key,r.row_index,r.raw_text,r.raw_label,r.bbox,r.parser_confidence
                   FROM budget.source_table_row r JOIN budget.source_table t ON t.id=r.source_table_id
                   JOIN budget.source_document d ON d.id=t.document_id WHERE d.sha256=ANY(%s)
                   ORDER BY d.sha256,t.table_key,r.row_index""", (self.shas,)
            )
            actual = [tuple(importer.json_value(value) for value in row) for row in cur.fetchall()]
        self.assertEqual(sorted(expected, key=lambda row: (row[0], row[1], row[3])), actual)

    def test_05_cell_content_and_composite_identity_matches(self) -> None:
        expected = []
        row_order = {}
        for bundle in self.artifacts["documents"]:
            sha = bundle["registry"]["sha256"]
            row_order.update({row["row_key"]: row["row_index"] for row in bundle["rows"]})
            expected.extend(tuple(importer.json_value(value) for value in (
                sha, cell["table_key"], cell["row_key"], cell["column_index"], cell["raw_text"],
                cell.get("bbox"), cell.get("parse_status", "unparsed"),
                importer.confidence(cell.get("parser_confidence"))
            )) for cell in bundle["cells"])
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT d.sha256,t.table_key,r.row_key,col.column_index,c.raw_text,c.bbox,c.parse_status,c.parser_confidence
                   FROM budget.source_table_cell c JOIN budget.source_table_row r ON r.id=c.source_row_id
                   JOIN budget.source_table_column col ON col.id=c.source_table_column_id
                   JOIN budget.source_table t ON t.id=r.source_table_id JOIN budget.source_document d ON d.id=t.document_id
                   WHERE d.sha256=ANY(%s) ORDER BY d.sha256,t.table_key,r.row_index,col.column_index""", (self.shas,)
            )
            actual = [tuple(importer.json_value(value) for value in row) for row in cur.fetchall()]
        self.assertEqual(sorted(expected, key=lambda row: (row[0], row[1], row_order[row[2]], row[3])), actual)

    def test_06_result_artifacts_prove_counts_and_idempotence(self) -> None:
        result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        rerun = json.loads(IDEMPOTENCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual("committed", result["status"])
        self.assertEqual(importer.EXPECTED_COUNTS, result["inserted_counts"])
        self.assertTrue(result["protected_counts_unchanged"])
        self.assertEqual("committed", rerun["status"])
        self.assertEqual({name: 0 for name in importer.EXPECTED_COUNTS}, rerun["inserted_counts"])
        self.assertEqual(importer.EXPECTED_COUNTS, rerun["scoped_database_counts"])
        self.assertEqual(result["database_counts_after_transaction"], rerun["database_counts_before"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

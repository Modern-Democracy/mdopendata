#!/usr/bin/env python3
"""First-pass classifier for Charlottetown budget PDFs.

This script intentionally avoids normalized budget semantics. It captures raw
page text and page/table manifests to support later schema design.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


MONEY_RE = re.compile(r"\$?\(?-?\d[\d,]*(?:\.\d{2})?\)?")
YEAR_RE = re.compile(r"20\d{2}\s*/\s*20\d{2}|20\d{2}\s*/\s*\d{2}|20\d{2}-20\d{2}|20\d{2}")


@dataclass
class PageRecord:
    page_number: int
    source_page_label: str
    section: str
    subsection: str | None
    title_guess: str | None
    content_type: str
    has_table: bool
    has_chart: bool
    has_project_profile: bool
    has_rate_schedule: bool
    has_debt_schedule: bool
    extraction_priority: str
    line_count: int
    numeric_token_count: int
    year_tokens: list[str]
    notes: list[str]


@dataclass
class TableRecord:
    table_id: str
    page_start: int
    page_end: int
    title: str
    table_type: str
    section: str
    subsection: str | None
    entity: str | None
    department: str | None
    columns_observed: list[str]
    numeric_years: list[str]
    row_count_estimate: int
    confidence: str
    needs_manual_review: bool
    notes: list[str]


def run_text_command(pdf: Path, first_page: int, last_page: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-f", str(first_page), "-l", str(last_page), "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.replace("\x0c", "").rstrip()


def page_count(pdf: Path) -> int:
    result = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True)
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not read PDF page count from pdfinfo output")
    return int(match.group(1))


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def title_guess(lines: list[str]) -> str | None:
    skip = {
        "city of charlottetown",
        "2026/2027 operating budget",
        "2026/2027 capital budget",
        "detailed breakdown of budget item",
    }
    for line in lines[:12]:
        lowered = line.lower()
        if lowered in skip or re.fullmatch(r"\d+", line):
            continue
        if len(line) > 2:
            return re.sub(r"\s+", " ", line)
    return None


def section_for_page(page: int) -> tuple[str, str | None]:
    ranges = [
        (1, 3, "Front matter", None),
        (4, 6, "Introduction", None),
        (7, 8, "Strategic Plan", None),
        (9, 17, "Budget Overview", None),
        (18, 24, "Operating Budget", "Overview"),
        (25, 33, "Operating Budget", "City Government"),
        (34, 41, "Operating Budget", "Economic, Tourism and Cultural Development"),
        (42, 46, "Operating Budget", "Environment and Sustainability"),
        (47, 50, "Operating Budget", "Finance"),
        (51, 55, "Operating Budget", "Fire"),
        (56, 60, "Operating Budget", "Human Resources"),
        (61, 64, "Operating Budget", "Mayor and Council"),
        (65, 74, "Operating Budget", "Parks and Recreation"),
        (75, 80, "Operating Budget", "Planning and Heritage"),
        (81, 85, "Operating Budget", "Police"),
        (86, 92, "Operating Budget", "Public Works"),
        (93, 100, "Operating Budget", "Water and Sewer"),
        (101, 104, "Operating Budget", "Eastlink Centre"),
        (105, 108, "Operating Budget", "Bell Aliant Centre"),
        (109, 110, "Capital Budget", "Overview"),
        (111, 116, "Capital Budget", "Environment and Sustainability"),
        (117, 119, "Capital Budget", "Fire"),
        (120, 121, "Capital Budget", "Information Technology"),
        (122, 126, "Capital Budget", "Parks and Recreation"),
        (127, 132, "Capital Budget", "Police"),
        (133, 143, "Capital Budget", "Public Works"),
        (144, 144, "Capital Budget", "Water and Sewer"),
        (145, 146, "Capital Budget", "Eastlink Centre"),
        (147, 147, "Capital Budget", "Bell Aliant Centre"),
        (148, 149, "Appendix", "Property Taxes"),
        (150, 151, "Appendix", "Fiscal Services Long Term Debt"),
        (152, 153, "Appendix", "Water and Sewer Long Term Debt"),
        (154, 154, "Back matter", None),
    ]
    for start, end, section, subsection in ranges:
        if start <= page <= end:
            return section, subsection
    return "Unknown", None


def classify_page(page: int, text: str) -> PageRecord:
    lines = clean_lines(text)
    section, subsection = section_for_page(page)
    lower = text.lower()
    numeric_count = len(MONEY_RE.findall(text))
    years = sorted(set(YEAR_RE.findall(text)))
    has_chart = page in {18, 19} or (" chart" in lower and section not in {"Front matter"})
    has_project_profile = all(marker in text for marker in ["Department:", "Project:", "Project Description"])
    has_rate_schedule = section != "Front matter" and (
        "rates per $100" in lower
        or "base rate" in lower
        or "consumption rate" in lower
        or " x $" in lower and "per $100" in lower
    )
    has_debt_schedule = section == "Appendix" and "servicing of long term debt" in lower
    table_eligible = section in {"Operating Budget", "Capital Budget", "Appendix"}
    amount_line_count = sum(
        1
        for line in text.splitlines()
        if re.search(r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b", line)
        or re.search(r"\$\s*\d", line)
    )
    detailed_continuation_signal = (
        section == "Operating Budget"
        and amount_line_count >= 3
    )
    has_budget_column_signal = any(
        signal in text
        for signal in [
            "2025/2026",
            "2026/2027",
            "2023/2024",
            "2024/2025",
            "2023/24",
            "2024/25",
            "2025/26",
            "2026/27",
            "Budget",
            "Forecast",
            "Revenue",
            "Expenses",
        ]
    )
    has_table = table_eligible and (
        numeric_count >= 8 and has_budget_column_signal
        or detailed_continuation_signal
        or has_rate_schedule
        or has_debt_schedule
    )
    if has_project_profile:
        content_type = "project_profile"
    elif has_debt_schedule:
        content_type = "debt_schedule"
    elif has_rate_schedule:
        content_type = "rate_schedule"
    elif has_chart and has_table:
        content_type = "chart_with_data_table"
    elif has_table:
        content_type = "table"
    elif section in {"Introduction", "Strategic Plan", "Budget Overview"}:
        content_type = "text"
    else:
        content_type = "section_divider_or_text"

    if has_debt_schedule or has_rate_schedule or has_table:
        priority = "high"
    elif has_project_profile:
        priority = "medium"
    elif section in {"Front matter", "Back matter"}:
        priority = "low"
    else:
        priority = "medium"

    notes: list[str] = []
    if has_chart:
        notes.append("chart or chart-derived summary present")
    if has_project_profile:
        notes.append("capital project profile with narrative fields")
    if not lines:
        notes.append("no extractable text detected")

    return PageRecord(
        page_number=page,
        source_page_label=str(page),
        section=section,
        subsection=subsection,
        title_guess=title_guess(lines),
        content_type=content_type,
        has_table=has_table,
        has_chart=has_chart,
        has_project_profile=has_project_profile,
        has_rate_schedule=has_rate_schedule,
        has_debt_schedule=has_debt_schedule,
        extraction_priority=priority,
        line_count=len(lines),
        numeric_token_count=numeric_count,
        year_tokens=years,
        notes=notes,
    )


def observed_columns(text: str, content_type: str) -> list[str]:
    if content_type == "debt_schedule":
        return ["debt_instrument", "2026_balance", "2026_2027_principal", "2026_2027_interest"]
    if content_type == "rate_schedule":
        return ["rate_label", "rate_or_amount"]
    if "2025/2026" in text and "Forecast" in text and "2026/2027" in text:
        return ["item", "2025_2026_budget", "2025_2026_forecast", "2026_2027_budget"]
    if "2024/2025" in text and "Forecast" in text and "2025/2026" in text:
        return ["item", "2024_2025_budget", "2024_2025_forecast", "2025_2026_budget"]
    if "2023/2024" in text and "Forecast" in text and "2024/2025" in text:
        return ["item", "2023_2024_budget", "2023_2024_forecast", "2024_2025_budget"]
    if "2025/26" in text and "Forecast" in text and "2026/27" in text:
        return ["item", "2025_2026_budget", "2025_2026_forecast", "2026_2027_budget"]
    if "2024/25" in text and "Forecast" in text and "2025/26" in text:
        return ["item", "2024_2025_budget", "2024_2025_forecast", "2025_2026_budget"]
    if "2023/24" in text and "Forecast" in text and "2024/25" in text:
        return ["item", "2023_2024_budget", "2023_2024_forecast", "2024_2025_budget"]
    if "2024/25" in text and "2025/26" in text:
        return ["item", "2024_2025_capital_budget", "2025_2026_capital_budget"]
    if "2023/24" in text and "2024/25" in text:
        return ["item", "2023_2024_capital_budget", "2024_2025_capital_budget"]
    if "2025/26" in text and "2026/27" in text:
        return ["item", "2025_2026_capital_budget", "2026_2027_capital_budget"]
    if "Budget" in text and "Variance" in text:
        return ["item", "2026_2027_budget", "2025_2026_budget", "variance_percent"]
    if "Budget" in text:
        return ["item", "budget"]
    return ["raw_label", "raw_value"]


def table_type(record: PageRecord, text: str) -> str:
    if record.has_debt_schedule:
        return "debt_schedule"
    if record.has_rate_schedule:
        return "tax_or_utility_rate_schedule"
    if record.has_chart:
        return "chart_source_table"
    if record.section == "Capital Budget":
        if record.has_project_profile:
            return "capital_project_profile"
        return "capital_budget_table"
    if record.subsection in {"Eastlink Centre", "Bell Aliant Centre"}:
        return "third_party_facility_operating_budget"
    if record.section == "Operating Budget":
        if "Detailed Breakdown of Budget Item" in text:
            return "operating_budget_detail"
        return "operating_budget_summary"
    if record.section == "Appendix":
        return "appendix_table"
    return "table_candidate"


def entity_for(record: PageRecord) -> str | None:
    if record.subsection == "Water and Sewer":
        return "Charlottetown Water and Sewer"
    if record.subsection == "Eastlink Centre":
        return "Eastlink Centre"
    if record.subsection == "Bell Aliant Centre":
        return "Bell Aliant Centre"
    if record.section in {"Operating Budget", "Capital Budget", "Appendix"}:
        return "City of Charlottetown"
    return None


def table_manifest(page_records: list[PageRecord], page_text: dict[int, str]) -> list[TableRecord]:
    tables: list[TableRecord] = []
    for record in page_records:
        if not record.has_table and not record.has_project_profile:
            continue
        text = page_text[record.page_number]
        lines = clean_lines(text)
        row_estimate = sum(1 for line in lines if MONEY_RE.search(line))
        ttype = table_type(record, text)
        tables.append(
            TableRecord(
                table_id=f"ctown_budget_2026_2027_p{record.page_number:03d}",
                page_start=record.page_number,
                page_end=record.page_number,
                title=record.title_guess or f"Page {record.page_number}",
                table_type=ttype,
                section=record.section,
                subsection=record.subsection,
                entity=entity_for(record),
                department=record.subsection if record.section in {"Operating Budget", "Capital Budget"} else None,
                columns_observed=observed_columns(text, record.content_type),
                numeric_years=record.year_tokens,
                row_count_estimate=row_estimate,
                confidence="medium" if record.has_table else "low",
                needs_manual_review=record.has_project_profile or row_estimate == 0 or record.content_type == "chart_with_data_table",
                notes=record.notes,
            )
        )
    return tables


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    pdf = args.pdf
    out_dir = args.out
    raw_dir = out_dir / "raw-pages"
    raw_dir.mkdir(parents=True, exist_ok=True)

    pages = page_count(pdf)
    page_text: dict[int, str] = {}
    records: list[PageRecord] = []
    for page in range(1, pages + 1):
        text = run_text_command(pdf, page, page)
        page_text[page] = text
        (raw_dir / f"page-{page:03d}.txt").write_text(text + "\n", encoding="utf-8")
        records.append(classify_page(page, text))

    tables = table_manifest(records, page_text)
    inventory_payload = {
        "schema_version": 1,
        "source_pdf": str(pdf.as_posix()),
        "page_count": pages,
        "records": [asdict(record) for record in records],
    }
    table_payload = {
        "schema_version": 1,
        "source_pdf": str(pdf.as_posix()),
        "table_count": len(tables),
        "records": [asdict(table) for table in tables],
    }
    summary_payload = {
        "schema_version": 1,
        "source_pdf": str(pdf.as_posix()),
        "page_count": pages,
        "raw_page_text_dir": str(raw_dir.as_posix()),
        "page_inventory": "page_inventory.json",
        "table_manifest": "table_manifest.json",
        "counts": {
            "pages_by_section": count_by(records, "section"),
            "pages_by_content_type": count_by(records, "content_type"),
            "tables_by_type": count_by(tables, "table_type"),
            "high_priority_pages": sum(1 for record in records if record.extraction_priority == "high"),
            "manual_review_tables": sum(1 for table in tables if table.needs_manual_review),
        },
    }

    write_json(out_dir / "page_inventory.json", inventory_payload)
    write_json(out_dir / "table_manifest.json", table_payload)
    write_json(out_dir / "ingestion_summary.json", summary_payload)


def count_by(items: list[object], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = getattr(item, attr)
        key = "null" if key is None else str(key)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()

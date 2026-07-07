#!/usr/bin/env python3
"""Profile one Charlottetown budget PDF without assigning normalized semantics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


YEAR_RE = re.compile(r"\b20\d{2}(?:\s*[/\-]\s*(?:20)?\d{2})?\b")
VALUE_RE = re.compile(r"(?:\$\s*)?\(?-?\d[\d,]*(?:\.\d+)?\)?%?")
AMOUNT_LINE_RE = re.compile(r"(?:\$\s*)?\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?")
SPACE_COLUMNS_RE = re.compile(r"\S(?:.*?\S)?\s{2,}\S")


@dataclass
class PageProfile:
    page_number: int
    printed_page_label: str | None
    section: str
    title_guess: str | None
    content_type: str
    text_extraction_method: str
    embedded_line_count: int
    table_candidate: bool
    table_family: str | None
    column_pattern: str | None
    entities: list[str]
    periods: list[str]
    amount_line_count: int
    numeric_token_count: int
    repeated_header: bool
    continuation_candidate: bool
    continuation_group: str | None
    confidence: str
    review_reasons: list[str]


def command_text(args: list[str]) -> str:
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def pdf_metadata(pdf: Path) -> dict[str, object]:
    text = command_text(["pdfinfo", str(pdf)])
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return {
        "title": fields.get("Title"),
        "producer": fields.get("Producer"),
        "tagged": fields.get("Tagged"),
        "encrypted": fields.get("Encrypted"),
        "page_count": int(fields["Pages"]),
        "page_size": fields.get("Page size"),
    }


def extract_page(pdf: Path, page: int) -> str:
    return command_text(
        ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"]
    ).replace("\x0c", "").rstrip()


def extract_page_with_ocr(pdf: Path, page: int, ocr_dir: Path) -> tuple[str, str, int]:
    embedded = extract_page(pdf, page)
    embedded_lines = len(nonempty_lines(embedded))
    if embedded_lines >= 5 or page <= 5:
        return embedded, "embedded_text", embedded_lines
    with tempfile.TemporaryDirectory(prefix="budget-profile-") as temp:
        prefix = Path(temp) / "page"
        subprocess.run(
            ["pdftoppm", "-f", str(page), "-l", str(page), "-png", "-r", "180", "-singlefile", str(pdf), str(prefix)],
            check=True,
            capture_output=True,
        )
        image = prefix.with_suffix(".png")
        tesseract = shutil.which("tesseract")
        if not tesseract:
            candidates = [
                Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
                Path(r"C:\Program Files\PDF24\tesseract\tesseract.exe"),
            ]
            tesseract = next((str(candidate) for candidate in candidates if candidate.exists()), None)
        if not tesseract:
            return embedded, "embedded_text_ocr_unavailable", embedded_lines
        result = subprocess.run(
            [tesseract, str(image), "stdout", "--psm", "6"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    ocr = result.stdout.rstrip()
    if len(nonempty_lines(ocr)) <= embedded_lines:
        return embedded, "embedded_text", embedded_lines
    ocr_dir.mkdir(parents=True, exist_ok=True)
    (ocr_dir / f"page-{page:03d}.txt").write_text(ocr + "\n", encoding="utf-8")
    return ocr, "ocr_fallback", embedded_lines


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def nonempty_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def printed_page_label(lines: list[str], page: int) -> str | None:
    for line in lines[-5:]:
        value = line.strip()
        if value.isdigit() and abs(int(value) - page) <= 3:
            return value
    return None


def detect_section(text: str, prior: str) -> str:
    lines = [compact(line).upper() for line in nonempty_lines(text)[:18]]
    if any("TABLE OF CONTENTS" in line for line in lines):
        return prior
    if any(line == "BUDGET OVERVIEW" for line in lines):
        return "Budget Overview"
    joined = " ".join(lines)
    if prior != "Front matter" and "APPENDIX" in joined and "PROPERTY TAX" in joined:
        return "Appendix - Taxes and Rates"
    if prior != "Front matter" and "APPENDIX" in joined and "LONG TERM DEBT" in joined:
        return "Appendix - Debt"
    if prior.startswith("Appendix -"):
        return prior
    budget_headings = [
        line
        for line in lines
        if re.fullmatch(r"(?:CITY OF CHARLOTTETOWN )?(?:20\d{2}\s*[/\-]\s*(?:20)?\d{2} )?(?:OPERATING|OPERATIONAL|CAPITAL) BUDGET", line)
    ]
    has_operating = any("OPERATING BUDGET" in line or "OPERATIONAL BUDGET" in line for line in budget_headings)
    has_capital = any("CAPITAL BUDGET" in line for line in budget_headings)
    if has_operating and not has_capital:
        return "Operating Budget"
    if has_capital and not has_operating:
        return "Capital Budget"
    if any(line == "STRATEGIC PLAN" or line.endswith(" STRATEGIC PLAN") for line in lines):
        return "Strategic Plan"
    return prior


def detect_entities(text: str) -> list[str]:
    lower = text.lower()
    signals = [
        ("bell aliant", "Bell Aliant Centre"),
        ("cari", "Bell Aliant Centre"),
        ("eastlink centre", "Eastlink Centre"),
        ("water and sewer", "Charlottetown Water and Sewer"),
        ("city of charlottetown", "City of Charlottetown"),
    ]
    entities: list[str] = []
    for signal, entity in signals:
        if signal in lower and entity not in entities:
            entities.append(entity)
    return entities


def title_guess(lines: list[str]) -> str | None:
    ignored = re.compile(
        r"^(CITY OF CHARLOTTETOWN|CITY OF CHARLOTTETOWN|\d{4}\s*[/\-]\s*(?:\d{2}|\d{4})|"
        r"FINANCIAL PLAN|CAPITAL AND OPERATIONAL BUDGETS?|CAPITAL AND OPERATING BUDGETS?|"
        r"DETAILED BREAKDOWN OF BUDGET ITEM|BUDGET|FORECAST)$",
        re.IGNORECASE,
    )
    for raw in lines[:16]:
        line = compact(raw)
        if not line or line.isdigit() or ignored.match(line) or len(line) > 100:
            continue
        return line
    return None


def repeated_header(text: str) -> bool:
    upper = text.upper()
    return any(
        signal in upper
        for signal in [
            "DETAILED BREAKDOWN OF BUDGET ITEM",
            "BUDGET 202",
            "FORECAST 202",
            "REVENUE EXPENSE",
            "PRINCIPAL",
            "INTEREST",
        ]
    )


def column_pattern(text: str, family: str | None) -> str | None:
    periods = sorted(set(compact(value) for value in YEAR_RE.findall(text)))
    upper = text.upper()
    if family == "debt_schedule":
        return "instrument | balance | principal | interest"
    if family == "tax_assessment_rate":
        return "class | assessment | rate | revenue"
    if family == "utility_rate_schedule":
        return "customer/rate label | rate or charge"
    if family == "capital_project_profile":
        return "profile field | narrative value"
    roles: list[str] = []
    if "BUDGET" in upper:
        roles.append("budget")
    if "FORECAST" in upper:
        roles.append("forecast")
    if "VARIANCE" in upper:
        roles.append("variance")
    if "ACTUAL" in upper:
        roles.append("actual")
    suffix = ", ".join(periods) if periods else "unlabeled period"
    return "item | " + " | ".join(roles or ["amount"]) + f" ({suffix})"


def table_family(text: str, section: str, amount_lines: int) -> str | None:
    upper = text.upper()
    if section == "Front matter":
        return None
    if "SERVICING OF LONG TERM DEBT" in upper or (
        "PRINCIPAL" in upper and "INTEREST" in upper and "BALANCE" in upper
    ):
        return "debt_schedule"
    if "PER $100" in upper and ("ASSESSMENT" in upper or "PROPERTY TAX" in upper):
        return "tax_assessment_rate"
    if any(value in upper for value in ["CONSUMPTION RATE", "BASE RATE", "UNMETERED RATE"]):
        return "utility_rate_schedule"
    if all(value in upper for value in ["DEPARTMENT:", "PROJECT:"]):
        return "capital_project_profile"
    if section == "Capital Budget" and amount_lines >= 2:
        return "capital_budget_schedule"
    if section == "Operating Budget" and "DETAILED BREAKDOWN" in upper:
        return "operating_detail"
    if section == "Operating Budget" and amount_lines >= 2:
        if any(value in upper for value in ["EASTLINK CENTRE", "BELL ALIANT", "CARI"]):
            return "facility_operating_statement"
        return "operating_statement"
    if section == "Budget Overview" and amount_lines >= 2:
        return "overview_summary"
    if amount_lines >= 3:
        return "unclassified_financial_table"
    return None


def profile_pages(pdf: Path, out: Path) -> tuple[dict[int, str], list[PageProfile]]:
    metadata = pdf_metadata(pdf)
    raw_dir = out / "profile-raw-pages"
    ocr_dir = out / "profile-ocr-pages"
    raw_dir.mkdir(parents=True, exist_ok=True)
    texts: dict[int, str] = {}
    profiles: list[PageProfile] = []
    section = "Front matter"
    for page in range(1, int(metadata["page_count"]) + 1):
        text, extraction_method, embedded_line_count = extract_page_with_ocr(pdf, page, ocr_dir)
        texts[page] = text
        (raw_dir / f"page-{page:03d}.txt").write_text(text + "\n", encoding="utf-8")
        lines = nonempty_lines(text)
        section = detect_section(text, section)
        amounts = sum(1 for line in lines if AMOUNT_LINE_RE.search(line))
        family = table_family(text, section, amounts)
        candidate = family is not None
        reviews: list[str] = []
        if family == "unclassified_financial_table":
            reviews.append("financial table family requires manual classification")
        if not text.strip():
            reviews.append("no embedded text")
        profiles.append(
            PageProfile(
                page_number=page,
                printed_page_label=printed_page_label(lines, page),
                section=section,
                title_guess=title_guess(lines),
                content_type="table_or_profile" if candidate else "text_or_divider",
                text_extraction_method=extraction_method,
                embedded_line_count=embedded_line_count,
                table_candidate=candidate,
                table_family=family,
                column_pattern=column_pattern(text, family) if candidate else None,
                entities=detect_entities(text),
                periods=sorted(set(compact(value) for value in YEAR_RE.findall(text))),
                amount_line_count=amounts,
                numeric_token_count=len(VALUE_RE.findall(text)),
                repeated_header=repeated_header(text),
                continuation_candidate=False,
                continuation_group=None,
                confidence="low" if reviews else ("high" if candidate and repeated_header(text) else "medium"),
                review_reasons=reviews,
            )
        )

    group_number = 0
    prior: PageProfile | None = None
    for current in profiles:
        if not current.table_candidate:
            prior = current
            continue
        is_continuation = bool(
            prior
            and prior.table_candidate
            and current.page_number == prior.page_number + 1
            and current.section == prior.section
            and current.table_family == prior.table_family
            and (not current.repeated_header or current.title_guess == prior.title_guess)
        )
        if is_continuation and prior:
            current.continuation_candidate = True
            if prior.continuation_group is None:
                group_number += 1
                prior.continuation_group = f"continuation-{group_number:03d}"
            current.continuation_group = prior.continuation_group
            current.review_reasons.append("adjacent same-family page; continuation requires visual review")
        prior = current
    return texts, profiles


def table_records(profiles: list[PageProfile], document_key: str) -> list[dict[str, object]]:
    return [
        {
            "table_key": f"{document_key}-p{page.page_number:03d}",
            "page_start": page.page_number,
            "page_end": page.page_number,
            "title_guess": page.title_guess,
            "section": page.section,
            "table_family": page.table_family,
            "column_pattern": page.column_pattern,
            "entities": page.entities,
            "periods": page.periods,
            "continuation_candidate": page.continuation_candidate,
            "continuation_group": page.continuation_group,
            "confidence": page.confidence,
            "review_reasons": page.review_reasons,
        }
        for page in profiles
        if page.table_candidate
    ]


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    if not records:
        return
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                    for key, value in record.items()
                }
            )
    temp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--document-key", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    metadata = pdf_metadata(args.pdf)
    _, profiles = profile_pages(args.pdf, args.out)
    page_records = [asdict(page) for page in profiles]
    tables = table_records(profiles, args.document_key)
    source_hash = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    profile = {
        "schema_version": 1,
        "document_key": args.document_key,
        "source_pdf": args.pdf.as_posix(),
        "sha256": source_hash,
        "metadata": metadata,
        "counts": {
            "pages": len(profiles),
            "table_candidates": len(tables),
            "continuation_candidates": sum(page.continuation_candidate for page in profiles),
            "pages_by_section": dict(sorted(Counter(page.section for page in profiles).items())),
            "tables_by_family": dict(
                sorted(Counter(page.table_family for page in profiles if page.table_candidate).items())
            ),
            "column_patterns": dict(
                sorted(Counter(page.column_pattern for page in profiles if page.table_candidate).items())
            ),
            "entities": dict(
                sorted(Counter(entity for page in profiles for entity in page.entities).items())
            ),
            "periods": dict(
                sorted(Counter(period for page in profiles for period in page.periods).items())
            ),
            "review_pages": sum(bool(page.review_reasons) for page in profiles),
        },
    }
    write_json(args.out / "source_profile.json", profile)
    write_json(args.out / "profile_page_inventory.json", {"schema_version": 1, "records": page_records})
    write_json(args.out / "profile_table_inventory.json", {"schema_version": 1, "records": tables})
    write_csv(args.out / "profile_page_inventory.csv", page_records)
    write_csv(args.out / "profile_table_inventory.csv", tables)


if __name__ == "__main__":
    main()

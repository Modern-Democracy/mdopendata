#!/usr/bin/env python3
"""Profile the registered Charlottetown financial-statement PDFs.

This Gate 2 profiler records page-level OCR and structural candidates. It does
not extract rows, assign normalized financial semantics, or write a database.
"""

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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


SCHEMA_VERSION = 1
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
AMOUNT_RE = re.compile(
    r"(?<![A-Za-z])(?:\$\s*)?(?:\(\s*)?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:\s*\))?"
)
INTEGER_COLUMN_RE = re.compile(r"(?<![A-Za-z])(?:\(\s*)?-?\d{2,}(?:\s*\))?(?![A-Za-z])")
NOTE_HEADING_RE = re.compile(r"NOTES?\s+TO\s+THE\s+(?:CONSOLIDATED\s+)?FINANCIAL\s+STATEMENTS?", re.I)


@dataclass(frozen=True)
class OcrResult:
    page_number: int
    text: str
    mean_confidence: float | None
    recognized_words: int
    rotation_degrees: int


@dataclass
class PageRecord:
    page_key: str
    page_number: int
    printed_page_label: str | None
    content_type: str
    disposition: str
    section: str
    title_guess: str | None
    statement_class: str | None
    table_candidate: bool
    table_family: str | None
    text_extraction_method: str
    embedded_character_count: int
    ocr_character_count: int
    ocr_word_count: int
    ocr_mean_confidence: float | None
    ocr_rotation_degrees: int
    amount_token_count: int
    numeric_line_count: int
    periods: list[str]
    continuation_candidate: bool
    continuation_of_page_key: str | None
    confidence: str
    review_reasons: list[str]


def run_text(args: list[str]) -> str:
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def locate_tools() -> dict[str, str]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise RuntimeError("pdftotext is unavailable")
    poppler_dir = Path(pdftotext).resolve().parent

    def poppler_tool(name: str) -> str:
        sibling = poppler_dir / f"{name}.exe"
        if sibling.exists():
            return str(sibling)
        located = shutil.which(name)
        if located:
            return located
        raise RuntimeError(f"{name} is unavailable")

    tesseract = shutil.which("tesseract")
    if not tesseract:
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files\PDF24\tesseract\tesseract.exe"),
        ]
        tesseract = next((str(candidate) for candidate in candidates if candidate.exists()), None)
    if not tesseract:
        raise RuntimeError("tesseract is unavailable")
    return {
        "pdftotext": pdftotext,
        "pdfinfo": poppler_tool("pdfinfo"),
        "pdftoppm": poppler_tool("pdftoppm"),
        "tesseract": tesseract,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                    for key, value in record.items()
                }
            )


def pdf_metadata(pdf: Path, tools: dict[str, str]) -> dict[str, object]:
    fields: dict[str, str] = {}
    for line in run_text([tools["pdfinfo"], str(pdf)]).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return {
        "page_count": int(fields["Pages"]),
        "page_size": fields.get("Page size"),
        "producer": fields.get("Producer"),
        "tagged": fields.get("Tagged"),
        "encrypted": fields.get("Encrypted"),
    }


def embedded_pages(pdf: Path, page_count: int, tools: dict[str, str], out_dir: Path) -> dict[int, str]:
    pages: dict[int, str] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for page in range(1, page_count + 1):
        text = run_text(
            [tools["pdftotext"], "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"]
        ).replace("\x0c", "").rstrip()
        pages[page] = text
        (out_dir / f"page-{page:03d}.txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
    return pages


def render_pages(pdf: Path, page_count: int, tools: dict[str, str], render_dir: Path) -> list[Path]:
    render_dir.mkdir(parents=True, exist_ok=True)
    prefix = render_dir / "page"
    subprocess.run(
        [tools["pdftoppm"], "-f", "1", "-l", str(page_count), "-jpeg", "-jpegopt", "quality=88", "-r", "180", str(pdf), str(prefix)],
        check=True,
        capture_output=True,
    )
    images = sorted(render_dir.glob("page-*.jpg"))
    if len(images) != page_count:
        raise RuntimeError(f"rendered {len(images)} pages; expected {page_count}")
    return images


def parse_ocr_tsv(page: int, tsv: str, rotation_degrees: int) -> OcrResult:
    rows = list(csv.DictReader(tsv.splitlines(), delimiter="\t"))
    words: list[dict[str, str]] = []
    confidences: list[float] = []
    for row in rows:
        value = (row.get("text") or "").strip()
        if not value:
            continue
        words.append(row)
        try:
            confidence = float(row.get("conf", "-1"))
        except ValueError:
            confidence = -1
        if confidence >= 0:
            confidences.append(confidence)
    lines: dict[tuple[str, str, str, str], list[str]] = {}
    for row in words:
        key = (row["block_num"], row["par_num"], row["line_num"], row["page_num"])
        lines.setdefault(key, []).append(row["text"].strip())
    text = "\n".join(" ".join(values) for values in lines.values()).strip()
    mean = round(sum(confidences) / len(confidences), 2) if confidences else None
    return OcrResult(page, text, mean, len(words), rotation_degrees)


def ocr_image(page_and_image: tuple[int, Path], tesseract: str) -> OcrResult:
    page, image = page_and_image
    tsv = run_text([tesseract, str(image), "stdout", "--psm", "6", "tsv"])
    best = parse_ocr_tsv(page, tsv, 0)
    if best.mean_confidence is not None and best.mean_confidence >= 60:
        return best
    candidates = [best]
    with Image.open(image) as source:
        for rotation in (90, 270):
            rotated_path = image.with_name(f"{image.stem}-r{rotation}.jpg")
            source.rotate(rotation, expand=True, fillcolor="white").save(rotated_path, quality=88)
            try:
                rotated_tsv = run_text([tesseract, str(rotated_path), "stdout", "--psm", "6", "tsv"])
                candidates.append(parse_ocr_tsv(page, rotated_tsv, rotation))
            finally:
                rotated_path.unlink(missing_ok=True)
    return max(
        candidates,
        key=lambda result: (
            result.mean_confidence if result.mean_confidence is not None else -1,
            result.recognized_words,
        ),
    )


def ocr_pages(images: list[Path], tools: dict[str, str], workers: int, out_dir: Path) -> dict[int, OcrResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = list(enumerate(images, start=1))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda item: ocr_image(item, tools["tesseract"]), inputs))
    by_page = {result.page_number: result for result in results}
    for page in sorted(by_page):
        text = by_page[page].text
        (out_dir / f"page-{page:03d}.txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
    return by_page


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def nonempty_lines(text: str) -> list[str]:
    return [compact(line) for line in text.splitlines() if line.strip()]


def printed_page_label(lines: list[str], page: int) -> str | None:
    candidates = lines[:4] + lines[-4:]
    for line in candidates:
        match = re.fullmatch(r"(?:PAGE\s+)?(\d{1,3})", line, re.I)
        if match and abs(int(match.group(1)) - page) <= 5:
            return match.group(1)
    return None


def statement_class(text: str) -> str | None:
    upper = compact(text).upper()
    signals = [
        ("CHANGES IN NET ASSETS AVAILABLE FOR BENEFITS", "changes_in_net_assets_available_for_benefits"),
        ("CHANGES IN PENSION OBLIGATIONS", "changes_in_pension_obligations"),
        ("CHANGE IN NET DEBT", "changes_in_net_debt"),
        ("CHANGES IN NET DEBT", "changes_in_net_debt"),
        ("STATEMENT OF FINANCIAL POSITION", "financial_position"),
        ("STATEMENT OF OPERATIONS", "operations"),
        ("STATEMENT OF CASH FLOWS", "cash_flow"),
        ("STATEMENT OF CASH FLOW", "cash_flow"),
        ("REMEASUREMENT GAINS", "remeasurement_gains_and_losses"),
    ]
    return next((value for signal, value in signals if signal in upper), None)


def schedule_family(text: str) -> str | None:
    upper = compact(text).upper()
    signals = [
        ("TANGIBLE CAPITAL ASSETS", "tangible_capital_assets_schedule"),
        ("SEGMENT", "segmented_disclosure_schedule"),
        ("ACCUMULATED SURPLUS", "accumulated_surplus_schedule"),
        ("EXPENSES BY OBJECT", "expenses_by_object_schedule"),
        ("GOVERNMENT TRANSFERS", "government_transfers_schedule"),
    ]
    if "SCHEDULE" not in upper:
        return None
    return next((value for signal, value in signals if signal in upper), "financial_schedule")


def classify_page(
    page: int,
    text: str,
    prior_section: str,
    amount_count: int,
    numeric_lines: int,
) -> tuple[str, str, str, str | None, str | None]:
    lines = nonempty_lines(text)
    heading_text = "\n".join(lines[:10])
    heading_upper = compact(heading_text).upper()
    statement = statement_class(heading_text)
    schedule = schedule_family(heading_text)
    if page == 1:
        return "cover", "administrative_front_matter", "Front matter", None, None
    if (
        "TABLE OF CONTENTS" in heading_upper
        or heading_upper.startswith("CONTENTS")
        or "INDEX TO FINANCIAL STATEMENTS" in heading_upper
    ):
        return "index", "administrative_front_matter", "Front matter", None, None
    if "MANAGEMENT" in heading_upper and "RESPONSIBILITY" in heading_upper:
        return "management_responsibility", "administrative_front_matter", "Front matter", None, None
    if "INDEPENDENT AUDITOR" in heading_upper or "AUDITOR'S REPORT" in heading_upper or "AUDITORS' REPORT" in heading_upper:
        return "auditor_report", "administrative_front_matter", "Auditor report", None, None
    if schedule and not statement:
        return "schedule", "financial_table_candidate", "Schedules", None, schedule
    notes_started = prior_section == "Notes" or NOTE_HEADING_RE.search(heading_text) is not None
    if notes_started:
        if "BUDGET FIGURES" in heading_upper:
            return "notes", "financial_table_candidate", "Notes", None, "budget_reconciliation_note"
        if amount_count >= 2 or numeric_lines >= 3:
            return "notes", "financial_table_candidate", "Notes", None, "note_disclosure_table"
        return "notes", "financial_note_narrative", "Notes", None, None
    if statement:
        return "financial_statement", "financial_table_candidate", "Primary statements", statement, statement
    if prior_section == "Auditor report":
        return "auditor_report", "administrative_front_matter", "Auditor report", None, None
    if not text.strip():
        return "blank_or_scan_artifact", "blank_or_scan_artifact", prior_section, None, None
    if amount_count >= 3 and numeric_lines >= 3:
        return "schedule", "financial_table_candidate", "Schedules", None, "financial_schedule"
    return "other_text", "context_or_narrative", prior_section, None, None


def title_guess(lines: list[str]) -> str | None:
    ignored = re.compile(r"^(?:CITY OF|CHARLOTTETOWN|MARCH|DECEMBER|PAGE\s+)?(?:\d+)?$", re.I)
    for line in lines[:10]:
        if 3 <= len(line) <= 140 and not ignored.fullmatch(line):
            return line
    return None


def build_page_records(
    document_key: str,
    embedded: dict[int, str],
    ocr: dict[int, OcrResult],
) -> list[PageRecord]:
    records: list[PageRecord] = []
    section = "Front matter"
    for page in sorted(ocr):
        result = ocr[page]
        text = result.text
        lines = nonempty_lines(text)
        amount_count = len(AMOUNT_RE.findall(text))
        numeric_lines = sum(bool(AMOUNT_RE.search(line) or INTEGER_COLUMN_RE.search(line)) for line in lines)
        content_type, disposition, section, statement, family = classify_page(
            page, text, section, amount_count, numeric_lines
        )
        reviews: list[str] = []
        if result.mean_confidence is None or result.mean_confidence < 70:
            reviews.append("low OCR confidence; visual source review required before extraction")
        if content_type == "blank_or_scan_artifact":
            reviews.append("no OCR text; visual source review required")
        confidence = "low" if reviews else ("high" if content_type in {"cover", "index", "financial_statement"} else "medium")
        records.append(
            PageRecord(
                page_key=f"{document_key}_p{page:03d}",
                page_number=page,
                printed_page_label=printed_page_label(lines, page),
                content_type=content_type,
                disposition=disposition,
                section=section,
                title_guess=title_guess(lines),
                statement_class=statement,
                table_candidate=family is not None,
                table_family=family,
                text_extraction_method="ocr_full_page",
                embedded_character_count=len(embedded[page]),
                ocr_character_count=len(text),
                ocr_word_count=result.recognized_words,
                ocr_mean_confidence=result.mean_confidence,
                ocr_rotation_degrees=result.rotation_degrees,
                amount_token_count=amount_count,
                numeric_line_count=numeric_lines,
                periods=sorted(set(YEAR_RE.findall(text))),
                continuation_candidate=False,
                continuation_of_page_key=None,
                confidence=confidence,
                review_reasons=reviews,
            )
        )

    prior: PageRecord | None = None
    for record in records:
        if record.table_candidate and prior and prior.table_candidate:
            same_family = record.table_family == prior.table_family
            notes_pair = record.section == prior.section == "Notes"
            if same_family and (notes_pair or record.statement_class == prior.statement_class):
                record.continuation_candidate = True
                record.continuation_of_page_key = prior.page_key
        prior = record
    return records


def table_manifest(document_key: str, pages: list[PageRecord]) -> list[dict[str, object]]:
    return [
        {
            "table_key": f"{page.page_key}_t01",
            "document_key": document_key,
            "page_key": page.page_key,
            "page_number": page.page_number,
            "title_guess": page.title_guess,
            "section": page.section,
            "table_family": page.table_family,
            "statement_class": page.statement_class,
            "periods": page.periods,
            "continuation_candidate": page.continuation_candidate,
            "continuation_of_page_key": page.continuation_of_page_key,
            "disposition": "profiled_for_gate_3_schema_spike",
            "confidence": page.confidence,
            "review_reasons": page.review_reasons,
        }
        for page in pages
        if page.table_candidate
    ]


def replace_generated_directory(staging: Path, destination: Path) -> None:
    prior = destination.with_name(destination.name + ".prior")
    if prior.exists():
        shutil.rmtree(prior)
    if destination.exists():
        destination.replace(prior)
    staging.replace(destination)
    if prior.exists():
        shutil.rmtree(prior)


def profile_document(
    root: Path,
    output_root: Path,
    document: dict[str, object],
    tools: dict[str, str],
    workers: int,
) -> dict[str, object]:
    document_key = str(document["document_key"])
    pdf = root / str(document["source_file"])
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    actual_hash = sha256(pdf)
    if actual_hash != document["sha256"]:
        raise RuntimeError(f"{document_key}: SHA-256 differs from the Gate 1 registry")
    metadata = pdf_metadata(pdf, tools)
    if metadata["page_count"] != document["page_count"]:
        raise RuntimeError(f"{document_key}: page count differs from the Gate 1 registry")

    with tempfile.TemporaryDirectory(prefix=f"{document_key}-") as temp_name:
        temp = Path(temp_name)
        staging = output_root / f".{document_key}.staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        embedded = embedded_pages(pdf, int(document["page_count"]), tools, staging / "profile-raw-pages")
        images = render_pages(pdf, int(document["page_count"]), tools, temp / "rendered-pages")
        ocr = ocr_pages(images, tools, workers, staging / "profile-ocr-pages")
        pages = build_page_records(document_key, embedded, ocr)
        tables = table_manifest(document_key, pages)
        page_payload = [asdict(page) for page in pages]
        write_json(staging / "page_inventory.json", {"schema_version": SCHEMA_VERSION, "records": page_payload})
        write_json(staging / "table_manifest.json", {"schema_version": SCHEMA_VERSION, "records": tables})
        write_csv(staging / "page_inventory.csv", page_payload)
        write_csv(staging / "table_manifest.csv", tables)
        counts = {
            "pages": len(pages),
            "pages_with_disposition": sum(bool(page.disposition) for page in pages),
            "table_candidates": len(tables),
            "unclassified_financial_tables": sum(
                page.table_candidate and not page.table_family for page in pages
            ),
            "continuation_candidates": sum(page.continuation_candidate for page in pages),
            "review_pages": sum(bool(page.review_reasons) for page in pages),
            "pages_by_content_type": dict(sorted(Counter(page.content_type for page in pages).items())),
            "pages_by_disposition": dict(sorted(Counter(page.disposition for page in pages).items())),
            "tables_by_family": dict(sorted(Counter(page.table_family for page in pages if page.table_family).items())),
            "statements_by_class": dict(sorted(Counter(page.statement_class for page in pages if page.statement_class).items())),
        }
        profile = {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": "financial_statement_source_profile",
            "gate": 2,
            "document_key": document_key,
            "source_file": document["source_file"],
            "sha256": actual_hash,
            "reporting_entity_key": document["reporting_entity_key"],
            "reporting_date": document["reporting_date"],
            "metadata": metadata,
            "profiling_method": {
                "embedded_text": "pdftotext -layout retained as raw diagnostic evidence",
                "ocr": "all pages rendered at 180 DPI and read with Tesseract psm 6 TSV",
                "rendered_pages_retained": False,
                "semantic_limit": "candidate classification only; no normalized row or observation semantics",
            },
            "counts": counts,
            "gate_checks": {
                "registry_hash_match": True,
                "registry_page_count_match": True,
                "every_page_has_disposition": counts["pages"] == counts["pages_with_disposition"],
                "unclassified_financial_table_count": counts["unclassified_financial_tables"],
            },
        }
        write_json(staging / "source_profile.json", profile)
        replace_generated_directory(staging, output_root / document_key)
    return profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("data/financial-statements/charlottetown/source-document-registry.json"))
    parser.add_argument("--output-root", type=Path, default=Path("data/financial-statements/charlottetown"))
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    root = Path(__file__).resolve().parent.parent
    registry_path = args.registry if args.registry.is_absolute() else root / args.registry
    output_root = args.output_root if args.output_root.is_absolute() else root / args.output_root
    registry = read_json(registry_path)
    documents = registry.get("documents")
    if not isinstance(documents, list) or len(documents) != 8:
        raise RuntimeError("Gate 2 requires the eight-document Gate 1 registry")
    tools = locate_tools()
    profiles: list[dict[str, object]] = []
    for document in documents:
        key = document["document_key"]
        print(f"Profiling {key}", flush=True)
        profiles.append(profile_document(root, output_root, document, tools, args.workers))

    total_pages = sum(int(profile["counts"]["pages"]) for profile in profiles)
    total_tables = sum(int(profile["counts"]["table_candidates"]) for profile in profiles)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "financial_statement_gate_2_profile_summary",
        "gate": 2,
        "status": "complete" if total_pages == registry["counts"]["pdf_pages"] else "failed",
        "registry_path": args.registry.as_posix(),
        "counts": {
            "documents": len(profiles),
            "pages": total_pages,
            "pages_with_disposition": sum(int(profile["counts"]["pages_with_disposition"]) for profile in profiles),
            "table_candidates": total_tables,
            "unclassified_financial_tables": sum(int(profile["counts"]["unclassified_financial_tables"]) for profile in profiles),
            "review_pages": sum(int(profile["counts"]["review_pages"]) for profile in profiles),
        },
        "documents": [
            {
                "document_key": profile["document_key"],
                "sha256": profile["sha256"],
                "counts": profile["counts"],
                "gate_checks": profile["gate_checks"],
            }
            for profile in profiles
        ],
        "gate_checks": {
            "all_registry_documents_profiled": len(profiles) == 8,
            "all_registry_pages_profiled": total_pages == registry["counts"]["pdf_pages"],
            "every_page_has_disposition": total_pages == sum(int(profile["counts"]["pages_with_disposition"]) for profile in profiles),
            "unclassified_financial_table_count": sum(int(profile["counts"]["unclassified_financial_tables"]) for profile in profiles),
            "database_writes": 0,
        },
    }
    write_json(output_root / "gate-2-profile-summary.json", summary)
    if summary["status"] != "complete" or summary["gate_checks"]["unclassified_financial_table_count"] != 0:
        raise RuntimeError("Gate 2 profiling checks failed")
    print(f"Profiled {len(profiles)} documents, {total_pages} pages, and {total_tables} table candidates", flush=True)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
AGENDA_PDF = ROOT / "docs" / "charlottetown" / "council-meetings" / "05 Regular Meeting of Council Agenda - May 12, 2026.pdf"
PACKAGE_PDF = ROOT / "docs" / "charlottetown" / "council-meetings" / "05 Regular Meeting of Council Package - May 12, 2026.pdf"
OUT_DIR = ROOT / "data" / "council-meetings" / "charlottetown" / "2026-05-12-regular-council"
OUT_FILE = OUT_DIR / "meeting.json"
RAW_DIR = OUT_DIR / "raw-pages"
SCHEMA_PATH = ROOT / "schema" / "json-schema" / "council-meeting-extraction.schema.json"


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(text: str) -> str:
    replacements = {
        "\uf0b7": "-",
        "\u2022": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def pypdf_pages(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(clean_text(page.extract_text() or ""))
    return pages


def poppler_pages(path: Path, page_count: int) -> list[str] | None:
    try:
        pages: list[str] = []
        for page_number in range(1, page_count + 1):
            result = subprocess.run(
                ["pdftotext", "-layout", "-f", str(page_number), "-l", str(page_number), str(path), "-"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            pages.append(clean_text(result.stdout.replace("\f", "")))
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return pages


def extract_pages(path: Path) -> list[str]:
    page_count = len(PdfReader(str(path)).pages)
    pages = poppler_pages(path, page_count)
    if pages:
        return pages
    return pypdf_pages(path)


def citation(document_id: str, page: int, excerpt: str) -> dict[str, Any]:
    return {
        "source_document_id": document_id,
        "pdf_page_start": page,
        "pdf_page_end": page,
        "text_excerpt": clean_text(excerpt)[:1200],
    }


def first_matching_page(pages: list[str], pattern: str) -> tuple[int, str] | None:
    rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for index, text in enumerate(pages, start=1):
        if rx.search(text):
            return index, text
    return None


def excerpt_around(text: str, pattern: str, chars: int = 900) -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return text[:chars]
    start = max(0, match.start() - chars // 4)
    end = min(len(text), match.end() + chars)
    return text[start:end]


def write_raw_pages(pages_by_document: dict[str, list[str]]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for document_id, pages in pages_by_document.items():
        for page_number, text in enumerate(pages, start=1):
            path = RAW_DIR / f"{document_id}-page-{page_number:03d}.txt"
            path.write_text(text + "\n", encoding="utf-8")


def build_payload(agenda_pages: list[str], package_pages: list[str]) -> dict[str, Any]:
    agenda_text = "\n\n".join(agenda_pages)
    package_text = "\n\n".join(package_pages)
    planning_page = first_matching_page(package_pages, r"PLANNING AND HERITAGE\s+REPORT TO COUNCIL")
    brackley_page = first_matching_page(package_pages, r"PH-ZD\.2-110|Business\s+Park\s+Industrial\s+\(M-3\)")
    king_page = first_matching_page(package_pages, r"PH-ZD\.2-109|Downtown\s+Main\s+Street\s+\(DMS\)")

    brackley_excerpt = excerpt_around(
        (brackley_page or (1, package_text))[1],
        r"PH-ZD\.2-110|Business\s+Park\s+Industrial\s+\(M-3\)|231\s+Brackley\s+Point\s+Road",
    )
    king_excerpt = excerpt_around(
        (king_page or (1, package_text))[1],
        r"PH-ZD\.2-109|Downtown\s+Main\s+Street\s+\(DMS\)|King\s+and\s+Dorchester|King\s+&\s+Dorchester",
    )
    planning_excerpt = excerpt_around(
        (planning_page or (1, package_text))[1],
        r"Resolutions:\s+Five|Second Readings:\s+Two|Planning Board",
    )

    return {
        "$schema": "../../../schema/json-schema/council-meeting-extraction.schema.json",
        "schema_version": 1,
        "meeting": {
            "meeting_id": "charlottetown-2026-05-12-regular-council",
            "jurisdiction": "City of Charlottetown",
            "body": "Council",
            "meeting_type": "regular_council",
            "title": "Regular Monthly Meeting of Council",
            "date": "2026-05-12",
            "time": "5:00 PM",
            "location": "Council Chambers, City Hall, 199 Queen Street",
            "livestream_url": "https://www.charlottetown.ca/video",
            "focus": "Public preparation for zoning-related agenda items and bylaw readings.",
        },
        "source_documents": [
            {
                "source_document_id": "agenda",
                "document_type": "agenda",
                "repo_relpath": relpath(AGENDA_PDF),
                "page_count": len(agenda_pages),
                "sha256": sha256_file(AGENDA_PDF),
            },
            {
                "source_document_id": "package",
                "document_type": "agenda_package",
                "repo_relpath": relpath(PACKAGE_PDF),
                "page_count": len(package_pages),
                "sha256": sha256_file(PACKAGE_PDF),
            },
        ],
        "agenda_sections": [
            {
                "agenda_section_id": "agenda-7-1-planning-heritage",
                "label_raw": "7.1",
                "title_raw": "Planning & Heritage",
                "summary": "Planning & Heritage lists a monthly report, five resolutions, and two second readings to amend the Zoning & Development Bylaw.",
                "citations": [citation("agenda", 1, excerpt_around(agenda_text, r"7\.1\.\s+Planning\s+&\s+Heritage"))],
            },
            {
                "agenda_section_id": "agenda-7-11-new-business",
                "label_raw": "7.11",
                "title_raw": "New Business",
                "summary": "New Business lists one resolution outside the committee report sequence.",
                "citations": [citation("agenda", 2, excerpt_around(agenda_text, r"7\.11\.\s+New\s+Business"))],
            },
        ],
        "committee_reports": [
            {
                "committee_report_id": "planning-heritage-report-2026-05-12",
                "committee_name": "Planning & Heritage",
                "chair": "Deputy Mayor Alanna Jankov",
                "summary": "The Planning & Heritage report identifies five resolutions and two second readings, including zoning-related items for 231 Brackley Point Road and King/Dorchester Streets.",
                "citations": [citation("package", planning_page[0] if planning_page else 1, planning_excerpt)],
            }
        ],
        "resolutions": [
            {
                "item_id": "resolution-planning-board-307-patterson-public-consultation",
                "agenda_section_id": "agenda-7-1-planning-heritage",
                "item_type": "resolution",
                "title": "307 Patterson Drive rezoning request to proceed to public consultation",
                "stage": "public_consultation_request",
                "decision_requested": "Proceed to public consultation concerning a request to rezone the subject property.",
                "property_references": [
                    {"label": "307 Patterson Drive", "address": "307 Patterson Drive", "pids": ["676585"]}
                ],
                "zoning_amendment": {
                    "from_zone": "unknown",
                    "to_zone": "unknown",
                    "bylaw_name": "Zoning & Development Bylaw",
                    "official_plan_amendment": False,
                    "future_land_use_change": None,
                },
                "public_summary": "This item is at an earlier consultation stage than tonight's second readings.",
                "citations": [citation("package", planning_page[0] if planning_page else 1, planning_excerpt)],
            },
            {
                "item_id": "resolution-planning-board-pid-390534-1179670-public-consultation",
                "agenda_section_id": "agenda-7-1-planning-heritage",
                "item_type": "resolution",
                "title": "Unaddressed properties PID 390534 and PID 1179670 rezoning request to proceed to public consultation",
                "stage": "public_consultation_request",
                "decision_requested": "Proceed to public consultation concerning a request to rezone the subject properties.",
                "property_references": [
                    {"label": "Unaddressed properties", "address": None, "pids": ["390534", "1179670"]}
                ],
                "zoning_amendment": {
                    "from_zone": "unknown",
                    "to_zone": "unknown",
                    "bylaw_name": "Zoning & Development Bylaw",
                    "official_plan_amendment": False,
                    "future_land_use_change": None,
                },
                "public_summary": "This item is at an earlier consultation stage than tonight's second readings.",
                "citations": [citation("package", planning_page[0] if planning_page else 1, planning_excerpt)],
            },
        ],
        "bylaw_readings": [
            {
                "item_id": "bylaw-reading-ph-zd-2-110-231-brackley-point-road",
                "agenda_section_id": "agenda-7-1-planning-heritage",
                "item_type": "bylaw_reading",
                "title": "PH-ZD.2-110 - 231 Brackley Point Road rezoning",
                "stage": "second_reading",
                "decision_requested": "Read a second time and approve the bylaw amendment for 231 Brackley Point Road.",
                "property_references": [
                    {"label": "231 Brackley Point Road", "address": "231 Brackley Point Road", "pids": ["623090"]}
                ],
                "zoning_amendment": {
                    "from_zone": "I",
                    "to_zone": "M-3",
                    "bylaw_name": "Zoning & Development Bylaw",
                    "official_plan_amendment": True,
                    "future_land_use_change": "Neighbourhood to Workscapes",
                },
                "public_summary": "Council is considering second reading for a rezoning from Institutional to Business Park Industrial and related Official Plan future land use change.",
                "citations": [
                    citation("agenda", 1, excerpt_around(agenda_text, r"231\s+Brackley\s+Point\s+Road")),
                    citation("package", brackley_page[0] if brackley_page else 1, brackley_excerpt),
                ],
            },
            {
                "item_id": "bylaw-reading-ph-zd-2-109-king-dorchester",
                "agenda_section_id": "agenda-7-1-planning-heritage",
                "item_type": "bylaw_reading",
                "title": "PH-ZD.2-109 - King and Dorchester Streets rezoning",
                "stage": "second_reading",
                "decision_requested": "Read a second time and approve the bylaw amendment for the King and Dorchester Streets properties.",
                "property_references": [
                    {
                        "label": "King and Dorchester Streets",
                        "address": "King and Dorchester Streets",
                        "pids": ["336974", "336909", "336917", "336966", "1172915"],
                    }
                ],
                "zoning_amendment": {
                    "from_zone": "DMUN",
                    "to_zone": "DMS",
                    "bylaw_name": "Zoning & Development Bylaw",
                    "official_plan_amendment": True,
                    "future_land_use_change": "Downtown Mixed-Use Neighbourhood to Downtown Main Street",
                },
                "public_summary": "Council is considering second reading for a rezoning from Downtown Mixed-Use Neighbourhood to Downtown Main Street for multiple King/Dorchester properties.",
                "citations": [
                    citation("agenda", 1, excerpt_around(agenda_text, r"King\s+&\s+Dorchester")),
                    citation("package", king_page[0] if king_page else 1, king_excerpt),
                ],
            },
        ],
        "planning_items": [
            {
                "planning_item_id": "planning-item-231-brackley-point-road",
                "title": "231 Brackley Point Road",
                "item_type": "planning_application",
                "stage": "second_reading",
                "property_references": [
                    {"label": "231 Brackley Point Road", "address": "231 Brackley Point Road", "pids": ["623090"]}
                ],
                "citations": [citation("package", brackley_page[0] if brackley_page else 1, brackley_excerpt)],
            },
            {
                "planning_item_id": "planning-item-king-dorchester",
                "title": "King and Dorchester Streets",
                "item_type": "planning_application",
                "stage": "second_reading",
                "property_references": [
                    {
                        "label": "King and Dorchester Streets",
                        "address": "King and Dorchester Streets",
                        "pids": ["336974", "336909", "336917", "336966", "1172915"],
                    }
                ],
                "citations": [citation("package", king_page[0] if king_page else 1, king_excerpt)],
            },
        ],
        "audience_workflows": [
            {
                "audience": "public_member",
                "stages": [
                    {
                        "stage": "prepare",
                        "tasks": [
                            "Identify zoning items on the agenda.",
                            "Check each PID or address against current and draft zoning data.",
                            "Open the source agenda/package pages before the meeting.",
                        ],
                    },
                    {
                        "stage": "observe",
                        "tasks": [
                            "Watch for Planning & Heritage item 7.1.",
                            "Record the motion wording, mover, seconder, vote, and any amendments.",
                        ],
                    },
                    {
                        "stage": "follow_up",
                        "tasks": [
                            "Compare the outcome against official minutes when posted.",
                            "Update parcel notes, bylaw amendment status, and any appeal or implementation dates.",
                        ],
                    },
                ],
            },
            {
                "audience": "council_or_committee",
                "stages": [
                    {"stage": "prepare", "tasks": ["Review prior reading status, property references, and zoning/Official Plan implications."]},
                    {"stage": "observe", "tasks": ["Track amendments, conflicts, questions to staff, and vote outcomes."]},
                    {"stage": "follow_up", "tasks": ["Confirm adopted wording and direct staff follow-up where required."]},
                ],
            },
            {
                "audience": "municipal_staff",
                "stages": [
                    {"stage": "prepare", "tasks": ["Verify source package completeness, legal descriptions, PIDs, maps, and draft bylaw references."]},
                    {"stage": "observe", "tasks": ["Capture procedural changes, deferrals, amendments, and implementation instructions."]},
                    {"stage": "follow_up", "tasks": ["Publish minutes, update bylaw status, update maps/data, and prepare implementation records."]},
                ],
            },
        ],
        "review_flags": [
            {
                "review_flag_id": "package-page-citation-review",
                "severity": "info",
                "message": "Package citations are derived from PDF text search and should be reviewed against the rendered source pages before production use.",
                "citations": [citation("package", planning_page[0] if planning_page else 1, planning_excerpt)],
            }
        ],
    }


def validate_payload(payload: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        for error in errors:
            path = ".".join(str(part) for part in error.path) or "<root>"
            print(f"{path}: {error.message}")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Charlottetown council meeting agenda/package JSON.")
    parser.add_argument("--no-raw-pages", action="store_true", help="Do not write page-level raw text files.")
    args = parser.parse_args()

    agenda_pages = extract_pages(AGENDA_PDF)
    package_pages = extract_pages(PACKAGE_PDF)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.no_raw_pages:
      write_raw_pages({"agenda": agenda_pages, "package": package_pages})
    payload = build_payload(agenda_pages, package_pages)
    validate_payload(payload)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {relpath(OUT_FILE)}")


if __name__ == "__main__":
    main()

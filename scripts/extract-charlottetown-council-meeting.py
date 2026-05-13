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
AGENDA_OUT_FILE = OUT_DIR / "agenda.json"
TOC_OUT_FILE = OUT_DIR / "toc.json"
RAW_DIR = OUT_DIR / "raw-pages"
SCHEMA_PATH = ROOT / "schema" / "json-schema" / "council-meeting-extraction.schema.json"

PACKAGE_DOCUMENTS = [
    {
        "document_id": "package-agenda",
        "source_document_id": "package",
        "title": "Regular Monthly Meeting of Council agenda",
        "document_type": "agenda",
        "page_start": 1,
        "page_end": 2,
        "agenda_item_ids": ["agenda-root"],
        "summary": "Package copy of the regular council agenda, listing opening business, committee reports, Planning & Heritage zoning items, closed-session matter, and adjournment.",
        "boundary_basis": "Agenda title page followed by agenda continuation page.",
    },
    {
        "document_id": "previous-minutes-2026-04-14",
        "source_document_id": "package",
        "title": "Draft regular council minutes, April 14, 2026",
        "document_type": "minutes",
        "page_start": 3,
        "page_end": 10,
        "agenda_item_ids": ["agenda-4"],
        "summary": "Draft minutes from the April 14 regular council meeting, including prior motions, first readings, committee reports, and adjournment.",
        "boundary_basis": "Draft minutes cover pages marked page 1 of 8 through page 8 of 8.",
    },
    {
        "document_id": "planning-heritage-report",
        "source_document_id": "package",
        "title": "Planning & Heritage report to council",
        "document_type": "committee_report",
        "template_type": "committee-report-cover",
        "page_start": 11,
        "page_end": 11,
        "agenda_item_ids": ["agenda-7-1-planning-heritage"],
        "summary": "Planning & Heritage cover report listing the monthly report, five resolutions, and two zoning bylaw second readings.",
        "boundary_basis": "Report to Council cover page before committee minutes.",
    },
    {
        "document_id": "planning-heritage-committee-minutes",
        "source_document_id": "package",
        "title": "Planning & Heritage Committee minutes, May 5, 2026",
        "document_type": "committee_minutes",
        "page_start": 12,
        "page_end": 14,
        "agenda_item_ids": ["agenda-7-1-planning-heritage"],
        "summary": "Committee minutes covering Victoria Row pedestrian mall agreement discussions and related committee business.",
        "boundary_basis": "Minutes pages marked page 1 of 3 through page 3 of 3.",
    },
    {
        "document_id": "pedestrian-mall-agreement-report",
        "source_document_id": "package",
        "title": "Pedestrian Mall Agreement operating hours report and bylaw background",
        "document_type": "agenda_item_package",
        "template_type": "staff-report-with-attachments",
        "page_start": 15,
        "page_end": 25,
        "agenda_item_ids": ["resolution-pedestrian-mall-agreement"],
        "summary": "Staff report and Pedestrian Mall Bylaw materials for amending Victoria Row pedestrian mall operating hours.",
        "boundary_basis": "City staff report followed by bylaw attachment ending before the resolution cover page.",
    },
    {
        "document_id": "pedestrian-mall-resolution",
        "source_document_id": "package",
        "title": "Planning & Heritage resolution: Pedestrian Mall Agreement",
        "document_type": "resolution",
        "template_type": "resolution-template",
        "page_start": 26,
        "page_end": 26,
        "agenda_item_ids": ["resolution-pedestrian-mall-agreement"],
        "summary": "Resolution template for Council approval of amended Victoria Row pedestrian mall operating hours.",
        "boundary_basis": "One-page City of Charlottetown resolution template.",
    },
    {
        "document_id": "planning-board-minutes",
        "source_document_id": "package",
        "title": "Planning Board minutes, May 5, 2026",
        "document_type": "board_minutes",
        "page_start": 27,
        "page_end": 37,
        "agenda_item_ids": ["agenda-7-1-planning-heritage"],
        "summary": "Planning Board minutes covering variance, rezoning, consolidation, and second-reading items later represented as Planning & Heritage resolutions.",
        "boundary_basis": "Minutes pages marked page 1 of 11 through page 11 of 11.",
    },
    {
        "document_id": "major-variance-15-clonhaven",
        "source_document_id": "package",
        "title": "15 Clonhaven Street major variance package",
        "document_type": "agenda_item_package",
        "template_type": "planning-board-report-with-resolution",
        "page_start": 38,
        "page_end": 55,
        "agenda_item_ids": ["resolution-planning-board-15-clonhaven-major-variance"],
        "summary": "Planning Board report, supporting attachments, and resolutions for a major variance request affecting lots at 15 Clonhaven Street.",
        "boundary_basis": "Committee report pages and two resolution templates before the next resolution cover page.",
    },
    {
        "document_id": "rezoning-307-patterson",
        "source_document_id": "package",
        "title": "307 Patterson Drive public consultation package",
        "document_type": "agenda_item_package",
        "template_type": "planning-board-report-with-resolution",
        "page_start": 56,
        "page_end": 62,
        "agenda_item_ids": ["resolution-planning-board-307-patterson-public-consultation"],
        "summary": "Planning Board resolution and report materials for proceeding to public consultation on a rezoning request at 307 Patterson Drive.",
        "boundary_basis": "Resolution cover page, staff report pages, and attachments ending before the next resolution cover page.",
    },
    {
        "document_id": "rezoning-unaddressed-pids-390534-1179670",
        "source_document_id": "package",
        "title": "Unaddressed PIDs 390534 and 1179670 public consultation package",
        "document_type": "agenda_item_package",
        "template_type": "planning-board-report-with-resolution",
        "page_start": 63,
        "page_end": 79,
        "agenda_item_ids": ["resolution-planning-board-pid-390534-1179670-public-consultation"],
        "summary": "Planning Board resolution and report materials for proceeding to public consultation on rezoning unaddressed properties identified by PID 390534 and PID 1179670.",
        "boundary_basis": "Resolution cover page, committee report, and attachments ending before the next resolution cover page.",
    },
    {
        "document_id": "parcel-consolidation-600-north-river",
        "source_document_id": "package",
        "title": "600 North River Road parcel consolidation package",
        "document_type": "agenda_item_package",
        "template_type": "planning-board-report-with-resolution",
        "page_start": 80,
        "page_end": 89,
        "agenda_item_ids": ["resolution-planning-board-600-north-river-consolidation"],
        "summary": "Planning Board resolution and report materials for consolidating PID 444679 and PID 600817 at 600 North River Road.",
        "boundary_basis": "Resolution cover page and report attachments ending before weekly Planning & Heritage summaries.",
    },
    {
        "document_id": "planning-heritage-weekly-summaries",
        "source_document_id": "package",
        "title": "Planning & Heritage weekly summaries and permit decision tables",
        "document_type": "department_summary",
        "page_start": 90,
        "page_end": 105,
        "agenda_item_ids": ["agenda-7-1-planning-heritage"],
        "summary": "Weekly Planning & Heritage summaries for April 3 through May 1, 2026, including IRAC appeal-period information, applications, decisions, lot subdivisions, and Council approvals.",
        "boundary_basis": "Repeated weekly summary headings ending before Environment & Sustainability report.",
    },
    {
        "document_id": "environment-sustainability-package",
        "source_document_id": "package",
        "title": "Environment & Sustainability report, minutes, and resolutions",
        "document_type": "committee_package",
        "template_type": "committee-report-with-minutes-and-resolutions",
        "page_start": 106,
        "page_end": 132,
        "agenda_item_ids": ["agenda-7-2"],
        "summary": "Environment & Sustainability report package with committee minutes, four resolutions, and supporting materials.",
        "boundary_basis": "Committee report cover through resolution attachments ending before Finance report.",
    },
    {
        "document_id": "finance-administration-package",
        "source_document_id": "package",
        "title": "Finance, Audit, Tendering & Administration report package",
        "document_type": "committee_package",
        "template_type": "committee-report-with-minutes",
        "page_start": 133,
        "page_end": 146,
        "agenda_item_ids": ["agenda-7-3"],
        "summary": "Finance committee report materials, including minutes and budget roll-up information.",
        "boundary_basis": "Finance report cover through supporting budget pages before Human Resources report.",
    },
    {
        "document_id": "human-resources-package",
        "source_document_id": "package",
        "title": "Human Resources report package",
        "document_type": "committee_package",
        "template_type": "committee-report-with-minutes",
        "page_start": 147,
        "page_end": 155,
        "agenda_item_ids": ["agenda-7-4"],
        "summary": "Human Resources report, draft committee minutes, and supporting legislative authority notes.",
        "boundary_basis": "Human Resources report cover through supporting notes before Strategic Priorities report.",
    },
    {
        "document_id": "strategic-priorities-summary",
        "source_document_id": "package",
        "title": "Strategic Priorities, Communications & Intergovernmental Cooperation report",
        "document_type": "committee_report",
        "page_start": 156,
        "page_end": 156,
        "agenda_item_ids": ["agenda-7-5"],
        "summary": "One-page Strategic Priorities, Communications & Intergovernmental Cooperation report summary.",
        "boundary_basis": "Single report page before Protective and Emergency Services report.",
    },
    {
        "document_id": "protective-emergency-services-package",
        "source_document_id": "package",
        "title": "Protective and Emergency Services report, nuisance bylaw, and horsedrawn/rickshaw bylaw materials",
        "document_type": "committee_package",
        "template_type": "committee-report-with-bylaw-attachments",
        "page_start": 157,
        "page_end": 228,
        "agenda_item_ids": ["agenda-7-6"],
        "summary": "Protective and Emergency Services report package with nuisance bylaw amendment materials, monthly statistics, and Horsedrawn and Rickshaw Vehicle Bylaw first-reading materials.",
        "boundary_basis": "Protective report cover through horsedrawn and rickshaw bylaw proposed amendment pages before Parks report.",
    },
    {
        "document_id": "parks-recreation-summary",
        "source_document_id": "package",
        "title": "Parks, Recreation and Leisure Activities report",
        "document_type": "committee_report",
        "page_start": 229,
        "page_end": 229,
        "agenda_item_ids": ["agenda-7-7"],
        "summary": "One-page Parks, Recreation and Leisure Activities report summary.",
        "boundary_basis": "Single report page before Water & Sewer Utility report.",
    },
    {
        "document_id": "water-sewer-summary",
        "source_document_id": "package",
        "title": "Water & Sewer Utility report",
        "document_type": "committee_report",
        "page_start": 230,
        "page_end": 230,
        "agenda_item_ids": ["agenda-7-8"],
        "summary": "One-page Water & Sewer Utility report summary.",
        "boundary_basis": "Single report page before Economic, Tourism & Cultural Development report.",
    },
    {
        "document_id": "economic-tourism-cultural-development-package",
        "source_document_id": "package",
        "title": "Economic, Tourism & Cultural Development report and Arts Advisory Board minutes",
        "document_type": "committee_package",
        "template_type": "committee-report-with-board-minutes",
        "page_start": 231,
        "page_end": 234,
        "agenda_item_ids": ["agenda-7-9"],
        "summary": "Economic, Tourism & Cultural Development report with Charlottetown Arts Advisory Board draft meeting minutes.",
        "boundary_basis": "Committee report cover and Arts Advisory Board minutes before Public Works report.",
    },
    {
        "document_id": "public-works-package",
        "source_document_id": "package",
        "title": "Public Works report, minutes, resolution, and operational updates",
        "document_type": "committee_package",
        "template_type": "committee-report-with-minutes-and-resolution",
        "page_start": 235,
        "page_end": 252,
        "agenda_item_ids": ["agenda-7-10"],
        "summary": "Public Works report package with committee minutes, a resolution, staff report, capital summary updates, and operational report.",
        "boundary_basis": "Public Works report cover through operational report before New Business resolution.",
    },
    {
        "document_id": "new-business-food-council-appointment",
        "source_document_id": "package",
        "title": "New Business resolution: Food Council appointment",
        "document_type": "resolution",
        "template_type": "new-business-resolution-with-application",
        "page_start": 253,
        "page_end": 256,
        "agenda_item_ids": ["agenda-7-11-new-business"],
        "summary": "New Business resolution and supporting application/email material for an appointment to the Food Council.",
        "boundary_basis": "New Business resolution cover through final package page.",
    },
]


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


def page_range_citation(document_id: str, start: int, end: int, pages: list[str]) -> dict[str, Any]:
    excerpt = pages[start - 1] if 0 <= start - 1 < len(pages) else ""
    return {
        "source_document_id": document_id,
        "pdf_page_start": start,
        "pdf_page_end": end,
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


def page_count(record: dict[str, Any]) -> int:
    return int(record["page_end"]) - int(record["page_start"]) + 1


def document_category(record: dict[str, Any]) -> str:
    document_type = record.get("document_type", "")
    title = f"{record.get('title', '')} {record.get('summary', '')}".lower()
    template_type = record.get("template_type", "")
    if document_type == "agenda":
        return "agenda"
    if "minutes" in document_type:
        return "minutes"
    if document_type == "resolution":
        return "resolutions"
    if "reading" in title or "bylaw" in title or "bylaw" in template_type:
        return "readings"
    if document_type == "department_summary":
        return "monthly_reports"
    if "email" in title:
        return "emails"
    if "applicant" in title or "application" in title:
        return "applicant_submissions"
    if "developer" in title:
        return "developer_submissions"
    if "public submission" in title:
        return "public_submissions"
    if "submission" in title:
        return "document_submissions"
    if document_type in {
        "committee_report",
        "committee_package",
        "agenda_item_package",
    }:
        return "monthly_reports"
    return "uncategorized"


def build_toc(agenda_pages: list[str], package_pages: list[str]) -> dict[str, Any]:
    package_page_count = len(package_pages)
    documents = []
    for record in PACKAGE_DOCUMENTS:
        if record["page_end"] > package_page_count:
            raise ValueError(f"{record['document_id']} ends after package page count {package_page_count}.")
        entry = dict(record)
        entry["document_category"] = document_category(entry)
        entry["page_count"] = page_count(record)
        entry["citations"] = [page_range_citation("package", record["page_start"], record["page_end"], package_pages)]
        documents.append(entry)

    return {
        "schema_version": 1,
        "meeting_id": "charlottetown-2026-05-12-regular-council",
        "generated_from": {
            "agenda_pdf": {
                "repo_relpath": relpath(AGENDA_PDF),
                "page_count": len(agenda_pages),
                "sha256": sha256_file(AGENDA_PDF),
            },
            "package_pdf": {
                "repo_relpath": relpath(PACKAGE_PDF),
                "page_count": package_page_count,
                "sha256": sha256_file(PACKAGE_PDF),
            },
        },
        "documents": documents,
        "document_structure_standards": [
            {
                "standard_id": "agenda-first",
                "description": "The agenda appears first in the standalone agenda PDF and is repeated as the first package document. Treat these pages as one logical agenda source.",
                "observed_pages": [{"source_document_id": "agenda", "page_start": 1, "page_end": len(agenda_pages)}, {"source_document_id": "package", "page_start": 1, "page_end": 2}],
            },
            {
                "standard_id": "template-then-attachments",
                "description": "Most actionable items begin with a City resolution or committee/staff report template, followed by minutes, reports, maps, bylaws, tables, or application attachments.",
                "review_action": "When a future package does not start an item with a recognizable template page, create a review flag instead of forcing extraction into a known template type.",
            },
            {
                "standard_id": "visual-document-boundaries",
                "description": "Document boundaries are detected from visible title-page changes, page x of y markers, recurring committee report covers, resolution cover pages, and table/report formatting shifts.",
            },
        ],
        "page_reproduction_options": [
            {
                "option_id": "page-images",
                "label": "Rendered page images",
                "delivery": "Pre-render each PDF page to PNG or WebP and serve by source document plus page number.",
                "accuracy": "High visual fidelity at chosen DPI; selectable text requires a separate OCR/text overlay.",
                "fit": "Best first implementation for top-level agenda view and filtered item pages without serving PDF.",
            },
            {
                "option_id": "svg-pages",
                "label": "SVG page renderings",
                "delivery": "Convert each PDF page to SVG and serve the SVG assets directly.",
                "accuracy": "Can preserve vector geometry and text, but fonts and browser rendering may vary.",
                "fit": "Useful where zoom fidelity matters and the source PDFs convert cleanly.",
            },
            {
                "option_id": "html-text-overlay",
                "label": "Image plus positioned text layer",
                "delivery": "Render each page image and add a generated HTML text layer from PDF coordinates.",
                "accuracy": "Strong visual fidelity with searchable/copyable text, but coordinate extraction needs QA.",
                "fit": "Best long-term web viewer path if source-page interaction matters.",
            },
        ],
        "review_flags": [
            {
                "review_flag_id": "toc-boundaries-manual-review",
                "severity": "warning",
                "message": "Package document boundaries are deterministic for this May 12 package but were seeded from observed page headings and page-number patterns; future packages require mismatch flags before reuse.",
            }
        ],
    }


def build_agenda(agenda_pages: list[str], package_pages: list[str], meeting_payload: dict[str, Any], toc_payload: dict[str, Any]) -> dict[str, Any]:
    package_agenda_doc = next(document for document in toc_payload["documents"] if document["document_id"] == "package-agenda")
    agenda_documents = [
        {
            "document_id": "standalone-agenda",
            "source_document_id": "agenda",
            "title": "Standalone Regular Monthly Meeting of Council agenda",
            "document_type": "agenda",
            "document_category": "agenda",
            "page_start": 1,
            "page_end": len(agenda_pages),
            "page_count": len(agenda_pages),
            "summary": "Standalone agenda listing the May 12 regular council meeting order of business.",
            "citations": [page_range_citation("agenda", 1, len(agenda_pages), agenda_pages)],
        },
        package_agenda_doc,
    ]
    agenda_items = (
        meeting_payload["agenda_sections"]
        + meeting_payload["committee_reports"]
        + meeting_payload["resolutions"]
        + meeting_payload["bylaw_readings"]
        + meeting_payload["planning_items"]
    )
    return {
        "schema_version": 1,
        "meeting": meeting_payload["meeting"],
        "agenda_documents": agenda_documents,
        "agenda_items": agenda_items,
        "linked_package_documents": [
            {
                "document_id": document["document_id"],
                "title": document["title"],
                "document_type": document["document_type"],
                "document_category": document.get("document_category", "other"),
                "template_type": document.get("template_type"),
                "page_start": document["page_start"],
                "page_end": document["page_end"],
                "page_count": document["page_count"],
                "agenda_item_ids": document["agenda_item_ids"],
                "summary": document["summary"],
            }
            for document in toc_payload["documents"]
        ],
        "extraction_scope": {
            "full_content_extraction": False,
            "summary_extraction": True,
            "rezoning_detail_exceptions": [
                "bylaw-reading-ph-zd-2-110-231-brackley-point-road",
                "bylaw-reading-ph-zd-2-109-king-dorchester",
            ],
        },
    }


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
    toc_payload = build_toc(agenda_pages, package_pages)
    agenda_payload = build_agenda(agenda_pages, package_pages, payload, toc_payload)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    AGENDA_OUT_FILE.write_text(json.dumps(agenda_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    TOC_OUT_FILE.write_text(json.dumps(toc_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {relpath(OUT_FILE)}")
    print(f"Wrote {relpath(AGENDA_OUT_FILE)}")
    print(f"Wrote {relpath(TOC_OUT_FILE)}")


if __name__ == "__main__":
    main()

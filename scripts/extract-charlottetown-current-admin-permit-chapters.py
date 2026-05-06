from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import fitz


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "docs" / "charlottetown" / "charlottetown-zoning-bylaw.pdf"
ROOT = REPO_ROOT / "data" / "zoning" / "charlottetown"
MANIFEST = ROOT / "source-manifest.json"
EXTRACTOR = REPO_ROOT / "scripts" / "extract-charlottetown-zoning-bylaw.py"


DOCS = [
    {
        "file": "administration.json",
        "label": "Chapters 1-2",
        "title": "SCOPE AND OPERATION",
        "chapters": {"1", "2"},
        "pdf_page_start": 11,
        "pdf_page_end": 16,
    },
    {
        "file": "permit-applications-processes.json",
        "label": "Chapter 3",
        "title": "PERMIT APPLICATIONS AND APPLICATION PROCESSES",
        "chapters": {"3"},
        "pdf_page_start": 17,
        "pdf_page_end": 32,
    },
]


HEADER_RE = re.compile(r"^Zoning & Development Bylaw ")
PAGE_NO_RE = re.compile(r"^\d+$")
CLAUSE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\s+(.+))?$")
SUBCLAUSE_RE = re.compile(r"^([a-z]|[ivxlcdm]+)\.\s+(.+)$", re.IGNORECASE)
CHAPTER_TITLES = {
    "1": "SCOPE",
    "2": "OPERATION",
    "3": "PERMIT APPLICATIONS AND APPLICATION PROCESSES",
}


def load_current_module() -> Any:
    spec = importlib.util.spec_from_file_location("current_extractor", EXTRACTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXTRACTOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def page_lines(pdf: fitz.Document, page_number: int) -> list[str]:
    lines: list[str] = []
    for raw in pdf[page_number - 1].get_text().splitlines():
        line = clean_line(raw)
        if not line:
            continue
        if HEADER_RE.match(line):
            continue
        if PAGE_NO_RE.match(line) and int(line) == page_number:
            continue
        lines.append(line)
    return lines


def is_heading(line: str) -> bool:
    if CLAUSE_RE.match(line) or SUBCLAUSE_RE.match(line):
        return False
    if len(line) < 3:
        return False
    letters = [char for char in line if char.isalpha()]
    if not letters:
        return False
    return sum(1 for char in letters if char.isupper()) / len(letters) > 0.8


def source_ref(ref_type: str, ref_id: str) -> dict[str, str]:
    return {"source_ref_type": ref_type, "source_ref_id": ref_id}


def append_text(clause: dict[str, Any], text: str) -> None:
    current = clause.get("clause_text_raw") or ""
    if current:
        clause["clause_text_raw"] = f"{current} {text}"
    else:
        clause["clause_text_raw"] = text


def parse_sections(pdf: fitz.Document, page_start: int, page_end: int, chapters: set[str], prefix: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    section_by_label: dict[str, dict[str, Any]] = {}
    current_title = ""
    current_clause: dict[str, Any] | None = None
    current_parent: dict[str, Any] | None = None
    active_chapter: str | None = None
    source_order_by_section: dict[str, int] = {}

    for page_number in range(page_start, page_end + 1):
        for line in page_lines(pdf, page_number):
            if line in chapters:
                active_chapter = line
                continue
            if active_chapter not in chapters:
                continue
            if is_heading(line):
                current_title = line
                continue
            match = CLAUSE_RE.match(line)
            if match:
                section_label = f"{match.group(1)}.{match.group(2)}"
                section = section_by_label.get(section_label)
                if section is None:
                    section_order = len(sections) + 1
                    section_id = f"{prefix}-section-{section_label.replace('.', '-')}"
                    section = {
                        "section_id": section_id,
                        "section_label_raw": section_label,
                        "section_title_raw": current_title or section_label,
                        "source_order": section_order,
                        "clauses_raw": [],
                        "tables_raw": [],
                        "content_refs": [],
                        "citations": {
                            "pdf_page_start": page_number,
                            "pdf_page_end": page_number,
                            "bylaw_page_start": page_number,
                            "bylaw_page_end": page_number,
                        },
                    }
                    sections.append(section)
                    section_by_label[section_label] = section
                    source_order_by_section[section_label] = 0
                source_order_by_section[section_label] += 1
                clause_label = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
                clause_id = f"{prefix}-clause-{clause_label.replace('.', '-')}"
                current_clause = {
                    "clause_id": clause_id,
                    "clause_label_raw": clause_label,
                    "clause_text_raw": match.group(4) or "",
                    "parent_clause_id": None,
                    "source_order": source_order_by_section[section_label],
                    "citations": {
                        "pdf_page_start": page_number,
                        "pdf_page_end": page_number,
                        "bylaw_page_start": page_number,
                        "bylaw_page_end": page_number,
                    },
                }
                section["clauses_raw"].append(current_clause)
                section["content_refs"].append(
                    {"content_type": "clause", "content_id": clause_id, "source_order": len(section["content_refs"]) + 1}
                )
                section["citations"]["pdf_page_end"] = page_number
                section["citations"]["bylaw_page_end"] = page_number
                current_parent = current_clause
                continue
            submatch = SUBCLAUSE_RE.match(line)
            if submatch and current_parent is not None:
                section_label = ".".join(str(current_parent["clause_label_raw"]).split(".")[:2])
                section = section_by_label[section_label]
                source_order_by_section[section_label] += 1
                label = submatch.group(1).lower()
                clause_id = f"{prefix}-clause-{str(current_parent['clause_label_raw']).replace('.', '-')}-{label}"
                current_clause = {
                    "clause_id": clause_id,
                    "clause_label_raw": f"{label}.",
                    "clause_text_raw": submatch.group(2),
                    "parent_clause_id": current_parent["clause_id"],
                    "source_order": source_order_by_section[section_label],
                    "citations": {
                        "pdf_page_start": page_number,
                        "pdf_page_end": page_number,
                        "bylaw_page_start": page_number,
                        "bylaw_page_end": page_number,
                    },
                }
                section["clauses_raw"].append(current_clause)
                section["content_refs"].append(
                    {"content_type": "clause", "content_id": clause_id, "source_order": len(section["content_refs"]) + 1}
                )
                section["citations"]["pdf_page_end"] = page_number
                section["citations"]["bylaw_page_end"] = page_number
                continue
            if current_clause is not None:
                append_text(current_clause, line)
                current_clause["citations"]["pdf_page_end"] = page_number
                current_clause["citations"]["bylaw_page_end"] = page_number
                section_label = ".".join(str(current_clause["clause_id"]).split("-clause-", 1)[1].split("-")[:2]).replace("-", ".")
                section = section_by_label.get(section_label)
                if section:
                    section["citations"]["pdf_page_end"] = page_number
                    section["citations"]["bylaw_page_end"] = page_number

    return sections


def clause_refs_from_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for section in sections:
        for clause in section.get("clauses_raw") or []:
            refs.append(
                {
                    "clause_id": clause["clause_id"],
                    "section_id": section["section_id"],
                    "clause_label_raw": clause.get("clause_label_raw"),
                    "clause_path": [str(part) for part in re.findall(r"[0-9]+|[a-z]+|[ivxlcdm]+", str(clause.get("clause_label_raw") or ""))],
                    "source_order": clause.get("source_order"),
                    "citations": clause.get("citations") or section.get("citations") or {},
                }
            )
    return refs


def source_text(sections: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for section in sections:
        chunks.append(f"{section['section_label_raw']} {section['section_title_raw']}")
        for clause in section.get("clauses_raw") or []:
            if clause.get("clause_text_raw"):
                chunks.append(str(clause["clause_text_raw"]))
    return "\n".join(chunks)


def build_document(current: Any, normalizer: Any, doc: dict[str, Any], sections: list[dict[str, Any]]) -> dict[str, Any]:
    prefix = "doc-other"
    review_flags: list[dict[str, Any]] = []
    numeric_values, requirements, other_requirements = current.build_numeric_and_requirements(sections, prefix, review_flags)
    citations = {
        "pdf_page_start": doc["pdf_page_start"],
        "pdf_page_end": doc["pdf_page_end"],
        "bylaw_page_start": doc["pdf_page_start"],
        "bylaw_page_end": doc["pdf_page_end"],
    }
    structured = current.base_structured_data()
    structured.update(
        {
            "numeric_values": numeric_values,
            "requirements": requirements,
            "regulation_groups": [
                {
                    "regulation_group_id": f"{prefix}-{sorted(doc['chapters'], key=int)[0]}-regulation-group",
                    "group_title_raw": doc["title"],
                    "requirement_refs": [req["requirement_id"] for req in requirements],
                    "source_section_ref": sections[0]["section_id"] if sections else f"{prefix}-source",
                    "confidence": "medium",
                }
            ],
            "other_requirements": other_requirements,
        }
    )
    data = {
        "$schema": "../../schema/json-schema/charlottetown-bylaw-extraction.schema.json",
        "document_metadata": {
            "jurisdiction": current.JURISDICTION,
            "bylaw_name": current.BYLAW_NAME,
            "source_document_path": current.SOURCE_REL,
            "document_type": "other",
            "document_label_raw": doc["label"],
            "document_title_raw": doc["title"],
            "citations": citations,
        },
        "raw_data": {
            "source_units": [
                {
                    "source_unit_id": f"{prefix}-source",
                    "source_unit_type": "other",
                    "label_raw": doc["label"],
                    "title_raw": doc["title"],
                    "text_raw": source_text(sections),
                    "source_order": 1,
                    "citations": citations,
                }
            ],
            "sections_raw": sections,
            "clause_refs": clause_refs_from_sections(sections),
            "tables_raw": [],
            "map_references_raw": [],
        },
        "structured_data": structured,
        "review_flags": review_flags,
    }
    current.reset_review_flags(data)
    current.refresh_schema_numeric_values(data)
    for requirement in data["structured_data"].get("other_requirements") or []:
        if requirement.get("confidence") == "needs_review":
            requirement["confidence"] = "medium"
    return current.apply_zone_reference_model(current.refresh_schema_terms(normalizer, data))


def update_manifest() -> None:
    manifest = read_json(MANIFEST)
    existing = [entry for entry in manifest.get("document_files") or [] if entry.get("file") not in {doc["file"] for doc in DOCS}]
    new_entries = [
        {
            "file": doc["file"],
            "document_type": "other",
            "pdf_page_start": doc["pdf_page_start"],
            "pdf_page_end": doc["pdf_page_end"],
            "source_sections": sorted(doc["chapters"], key=int),
        }
        for doc in DOCS
    ]
    manifest["document_files"] = new_entries + existing
    limits = manifest.setdefault("known_limits", [])
    note = "Current Chapters 1-3 are extracted as document_type other artifacts for comparison with draft Parts 1-2."
    if note not in limits:
        limits.append(note)
    write_json(MANIFEST, manifest)


def main() -> None:
    current = load_current_module()
    normalizer = current.Normalizer()
    pdf = fitz.open(SOURCE)
    for doc in DOCS:
        sections = parse_sections(pdf, doc["pdf_page_start"], doc["pdf_page_end"], doc["chapters"], "doc-other")
        if not sections:
            raise RuntimeError(f"no sections extracted for {doc['file']}")
        data = build_document(current, normalizer, doc, sections)
        if data.get("review_flags"):
            raise RuntimeError(f"{doc['file']} generated review flags")
        write_json(ROOT / doc["file"], data)
    update_manifest()


if __name__ == "__main__":
    main()

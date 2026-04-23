from __future__ import annotations

import importlib.util
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "zoning" / "charlottetown-draft"
SOURCE_REL = "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf"
SCHEMA_PATH = ROOT / "schema" / "json-schema" / "charlottetown-bylaw-extraction.schema.json"
CURRENT_EXTRACTOR_PATH = ROOT / "scripts" / "extract-charlottetown-zoning-bylaw.py"
DRAFT_RAW_EXTRACTOR_PATH = ROOT / "scripts" / "extract-charlottetown-draft-zoning-bylaw.py"
CODE_TABLES = ROOT / "data" / "normalized" / "code-tables"


def load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


current = load_module("charlottetown_current_extractor", CURRENT_EXTRACTOR_PATH)
draft_raw = load_module("charlottetown_draft_raw_extractor", DRAFT_RAW_EXTRACTOR_PATH)

NORMALIZER = current.Normalizer()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_text(text: str | None) -> str:
    return current.clean_text(text)


def citation_key(citation: dict[str, Any] | None) -> tuple[int | None, int | None, int | None, int | None]:
    citation = citation or {}
    return (
        citation.get("pdf_page_start"),
        citation.get("pdf_page_end"),
        citation.get("bylaw_page_start"),
        citation.get("bylaw_page_end"),
    )


def clause_token(label: str) -> str | None:
    label = clean_text(label)
    if not label:
        return None
    match = re.fullmatch(r"\.(\d+)", label)
    if match:
        return match.group(1)
    match = re.fullmatch(r"\(([^)]+)\)", label)
    if match:
        return match.group(1)
    match = re.fullmatch(r"([ivxlcdm]+)\)", label, flags=re.IGNORECASE)
    if match:
        return match.group(1).lower()
    if re.fullmatch(r"\d+(?:\.\d+)+", label):
        return label
    return None


def enrich_sections_with_clause_paths(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for section in sections:
        section_label = clean_text(section.get("section_label_raw"))
        current_decimal: str | None = None
        current_paren: str | None = None
        for provision in section.get("provisions") or []:
            label = clean_text(provision.get("provision_label_raw"))
            token = clause_token(label)
            if label == "section":
                provision["clause_path"] = [section_label]
                current_paren = None
                continue
            if token is None:
                continue
            if re.fullmatch(r"\d+(?:\.\d+)+", token):
                provision["clause_path"] = [token]
                current_decimal = token.split(".")[-1]
                current_paren = None
                continue
            if label.startswith("."):
                current_decimal = token
                current_paren = None
                provision["clause_path"] = [section_label, current_decimal]
                continue
            if label.startswith("("):
                if current_decimal:
                    provision["clause_path"] = [section_label, current_decimal, token]
                else:
                    provision["clause_path"] = [section_label, token]
                current_paren = token
                continue
            if label.endswith(")"):
                if current_decimal and current_paren:
                    provision["clause_path"] = [section_label, current_decimal, current_paren, token]
                elif current_decimal:
                    provision["clause_path"] = [section_label, current_decimal, token]
                else:
                    provision["clause_path"] = [section_label, token]
    return sections


def attach_permitted_use_clause_paths(doc: dict[str, Any]) -> dict[str, Any]:
    available: dict[tuple[str, str, tuple[int | None, int | None, int | None, int | None]], list[list[str]]] = defaultdict(list)
    for section in doc.get("requirement_sections") or []:
        title = clean_text(section.get("title_label_raw"))
        if "PERMITTED USE" not in title:
            continue
        for provision in section.get("provisions") or []:
            path = provision.get("clause_path")
            label = clean_text(provision.get("provision_label_raw"))
            text = clean_text(provision.get("text"))
            if not path or not label or not text:
                continue
            key = (label, text, citation_key(provision.get("citations")))
            available[key].append(list(path))

    for item in doc.get("permitted_uses") or []:
        key = (
            clean_text(item.get("clause_label_raw")),
            clean_text(item.get("use_name")),
            citation_key(item.get("citations")),
        )
        paths = available.get(key)
        if paths:
            item["clause_path"] = paths.pop(0)
    return doc


def preprocess_zone_legacy(doc: dict[str, Any]) -> dict[str, Any]:
    enrich_sections_with_clause_paths(doc.get("requirement_sections") or [])
    attach_permitted_use_clause_paths(doc)
    return doc


def preprocess_sections_legacy(doc: dict[str, Any]) -> dict[str, Any]:
    enrich_sections_with_clause_paths(doc.get("sections") or [])
    return doc


def transform_zone_doc(path: Path) -> dict[str, Any]:
    legacy = preprocess_zone_legacy(read_json(path))
    data = current.transform_zone(NORMALIZER, legacy)
    current.refresh_schema_numeric_values(data)
    current.refresh_schema_terms(NORMALIZER, data)
    current.apply_zone_reference_model(data)
    return data


def transform_supporting_doc(path: Path, document_type: str) -> dict[str, Any]:
    legacy = preprocess_sections_legacy(read_json(path))
    data = current.transform_sections_doc(NORMALIZER, legacy, document_type)
    current.refresh_schema_numeric_values(data)
    current.refresh_schema_terms(NORMALIZER, data)
    current.apply_zone_reference_model(data)
    return data


def transform_definitions_doc(path: Path) -> dict[str, Any]:
    data = current.transform_definitions(NORMALIZER, read_json(path))
    current.refresh_schema_terms(NORMALIZER, data)
    return data


def transform_schedule_doc(path: Path) -> dict[str, Any]:
    legacy = read_json(path)
    metadata = legacy.get("document_metadata") or {}
    source = legacy.get("source_section") or {}
    prefix = f"schedule-{current.slugify(source.get('section_label_raw') or path.stem)}"
    pages_raw = []
    for index, block in enumerate(legacy.get("content_blocks") or [], start=1):
        cite = current.citation(block.get("citations") or source)
        pages_raw.append(
            {
                "page_id": f"{prefix}-page-{index}",
                "pdf_page": cite.get("pdf_page_start"),
                "bylaw_page": cite.get("bylaw_page_start"),
                "text_raw": block.get("text") or "",
                "source_order": index,
            }
        )
    map_ref_id = f"{prefix}-map"
    cite = current.citation(source)
    return {
        "$schema": "../../schema/json-schema/charlottetown-bylaw-extraction.schema.json",
        "document_metadata": {
            "jurisdiction": metadata.get("jurisdiction") or current.JURISDICTION,
            "bylaw_name": metadata.get("bylaw_name") or "Draft Zoning & Development Bylaw",
            "source_document_path": metadata.get("source_document_path") or SOURCE_REL,
            "document_type": "other",
            "citations": cite,
        },
        "raw_data": {
            "source_units": [
                {
                    "source_unit_id": f"{prefix}-source",
                    "source_unit_type": "schedule_map",
                    "label_raw": source.get("section_label_raw") or "",
                    "title_raw": source.get("title_label_raw") or "",
                    "text_raw": "\n".join(page["text_raw"] for page in pages_raw),
                    "source_order": 1,
                    "citations": cite,
                }
            ],
            "clause_refs": [],
            "tables_raw": [],
            "map_references_raw": [
                {
                    "map_reference_id": map_ref_id,
                    "map_label_raw": source.get("section_label_raw") or "",
                    "map_title_raw": source.get("title_label_raw") or "",
                    "text_raw": "\n".join(page["text_raw"] for page in pages_raw),
                    "citations": cite,
                }
            ],
            "pages_raw": pages_raw,
        },
        "structured_data": {
            **current.base_structured_data(),
            "map_layer_references": [
                {
                    "map_reference_id": map_ref_id,
                    "map_title_raw": source.get("title_label_raw") or "",
                    "map_label_raw": source.get("section_label_raw") or "",
                    "map_reference_type": "other",
                    "feature_key": current.slugify(source.get("title_label_raw") or path.stem),
                    "source_refs": [current.source_ref("map_reference", map_ref_id)],
                    "confidence": "medium",
                }
            ],
        },
        "review_flags": [
            current.make_review_flag(
                f"{prefix}-flag-schedule-review",
                "schedule_map_review",
                "Schedule map text is preserved by page and requires spatial QA before downstream use.",
                [current.source_ref("map_reference", map_ref_id)],
            )
        ],
    }


def load_seed_entries(table: str) -> list[dict[str, Any]]:
    return read_json(CODE_TABLES / f"{table}.seed.json")["entries"]


def exact_match_keys(entry: dict[str, Any]) -> set[str]:
    keys = {current.code_key(entry.get("code")), current.code_key(entry.get("label"))}
    metadata = entry.get("metadata") or {}
    for alias in metadata.get("aliases") or []:
        keys.add(current.code_key(alias))
    symbol = entry.get("symbol")
    if symbol:
        keys.add(current.code_key(symbol))
    return {key for key in keys if key}


def classify_match(raw: str, entry: dict[str, Any]) -> str:
    return "exact" if current.code_key(raw) in exact_match_keys(entry) else "semantic"


def build_code_match_report(doc_paths: list[Path]) -> dict[str, Any]:
    seeds = {
        "term": {entry["code"]: entry for entry in load_seed_entries("term")},
        "use": {entry["code"]: entry for entry in load_seed_entries("use")},
    }
    report: dict[str, Any] = {
        "source_document_path": SOURCE_REL,
        "generated_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "tables": {
            "term": {"exact_matches": [], "semantic_matches": [], "new_codes": []},
            "use": {"exact_matches": [], "semantic_matches": [], "new_codes": []},
        },
    }
    seen: dict[str, set[tuple[str, str]]] = {"term": set(), "use": set()}

    for path in doc_paths:
        data = read_json(path)
        structured = data.get("structured_data") or {}
        used_term_ids = {use.get("use_term_id") for use in structured.get("uses") or [] if use.get("use_term_id")}
        for term in structured.get("terms") or []:
            table = term.get("code_table")
            raw = term.get("term_raw") or term.get("term_normalized") or ""
            if not raw or term.get("term_category") == "document_reference":
                continue
            if table not in {"term", "use"}:
                table = "use" if term.get("term_id") in used_term_ids else "term"
            code = term.get("code") or term.get("term_normalized")
            key = (raw, code or "")
            if key in seen[table]:
                continue
            seen[table].add(key)
            if code and code in seeds[table]:
                entry = seeds[table][code]
                bucket = "exact_matches" if classify_match(raw, entry) == "exact" else "semantic_matches"
                report["tables"][table][bucket].append(
                    {
                        "raw": raw,
                        "matched_code": code,
                        "matched_label": entry.get("label"),
                        "source_file": path.relative_to(ROOT).as_posix(),
                    }
                )
            else:
                report["tables"][table]["new_codes"].append(
                    {
                        "raw": raw,
                        "suggested_code": current.code_key(raw),
                        "source_file": path.relative_to(ROOT).as_posix(),
                    }
                )

    for table_payload in report["tables"].values():
        for key in ("exact_matches", "semantic_matches", "new_codes"):
            table_payload[key].sort(key=lambda item: (item["raw"].lower(), item.get("matched_code") or item.get("suggested_code") or ""))
    return report


def validate_outputs(doc_paths: list[Path]) -> None:
    schema = read_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for path in doc_paths:
        payload = read_json(path)
        for error in validator.iter_errors(payload):
            location = "/".join(str(part) for part in error.path)
            errors.append(f"{path.relative_to(ROOT).as_posix()}: {location}: {error.message}")
    if errors:
        raise RuntimeError("Schema validation failed:\n" + "\n".join(errors[:100]))


def build_manifest(doc_paths: list[Path]) -> dict[str, Any]:
    zones = []
    document_files = []
    schedules = []
    for path in sorted(doc_paths):
        payload = read_json(path)
        metadata = payload.get("document_metadata") or {}
        citations = metadata.get("citations") or {}
        rel = path.relative_to(OUT).as_posix()
        if "/zones/" in f"/{rel}":
            zones.append(
                {
                    "zone_code": metadata.get("zone_code"),
                    "zone_name": metadata.get("zone_name"),
                    "file": rel,
                    **citations,
                }
            )
        elif "/schedules/" in f"/{rel}":
            schedules.append(
                {
                    "file": rel,
                    "title": ((payload.get("raw_data") or {}).get("source_units") or [{}])[0].get("title_raw"),
                    **citations,
                }
            )
        else:
            document_files.append(
                {
                    "file": rel,
                    "document_type": metadata.get("document_type"),
                    "document_title_raw": metadata.get("document_title_raw"),
                    **citations,
                }
            )
    return {
        "source_document_path": SOURCE_REL,
        "extracted_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "extractor": "scripts/regenerate-charlottetown-draft-zoning-bylaw.py",
        "bylaw_name": "Draft Zoning & Development Bylaw",
        "jurisdiction": "City of Charlottetown",
        "zone_count": len(zones),
        "zones": zones,
        "document_files": document_files,
        "schedules": schedules,
        "known_limits": [
            "Draft outputs are normalized into the approved Charlottetown extraction schema.",
            "Code-table matches reuse reviewed current Charlottetown seed files; unmatched phrases are preserved with review flags and summarized in code-table-match-report.json.",
            "Draft schedule map files preserve page text only and still require spatial QA before downstream use.",
            "Any raw PDF ordering defects that survive the source extraction pass remain surfaced through review flags rather than silent normalization.",
        ],
    }


def write_readme(report: dict[str, Any], manifest: dict[str, Any]) -> None:
    term_table = report["tables"]["term"]
    use_table = report["tables"]["use"]
    text = f"""# Charlottetown Draft Zoning & Development Bylaw extraction

Source: `{SOURCE_REL}`.

This folder contains approved-schema draft zoning bylaw extraction outputs regenerated from the April 9, 2026 draft PDF. Draft zone and supporting JSON files follow `schema/json-schema/charlottetown-bylaw-extraction.schema.json`.

## Coverage

- Zone files: {manifest["zone_count"]}
- Supporting document files: {len(manifest["document_files"])}
- Schedule files: {len(manifest["schedules"])}

## Code-table matching

- Term exact matches: {len(term_table["exact_matches"])}
- Term semantic matches: {len(term_table["semantic_matches"])}
- Term new codes surfaced: {len(term_table["new_codes"])}
- Use exact matches: {len(use_table["exact_matches"])}
- Use semantic matches: {len(use_table["semantic_matches"])}
- Use new codes surfaced: {len(use_table["new_codes"])}

See `code-table-match-report.json` for phrase-level details.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def run_raw_extraction() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    draft_raw.main()


def main() -> None:
    run_raw_extraction()

    generated_paths: list[Path] = []
    transformed_payloads: dict[Path, dict[str, Any]] = {}

    manifest = read_json(OUT / "source-manifest.json")
    for zone in manifest.get("zones") or []:
        path = OUT / zone["file"]
        transformed_payloads[path] = transform_zone_doc(path)
        generated_paths.append(path)

    for item in manifest.get("supporting_documents") or []:
        path = OUT / item["file"]
        doc_type = item.get("document_type")
        if doc_type == "definitions":
            transformed_payloads[path] = transform_definitions_doc(path)
        elif doc_type in {"general_provisions", "design_standards"}:
            transformed_payloads[path] = transform_supporting_doc(path, doc_type)
        else:
            transformed_payloads[path] = transform_supporting_doc(path, "other")
        generated_paths.append(path)

    for item in manifest.get("schedules") or []:
        path = OUT / item["file"]
        transformed_payloads[path] = transform_schedule_doc(path)
        generated_paths.append(path)

    maps_path = OUT / "maps.json"
    if maps_path.exists():
        maps_path.unlink()
    notes_path = OUT / "extraction-notes.md"
    if notes_path.exists():
        notes_path.unlink()

    for path, payload in transformed_payloads.items():
        write_json(path, payload)

    validate_outputs(generated_paths)
    report = build_code_match_report(generated_paths)
    write_json(OUT / "code-table-match-report.json", report)
    fresh_manifest = build_manifest(generated_paths)
    write_json(OUT / "source-manifest.json", fresh_manifest)
    write_readme(report, fresh_manifest)


if __name__ == "__main__":
    main()

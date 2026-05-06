from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "data" / "zoning" / "charlottetown"
SOURCE = ROOT / "general-provisions.json"
MANIFEST = ROOT / "source-manifest.json"


TARGETS = [
    {
        "file": "general-provisions-buildings-structures.json",
        "label": "Chapter 4",
        "title": "GENERAL PROVISIONS FOR BUILDINGS AND STRUCTURES",
        "prefixes": {"4"},
    },
    {
        "file": "general-provisions-land-use.json",
        "label": "Chapter 5",
        "title": "GENERAL PROVISIONS FOR LAND USE",
        "prefixes": {"5"},
    },
    {
        "file": "general-provisions-lots-site-design.json",
        "label": "Chapter 6",
        "title": "GENERAL PROVISIONS FOR LOTS AND SITE DESIGN",
        "prefixes": {"6"},
    },
    {
        "file": "general-provisions-parking.json",
        "label": "Chapter 46",
        "title": "PARKING",
        "prefixes": {"46"},
    },
    {
        "file": "general-provisions-signage.json",
        "label": "Chapter 47",
        "title": "SIGNAGE",
        "prefixes": {"47"},
    },
    {
        "file": "general-provisions-subdividing-land.json",
        "label": "Chapter 48",
        "title": "SUBDIVIDING LAND",
        "prefixes": {"48"},
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def section_prefix(section: dict[str, Any]) -> str:
    label = str(section.get("section_label_raw") or "")
    return label.split(".", 1)[0]


def citations_for(sections: list[dict[str, Any]]) -> dict[str, int]:
    starts: list[int] = []
    ends: list[int] = []
    for section in sections:
        citations = section.get("citations") or {}
        for key in ("pdf_page_start", "bylaw_page_start"):
            if citations.get(key) is not None:
                starts.append(int(citations[key]))
        for key in ("pdf_page_end", "bylaw_page_end"):
            if citations.get(key) is not None:
                ends.append(int(citations[key]))
    if not starts or not ends:
        return {}
    page_start = min(starts)
    page_end = max(ends)
    return {
        "pdf_page_start": page_start,
        "pdf_page_end": page_end,
        "bylaw_page_start": page_start,
        "bylaw_page_end": page_end,
    }


def clause_ids_for(sections: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for section in sections:
        for clause in section.get("clauses_raw") or []:
            if clause.get("clause_id"):
                ids.add(clause["clause_id"])
    return ids


def table_ids_for(sections: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for section in sections:
        for table in section.get("tables_raw") or []:
            if table.get("table_id"):
                ids.add(table["table_id"])
    return ids


def item_refs(item: dict[str, Any]) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for key in ("source_refs", "source_references"):
        for ref in item.get(key) or []:
            ref_type = ref.get("source_ref_type")
            ref_id = ref.get("source_ref_id")
            if ref_type and ref_id:
                refs.add((str(ref_type), str(ref_id)))
    for key in ("source_ref", "target_ref"):
        ref = item.get(key)
        if isinstance(ref, dict) and ref.get("source_ref_type") and ref.get("source_ref_id"):
            refs.add((str(ref["source_ref_type"]), str(ref["source_ref_id"])))
    return refs


def keep_structured_item(item: dict[str, Any], section_ids: set[str], clause_ids: set[str], table_ids: set[str]) -> bool:
    refs = item_refs(item)
    if not refs:
        return False
    for ref_type, ref_id in refs:
        if ref_type == "section" and ref_id in section_ids:
            return True
        if ref_type == "clause" and ref_id in clause_ids:
            return True
        if ref_type in {"table", "raw_table", "table_row", "table_cell"} and any(ref_id.startswith(table_id) for table_id in table_ids):
            return True
    return False


def build_source_text(sections: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for section in sections:
        title = section.get("section_title_raw")
        if title:
            chunks.append(str(title))
        for clause in section.get("clauses_raw") or []:
            text = clause.get("clause_text_raw")
            if text:
                chunks.append(str(text))
    return "\n".join(chunks)


def main() -> None:
    source = read_json(SOURCE)
    sections = source["raw_data"]["sections_raw"]
    seen_sections: set[str] = set()
    new_manifest_entries: list[dict[str, Any]] = []

    for target in TARGETS:
        target_sections = [deepcopy(section) for section in sections if section_prefix(section) in target["prefixes"]]
        if not target_sections:
            raise RuntimeError(f"no sections matched {target['file']}")

        for section in target_sections:
            section_id = section["section_id"]
            if section_id in seen_sections:
                raise RuntimeError(f"section assigned twice: {section_id}")
            seen_sections.add(section_id)

        section_ids = {section["section_id"] for section in target_sections}
        clause_ids = clause_ids_for(target_sections)
        table_ids = table_ids_for(target_sections)
        citations = citations_for(target_sections)

        output = deepcopy(source)
        metadata = output["document_metadata"]
        metadata["document_label_raw"] = target["label"]
        metadata["document_title_raw"] = target["title"]
        metadata["citations"] = citations

        source_unit = deepcopy(output["raw_data"]["source_units"][0])
        source_unit["label_raw"] = target["label"]
        source_unit["title_raw"] = target["title"]
        source_unit["text_raw"] = build_source_text(target_sections)
        source_unit["citations"] = citations

        output["raw_data"]["source_units"] = [source_unit]
        output["raw_data"]["sections_raw"] = target_sections
        output["raw_data"]["clause_refs"] = [
            ref for ref in output["raw_data"].get("clause_refs") or [] if ref.get("clause_id") in clause_ids
        ]
        output["raw_data"]["tables_raw"] = [
            table for table in output["raw_data"].get("tables_raw") or [] if table.get("table_id") in table_ids
        ]
        output["raw_data"]["map_references_raw"] = [
            ref for ref in output["raw_data"].get("map_references_raw") or [] if keep_structured_item(ref, section_ids, clause_ids, table_ids)
        ]

        structured = output["structured_data"]
        for key, value in list(structured.items()):
            if not isinstance(value, list):
                continue
            if key == "regulation_groups":
                requirements = {
                    req["requirement_id"]
                    for req in structured.get("requirements") or []
                    if keep_structured_item(req, section_ids, clause_ids, table_ids)
                }
                groups = []
                for group in value:
                    kept_refs = [req_id for req_id in group.get("requirement_refs") or [] if req_id in requirements]
                    if kept_refs:
                        new_group = deepcopy(group)
                        new_group["regulation_group_id"] = f"doc-general-provisions-{target['prefixes'].copy().pop()}-regulation-group"
                        new_group["group_title_raw"] = target["title"]
                        new_group["requirement_refs"] = kept_refs
                        new_group["source_section_ref"] = target_sections[0]["section_id"]
                        groups.append(new_group)
                structured[key] = groups
            else:
                structured[key] = [
                    item for item in value if isinstance(item, dict) and keep_structured_item(item, section_ids, clause_ids, table_ids)
                ]

        output["review_flags"] = [
            flag for flag in output.get("review_flags") or [] if keep_structured_item(flag, section_ids, clause_ids, table_ids)
        ]

        write_json(ROOT / target["file"], output)
        new_manifest_entries.append(
            {
                "file": target["file"],
                "document_type": "general_provisions",
                "pdf_page_start": citations.get("pdf_page_start"),
                "pdf_page_end": citations.get("pdf_page_end"),
                "source_sections": sorted(target["prefixes"], key=int),
            }
        )

    original_sections = {section["section_id"] for section in sections}
    if seen_sections != original_sections:
        missing = sorted(original_sections - seen_sections)
        extra = sorted(seen_sections - original_sections)
        raise RuntimeError(f"split mismatch missing={missing} extra={extra}")

    manifest = read_json(MANIFEST)
    manifest["document_files"] = [
        entry for entry in manifest.get("document_files") or [] if entry.get("file") != "general-provisions.json"
    ]
    insertion = 0
    manifest["document_files"][insertion:insertion] = new_manifest_entries
    limits = manifest.setdefault("known_limits", [])
    note = "Current general provisions are split into themed Chapter 4, 5, 6, 46, 47, and 48 JSON artifacts."
    if note not in limits:
        limits.append(note)
    write_json(MANIFEST, manifest)
    SOURCE.unlink()


if __name__ == "__main__":
    main()

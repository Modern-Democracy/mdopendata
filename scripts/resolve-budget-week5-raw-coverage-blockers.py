"""Add raw table-manifest coverage for Week 5 prior-year raw-blocked pages."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown"
REVIEW = BASE / "week-5-normalized-mapping-review.json"

TABLE_TYPE_BY_FAMILY = {
    "capital_budget_schedule": "capital_budget_table",
    "capital_project_profile": "capital_project_profile",
    "debt_schedule": "debt_schedule",
    "facility_operating_statement": "third_party_facility_operating_budget",
    "operating_detail": "operating_budget_detail",
    "operating_statement": "operating_budget_summary",
    "tax_assessment_rate": "tax_or_utility_rate_schedule",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def ensure_page_text(document_dir: Path, page: int) -> None:
    raw_path = document_dir / "raw-pages" / f"page-{page:03d}.txt"
    profile_path = document_dir / "profile-raw-pages" / f"page-{page:03d}.txt"
    if not profile_path.exists():
        return
    if not raw_path.exists() or line_count(raw_path) <= 1:
        raw_path.write_text(profile_path.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    review = load(REVIEW)
    changes = []
    for document in review["documents"]:
        document_key = document["document_key"]
        document_dir = BASE / document_key
        table_manifest_path = document_dir / "table_manifest.json"
        page_inventory_path = document_dir / "page_inventory.json"
        table_manifest = load(table_manifest_path)
        page_inventory = load(page_inventory_path)
        tables = table_manifest["records"]
        existing_pages = {int(item["page_start"]) for item in tables}
        page_records = {int(item["page_number"]): item for item in page_inventory["records"]}
        added_pages = []
        for record in document["records"]:
            if record["disposition"] != "raw_blocked":
                continue
            page = int(record["page_start"])
            ensure_page_text(document_dir, page)
            page_record = page_records.get(page)
            if page_record:
                page_record["has_table"] = True
                page_record["content_type"] = (
                    "project_profile"
                    if record["table_family"] == "capital_project_profile"
                    else "table"
                )
                page_record["extraction_priority"] = "high"
                note = "supplemental raw table coverage from profiler candidate"
                if note not in page_record["notes"]:
                    page_record["notes"].append(note)
            if page in existing_pages:
                continue
            table_type = TABLE_TYPE_BY_FAMILY[record["table_family"]]
            tables.append(
                {
                    "table_id": f"ctown_budget_2026_2027_p{page:03d}",
                    "page_start": page,
                    "page_end": page,
                    "title": record["table_key"],
                    "table_type": table_type,
                    "section": record["section"],
                    "subsection": None,
                    "entity": (record.get("entities") or [None])[0],
                    "department": None,
                    "columns_observed": ["raw_label", "raw_value"],
                    "numeric_years": record.get("periods") or [],
                    "row_count_estimate": 0,
                    "confidence": "low",
                    "needs_manual_review": True,
                    "notes": ["supplemental raw table coverage from normalized mapping review"],
                }
            )
            added_pages.append(page)
            existing_pages.add(page)
        if added_pages:
            tables.sort(key=lambda item: (int(item["page_start"]), item["table_id"]))
            table_manifest["table_count"] = len(tables)
            write(table_manifest_path, table_manifest)
            write(page_inventory_path, page_inventory)
            changes.append({"document_key": document_key, "added_pages": added_pages})
    print(json.dumps({"changes": changes}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

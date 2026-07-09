"""Build Week 5 normalized mapping review artifacts for prior budget documents."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/budget/charlottetown"
OUTPUT = BASE / "week-5-normalized-mapping-review.json"
DOCUMENTS = ("2025-2026", "2024-2025")

FAMILY_BASELINE = {
    "operating_statement",
    "operating_detail",
    "facility_operating_statement",
    "capital_budget_schedule",
    "capital_project_profile",
    "tax_assessment_rate",
    "debt_schedule",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_period(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "")
        .replace("/", "-")
        .replace("2024-25", "2024-2025")
        .replace("2025-26", "2025-2026")
        .replace("2026-27", "2026-2027")
        .replace("2023-24", "2023-2024")
    )


def expected_periods(document_key: str) -> set[str]:
    start = int(document_key[:4])
    return {f"{start}-{start + 1}", f"{start - 1}-{start}"}


def disposition_for(record: dict, raw_pages: set[int], document_key: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    family = record["table_family"]
    page = int(record["page_start"])
    if page not in raw_pages:
        reasons.append("profile candidate lacks matching full-2 raw table")
    if family not in FAMILY_BASELINE:
        reasons.append("table family is not in the approved 2026/2027 mapping baseline")
    periods = {normalize_period(value) for value in record.get("periods") or []}
    unsupported_periods = sorted(
        value
        for value in periods
        if value.startswith("20") and value not in expected_periods(document_key)
    )
    if unsupported_periods and family not in {"capital_project_profile", "debt_schedule"}:
        reasons.append(f"period labels require review: {', '.join(unsupported_periods)}")
    if record.get("continuation_candidate"):
        reasons.append("continuation membership requires section-level review")
    if family == "capital_project_profile":
        reasons.append("project alias requires cross-year review")
    if family == "debt_schedule":
        reasons.append("debt instrument identity and maturity labels require review")
    if family == "tax_assessment_rate":
        reasons.append("assessment/rate operands require formula review")
    if page not in raw_pages:
        return "raw_blocked", reasons
    if reasons:
        return "review_blocked", reasons
    return "candidate_equivalent", ["profile family and period labels fit baseline review inputs"]


def build_document(document_key: str) -> dict:
    base = BASE / document_key
    profile = load(base / "profile_table_inventory.json")["records"]
    raw = load(base / "table_manifest.json")["records"]
    raw_summary = load(base / "raw-tables/raw_row_value_summary.json")
    raw_pages = {int(item["page_start"]) for item in raw}
    raw_by_page = {int(item["page_start"]): item for item in raw}
    records = []
    for record in profile:
        disposition, reasons = disposition_for(record, raw_pages, document_key)
        raw_match = raw_by_page.get(int(record["page_start"]))
        records.append(
            {
                "table_key": record["table_key"],
                "page_start": record["page_start"],
                "section": record["section"],
                "table_family": record["table_family"],
                "column_pattern": record["column_pattern"],
                "periods": record.get("periods") or [],
                "entities": record.get("entities") or [],
                "raw_table_id": raw_match["table_id"] if raw_match else None,
                "disposition": disposition,
                "review_reasons": reasons,
            }
        )
    disposition_counts = Counter(item["disposition"] for item in records)
    family_counts = Counter(item["table_family"] for item in records)
    raw_gaps = [item for item in records if item["disposition"] == "raw_blocked"]
    grouped = defaultdict(list)
    for item in records:
        grouped[item["disposition"]].append(item["table_key"])
    return {
        "document_key": document_key,
        "profile_candidate_count": len(profile),
        "full2_raw_table_count": len(raw),
        "raw_row_count": raw_summary["row_count"],
        "raw_value_count": raw_summary["value_count"],
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "raw_gap_pages": [item["page_start"] for item in raw_gaps],
        "raw_gap_count": len(raw_gaps),
        "records": records,
        "review_groups": {key: value for key, value in sorted(grouped.items())},
    }


def main() -> int:
    payload = {
        "schema_version": 1,
        "status": "review_package",
        "documents": [build_document(document) for document in DOCUMENTS],
        "normalization_authorized": False,
        "publication_snapshot_authorized": False,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for document in payload["documents"]:
        print(
            document["document_key"],
            document["profile_candidate_count"],
            document["full2_raw_table_count"],
            document["disposition_counts"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

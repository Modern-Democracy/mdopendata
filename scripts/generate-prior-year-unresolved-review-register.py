import html
import json
from pathlib import Path


BASE = Path("data/budget/charlottetown")
OUTPUT = Path("output/budget/prior-year-phase-2-unresolved-review-register.md")


def proposal(year, page, family, values):
    if year == "2024-2025" and page in {14, 15, 16}:
        if not values:
            return (
                "No numeric source values are present; the row may be a document, entity, period, section, or column header.",
                "Treat as non-additive source context unless visual review shows an omitted amount.",
            )
        return (
            "The three-column summary layout mixes City and Water and Sewer rows; the row hierarchy and reporting entity are not yet fixed.",
            "Preserve the label; map each visible CAD value to 2023/24 budget, 2023/24 forecast, and 2024/25 budget only after confirming its City or Water and Sewer section.",
        )
    if year == "2024-2025" and page in {82, 83, 84, 85, 86}:
        if not values:
            return (
                "No numeric source values are present; this may be a third-party operating-statement heading or grouping row.",
                "Map as non-additive context and retain the Charlottetown Civic Centre Management Inc. reporting scope.",
            )
        return (
            "The third-party statement needs entity, hierarchy, and period-role confirmation before its amount can be comparable with City operating data.",
            "Best guess: map the visible CAD value(s) as 2024/25 budget detail, subtotal, or total under Charlottetown Civic Centre Management Inc.; do not claim cross-entity comparability.",
        )
    if year == "2024-2025" and family == "capital_budget_schedule":
        return (
            "The project label includes a calendar year or phased work, which could be misread as a reporting period or separate project.",
            "Treat the year/phase as part of the raw project label and map the visible amount as 2024/25 capital-budget expenditure.",
        )
    if year == "2024-2025" and family == "facility_operating_statement":
        return (
            "A dash or missing first amount cell prevents a complete two-budget-column mapping.",
            "Treat the dash as calculation-zero, preserve the source display, and map the available amount to its visually confirmed budget column.",
        )
    if year == "2025-2026" and page in {17, 18}:
        return (
            "The early detailed-breakdown pages have non-contiguous or incomplete value columns relative to the three-period header.",
            "Visually confirm each column position; then map only the aligned 2024/25 budget, 2024/25 forecast, and 2025/26 budget CAD values.",
        )
    if year == "2025-2026" and page in {28, 29, 64, 65, 66, 67, 68, 69, 70}:
        return (
            "The raw label is blank or wrapped across adjacent rows, so the value cannot be assigned safely to a line item or subtotal.",
            "Reconstruct the label from the preceding/following visible rows; map it as a 2025/26 budget detail or subtotal only after the parent category is confirmed.",
        )
    if year == "2025-2026" and page in {97, 98}:
        return (
            "The row has no recoverable label/value alignment in the operating-statement extraction.",
            "Visually inspect the page and classify as non-additive context, or reconstruct its label and period role before creating a fact.",
        )
    if year == "2025-2026" and family == "facility_operating_statement":
        return (
            "The Sponsorship row is dash-only in the relevant budget column and lacks a complete source value mapping.",
            "Treat the dash as calculation-zero while preserving the source display; map a reported-zero fact only if a source-cell identifier is recovered.",
        )
    return (
        "The raw row requires explicit hierarchy, aggregation role, period role, or reporting-scope confirmation.",
        "Preserve the raw label and values; map only after visual confirmation establishes its detail, subtotal, total, or context role.",
    )


def esc(value):
    return html.escape(value).replace("|", "\\|").replace("\n", " ")


def main():
    lines = [
        "# Prior-Year Phase 2 Unresolved Row Review Register",
        "",
        "Generated from the Phase 2 unresolved-review artifacts after commit `bd9433e`. Each entry identifies one unresolved raw row and a provisional resolution. Proposed resolutions require confirmation before regeneration.",
        "",
    ]
    count = 0
    for year in ("2024-2025", "2025-2026"):
        root = BASE / year
        report = json.loads((root / "phase-2-unresolved-review-report.json").read_text(encoding="utf-8"))
        raw_values = json.loads((root / "raw-tables/source_values.json").read_text(encoding="utf-8"))
        values_by_id = {value["value_id"]: value["raw_value"] for value in raw_values["records"]}
        lines.extend([f"## {year}", "", "| PDF page | Row ID | Raw label | Values | Ambiguity | Proposed resolution |", "| ---: | --- | --- | --- | --- | --- |"])
        for row in report["records"]:
            values = [values_by_id.get(value_id, value_id) for value_id in row["source_value_ids"]]
            ambiguity, resolution = proposal(year, row["page_start"], row["table_family"], values)
            lines.append(
                f"| {row['page_start']} | `{row['row_id']}` | {esc(row['raw_label']) or '_blank_'} | {esc('; '.join(values)) or '_none_'} | {esc(ambiguity)} | {esc(resolution)} |"
            )
            count += 1
        lines.append("")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {count} rows to {OUTPUT}")


if __name__ == "__main__":
    main()

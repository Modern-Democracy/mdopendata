# Charlottetown Draft Zoning & Development Bylaw extraction

Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`.

This folder contains a non-normalized source extraction for the City of Charlottetown draft Zoning & Development Bylaw dated April 7, 2026. The extraction is intended for a later normalization pass. It preserves raw provision labels, raw legal text, citations, and review issues.

## Organization

- `zones/*.json`: one file per zone or zoning district from Parts 10 through 29.
- `source-manifest.json`: inventory of extracted zones, source pages, and known limits.
- `extraction-notes.md`: reproducibility notes and QA guidance.

## Extraction status

- Zone part scope: Parts 10-29, bylaw pages 87-162.
- Zone count: 20.
- PDF page numbers and visible bylaw page numbers are recorded separately.
- Dimensional requirements are preserved as text in `requirement_sections`. They are not normalized into database-ready dimensional records.
- Clause labels such as `.1`, `(a)`, and `i)` are preserved exactly as extracted and listed in `pending_review_clause_patterns` when encountered.

## Known limits

- PDF text order does not always match visual order around columns, tables, figures, and schedules.
- Table and figure labels are preserved for review and are not converted into normalized rows.
- Schedule maps are not spatially extracted in this source JSON pass.

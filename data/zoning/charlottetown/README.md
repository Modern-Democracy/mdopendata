# Charlottetown Zoning & Development Bylaw extraction

Source: `docs/charlottetown/charlottetown-zoning-bylaw.pdf`.

This folder contains a non-normalized source extraction for the City of Charlottetown Zoning & Development Bylaw (PH-ZD.2 rev 049). The extraction is intended for a later normalization pass. It preserves raw legal text, raw provision labels, table-derived text, citations, and review issues.

## Organization

- `zones/*.json`: one file per zone or zoning district from chapters 9 through 45.
- `appendix-b-cda-parcels-and-permitted-uses.json`: preserved CDA parcel/permitted-use appendix text by PDF page.
- `appendix-c-approved-site-specific-exemptions.json`: preserved site-specific exemption appendix text by PDF page.
- `source-manifest.json`: inventory of extracted chapters, source pages, and known extraction limits.

## Extraction status

- Zone chapter scope: chapters 9-45, PDF pages 61-123.
- Bylaw page numbers are recorded as matching the visible page number in the PDF header.
- Clear decimal provisions such as `9.1.1` are preserved raw and represented as single clause path units.
- Clear lettered list provisions such as `a.` and `b.` are split into separate provisions when extracted as separate PDF lines.
- Dimensional tables are preserved as requirement section provisions with raw table text. They are not normalized into dimensional regulation records.

## Known limits

- PDF text extraction does not preserve all table column alignment. Table-derived sections have `table_parsing_review` open issues.
- Appendix B and Appendix C are preserved as page-level content blocks rather than parsed table rows.
- The source PDF cover identifies rev 049 updated March 9, 2026, while many zone pages display rev 048 updated October 24, 2025 in the page header. A `source_revision_review` issue is recorded on affected zone files.
- The WLOS/WL-OS zone symbol discrepancy is preserved for review in the `WL-OS` zone file.

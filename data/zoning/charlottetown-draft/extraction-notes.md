# Charlottetown draft extraction notes

Extractor: `scripts/extract-charlottetown-draft-zoning-bylaw.py`.

Method:

- Uses `pypdf` text extraction against the draft PDF.
- Uses the table of contents page ranges to split zone parts.
- Parses labeled sections such as `10.3 PERMITTED USES`.
- Parses raw provision labels that appear at line starts: `.1`, `(a)`, and roman labels such as `i)`.
- Extracts permitted uses only from sections whose titles contain `PERMITTED USE`.

QA checks recommended before normalization:

- Compare each zone's `requirement_sections` against the visual PDF where `table_parsing_review` or `layout_order_review` is present.
- Verify that table/figure text has not shifted between adjacent provisions.
- Verify unassigned text in `content_blocks` for RN, RM, and any other zone with `zone_boundary_review`.
- Confirm whether raw label patterns `.1`, `(a)`, and `i)` should be added to the approved hierarchy policy for this bylaw.

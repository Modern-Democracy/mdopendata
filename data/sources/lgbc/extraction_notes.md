# LGBC Source Registration Notes

## Source

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Source id | `lgbc-2008-4th-edition` |
| Title | `Local Government in British Columbia - 4th Edition` |
| PDF pages | 250 |
| SHA-256 | `57D8C1762E354BA871B4408C85FD6B76A8F895A8926BDA0951C21600D16F9D8E` |

## Phase 1 Artifacts

| Artifact | Status | Notes |
| --- | --- | --- |
| `pdfinfo.txt` | complete | Generated from `pdfinfo docs\LGBC-All.pdf`. |
| `full_text_layout.txt` | complete | Generated from `pdftotext -layout`. |
| `pages_text/NNN.txt` | complete | One layout text file per PDF page, `001.txt` through `250.txt`. |
| `structure_index.json` | registered | Skeleton only; chapter and section extraction is Phase 2. |
| `exhibit_index.json` | registered | Skeleton only; exhibit extraction is Phase 2. |
| `chapter_review_queue.json` | registered | Skeleton only; queue population is Phase 3. |

## Phase 2 Artifacts

| Artifact | Status | Notes |
| --- | --- | --- |
| `structure_index.json` | complete | Populated from the extracted table of contents with front matter, 13 chapters, 78 numbered chapter sections, appendix sections, and back matter. |
| `exhibit_index.json` | complete | Populated from the extracted exhibit list with 41 listed exhibits. |
| `chapter_review_queue.json` | complete | Populated with 18 review records: 13 chapters, 1 appendix, and 4 back-matter units. |

## PDF Metadata Observations

- The PDF is unencrypted.
- The PDF has 250 pages.
- The PDF is untagged.
- The PDF producer is `Adobe Acrobat 9.13 Paper Capture Plug-in`, so extracted text should be treated as OCR-derived.
- The page size is letter, `612 x 792 pts`.

## Locator Policy

Use PDF page as the stable raw extraction locator. Add visible page when it is detected from the front matter, table of contents, or page text. Do not rely on visible page alone because front matter uses roman numerals and the PDF includes non-content pages before visible page 1.

## OCR And Layout Caveats

- The document is OCR-derived and may contain heading, punctuation, dash, or spacing errors.
- The source is untagged, so table and heading structure must be reconstructed from layout text.
- Tables and exhibits may need manual review after automated extraction.
- BC-specific governance concepts must not be generalized to Charlottetown or PEI without separate jurisdiction review.
- The extracted front-matter exhibit ids show mojibake for en dashes; `exhibit_index.json` normalizes exhibit ids to ASCII hyphen.
- The original ingestion plan expected 76 numbered chapter sections and 45 exhibits. The extracted table of contents lists 78 numbered chapter sections and the extracted exhibit list contains 41 exhibits.

## Next Phase

Phase 4 should begin with Chapter 6 and keep source claims separate from proposed portal metrics.

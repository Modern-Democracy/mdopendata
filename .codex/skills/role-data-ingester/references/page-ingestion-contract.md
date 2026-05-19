# Page Ingestion Contract

Use this reference when creating or validating municipal PDF ingestion bundles.

## Required Page Evidence

Each source page must preserve:

- `source_document_key`: stable document identifier.
- `page_number`: one-based PDF page number.
- `page_label_raw`: raw visible or embedded label when available.
- `source_locator`: stable locator such as repository path plus page number.
- `text_raw`: embedded text or OCR text, preserving raw wording.
- `text_extraction_status`: `embedded`, `ocr`, `empty`, `failed`, or `not_attempted`.
- `rendered_image_path`: repository-relative screenshot or page render path.
- `rendered_image_hash`: file hash when available.
- `width`, `height`, and `render_dpi` when available.
- `metadata`: extractor version, extraction warnings, rotation, crop, OCR language, and source timestamps when available.

## Required Classification Evidence

Each page classification should preserve:

- document family candidate
- document type candidate
- section type candidate
- page template candidate
- matched pattern key when available
- classification source: `parser`, `reviewer`, `imported`, or `model`
- confidence where meaningful
- review status: `accepted`, `rejected`, or `needs_review`
- evidence cues that support the classification

## Bundle Requirements

An ingestion bundle is acceptable only when:

1. page count equals the source PDF page count
2. every page number from 1 to page count is represented exactly once
3. every page has a rendered image or explicit render failure record
4. every page has extracted text or explicit OCR/text failure status
5. every page is either classified, weakly matched, unmatched, or attached to a model gap
6. every normalized field can trace back to one or more page locators

#!/usr/bin/env python3
"""Validate a municipal document ingestion bundle JSON file.

Expected minimal shape:
{
  "source_document": {"source_document_key": "...", "page_count": 1},
  "pages": [
    {
      "page_number": 1,
      "source_locator": "...",
      "text_extraction_status": "embedded|ocr|empty|failed|not_attempted",
      "rendered_image_path": "...",
      "classification": {"review_status": "accepted|rejected|needs_review"}
    }
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

VALID_TEXT_STATUS = {"embedded", "ocr", "empty", "failed", "not_attempted"}
VALID_REVIEW_STATUS = {"accepted", "rejected", "needs_review"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(bundle: dict) -> list[str]:
    errors: list[str] = []
    doc = bundle.get("source_document") or {}
    pages = bundle.get("pages")
    if not isinstance(pages, list):
        return ["pages must be a list"]

    page_count = doc.get("page_count")
    if page_count is not None and page_count != len(pages):
        errors.append(f"page_count {page_count} does not equal pages length {len(pages)}")

    numbers = [p.get("page_number") for p in pages]
    counts = Counter(numbers)
    for n, count in sorted(counts.items(), key=lambda x: (x[0] is None, x[0])):
        if n is None:
            errors.append("one or more pages are missing page_number")
        elif count != 1:
            errors.append(f"page_number {n} appears {count} times")

    if page_count:
        expected = set(range(1, page_count + 1))
        observed = {n for n in numbers if isinstance(n, int)}
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        if missing:
            errors.append(f"missing page numbers: {missing}")
        if extra:
            errors.append(f"page numbers outside page_count: {extra}")

    for idx, page in enumerate(pages, start=1):
        label = page.get("page_number", f"index {idx}")
        if not page.get("source_locator"):
            errors.append(f"page {label} missing source_locator")
        if page.get("text_extraction_status") not in VALID_TEXT_STATUS:
            errors.append(f"page {label} has invalid or missing text_extraction_status")
        if not page.get("rendered_image_path") and not page.get("render_failure"):
            errors.append(f"page {label} missing rendered_image_path or render_failure")
        classification = page.get("classification") or {}
        if classification.get("review_status") not in VALID_REVIEW_STATUS:
            errors.append(f"page {label} has invalid or missing classification.review_status")
        routed = bool(classification.get("pipeline_key") or page.get("pipeline_route"))
        pattern_status = classification.get("pattern_status")
        if routed and pattern_status and pattern_status != "approved":
            errors.append(f"page {label} routed with non-approved pattern_status {pattern_status!r}")
        if not routed and classification.get("review_status") == "accepted" and not classification.get("pattern_key"):
            errors.append(f"page {label} accepted without route or pattern_key")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a document ingestion bundle")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    errors = validate(load_json(args.bundle))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

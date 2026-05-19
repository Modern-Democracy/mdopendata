#!/usr/bin/env python3
"""Summarize pattern candidates from ingestion bundle classifications."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize candidate document patterns")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    data = json.loads(args.bundle.read_text(encoding="utf-8"))
    groups: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    statuses: Counter[str] = Counter()
    for page in data.get("pages", []):
        c = page.get("classification") or {}
        key = (
            c.get("document_family_key") or "",
            c.get("document_type_key") or "",
            c.get("section_type_key") or "",
            c.get("page_template_key") or "",
        )
        groups[key].append(page.get("page_number"))
        statuses[c.get("review_status") or "missing"] += 1
    print(json.dumps({
        "classification_status_counts": dict(statuses),
        "candidate_groups": [
            {
                "document_family_key": k[0],
                "document_type_key": k[1],
                "section_type_key": k[2],
                "page_template_key": k[3],
                "page_count": len(v),
                "pages": v,
            }
            for k, v in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

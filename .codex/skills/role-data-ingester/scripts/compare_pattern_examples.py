#!/usr/bin/env python3
"""Compare a pattern JSON record's examples against required promotion evidence."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check pattern example support")
    parser.add_argument("pattern", type=Path)
    args = parser.parse_args()
    pattern = json.loads(args.pattern.read_text(encoding="utf-8"))
    status = pattern.get("status")
    examples = pattern.get("examples") or []
    counts = Counter(e.get("example_type") for e in examples)
    errors: list[str] = []
    if status in {"candidate", "approved"} and counts.get("positive", 0) < 1:
        errors.append("candidate or approved pattern requires at least one positive example")
    if status == "approved" and counts.get("negative", 0) < 1:
        errors.append("approved pattern should include at least one negative example or documented exception")
    if status == "approved" and not pattern.get("confidence_rule"):
        errors.append("approved pattern requires confidence_rule")
    cues = pattern.get("cues") or []
    if status == "approved" and not cues:
        errors.append("approved pattern requires cues")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": status, "example_counts": dict(counts), "cue_count": len(cues)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

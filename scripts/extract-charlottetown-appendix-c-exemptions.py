"""Parse Appendix C of the current Charlottetown bylaw into per-PID records.

Reads `data/zoning/charlottetown/appendix-c-approved-site-specific-exemptions.json`
(8 pages, ~25 zone-header blocks, ~47 distinct PIDs across 14 zones). The
appendix is a 5-column table — Zone, PID, Civic Address, Use, Regulation —
flattened by the PDF text-extractor into multi-line cells with no clean
delimiter. We split on the lines that contain just `(CODE)` (or
`(CODE) Zone`), trim trailing zone-name preambles, then bucket each
block's content lines into PIDs / civic addresses / use / regulation
using simple heuristics.

Each row produced is fanned out to one record per PID. Records the
parser is confident about (PID-count == address-count, regulation
preamble detected when present, no junk) are emitted with
`confidence='high'`; the rest fall back to `confidence='needs_review'`
with the raw block text preserved in `notes`. The companion
`scripts/apply-charlottetown-appendix-c-exemptions.py` promotes only
the high-confidence rows to `zoning.structured_fact` by default.

Usage
-----
    python scripts/extract-charlottetown-appendix-c-exemptions.py
    python scripts/extract-charlottetown-appendix-c-exemptions.py --print-summary

Output
------
    data/zoning/charlottetown/manual-corrections/appendix-c-exemptions.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = (
    REPO_ROOT / "data" / "zoning" / "charlottetown"
    / "appendix-c-approved-site-specific-exemptions.json"
)
OUTPUT_PATH = (
    REPO_ROOT / "data" / "zoning" / "charlottetown" / "manual-corrections"
    / "appendix-c-exemptions.json"
)
SCHEMA_VERSION = 1

# Lines we always strip — page headers + the table column header.
STRIP_LINES = {
    "Zone PID Civic Address Use Regulation",
    "APPENDIX C. APPROVED SITE SPECIFIC EXEMPTIONS",
}

# `(CODE)` or `(CODE) Zone` on a line by itself => zone-header marker.
ZONE_RE = re.compile(r"^\(([A-Z][A-Z0-9-]*)\)(?:\s*Zone)?\s*$")

# A pure PID token: 5–7 digits, optionally followed by a comma/period and
# optional trailing " and".
PID_LINE_RE = re.compile(r"^(\d{5,7})\s*[,.]?\s*(and)?\s*$")
PID_TOKEN_RE = re.compile(r"\b\d{5,7}\b")

# Civic-address line: starts with a number, contains a recognized street type.
ADDR_LINE_RE = re.compile(
    r"^\s*\d[\d\-]*\s.+\b(?:Street|Avenue|Drive|Road|Way|Lane|Boulevard|"
    r"Place|Court|Crescent|Terrace|Cove|Park|Heights|Trail|Square|Circle)\b",
    re.IGNORECASE,
)

# Regulation-cell preamble: typical opening clauses observed in the source.
REG_PREAMBLE_RE = re.compile(
    r"^(?:To\s+(?:amend|increase|permit|reduce|allow|recognize|extend|"
    r"exempt|legalize|establish|create|change|expand|approve|construct|"
    r"reconstruct|enable|relax|lower|raise|maintain|grant|provide|add)|"
    r"A\s+site\s+specific|"
    r"In\s+order\s+to|"
    r"Notwithstanding)",
    re.IGNORECASE,
)


def load_pages(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages = (payload.get("raw_data") or {}).get("pages_raw") or []
    return [str(page.get("text_raw") or "") for page in pages]


def page_starts(pages: list[str]) -> list[int]:
    """Return the start-line index of each page after concatenation."""
    starts: list[int] = []
    cursor = 0
    for page_text in pages:
        starts.append(cursor)
        cursor += page_text.count("\n") + 1  # +1 for the inter-page newline
    return starts


def page_for_line(line_index: int, starts: list[int]) -> int:
    """Return the 1-indexed PDF page that contains the given line."""
    page = 1
    for i, start in enumerate(starts):
        if line_index >= start:
            page = i + 1
        else:
            break
    return page


def parse_pid_line(line: str) -> list[str]:
    """Extract every PID token from a line — handles tolerant lists like
    `669796. 751701` or `357756, 361519, ...`.
    """
    return PID_TOKEN_RE.findall(line)


def split_blocks(lines: list[str]) -> list[dict[str, Any]]:
    """Split the concatenated text into per-zone-header blocks.

    Each block is bounded above by a `(CODE)` marker line and below by the
    next marker (or end-of-text). The trailing lines of each block — the
    next zone's name preamble (e.g. `"Business Office\nCommercial"`
    immediately before `"(C-1)"`) — are stripped before returning.
    """
    markers: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        match = ZONE_RE.match(line)
        if match:
            markers.append((i, match.group(1)))
    blocks: list[dict[str, Any]] = []
    for index, (line_idx, code) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(lines)
        # Trim the next block's name preamble: walk backwards while we see
        # capitalized title-case lines without digits/punctuation other
        # than spaces.
        stop = end
        while stop > line_idx + 1:
            candidate = lines[stop - 1].strip()
            if not candidate:
                stop -= 1
                continue
            if re.fullmatch(r"[A-Z][A-Za-z'&\- ]*", candidate):
                stop -= 1
                continue
            break
        body = [
            line for line in lines[line_idx + 1: stop]
            if line.strip() and line.strip() not in STRIP_LINES
        ]
        blocks.append({
            "zone_code_at_amendment": code,
            "marker_line": line_idx,
            "body": body,
        })
    return blocks


def classify_lines(body: list[str]) -> dict[str, list[str]]:
    """Bucket each line of a block into pids / addresses / use / regulation."""
    pids: list[str] = []
    addresses: list[str] = []
    use_lines: list[str] = []
    regulation_lines: list[str] = []
    in_regulation = False
    pid_phase = True  # true until we hit the first non-PID, non-empty line
    for line in body:
        stripped = line.strip()
        if in_regulation:
            regulation_lines.append(stripped)
            continue
        if REG_PREAMBLE_RE.match(stripped):
            in_regulation = True
            regulation_lines.append(stripped)
            continue
        # Tolerant PID detection: pure-digit lines, lines that are just
        # comma/period-separated PIDs, or a final " and" PID line.
        pid_tokens = parse_pid_line(stripped)
        only_pid_chars = bool(pid_tokens) and bool(
            re.fullmatch(r"[\d\s,.\sand]+", stripped, re.IGNORECASE)
        )
        if pid_phase and only_pid_chars:
            pids.extend(pid_tokens)
            continue
        # Lines that mash PID + address + use (page 1 single-row blocks
        # like "339994 99 Pownal Street Fitness Centre"): split on the
        # first PID token and treat the rest as address + use.
        if pid_phase and pid_tokens and ADDR_LINE_RE.search(stripped):
            pids.extend(pid_tokens)
            tail = re.sub(r"^\s*" + pid_tokens[0] + r"\s*", "", stripped, count=1)
            addresses.append(tail)
            pid_phase = False
            continue
        pid_phase = False
        if ADDR_LINE_RE.search(stripped):
            addresses.append(stripped.rstrip(",").rstrip(" and").rstrip(","))
        else:
            use_lines.append(stripped)
    return {
        "pids": pids,
        "addresses": addresses,
        "use_lines": use_lines,
        "regulation_lines": regulation_lines,
    }


def collapse_text(lines: list[str]) -> str:
    if not lines:
        return ""
    out = " ".join(line.strip() for line in lines).strip()
    out = re.sub(r"\s+", " ", out)
    return out


def expand_records(block: dict[str, Any], buckets: dict[str, list[str]],
                   page_starts: list[int]) -> list[dict[str, Any]]:
    pids = buckets["pids"]
    addresses = buckets["addresses"]
    use_text = collapse_text(buckets["use_lines"])
    regulation_text = collapse_text(buckets["regulation_lines"])
    page = page_for_line(block["marker_line"], page_starts)
    notes = None
    if not pids:
        # Some blocks (rare) have no PID — emit one needs-review record.
        return [{
            "zone_code_at_amendment": block["zone_code_at_amendment"],
            "pid": None,
            "civic_address": None,
            "use_added_or_modified": use_text or None,
            "regulation_override_text": regulation_text or None,
            "source_page": page,
            "confidence": "needs_review",
            "notes": "no_pid_detected; raw=" + " | ".join(block["body"]),
        }]
    pairing_ok = len(addresses) == len(pids) or len(addresses) == 1
    confidence = "high" if pairing_ok else "needs_review"
    if not pairing_ok:
        notes = (
            f"pid_address_count_mismatch pids={len(pids)} addresses={len(addresses)}; "
            "raw=" + " | ".join(block["body"])
        )
    records: list[dict[str, Any]] = []
    for index, pid in enumerate(pids):
        address: str | None
        if not addresses:
            address = None
        elif len(addresses) == len(pids):
            address = addresses[index]
        elif len(addresses) == 1:
            address = addresses[0]
        else:
            address = addresses[index] if index < len(addresses) else None
        records.append({
            "zone_code_at_amendment": block["zone_code_at_amendment"],
            "pid": pid,
            "civic_address": address,
            "use_added_or_modified": use_text or None,
            "regulation_override_text": regulation_text or None,
            "source_page": page,
            "confidence": confidence,
            "notes": notes,
        })
    return records


def parse(pages: list[str]) -> list[dict[str, Any]]:
    text = "\n".join(pages)
    lines = text.split("\n")
    starts = page_starts(pages)
    records: list[dict[str, Any]] = []
    for block in split_blocks(lines):
        buckets = classify_lines(block["body"])
        records.extend(expand_records(block, buckets, starts))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-summary", action="store_true",
                        help="Print per-record output to stdout in addition to writing the file.")
    parser.add_argument("--out", type=Path, default=OUTPUT_PATH,
                        help=f"Output path (default: {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()})")
    args = parser.parse_args()

    pages = load_pages(SOURCE_PATH)
    records = parse(pages)
    summary: dict[str, int] = {"high": 0, "needs_review": 0}
    for record in records:
        summary[record["confidence"]] = summary.get(record["confidence"], 0) + 1
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_file_path": SOURCE_PATH.relative_to(REPO_ROOT).as_posix(),
        "summary": {"total": len(records), **summary},
        "exemptions": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(records)} records to "
        f"{args.out.relative_to(REPO_ROOT).as_posix()} "
        f"(high={summary.get('high',0)}, needs_review={summary.get('needs_review',0)})."
    )
    if args.print_summary:
        for record in records:
            print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()

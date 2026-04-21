from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fitz
except ModuleNotFoundError:  # pragma: no cover - supports lighter repo Python envs.
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "docs" / "charlottetown" / "charlottetown-zoning-bylaw.pdf"
SOURCE_REL = "docs/charlottetown/charlottetown-zoning-bylaw.pdf"
OUT_DIR = ROOT / "data" / "normalized" / "code-tables" / "candidates" / "charlottetown"
SEED_DIR = ROOT / "data" / "normalized" / "code-tables"
SCHEMA_REL = "../../../../../schema/json-schema/candidate-code-table-seed.schema.json"

MAX_EXAMPLES = 5
MAX_SOURCE_REFS = 25


CANDIDATE_TABLES = {
    "term": "Candidate zoning terms and terminology categories discovered before extraction.",
    "requirement_type": "Candidate requirement categories inferred from headings and rule text.",
    "relationship_type": "Candidate relationship phrases discovered before extraction.",
    "use": "Candidate use names discovered before extraction.",
}

CANONICAL_PHRASES = {
    "accessory buildings": "accessory building",
    "accessory structures": "accessory structure",
    "accessory uses": "accessory use",
    "conditional uses": "conditional use",
    "development permits": "development permit",
    "dwelling units": "dwelling unit",
    "parking spaces": "parking space",
    "permitted uses": "permitted use",
    "prohibited uses": "prohibited use",
    "uses permitted": "permitted use",
    "uses prohibited": "prohibited use",
}

KNOWN_PHRASES = {
    "dwelling_type": [
        "single detached dwelling",
        "semi-detached dwelling",
        "duplex dwelling",
        "townhouse dwelling",
        "stacked townhouse",
        "apartment building",
        "secondary suite",
        "garden suite",
        "boarding house",
        "rooming house",
    ],
    "accessory_use": [
        "accessory building",
        "accessory structure",
        "accessory use",
        "home occupation",
        "secondary use",
        "temporary use",
    ],
    "approval_process": [
        "development permit",
        "building permit",
        "development agreement",
        "site plan approval",
        "variance",
        "minor variance",
        "concept plan",
        "special permit",
    ],
    "lot_context": [
        "corner lot",
        "interior lot",
        "through lot",
        "flankage lot",
        "water lot",
        "lot frontage",
        "lot coverage",
        "lot area",
    ],
    "yard_type": [
        "front yard",
        "rear yard",
        "side yard",
        "flankage yard",
        "required yard",
        "setback",
    ],
}

REQUIREMENT_PATTERNS = {
    "dimensional_standard": [
        "minimum lot area",
        "minimum lot frontage",
        "minimum front yard",
        "minimum rear yard",
        "minimum side yard",
        "maximum building height",
        "maximum lot coverage",
        "floor area ratio",
    ],
    "permitted_use_rule": [
        "permitted uses",
        "uses permitted",
        "permitted use",
        "conditional use",
    ],
    "prohibited_use_rule": [
        "prohibited use",
        "uses prohibited",
        "shall not be permitted",
    ],
    "process_requirement": [
        "development permit",
        "application shall",
        "approval of council",
        "site plan approval",
    ],
    "parking_requirement": [
        "parking space",
        "parking requirement",
        "loading space",
        "driveway",
    ],
    "map_applicability_rule": [
        "as shown on",
        "schedule",
        "zoning map",
        "overlay",
    ],
}

RELATIONSHIP_PATTERNS = {
    "notwithstanding": "exclude_target_values",
    "does not apply": "exclude_target_values",
    "except as provided": "exclude_target_values",
    "as shown on": "reference_only",
    "referred to in": "reference_only",
    "where permitted in": "reference_only",
}

UNIT_PATTERNS = {
    "m": [r"\bm(?:etre|eter|etres|eters)?\b"],
    "ft": [r"\bft\b", r"\bfeet\b", r"\bfoot\b"],
    "sq_m": [r"\bsq\.?\s*m\b", r"\bsquare metres?\b", r"\bsquare meters?\b"],
    "sq_ft": [r"\bsq\.?\s*ft\b", r"\bsquare feet\b", r"\bsquare foot\b"],
    "ha": [r"\bha\b", r"\bhectares?\b"],
    "acre": [r"\bacres?\b"],
    "percent": [r"%", r"\bper cent\b", r"\bpercent\b"],
    "storey": [r"\bstor(?:e)?ys?\b", r"\bstor(?:e)?ies\b"],
    "dwelling_unit": [r"\bdwelling units?\b"],
    "parking_space": [r"\bparking spaces?\b"],
    "bedroom": [r"\bbedrooms?\b"],
}

MEASURE_BY_UNIT = {
    "m": "length",
    "ft": "length",
    "sq_m": "area",
    "sq_ft": "area",
    "ha": "area",
    "acre": "area",
    "percent": "percentage",
    "storey": "height",
    "dwelling_unit": "density",
    "parking_space": "count",
    "bedroom": "count",
}


def slugify(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    value = re.sub(r"_+", "_", value)
    return value or "unknown"


def candidate_key(table: str, category: str, phrase: str) -> tuple[str, str, str]:
    return table, category, slugify(phrase)


def canonicalize_phrase(phrase: str) -> tuple[str, str | None]:
    compacted = compact_text(phrase).strip(" ,;:.")
    canonical = CANONICAL_PHRASES.get(compacted.lower())
    if canonical:
        return canonical, compacted
    return compacted, None


def load_reviewed_entries() -> dict[str, list[dict[str, Any]]]:
    reviewed: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(SEED_DIR.glob("*.seed.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        reviewed[payload["code_table"]] = payload.get("entries", [])
    return reviewed


def existing_match(table: str, phrase: str, reviewed: dict[str, list[dict[str, Any]]]) -> dict[str, str] | None:
    entries = reviewed.get(table, [])
    normalized = slugify(phrase)
    phrase_lower = phrase.lower()
    for entry in entries:
        if normalized == entry.get("code"):
            return {
                "code_table": table,
                "code": entry["code"],
                "label": entry["label"],
                "match_type": "code",
            }
        if phrase_lower == str(entry.get("label", "")).lower():
            return {
                "code_table": table,
                "code": entry["code"],
                "label": entry["label"],
                "match_type": "label",
            }
        symbol = entry.get("symbol")
        if symbol and phrase_lower == str(symbol).lower():
            return {
                "code_table": table,
                "code": entry["code"],
                "label": entry["label"],
                "match_type": "symbol",
            }
    return None


def reviewed_unit_measure_type(unit_code: str, reviewed: dict[str, list[dict[str, Any]]]) -> str | None:
    for entry in reviewed.get("unit", []):
        if entry.get("code") == unit_code:
            return entry.get("measure_type")
    return None


def read_pdf_pages(path: Path) -> list[dict[str, Any]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is required to extract PDF text. Run with the bundled workspace Python.")
    doc = fitz.open(path)
    pages = []
    for index, page in enumerate(doc, start=1):
        pages.append({"page": index, "text": page.get_text("text")})
    return pages


def compact_text(value: str) -> str:
    return " ".join(value.split())


def detect_section(line: str, current_section: str | None) -> str | None:
    stripped = line.strip()
    match = re.match(r"^(\d+(?:\.\d+)*)(?:\s+|\t+)[A-Z][A-Za-z0-9 ,;:'\"()/-]{4,}$", stripped)
    if match:
        return match.group(1)
    return current_section


def detect_clause(line: str) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+)?(?:\([A-Za-z0-9.]+\))+)", line)
    return match.group(1) if match else None


def context_label(line: str) -> str:
    lowered = line.lower()
    for label in [
        "permitted uses",
        "conditional uses",
        "prohibited uses",
        "regulations",
        "definitions",
        "parking",
        "signs",
        "maps",
        "schedule",
    ]:
        if label in lowered:
            return label
    return ""


def add_candidate(
    candidates: dict[tuple[str, str, str], dict[str, Any]],
    reviewed: dict[str, list[dict[str, Any]]],
    *,
    table: str,
    category: str,
    phrase: str,
    page: int | None,
    section: str | None,
    clause: str | None,
    context: str,
    example_text: str,
    match_basis: list[str],
    confidence: float,
    alias: str | None = None,
    review_flags: list[dict[str, str]] | None = None,
    default_join_behavior: str | None = None,
) -> None:
    phrase, canonical_alias = canonicalize_phrase(phrase)
    if len(phrase) < 2:
        return
    if canonical_alias and alias is None:
        alias = canonical_alias
    key = candidate_key(table, category, phrase)
    if key not in candidates:
        suggested_code = slugify(phrase)
        candidates[key] = {
            "candidate_id": f"charlottetown-{table}-{category}-{suggested_code}".replace("_", "-"),
            "canonical_candidate": phrase.lower(),
            "suggested_code": suggested_code,
            "candidate_table": table,
            "category": category,
            "status": "candidate",
            "aliases": [],
            "occurrence_count": 0,
            "confidence": 0.0,
            "match_basis": [],
            "existing_code_match": existing_match(table, phrase, reviewed),
            "source_refs": [],
            "examples": [],
            "review_flags": [],
            "review_decision": {
                "status": "unreviewed",
                "approved_code": None,
                "review_notes": None,
            },
        }
        if default_join_behavior is not None:
            candidates[key]["default_join_behavior"] = default_join_behavior
    candidate = candidates[key]
    candidate["occurrence_count"] += 1
    candidate["confidence"] = min(1.0, max(float(candidate["confidence"]), confidence))
    for basis in match_basis:
        if basis not in candidate["match_basis"]:
            candidate["match_basis"].append(basis)
    if alias and alias != candidate["canonical_candidate"] and alias not in candidate["aliases"]:
        candidate["aliases"].append(alias)
    source_ref = {
        "source_document": SOURCE_REL,
        "page": page,
        "section": section,
        "clause": clause,
        "context": context,
    }
    if source_ref not in candidate["source_refs"] and len(candidate["source_refs"]) < MAX_SOURCE_REFS:
        candidate["source_refs"].append(source_ref)
    example = {
        "text": compact_text(example_text)[:300],
        "page": page,
        "section": section,
        "clause": clause,
    }
    if example not in candidate["examples"] and len(candidate["examples"]) < MAX_EXAMPLES:
        candidate["examples"].append(example)
    for flag in review_flags or []:
        if flag not in candidate["review_flags"]:
            candidate["review_flags"].append(flag)


def detect_known_phrases(
    candidates: dict[tuple[str, str, str], dict[str, Any]],
    reviewed: dict[str, list[dict[str, Any]]],
    line: str,
    page: int,
    section: str | None,
    clause: str | None,
) -> None:
    lowered = line.lower()
    for category, phrases in KNOWN_PHRASES.items():
        for phrase in phrases:
            if phrase in lowered:
                add_candidate(
                    candidates,
                    reviewed,
                    table="term",
                    category=category,
                    phrase=phrase,
                    page=page,
                    section=section,
                    clause=clause,
                    context=context_label(line),
                    example_text=line,
                    match_basis=["known_phrase"],
                    confidence=0.75,
                )
                if category in {"dwelling_type", "accessory_use"}:
                    add_candidate(
                        candidates,
                        reviewed,
                        table="use",
                        category=category,
                        phrase=phrase,
                        page=page,
                        section=section,
                        clause=clause,
                        context=context_label(line),
                        example_text=line,
                        match_basis=["known_use_phrase"],
                        confidence=0.7,
                    )


def detect_requirements(
    candidates: dict[tuple[str, str, str], dict[str, Any]],
    reviewed: dict[str, list[dict[str, Any]]],
    line: str,
    page: int,
    section: str | None,
    clause: str | None,
) -> None:
    lowered = line.lower()
    for category, phrases in REQUIREMENT_PATTERNS.items():
        for phrase in phrases:
            if phrase in lowered:
                add_candidate(
                    candidates,
                    reviewed,
                    table="requirement_type",
                    category=category,
                    phrase=phrase,
                    page=page,
                    section=section,
                    clause=clause,
                    context=context_label(line),
                    example_text=line,
                    match_basis=["requirement_phrase"],
                    confidence=0.72,
                    review_flags=[
                        {
                            "code": "category_requires_review",
                            "message": "Requirement phrase category is provisional until human review.",
                        }
                    ],
                )


def detect_relationships(
    candidates: dict[tuple[str, str, str], dict[str, Any]],
    reviewed: dict[str, list[dict[str, Any]]],
    line: str,
    page: int,
    section: str | None,
    clause: str | None,
) -> None:
    lowered = line.lower()
    for phrase, default_join_behavior in RELATIONSHIP_PATTERNS.items():
        if phrase in lowered:
            add_candidate(
                candidates,
                reviewed,
                table="relationship_type",
                category="relationship_phrase",
                phrase=phrase,
                page=page,
                section=section,
                clause=clause,
                context=context_label(line),
                example_text=line,
                match_basis=["relationship_phrase"],
                confidence=0.68,
                default_join_behavior=default_join_behavior,
                review_flags=[
                    {
                        "code": "relationship_semantics_requires_review",
                        "message": "Phrase has a provisional join behavior and still requires human semantic review.",
                    }
                ],
            )


def detect_units_and_measures(
    candidates: dict[tuple[str, str, str], dict[str, Any]],
    reviewed: dict[str, list[dict[str, Any]]],
    line: str,
    page: int,
    section: str | None,
    clause: str | None,
) -> None:
    lowered = line.lower()
    if not re.search(r"\d", lowered):
        return
    for unit_code, patterns in UNIT_PATTERNS.items():
        for pattern in patterns:
            if re.search(rf"(?:\d|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:{pattern})", lowered):
                measure_type = reviewed_unit_measure_type(unit_code, reviewed) or MEASURE_BY_UNIT.get(unit_code, "unknown")
                add_candidate(
                    candidates,
                    reviewed,
                    table="unit",
                    category=measure_type,
                    phrase=unit_code,
                    page=page,
                    section=section,
                    clause=clause,
                    context=context_label(line),
                    example_text=line,
                    match_basis=["numeric_unit_pattern"],
                    confidence=0.86,
                )
                add_candidate(
                    candidates,
                    reviewed,
                    table="measure_type",
                    category="measure_type",
                    phrase=measure_type,
                    page=page,
                    section=section,
                    clause=clause,
                    context=context_label(line),
                    example_text=line,
                    match_basis=["unit_to_measure_type"],
                    confidence=0.74,
                )
                break


def discover_candidates(pages: list[dict[str, Any]], reviewed: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
    current_section: str | None = None
    for page_payload in pages:
        page = int(page_payload["page"])
        for raw_line in page_payload["text"].splitlines():
            line = compact_text(raw_line)
            if len(line) < 3:
                continue
            current_section = detect_section(line, current_section)
            clause = detect_clause(line)
            detect_known_phrases(candidates, reviewed, line, page, current_section, clause)
            detect_requirements(candidates, reviewed, line, page, current_section, clause)
            detect_relationships(candidates, reviewed, line, page, current_section, clause)

    grouped: dict[str, list[dict[str, Any]]] = {table: [] for table in CANDIDATE_TABLES}
    for candidate in candidates.values():
        candidate["aliases"].sort()
        candidate["match_basis"].sort()
        candidate["review_flags"].sort(key=lambda item: item["code"])
        grouped[candidate["candidate_table"]].append(candidate)
    for entries in grouped.values():
        entries.sort(key=lambda item: (-item["occurrence_count"], item["category"], item["canonical_candidate"]))
    return grouped


def build_payload(table: str, entries: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    return {
        "$schema": SCHEMA_REL,
        "candidate_table": table,
        "description": CANDIDATE_TABLES[table],
        "jurisdiction": "Charlottetown",
        "source_document": SOURCE_REL,
        "version": "0.1.0",
        "generated_at": generated_at,
        "status": "candidate",
        "entries": entries,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_review_report(grouped: dict[str, list[dict[str, Any]]], generated_at: str) -> dict[str, Any]:
    review_flags = Counter()
    for entries in grouped.values():
        for entry in entries:
            for flag in entry["review_flags"]:
                review_flags[flag["code"]] += 1
    return {
        "jurisdiction": "Charlottetown",
        "source_document": SOURCE_REL,
        "generated_at": generated_at,
        "status": "candidate_review_required",
        "candidate_files": [
            f"{table}_candidate.seed.json" for table in sorted(CANDIDATE_TABLES)
        ],
        "entry_counts": {
            table: len(entries) for table, entries in sorted(grouped.items())
        },
        "review_flag_counts": dict(sorted(review_flags.items())),
        "review_gates": [
            "Do not promote candidates to reviewed seed files without human approval.",
            "Review ambiguous terminology categories before final extraction.",
            "Review relationship phrase semantics before using provisional join behavior.",
            "Keep municipality-specific zone codes and map references outside municipality-agnostic code tables.",
            "Skip unit and measure-type candidates when every candidate already exists in reviewed code tables.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover provisional Charlottetown code-table candidates from the zoning bylaw PDF."
    )
    parser.add_argument("--source", type=Path, default=SOURCE_PDF)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing candidate files.")
    args = parser.parse_args()

    pages = read_pdf_pages(args.source)
    grouped = discover_candidates(pages, load_reviewed_entries())
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if args.dry_run:
        for table, entries in sorted(grouped.items()):
            print(f"{table}: {len(entries)} candidates")
        return 0

    for table, entries in sorted(grouped.items()):
        write_json(args.out_dir / f"{table}_candidate.seed.json", build_payload(table, entries, generated_at))
    write_json(args.out_dir / "review_report.json", build_review_report(grouped, generated_at))
    print(f"Wrote candidate discovery outputs to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

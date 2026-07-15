#!/usr/bin/env python3
"""Generate a deterministic Stage 1 candidate block inventory from Stage 0 evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT
    / "data"
    / "budget"
    / "charlottetown"
    / "2026-2027"
    / "staged-pdf"
    / "v1"
    / "stage-0"
    / "source-evidence.json"
)
DEFAULT_OUT = DEFAULT_SOURCE.parents[1] / "stage-1"
VALIDATOR_PATH = ROOT / "scripts" / "validate-staged-pdf-artifacts.py"
GENERATOR_NAME = "staged-pdf-block-inventory"
GENERATOR_VERSION = "2"
CONFIG = {
    "generator_version": GENERATOR_VERSION,
    "body_top": 0.18,
    "footer_top": 0.91,
    "sparse_page_word_limit": 15,
    "financial_numeric_minimum": 8,
    "geometry_source": "stage-0-word-evidence",
}

NUMBER_RE = re.compile(r"(?:[$%]?[-+]?\d[\d,]*(?:\.\d+)?|\d{4}/\d{2,4})")
FINANCIAL_RE = re.compile(
    r"\b(?:budget|revenue|expense|expenditure|forecast|variance|assessment|rate|tax|debt|capital|operating|principal|interest)\b",
    re.IGNORECASE,
)


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("staged_pdf_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schema_reference(output: Path) -> str:
    schema = ROOT / "schema" / "json-schema" / "staged-pdf-artifacts.schema.json"
    return Path(os.path.relpath(schema, output)).as_posix()


def bounded(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 6)


def union_box(words: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "x0": bounded(min(word["bbox"]["x0"] for word in words)),
        "y0": bounded(min(word["bbox"]["y0"] for word in words)),
        "x1": bounded(max(word["bbox"]["x1"] for word in words)),
        "y1": bounded(max(word["bbox"]["y1"] for word in words)),
    }


def ordered_text(words: list[dict[str, Any]]) -> str:
    ordered = sorted(
        words,
        key=lambda word: (
            word.get("block_number", 0),
            word.get("line_number", 0),
            word.get("word_number", 0),
            word["bbox"]["y0"],
            word["bbox"]["x0"],
        ),
    )
    return " ".join(str(word.get("text", "")).strip() for word in ordered if word.get("text")).strip()


def classify_body(text: str, word_count: int, page_text: str = "") -> tuple[str, bool, str | None, list[str]]:
    lower = text.lower()
    page_lower = page_text.lower()
    numeric_count = len(NUMBER_RE.findall(text))
    financial = bool(FINANCIAL_RE.search(text)) and numeric_count >= CONFIG["financial_numeric_minimum"]
    chart_financial = (
        numeric_count >= 4
        and any(token in page_lower for token in ("revenue", "expense", "expenditure"))
        and text.count("%") >= 3
    )
    financial = financial or chart_financial
    if "table of contents" in page_lower:
        return "table_of_contents", False, None, ["contents-page"]
    profile_cues = sum(
        phrase in lower
        for phrase in ("project name", "department", "project cost", "funding source", "project description", "project timeline")
    )
    if "project" in lower and profile_cues >= 2:
        return "formatted_text", True, "capital_project_profile", ["project-profile-cues"]
    if financial:
        if "assessment" in lower and "rate" in lower:
            family = "tax_assessment_rate"
        elif "debt" in lower and any(token in lower for token in ("principal", "interest", "outstanding")):
            family = "debt_schedule"
        elif "capital" in lower and "project" in lower:
            family = "capital_budget_schedule"
        elif any(token in lower for token in ("forecast", "variance")):
            family = "operating_detail"
        else:
            family = "operating_statement"
        return "table", True, family, ["financial-text-cues", "numeric-density"]
    if word_count <= CONFIG["sparse_page_word_limit"]:
        return "divider", False, None, ["sparse-page"]
    return "formatted_text", False, None, ["prose-density"]


def internal_regions(block_key: str, block_type: str, words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if block_type != "formatted_text":
        return []
    grouped: dict[int, list[dict[str, Any]]] = {}
    for word in words:
        grouped.setdefault(int(word.get("block_number", 0)), []).append(word)
    regions: list[dict[str, Any]] = []
    for sequence, group_words in enumerate(
        sorted(grouped.values(), key=lambda group: (min(word["bbox"]["y0"] for word in group), min(word["bbox"]["x0"] for word in group))),
        start=1,
    ):
        text = ordered_text(group_words)
        if not text:
            continue
        if re.match(r"^[\u2022\u00b7\u25aa\u25e6*\-]\s*", text):
            region_type = "bullet_list"
        elif re.match(r"^(?:\(?\d+|[A-Za-z])[.)]\s+", text):
            region_type = "sorted_list"
        else:
            region_type = "paragraph"
        regions.append({
            "region_key": f"{block_key}:region-{sequence:03d}",
            "region_type": region_type,
            "bbox": union_box(group_words),
            "text_excerpt": text[:240],
            "review": {"status": "proposed", "reason_codes": ["automated-internal-region"], "decision_ids": []},
        })
    return regions


def record(
    *,
    page: dict[str, Any],
    role: str,
    words: list[dict[str, Any]],
    reading_order: int,
    text_source: str,
    page_text: str,
    forced_type: str | None = None,
) -> dict[str, Any]:
    text = ordered_text(words)
    if forced_type:
        block_type = forced_type
        financial = False
        family = None
        reasons = [f"{forced_type}-position"]
    else:
        block_type, financial, family, reasons = classify_body(text, len(words), page_text)
    low_confidence = text_source == "ocr"
    confidence_level = "low" if low_confidence else "medium"
    confidence_score = 0.55 if low_confidence else (0.9 if forced_type else 0.78)
    review_status = "needs_review" if low_confidence else "proposed"
    review_reasons = ["automated-block-candidate"]
    if text_source == "ocr":
        review_reasons.append("ocr-derived-geometry")
    exclusion = "header_footer" if forced_type in {"header", "footer", "page_number"} else None
    block_key = f'{page["page_key"]}:{role}'
    box = union_box(words)
    return {
        "block_key": block_key,
        "candidate_key": block_key,
        "page_key": page["page_key"],
        "page_number": page["page_number"],
        "bbox": box,
        "polygon": None,
        "reading_order": reading_order,
        "block_type": block_type,
        "table_family_candidate": family,
        "text_source": text_source,
        "financial_candidate": financial,
        "regions": internal_regions(block_key, block_type, words),
        "anchors": [],
        "confidence": {
            "level": confidence_level,
            "score": confidence_score,
            "reason_codes": reasons,
        },
        "evidence": [{
            "page_key": page["page_key"],
            "page_number": page["page_number"],
            "block_key": block_key,
            "bbox": box,
            "text_excerpt": text[:240] or None,
        }],
        "exclusion_disposition": exclusion,
        "review": {
            "status": review_status,
            "reason_codes": review_reasons,
            "decision_ids": [],
        },
    }


def page_records(page: dict[str, Any], words: list[dict[str, Any]], text_source: str) -> list[dict[str, Any]]:
    page_text = ordered_text(words)
    footer = [word for word in words if word["bbox"]["y0"] >= CONFIG["footer_top"]]
    content = [word for word in words if word not in footer]
    results: list[dict[str, Any]] = []
    if len(content) <= CONFIG["sparse_page_word_limit"]:
        regions = [("body", content, None)]
    else:
        header = [word for word in content if word["bbox"]["y1"] <= CONFIG["body_top"]]
        body = [word for word in content if word not in header]
        regions = [("title", header, "title"), ("body", body, None)]
    if footer:
        footer_text = ordered_text(footer).strip()
        footer_type = "page_number" if re.fullmatch(r"\d{1,3}", footer_text) else "footer"
        regions.append(("footer", footer, footer_type))
    for role, region_words, forced_type in regions:
        if region_words:
            results.append(
                record(
                    page=page,
                    role=role,
                    words=region_words,
                    reading_order=len(results) + 1,
                    text_source=text_source,
                    page_text=page_text,
                    forced_type=forced_type,
                )
            )
    return results


def generate(*, source_evidence: Path, output: Path) -> tuple[dict[str, Any], str, str]:
    source_evidence = source_evidence.resolve()
    output = output.resolve()
    if not source_evidence.is_file():
        raise FileNotFoundError(source_evidence)
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Output must remain inside the repository: {output}")
    source = read_json(source_evidence)
    if source.get("artifact_type") != "source_evidence":
        raise ValueError("Stage 1 requires a source_evidence artifact")
    validator = load_validator()
    source_errors = validator.validate_payload(source)
    if source_errors:
        raise RuntimeError("Invalid Stage 0 source evidence: " + "; ".join(source_errors[:5]))

    records: list[dict[str, Any]] = []
    page_dispositions: list[dict[str, Any]] = []
    for page in source["pages"]:
        use_ocr = page["ocr"]["status"] == "completed"
        evidence_relpath = (
            page["ocr"]["evidence_relpath"] if use_ocr else page["embedded_text"]["evidence_relpath"]
        )
        evidence = read_json(ROOT / evidence_relpath)
        blocks = page_records(page, evidence.get("words", []), "ocr" if use_ocr else "embedded")
        records.extend(blocks)
        needs_review = not blocks or any(block["review"]["status"] == "needs_review" for block in blocks)
        if not blocks:
            status = "needs_review"
            reasons = ["no-word-derived-blocks"]
        elif needs_review:
            status = "needs_review"
            reasons = ["contains-low-confidence-blocks"]
        else:
            status = "inventoried"
            reasons = ["automated-candidate-inventory"]
        page_dispositions.append({
            "page_key": page["page_key"],
            "page_number": page["page_number"],
            "block_keys": [block["block_key"] for block in blocks],
            "status": status,
            "review": {"status": "needs_review" if needs_review else "proposed", "reason_codes": reasons, "decision_ids": []},
        })

    artifact = {
        "$schema": schema_reference(output),
        "schema_version": 1,
        "artifact_type": "block_inventory",
        "artifact_key": f'{source["document_key"]}:block-inventory:v1',
        "document_key": source["document_key"],
        "source_sha256": source["source_sha256"],
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "config_sha256": sha256_bytes(canonical_json_bytes(CONFIG)),
        },
        "upstream_artifacts": [{
            "artifact_type": "source_evidence",
            "artifact_key": source["artifact_key"],
            "sha256": sha256_path(source_evidence),
        }],
        "page_dispositions": page_dispositions,
        "records": records,
        "relationships": [],
    }
    errors = validator.validate_payload(artifact)
    if errors:
        raise RuntimeError("Generated Stage 1 artifact is invalid: " + "; ".join(errors[:10]))

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="stage-1-", dir=output.parent))
    try:
        artifact_path = temporary / "block-inventory.json"
        artifact_path.write_bytes(canonical_json_bytes(artifact))
        artifact_hash = sha256_path(artifact_path)
        if output.exists():
            existing = output / "block-inventory.json"
            if existing.is_file() and sha256_path(existing) == artifact_hash and len(list(output.iterdir())) == 1:
                return artifact, artifact_hash, "unchanged"
            raise RuntimeError("Stage 1 content conflict. Remove or move the existing output after review.")
        temporary.replace(output)
        return artifact, artifact_hash, "created"
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-evidence", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    artifact, artifact_hash, state = generate(source_evidence=args.source_evidence, output=args.out)
    financial = sum(record["financial_candidate"] for record in artifact["records"])
    review_pages = sum(page["status"] == "needs_review" for page in artifact["page_dispositions"])
    print(
        f"Stage 1 {state}: pages={len(artifact['page_dispositions'])}, "
        f"blocks={len(artifact['records'])}, financial_blocks={financial}, "
        f"review_pages={review_pages}, artifact_sha256={artifact_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate deterministic Stage 0 source evidence for a staged PDF workflow."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import fitz


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = (
    ROOT
    / "docs"
    / "charlottetown"
    / "budget"
    / "2026-2027 Financial Plan Capital and Operating Budgets.pdf"
)
DEFAULT_OUT = (
    ROOT
    / "data"
    / "budget"
    / "charlottetown"
    / "2026-2027"
    / "staged-pdf"
    / "v1"
    / "stage-0"
)
VALIDATOR_PATH = ROOT / "scripts" / "validate-staged-pdf-artifacts.py"
GENERATOR_NAME = "staged-pdf-source-evidence"
GENERATOR_VERSION = "1"


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> str:
    value = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return sha256_bytes(value)


def repo_relpath(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path is outside the repository: {resolved}")
    return resolved.relative_to(root).as_posix()


def schema_reference(output: Path) -> str:
    schema = ROOT / "schema" / "json-schema" / "staged-pdf-artifacts.schema.json"
    return Path(os.path.relpath(schema, output)).as_posix()


def find_tesseract() -> Path | None:
    command = shutil.which("tesseract")
    if command:
        return Path(command)
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files\PDF24\tesseract\tesseract.exe"),
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def tesseract_version(executable: Path | None) -> str | None:
    if executable is None:
        return None
    result = subprocess.run(
        [str(executable), "--version"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.splitlines()[0].strip()


def rounded(value: float) -> float:
    return round(float(value), 6)


def point_box(rect: fitz.Rect) -> dict[str, float]:
    return {
        "x0": rounded(rect.x0),
        "y0": rounded(rect.y0),
        "x1": rounded(rect.x1),
        "y1": rounded(rect.y1),
    }


def normalized_box(
    x0: float, y0: float, x1: float, y1: float, width: float, height: float
) -> dict[str, float]:
    return {
        "x0": rounded(x0 / width),
        "y0": rounded(y0 / height),
        "x1": rounded(x1 / width),
        "y1": rounded(y1 / height),
    }


def embedded_word_payload(
    page: fitz.Page, document_key: str, source_sha256: str
) -> dict[str, Any]:
    page_number = page.number + 1
    page_key = f"{document_key}:p{page_number:03d}"
    width = page.rect.width
    height = page.rect.height
    words = []
    for raw in page.get_text("words", sort=True):
        x0, y0, x1, y1, text, block_number, line_number, word_number = raw
        if not str(text).strip():
            continue
        words.append(
            {
                "text": str(text),
                "bbox_pt": {
                    "x0": rounded(x0),
                    "y0": rounded(y0),
                    "x1": rounded(x1),
                    "y1": rounded(y1),
                },
                "bbox": normalized_box(x0, y0, x1, y1, width, height),
                "block_number": int(block_number),
                "line_number": int(line_number),
                "word_number": int(word_number),
            }
        )
    return {
        "schema_version": 1,
        "evidence_type": "embedded_words",
        "document_key": document_key,
        "source_sha256": source_sha256,
        "page_key": page_key,
        "page_number": page_number,
        "width_pt": rounded(width),
        "height_pt": rounded(height),
        "word_count": len(words),
        "words": words,
    }


def ocr_word_payload(
    image_path: Path,
    page_key: str,
    page_number: int,
    source_sha256: str,
    document_key: str,
    executable: Path,
    engine_version: str,
    dpi: int,
    width_px: int,
    height_px: int,
) -> tuple[dict[str, Any], float]:
    result = subprocess.run(
        [
            str(executable),
            str(image_path),
            "stdout",
            "--dpi",
            str(dpi),
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    words: list[dict[str, Any]] = []
    confidences: list[float] = []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        text = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf") or -1)
            left = int(row.get("left") or 0)
            top = int(row.get("top") or 0)
            width = int(row.get("width") or 0)
            height = int(row.get("height") or 0)
        except ValueError:
            continue
        if not text or confidence < 0 or width <= 0 or height <= 0:
            continue
        confidences.append(confidence / 100)
        words.append(
            {
                "text": text,
                "confidence": rounded(confidence / 100),
                "bbox_px": {
                    "x0": left,
                    "y0": top,
                    "x1": left + width,
                    "y1": top + height,
                },
                "bbox": normalized_box(
                    left,
                    top,
                    left + width,
                    top + height,
                    width_px,
                    height_px,
                ),
                "block_number": int(row.get("block_num") or 0),
                "paragraph_number": int(row.get("par_num") or 0),
                "line_number": int(row.get("line_num") or 0),
                "word_number": int(row.get("word_num") or 0),
            }
        )
    mean_confidence = rounded(sum(confidences) / len(confidences)) if confidences else 0.0
    payload = {
        "schema_version": 1,
        "evidence_type": "ocr_words",
        "document_key": document_key,
        "source_sha256": source_sha256,
        "page_key": page_key,
        "page_number": page_number,
        "engine": "tesseract",
        "engine_version": engine_version,
        "dpi": dpi,
        "width_px": width_px,
        "height_px": height_px,
        "word_count": len(words),
        "mean_confidence": mean_confidence,
        "words": words,
    }
    return payload, mean_confidence


def load_artifact_validator() -> Any:
    spec = importlib.util.spec_from_file_location("staged_pdf_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def directory_hashes(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): sha256_path(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def compare_existing(generated: Path, existing: Path) -> None:
    generated_hashes = directory_hashes(generated)
    existing_hashes = directory_hashes(existing)
    if generated_hashes == existing_hashes:
        return
    added = sorted(set(generated_hashes) - set(existing_hashes))
    removed = sorted(set(existing_hashes) - set(generated_hashes))
    changed = sorted(
        key
        for key in set(generated_hashes) & set(existing_hashes)
        if generated_hashes[key] != existing_hashes[key]
    )
    raise RuntimeError(
        "Stage 0 content conflict. "
        f"Added={added[:10]}, removed={removed[:10]}, changed={changed[:10]}"
    )


def generate(
    *,
    pdf: Path,
    output: Path,
    document_key: str,
    municipality_key: str,
    document_kind: str,
    title: str,
    source_uri: str | None,
    render_dpi: int,
    thumbnail_dpi: int,
    minimum_embedded_word_count: int,
) -> tuple[dict[str, Any], str, str]:
    pdf = pdf.resolve()
    output = output.resolve()
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Output must remain inside the repository: {output}")
    if render_dpi < 72 or thumbnail_dpi < 72:
        raise ValueError("Render and thumbnail DPI must be at least 72")
    if minimum_embedded_word_count < 0:
        raise ValueError("Minimum embedded word count must not be negative")

    source_hash = sha256_path(pdf)
    tesseract = find_tesseract()
    ocr_version = tesseract_version(tesseract)
    config = {
        "generator_version": GENERATOR_VERSION,
        "renderer": "fitz",
        "renderer_version": fitz.VersionBind,
        "render_dpi": render_dpi,
        "thumbnail_dpi": thumbnail_dpi,
        "ocr_mode": "when_text_deficient",
        "minimum_embedded_word_count": minimum_embedded_word_count,
        "ocr_engine": "tesseract" if tesseract else None,
        "ocr_engine_version": ocr_version,
        "embedded_word_sort": True,
    }
    config_hash = sha256_bytes(canonical_json_bytes(config))
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = Path(
        tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent)
    ).resolve()
    try:
        renders = temp_output / "renders"
        thumbnails = temp_output / "thumbnails"
        embedded_dir = temp_output / "embedded-words"
        ocr_dir = temp_output / "ocr-words"
        for path in [renders, thumbnails, embedded_dir]:
            path.mkdir(parents=True, exist_ok=True)

        pages: list[dict[str, Any]] = []
        with fitz.open(pdf) as document:
            for page in document:
                page_number = page.number + 1
                page_key = f"{document_key}:p{page_number:03d}"
                filename = f"page-{page_number:03d}"
                render_path = renders / f"{filename}.png"
                thumbnail_path = thumbnails / f"{filename}.png"
                embedded_path = embedded_dir / f"{filename}.json"

                render_pixmap = page.get_pixmap(
                    dpi=render_dpi, colorspace=fitz.csRGB, alpha=False
                )
                render_pixmap.save(render_path)
                thumbnail_pixmap = page.get_pixmap(
                    dpi=thumbnail_dpi, colorspace=fitz.csRGB, alpha=False
                )
                thumbnail_pixmap.save(thumbnail_path)

                embedded_payload = embedded_word_payload(page, document_key, source_hash)
                embedded_hash = write_json(embedded_path, embedded_payload)
                embedded_count = embedded_payload["word_count"]
                ocr_record: dict[str, Any]
                evidence_disposition = "complete"
                reason_codes = ["embedded_text"]

                if embedded_count >= minimum_embedded_word_count:
                    ocr_record = {
                        "status": "not_needed",
                        "engine": None,
                        "engine_version": None,
                        "rotation": None,
                        "dpi": None,
                        "mean_confidence": None,
                        "evidence_relpath": None,
                        "sha256": None,
                    }
                elif tesseract is not None and ocr_version is not None:
                    ocr_dir.mkdir(parents=True, exist_ok=True)
                    ocr_path = ocr_dir / f"{filename}.json"
                    ocr_payload, mean_confidence = ocr_word_payload(
                        render_path,
                        page_key,
                        page_number,
                        source_hash,
                        document_key,
                        tesseract,
                        ocr_version,
                        render_dpi,
                        render_pixmap.width,
                        render_pixmap.height,
                    )
                    ocr_hash = write_json(ocr_path, ocr_payload)
                    ocr_record = {
                        "status": "completed",
                        "engine": "tesseract",
                        "engine_version": ocr_version,
                        "rotation": int(page.rotation),
                        "dpi": render_dpi,
                        "mean_confidence": mean_confidence,
                        "evidence_relpath": repo_relpath(
                            output / "ocr-words" / f"{filename}.json"
                        ),
                        "sha256": ocr_hash,
                    }
                    reason_codes = ["ocr_fallback"]
                    if ocr_payload["word_count"] < minimum_embedded_word_count:
                        evidence_disposition = "text_deficient"
                        reason_codes.append("low_ocr_word_count")
                else:
                    ocr_record = {
                        "status": "unavailable",
                        "engine": None,
                        "engine_version": None,
                        "rotation": None,
                        "dpi": None,
                        "mean_confidence": None,
                        "evidence_relpath": None,
                        "sha256": None,
                    }
                    evidence_disposition = "blocked"
                    reason_codes = ["ocr_required", "ocr_unavailable"]

                pages.append(
                    {
                        "page_key": page_key,
                        "page_number": page_number,
                        "width_pt": rounded(page.rect.width),
                        "height_pt": rounded(page.rect.height),
                        "rotation": int(page.rotation),
                        "media_box": point_box(page.mediabox),
                        "crop_box": point_box(page.cropbox),
                        "render": {
                            "repo_relpath": repo_relpath(
                                output / "renders" / f"{filename}.png"
                            ),
                            "sha256": sha256_path(render_path),
                            "width_px": render_pixmap.width,
                            "height_px": render_pixmap.height,
                            "dpi": render_dpi,
                        },
                        "thumbnail": {
                            "repo_relpath": repo_relpath(
                                output / "thumbnails" / f"{filename}.png"
                            ),
                            "sha256": sha256_path(thumbnail_path),
                            "width_px": thumbnail_pixmap.width,
                            "height_px": thumbnail_pixmap.height,
                            "dpi": thumbnail_dpi,
                        },
                        "embedded_text": {
                            "available": embedded_count > 0,
                            "word_count": embedded_count,
                            "evidence_relpath": repo_relpath(
                                output / "embedded-words" / f"{filename}.json"
                            ),
                            "sha256": embedded_hash,
                        },
                        "ocr": ocr_record,
                        "evidence_disposition": evidence_disposition,
                        "review": {
                            "status": (
                                "needs_review"
                                if evidence_disposition in {"text_deficient", "blocked"}
                                else "proposed"
                            ),
                            "reason_codes": reason_codes,
                            "decision_ids": [],
                        },
                    }
                )

            artifact = {
                "$schema": schema_reference(output),
                "schema_version": 1,
                "artifact_type": "source_evidence",
                "artifact_key": f"{document_key}:source-evidence:v1",
                "document_key": document_key,
                "source_sha256": source_hash,
                "generator": {
                    "name": GENERATOR_NAME,
                    "version": GENERATOR_VERSION,
                    "config_sha256": config_hash,
                },
                "upstream_artifacts": [],
                "source": {
                    "title": title,
                    "municipality_key": municipality_key,
                    "document_kind": document_kind,
                    "repo_relpath": repo_relpath(pdf),
                    "source_uri": source_uri,
                    "sha256": source_hash,
                    "page_count": len(document),
                },
                "render_policy": {
                    "renderer": "fitz",
                    "renderer_version": fitz.VersionBind,
                    "dpi": render_dpi,
                    "color_mode": "rgb",
                },
                "ocr_policy": {
                    "mode": "when_text_deficient",
                    "minimum_embedded_word_count": minimum_embedded_word_count,
                    "engine": "tesseract" if tesseract else None,
                    "engine_version": ocr_version,
                },
                "pages": pages,
            }

        validator_module = load_artifact_validator()
        validation_errors = validator_module.validate_payload(artifact)
        if validation_errors:
            raise RuntimeError(
                "Generated source evidence failed validation:\n"
                + "\n".join(validation_errors)
            )
        artifact_hash = write_json(temp_output / "source-evidence.json", artifact)

        if output.exists():
            compare_existing(temp_output, output)
            output_state = "unchanged"
        else:
            temp_output.replace(output)
            output_state = "created"
        return artifact, artifact_hash, output_state
    finally:
        if temp_output.exists():
            shutil.rmtree(temp_output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--document-key", default="ctown-budget-2026-2027")
    parser.add_argument("--municipality-key", default="charlottetown")
    parser.add_argument("--document-kind", default="budget")
    parser.add_argument(
        "--title",
        default="2026-2027 Financial Plan Capital and Operating Budgets",
    )
    parser.add_argument("--source-uri")
    parser.add_argument("--render-dpi", type=int, default=144)
    parser.add_argument("--thumbnail-dpi", type=int, default=72)
    parser.add_argument("--minimum-embedded-word-count", type=int, default=5)
    args = parser.parse_args()

    artifact, artifact_hash, output_state = generate(
        pdf=args.pdf,
        output=args.out,
        document_key=args.document_key,
        municipality_key=args.municipality_key,
        document_kind=args.document_kind,
        title=args.title,
        source_uri=args.source_uri,
        render_dpi=args.render_dpi,
        thumbnail_dpi=args.thumbnail_dpi,
        minimum_embedded_word_count=args.minimum_embedded_word_count,
    )
    pages = artifact["pages"]
    ocr_pages = sum(page["ocr"]["status"] == "completed" for page in pages)
    blocked_pages = sum(page["evidence_disposition"] == "blocked" for page in pages)
    print(
        f"Stage 0 {output_state}: pages={len(pages)}, "
        f"ocr_pages={ocr_pages}, blocked_pages={blocked_pages}, "
        f"artifact_sha256={artifact_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

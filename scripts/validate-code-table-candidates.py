from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "json-schema" / "candidate-code-table-seed.schema.json"
CANDIDATE_DIR = ROOT / "data" / "normalized" / "code-tables" / "candidates"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate candidate code-table seed files.")
    parser.add_argument("--candidate-dir", type=Path, default=CANDIDATE_DIR)
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    paths = sorted(args.candidate_dir.glob("**/*_candidate.seed.json"))
    failures: list[str] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
        ids = [entry.get("candidate_id") for entry in payload.get("entries", [])]
        duplicates = sorted({candidate_id for candidate_id in ids if ids.count(candidate_id) > 1})
        if duplicates:
            failures.append(f"{path}: duplicate candidate ids: {', '.join(duplicates)}")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "$"
            failures.append(f"{path}: {location}: {error.message}")

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print(f"Validated {len(paths)} candidate code-table seed files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "json-schema" / "code-table-seed.schema.json"
SEED_DIR = ROOT / "data" / "normalized" / "code-tables"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    failures: list[str] = []
    for path in sorted(SEED_DIR.glob("*.seed.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
        codes = [entry.get("code") for entry in payload.get("entries", [])]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            failures.append(f"{path}: duplicate codes: {', '.join(duplicates)}")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "$"
            failures.append(f"{path}: {location}: {error.message}")

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print(f"Validated {len(list(SEED_DIR.glob('*.seed.json')))} code-table seed files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

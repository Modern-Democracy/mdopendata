from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "schema" / "sql" / "025_budget_schema.sql"
REGRESSION = REPO_ROOT / "schema" / "tests" / "025_budget_schema_regression.sql"


def regression_body() -> str:
    sql = REGRESSION.read_text(encoding="utf-8")
    sql = re.sub(r"(?m)^\\set ON_ERROR_STOP on\s*$", "", sql)
    sql = re.sub(r"(?m)^BEGIN;\s*$", "", sql)
    sql = re.sub(r"(?m)^ROLLBACK;\s*$", "", sql)
    return sql.strip()


def main() -> int:
    container = os.environ.get("PGCONTAINER", "mdopendata-postgis")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    sql = (
        "BEGIN;\n"
        f"{MIGRATION.read_text(encoding='utf-8').rstrip()}\n"
        f"{regression_body()}\n"
        "ROLLBACK;\n"
    )
    result = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-q", "-v", "ON_ERROR_STOP=1", "-U", user, "-d", database],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stderr)
        return result.returncode
    print("Budget migration regression controls passed; transaction rolled back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

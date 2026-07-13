from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = (
    REPO_ROOT / "schema" / "sql" / "025_budget_schema.sql",
    REPO_ROOT / "schema" / "sql" / "027_budget_web_taxonomy.sql",
)
REGRESSIONS = (
    REPO_ROOT / "schema" / "tests" / "025_budget_schema_regression.sql",
    REPO_ROOT / "schema" / "tests" / "027_budget_web_taxonomy_regression.sql",
)


def main() -> int:
    container = os.environ.get("PGCONTAINER", "mdopendata-postgis")
    user = os.environ.get("PGUSER", "mdopendata")
    admin_database = os.environ.get("PGADMIN_DATABASE", "postgres")
    database = f"budget_migration_test_{uuid.uuid4().hex}"
    sql = "\n".join(path.read_text(encoding="utf-8").rstrip() for path in (*MIGRATIONS, *REGRESSIONS)) + "\n"

    def psql(target_database: str, input_sql: str | None = None, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "exec", "-i", container, "psql", "-q", "-v", "ON_ERROR_STOP=1", "-U", user, "-d", target_database, *args],
            input=input_sql,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=REPO_ROOT,
            check=False,
        )

    created = False
    try:
        create = psql(admin_database, None, "-c", f"CREATE DATABASE {database} TEMPLATE template0")
        if create.returncode:
            sys.stderr.write(create.stderr)
            return create.returncode
        created = True
        result = psql(database, sql)
        if result.returncode:
            sys.stderr.write(result.stderr)
            return result.returncode
        print(f"Budget migration regression controls passed in isolated database {database}.")
        return 0
    finally:
        if created:
            drop = psql(admin_database, None, "-c", f"DROP DATABASE IF EXISTS {database}")
            if drop.returncode:
                sys.stderr.write(f"Failed to remove temporary database {database}:\n{drop.stderr}")


if __name__ == "__main__":
    raise SystemExit(main())

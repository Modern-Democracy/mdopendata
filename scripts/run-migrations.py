from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = (
    REPO_ROOT / "schema" / "001_zoning_schema.sql",
    REPO_ROOT / "schema" / "002_zoning_views.sql",
    REPO_ROOT / "schema" / "003_rename_zoning_schema_to_hrm.sql",
)


def db_env() -> tuple[str, str, str]:
    return (
        os.environ.get("PGCONTAINER", "mdopendata-postgis"),
        os.environ.get("PGDATABASE", "mdopendata"),
        os.environ.get("PGUSER", "mdopendata"),
    )


def psql(sql: str, *, capture: bool = False) -> str:
    container, database, user = db_env()
    (REPO_ROOT / ".docker-local").mkdir(exist_ok=True)
    env = os.environ.copy()
    env["DOCKER_CONFIG"] = str(REPO_ROOT / ".docker-local")
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        user,
        "-d",
        database,
    ]
    if capture:
        command.append("-At")
    result = subprocess.run(
        command,
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def ensure_migration_table() -> None:
    psql(
        """
        CREATE TABLE IF NOT EXISTS public.schema_migrations (
          filename text PRIMARY KEY,
          applied_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def applied_migrations() -> set[str]:
    output = psql("SELECT filename FROM public.schema_migrations ORDER BY filename;\n", capture=True)
    return {line.strip() for line in output.splitlines() if line.strip()}


def apply_migration(path: Path) -> None:
    sql = (
        "BEGIN;\n"
        f"{path.read_text(encoding='utf-8').rstrip()}\n"
        f"INSERT INTO public.schema_migrations (filename) VALUES ('{path.name}') "
        "ON CONFLICT (filename) DO NOTHING;\n"
        "COMMIT;\n"
    )
    psql(sql)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply repository SQL migrations.")
    parser.add_argument("--list", action="store_true", help="List pending migrations.")
    args = parser.parse_args()

    ensure_migration_table()
    applied = applied_migrations()
    pending = [path for path in MIGRATIONS if path.name not in applied]

    if args.list:
        for path in pending:
            print(path.name)
        return 0

    if not pending:
        print("No pending migrations.")
        return 0

    for path in pending:
        print(f"Applying {path.name}")
        apply_migration(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

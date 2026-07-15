---
type: platform
tags:
  - environment
  - python
  - dependencies
  - deployment
updated: 2026-07-14
---

This page records the canonical project runtime, dependency, and environment-management contract.

# Project Environment

## Ownership and Change Control

The `DevOps` role at `../../.codex/skills/role-dev-ops/SKILL.md` is the sole role authorized to install or update dependencies and mutate project environments, toolchains, containers, infrastructure, CI/CD, or deployment targets. DevOps must review the current state and obtain explicit user approval for the exact proposed change before mutation.

Other roles route operational requirements to DevOps. DevOps updates project documentation and this wiki when the verified setup changes.

## Canonical Python Runtime

The canonical repository Python environment is `.venv`, created with Python 3.14 or newer as required by `pyproject.toml`. The repository wrapper `scripts/python.ps1` resolves and invokes:

```text
.venv\Scripts\python.exe
```

Run project scripts through the wrapper:

```powershell
.\scripts\python.ps1 .\scripts\validate-code-table-candidates.py
```

`pyproject.toml` defines supported dependency ranges. `requirements.lock.txt` records the exact validated Python dependency set. Installation and refresh commands remain in the root `README.md`.

## Separate Python Runtimes

QGIS MCP does not use the canonical `.venv`. It uses the Python runtime bundled with the installed QGIS version, plus `.qgis-mcp-packages` and `qgis_mcp_vendor`, as configured by `scripts/start-qgis-mcp.ps1`.

Historical `.python` paths and Codex bundled-runtime paths in generated manifests or old workflow notes are not the canonical project runtime. They must not be copied into new setup instructions.

## Current Deployment Surfaces

- Local services use Docker Compose through `docker-compose.yml`.
- The optional AWS deployment target is a single-host AWS EC2 Docker Compose deployment described in `wiki/implementation/aws-deployment.md`.
- The canonical user-facing demonstration target is the Render Docker web service at `https://mdopendata-demo.onrender.com`, backed by a one-time Supabase PostGIS snapshot and described in `wiki/implementation/render-supabase-deployment.md`.
- Requests to inspect or demonstrate the deployed application route to the Render endpoint; ingestion and other write workflows remain local.
- Adding or changing a deployment target requires DevOps review and explicit user approval.

## Budget Raw Import Versioning

Budget raw tables are append-only. When reviewed extraction artifacts change after import, do not update or delete existing raw rows or cells. Use `scripts/sync-budget-2026-raw-content.py` to append a versioned raw namespace after explicit approval. The Charlottetown 2026/2027 normalized manifest targets `full-2`; the two prior-year manifests target corrected `full-3` namespaces. Earlier imports remain immutable historical extraction evidence.

Run a rollback-only validation before mutation:

```powershell
.\scripts\python.ps1 .\scripts\sync-budget-2026-raw-content.py --dry-run
```

Run the approved append-only import without `--dry-run`, then validate provenance with:

```powershell
.\scripts\python.ps1 .\scripts\validate-budget-2026-normalized-provenance.py --database
```

## Budget Migration Repair

Migration `026_budget_capital_project_reference.sql` restores the approved document-to-project reference table when migration 025 was recorded before that table reached the active database. It is additive and preserves project identity independently of fiscal-year documents. The pre-migration rollback artifact is `backups/database/mdopendata-before-prior-year-normalized-20260712.dump`.

## Isolated Budget Migration Regression Test

`scripts/test-budget-migration.py` creates a uniquely named empty PostgreSQL database from `template0` in `mdopendata-postgis`, applies migrations 025 and 027 through 031 with their regression controls, then drops the temporary database. It never applies DDL to the active `mdopendata` database. The test uses `PGCONTAINER`, `PGUSER`, and optional `PGADMIN_DATABASE` environment variables; the configured database role must have `CREATEDB` permission.

## Budget Web Taxonomy Migration

Migration 027 and `scripts/apply-budget-web-taxonomy.py` implement the authorized budget-edition, assignment, taxonomy-revision, capital-program, and subsequent-forecast records. The verified pre-migration backup is `backups/database/mdopendata-before-budget-web-taxonomy-20260713.dump`. Run the assignment script without `--apply` for rollback-only validation; use `--apply` only after explicit authorization. A verified repeat apply writes zero records.

The local `web` service was rebuilt from the existing Docker Compose definition after the server and static UI changes. No dependency, lockfile, runtime, secret, port, or deployment-target change was made.

## Required Documentation for Changes

Every environment or deployment change must record:

- the effective runtime or tool version and its source of truth
- reproducible setup or update commands
- affected manifests, lockfiles, wrappers, containers, and deployment targets
- required environment-variable names without secret values
- verification results, exceptions, and rollback instructions
- corresponding updates to project documentation, this wiki, `wiki/index.md`, and `wiki/log.md`

## Sources

- [Root README](../../README.md)
- [Python project configuration](../../pyproject.toml)
- [Locked Python dependencies](../../requirements.lock.txt)
- [Python wrapper](../../scripts/python.ps1)
- [Budget migration regression test](../../scripts/test-budget-migration.py)
- [QGIS MCP launcher](../../scripts/start-qgis-mcp.ps1)
- [AWS deployment](../implementation/aws-deployment.md)
- [Repository instructions](../../AGENTS.md)

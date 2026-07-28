---
type: implementation
tags:
  - render
  - supabase
  - deployment
  - demo
  - postgis
updated: 2026-07-28
---

This page documents the read-only demonstration deployment of the mdopendata web application on Render with a one-time PostGIS snapshot in Supabase.

# Render and Supabase Demonstration Deployment

## Deployment shape

- Render runs [`web/Dockerfile.render`](../../web/Dockerfile.render) from the repository root context.
- [`render.yaml`](../../render.yaml) configures the web service, health check, server-side database secret, and `DEMO_MODE=true`.
- Supabase stores a one-time snapshot of the local PostgreSQL/PostGIS database.
- Local ingestion, uploads, extraction, and review writes remain local.
- The remote service packages tracked `data/` files only. Ignored local PDFs, uploads, rendered page images, and terrain DEM files are not part of the image.

## Supabase bootstrap

Use a new Supabase project with PostGIS enabled. From the repository root, with the local `mdopendata-postgis` container running:

```powershell
$env:DATABASE_URL = "postgresql://..."
.\scripts\supabase-bootstrap.ps1
```

The script enables PostGIS and PostGIS raster in the `extensions` schema, exports the local `public`, `zoning`, `budget`, `council`, and `help` schemas, removes the local `public` schema declaration, restores the schema to Supabase, seeds the repository migration filenames as applied for the snapshot, and restores data without owners or ACLs. It excludes `public.spatial_ref_sys` and `public.schema_migrations` from the data dump. Use `-SchemaOnly` to omit data. The target must be a new project because the bootstrap is a snapshot restore, not a merge operation.

For later repository migrations, set `DATABASE_URL` and run:

```powershell
.\scripts\python.ps1 .\scripts\run-migrations.py --base-schema
```

Migration `032_enable_demo_row_level_security.sql` enables row-level security
on every ordinary table in `public`, `zoning`, `budget`, `council`, and `help`.
It creates no policies, so Supabase `anon` and `authenticated` roles receive
default-deny table access. Render continues to query through the server-side
database owner connection, which bypasses RLS. Do not replace that connection
with an anonymous or authenticated Supabase client credential.

## Render configuration

The canonical demonstration endpoint is [https://mdopendata-demo.onrender.com](https://mdopendata-demo.onrender.com), provided by the free Render web service `mdopendata-demo`. The Render Blueprint flow in this workspace required payment information, so the service was created through the manual free-instance flow without adding payment details. [`render.yaml`](../../render.yaml) remains the reproducible configuration reference. Set `DATABASE_URL` to the Supabase PostgreSQL connection string as a secret. The service uses `HOST=0.0.0.0`, port `10000`, `REPO_ROOT=/workspace`, SSL, the `public,extensions` search path, and a five-connection application pool.

The service health endpoint is `/healthz`. It requires a successful `SELECT 1` against Supabase. `DEMO_MODE=true` returns HTTP 403 for non-GET requests under `/api/document-ingestion/` and for section-equivalence decision writes.

## Endpoint routing

- Route user requests to inspect, demonstrate, or verify the deployed application to `https://mdopendata-demo.onrender.com`.
- Verify service availability with `GET https://mdopendata-demo.onrender.com/healthz`.
- Treat the endpoint as read-only demonstration infrastructure. Route ingestion, uploads, extraction, review writes, and other mutation workflows to the local environment.
- Do not substitute the AWS deployment endpoint for demonstration requests. AWS remains a separate infrastructure workflow documented in [AWS deployment](./aws-deployment.md).

## Verification

```powershell
docker build -f web/Dockerfile.render -t mdopendata-demo .
$env:WEB_SMOKE_BASE_URL = "https://mdopendata-demo.onrender.com"
npm run web:smoke
```

Verify Supabase with table counts for `zoning.section`, `budget.financial_observation`, `council.meeting`, and `help.term`. Verify `/healthz` before running the full smoke suite.

Verify RLS coverage with:

```sql
SELECT n.nspname, c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('public', 'zoning', 'budget', 'council', 'help')
  AND c.relkind IN ('r', 'p')
  AND NOT c.relrowsecurity;
```

The query must return zero rows. If Render cannot read after the migration,
disable RLS only as a temporary rollback while restoring its database owner
connection.

Migration 032 was applied to the demo Supabase project on 2026-07-28. The
remote verification covered 145 tables: `budget` 58, `council` 29, `help` 6,
`public` 28, and `zoning` 24, with every table reporting RLS enabled. Supabase
Advisor reported no remaining issues, Render `/healthz` returned HTTP 200, and
35 read-only smoke checks passed. The separate published-budget source-page
check for source 9 returned HTTP 404 and remains an unrelated packaged-source
artifact exception.

## Rollback and limits

Render can roll back to the previous deploy. Preserve the generated local dump until the Supabase snapshot has been verified. The remote filesystem is ephemeral by design; no ingestion artifact is considered durable on Render.

## Sources

- [Render Blueprint](../../render.yaml)
- [Render production Dockerfile](../../web/Dockerfile.render)
- [Supabase bootstrap script](../../scripts/supabase-bootstrap.ps1)
- [Migration runner](../../scripts/run-migrations.py)
- [Root README](../../README.md)
- [Project environment](../platform/project-environment.md)

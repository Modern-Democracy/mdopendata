---
type: implementation
tags:
  - render
  - supabase
  - deployment
  - demo
  - postgis
updated: 2026-07-14
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

## Render configuration

The demonstration service is deployed as the free Render web service `mdopendata-demo` at [mdopendata-demo.onrender.com](https://mdopendata-demo.onrender.com). The Render Blueprint flow in this workspace required payment information, so the service was created through the manual free-instance flow without adding payment details. [`render.yaml`](../../render.yaml) remains the reproducible configuration reference. Set `DATABASE_URL` to the Supabase PostgreSQL connection string as a secret. The service uses `HOST=0.0.0.0`, port `10000`, `REPO_ROOT=/workspace`, SSL, the `public,extensions` search path, and a five-connection application pool.

The service health endpoint is `/healthz`. It requires a successful `SELECT 1` against Supabase. `DEMO_MODE=true` returns HTTP 403 for non-GET requests under `/api/document-ingestion/` and for section-equivalence decision writes.

## Verification

```powershell
docker build -f web/Dockerfile.render -t mdopendata-demo .
$env:WEB_SMOKE_BASE_URL = "https://YOUR-SERVICE.onrender.com"
npm run web:smoke
```

Verify Supabase with table counts for `zoning.section`, `budget.financial_observation`, `council.meeting`, and `help.term`. Verify `/healthz` before running the full smoke suite.

## Rollback and limits

Render can roll back to the previous deploy. Preserve the generated local dump until the Supabase snapshot has been verified. The remote filesystem is ephemeral by design; no ingestion artifact is considered durable on Render.

## Sources

- [Render Blueprint](../../render.yaml)
- [Render production Dockerfile](../../web/Dockerfile.render)
- [Supabase bootstrap script](../../scripts/supabase-bootstrap.ps1)
- [Migration runner](../../scripts/run-migrations.py)
- [Root README](../../README.md)
- [Project environment](../platform/project-environment.md)

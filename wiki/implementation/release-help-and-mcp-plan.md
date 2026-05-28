---
type: implementation
tags:
  - help
  - mcp
  - wiki
  - web-ui
updated: 2026-05-28
---

This page records the first implementation pattern for release-facing contextual help and the repo-local `mdopendata-mcp` server.

# Release Help And MCP Plan

## Wiki Source Rule

Markdown under `wiki/` remains the canonical internal knowledge source. The release-facing help layer is generated, exported, or queried from reviewed Markdown and database records; it does not replace the existing wiki schema.

Template HTML conventions may guide generated release layout, but hand-authored HTML is not the source of truth for durable project knowledge.

## Help Schema

The `help` database schema stores release-safe contextual help for the web application. It separates business and technical terms from code-table values so the UI can request compact help records for routes, fields, filters, tooltips, panels, and glossary pages.

The first schema includes:

| Table | Purpose |
| --- | --- |
| `help.term` | Release-reviewed business and technical terms with citations and source table references. |
| `help.code_table` | Named code sets such as zoning topics, zone crosswalks, meeting statuses, and business item statuses. |
| `help.code_value` | Individual code values with raw values, display labels, descriptions, citations, and release status. |
| `help.context_binding` | Route, field, card, filter, tooltip, or panel bindings for contextual UI help. |
| `help.import_batch` and `help.import_record_event` | Repeatable seed/import tracking using the project import pattern. |

The first seed path is `scripts/seed-help-context.py`, which reads existing zoning and council records, preserves raw labels, and inserts release-ready help records through natural-key, content-hash, active-row, and supersession fields.

## Web Boundary

The Node web service remains the database boundary. Browser code reads help through these JSON APIs:

- `GET /api/help/terms`
- `GET /api/help/terms/:termKey`
- `GET /api/help/code-tables/:tableKey`
- `GET /api/help/context/:contextKey`

The first UI integration is `/help`, a small release-facing help page that reads public terms and the `route:/zoning-comparison` context binding.

## MCP Boundary

The repo-local MCP package lives under `mcp/` and is registered as `mdopendata` beside the existing read-only Postgres and QGIS MCP servers.

The package is project-aware:

- schema introspection reads `schema/sql/*.sql`
- database querying remains read-only
- schema docs generate Markdown under `wiki/generated/schema/`
- diagrams and charts may save images under `wiki/shared/assets/`
- release help export writes `web/public/help/release-help.json`

Schema or data mutations still go through SQL migrations and Python scripts, not MCP tools.

## ERD Export Workflow

The release ERD image for the zoning schema is exported from pgAdmin rather than the MCP fallback renderer. The repeatable path is:

```powershell
$env:NODE_PATH = Join-Path $env:USERPROFILE 'node_modules'
$env:PGADMIN_EMAIL = '<pgAdmin email>'
$env:PGADMIN_PASSWORD = '<pgAdmin password>'
npm run erd:pgadmin:zoning
```

The script opens pgAdmin in Playwright, connects the registered `mdopendata PostGIS` server, selects the `zoning` schema, opens pgAdmin's generated ERD tool, clicks Zoom to Fit, clicks Download image, and saves the PNG to `wiki/shared/assets/zoning-schema-erd.png`.

The MCP Graphviz/matplotlib renderer remains available only as a lightweight fallback for quick diagrams and charts. pgAdmin is the preferred workflow for release ERD assets when its richer table layout and relationship rendering are required.

## Sources

- [Wiki schema](../AGENTS.md)
- [Web UI stack](./web-ui-stack.md)
- [Zoning data-layer conventions](../charlottetown/topics/data-layer-conventions.md)
- [MCP config](../../.codex/mcp.json)
- [Help schema migration](../../schema/sql/021_help_schema.sql)
- [Help seed script](../../scripts/seed-help-context.py)
- [pgAdmin ERD export script](../../scripts/export-pgadmin-erd.mjs)

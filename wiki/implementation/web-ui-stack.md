---
type: implementation
tags:
  - web-ui
  - docker
  - charlottetown
updated: 2026-04-29
---

This page records the initial web UI stack decision for hosted review tools over the mdopendata database and zoning review artifacts.

# Web UI Stack

## Decision

Use a small Node.js HTTP service in Docker as the initial hosted web interface.

For the first Charlottetown review page, the service uses server-side JavaScript with the `pg` driver and static client files:

- Container service: `web` in `docker-compose.yml`.
- Server entry point: `web/server.js`.
- Static UI files: `web/public`.
- Local URL: `http://localhost:3000` by default, controlled by `WEB_PORT`.

## Rationale

This stack is intentionally small for the first review milestone. It exposes JSON APIs beside static pages without committing the repository to a frontend build system before the review workflows stabilize.

The first page reads `zoning.section_equivalence`, `zoning.section`, `zoning.clause`, `zoning.raw_table`, and `zoning.raw_table_cell` directly from PostgreSQL and displays the selected row as a split-pane current-versus-draft section review.

## Near-Term Direction

Keep the client as static HTML, CSS, and JavaScript until the UI needs shared components, routing, or complex state. Revisit a compiled framework such as React plus Vite only after there are multiple database-backed screens with repeated UI patterns.

Use the Node service as the boundary for database access. Browser code should not connect directly to PostGIS.

## Sources

- [Root README](../../README.md)
- [Docker Compose](../../docker-compose.yml)
- [Web server](../../web/server.js)
- [Section-equivalence review export](../../data/zoning/charlottetown-draft/review/section-equivalence-review.csv)
- [Charlottetown unified zoning ingestion plan](../charlottetown/topics/unified-zoning-ingestion-plan.md)

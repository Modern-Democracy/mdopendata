---
type: implementation
tags:
  - web-ui
  - docker
  - charlottetown
updated: 2026-05-20
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

Keep the current React/Babel page pattern while the municipal portal 1.0 shell and route stubs are established. Before writing new reusable components, complete the basic-HTML feasibility study described in the portal UI architecture page to decide whether to stay with React/Babel, migrate gradually, or switch to basic HTML/CSS/first-party JavaScript before component buildout.

Use the Node service as the boundary for database access. Browser code should not connect directly to PostGIS.

The staged PDF inventory reviewer also uses this Node/static boundary, but it reads allowlisted repository artifacts without querying PostgreSQL. Its route is disabled by default, denied in demo mode, and restricted to loopback. The host launcher uses port 3217 so the canonical Windows Python validator remains available.

## Sources

- [Root README](../../README.md)
- [Docker Compose](../../docker-compose.yml)
- [Web server](../../web/server.js)
- [Section-equivalence review export](../../data/zoning/charlottetown-draft/review/section-equivalence-review.csv)
- [Charlottetown unified zoning ingestion plan](../charlottetown/topics/unified-zoning-ingestion-plan.md)
- [Municipal portal UI architecture](../product/municipal-portal-ui-architecture.md)
- [Staged PDF inventory review UI](./staged-pdf-inventory-review-ui-plan.md)

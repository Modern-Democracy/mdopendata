---
type: project
tags:
  - charlottetown
  - wiki
updated: 2026-04-28
---

This wiki is the LLM-maintained working knowledge layer for the Charlottetown current and draft zoning workstream. It is documentation-only and does not replace the source PDFs, extracted JSON, maps, spatial files, plans, schemas, scripts, or database imports.

# Charlottetown LLM Wiki

## Scope

Use this wiki for Charlottetown zoning knowledge only:

- current Charlottetown zoning bylaw extraction
- draft Charlottetown zoning bylaw extraction
- current and draft zoning comparison notes
- source-aware questions, lint reports, and reusable analysis notes
- later parcel, street, map, and neighbourhood comparison notes when approved

Do not use this wiki for HRM, PEI corporate land-use, or unrelated municipal sources unless a later task explicitly expands the scope.

## Active Workstream

The active workstream is the City of Charlottetown current and draft zoning bylaw extraction, including associated zoning maps, parcel layer, and street map.

Use source material under `docs/charlottetown`. Write current zoning bylaw extraction outputs under `data/zoning/charlottetown` and draft zoning bylaw extraction outputs under `data/zoning/charlottetown-draft` unless the task explicitly names another destination.

The current purpose is to enable parcel and neighbourhood comparison between current and draft Charlottetown zoning, with outputs suitable for later PostGIS/QGIS use and a future public web front end.

For the Charlottetown draft zoning validation workstream, keep `plan/chalottetown-draft-zoning-timeline.md` up to date until the plan is complete. Update its active phase, overall status, current progress, and phase statuses whenever work advances, pauses, is blocked, or completes.

## Source Policy

Raw sources remain outside the wiki and must not be copied here. Reference existing repository files in place, including:

- `docs/charlottetown`
- `maps`
- `data/zoning/charlottetown`
- `data/zoning/charlottetown-draft`
- `data/spatial/charlottetown`
- `plan`

The source files are the authority. Wiki pages are synthesized notes and must stay traceable to the source files.

## Citation Rules

Every substantive zoning claim added after this scaffold must include source support. Use repository-relative citations and include the most specific locator available:

- source file path
- PDF page or visible bylaw page where known
- clause label exactly as written in the source
- zone code, schedule name, map layer, JSON file, or object identifier where relevant

Preserve raw clause labels exactly as written in the source. Follow `wiki/domain/bylaw-clause-labels.md` for clause hierarchy, compact labels, repealed labels, and review flags.

## Page Types

- `sources`: source-summary pages for PDFs, extracted JSON families, map layers, plans, or other approved source artifacts
- `entities`: pages for named objects such as zones, maps, schedules, parcels, streets, neighbourhoods, or bylaws
- `topics`: concept pages such as permitted uses, parking, height, setbacks, overlays, definitions, or review issues
- `comparisons`: reusable current-versus-draft or parcel/neighbourhood comparison pages
- `questions`: durable answers produced from user queries
- `templates`: page templates for future maintenance

## Ingest Workflow

When ingesting an approved source into the wiki:

1. Read the source and nearby existing wiki pages.
2. Create or update the relevant source, entity, topic, comparison, or question pages.
3. Cite source paths and precise locators for every substantive claim.
4. Update `index.md` in the same change.
5. Append one entry to `log.md` in the same change.
6. Stop and report ambiguity instead of inventing unsupported zoning conclusions.

## Query Workflow

When answering against the wiki:

1. Read `index.md` first.
2. Read the relevant wiki pages and cited source files.
3. Answer with citations.
4. If the answer is reusable, file it under `questions` or `comparisons`, update `index.md`, and append `log.md`.

## Lint Workflow

Wiki lint passes should check:

- broken links
- orphan pages
- missing citations
- stale claims superseded by newer source files
- claims contradicted by cited sources
- recurring entities or topics that lack pages
- pages missing from `index.md`

File lint reports under a future `questions` or `comparisons` page only when the report is useful beyond the current chat.

## V1 Limits

This v1 scaffold contains no substantive bylaw synthesis. It adds only the directory structure, templates, index, log, and maintenance contract.

Do not add scripts, database integration, search tooling, schema changes, extraction changes, Obsidian configuration, or generated zoning output changes as part of this v1 wiki scaffold.

## Sources

- [Charlottetown workstream context](./topics/workstream-context.md)
- [Root wiki schema](../AGENTS.md)

---
type: schema
tags:
  - wiki
  - schema
updated: 2026-04-28
---

This document defines the schema, directory layout, and maintenance workflows for the repository markdown wiki.

# Wiki Schema

## Layering

The wiki uses three layers:

1. Raw Sources: Immutable or source-of-record project files outside the wiki, including PDFs, maps, extracted data, plans, schemas, scripts, and database outputs.
2. Wiki: LLM-maintained markdown synthesis under `wiki/` for durable project knowledge, source summaries, domain concepts, reusable analyses, and human reference.
3. Schema: This document, which governs wiki structure, page conventions, maintenance workflows, and quality checks.

Raw Sources remain authoritative. Wiki pages summarize and connect raw sources, but do not replace them.

## Directory Layout

```text
wiki/
  AGENTS.md
  index.md
  log.md
  sources/
  domain/
  platform/
  implementation/
  charlottetown/
```

| Path | Purpose |
| --- | --- |
| [AGENTS.md](./AGENTS.md) | Root schema and maintenance contract for the wiki. |
| [index.md](./index.md) | Central content catalog for wiki pages and page areas. |
| [log.md](./log.md) | Append-only chronological record of ingests, substantive queries, lint passes, and structural changes. |
| [sources/](./sources/.gitkeep) | Root source-summary pages for project-wide raw documentation and source families. |
| [domain/](./domain/.gitkeep) | Variable domain categories for concepts that apply across projects or municipalities. |
| [platform/](./platform/.gitkeep) | Durable notes about tools, runtime constraints, QGIS/PostGIS behavior, environment quirks, and ingestion issues. |
| [implementation/](./implementation/.gitkeep) | Durable notes about extraction workflows, schema decisions, packing constraints, scripts, and repeatable technical patterns. |
| [charlottetown/](./charlottetown/README.md) | Active Charlottetown zoning wiki for current and draft zoning extraction, validation, comparison, and GIS preparation. |

Domain subdirectories may be added when there is enough durable content to justify them. Use plural, lowercase, hyphenated names.

## Page Conventions

Every substantive wiki page must use this frontmatter:

```yaml
---
type: source|domain|platform|implementation|project|query|lint|index|log|schema
tags:
  - example-tag
updated: YYYY-MM-DD
---
```

Every substantive page must begin with a one-sentence purpose line immediately after the frontmatter.

Every substantive page must end with a `## Sources` section. Use relative markdown links only, for example `[Root index](./index.md)`. Do not use Obsidian-specific wiki link syntax.

Keep pages near 300 lines or fewer. Split a page when it becomes hard to scan, contains multiple separable topics, or exceeds the line target.

Use repository-relative source references in citations when linking directly is impractical. Prefer the most specific locator available, including PDF page, visible source page, clause label, zone code, file path, schema object, table, map layer, or commit context.

## Link Rules

Use relative markdown links exclusively:

```markdown
[Charlottetown wiki](./charlottetown/README.md)
[Root log](./log.md)
```

Do not use Obsidian-specific wiki links, absolute web URLs for internal wiki pages, or local file URI links.

## Core Workflows

### Ingest

Use ingest when a raw source or durable source-derived finding should become wiki knowledge.

1. Read the raw source and the relevant existing wiki pages.
2. Identify the durable takeaways, unresolved questions, contradictions, and affected terms.
3. Discuss material takeaways when interpretation is uncertain or when source patterns differ from existing wiki assumptions.
4. Create or update the source summary page under [sources/](./sources/.gitkeep) or the relevant project source area.
5. Propagate changes across 5 to 15 related pages when the source changes concepts, workflows, definitions, entities, comparisons, or project status.
6. Update [index.md](./index.md) for added, renamed, removed, or materially changed pages.
7. Append one entry to [log.md](./log.md).

Stop instead of guessing when the source conflicts with an existing page, lacks a stable locator, or requires an unapproved schema interpretation.

### Query

Use the Map-to-Mine strategy for wiki-backed answers:

1. Map: Read [index.md](./index.md) first to locate relevant page areas.
2. Drill: Read the most relevant pages and cited raw sources.
3. Mine: Synthesize the answer with source-aware caveats and exact unresolved gaps.
4. File back: When the answer is reusable, create or update a query, comparison, domain, implementation, or project page.
5. Record: Update [index.md](./index.md) and append [log.md](./log.md) when durable wiki knowledge changes.

### Lint

Use lint to maintain wiki reliability.

Check for:

- contradictions between pages
- contradictions between wiki pages and cited raw sources
- orphan pages not linked from an index
- index entries pointing to missing pages
- stale pages with older `updated` dates than the source facts they summarize
- missing frontmatter
- missing one-sentence purpose lines
- missing `## Sources` sections
- overlong pages that should be split
- non-relative links or Obsidian-specific links

Record durable lint findings in a lint page only when the result is useful beyond the current chat. Always append [log.md](./log.md) for substantive lint passes.

## High-Value Targets

These existing project files are high-value wiki integration targets that are not yet fully integrated at the root wiki layer:

| Target | Why it matters |
| --- | --- |
| [Repository architecture](../docs/architecture.md) | Project-wide system context for extraction, data layout, and workflows. |
| [Local GIS requirements](../docs/requirements-local-gis.md) | GIS setup and workflow constraints relevant to QGIS/PostGIS use. |
| [Normalized land-use standard](../docs/normalized-land-use-standard.md) | Shared vocabulary and normalization rules across zoning extraction work. |
| [Charlottetown current zoning bylaw](../docs/charlottetown/charlottetown-zoning-bylaw.pdf) | Active source for current Charlottetown zoning extraction. |
| [Charlottetown draft zoning bylaw](../docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf) | Active source for draft zoning extraction and comparison. |
| [Charlottetown current zoning codes and map legend](../docs/charlottetown/current-zoning-codes-and-map-legend.md) | Current zoning code and legend context for map and parcel comparison. |
| [Code table candidate discovery workflow](../docs/charlottetown/code-table-candidate-discovery-workflow.md) | Existing workflow notes relevant to repeatable extraction and QA. |
| [Charlottetown Official Plan 2026](../docs/charlottetown/ocp/Charlottetown%20Official%20Plan%202026.pdf) | Planning-policy source for future land use and zoning comparison context. |
| [Future Land Use Map](../docs/charlottetown/ocp/Future%20Land%20Use%20Map%20-%20October%2024%202025.pdf) | Spatial policy context for parcel and neighbourhood comparison. |
| [Charlottetown draft zoning timeline](../plan/chalottetown-draft-zoning-timeline.md) | Active validation status and phase tracking for the draft workstream. |
| [Charlottetown draft zoning plan](../plan/chalottetown-draft-zoning-plan.md) | Planning and execution context for draft zoning extraction. |
| [Current zoning extraction README](../data/zoning/charlottetown/README.md) | Output context for current zoning data. |
| [Draft zoning extraction README](../data/zoning/charlottetown-draft/README.md) | Output context for draft zoning data. |
| [Charlottetown zoning map](../maps/Charlottetown%20Zoning%20Map%20-%20March%209,%202026.pdf) | Current map source for spatial validation and parcel comparison. |
| [Charlottetown street map](../maps/FINAL%20City%20of%20Charlottetown%20Street%20Map%20A1%20Landscape.pdf) | Street reference source for later neighbourhood and parcel analysis. |

## Sources

- [Charlottetown wiki guide](./charlottetown/README.md)
- [Charlottetown wiki index](./charlottetown/index.md)
- [Repository instructions](../AGENTS.md)

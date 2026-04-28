- The first role for every new task is `Project Management`.
- Before acting in a role, read the corresponding role skill:
  - `Project Management`: `.codex/skills/role-project-management/SKILL.md`
  - `Business Analyst`: `.codex/skills/role-business-analyst/SKILL.md`
  - `Coding Architect`: `.codex/skills/role-coding-architect/SKILL.md`
  - `Data Engineer`: `.codex/skills/role-data-engineer/SKILL.md`
  - `GIS Specialist`: `.codex/skills/role-gis-specialist/SKILL.md`
  - `Data Quality Analyst`: `.codex/skills/role-data-quality-analyst/SKILL.md`
  - `Debugger`: `.codex/skills/role-debugger/SKILL.md`
  - `QA Reviewer`: `.codex/skills/role-qa-reviewer/SKILL.md`
- Do not begin coding or bulk data generation until `Project Management` has
  classified the task and identified the next role.
- Do not transition from `Business Analyst` to implementation until the
  requirements, scenarios, and edge cases are explicit enough to code safely.
- Do not transition from `Coding Architect` to implementation until the design
  is shown to be viable for this repository's memory, packing, and runtime
  constraints.
- Do not transition from `Debugger` to implementation until the failure has
  been reduced to observed facts plus a discriminating cause, unless the user
  explicitly approves a hypothesis-driven fix.
- If a task would introduce a new abstraction, helper module, protocol,
  workflow change, or architectural refactor that the user did not explicitly
  request, obtain approval before implementation.
- Implementation is a protocol, not a role skill. During implementation:
  - execute only the approved objective, files, identifiers, schemas, data
    paths, or deployment targets
  - inspect relevant source files, scripts, schemas, generated artifacts, and
    specifications before editing
  - prefer existing repository patterns, scripts, schemas, and workflows
  - apply the smallest concrete change that satisfies the approved requirement
  - do not introduce new abstractions, helper modules, protocols, schema
    shapes, or workflow changes unless explicitly approved
  - do not widen targeted edits beyond named files, rows, codes, clauses,
    categories, terms, or fields
  - do not preserve legacy compatibility fields unless the user explicitly
    requested compatibility preservation
  - for bulk generation, stop on material source-pattern mismatch unless a
    review-output strategy was approved
  - for structured data, edit by keyed object or schema-aware tooling where
    practical instead of broad text replacement
  - route to `Project Management` if scope, deliverables, affected artifact
    classes, roadmap, or priority changes appear
  - route to `Business Analyst` if requirements, scenarios, accepted
    variations, compatibility expectations, or data-standard interpretations
    are not explicit enough to execute safely
  - route to `Coding Architect` if execution requires unapproved design,
    schema, workflow, protocol, or architectural decisions
  - route to `Debugger` if an error, failed output, unexpected runtime
    behavior, suspected extraction defect, or integration blocker lacks a
    discriminating cause
- After any implementation task, finish in `QA Reviewer`.
- When asked to prepare a prompt for a new conversation, do not include
  instructions that already appear in `AGENTS.md` or role skill `SKILL.md`
  files. Reference those files instead of restating their contents.
- When parsing by-law zones or clauses, preserve each raw clause label exactly
  as written in the source.
- For clause hierarchy normalization, the currently approved interpretation is
  hierarchical addressing such as  `20(1)(a.1)` -> `20 -> 1 -> a.1`,
  `21(e)` -> `21 -> e`, `21(ea)` -> `21 -> ea`, and `21(ea)(1)` -> `21 -> ea -> 1`.
- Treat alphabetic, numeric, roman-numeral, decimal, and compact alphanumeric
  labels as single label units when they contain no whitespace and follow an
  incrementing sequence pattern. Examples include `a`, `1`, `i`, `1.1`, `ba`,
  `c1`, `2a`, `5.1`, and `24A1`.
- Preserve each unit as one hierarchy segment. Do not split compact amendment
  labels such as `aa`, `ea`, `ba`, `c1`, `2a`, `24A1`, or `34B38` into
  character-level segments.
- For section-level labels only, compact whitespace may be stripped when the
  source uses spacing inside a single amendment label, such as `24 A3` ->
  `24A3`. Do not apply this whitespace compaction to clause labels.
- Repealed section or clause labels remain part of the sequence and should be
  retained with a repealed status when the source provides that tag or related
  amendment dates.
- Flag an identified section or clause label for review when it does not follow
  the preceding and following label pattern and does not clearly start a new
  sub-pattern.
- Current task context: the active workstream is the City of Charlottetown
  current and draft zoning bylaw extraction, including associated zoning maps,
  parcel layer, and street map. Use source material under `docs/charlottetown`
  and write current zoning bylaw extraction outputs under
  `data/zoning/charlottetown` and draft zoning bylaw extraction outputs under
  `data/zoning/charlottetown-draft` unless the task explicitly names another
  destination.
- Current task purpose: enable parcel and neighbourhood comparison between
  current and draft Charlottetown zoning, with outputs suitable for later
  PostGIS/QGIS use and a future public web front end.
- For substantive Charlottetown extraction, validation, comparison, GIS, QA,
  or planning work, maintain `wiki/charlottetown` when the work creates or
  changes durable knowledge. Follow `wiki/charlottetown/README.md`, update
  `wiki/charlottetown/index.md` for added or materially changed wiki pages,
  and append `wiki/charlottetown/log.md` in the same change. Do not add wiki
  entries for purely mechanical edits, failed experiments, or transient
  command output unless they affect durable project knowledge.
- For the Charlottetown draft zoning validation workstream, keep
  `plan/chalottetown-draft-zoning-timeline.md` up to date until the plan is
  complete. Update its active phase, overall status, current progress, and
  phase statuses whenever work advances, pauses, is blocked, or completes.

## Wiki Maintenance

Keeping the wiki current is part of doing work on this project — see [wiki/README.md](wiki/README.md) for the full schema and ingest/query/lint workflows. In brief:

- **Ingest new source files as needed.** When a task reads a raw source not yet reflected in the wiki, update `wiki/sources/` and propagate to the pages it informs.
- **Record new lessons learned.** Platform quirks, DCC gotchas, memory/packing constraints, timing findings → the relevant `wiki/platform/` or `wiki/implementation/` page.
- **Record new plans and decisions.** Capture the decision AND its rationale (especially GDD "Option A vs B" resolutions, scope changes, workflow shifts).
- **Update the index.** Any new page must be linked from [wiki/index.md](wiki/index.md).
- **Append to the log.** Every ingest, substantive query, or lint pass gets a dated line in [wiki/log.md](wiki/log.md).
- **Prefer updating over creating.** Before adding a page, check whether the concept already has one.

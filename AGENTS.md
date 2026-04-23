- The first role for every new task is `Project Management`.
- Before acting in a role, read the corresponding role skill:
  - `Project Management`: `.codex/skills/role-project-management/SKILL.md`
  - `Business Analyst`: `.codex/skills/role-business-analyst/SKILL.md`
  - `Coding Architect`: `.codex/skills/role-coding-architect/SKILL.md`
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

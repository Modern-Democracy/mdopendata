- The first role for every new task is `Project Management`.
- In that role, first determine:
  1. the task objective
  2. the scope boundaries
  3. the affected code, docs, scripts, and workflow artifacts
  4. the most appropriate next role
- Do not begin coding until the task has been classified and the next role has
  been identified.
- Route to `Business Analyst` when the task is ambiguous, requirement-heavy,
  behavior-changing, or likely to depend on edge-case clarification.
- Route to `Coding Architect` when the task involves module boundaries, memory
  pressure, runtime ownership, packing implications, protocol changes, or new
  technical patterns.
- Route to `Debugger` when the task begins from a reported error, unexpected
  runtime behavior, failed output, or an unverified regression.
- Route directly to implementation only when the requested code change is
  narrow, already approved, and sufficiently specified.
- Route to `QA Reviewer` when the task is primarily about verification, review,
  regression checking, acceptance, or completion readiness.
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

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
  hierarchical addressing such as `21(e)` -> `21 -> e`, `21(ea)` -> `21 -> e ->
  a`, and `21(ea)(1)` -> `21 -> e -> a -> 1`.
- Do not apply hierarchy normalization to a clause syntax pattern that has not
  already been explicitly reviewed in this repository context.
- If a new clause syntax appears, stop and surface the exact raw examples for
  review before normalizing them. Examples already identified for review
  include dotted subclauses like `20(1)(a.1)` and alphanumeric section-style
  identifiers like `34B38`.

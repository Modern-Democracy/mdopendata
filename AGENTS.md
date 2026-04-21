- The first role for every new task is `Project Management`.
- In that role, first determine:
  1. the task objective
  2. the scope boundaries
  3. the affected code, docs, scripts, and workflow artifacts
  4. whether the request contains grey areas, implied choices, or
     bulk-pattern variation risk
  5. the most appropriate next role
- Do not begin coding or bulk data generation until the task has been
  classified and the next role has been identified.
- If the task contains grey areas, stop and ask the user for clarification
  before implementation. Grey areas include:
  - preserving compatibility fields, legacy schemas, or existing output
    structures not explicitly requested
  - adding new abstractions, helper scripts, normalization layers, or workflow
    changes not explicitly requested
  - deciding how to handle source content that does not fit a provided template
  - making assumptions that affect document structure, data schema, field
    naming, normalization semantics, or downstream imports
  - applying one example template across multiple sections, zones, appendices,
    tables, or document types where source patterns vary materially
- For bulk template-adaptation tasks:
  - Apply the template directly only where the source pattern is clearly
    equivalent.
  - For light variation, make a conservative best-effort adaptation and flag
    the variation in the output or final report.
  - For material variation, stop before bulk generation and report:
    1. the source section or zone
    2. the raw text or structural feature causing the mismatch
    3. why the provided template does not fit cleanly
    4. the minimum template change or decision needed
  - Do not force a template onto content that is structurally different.
  - Do not preserve legacy top-level fields, importer compatibility fields, or
    old schema shapes unless the user explicitly asks for compatibility
    preservation.
- Route to `Business Analyst` when the task is ambiguous, requirement-heavy,
  behavior-changing, likely to depend on edge-case clarification, or contains
  unresolved template-fit, schema, compatibility, or acceptable-variation
  questions.
- Route to `Coding Architect` when the task involves module boundaries, memory
  pressure, runtime ownership, packing implications, protocol changes, or new
  technical patterns, and only after template-fit policy and compatibility
  requirements are explicit enough to design safely.
- Route to `Debugger` when the task begins from a reported error, unexpected
  runtime behavior, failed output, or an unverified regression.
- Route directly to implementation only when the requested code change is
  narrow, already approved, and sufficiently specified.
- Route to `QA Reviewer` when the task is primarily about verification, review,
  regression checking, acceptance, or completion readiness.
- In `QA Reviewer`, start by restating the specific failure mode or acceptance
  claim that must be verified. Identify the observable symptom, the expected
  invariant, and the smallest evidence that can distinguish success from
  failure.
- In `QA Reviewer`, do not accept proxy checks when the user has identified a
  more specific failure. A check is insufficient if it can pass while the
  reported problem remains present. State why the check is discriminating before
  relying on it.
- In `QA Reviewer`, validate at the earliest reliable source level. Prefer raw
  source data, protocol messages, parser inputs, database records, or canonical
  control features over derived outputs when derived outputs may add noise,
  clipping, aggregation, caching, polygonization, formatting, or rendering
  artifacts.
- In `QA Reviewer`, when two outputs should agree, identify stable common
  features that should be identical or near-identical, exclude known noisy or
  intentionally different regions, and measure direct correspondence between
  those features. Use aggregate extents, counts, centroids, or visual inspection
  only as supporting evidence unless they directly test the claimed invariant.
- In `QA Reviewer`, if a fix changes alignment, scale, ordering, identity,
  matching, or equivalence, verify the result with matched controls distributed
  across the full relevant domain. Report both the number of matched controls
  and residual error statistics.
- In `QA Reviewer`, before recommending or accepting a corrective transform,
  migration, normalization, or data repair, test whether the apparent problem is
  caused by the source, an intermediate transform, or a later derived artifact.
  Do not tune a downstream artifact until the upstream representation has been
  checked.
- In `QA Reviewer`, prefer falsifiable thresholds tied to the task over vague
  pass/fail statements. Examples include overlap ratios, residual distances,
  unmatched counts, schema violations, round-trip differences, or exact
  equality counts, depending on the domain.
- If QA reveals that the current troubleshooting approach is not discriminating
  the failure, transition back to `Debugger` with the observed facts and the
  missing discriminating test. Do not continue iterating on fixes using the same
  insufficient evidence.
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

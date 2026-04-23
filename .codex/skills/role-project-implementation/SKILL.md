---
name: role-project-implementation
description: Use after Project Management, Business Analyst, Coding Architect, or Debugger has approved implementation and the task requires executing a narrow technical change, data generation step, deployment step, integration step, or standardized schema/data update within defined constraints.
metadata:
  short-description: Execute approved technical work
---

# Project Implementation

Use this role only after the objective, scope, affected artifacts, requirements, and design constraints are explicit enough to execute.

## Objective

Execute approved project plans to deliver technical changes, standardized data schemas, generated data, integration work, or deployment steps within the defined constraints.

## Entry Gate

Before implementation, confirm:
1. `Project Management` classified the task and routed to implementation or a prerequisite role.
2. Any required `Business Analyst`, `Coding Architect`, or `Debugger` gate is complete.
3. The allowed files, data paths, identifiers, schemas, or deployment targets are explicit.
4. The acceptance checks and stop conditions are known.

Do not implement when scope, schema, compatibility, source-pattern handling, or failure cause is still unresolved.

## Workflow

1. Restate the approved implementation objective and allowed change surface.
2. Inspect the relevant files, generated artifacts, schemas, scripts, or deployment specifications before editing.
3. Prefer existing repository patterns, scripts, schemas, and workflows.
4. Translate the approved plan into the smallest concrete work units needed to complete the task.
5. Apply changes only inside the approved scope.
6. Run the discriminating checks defined by the prior role, or the smallest checks that prove the implementation meets the accepted requirements.
7. Record what changed, what was verified, and any remaining constraints for `QA Reviewer`.

## Execution Rules

- Do not introduce new abstractions, helper modules, protocols, schema shapes, or workflow changes unless explicitly approved.
- Do not widen targeted edits beyond named files, rows, codes, clauses, categories, terms, or fields.
- Do not preserve legacy compatibility fields unless the user explicitly asked for compatibility preservation.
- For bulk generation, stop on material source-pattern mismatch unless the prior role approved a review-output strategy.
- For structured data, edit by keyed object or schema-aware tooling where practical instead of broad text replacement.
- For deployment or environment work, follow specification documents and record commands, targets, and observable outcomes.
- For integration blockers, reduce the blocker to observed facts before patching; route to `Debugger` if the cause is not discriminating.

## Redirection

Route to `Project Management` when scope changes, new deliverables, new affected artifact classes, roadmap changes, or priority conflicts appear during execution.

Route to `Business Analyst` when requirements, scenarios, accepted variations, compatibility expectations, or data-standard interpretations are not explicit enough to execute safely.

Route to `Coding Architect` when implementation would require a new abstraction, helper module, protocol, schema design, workflow design, or architectural refactor that was not already approved.

Route to `Debugger` when an error, failed output, unexpected runtime behavior, suspected extraction defect, or integration blocker lacks a discriminating cause.

Route to `QA Reviewer` after implementation is complete, with the exact change surface and verification evidence.

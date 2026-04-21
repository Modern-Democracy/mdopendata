---
name: role-project-management
description: Use for the first step of every project task in this repository to classify objective, scope, affected artifacts, ambiguity, bulk-pattern variation risk, and next role before implementation.
metadata:
  short-description: Classify tasks and gate ambiguity
---

# Project Management

Use this role before any coding, file generation, bulk extraction, or verification work.

## Required Classification

Determine:
1. the task objective
2. the scope boundaries
3. the affected code, docs, scripts, data, schema, and workflow artifacts
4. whether the request contains grey areas, implied choices, or bulk-pattern variation risk
5. the most appropriate next role

Do not begin coding or bulk data generation until the task has been classified and the next role has been identified.

## Clarification Gate

If the task contains grey areas, stop and ask the user for clarification before implementation.

Grey areas include:
- preserving compatibility fields, legacy schemas, or existing output structures not explicitly requested
- adding new abstractions, helper scripts, normalization layers, or workflow changes not explicitly requested
- deciding how to handle source content that does not fit a provided template
- making assumptions that affect document structure, data schema, field naming, normalization semantics, or downstream imports
- applying one example template across multiple sections, zones, appendices, tables, or document types where source patterns vary materially

## Bulk Template Adaptation

For bulk template-adaptation tasks:
- Apply the template directly only where the source pattern is clearly equivalent.
- For light variation, make a conservative best-effort adaptation and flag the variation in the output or final report.
- For material variation, stop before bulk generation and report:
  1. the source section or zone
  2. the raw text or structural feature causing the mismatch
  3. why the provided template does not fit cleanly
  4. the minimum template change or decision needed
- Do not force a template onto content that is structurally different.
- Do not preserve legacy top-level fields, importer compatibility fields, or old schema shapes unless the user explicitly asks for compatibility preservation.

## Routing

Route to `Business Analyst` when the task is ambiguous, requirement-heavy, behavior-changing, likely to depend on edge-case clarification, or contains unresolved template-fit, schema, compatibility, or acceptable-variation questions.

Route to `Coding Architect` when the task involves module boundaries, memory pressure, runtime ownership, packing implications, protocol changes, or new technical patterns, and only after template-fit policy and compatibility requirements are explicit enough to design safely.

Route to `Debugger` when the task begins from a reported error, unexpected runtime behavior, failed output, or an unverified regression.

Route directly to implementation only when the requested code change is narrow, already approved, and sufficiently specified.

Route to `QA Reviewer` when the task is primarily about verification, review, regression checking, acceptance, or completion readiness.


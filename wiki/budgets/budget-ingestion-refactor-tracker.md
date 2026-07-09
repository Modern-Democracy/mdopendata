---
type: implementation
tags:
  - budget
  - refactor
  - extraction
  - normalization
updated: 2026-07-09
---

This page tracks deferred refactor lessons from Charlottetown budget ingestion so reusable pipeline work starts after the 2025/2026 and 2024/2025 normalization imports are complete.

# Budget Ingestion Refactor Tracker

## Status

The refactor is deferred. The current priority is completing normalized review, import, and QA for the 2025/2026 and 2024/2025 Charlottetown budget documents to the same level reached by 2026/2027.

This page should be updated while those two prior-year documents are normalized. The purpose is to preserve lessons that would otherwise be lost if the code were generalized before the prior-year edge cases are fully understood.

## Refactor Goal

Separate the budget ingestion code into:

- reusable pipeline code that can apply across materially equivalent municipal budget documents
- municipality-specific configuration, such as Charlottetown entity and fiscal-period definitions
- document-specific review artifacts, such as section groupings, continuation decisions, project aliases, tax/rate operands, debt identities, exceptions, and compatibility decisions

The first refactor target should not claim universal document support. It should provide a repeatable framework that stops on material variation and emits review records.

## Deferral Rationale

The 2026/2027 workflow proved the database model, raw extraction layer, normalized manifest shape, import gates, and QA gates. It did not prove that the 2026/2027 normalization code can safely become the general rule.

The 2025/2026 and 2024/2025 documents already show useful variation:

- different page counts and table counts
- different prior-period labels and shorthand year labels
- different continuation structure
- capital schedules and profiles that need cross-year alias review
- tax/rate and debt sections that require document-specific operand and identity checks
- smaller 2024/2025 source scope with no separate tax/rate and debt table-family coverage in the current review artifact

## Current Code Separation Observations

| Area | Current state | Refactor direction |
| --- | --- | --- |
| PDF profiling | Scripted and mostly reusable, but Charlottetown-named and family heuristics are embedded. `extract-charlottetown-budget-first-pass.py` now accepts `--municipality-key` and derives the fiscal-period stem for raw table IDs. | Promote to configurable budget PDF profiler with municipality/document metadata inputs. |
| Raw rows and values | `extract-charlottetown-budget-raw-rows.py` already accepts manifest, raw page, and output paths. | Extract shared parser functions for rows, values, aligned-column recovery, value states, and summaries. |
| Raw coverage repair | `resolve-budget-week5-raw-coverage-blockers.py` is Charlottetown-specific but now generates supplemental table IDs from `--municipality-key` and each document key, instead of reusing the 2026/2027 stem. | Fold this behavior into reusable raw coverage tooling with source metadata inputs and explicit review provenance. |
| Raw database sync | Current sync scripts are tied to document directories and importer versions. | Parameterize document key, municipality key, source hash, source metadata, manifest path, and raw version. |
| Normalization artifacts | `build-budget-2026-normalization-artifacts.py` is strongly document-specific. | Keep semantic mappings as document review artifacts and use shared builders only after template fit is proven. |
| Manifest generation | `build-budget-2026-normalized-manifest.py` has reusable shape but hard-coded periods, counts, aliases, and source hash. | Convert to manifest builder driven by approved document mapping packages. |
| Reconciliation | Reconciliation code mixes generic formulas with 2026/2027 named checks. | Separate formula engine and tolerance handling from document-specific check catalogue. |
| Importer | `import-budget-2026-normalized-full.py` has reusable transactional import mechanics but hard-coded counts and document metadata. | Convert to a manifest-driven importer with document-independent validation and explicit expected-count input. |
| QA | QA scripts prove source fidelity but assert 2026/2027 constants. | Convert to family-stratified QA that reads expected controls from each approved manifest and review package. |

## Reusable Components To Preserve

- raw source preservation before normalization
- stable document, table, row, cell, line, fact, and source-link identities
- aligned financial-column value recovery with negative controls for narrative numbers
- deterministic manifest hashing and expected-count reports
- dry-run import plans
- transactional import with idempotence checks
- content-conflict failure instead of silent overwrite
- source-cell provenance validation
- publication snapshot prohibition during normalization import
- reconciliation catalogue and review-issue gate
- family-stratified QA before completion

## Document-Specific Inputs To Isolate

- municipality key used in raw IDs, such as `ctown`, and the authoritative municipality record it maps to
- source document metadata, PDF path, SHA-256 hash, page count, document kind, and title
- fiscal-period source labels, fiscal dates, and amount-type roles
- page ranges, section keys, and section titles
- table-family template-fit decisions
- continuation group membership
- duplicate summary and non-financial dispositions
- reporting-entity and organization-unit assignments
- row semantics, hierarchy, aggregation roles, and value states when not directly inferable
- capital project aliases and profile-to-schedule links
- debt instrument identities and maturity treatment
- tax/rate operand roles and formula treatment
- cross-document compatibility and restatement decisions
- approved reconciliation exceptions and publication effects

## Lessons To Capture During Prior-Year Completion

| Lesson area | Evidence to add while working |
| --- | --- |
| Raw identity contract | Confirm every generated table, row, and value ID uses `<municipality_key>_budget_<fiscal_period_slug>` and that prior-year artifacts do not reuse the 2026/2027 stem. |
| Continuation review | Which section grouping rules repeated from 2026/2027 and which changed. |
| Fiscal periods | Exact raw labels that map to fiscal periods and amount types. |
| Capital aliases | Cross-year project labels that map cleanly, split, merge, or remain unmatched. |
| Profiles without schedules | Whether unmatched profiles indicate source omissions, changed labels, or non-comparable projects. |
| Tax/rate formulas | Which operands are present, implicit, missing, or differently expressed. |
| Debt schedules | Whether debt identities can be matched by label, maturity, balance, or other source evidence. |
| Facility statements | Whether Civic Centre, Bell Aliant, or other facility layouts match the 2026/2027 mappers. |
| Expected-count controls | Which counts should be generated from mappings rather than hard-coded in scripts. |
| QA controls | Which positive and negative controls are document-independent versus document-specific. |

## Initial Refactor Acceptance Criteria

- A new budget document can be profiled and raw-ingested without editing Python source code.
- Normalization cannot proceed without an approved document mapping package.
- The reusable builder refuses unknown table families, unmapped fiscal labels, missing source links, and unsupported value states.
- Document-specific review records can coexist with reusable code without page-specific branches in shared modules.
- Import and QA scripts accept manifest paths and expected-count artifacts instead of hard-coded 2026/2027 constants.
- Cross-document compatibility records are produced only from approved alias, period, and semantic mappings.
- The first refactor is tested against Charlottetown 2026/2027, 2025/2026, 2024/2025, and at least one non-Charlottetown budget document before being treated as a reusable workflow.

## Deferred Work Items

| Item | Status | Notes |
| --- | --- | --- |
| Audit remaining hardcoded budget identifiers | Started | Current scan found expected 2026/2027 constants in document-specific normalization, reconciliation, validation, and test scripts; reusable raw artifact generation has been parameterized for municipality key and fiscal period. |
| Define document mapping package schema | Deferred | Should wait for prior-year mapping artifacts. |
| Extract raw parser module | Deferred | Low risk, but prior-year raw coverage should finish first. |
| Convert manifest builder to config input | Deferred | Needs 25/26 and 24/25 manifest lessons. |
| Convert importer to manifest-driven CLI | Deferred | Depends on final expected-count and coexistence behavior. |
| Convert QA scripts to document-agnostic controls | Deferred | Needs prior-year source-fidelity patterns. |
| Test with other municipalities | Deferred | Explicitly after Charlottetown three-year completion. |

## Sources

- [Document extraction engineering](../implementation/document-extraction-engineering.md)
- [Budget implementation and test plan](./implementation-plan.md)
- [2026/2027 normalization status](./2026-normalization-status.md)
- [Week 5 raw ingestion status](./week-5-raw-ingestion-status.md)
- [Week 5 normalized mapping review](./week-5-normalized-mapping-review.md)
- [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md)
- `scripts/extract-charlottetown-budget-raw-rows.py`
- `scripts/build-budget-2026-normalization-artifacts.py`
- `scripts/build-budget-2026-normalized-manifest.py`
- `scripts/import-budget-2026-normalized-full.py`
- `scripts/verify-budget-2026-phase-7-qa.py`

---
type: log
tags:
  - wiki
  - log
updated: 2026-07-28
---

This page is the append-only chronological record for root wiki changes, ingests, substantive queries, and lint passes.

Append new entries in reverse chronological order. Use this heading format:

```text
## [YYYY-MM-DD] type | Short title
```

## [2026-07-28] operations | Local council-import web refresh

Rebuilt `mdopendata-web:latest` from the committed council agenda-package import implementation and force-recreated only the local web container. The running image is `sha256:5c1e625acb825f0203c3b4af4ee1b88159546b53ea657f9e531312434df0cb0f`; embedded server and ingestion UI hashes match the workspace exactly. Local health returned `ok`, the council-import preview returned the explicit `meeting-required` gate with five documents, and the existing PostGIS and pgAdmin containers were not recreated.

## [2026-07-28] platform | Supabase demo row-level security

Added and deployed migration 032 to enable row-level security on all 145 ordinary tables in the remote `public`, `zoning`, `budget`, `council`, and `help` demo schemas. No client policies are created, so Supabase anonymous and authenticated access is denied by default while the server-side Render database owner connection retains read access. Supabase Advisor reported no remaining issues, Render health returned HTTP 200, and 35 read-only smoke checks passed; the separate packaged source-page check for budget source 9 remains HTTP 404.

## [2026-07-28] implementation | Council agenda-package binding and import

Implemented and live-verified the post-extraction council-domain handoff. A completed package now requires an explicit existing same-jurisdiction meeting and exact meeting-scoped agenda-item keys before one transaction imports its source and package-document records. The agenda remains unbound; all four supporting documents bind to the exact agenda item and inherit only its business-item relationship. The six-page control imported five documents at ranges `1`, `2`, `3`, `4`, and `5-6`; a missing-key control returned `409` with zero writes, and an unchanged rerun preserved all active IDs. Permanent council rows were fingerprint-identical before and after ephemeral verification.

## [2026-07-28] implementation | Agenda-package reuse-preview assembly handoff

Implemented and live-verified the explicit approved agenda-package reuse-preview handoff. Complete, conflict-free, non-material previews can now bind structural page roles to accepted active positive-control extraction templates, supersede page classifications with reviewer-accepted profile evidence, and create an editable draft assembly transactionally. The ephemeral positive control produced six classifications and five draft documents, reran without writes, and was removed completely. Approved assemblies, blocked previews, missing or inconsistent templates, extraction, council import, publication, and permanent control rows remained protected.

## [2026-07-27] implementation | Charlottetown agenda-package reuse profile

Completed the Phase 6 real-package profile gate from source document 2, the reviewed six-page February 3 public-meeting package. Promoted five immutable same-edition structural templates and five `review_required` policies covering four single-page documents and one two-page mailed notice and map. The positive preview assigns all six pages exactly once to five exact matches with zero unknown, conflicting, or omitted pages. The stored nearest-negative slice from unreviewed source document 3 remains wholly unknown and blocked; live endpoint verification against all 453 pages likewise returns zero documents, 453 unknown pages, zero conflicts, and zero omissions. Transactionally backfilled `metadata.source_family = charlottetown-council` for exact source-document IDs 2 and 3; repeat generation reports zero pending rows and byte-identical outputs. No classifications, assemblies, extraction results, source files, or publication state changed.

## [2026-07-27] implementation | Version 2 active-workspace handoff

Approved and completed the Phase 7 transition after full structural, observation-set, and live Snapshot 3 parity. The loopback reviewer and launcher now default to version 2; explicit schema version 1 selection remains the frozen rollback. The final 858-record parity report has 753 matches, one approved migration event, 104 approved provenance shifts, zero missing or changed records, zero blockers, and `passed: true` at SHA-256 `526ad87dbb9b2ddf91c33c5b83f6b8e47ae4e20c9351050e9cf83d5f731e733b`. Version 2 Stage 2 groups and 2,290 observations are the approved downstream structural-extraction inputs. Database, publication, deployment, dependency, and version 1 artifacts remain unchanged.

## [2026-07-16] implementation | Cross-page content association workflow

Repaired the source-first Stage 1 association workflow for same-page chart sources and cross-page table continuations and overview-detail links. Association state now records and displays the source page and label, persists across page navigation, validates relationship-specific source and target roles, supports explicit cancellation, and remains selected after a failed write. Overview row selection resolves to its typed row-label cell; semantic validation requires whole chart/table endpoints, cross-page whole tables for continuations, and row-label-to-different-detail-table endpoints.

## [2026-07-16] implementation | Incremental Stage 1 review writes

Removed duplicate full-artifact validation and client reinitialization from routine Stage 1 edits. The writer now validates affected component schemas plus complete semantic and cross-artifact invariants, returns affected page numbers, and preserves full canonical validation for startup, tests, explicit checks, and handoff. The server refreshes its trusted cache after an atomic write and returns updated page payloads for in-place browser patching; the global save lock remains unchanged. A representative temporary-workspace resize completed in 0.338 seconds.

## [2026-07-16] implementation | Spreadsheet table-grid editing

Replaced table cell-region overlays with complete spreadsheet grids for all 77 Charlottetown pilot tables. Added draggable dividers, Cell/Row/Column selection modes, contiguous Shift selection, cell typing, deterministic row and column split or merge, resize redetection, schema validation, and append-only migration decision 39. Split operations duplicate source types; merge operations retain a type only when every source matches and otherwise reset the result to `cell`.

## [2026-07-15] implementation | Automatic table-region detection

Added deterministic Stage 1 table-region proposals from Stage 0 word geometry. The generator and reviewed writer now detect table headers, column labels, row labels, numeric cells, subtotals, and totals. The local reviewer can replace a table's internal regions explicitly or atomically while resizing its outer box; all replacement regions remain `needs_review`. Added generator, writer, schema, smoke, and UI regression coverage.

## [2026-07-15] implementation | Stage 1 taxonomy, internal regions, and relationships

Reverted the staged PDF reviewer to loopback-only operation, removed the iPad firewall rule, and deferred installer-managed LAN access plus phone/tablet support. Replaced the candidate vocabulary with the reviewed ordered block types, regenerated the 440-block pilot with 143 titles and 709 formatted-text internal regions, added table/text internal edit contracts, and added graph-source, cross-page-table, and overview-detail relationships.

## [2026-07-15] implementation | Editable Stage 1 PDF inventory review

Added schema-validated Stage 1 block creation, resize handles, reclassification, financial-candidate editing, deletion, and drawing to the local Charlottetown reviewer. Mutations use optimistic artifact hashes, the canonical Python runtime, and append-only review decisions. Verified the Node listener on `0.0.0.0:3217`, the iPad-restricted firewall rule for `192.168.2.43`, and the host neighbour entry; the unresolved iPad timeout now requires an elevated packet-arrival capture during a retry.

## [2026-07-14] operations | Render and Supabase demonstration deployment

Added the approved read-only demonstration deployment surface: Render Docker Blueprint configuration, tracked-data production image, Supabase connection support, health check, demo-mode write barrier, direct migration support, and a local-to-Supabase schema/data bootstrap script. Local ingestion remains outside the remote environment.

## [2026-07-14] operations | Canonical demonstration endpoint routing

Recorded `https://mdopendata-demo.onrender.com` as the canonical user-facing Render demonstration endpoint. Updated the deployment and project-environment pages to distinguish Render demonstration reads from local ingestion writes, and added the same routing rule to the DevOps role skill.

## [2026-07-12] implementation | Budget API pagination, validation, and warnings

Added bounded cursor pagination, strict allowlisted query-filter validation, and accepted debt-balance discrepancy warning coverage to the first budget API slice. Updated the Bruno collection with paginated and filtered requests plus an unknown-filter rejection request, rebuilt the local Docker web service, and passed the expanded API smoke checks.

## [2026-07-12] operations | Local web container rebuild for budget API validation

Rebuilt and recreated the local Docker Compose `web` service from the current `web/server.js` source after the stale image returned `404` for budget API routes. The refreshed service returned `200` for municipalities, periods, sources, fact detail, and CSV download using the Bruno Local environment; `factId` was set to published fact `13067`.

## [2026-07-12] implementation | Prior-year budget normalized imports complete

Completed deterministic manifests, reconciliation catalogues, controlled normalized imports, idempotence reruns, and source-fidelity QA for the 2024/2025 and 2025/2026 Charlottetown budgets. Imported 4,091 facts with 4,091 verified source links and 14 passing reconciliations. Migration 026 restored `budget.capital_project_reference`; 173 approved 2026/2027 references were backfilled, producing 27 project identities referenced by multiple budget documents. Publication snapshots remain zero.

## [2026-07-12] implementation | Prior-year normalization Phase 2 complete

Completed prior-year budget normalization Phase 2 row review. The deterministic artifacts now contain 1,717 approved source-linked facts for 2024/2025 and 2,374 for 2025/2026, with zero unresolved rows. Verified mixed monetary/percentage/count rows and omitted fiscal-period cells against rendered PDF pages; no 2026/2027 data refactor or schema change was required.

## [2026-07-09] fix | Budget raw identity contract

Audited budget scripts for hardcoded `ctown` and `2026_2027` identifier stems. Parameterized raw artifact generation so first-pass extraction and Week 5 supplemental raw coverage use a configurable municipality key with document-derived fiscal-period stems; documented that remaining `ctown_budget_2026_2027` constants are document-specific normalization, reconciliation, validation, and test controls pending the deferred budget ingestion refactor.

## [2026-07-09] implementation | Normalized import Phase 5 dry-run importer

Implemented `normalized-full-1`, a dry-run-capable full normalized importer for the 2026/2027 manifest and reconciliation catalogue. Two consecutive dry runs produced the same plan hash, rolled back successfully, left zero persisted normalized-full batches, and kept publication snapshots at zero. The dry-run plan covers 2,165 facts, 2,165 fact-source links, 161 reconciliations, one review issue, capital/debt links, and profile extension events. Gate 6 is ready for review.

## [2026-07-08] implementation | Append-only budget full-2 raw import

Created a pre-import database dump, dry-ran and applied an append-only `full-2` import containing 114 source tables, 3,233 rows, and 3,092 value cells, and repointed the normalized manifest. PostgreSQL validation resolved all 2,165 fact-source links with zero token or numeric mismatches and zero publication snapshots. Gate 4 is approved; immutable `full-1` records remain unchanged.

## [2026-07-08] implementation | Normalized import Phase 4 reconciliation design

Generated the full-document reconciliation catalogue for the 2026/2027 normalized import manifest. The catalogue contains 161 exact fact-key checks, 160 passes, one source-document discrepancy, zero unresolved inputs, and zero adjacent-block exclusions. Dashes are treated as zero for reconciliation arithmetic, page 110 uses title-scoped city, water/sewer, and combined net checks, Civic Centre/Public Works nested totals use explicit component checks, and page 22 totals reconcile as a continued page 21/22 table. Gate 5 is ready for review; no database writes or publication snapshots were created.

## [2026-07-08] implementation | Normalized import Phase 3 provenance validation

Validated 2,165 fact-source links, 2,165 unique source cells, 253 capital-profile field-row links, and page 87 text-extraction row reconstruction with zero file-level mismatches. Visual PDF review confirmed Snow Removal is one aligned source row; the two extracted rows are a text-order artifact. PostgreSQL resolves every natural key but contains 23 stale raw-cell values from before aligned-column recovery; Gate 4 remains blocked and no database writes were performed.

## [2026-07-08] implementation | Normalized import Gate 3 approval

Applied the approved capital profile decisions: 22 one-to-one links, one profile linked to two intersection projects, and one reviewed Vehicle Equipment narrative-only exception. The regenerated manifest has zero unresolved decisions, zero identity collisions, 1,163 lines, 2,165 facts, and deterministic output. Gate 3 is approved.

## [2026-07-08] implementation | Recovered omitted row-4 capital items

Corrected the capital schedule mapper's row-4 exclusion and recovered six source-backed projects and facts, including New Fire Station Build ($6,000,000) and Police Specialized Equipment ($128,000). Regenerated Phase 2 at 1,163 lines and 2,165 facts. Police detail reconciles exactly to $494,000 with no Vehicle Equipment residual; drafted a City clarification request after confirming official budget approval on March 31, 2026.

## [2026-07-08] query | Capital profile alias review

Reviewed 14 non-exact capital profile mappings against their section-scoped schedule rows and profile descriptions. Proposed ten direct aliases, one composite link to two intersection schedule projects, and three explicit narrative-only exceptions where no defensible schedule row exists. No mappings were applied.

## [2026-07-08] implementation | Capital profile wrapped-field repair

Corrected capital profile extraction to join wrapped title, department, and project rows using explicit field boundaries. Regenerated the profile mapping, deterministic manifest, and section-scoped alias review; no aliases were inferred and Gate 3 remains pending review of 14 non-exact mappings.

## [2026-07-08] implementation | Normalized import Phase 2 review manifest

Recorded Gate 1 and Gate 2 approval and generated a deterministic full-document review manifest with 1,157 lines, 2,159 facts, 2,159 source-value references, and zero identity collisions. Gate 3 remains blocked because 14 of 24 capital profiles require reviewed aliases to capital schedule projects. No SQL or database changes were performed.

## [2026-07-08] implementation | Normalized import Phase 1 evidence

Defined the proposed full-document manifest protocol, deterministic identity rules, entity/unit/fund/family inventories, vocabulary translations, representative-data collision treatment, and Gate 1/2 decisions. No SQL, importer, normalized data, or database records were changed; both gates remain pending explicit approval.

## [2026-07-08] implementation | Normalized import implementation plan

Converted `wiki/budgets/2026-normalized-import-gap-report.md` into a seven-phase implementation plan with eight approval gates. Preserved the audited scope and blockers as scoped work, evidence requirements, pass criteria, dependencies, and stop conditions. Publication remains outside the plan, and publication snapshots must remain at zero.

## [2026-07-08] platform | DevOps role and environment ownership

Added the DevOps role as the exclusive owner of dependency installation, project environment and toolchain mutation, infrastructure, CI/CD, and deployment-target changes. Added an explicit pre-change user approval gate, Project Management routing, and a canonical project-environment wiki page covering `.venv`, the separate QGIS runtime, current deployment surfaces, and documentation requirements.

## [2026-07-08] query | 2026/2027 normalized import gap audit

Audited 28 normalization files containing 1,157 rows, 2,159 facts, and 24 profiles against the PostgreSQL schema and representative importer. Confirmed complete raw-value provenance but identified blocking gaps in manifest identities, controlled vocabularies, amount types, source-cell periods, extension links, reconciliation coverage, importer mode, and representative-data coexistence. No database writes were performed.

## [2026-07-08] implementation | Complete 2026/2027 normalization review

Classified Funding and Taxation page 15 as non-financial narrative, mapped 109 Civic Centre single-period rows, and mapped 52 Bell Aliant departmental rows into 104 two-period facts while excluding variance percentages. All 116 candidates now have final dispositions and the unresolved review report is empty.

## [2026-07-08] implementation | Capital profiles, schedules, and debt normalization

Mapped 13 capital schedules into 216 reviewed rows and 240 facts, structured 24 capital project profiles as narrative-only records, and mapped ten Water and Sewer debt instruments with balance, principal, interest, and maturity metadata. Regeneration leaves three section reviews covering eight candidates.

## [2026-07-08] fix | Charlottetown budget page 87 staggered rows

Verified the rendered page 87 Municipal Buildings labels and values against raw text, source rows, source values, and normalization logic. Preserved raw physical extraction and added an isolated reviewed logical-row reconstruction for the unique five-row staggered chain. Regenerated normalization artifacts; Public Works and Municipal Buildings is approved, leaving 14 section reviews.

## [2026-07-07] budget | Full 2026/2027 raw import and normalization gate

Reconciled 114 first-pass tables with 116 profile candidates, recorded dispositions for every candidate and non-join decisions for all 63 continuation flags, imported 154 pages with 3,233 rows and 2,420 values, and produced coverage, reconciliation, and unresolved-review reports. Full fact normalization remains blocked for 112 candidates pending semantic review; no publication snapshot was created.

## [2026-07-07] budget | Representative normalized mapping design

Defined stable raw and normalized identities for the representative Charlottetown budget spike. Added a reviewed mapping-manifest contract, import order, reconciliation linkage rules, and explicit stop conditions. Normalized import remains blocked until row-level and cell-level assignments are materialized in `normalized-mapping.json`.

## [2026-07-07] budget | Requirements and architecture contracts

Added the municipal budget wiki section with prototype scope, source-aware requirements, a proposed raw-to-normalized PostgreSQL schema, public website/API contracts, and an eight-week implementation and test plan. The contracts use the three Charlottetown budget PDFs as the initial source family and identify representative 2026/2027 operating, capital, tax, facility, and debt layouts as the pre-migration architecture gate.

## [2026-07-07] budget | Three-year source profiling

Added a repeatable discovery profiler and page/table inventories for all 392 pages across the three Charlottetown financial plans. Documented table families, column and fiscal-label patterns, reporting entities, OCR requirements, continuation candidates, material annual variations, and representative tables for the schema spike.

## [2026-07-07] budget | Representative-table schema spike started

Mapped seven representative operating, facility, OCR, capital, tax, and debt source patterns to the proposed budget schema. Recorded confirmed schema fits and blocking gaps for document-period identity, extraction provenance, and multi-fact tax expressions before SQL migrations.

## [2026-07-07] budget | Representative schema gaps resolved

Resolved all five structural gaps found by the representative-table spike. Added source table columns, explicit table-page membership, keyed document periods, OCR extraction provenance, and a many-to-many fact-source evidence model to the proposed budget schema; SQL migrations remain gated on materialized source rows and reconciliations.

## [2026-07-07] budget | Representative rows, cells, and reconciliations

Materialized 408 source rows and 616 source cells across 12 representative pages with stable keys and normalized embedded-text coordinates. Four of seven reconciliation controls passed; the displayed property-tax calculation and two facility earnings dashes remain explicit source-review findings.

## [2026-07-07] budget | Reconciliation review records

Designed three stable review issues for the property-tax arithmetic variance and facility earnings dashes. Added controlled severity, publication effects, allowed decisions, prohibited transformations, evidence links, and append-only decision requirements to the proposed budget schema and spike outputs.

## [2026-07-07] budget | Word-level facility OCR coordinates

Replaced line-only OCR evidence for 2024/2025 facility pages 82-87 with Tesseract word-TSV materialization at 180 DPI. All 221 OCR rows and 442 OCR cells now have normalized bounding boxes and confidence values; the representative spike is ready for a draft SQL migration.

## [2026-07-06] implementation | Page-template classification and unknown detection

Added approved-pattern page classification with required and weighted cues, ambiguous-match handling, rerunnable page classifications, blocking `new_page_template` gaps, package approval-state transitions, classification APIs, and browser template-status badges.

## [2026-07-06] implementation | Agenda package page traversal

Added Poppler-based page counting, PNG rendering, embedded-text extraction, transactional source-page and source-asset persistence, idempotent traversal, page APIs, and a rendered-page grid on `/agenda-package-ingestion`.

## [2026-07-06] correction | Separate agenda package ingestion endpoint

Restored the fixed-package `/document-import` demo and moved browser PDF selection to the dedicated `/agenda-package-ingestion` workflow endpoint.

## [2026-07-06] implementation | Agenda package browser upload

Applied migration `022_agenda_package_extraction.sql` and added streamed PDF upload, signature and hash validation, duplicate detection, transactional source/package registration, status retrieval, writable Docker upload storage, and the `/document-import` file selector.

## [2026-07-06] correction | Active local Postgres port

Updated the database standup, data-layer conventions, and zoning backlog to use active local host port `55432` and identify `54329` as obsolete.

## [2026-07-06] implementation | Agenda package ingestion contract

Defined the canonical package JSON as an ordered logical-document array, with the agenda first and one primary agenda-item key on each following document. Added PostgreSQL package extraction/result tables and blocked completion until all unknown templates have approved definitions.

## [2026-06-23] implementation | AWS deployment workflow

Added [AWS deployment](./implementation/aws-deployment.md), `infra/aws/mdopendata-ec2.yml`, `docker-compose.aws.yml`, `scripts/aws-deploy.ps1`, and `scripts/aws-sync-db.ps1` for repeatable EC2 Docker Compose deployment and local-to-AWS PostGIS synchronization.

## [2026-05-27] implementation | Release help and MCP scaffold

Added [Release help and MCP plan](./implementation/release-help-and-mcp-plan.md) to record the Markdown-source/release-output documentation boundary, `help` schema purpose, web help API boundary, and repo-local `mdopendata-mcp` package role. Implemented the first help schema migration, seed script, web help APIs, `/help` route, and local MCP package scaffold.

## [2026-05-25] source | Local Government in British Columbia ingestion plan

Added [Local Government in British Columbia](./sources/lgbc-local-government-bc.md) as a source summary for `docs/LGBC-All.pdf` and added [Local Government in British Columbia ingestion plan](../plan/lgbc-ingestion-plan.md) for raw-first structure indexing, exhibit extraction, chapter review, benchmark-candidate discovery, and Charlottetown prototype mapping.

## [2026-05-25] source | Local Government in British Columbia source registration

Completed Phase 1 source registration for `docs/LGBC-All.pdf` under `data/sources/lgbc/`, including PDF metadata, full layout text, 250 per-page text files, registration skeletons for structure, exhibits, and chapter review, and extraction notes.

## [2026-05-25] source | Local Government in British Columbia structure extraction

Completed Phase 2 structure extraction for `docs/LGBC-All.pdf`, populating `data/sources/lgbc/structure_index.json` with front matter, 13 chapters, 78 numbered chapter sections, appendix sections, and back matter, and `data/sources/lgbc/exhibit_index.json` with 41 listed exhibits. Recorded that these observed counts supersede the initial plan estimates of 76 sections and 45 exhibits.

## [2026-05-25] source | Local Government in British Columbia chapter review queue

Completed Phase 3 chapter review queue setup for `docs/LGBC-All.pdf`, populating `data/sources/lgbc/chapter_review_queue.json` with 18 pending records for 13 chapters, 1 appendix, and 4 back-matter units. The queue preserves the first-pass review order of Chapter 6, Chapter 1, Chapter 10, Chapter 12, Chapter 7, and Chapter 8.

## [2026-05-25] source | Local Government in British Columbia Chapter 6 review

Completed the Chapter 6 service-delivery review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 6: Service Delivery](./sources/lgbc/chapter-6-service-delivery.md) with source claims, exhibit use, benchmark and process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 1 review

Completed the Chapter 1 introduction review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 1: Introduction](./sources/lgbc/chapter-1-introduction.md) with source claims, fiscal-equivalence framing, collective-problem categories, benchmark and process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 10 review

Completed the Chapter 10 regulatory and development functions review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 10: Regulatory And Development Functions](./sources/lgbc/chapter-10-regulatory-development-functions.md) with source claims, planning/zoning/subdivision/enforcement process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 12 review

Completed the Chapter 12 finance review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 12: Finance](./sources/lgbc/chapter-12-finance.md) with source claims, revenue/tax/fee/transfer/debt/reserve process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 7 review

Completed the Chapter 7 protective services review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 7: Protective Services](./sources/lgbc/chapter-7-protective-services.md) with source claims, police/fire/emergency performance candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 8 review

Completed the Chapter 8 engineering services review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 8: Engineering Services](./sources/lgbc/chapter-8-engineering-services.md) with source claims, water/wastewater/solid-waste/transportation/transit performance candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 9 review

Completed the Chapter 9 human services review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 9: Human Services](./sources/lgbc/chapter-9-human-services.md) with source claims, parks/recreation/library/museum/public-health/social-housing candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 11 review

Completed the Chapter 11 labour relations review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 11: Labour Relations](./sources/lgbc/chapter-11-labour-relations.md) with source claims, workforce/unionization/bargaining-unit/service-continuity candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Phase 5 candidate catalogue

Started Phase 5 by generating `data/sources/lgbc/benchmark_process_candidate_catalogue.json` and adding [LGBC Benchmark And Process Candidate Catalogue](./sources/lgbc/benchmark-process-candidate-catalogue.md). The initial catalogue contains 86 source-derived candidates from Chapters 1, 6, 7, 8, 9, 10, 11, and 12, all pending Phase 6 Charlottetown source mapping.

## [2026-05-25] source | Local Government in British Columbia Phase 6 Charlottetown mapping

Started Phase 6 by generating `data/sources/lgbc/charlottetown_prototype_mapping.json` and adding [LGBC Charlottetown Prototype Mapping](./sources/lgbc/charlottetown-prototype-mapping.md). The first-pass mapping covers all 86 Phase 5 candidates, classifying 10 as strong source-family matches, 56 as partial source-family matches, and 20 as source gaps, with no candidate ready for public metrics or scoring.

## [2026-05-25] source | Local Government in British Columbia planning land-use dataset review

Continued Phase 6 by generating `data/sources/lgbc/charlottetown_planning_land_use_dataset_review.json` and adding [LGBC Charlottetown Planning And Land-Use Dataset Review](./sources/lgbc/charlottetown-planning-land-use-dataset-review.md). The review covers 10 Chapter 10 candidates and finds 2 ready for source-completeness review, 2 partial, 1 sample-only, and 5 source gaps for required process or outcome datasets.

## [2026-05-20] implementation | Agenda tree component split

Refactored `web/public/ui_kits/shared/agenda-tree.jsx` into a generic `PortalTreeView`, `RolePresetTabs`, and a meeting-specific `buildMeetingAgendaTree` adapter while preserving the existing `window.CouncilAgendaTree.AgendaTree`, `allItems`, and `buildAgendaTree` API used by `/council-meetings`. Updated [Municipal portal UI component architecture](./product/municipal-portal-ui-component-architecture.md) with the agenda tree contract.

## [2026-05-20] implementation | Municipal portal component architecture

Added [Municipal portal UI component architecture](./product/municipal-portal-ui-component-architecture.md) to define the reusable view-component contract, dependency posture, page-context expectations, first component families, and implementation-independence rules. Updated [Municipal portal UI architecture](./product/municipal-portal-ui-architecture.md) to reframe the basic-HTML feasibility study around component contracts rather than a blanket rewrite.

## [2026-05-20] product | Municipal portal 1.0 shell

Added the municipal portal product wiki area with product purpose, 1.0 roadmap, role model, UI architecture, and domain inventory pages. Added a React/Babel portal shell at `/`, route stubs for meetings, business items, documents, planning, budgets, maps, validation, and lab tools, a Charlottetown theme stylesheet, and `/api/portal/context` for the stable page-context contract. Updated [Root index](./index.md) and [Web UI stack](./implementation/web-ui-stack.md) to record the retained React/Babel stack and the basic-HTML feasibility-study gate before new reusable component coding.

## [2026-05-08] implementation | Charlottetown terrain DEM pipeline

Added [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) describing the first PDAL/GDAL bare-earth DEM workflow for PEI COPC LIDAR, including metadata gates, tile selection, ground filtering, 1 m EPSG:2961 output products, QA thresholds, and parcel 3D integration path. Updated [Root index](./index.md) with the new implementation page.

## [2026-05-08] source | PEI LIDAR and bathymetry metadata

Added [PEI LIDAR and bathymetry metadata](./sources/pei-lidar-bathymetry-metadata.md) summarizing local PDAL and GDAL inspection results for `maps/pei/lidar` and `maps/pei/bathymetry`, including LIDAR EPSG:2961 horizontal metadata, unresolved LIDAR vertical CRS, NONNA BAG ChartDatum metadata, GeoTIFF depth ranges, and backscatter intensity caveats. Updated [Root index](./index.md) with the new source page.

## [2026-05-08] implementation | Parcel 3D LIDAR terrain plan

Added [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) documenting the preprocessing path for PEI COPC LAZ source data, terrain and building-height derivation, `/api/parcels/:pid/3d-context` integration, browser fallback behavior, and CRS and vertical datum verification gates. Updated [Root index](./index.md) with the new implementation page.

## [2026-05-03] implementation | Provisions comparison page

Added `/provisions-comparison` and `/api/provisions-comparison` for draft Part 1 through Part 9 non-zone comparisons, with raw current-versus-draft part text and structured accepted section pairs filtered by selected draft part. The provisions UI now uses title-only part menu labels, lists structured matches in ascending order without a secondary menu, and supports collapsible structured pair cards from the pair header. Added a `Compare provisions` top-navigation link immediately after `Compare bylaws`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with endpoint behavior and scope limits.

## [2026-05-01] implementation | Web demo phase 8

Implemented phase 8 of the web demo design-kit plan by removing remaining mock-only lookup result code and inactive navigation from active demo routes, hardening disabled city-view parcel actions, and adding `npm run web:smoke` for route and API-contract checks. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and verification notes.

## [2026-05-01] implementation | Web demo phase 7

Implemented phase 7 of the web demo design-kit plan by adding `/api/zoning-comparison/:pid` and wiring `web/public/ui_kits/zoning-comparison/index.html` to live parcel zone comparison data with current and draft zone-section citations or explicit pending states. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and behavior notes.

## [2026-05-01] implementation | Web demo phase 5

Implemented phase 5 of the web demo design-kit plan by replacing the static map explorer mockup with a Leaflet parcel-centered map backed by `/api/parcels/:pid`, `/api/parcels.geojson`, `/api/zoning/current.geojson`, and `/api/zoning/draft.geojson`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and behavior notes.

## [2026-05-01] implementation | Web demo phase 4

Implemented phase 4 of the web demo design-kit plan by wiring `web/public/ui_kits/parcel-lookup/index.html` to `/api/addresses` for autocomplete and selected-PID redirects to `/map-explorer`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and behavior notes.

## [2026-05-01] implementation | Web demo phase 3

Implemented phase 3 of the web demo design-kit plan by adding bbox-filtered GeoJSON APIs for parcel candidates, current zoning boundaries, and draft zoning boundaries in `web/server.js`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with endpoint behavior, source SRID handling, and feature limits.

## [2026-05-08] implementation | Parcel 3D browser visualization

Added the parcel-specific `/parcel-3d?pid=PID` browser visualization to the web demo plan. The new page uses `/api/parcels/:pid/3d-context` for selected and adjacent parcel buildings, road context, parcel boundaries, and a 250 m default radius with seasonal shadow controls.

## [2026-05-01] implementation | Web demo phase 2

Implemented phase 2 of the web demo design-kit plan by adding civic address autocomplete and PID-based parcel resolution APIs in `web/server.js`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with the completed phase status and the provisional parcel identity constraint.

## [2026-05-01] implementation | Web demo phase 1

Completed phase 1 of the web demo design-kit plan by adding route entry points for parcel lookup, map explorer, city-view map, and zoning comparison, and promoting the selected `Island as needle` logo to `web/public/assets`.

## [2026-05-01] implementation | Web demo design kit plan

Added `implementation/web-demo-design-kit-plan.md` documenting the design-kit replacement plan, database API connection steps, UI cleanup tasks, demo acceptance criteria, timeline, risks, and open decisions.

## [2026-04-29] implementation | Web UI stack decision

Added `implementation/web-ui-stack.md` documenting the initial Docker-hosted Node web UI stack and first Charlottetown section-equivalence review page.

## [2026-04-28] maintenance | Wiki-first role workflows

Applied the wiki-first setup pattern across role skills so Business Analyst, Coding Architect, Data Quality Analyst, Debugger, GIS Specialist, and QA Reviewer read `Project Management` identified wiki pages and use `wiki/index.md` for additional context during normal task setup.

## [2026-04-28] maintenance | Wiki lookup as normal role workflow

Removed the clause-specific lookup pointer from the `Data Engineer` skill and moved wiki discovery into the normal `Project Management` classification and `Data Engineer` setup workflow.

## [2026-04-28] maintenance | Clause-label guidance relocation

Moved task-specific by-law clause label handling guidance from the `Data Engineer` skill into `domain/bylaw-clause-labels.md`.

## [2026-04-28] maintenance | Root instruction streamlining

Moved non-universal startup instructions out of root `AGENTS.md`: role gates and implementation protocol moved to the `Project Management` skill, by-law clause label handling moved to data extraction and quality skills, and Charlottetown workstream context moved to the Charlottetown wiki.

## [2026-04-28] setup | Root wiki schema scaffold

Created the root wiki schema, catalog, log, and top-level page areas for source summaries, domain concepts, platform notes, and implementation notes. Linked the existing Charlottetown wiki as the active project wiki.

## [2026-05-08] implementation | Terrain DEM demo acceptance

Updated [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) to record that the current 97.4905% refined land coverage DEM is acceptable for demo-only parcel 3D and storm-surge visualization, while deferring the 99% refined coverage target to backlog work if demo results are not satisfactory.

## [2026-05-08] implementation | Parcel 3D demo terrain integration

Implemented the first demo terrain integration for `/parcel-3d`: `/api/parcels/:pid/3d-context` now returns a compact GDAL-sampled DEM patch with demo-status metadata and fallback state, and the Three.js viewer renders the terrain mesh when available while preserving flat terrain fallback. Updated [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) with the implemented API/UI behavior and local GDAL dependency.

## [2026-05-08] deployment | Parcel 3D terrain Docker redeploy

Rebuilt and redeployed the Docker `web` service for parcel 3D terrain support. The web image now installs GDAL tools, and the normal app port returns `demo_terrain` metadata for `/api/parcels/358960/3d-context?radiusM=250`.

## [2026-05-08] implementation | Storm surge demo page

Added the demo-only `/storm-surge` web page, reusing `/api/parcels/:pid/3d-context` to render the existing parcel 3D terrain, parcels, roads, and buildings with a transparent static water plane. Added controls for Charlottetown tide presets, 0-10 m storm surge, storm/category 1/category 2 wind labels, and 0-100 year sea-level-rise scenarios. Added [Storm surge demo plan](./implementation/storm-surge-demo-plan.md) and updated [Root index](./index.md) with the new implementation page.

## [2026-05-08] deployment | Storm surge navigation Docker redeploy

Added the storm-surge top-navigation link across the web UI kit pages and rebuilt/redeployed the Docker `web` service. Verified deployed HTTP 200 responses on port 3000 for `/parcel-lookup`, `/city-view`, `/map-explorer`, `/zoning-comparison`, `/restriction-stack`, `/provisions-comparison`, `/parcel-3d`, and `/storm-surge`, each containing the Storm surge navigation text.

## [2026-05-08] implementation | Storm surge visual datum offset

Adjusted the `/storm-surge` demo water rendering to apply a configurable visual datum offset after composing chart-datum tide height, surge, and sea-level rise. The default offset is `-1.72 m`, matching the CHS Charlottetown station 01700 CGVD28 offset, so the default full/new moon high tide renders at 1.25 m in the current terrain display space rather than 2.97 m. Updated [Storm surge demo plan](./implementation/storm-surge-demo-plan.md) with the offset behavior and continued non-authoritative caveat.

## [2026-05-08] implementation | Storm surge context and water-bed rendering

Expanded the `/storm-surge` demo context radius from 250 m to 350 m, which is the current API terrain-patch cap and gives about 1.96 times the rendered area. Renamed neap-tide controls to half/quarter moon high and low tide. Adjusted terrain rendering so DEM NoData cells in the patch render as a lowered `-4 m` water bed, allowing known water and shoreline gaps to appear immersed under the water plane instead of flat at zero elevation.

## [2026-05-08] fix | Storm surge terrain base normalization

Fixed the `/storm-surge` water plane rendering frame by subtracting the terrain patch `baseElevationM` from the composed water level after the visual datum offset. This matches the API terrain normalization, where DEM elevations are sent to the browser relative to the patch median. Removed the quarter-moon wording from the half-moon tide controls and lowered the NoData water bed from `-4 m` to `-14 m`.

## [2026-05-08] fix | Storm surge datum range and NoData holes

Changed the `/storm-surge` visual datum offset default to `-1.8 m` and narrowed the slider to `-2.8 m` through `-0.8 m` for calibration around the observed plausible baseline. Clarified the wind event control as informational only because surge remains manually controlled by the surge slider. Removed the lowered NoData water bed behavior so terrain gaps no longer fill as isolated water holes before the outer water plane reaches them.

## [2026-05-08] fix | Storm surge wind removal and water-bed restore

Removed the `/storm-surge` wind event control and wind references. Restored lowered NoData terrain rendering at `-14 m` so DEM gaps again appear as submerged water-bed areas.

## [2026-05-08] implementation | Parcel 3D building terrain seating

Adjusted the parcel 3D terrain renderer so building bases use bilinear terrain sampling across each footprint and add a short foundation skirt to reduce visible floating and ground intersection on sloped DEM terrain. Rebuilt and redeployed the Docker `web` service after the rendering fix.

## [2026-05-12] implementation | Council meeting prototype wiki and extraction

Added the [Council and committee meetings](./council-committee-meetings/README.md) wiki area for meeting-preparation workflows. Added the first JSON-first Charlottetown regular council meeting extraction branch for the May 12, 2026 agenda/package and documented the public, council/committee, and municipal staff workflow model.

## [2026-05-12] implementation | Council meeting audience tabs

Expanded `/council-meetings` from a public-first view to functional public, council, and staff tabs using the same JSON-backed meeting API.

## [2026-05-12] implementation | Agenda tree and rezoning endpoint copies

Reworked `/council-meetings` into a three-pane workspace with an agenda-order left tree, audience-specific general pages, selected-item package text panes, and rezoning tool panels. Added copied meeting-specific rezoning routes for parcel lookup, zoning comparison, spatial restrictions, and storm surge.

## [2026-05-12] implementation | Council package ToC and agenda outputs

Extended the May 12 Charlottetown council extraction to emit `agenda.json` and `toc.json` beside `meeting.json`. The ToC covers all 256 package pages as logical documents with page counts, summaries, boundary observations, template categories where known, and non-PDF page reproduction options; full package content extraction remains deferred except for the two rezoning items used by the web endpoints.

## [2026-05-13] project | Council meeting database cleanup backlog

Added a council-meetings backlog item to clean up agenda-related blank tables in the PostGIS `public` schema, including confirmation of empty tables, provenance checks, and removal or quarantine without affecting JSON-first meeting outputs.

## [2026-05-13] implementation | Council meeting database importer and schema backlog

Added the council meeting database importer and database-preferred `/council-meetings` API read path. Updated the council-meetings wiki backlog to table the broader city-portal subject-schema decision until source documents and endpoint requirements are clearer.

## [2026-05-13] implementation | Document import agenda tree and taxonomy

Extracted the shared council agenda tree for `/council-meetings` and `/document-import`, with Planning & Heritage and New Business child items nested under their standing-committee parents. Added the agenda/package document taxonomy page for document-import source classes, attachment types, and reusable workflow templates.

## [2026-05-14] implementation | Document import agenda and business bindings

Updated `/document-import` so the document panel groups package documents by agenda-item set and exposes editable agenda-item and item-of-business bindings. Added `business_items` to `meeting.json`, `agenda_item_id` and `business_item_id` to `toc.json`, and `council.package_document` persistence linked to `council.agenda_item` and `council.business_item`.

## Sources

- [Wiki schema](./AGENTS.md)
Implemented the first durable business-item identity layer for council-meeting ingestion: added evidence, relationship, and candidate-link tables; added Charlottetown identity configuration plus a deterministic evidence builder; exposed identity graph payload fields through the web API and document-import UI; and documented immutable-ID plus conservative-review behavior in the council-meetings wiki.
Extended `/document-import` with agenda-hierarchy, business-item-hierarchy, and candidate-link review modes. Agenda mode now lists documents linked to the selected agenda item, business mode lists meeting-local appearances and linked documents for the selected durable item, and queue mode records accept/reject decisions in QA feedback.

## [2026-05-28] implementation | pgAdmin zoning ERD export workflow

Replaced the release zoning ERD asset workflow with pgAdmin browser automation. Added a Playwright script that opens the pgAdmin ERD tool for the `zoning` schema, uses pgAdmin's Download image action, and writes `wiki/shared/assets/zoning-schema-erd.png`.

## [2026-07-06] implementation | Agenda package template drafting and approval

Added persisted model-generated page-template drafts, editable browser review controls, and explicit transactional approval. Approval creates the active template, approved pattern, and cues, resolves the associated page gaps, and reruns classification while remaining unknown pages continue to block extraction. API, database, and browser QA used the six-page February 3 public-meeting package; one approved template matched only its intended page and five drafts remained pending.

## [2026-07-06] implementation | Multi-page package document assembly

Added package-specific logical-document assembly plans with exact contiguous page coverage, agenda-first validation, primary agenda-item bindings, multi-template page ranges, approval gating, and browser editing. QA approved all six page templates and assembled pages 5–6 into one of five logical documents; the package advanced to `ready_for_extraction` only after assembly approval.

## [2026-07-06] implementation | Deterministic agenda package extraction

Added final template-driven extraction with explicit field strategies, safe JSON Pointer assignment, multi-page text assembly, package-level JSON persistence, queryable logical-document rows, provenance, failure diagnostics, rerun idempotency, and browser result rendering. The six-page QA package produced five schema-valid logical documents, including one object covering pages 5–6, and reached `completed` with zero unresolved gaps.

## [2026-07-06] implementation | Visual deterministic field mappings

Added a synchronized visual editor for template field keys, JSON Pointers, value types, required flags, instructions, deterministic strategies, normalization, regex capture, and constants. Approved mappings render read-only; editable drafts support adding and removing rows plus advanced JSON round trips. Server validation rejects malformed and duplicate mappings before persistence.

## [2026-07-06] implementation | Visual field regions and coordinate extraction

Added a rendered-page region picker with drag selection, direct normalized coordinates, preview-page selection, visual overlays, full-page reset, JSON synchronization, and bounds validation. Deterministic extraction now uses Poppler word bounding boxes for region-limited strategies. QA isolated the second agenda heading as `PUBLIC MEETING OF COUNCIL`, then restored and reproduced the canonical full-page result.

## [2026-07-07] implementation | Non-blocking agenda package traversal

Changed agenda-package traversal from a request-blocking operation to a background job with browser polling and failure reporting. New PDF selection clears all downstream workflow output, and the Docker web service now reaps Poppler child processes. Follow-up QA restored PostgreSQL after crash recovery, made duplicate temporary-file cleanup non-blocking, handled Poppler zero-padded filenames, and reused complete render sets. The 453-page January 13 package uploaded, traversed, classified, and generated 453 review drafts; extraction remains correctly blocked pending explicit template approval.

## [2026-07-08] implementation | Budget section-based normalization review

Grouped all 116 Charlottetown 2026/2027 budget candidates into 31 source-defined sections while preserving page-level identities and normalization gates. Replaced profiler continuation guesses with 85 explicit section relationships and reduced the machine review queue from 112 repetitive page records to 28 section records covering the same 112 blocked candidates.

## [2026-07-08] implementation | Consolidated operating row mapping

Reviewed pages 18–20 as one consolidated operating section. Classified pages 18 and 19 as duplicate presentation summaries and mapped page 20 into 31 approved lines and 91 reported facts across the 2025/2026 budget, 2025/2026 forecast, and 2026/2027 budget periods for the City and Water and Sewer entities.

## [2026-07-08] implementation | Operating supporting schedules mapping

Mapped 59 extracted revenue-detail lines and 177 reported facts from pages 21–22, retaining five exact extraction blockers for missing dash or small-value tokens. Approved 15 property-tax and utility-rate rows from page 23 with separate City and Water and Sewer entities and explicit assessed-value, annual, daily, and consumption units.

## [2026-07-08] fix | Budget small-value and dash extraction

Added reviewed token overrides for five exact rows on pages 21–22, recovering ten omitted plain-integer or dash tokens without broadening numeric matching into narrative text. The completed supporting mapping contains 64 lines and 192 facts, including four explicit `dash_unresolved` values; the full raw import now contains 2,430 detected values.

## [2026-07-08] implementation | City Government budget mapping

Approved the City Government section on pages 28–33. Page 28 maps 31 authoritative lines and 93 three-period facts; five supporting pages map 27 explicit 2026/2027 breakdown amounts while excluding parenthetical staff counts and layout zeros/dashes. Seven reviewed tokens were recovered, bringing the full raw import to 2,437 values.

## [2026-07-08] fix | Document-wide aligned budget value recovery

Replaced section-specific token overrides with a table-aware second extraction pass. Financial column anchors are inferred from complete rows; plain integers and dash variants are recovered only when aligned to those anchors. Regeneration recovered 672 tokens across the document, produced 3,092 raw values, and excluded narrative four-digit years from aligned recovery.

## [2026-07-08] implementation | Economic, tourism and culture budget mapping

Added a reusable departmental operating mapper and approved pages 35–41. The two summary pages map 37 lines and 111 facts; five supporting pages map 29 explicit 2026/2027 breakdown amounts. The document-wide numeric parser now accepts whitespace inside grouped numbers and correctly parses `2, 250,000` as 2,250,000.

## [2026-07-08] implementation | Document extraction engineering contract

Added a project-wide engineering contract requiring full-document recurrence audits, reusable extraction and mapping mechanisms, explicit variation boundaries, tightly gated one-off exceptions, deterministic regeneration, reimport controls, and invariant-level QA. The contract applies across document sections and across materially equivalent document families.

## [2026-07-08] implementation | Reusable departmental budget mapping

Applied the shared departmental operating mapper to nine equivalent sections covering Environment, Finance, Fire, Human Resources, Mayor and Council, Parks, Planning, Police, and Water and Sewer. Approved 249 authoritative lines, 747 facts, and 209 supporting breakdown rows. Public Works was excluded because an unlabeled three-period row on page 87 violates the mapper's source-label invariant.

## [2026-07-09] implementation | Budget normalized controlled import

Applied Charlottetown 2026/2027 normalized importer version `normalized-full-1` after Gate 6 approval. Created pre-import backup `backups/database/mdopendata-before-budget-normalized-full-20260709.dump`, completed import batches `17` and `18`, verified the second run produced zero added events, retained zero publication snapshots, and documented Gate 7 readiness in the budget wiki.

## [2026-07-09] qa | Budget normalized source-fidelity completion

Ran Phase 7 QA for the Charlottetown 2026/2027 full normalized budget dataset. Verified 2,165 manifest facts, 2,165 source links, 161 reconciliations, family-stratified zero mismatches, dash preservation, and zero publication snapshots. Recorded the approved $2 debt discrepancy review decision, excluded 19 representative-spike facts from the publication candidate, and documented Gate 8 readiness without authorizing publication.

## [2026-07-09] cleanup | Budget representative normalized spike removal

Removed test-only representative-spike normalized records from the 2026/2027 same-document budget scope: 19 facts, 21 fact-source links, 16 line items, four statements, six document periods, seven reconciliations, three review issues, and three review-issue evidence rows. Reran Phase 7 QA and confirmed 2,165 manifest facts, zero non-manifest same-document facts, one manifest review issue, and zero publication snapshots.

## [2026-07-09] implementation | Budget Week 5 raw ingestion

Generated first-pass manifests, raw page text, raw table rows, and value-token artifacts for the 2025/2026 and 2024/2025 Charlottetown budget PDFs. Appended full-2 raw database records for 150 2025/2026 pages, 110 tables, 3,711 rows, 4,811 values, and 88 2024/2025 pages, 44 tables, 1,200 rows, 1,352 values. Confirmed zero publication snapshots and documented that normalized comparability remains gated by document-specific mapping review.

## [2026-07-09] analysis | Budget Week 5 normalized mapping review

Generated the prior-year normalized mapping review artifact for 2025/2026 and 2024/2025. Classified 34 2025/2026 and 17 2024/2025 candidates as baseline-equivalent review inputs; recorded 76 and 27 review-blocked candidates and 4 and 14 raw-blocked candidates respectively. Documented that prior-year normalized import remains blocked by raw coverage gaps and document-specific mapping approvals.

## [2026-07-09] fix | Budget Week 5 raw coverage blockers

Resolved prior-year budget raw coverage blockers by adding supplemental full-2 raw table coverage for 2025/2026 pages 14-17 and 2024/2025 pages 14-16, 62-63, and 78-86. Appended 4 source tables, 160 rows, and 280 values for 2025/2026, plus 14 source tables, 501 rows, and 637 values for 2024/2025. Rebuilt the Week 5 normalized mapping review with zero raw-blocked candidates and zero publication snapshots.

## [2026-07-09] planning | Prior-year budget normalization and refactor tracking

Added a prior-year normalized import gap report for completing the 2025/2026 and 2024/2025 budget normalization, import, reconciliation, QA, and compatibility gates. Added a deferred budget ingestion refactor tracker to preserve lessons from prior-year completion before generalizing the 2026/2027 scripts across other budget documents.

## [2026-07-09] analysis | Prior-year budget Phase 1 review start

Started Phase 1 period-label and section-continuation review for the 2025/2026 and 2024/2025 budget normalization work. Generated period-label review artifacts with zero remaining period-label blockers, proposed 33 section groups, marked nine adjacent capital project profile groups as do-not-merge records, and documented remaining Phase 1 blockers for candidate dispositions, project aliases, tax/rate operands, and debt identities.

## [2026-07-09] fix | Prior-year overview chart-source table handling

Recorded the source-pattern rule that overview pie charts are duplicate presentation when followed by a backing data table. Regenerated the prior-year Phase 1 section-continuation review so 2025/2026 pages 14 and 15 are `duplicate_summary` records, matching the 2026/2027 page 18 and 19 precedent, instead of continuations with the operating summary; normalization should ignore the chart graphic.

## [2026-07-09] analysis | Prior-year Phase 1 candidate dispositions

Recorded the universal budget extraction rule that duplicate visualization-backed fact sets are `duplicate_summary` inputs for normalization unless they are approved summary/detail relationships. Generated prior-year Phase 1 candidate dispositions: 85 normalize, two duplicate-summary, and 27 review-blocked records for 2025/2026; 38 normalize and 20 review-blocked records for 2024/2025. Remaining blockers are project aliases, tax/rate operands, and debt identities.

## [2026-07-09] analysis | Prior-year capital project alias review

Generated Phase 1 capital project alias decisions for 43 prior-year profile candidates. Mapped 30 profiles to existing 2026/2027 capital project keys, assigned eight document-only prior-year identities, and left five 2024/2025 profiles review-blocked for split/merge decisions. Candidate dispositions now stand at 161 normalize, two duplicate-summary, and nine review-blocked records across both prior-year documents.

## [2026-07-09] fix | Prior-year wrapped capital profile identity review

Added a Phase 1 capital project profile identity review that reconstructs wrapped source titles and `Project:` values from raw page text instead of relying on truncated `title_guess` values. Reviewed 43 prior-year profiles, found 14 incomplete wrapped title guesses and 18 wrapped or differing `Project:` values, and left 2025/2026 page 130 blocked because the heading and `Project:` line conflict. Candidate dispositions now stand at 160 normalize, two duplicate-summary, and ten review-blocked records.

## [2026-07-09] analysis | Budget operating detail pattern variation

Documented the operating-detail variation between 2025/2026 and 2024/2025. The 2025/2026 document uses departmental overview tables followed by multi-page `Detailed Breakdown of Budget Item` line-item tables, with totals in the overview table. The 2024/2025 document generally embeds totals in the department detail table and lacks a separate overview table. Also recorded line-wrapped large-font text reconstruction as a universal extraction requirement for titles, departments, and project names.

## [2026-07-09] generation | Prior-year operating relationship artifact

Patched the prior-year Phase 1 generator to emit `operating-detail-relationship-review.json` for 2025/2026 and 2024/2025. The artifact records 14 2025/2026 `overview_to_detail` relationships and 16 2024/2025 `total_in_detail` relationships, both targeting the same normalized department operating statement with line items. Updated budget requirements and the Charlottetown three-year budget source profile to note that large-font text in narrow columns is prone to line-wrapping and must be reconstructed before identity matching or normalized label assignment.

## [2026-07-09] qa | 2026/2027 operating relationship verification

Verified the 2026/2027 departmental operating normalization against the overview/detail pattern. The row-mapping artifacts preserve overview pages as `summary_candidate_keys` and detail pages as `supporting_candidate_keys`, with detail rows marked `supporting_breakdown`; however, the normalized import manifest currently has zero `statement_relationships`, so explicit summary/detail relationship records remain a follow-up normalization gap.

## [2026-07-09] generation | 2026/2027 explicit summary-detail statements

Patched the 2026/2027 normalized manifest generator to create distinct supporting-detail statements and 12 deterministic `summary_detail` relationship records for reviewed departmental overview/detail mappings. Regeneration preserved all 1,163 mapped lines and 2,165 facts while increasing the statement count from 30 to 42.

## [2026-07-09] generation | Prior-year Phase 1 tax/rate and debt decisions

Generated deterministic 2025/2026 tax/rate and debt review artifacts. The review approves page 19 rate declarations with stated denominators, validates 22 page 145 assessment × rate ÷ 100 expressions against reported revenues after nearest-dollar rounding, and identifies 20 entity-scoped debt instruments plus two planned-debt buckets across the City and Water and Sewer schedules. Candidate dispositions now total 164 normalize, two duplicate-summary, and six capital-identity review-blocked records.

## [2026-07-09] generation | Capital project registry and budget references

Defined source-limited project lifecycle rules and generated the first three-document capital-project registry. It contains 52 municipality-scoped project identities and 67 document-owned references across 2024/2025, 2025/2026, and 2026/2027; six conflicting split/merge or identity references remain blocked. The 2026/2027 normalized manifest now emits 173 adopted-budget project references, independent of project identity ownership.

## [2026-07-09] fix | Canonical Python and budget full-2 regression controls

Updated root instructions to require `scripts/python.ps1` for repository Python commands, ensuring use of `.venv\\Scripts\\python.exe` and its installed `psycopg` dependency. Corrected the 2026/2027 database-backed normalization test to validate only the canonical append-only `:full-2` raw tables and require a `full-2` import batch rather than asserting the obsolete `full-1` count. The wrapper-run test passes against PostgreSQL.

## [2026-07-09] review | Prior-year capital identity resolution

Resolved all six remaining prior-year capital identity records. Five combined or joint 2024/2025 profiles are retained as separate document-scoped projects because their source budgets contain no allocable split; the 2025/2026 Public Works small-fleet profile uses its matching heading and description while preserving the contradictory `Project:` source field. Phase 1 now has 170 normalization candidates, two duplicate summaries, and zero review-blocked candidates.

## [2026-07-09] generation | Prior-year Phase 2 row-mapping inputs

Generated deterministic source-linked Phase 2 inputs for every approved prior-year candidate: 58 candidates and 1,701 rows for 2024/2025, plus 112 candidates and 3,808 rows for 2025/2026. No row semantics or normalized facts were inferred; all 5,509 rows remain explicitly `needs_review` pending family-specific hierarchy, aggregation, amount-type, unit, entity, and period decisions.

## [2026-07-09] review | Prior-year Phase 2 first family approvals

Approved 514 rows in 14 standard 2024/2025 City department operating tables with detail/total roles, CAD, reporting entity, and reviewed period roles. Approved 43 capital profiles covering 288 rows as narrative-only source fields. The remaining 4,707 rows remain in the family-specific review queue.

## [2026-07-09] generation | Prior-year coordinate raw extraction regeneration

Replaced transparent-glyph-sensitive text-line extraction with visible-PDF coordinate text extraction for the 2024/2025 and 2025/2026 budget artifacts. Regeneration produced 1,300 rows and 1,448 values for 2024/2025, plus 3,112 rows and 2,578 values for 2025/2026; exact visible-line matches retained 587 and 514 prior row IDs respectively. Source-level QA confirmed the 2025/2026 page 25 total is no longer detached onto a `0` layout row and restored the Phase 1 debt review to 20 instruments plus two planned-debt buckets. Database raw records were not changed.

## [2026-07-09] review | Prior-year Phase 2 regenerated operating approvals

Corrected the Phase 2 source-column map to use one-based value indexes and approved only contiguous, header-aligned operating rows. This approves 359 2024/2025 and 719 2025/2026 City operating rows, including current-budget-only detailed-breakdown rows with one source value. It leaves 3,084 rows in the family-specific queue rather than inferring a period for omitted or shifted columns.

## [2026-07-10] generation | Prior-year Phase 2 per-value fact contract

Replaced the provisional row-level period, amount-type, and unit fields in approved prior-year Phase 2 mappings with the 2026/2027-style per-value `facts` array. The reviewed operating mappings now contain 1,015 2024/2025 and 1,556 2025/2026 source-linked facts. This preserves one normalized contract while retaining document-specific mapping rules.

## [2026-07-10] decision | Currency zero and per-value facts contract

Approved a general rule for reviewed currency columns: explicit zero, blank, and dash cells normalize to numeric zero with `reported_zero`, while retaining the original source display and column provenance. Also established the per-value facts contract as the required normalized mapping form for future budget extractions.

## [2026-07-10] review | Prior-year Phase 2 debt schedules

Approved all 40 row mappings in the 2025/2026 City and Water and Sewer debt schedules. The review maps 20 instrument rows and two schedule totals to balance, principal, and interest facts, represents both `New Debt` rows as planned-debt buckets with balance and interest only, and retains comments-column values plus combined interest-and-principal totals as non-additive source evidence.

## [2026-07-10] review | Prior-year Phase 2 tax, capital, and facility mappings

Applied 2026/2027 precedents to 2025/2026 tax/rate formulas, property-tax subtotal inheritance, capital schedule context rows, and Bell Aliant facility statements. Operating-detail rows remain the active Phase 2 review queue.

## [2026-07-10] review | Prior-year Phase 2 user-reviewed structural decisions

Applied user decisions for department hierarchy and totals, zero-display calculation treatment, facility statement periods and variance context, capital funding deductions and totals, property-tax totals, and Water and Sewer debt entity context. Regeneration produced 1,433 approved source-linked facts with 317 open rows for 2024/2025, and 2,355 approved facts with 44 open rows for 2025/2026. No database import, compatibility record, or publication snapshot was created.

## [2026-07-11] correction | 2024/2025 operating-summary structural roles

Classified PDF page 14 as a standard three-period operating statement rather than a row-semantic exception. Its nine title, header, entity, and section rows are non-additive context; 31 City and six Water and Sewer monetary rows create 91 source-linked facts. This removes all 40 page-14 rows from the unresolved register, leaving 1,524 approved facts and 277 open rows for 2024/2025. No database import, compatibility record, or publication snapshot was created.

## [2026-07-11] decision | Budget duplicate-visualization exclusion

Established the budget-ingestion rule that charts and similar visualizations are excluded from normalization when an authoritative table elsewhere in the document reports the same figures. The 2024/2025 revenue and expenditure bubble charts on PDF pages 15 and 16 are retained as raw evidence but classified as `duplicate_summary`, removing 60 non-tabular rows from Phase 2 review. No database import, compatibility record, or publication snapshot was created.

## [2026-07-12] correction | 2026/2027 operating summary-detail identities

Corrected a post-import identity divergence between the 2026/2027 normalized manifest and PostgreSQL. A transactional migration created twelve manifest-defined operating detail statements, moved 301 existing line items and their facts, retained all 301 source links, and created the approved summary-detail relationships. Batch 53 records the migration. Phase 7 source-fidelity QA subsequently matched all 2,165 facts and source links with zero publication snapshots.

## [2026-07-12] correction | Isolated budget migration regression database

Changed the budget migration regression test to create a unique empty PostgreSQL database from `template0`, run migration 025 and its regression controls there, and remove it on success or failure. The active `mdopendata` database is no longer a test target. The configured `mdopendata` role has verified `CREATEDB` permission.

## [2026-07-12] review | 2026/2027 budget Gate 8 commenced

Started the Gate 8 QA-completion and publication-eligibility review without authorizing publication. Current Phase 7 QA matches all 2,165 facts and source links, retains 161 reconciliations with one accepted source-document discrepancy, confirms zero unresolved high- or critical-severity issues, and confirms zero publication snapshots. Gate 8 approval remains pending.

## [2026-07-12] decision | 2026/2027 budget Gate 8 approval

The project owner approved Gate 8 after reviewing the current QA evidence. The 2026/2027 normalized dataset is publication-eligible. No publication snapshot, public release authorization, or public API/UI exposure was created by this decision.

## [2026-07-12] review | Prior-year budget Gate 8 commenced

Started Gate 8 QA-completion and publication-eligibility review for the 2024/2025 and 2025/2026 normalized datasets. Current provenance QA confirms 1,717 and 2,374 facts respectively, zero source mismatches, 14 passing reconciliations across both documents, zero unresolved high- or critical-severity issues, and zero publication snapshots. Approval remains pending.

## [2026-07-12] decision | Prior-year budget Gate 8 approval

The project owner approved Gate 8 for the 2024/2025 and 2025/2026 normalized datasets. Both datasets are publication-eligible. No publication snapshot, public-release authorization, or cross-period publication scope was created by this decision.

## [2026-07-12] proposal | Three-year Charlottetown budget publication snapshot

Prepared a non-executing proposal for one draft Charlottetown snapshot covering all 6,256 approved facts from the three Gate 8-approved financial-plan documents. The proposal requires an exact approved taxonomy-version label before execution, preserves the accepted 2026/2027 debt discrepancy as a warning, and separates draft creation from the later decision to publish.

## [2026-07-12] decision | Charlottetown budget snapshot taxonomy version

The project owner approved `charlottetown-budget-v1` as immutable metadata for the first three-year Charlottetown budget snapshot. The label does not claim a cross-municipality taxonomy or enable cross-municipality comparison.

## [2026-07-12] generation | Three-year Charlottetown snapshot dry-run plan

Generated a non-mutating plan for draft release label `charlottetown-budget-2024-2027-initial` using taxonomy version `charlottetown-budget-v1`. It selects all 6,256 approved facts from source documents 7, 8, and 9, reports zero open high- or critical-severity issues and zero existing snapshots, and has SHA-256 `33a5aefbdb0778f26d9cec74add218e6dee3424f044bd7ed4e8382120dd88a91`.

## [2026-07-12] generation | Three-year Charlottetown draft publication snapshot

Created draft snapshot 1, `charlottetown-budget-2024-2027-initial`, with taxonomy version `charlottetown-budget-v1`. It contains 6,256 approved facts from source documents 7, 8, and 9. Validation confirms zero unapproved or out-of-scope members and zero rows in `budget.v_published_facts`; no public release was authorized.

## [2026-07-12] scope | Public budget API first slice

Defined the initial read-only API scope for published snapshots: municipality and period discovery, source inventory, single-fact provenance, and filtered CSV export. Draft snapshots remain invisible; aggregates, explorers, comparisons, and public pages are deferred pending implementation and compatibility controls.

## [2026-07-12] correction | Published budget snapshot documentation

Verified snapshot 1 directly in `budget.publication_snapshot` as `published` and confirmed 6,256 rows in `budget.v_published_facts`. Corrected the snapshot record, public API scope, budget index, and root index so they no longer describe the live snapshot as draft or awaiting publication.

## [2026-07-12] implementation | Public projects and budget visualization

Added published-snapshot-gated capital-project list and detail APIs, including multi-year facts, approved references, and profile fields. Replaced the `/budgets` contract stub with a fiscal-period budget view containing exploratory summary metrics, accessible sorted bars and tables, project browsing, fact provenance links, source inventory access, CSV download, and explicit comparison and lifecycle limits. No schema or dependency changes were introduced.

## [2026-07-12] qa | Public projects and budget visualization

Rebuilt the approved local web container and passed all 21 repository web smoke checks. Live browser QA for 2026/2027 rendered five financial bars, $252,143,798 in capital detail, and 169 published projects; the Aeration Tank Rehab detail returned two published facts, two approved references, four approved profile fields through the API, and no UI errors. Invalid project status returned `400`, an absent published project returned `404`, and source syntax and diff checks passed.

## [2026-07-12] implementation | Exact-identity comparison and source pages

Implemented nominal cross-period comparison for exact published fact identities with numeric and percentage change, zero-baseline suppression, stable pagination, and visible matched and unmatched coverage. Added fact citation metadata and authorized single-page PNG rendering for documents in the selected published snapshot, with repository path and page-bound validation. Extended `/budgets` with prior-period controls, comparison bars and tables, source-document links, and explicit compatibility limits.

## [2026-07-12] qa | Exact-identity comparison and source pages

Rebuilt the approved local web container and passed all 24 web smoke checks. The 2025/2026-to-2026/2027 query returned 440 exact detail matches against 1,296 prior and 729 current detail facts, with unmatched facts explicitly excluded rather than zero-filled. Browser QA rendered ten comparison bars and table rows without errors. Published document 9 page 1 rendered as a 1237 by 1600 PNG; unpublished document and out-of-range page requests returned `404`, same-period and malformed-entity comparisons returned `400`, and syntax and diff checks passed.

## [2026-07-12] correction | Filter-scoped comparison coverage

Corrected comparison coverage so matched, current-period, and prior-period counts use the same entity, metric, and category filters as returned rows, while the total matched count remains independent of pagination. QA confirmed 440 unfiltered matches and 362 City of Charlottetown matches with 528 current and 1,100 prior detail facts.

## [2026-07-12] proposal | Normalized category taxonomy and mapping

Prepared a non-mutating `charlottetown-budget-category-v1` vocabulary and mapping proposal covering 2,420 eligible detail line items and 4,941 facts. The proposal excludes 956 non-detail lines from first aggregate mapping, requires context-aware review for 325 repeated-label cohorts, defines exact per-row review evidence, and blocks implementation until a versioned assignment relation preserves snapshot 1 semantics.

## [2026-07-13] plan | Dedicated budget page views

Reevaluated the combined `/budgets` page and prepared a review-gated plan for budget-year, department, project, and municipal-analysis routes. Read-only inventory confirmed 6,256 published facts, 182 capital projects, only 389 published facts with organization-unit assignments, and duplicate fiscal-period labels across annual source documents; the plan therefore gates implementation on canonical observation, authoritative measure, department coverage, and analysis metric contracts.

## [2026-07-13] query | Budget edition and department-assignment coverage

Clarified that a budget-year page must use the corresponding annual PDF and its own budget observations rather than merging same-label values from later documents. Database review found 207 published facts linked to 172 published projects, zero project organization-unit assignments, 24 published projects with an approved department profile field, 389 department-assigned non-project operating facts, and 5,660 non-project facts without a department assignment. Recorded tentative acceptance of the normalized-category proposal for a visibly non-published browser preview while retaining its migration and publication gates.

## [2026-07-13] implementation | Budget edition, taxonomy, and fact explorer

Applied migration 027 and the authorized taxonomy/assignment workflow after creating `backups/database/mdopendata-before-budget-web-taxonomy-20260713.dump`. Added three budget editions, 34 category candidates, 667 proposed controlled-label assignments, 24 approved project-department assignments, nine capital programs with 577 line assignments, and 333 approved exact one-to-one subsequent-forecast links. Snapshot 1 retains 6,256 members and published fact rows while using the explicitly authorized `charlottetown-budget-category-v1` revision overlay.

Replaced `/budgets` with a source-document-scoped annual view and added `/budgets/facts` for fact and assignment review. The API now enforces document, department, program, and project filters; the annual page separates proposed revenue and expenses, source totals, capital, tax/rates, debt, and external funding, and displays exact subsequent forecasts for matched prior-year facts.

## [2026-07-13] qa | Budget web taxonomy and filtering

Passed the isolated migration regression, Python compilation, idempotent zero-write rerun, server syntax validation, and all 30 web smoke checks. Data-quality review removed 265 ambiguous many-to-one forecast links and enforced unique targets for the remaining 333 exact matches. Browser QA confirmed that 2025/2026 loads 1,220 primary-period facts, fact 33415 renders its matched $155,000 subsequent forecast, project URL filtering returns one `street-resurfacing` fact, edition requests cannot overwrite a newer selection, and no browser console errors occur.

## [2026-07-13] implementation | Budget content and financial observations

Applied migration 028 as a breaking rename: numeric facts are now financial observations, while `fact` exclusively stores source-authored narrative, attribute, or list content. Added a reviewed 101-section hierarchy based on the 2026/2027 table of contents, extracted contextual content across all three editions, standardized eight Strategic Plan 2022 to 2026 facts from the standalone source, and added four separate editorial budget guides.

Published snapshot 3 contains 6,381 financial observations with complete section mappings and 446 non-empty contextual facts. Recovered 125 previously omitted 2026/2027 property-tax and City debt observations. Replaced the budget interface with contents, overview, operating department, capital project, appendix, contextual-fact, and financial-observation views.

## [2026-07-13] qa | Budget content redesign

Passed clean isolated migration regressions, repeat content import, source-value controls, server and Python syntax checks, the full portal smoke suite, and browser checks. Verified department narrative-plus-number composition, three populated 2026/2027 appendices, and explicit absent-appendix placeholders for 2024/2025.

## [2026-07-13] correction | Budget fact formatting and source-aligned tables

Replaced plain-text fact bodies with semantic heading, paragraph, unordered-list, and ordered-list blocks while retaining searchable body text and page citations. Removed PDF hard line wrapping from normalized paragraph content and reconstructed wrapped department list items.

Pivoted financial observations into source-aligned HTML rows with fiscal periods or measures as columns and per-cell evidence links. Added explicit operating and capital overview sections, and corrected property-tax and long-term-debt schedules to align their source values on one row with reviewed source-column labels.

## [2026-07-14] plan | Charlottetown financial statements ingestion

Prepared a gated repository implementation plan for the eight image-only Charlottetown financial-statement PDFs. The plan defines migrations 029 and 030, twelve ETL and publication scripts, deterministic raw and normalized artifacts, representative source controls, eleven approval gates, API and browser scope, and nine named regression or smoke-test files. It preserves draft and audited comparatives, prevents consolidated/component and pension double counting, and requires reviewed budget-equivalence relationships before budget-to-actual publication.

## [2026-07-14] ingest | Financial statements Gate 1 source authority

Registered eight Charlottetown financial-statement PDFs with SHA-256 hashes, 188 total pages, source-page titles and reporting dates, reporting scopes, accounting frameworks, and independent-auditor evidence. Resolved six filename conflicts for ingestion identity, including two `Draft` labels on audited source copies, two 2024 filenames containing 2023 pension statements, one title spelling error, and the Water and Sewer pension December 21 filename versus repeated December 31 source content. All eight documents are approved for Gate 2 profiling and remain blocked from publication because municipal publication/adoption status is unknown.

## [2026-07-14] ingest | Financial statements Gate 2 full profile

Profiled all eight registered financial-statement PDFs and all 188 pages with full-page OCR, page dispositions, source profiles, page inventories, and table manifests. Classified 139 candidates comprising 28 primary statements, 14 schedules, and 97 note-disclosure tables with zero unclassified financial tables. Recovered eight sideways schedule pages through recorded rotation, retained two low-confidence City note pages as exact visual-review controls, passed five profile regressions, and confirmed a 417-file deterministic rerun with zero hash differences. No schema, database, normalized mapping, or publication changes were made.

## [2026-07-14] review | Financial statements Gate 2 low-confidence pages

Visually reviewed PDF page 28 in both City consolidated-statement editions. Both are legible Note 15 budget-reconciliation tables with `Per Budget Document`, `Net Adjustments`, and `Consolidated Budget` columns; reclassified them from generic note disclosures to `budget_reconciliation_note`. Recorded four source control rows per page, the unaudited budget-column limitation, the 2024 redundant negative notation on Protective services, and the 2025 underlined capital-transfer adjustment that OCR can misread as a trailing minus. Both controls are approved for Gate 3 with zero remaining low-confidence review blockers.

## [2026-07-14] implementation | Financial statements Gate 3 schema spike

Materialized seven representative financial-statement controls across seven unique PDF pages as 247 raw OCR rows and 612 cells with stable identities, normalized coordinates, confidence, and source hashes. Verified consolidated position, budget-to-actual operations, cash-flow sections, component operations, pension position, a one-dollar document-owned comparative difference, and the Water and Sewer pension filename-date conflict. All patterns fit the existing schema plus the four objects already planned for migration 029, with zero unsupported patterns and zero unplanned gaps. Seven regression tests passed; no migration, database write, normalized observation, snapshot, or publication change occurred.

## [2026-07-14] implementation | Financial statements Gate 4 migrations

Implemented migrations 029 and 030 with accounting context, nine statement classes, reviewed entity and observation relationships, financial-statement category assignments, publication gates, and six scope-safe finance views. Added isolated SQL regressions and extended the unique-database migration harness. Two clean builds passed together with Gate 2 and Gate 3 negative controls; no temporary databases remain. The active database remains unchanged at 2 snapshots, 12,637 observation memberships, and 2 published snapshots, and neither migration was applied to it.

## [2026-07-14] ingest | Financial statements Gate 5 raw extraction

Extracted all 139 profiled financial-table pages across eight documents as 4,852 raw coordinate rows and 10,085 raw cells, applying eight reviewed schedule rotations. Generated 1,331 exact row-mapping reviews and controlled period, statement-class, hierarchy, entity-scope, dash/sign, reporting-entity, comparative, budget-equivalence, and taxonomy registers with zero approvals. Nine regressions passed, five representative pages passed visual source review, and 51 generated files reproduced with zero SHA-256 differences. Raw-database import was not authorized or performed; no normalized record or publication state changed.

## [2026-07-14] review | Financial statements Gate 5 batch 01

Produced the complete 29-row review batch for parser-confidence-below-80 rows in primary statements across all eight documents and 17 source pages. Visual source review yielded seven retain proposals, nine source-verified transcription proposals, and 13 non-financial layout-artifact exclusions; every exact row remains unapproved. Added deterministic generation and source-locator regressions without applying raw corrections, normalization, database writes, or publication changes.

## [2026-07-14] decision | Financial statements Gate 5 batch 01

Reviewed all 29 Batch 01 rows against 17 exact PDF page renders. Approved 28 proposals as written and revised City 2025 operations record 10 from retention to source-verified transcription because its total-revenue raw text contains `97,421,447`, `100,740,160`, and `101,452,953` while its parsed value list is empty. Final extraction decisions are six retentions, ten transcriptions, and 13 layout-artifact exclusions; hierarchy, normalization, database import, and publication remain unchanged.

## [2026-07-14] apply | Financial statements Gate 5 batch 01 and batch 02

Applied all 29 Batch 01 extraction decisions to a deterministic controlled derived artifact, materializing 16 source-verified financial rows and recording 13 exclusions without mutating raw evidence. Produced Batch 02 with every remaining sub-80-confidence note or schedule row: 111 rows across 67 pages, comprising 82 note rows, 29 schedule rows, 26 value-bearing rows, and 85 rows without parsed values. Four family-stratified PDF controls confirmed locator alignment; Batch 02 retains zero approvals and makes no normalization, database, or publication change.

## [2026-07-14] review | Financial statements Gate 5 batch 02 decisions

Reviewed all 111 Batch 02 rows against exact PDF pages and row bounding boxes rendered at 180 DPI. Revised and approved 57 source-verified financial transcriptions, 7 context transcriptions, and 47 non-financial layout-artifact exclusions in 67 source-page groups. The decisions preserve raw evidence and do not yet apply controlled derived corrections, approve normalization, write the database, or change publication.

## [2026-07-14] apply | Financial statements Gate 5 batch 02

Applied all 111 approved Batch 02 decisions to deterministic controlled-derived artifacts, materializing 57 source-verified financial rows and 7 context records and recording 47 exclusions. Exact decision-to-raw round trips, source-fidelity controls, 111 unique row keys, and 10 raw and Batch 01 negative controls passed with zero changes. Raw evidence, hierarchy, normalization, the database, and publication remain unchanged.

## [2026-07-14] ingest | Financial statements Gate 5 batch 03

Produced an unsampled review batch for all 228 remaining sub-80-confidence cells across 191 unresolved parent rows, 77 PDF pages, and all eight documents. The queue contains 102 text cells, 51 amount candidates, 69 dash candidates, and 6 signed-amount candidates; 177 other low-confidence cells are excluded because approved Batch 01 or Batch 02 whole-row treatments supersede separate cell review. No visual decision, raw correction, value-state approval, normalization, database write, or publication change occurred.

## [2026-07-14] review | Financial statements Gate 5 batch 03 decisions

Reviewed all 228 Batch 03 cells against exact PDF pages and cell bounding boxes rendered at 180 DPI, including recorded schedule rotations. Revised and approved 117 source-verified financial transcriptions, 7 context transcriptions, 86 source dash placeholders, and 18 non-financial layout-artifact exclusions. Source controls corrected `(792,142)`, `(742,585)`, `35,377,973`, `73,115`, and `- %`; controlled-derived application, normalization, database writes, and publication remain unchanged.

## [2026-07-14] apply | Financial statements Gate 5 batch 03

Applied all 228 approved Batch 03 cell decisions to deterministic controlled-derived artifacts, materializing 117 source-verified financial cells, 7 context cells, and 86 source dash states while recording 18 exclusions. Exact decision-to-raw cell round trips and source-fidelity controls passed. Raw evidence, approved row decisions, hierarchy, normalization, the database, and publication remain unchanged.

## [2026-07-14] ingest | Financial statements Gate 5 batch 04

Produced the complete 139-table context review queue by exact table-key joins across the period, statement-class, and entity-scope registers. The queue spans all eight documents and 139 source pages, identifies 133 current-year candidates, 109 comparative-year candidates, and 34 tables with other detected years, and retains zero approvals. Source-column roles remain explicitly deferred; normalization, database writes, and publication remain unchanged.

## [2026-07-15] review | Financial statements Gate 5 batch 04 decisions

Reviewed all 139 Batch 04 table contexts against exact source pages. Approved 134 proposals as written and revised five period-evidence records: City 2024 page 19 adds an OCR-omitted 2023 assumptions heading, and City and Water and Sewer debt pages 26 or 17 classify future principal-repayment years as financial schedule evidence. Table-level reporting dates, statement classes, and entity scopes are approved; source-column roles, normalization, database writes, and publication remain unchanged.

## [2026-07-15] apply | Financial statements Gate 5 batch 04

Applied all 139 approved Batch 04 table-context decisions to deterministic controlled-derived artifacts. Materialized table-level reporting dates, financial and contextual years, statement classes, entity scopes, and the cross-entity non-addition rule while retaining zero source-column roles. Raw evidence, source registers, normalization, the database, and publication remain unchanged.

## [2026-07-15] implementation | Financial statements Gate 6 semantic columns

Audited all 551 Gate 5 OCR group columns and found 345 mixed text/year/value columns plus 258 columns spanning more than 25 percent of page width. Implemented migration 031 with reviewed semantic columns, multi-fragment raw-cell assignments, semantic document-period links, exact-fragment and same-table controls, and legacy raw-column compatibility. Isolated full-chain regressions passed without changing the active database or raw records.

## [2026-07-15] architecture | Staged PDF inventory and extraction

Specified a review-first PDF workflow that inventories bounded page blocks, assembles multi-page logical content groups, applies versioned structural templates, and gates raw extraction on approved structure. Defined a local review UI contract, append-only decisions, deterministic shadow artifacts, material template-mismatch stops, and source-linked parity testing against the published Charlottetown 2026/2027 financial plan: source hash `d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac`, 154 pages, and 2,290 distinct observations in published snapshot 3. No code, schema, database, dependency, or publication changes were made.

## [2026-07-15] implementation | Staged PDF artifact JSON Schemas

Implemented one JSON Schema Draft 2020-12 discriminated union with seven closed artifact contracts: source evidence, block inventory, logical content groups, structural templates, template applications, append-only review decisions, and baseline parity reports. Added semantic and cross-artifact validation for geometry, page and block accounting, logical ownership, reference integrity, template mismatch handling, review event chains, deterministic reruns, database-write controls, and parity counts. Ten regression tests passed. No extractor, UI, dependency, database, or publication changes were made.

## [2026-07-15] implementation | Charlottetown staged PDF source evidence

Generated the deterministic Stage 0 evidence package for all 154 pages of the Charlottetown 2026/2027 financial plan: 154 renders, 154 thumbnails, 154 embedded-word files, and one Tesseract fallback on PDF page 24. The 464-file, 43,550,929-byte package validates against the staged artifact contract and reproduced unchanged on a second run with artifact SHA-256 `d24885a23ebf33a63d9e09273a5335cdbef45fd727dcf93d6c23b5bbe9c3eb2e`. Three generator regressions and ten schema regressions passed; representative pages 24, 87, 149, and 153 passed visual review. No database, dependency, public UI, or publication state changed.

## [2026-07-15] plan | Staged PDF inventory review UI

Planned a disabled-by-default, local-only extension of the existing Node web runtime with a read-only Stage 0 first slice, allowlisted artifact and asset APIs, schema-mapped page, block, group, template, decision, and parity panels, and a separately gated canonical Python writer for atomic artifact plus review-chain updates. The plan defines optimistic concurrency, demo-route denial, dependency invalidation, rollout slices, and verification gates. No UI code, route, writer, dependency, database, or publication change was made.

## [2026-07-15] implementation | Staged PDF inventory review UI Stage 0

Implemented the disabled-by-default local Stage 0 inventory reviewer for the Charlottetown 2026/2027 financial plan. The Node service now exposes one allowlisted artifact through canonical pre-serve validation and per-request asset hash checks; the static interface provides 154 lazy thumbnails, page renders, embedded and OCR overlays, representative controls, URL and keyboard navigation, evidence counts, hashes, review state, and source citations. Targeted smoke checks passed disabled, demo-denied, non-loopback-denied, invalid-path, invalid-method, full inventory, page 24 OCR, and evidence-asset cases. Browser QA passed desktop and 700-pixel layouts, 4 embedded plus 6 OCR page 24 boxes, page 149 navigation, and zero console warnings or errors. No write endpoint, dependency, database query, public route, or publication change was introduced.

## [2026-07-15] operations | Staged PDF reviewer private-LAN access

Added explicitly gated private-LAN access for the read-only staged PDF reviewer. `scripts/start-staged-pdf-review.ps1` resolves the active private IPv4 address, binds the host Node runtime to port 3217, enables review and network flags, forces demo mode off, and preserves the canonical Windows Python validator. Non-loopback access still fails without the network flag, demo mode overrides both flags, and Docker and Render remain disabled by default. The endpoint is unauthenticated and restricted operationally to trusted private networks.

## [2026-07-15] operations | Restricted iPad firewall access

Added the approved Windows inbound rule `mdopendata PDF review 3217 iPad`, restricted to TCP port 3217, Public profile, the Node executable, and remote IPv4 address `192.168.2.43`. Verified the listener on `0.0.0.0:3217` and an HTTP 200 response through host address `192.168.2.52`. No other firewall scope or deployment surface changed.

## [2026-07-15] implementation | Staged PDF block inventory and overlays

Implemented the deterministic Stage 1 candidate block generator and generated 440 fully accounted blocks across 154 pages, including 101 conservative financial candidates and one OCR-derived review page. The read-only UI now validates Stage 0 and Stage 1 together, displays selectable normalized block overlays and exact block evidence, and reports page-level inventory status. Schema, generator, server-gate, API, asset, and responsive browser checks passed; the 820-pixel iPad layout has no horizontal overflow or console warnings. No approvals, write endpoints, database queries, normalization, or publication changes were introduced.

## [2026-07-16] decision | Staged PDF reviewer propagation and version 2 design

Approved prioritized requirements for document-scoped structural propagation, formatted-text title regions, span-aware tables, optional full-width table titles, progressive review policies, and municipal agenda-package template reuse. Approved a parallel version 2 schema design in which `column_span` and `row_span` are optional with effective defaults of `1`, template review policies are immutable artifacts separate from structural templates, and material variation cannot be automatically approved. Added the gated version 2 implementation plan, root wiki index entries, migration controls, and QA stop conditions. No code, schema file, generated artifact, database, dependency, deployment, or publication change was made.

## [2026-07-17] implementation | Staged PDF artifact version 2 phases 0 and 1

Froze the current version 1 Charlottetown pilot at 154 pages, 442 blocks, 77 tables, 9,638 cells, 709 formatted-text regions, one relationship, and 104 review events with exact schema, artifact, generator, writer, and review-head hashes. Implemented a separate version 2 Draft 2020-12 schema and version-aware validator for optional row and column spans with effective defaults of `1`, exact expanded grid coverage, formatted-text titles, full-width boundary table titles, immutable template review policies, policy-evaluated applications, and human or system review decisions. Added Phase 0 hash and inventory controls plus version 1 isolation and version 2 positive, negative, conditional, audit, and cross-artifact regressions. No version 1 artifact, migration output, active review workspace, database, dependency, deployment, or publication state was changed.

## [2026-07-27] implementation | Staged PDF artifact version 2 Phase 2

Implemented the deterministic version 1 to version 2 migration command and generated the Charlottetown pilot's parallel source evidence, block inventory, review decisions, and migration report. The migration preserved 154 pages, 442 blocks, one relationship, omitted unit spans, stable record keys, and all 104 historical event hashes; it appended one `migrate_schema` decision linking the frozen version 1 block hash to the version 2 block hash. The pilot contained no structural-template artifacts, so zero `review_required` policies were eligible or seeded and no automatic-approval policy was created. A clean rerun produced four unchanged outputs, 34 schema and migration tests passed, the version 2 set validated, version 1 hashes remained unchanged, and database and publication write counts were zero.

## [2026-07-27] implementation | Staged PDF artifact version 2 Phase 3

Implemented parallel version 2 Stage 1 generator and writer entry points, local workspace selection, and reviewer controls for formatted-text titles, effective row and column spans, logical-cell merge and split, and full-width top or bottom table titles. The frozen version 1 generator and writer remain byte-identical and version 1 remains the default local reviewer; version 2 requires explicit selection and remains shadow-only. Writer regressions cover horizontal and two-dimensional spans, omitted unit spans, split and merge round trips, top and bottom titles, relationship protection, version 2 audit provenance, and continuation of the migrated 105-event review chain. The 154-page version 2 generator reproduced byte-identically in temporary clean runs, server smoke checks passed both workspace versions, and desktop plus 700-pixel browser checks found zero console errors, warnings, or horizontal overflow. No pilot artifact, database, publication, dependency, deployment, or active downstream input changed.

## [2026-07-27] implementation | Staged PDF artifact version 2 Phase 4

Implemented deterministic document-scoped `Find similar` previews for approved table and formatted-text structures, target-evidence recalculation, fit and mismatch classification, current/proposed overlays, candidate exclusion, cancellation, atomic selected-target application, stale block and review hash protection, and append-only rejection negative controls. The actual page 18 pilot pattern produces one eligible candidate and 75 material controls; preview leaves canonical block and review hashes unchanged. Immutable template promotion, review policies, cross-document reuse, database writes, publication changes, dependencies, and deployments remain outside Phase 4.

## [2026-07-27] implementation | Staged PDF artifact version 2 Phase 5

Implemented human promotion of approved document patterns into immutable structural-template artifacts, immutable semantic-versioned review policies, evidence-gated review reduction, deterministic sampling, exact policy evaluation, automatic system audit events, policy demotion, explicit suspension, and runtime suspension for configured drift and control failures. The reviewer reports template and policy state and applies only server-recomputed automatic candidates. Fifty-seven staged-PDF regressions, both-version server smoke checks, canonical validation, JavaScript checks, and desktop and 700-pixel browser checks pass with zero overflow or console warnings; the canonical pilot registry remains empty until a reviewer explicitly promotes a pattern. Cross-document and agenda-package reuse, database writes, publication changes, dependencies, deployments, and active downstream workspace changes remain outside Phase 5.

## [2026-07-27] implementation | Staged PDF artifact version 2 Phase 6 started

Implemented closed JSON contracts for approved municipal-source reuse profiles and deterministic package previews, plus a read-only classifier for embedded-document boundaries, source order, package grammar, exact template and policy references, policy outcomes, and complete page accounting. Added a disabled-until-configured ingestion API and reviewer panel; incomplete source identity, incomplete traversal, unknown pages, equal-priority conflicts, material variation, and profile-scope mismatches fail closed. Nine isolated controls pass, including single-page and multi-page ordering, nearest-negative rejection, deterministic sampling, schema self-validation, and reviewer integration. No canonical source profile was invented because the Phase 5 registry contains no approved agenda-package template or policy; real-package profile promotion and controls remain pending.

## [2026-07-27] implementation | Staged PDF artifact version 2 Phase 7 core

Implemented deterministic stable-key parity across 154 source-page records, 154 page dispositions, 442 blocks, one relationship, and the version 1 and version 2 review histories. The generated 856-record report contains 751 exact matches, zero missing records, zero changed records, 104 approved provenance-only shifts, and one explicit schema-migration event; two clean runs are byte-identical at SHA-256 `dd2cbdcbe6dc7b0b3a7e15d1029fd2680a3b3611352a722eba115aad386ac2cf`. The explicit version 2 reviewer exposes the validated report and four handoff blockers read-only. Full handoff remains blocked because logical groups, a 2,290-observation shadow export, live publication-state verification, and explicit transition approval are absent.

## [2026-07-27] verification | Staged PDF Stage 2 and live Snapshot 3 parity

Materialized 77 logical groups with exact primary ownership for every Stage 1 financial candidate block and exported 2,290 unique shadow observations: 2,165 approved manifest observations, 76 recovered property-tax observations, and 49 recovered City-debt observations. Read-only PostgreSQL verification confirmed that published Snapshot 3 contains 6,381 total observations across source documents 7, 8, and 9, with exactly 2,290 unique document-9 semantic records, 2,290 unique source links, and zero missing links. Canonical semantic and provenance digests match Stage 2 exactly. The updated 858-record Phase 7 report has 753 exact matches, zero missing or changed records, 104 approved provenance shifts, one migration event, and only the explicit active-workspace transition approval blocker remaining.

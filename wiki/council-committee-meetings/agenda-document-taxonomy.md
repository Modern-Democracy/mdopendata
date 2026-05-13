---
type: domain
tags:
  - council-meetings
  - document-import
  - taxonomy
updated: 2026-05-13
---

This page catalogs agenda item and agenda package attachment types used by the council meeting document-import workflow.

# Agenda and Package Document Taxonomy

## Purpose

The `/document-import` workflow reshapes `agenda.json`, `toc.json`, and `meeting.json` so they match the agenda package PDF. Package segmentation should prioritize the related council resolution or decision item, then separate each item into the 1-n attached documents that appear in the PDF, each with a 1-n page count.

The resulting changelog is expected to feed parser refinement. Repeated document workflow templates, such as the City of Charlottetown `RESOLUTION OF COUNCIL` boilerplate title page, should become reusable detection patterns when they are observed in later document-import runs.

## Agenda Item Types

| Type | Sub-types | Notes |
| --- | --- | --- |
| Opening business | call to order, conflicts, agenda approval, minutes adoption, business arising, inquiries | Usually agenda-only unless minutes or supporting documents are attached. |
| Standing committee report | Planning & Heritage, Environment & Sustainability, Finance, Human Resources, Strategic Priorities, Protective & Emergency Services, Parks and Recreation, Water and Sewer, Economic Development, Public Works | May include a cover report plus multiple decision items and attachments. |
| Planning and development item | rezoning, variance, consolidation, subdivision, public consultation, development agreement, permit-related report | Often includes property references, PIDs, applicant material, staff analysis, maps, and resolutions. |
| Council resolution | committee resolution, planning board resolution, appointment resolution, agreement resolution, policy resolution | Resolution should be the primary grouping point when an agenda package item has multiple attachments. |
| Bylaw reading | first reading, second reading, third reading, amendment reading | May link to zoning, land-use, or procedural bylaw text and supporting maps. |
| New business | appointment, late resolution, emergent council item | Treat as part of the agenda tree under its parent new-business item when the source agenda nests it there. |
| Closed-session item | closed-session motion, business arising from closed session | Supporting details may be intentionally absent or limited. |
| Other agenda item | uncategorized, parser-created review item | Use only when the PDF content does not fit a known type. |

## Package Attachment Source Classes

| Class | Document types | Sub-types and examples |
| --- | --- | --- |
| Municipal sources | agenda, minutes, monthly report, committee report, staff report, planning board report, resolution, bylaw reading, map, permit list, financial report | City-generated or city-maintained material. Includes report covers, formal motions, source maps, internal summaries, and reproduced tables. |
| Received material | email, letter, document submission, applicant package, developer package, public submission, external-body submission, petition, image, site plan | Material received from applicants, developers, other bodies, members of the public, or other non-city originators. |
| Other | uncategorized, duplicate, blank separator, scan artifact, parser review item | Use when source class or document type cannot be assigned without review. |

## Attachment Template Types

| Template type | Applies to | Detection basis |
| --- | --- | --- |
| resolution-cover | `RESOLUTION OF COUNCIL` title or cover pages | Boilerplate title page, resolution number/title, committee source, moved/seconded fields, and council date. |
| resolution-text | Resolution body pages | Formal `WHEREAS`/`BE IT RESOLVED` text, motion wording, signatures, or voting fields. |
| committee-report-cover | Standing committee report cover page | Committee heading, council date, report-to-council language, and summary list of included matters. |
| minutes | Draft or adopted meeting minutes | Meeting date, presiding officer, attendance, motions, and page numbering. |
| staff-report | Staff-authored analysis | Staff author/department, recommendation, background, analysis, options, and attachments. |
| map-or-plan | Maps, site plans, drawings, surveys | Graphic-heavy page, legend, property labels, scale, or plan title block. |
| correspondence | Letters and emails | Sender/recipient metadata, salutation, email headers, submission text, or external letterhead. |
| permit-or-activity-list | Permit applications or monthly activity tables | Tabular lists of permits, addresses, application IDs, dates, or statuses. |
| other-template | Unclassified repeated pattern | Use for review until enough examples justify a named template. |

## Current Workflow Rules

- Resolution-linked package groups should keep the resolution or agenda decision item as the parent and attach the supporting documents below it.
- Attachment boundaries should preserve the source PDF page order and page counts.
- Source labels and titles should be preserved as observed unless a separate normalization rule exists.
- Template reuse should be reviewable: first sightings may be tagged, but repeated application should wait until the pattern is stable across multiple documents.
- Changelog entries should distinguish corrected PDF segmentation from parser workflow refinements.

## Open Questions

- Which taxonomy fields should become schema enums versus reviewer-only tags.
- Whether source class, document type, and template type should be stored separately in all generated JSON outputs.
- How much compatibility is required for existing `document_type` and `template_type` values in `toc.json`.

## Sources

- [Council and committee meetings](./README.md)
- [Root wiki schema](../AGENTS.md)

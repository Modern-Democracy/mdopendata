---
type: project
tags:
  - council-meetings
  - committee-meetings
  - workflows
updated: 2026-07-28
---

This page defines the council and committee meeting wiki area for converting zoning and civic-process data into preparation, observation, and follow-up workflows.

# Council and Committee Meetings

## Purpose

This wiki area tracks reusable meeting-preparation knowledge for municipal, regional, and provincial processes. The first implementation target is the May 12, 2026 Charlottetown regular council meeting, using zoning schema data and meeting-document extraction to prepare a public viewer for zoning-related agenda items.

## Audience Workflows

| Audience | Prepare | Observe | Follow up |
| --- | --- | --- | --- |
| Public member | Identify relevant agenda items, source pages, addresses, PIDs, current zones, proposed zones, and decision stage. | Watch the relevant agenda section, note motion wording, amendments, vote result, and any staff/council questions. | Compare against official minutes, update item outcome, and re-check parcel/zoning context after adopted changes are incorporated. |
| Council or committee | Review prior procedural stage, source package, affected properties, zoning/Official Plan implications, and public-facing explanation. | Track conflicts, amendments, staff advice, requested clarifications, and vote result. | Confirm adopted wording, implementation instructions, and items needing further committee or staff action. |
| Municipal staff | Verify package completeness, legal descriptions, PIDs, map references, bylaw references, and process stage. | Capture amendments, deferrals, procedural instructions, and official outcome. | Publish minutes, update bylaw/map status, update structured data, and prepare the next-process record. |

## Current Prototype

The initial prototype is JSON-first, with an added `council` PostgreSQL schema and importer for database-backed endpoint parity. The canonical generated meeting file is `data/council-meetings/charlottetown/2026-05-12-regular-council/meeting.json`, created by `scripts/extract-charlottetown-council-meeting.py` and validated against `schema/json-schema/council-meeting-extraction.schema.json`.

The May 12 package extraction also emits:

- `data/council-meetings/charlottetown/2026-05-12-regular-council/agenda.json`: unified agenda view combining the standalone agenda and package agenda pages, with agenda items and linked package documents.
- `data/council-meetings/charlottetown/2026-05-12-regular-council/toc.json`: logical document table of contents for all 256 package pages, including page counts, summaries, observed boundary basis, template categories where known, document-structure standards, and non-PDF page reproduction options.
- `business_items` in `meeting.json` and `agenda_item_id` / `business_item_id` fields in `toc.json`: reviewable bindings between package documents, the meeting agenda item, and the longer-lived business item record.
- `business_item_evidence`, `business_item_relationships`, and `business_item_candidate_links` in `meeting.json`: durable cross-document identity support for observed identifiers, typed item relationships, and conservative reviewer queues when cross-document matches are not yet confirmed.

The current extraction scope intentionally avoids full package content extraction except for the two rezoning bylaw second-reading items already used by the council-meeting web endpoints. Future reuse of the package segmentation should treat page-boundary rules as reviewable observations, not a universal template.

[Agenda and package document taxonomy](./agenda-document-taxonomy.md) records the initial category catalogue for agenda items, source classes, attachment types, and reusable document workflow templates used by `/document-import`.

The current web route is `/council-meetings`. It reads `GET /api/council-meetings/current` and provides a three-pane meeting workspace:

- left agenda tree in agenda order for public, council, and staff views
- audience-specific general landing page when no item is selected
- selected-item header, source package scroll pane, and right-side context panels when an item is selected

The two zoning bylaw second readings include rezoning tool links to copied meeting-specific endpoints:

- 231 Brackley Point Road, PID 623090, Institutional `I` to Business Park Industrial `M-3`.
- King and Dorchester Streets, PIDs 336974, 336909, 336917, 336966, and 1172915, `DMUN` to `DMS`.

The copied endpoints are `/rezoning-parcel-lookup`, `/rezoning-zoning-comparison`, `/rezoning-restriction-stack`, and `/rezoning-storm-surge`. They preserve the original endpoint code paths for later merge decisions while allowing meeting-specific current/future zone context.

The `/document-import` route uses the same endpoint payload for package review. Its document panel groups package documents into agenda-item panels and exposes editable document title, type, category, page range, agenda item binding, and item-of-business binding fields. It also exposes an agenda hierarchy view with linked documents, a business-item hierarchy view with meeting-local agenda/document appearances, and a candidate-link queue with reviewer accept/reject decisions captured in exported QA feedback.

The general `/agenda-package-ingestion` route can import a completed package into this domain after explicit resolution. Its council-import preview lists active meetings from the same jurisdiction and requires every supporting-document `primary_agenda_item_key` to resolve exactly within the selected existing meeting. The agenda remains unbound, and a supporting document inherits a business-item link only from its resolved agenda item. The import does not create meetings, perform fuzzy matching, infer business-item identity, or publish records.

## Schema Notes

Meeting JSON separates:

- raw PDF source documents and page citations
- agenda sections
- committee reports
- resolutions
- bylaw readings
- planning items
- property and PID references
- zoning amendment references
- audience workflows
- review flags

The `council` database schema follows the existing Charlottetown zoning natural-key, content-hash, supersession, and import-batch conventions. The current database importer is `scripts/import-council-meeting.py`; it imports the May 12 package into normalized council tables while preserving current API payload parity in meeting metadata until endpoint-specific database queries are expanded. Package-level document bindings are stored in `council.package_document`, linked where available to `council.agenda_item` and `council.business_item`.

Generic agenda-package ingestion exposes a read-only binding preview and an explicit transactional import at `GET` and `POST /api/document-ingestion/packages/{packageKey}/council-import`. The import resolves the source by jurisdiction and hash, versions package-document changes, and records import-batch and record-event audit history. Unchanged reruns preserve active package-document IDs.

Durable business-item identity now separates the underlying civic matter from meeting-local appearances. Region-agnostic storage lives in `council.business_item`, `council.business_item_evidence`, `council.business_item_relationship`, `council.business_item_candidate_link`, and `council.business_item_event`; Charlottetown-specific identifier extraction and conservative matching thresholds live in `data/council-meetings/charlottetown/business-item-identity-config.json`. `scripts/build-business-item-identity.py` derives evidence, confirmed same-as links from shared official identifiers, and pending candidate links from weaker property overlap without rewriting issued item IDs.

## Backlog

- Clean up agenda-related blank tables in the PostGIS `public` schema. Confirm which tables are empty, identify whether they were created by meeting extraction experiments or schema bootstrapping, preserve any migration history needed for repeatability, and remove or quarantine the unused tables without affecting current JSON-first meeting outputs.
- Decide whether broader city-portal data should be split into additional schemas such as `core`, `documents`, `property`, `planning`, `finance`, `infrastructure`, `environment`, and `public_services`, or kept as explicit cross-schema links from the existing `council` and `zoning` subject areas. This is tabled until there are source documents and endpoint requirements beyond council meetings and zoning.

## Sources

- [Root wiki schema](../AGENTS.md)
- [Root wiki index](../index.md)
- `docs/charlottetown/council-meetings/05 Regular Meeting of Council Agenda - May 12, 2026.pdf`
- `docs/charlottetown/council-meetings/05 Regular Meeting of Council Package - May 12, 2026.pdf`
- `schema/json-schema/council-meeting-extraction.schema.json`
- `scripts/extract-charlottetown-council-meeting.py`

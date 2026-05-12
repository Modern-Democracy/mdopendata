---
type: project
tags:
  - council-meetings
  - committee-meetings
  - workflows
updated: 2026-05-12
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

The initial prototype is JSON-first and does not add database tables. The canonical generated meeting file is `data/council-meetings/charlottetown/2026-05-12-regular-council/meeting.json`, created by `scripts/extract-charlottetown-council-meeting.py` and validated against `schema/json-schema/council-meeting-extraction.schema.json`.

The current web route is `/council-meetings`. It reads `GET /api/council-meetings/current` and provides public, council, and staff tabs for the two zoning bylaw second readings:

- 231 Brackley Point Road, PID 623090, Institutional `I` to Business Park Industrial `M-3`.
- King and Dorchester Streets, PIDs 336974, 336909, 336917, 336966, and 1172915, `DMUN` to `DMS`.

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

Database migration is deferred. When added, it should follow the existing Charlottetown zoning natural-key, content-hash, supersession, and import-batch conventions.

## Sources

- [Root wiki schema](../AGENTS.md)
- [Root wiki index](../index.md)
- `docs/charlottetown/council-meetings/05 Regular Meeting of Council Agenda - May 12, 2026.pdf`
- `docs/charlottetown/council-meetings/05 Regular Meeting of Council Package - May 12, 2026.pdf`
- `schema/json-schema/council-meeting-extraction.schema.json`
- `scripts/extract-charlottetown-council-meeting.py`

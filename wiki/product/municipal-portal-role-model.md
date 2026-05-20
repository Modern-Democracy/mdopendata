---
type: project
tags:
  - product
  - roles
  - municipal-portal
updated: 2026-05-20
---

This page defines role presets for the municipal portal without creating a permission model.

# Municipal Portal Role Model

## Contract

Role presets filter navigation, labels, panel emphasis, and workflow prompts. They do not authenticate users, hide public data as a security boundary, or authorize writes.

## Presets

| Preset | Primary questions | UI emphasis |
| --- | --- | --- |
| Public | What is happening, where, when, and why does it matter? | Plain-language summaries, source pages, maps, parcel lookup, meeting and business-item status. |
| Applicant/follower | What process applies, what is next, and what evidence is needed? | Item timelines, documents, application or bylaw stage, related parcels, required follow-up. |
| Elected official | What decision is requested and what evidence supports it? | Agenda preparation, source package, affected properties, decisions, staff follow-up. |
| Municipal staff | What must be verified, updated, or published? | Package completeness, minutes, bylaw/map updates, internal implementation checklist. |
| Data validation | What source-to-model gaps remain? | Extraction status, review flags, provenance, schema gaps, API/data contract state. |

## Local-Admin Boundary

Local-admin tools may include review decisions, document-import feedback, or validation corrections. These tools must be labeled separately from role presets and must not be presented as public 1.0 functionality.

## Sources

- [Municipal portal product purpose](./municipal-portal-purpose.md)
- [Council and committee meetings](../council-committee-meetings/README.md)

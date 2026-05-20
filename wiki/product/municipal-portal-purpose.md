---
type: project
tags:
  - product
  - municipal-portal
  - v1
updated: 2026-05-20
---

This page defines the 1.0 product purpose for mdopendata as a Charlottetown municipal public-data portal.

# Municipal Portal Product Purpose

## Product Definition

mdopendata 1.0 is a Charlottetown municipal public-data portal built over ingested public municipal data. It is public-member-led, while still accounting for applicant, elected-official, municipal-staff, and data-validation workflows.

The long-term product remains a full public-data ingestion stack with APIs and useful UI tools across municipalities and domains. Version 1.0 proves the portal model first, not complete ingestion of every domain.

## 1.0 Anchor

The 1.0 anchor is a municipal portal with Charlottetown as the only fully targeted municipality. Schemas, routes, page contracts, and theme conventions should avoid Charlottetown-only assumptions where the extra generality does not add implementation risk.

## Audience Priority

When 1.0 tradeoffs conflict, public-member comprehension wins. Other role views may expose different emphasis, workflow checklists, or local-admin actions, but the base experience must explain what public data exists, what it means, what is missing, and where each claim came from.

## Role Presets

Role presets are view filters, not permissions:

| Preset | Purpose |
| --- | --- |
| Public | Understand municipal business, parcels, bylaws, meetings, maps, and source records. |
| Applicant/follower | Follow or prepare for a business item, application, bylaw change, or municipal process. |
| Elected official | Prepare for agenda items, decisions, source evidence, and follow-up obligations. |
| Municipal staff | Check package completeness, implementation status, and operational data responsibilities. |
| Data validation | Inspect extraction status, review flags, provenance, and source-to-model gaps. |

## Write Scope

Public portal routes are read-oriented for 1.0. Browser-driven review or correction workflows may remain available as local-admin or trusted internal tools, but they are not public permission roles until a later authentication and audit design is approved.

## Sources

- [Root wiki index](../index.md)
- [Council and committee meetings](../council-committee-meetings/README.md)
- [Web UI stack](../implementation/web-ui-stack.md)

---
type: project
tags:
  - product
  - roadmap
  - municipal-portal
  - v1
updated: 2026-05-20
---

This page tracks the 1.0 roadmap for the Charlottetown municipal portal.

# Municipal Portal 1.0 Roadmap

## Release Shape

Version 1.0 should ship a portal shell, role-preset filtering, domain route stubs, and functional links into mature existing workflows. It should also identify which data domains are contract-only and which are backed by current APIs.

## Route Map

| Area | Route | 1.0 status |
| --- | --- | --- |
| Home | `/` | Portal shell and domain overview. |
| Meetings | `/meetings` and `/council-meetings` | Stub plus current May 12 meeting workspace. |
| Business items | `/business-items` | Contract stub for durable municipal matters. |
| Documents | `/documents` and `/document-import` | Stub plus local-admin document-import prototype. |
| Planning and land use | `/planning` plus parcel/zoning routes | Stub plus parcel lookup, map, zoning comparison, provisions comparison, and restrictions. |
| Budgets | `/budgets` | Contract stub using the budget data model as planning input. |
| Maps | `/maps` and `/city-view` | Stub plus current Leaflet city map. |
| Validation | `/validation` | Contract stub for extraction/data QA; local-admin only for write paths. |
| Lab tools | `/lab`, `/parcel-3d`, `/storm-surge` | Lab index plus demo-only 3D and storm-surge tools. |

## Ordered Work

1. Establish durable product wiki pages and route map.
2. Add a React/Babel portal shell with role presets, municipal theme loading, and page-contract stubs.
3. Add the basic-HTML feasibility study as a blocking task before new reusable component coding.
4. Migrate existing functional pages into the portal navigation model without changing their current API contracts.
5. Convert stubs into functional pages only after each domain has a documented API/data contract.

## Backlog

| Task | Status | Notes |
| --- | --- | --- |
| Portal shell | Started | React/Babel route shell with role presets and stubs. |
| Municipal theming | Started | Charlottetown theme stylesheet is the first swappable theme. |
| Basic HTML feasibility study | Planned | Must be completed before new reusable component coding. |
| Existing page migration | Planned | Keep current functional routes stable during migration. |
| Public/staff write boundary | Planned | Public routes stay read-oriented; local-admin write tools need explicit labels. |
| Domain API contracts | Planned | Required before turning stubs into functional pages. |

## Acceptance Criteria

- The portal shell loads at `/`.
- Role presets change visible emphasis without implying authentication.
- Each stub declares purpose, inputs, outputs, states, API contract, and unavailable-data behavior.
- Existing mature routes continue to load.
- Lab tools are separated from core public navigation and retain demo-only status.
- The feasibility study produces a recommendation before new reusable component coding begins.

## Sources

- [Municipal portal product purpose](./municipal-portal-purpose.md)
- [Municipal portal role model](./municipal-portal-role-model.md)
- [Municipal portal UI architecture](./municipal-portal-ui-architecture.md)
- [Municipal portal domain inventory](./municipal-portal-domain-inventory.md)

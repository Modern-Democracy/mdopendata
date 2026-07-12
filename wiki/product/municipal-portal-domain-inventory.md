---
type: project
tags:
  - product
  - domains
  - municipal-portal
updated: 2026-07-12
---

This page inventories 1.0 municipal portal domains and their current implementation depth.

# Municipal Portal Domain Inventory

## Domains

| Domain | Current depth | 1.0 treatment |
| --- | --- | --- |
| Meetings | JSON and database-backed current prototype. | Functional route plus portal stub summary. |
| Business items | Emerging from meeting extraction. | Contract stub for durable civic matters across meetings. |
| Documents | Document-import prototype and extraction schemas. | Stub plus local-admin document import route. |
| Planning and land use | Strongest current domain: parcels, zoning, bylaws, maps, comparison APIs. | Functional route family plus portal stub summary. |
| Budgets | Published three-document snapshot, read APIs, capital-project APIs, exact-identity comparisons, source-page rendering, CSV export, and accessible visualization page. | Retain published-snapshot isolation; add normalized-category comparison and source-cell overlays later. |
| Maps | Leaflet city map plus parcel/zoning APIs. | Functional city-view link and map-domain stub. |
| Validation | Existing extraction review patterns and smoke checks. | Contract stub plus local-admin boundary. |
| Lab tools | Parcel 3D and storm-surge demos. | Lab-only routes with demo caveats. |

## Domain Contract Rule

Do not turn a stub into a functional 1.0 page until the page has an explicit source/data contract and unavailable-data behavior. Existing functional pages may continue using their current contracts while migration planning continues.

## Sources

- [Council and committee meetings](../council-committee-meetings/README.md)
- [Municipal budget data model](../implementation/municipal-budget-data-model.md)
- [Municipal budget contracts](../budgets/README.md)
- [Web demo design kit plan](../implementation/web-demo-design-kit-plan.md)

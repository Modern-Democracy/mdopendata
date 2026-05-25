---
type: source
tags:
  - source
  - municipal-governance
  - labour-relations
  - workforce
  - operations
  - lgbc
updated: 2026-05-25
---

This page records the Chapter 11 review of `docs/LGBC-All.pdf` for local-government labour relations, unionization, bargaining units, workforce context, and municipal data needs.

# Chapter 11: Labour Relations

## Source Locator

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Unit id | `chapter_11` |
| Visible pages | 173-178 |
| PDF pages | 186-191 |
| Sections | 11.1 through 11.4 |
| Related exhibits | `11-1`, `11-2`, `11-3`, `11-4` |

## Source Claims

Chapter 11 states that BC local-government labour relations come under the same labour legislation as the private sector, unlike federal and provincial government employees, and that labour relations affect the efficiency and responsiveness of local-government service delivery.

The policy framework section identifies local-government employment powers, officer employment rules, the Employment Standards Act, the Labour Relations Code, Labour Relations Board processes, essential-service designation, and the Fire and Police Services Collective Bargaining Act.

The unionization section states that municipalities, school districts, and regional districts employed approximately 96,949 people in 2007, including management, and that approximately 87,749 were unionized. It reports estimated unionization of 90.5 percent across municipalities, school districts, and regional districts in 2007.

The chapter identifies CUPE and the BC Teachers' Federation as the largest unions representing local-government employees in the source context, and notes that many local governments bargain with several unions.

The chapter states that bargaining units are typically small and that employer associations are used by some municipalities and regional districts for labour-relations and bargaining purposes.

The private-market labour-law section emphasizes that public-sector work stoppages differ from private-sector stoppages because public services cease to be available while citizens may continue paying taxes. It also notes that essential fire and police services are handled differently through arbitration.

The summary states that public-sector labour relations differ from private-sector labour relations because service cessation can be serious, leading to essential-service designation and dispute-resolution modifications.

## Exhibits

| Exhibit | Title | Source use |
| --- | --- | --- |
| `11-1` | Change in Total Employees and Unionized Employees in Local Government 1982-2007 | Provides aggregate employee and union-member change over time. |
| `11-2` | Local Government Unionization | Provides employee, union-member, and unionization estimates by municipalities, school districts, and regional districts. |
| `11-3` | Unions Representing Local Government Employees | Provides union names and estimated local-government-related membership. |
| `11-4` | Sizes of Bargaining Units in the Greater Vancouver Regional District in 2004 | Provides bargaining-unit size distribution example. |

## Benchmark And Process Candidates

These candidates are review prompts, not approved schemas or scoring models.

| Candidate | Source basis | Municipal inputs required | Comparison mode | Status |
| --- | --- | --- | --- | --- |
| Workforce and unionization profile | `direct_source`: section 11.2 and Exhibits `11-1`, `11-2` | Employee counts, FTEs, union membership, management counts, department, employment type, year | longitudinal comparison | candidate |
| Collective agreement inventory | `direct_source`: sections 11.1, 11.2 | Collective agreements, union locals, expiry dates, bargaining unit coverage, essential-service clauses, settlement terms | source-completeness review | candidate |
| Bargaining-unit map | `direct_source`: section 11.2 and Exhibit `11-4` | Bargaining units, union local, covered positions, member counts, employer association participation | source-completeness review | candidate |
| Labour-relations governance map | `direct_source`: section 11.1 | Officer roles, council authorities, HR policies, labour-board decisions, employment standards references, arbitration records | source-completeness review | candidate |
| Service-continuity labour-risk review | `direct_source`: sections 11.1, 11.3, 11.4 | Essential-service designations, strike/lockout records, contingency plans, affected services, public notices | benchmark against stated local objective | candidate |
| Labour-cost service linkage | `derived_from_source`: sections 11.2, 11.3 | Wage schedules, benefits, overtime, payroll costs, departments, service outputs, contract costs | longitudinal comparison | candidate |
| Bargaining capacity review | `direct_source`: section 11.3 | Use of employer associations, external negotiators, bargaining mandates, council approvals, HR staffing | source-completeness review | candidate |
| Contracting and workforce boundary review | `derived_from_source`: sections 11.2, 11.3 | Contracted services, union jurisdiction, internal workforce counts, procurement records, service levels | local alternative comparison | candidate |

## Charlottetown Prototype Implications

Chapter 11 supports an operations and workforce context layer rather than a public-facing performance score. Labour relations can explain service cost, continuity risk, staffing constraints, and contract-vs-own-forces choices.

For Charlottetown, the immediate prototype should focus on:

- Building a workforce and collective-agreement inventory with source dates and coverage metadata.
- Separating municipal employees from school, provincial, regional, nonprofit, and contractor workforces.
- Linking labour data to service domains only after roles, departments, and bargaining units are clear.
- Treating wage or unionization comparisons as context-sensitive because job descriptions, service levels, and outsourced work can differ.
- Recording essential-service and service-continuity constraints for police, fire, and other public-facing services where source documents support them.

Chapter 11 should inform internal analysis workflows and contextual notes around service delivery, not standalone public rankings.

## Required Data Inventory

| Data class | Purpose |
| --- | --- |
| Workforce records | Supports employee count, FTE, department, position, employment type, and time-series review. |
| Union and bargaining-unit records | Supports unionization, bargaining-unit size, local affiliation, and coverage mapping. |
| Collective agreements | Supports agreement inventory, expiry tracking, settlement context, wages, benefits, and work-rule review. |
| HR policy and officer records | Supports governance mapping for employment powers, officer roles, suspension, termination, and council authority. |
| Labour-relations event records | Supports strike, lockout, mediation, arbitration, grievance, labour-board, and essential-service review. |
| Payroll and benefits records | Supports labour-cost trend review and service-domain cost linkage. |
| Contract and procurement records | Supports own-forces versus contracted-service boundary analysis. |
| Service-continuity records | Supports public-service impact, emergency coverage, and essential-service planning review. |

## Review Limits

Chapter 11 is BC-specific and reflects labour legislation, union patterns, and data estimates as of 2008. Charlottetown or PEI use requires separate labour-law and institutional mapping.

The source contains useful workforce and bargaining context, but it does not define a municipal performance standard for unionization, wage levels, bargaining-unit size, or service continuity.

Personnel, payroll, labour-relations, and bargaining records may include sensitive or restricted information. Public portal use should be limited to source-supported aggregate context unless disclosure rules are reviewed.

## Sources

- `docs/LGBC-All.pdf`, Chapter 11, visible pages 173-178, PDF pages 186-191.
- [Local Government in British Columbia source summary](../lgbc-local-government-bc.md)
- [Chapter 6: Service Delivery](./chapter-6-service-delivery.md)
- [Chapter 7: Protective Services](./chapter-7-protective-services.md)
- [Local Government in British Columbia ingestion plan](../../../plan/lgbc-ingestion-plan.md)

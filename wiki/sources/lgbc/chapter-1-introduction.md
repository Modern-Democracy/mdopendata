---
type: source
tags:
  - source
  - municipal-governance
  - fiscal-equivalence
  - performance
  - lgbc
updated: 2026-05-25
---

This page records the Chapter 1 review of `docs/LGBC-All.pdf` for local-government purpose, fiscal equivalence, evaluation criteria, and municipal data needs.

# Chapter 1: Introduction

## Source Locator

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Unit id | `chapter_1` |
| Visible pages | 1-10 |
| PDF pages | 14-23 |
| Sections | 1.1 through 1.6 |
| Related exhibits | `1-1` |

## Source Claims

Chapter 1 frames local government as a set of institutions that let citizens resolve local collective problems and provide goods and services more responsively and efficiently than a provincial government could, while operating inside provincial legislative authority.

The chapter rejects evaluating local government only by citizen participation or only by production efficiency. It treats participation as part of economic efficiency because citizens need mechanisms to express preferences and balance benefits against costs.

The chapter defines fiscal equivalence as the criterion that decision makers should balance benefits to constituents against costs imposed on those constituents through taxes, service charges, and regulatory compliance.

The chapter distinguishes system-level evaluation from service, program, and capital-investment evaluation. It points to Chapter 6 for technical efficiency, engineering efficiency, cost-effectiveness, performance measures, program evaluation, and cost-benefit analysis.

The chapter identifies collective-problem types that local government may address: public goods, external effects, common-pool resources, utilities, business regulation, and welfare-related local impacts.

The chapter defines local government for the book as a government other than federal or provincial government that has territorial jurisdiction, locally elected public officials, and property-taxing power under provincial legislation.

The chapter describes a polycentric, multigovernmental system with multiple local-government types and overlapping service relationships.

## Exhibit

| Exhibit | Title | Source use |
| --- | --- | --- |
| `1-1` | Local Governments in British Columbia | Provides a government-type inventory across 1999, 2005, and 2008 for municipalities, regional districts, special-purpose bodies, and total local governments. |

## Benchmark And Process Candidates

These candidates are review prompts, not approved schemas or scoring models.

| Candidate | Source basis | Municipal inputs required | Comparison mode | Status |
| --- | --- | --- | --- | --- |
| Fiscal-equivalence review | `direct_source`: section 1.2 | Tax, fee, service-charge, regulatory-cost, service-benefit, and affected-population records | fiscal-equivalence review | candidate |
| Local-government definition mapping | `direct_source`: section 1.4 | Governance body, territorial jurisdiction, election method, taxing authority, enabling legislation | source-completeness review | candidate |
| Collective-problem classification | `direct_source`: section 1.3 | Service catalogue, regulatory functions, infrastructure assets, public-goods and external-effect evidence | source-completeness review | candidate |
| Participation and decision-channel inventory | `direct_source`: sections 1.1 and 1.2 | Elections, referenda, hearings, meetings, complaints, volunteer bodies, advisory bodies | source-completeness review | candidate |
| Benefit-cost accountability trace | `direct_source`: sections 1.2 and 1.5 | Council decisions, cost estimates, affected beneficiaries, funding source, compliance burden | source-completeness review | candidate |
| Polycentric governance map | `direct_source`: sections 1.2 and 1.4 | Municipal, regional, special-purpose, provincial, and volunteer/quasi-governmental actors | source-completeness review | candidate |
| Local-government risk/caution review | `direct_source`: section 1.5 | Promises, project monitoring evidence, reporting completeness, decision records, accountability controls | source-completeness review | candidate |
| Municipal source-domain orientation | `direct_source`: section 1.6 | Chapter-to-domain mapping, current portal domain inventory, available municipal datasets | source-completeness review | candidate |

## Charlottetown Prototype Implications

Chapter 1 supports a portal workflow that explains what kind of public problem a municipal dataset or process relates to before trying to evaluate performance.

For Charlottetown, the immediate prototype should focus on:

- Mapping municipal services and regulations to collective-problem categories.
- Showing who pays, who benefits, and who must comply for a decision or service.
- Recording which decision channel produced the policy, service, or regulation.
- Distinguishing local municipal action from provincial authority or regional/special-purpose delivery.
- Treating public data gaps as accountability and source-completeness findings before treating them as performance failures.

The chapter does not justify importing BC local-government categories directly into Charlottetown or PEI. Its value is the evaluation frame: benefits, costs, decision authority, service type, and governance relationships.

## Required Data Inventory

| Data class | Purpose |
| --- | --- |
| Governance and authority records | Identifies council, boards, committees, statutory authority, and decision pathways. |
| Service and regulation catalogue | Connects municipal activities to public goods, external effects, common pools, utilities, business regulation, or welfare-related impacts. |
| Revenue and charge records | Supports fiscal-equivalence review through taxes, service charges, fees, and special assessments. |
| Beneficiary and affected-party records | Identifies who receives benefits and who bears costs or compliance obligations. |
| Public participation records | Captures elections, referenda, hearings, meetings, complaints, advisory bodies, and volunteer/co-production channels. |
| Project and decision monitoring records | Supports review of promises, implementation status, costs, and delivered outcomes. |
| Intergovernmental relationship records | Distinguishes local, regional, provincial, federal, First Nations, and special-purpose responsibilities. |

## Review Limits

Chapter 1 is BC-specific and uses a definition of local government based partly on property-taxing authority under provincial legislation. Charlottetown or PEI jurisdiction mapping requires separate review.

Chapter 1 provides an evaluation frame but does not define final metrics, thresholds, scoring methods, or public grades.

## Sources

- `docs/LGBC-All.pdf`, Chapter 1, visible pages 1-10, PDF pages 14-23.
- [Local Government in British Columbia source summary](../lgbc-local-government-bc.md)
- [Chapter 6: Service Delivery](./chapter-6-service-delivery.md)
- [Local Government in British Columbia ingestion plan](../../../plan/lgbc-ingestion-plan.md)

---
type: source
tags:
  - source
  - municipal-governance
  - protective-services
  - police
  - fire
  - emergency-management
  - lgbc
updated: 2026-05-25
---

This page records the Chapter 7 review of `docs/LGBC-All.pdf` for protective services, police, fire, emergency protection, performance measures, and municipal data needs.

# Chapter 7: Protective Services

## Source Locator

| Field | Value |
| --- | --- |
| Source file | `docs/LGBC-All.pdf` |
| Unit id | `chapter_7` |
| Visible pages | 97-114 |
| PDF pages | 110-127 |
| Sections | 7.1 through 7.4 |
| Related exhibits | `7-1`, `7-2` |

## Source Claims

Chapter 7 defines protective services broadly, but focuses on police protection, fire protection, and emergency protection. Ambulance service is identified as provincially provided in British Columbia, while regulatory functions and public health are handled in other chapters.

The chapter describes police protection as a public good with diverse activities: patrol, crime prevention, investigation, traffic enforcement, dispatch, information systems, detention, forensic laboratories, police academies, distress assistance, crowd control, emergency planning, and crime-prevention advice.

The chapter states that police performance is hard to evaluate because policing involves face-to-face interaction, citizen trust, unreported incidents, classification differences, and environmental variables outside police control.

The chapter identifies important police context variables: household size, family income, median age, population density, home ownership, housing type, length of residence, and nonresidential property composition.

The chapter treats fire protection as a public good with fire inspection, suppression, prevention education, investigation, emergency response, and hazardous-materials response. Fire performance is easier to measure than police performance, but still depends on local environment.

The chapter identifies response time as a key fire output measure, while warning that response time should be combined with environmental, input, output, outcome, and cost-effectiveness measures.

The chapter treats emergency protection as a public good involving prevention, preparedness, response, and recovery. Preparedness quality, response time, treatment of affected residents, and recovery performance are central review areas.

## Exhibits

| Exhibit | Title | Source use |
| --- | --- | --- |
| `7-1` | Independent Municipal Police Departments in B.C. | Provides police-organization inventory context for independent departments. |
| `7-2` | Fire Service Performance Measures | Provides direct seed categories for environmental, input, output, outcome, and cost-effectiveness fire measures. |

## Benchmark And Process Candidates

These candidates are review prompts, not approved schemas or scoring models.

| Candidate | Source basis | Municipal inputs required | Comparison mode | Status |
| --- | --- | --- | --- | --- |
| Police service arrangement inventory | `direct_source`: section 7.1 | Police provider, contracts, boards/committees, staffing, cost-share arrangements, service area | source-completeness review | candidate |
| Police environmental context profile | `direct_source`: section 7.1 | Population, density, income, age, homeownership, housing type, tenure, nonresidential property mix | source-completeness review | candidate |
| Police agency-statistics caution review | `direct_source`: section 7.1 | Reported crimes, clearance rates, calls for service, classification rules, UCR data notes | source-completeness review | candidate |
| Police survey-readiness review | `direct_source`: section 7.1 | Citizen survey availability, victimization, reporting, assists, stops, follow-up, trust indicators | source-completeness review | candidate |
| Police cost-effectiveness candidate | `direct_source`: section 7.1 | Police cost, officer count, patrol staffing, reported crimes, cleared cases, context variables | longitudinal or cross-sectional comparison | candidate |
| Fire performance measure inventory | `direct_source`: section 7.2 and Exhibit `7-2` | Fire incidents, alarms, response times, inspections, education visits, property losses, costs | benchmark against stated local objective | candidate |
| Fire environmental context profile | `direct_source`: Exhibit `7-2` | Housing units, housing age, assessed value, population, jurisdiction area | source-completeness review | candidate |
| Fire cost-effectiveness candidate | `direct_source`: Exhibit `7-2` | Fire suppression cost, inspection/prevention cost, medical response cost, hazmat cost, output counts | longitudinal or cross-sectional comparison | candidate |
| Fire insurance value comparison | `direct_source`: section 7.2 | Fire-service taxes/costs, estimated insurance with and without service, property values | requires_external_standard | candidate |
| Emergency preparedness completeness review | `direct_source`: section 7.3 | Emergency plan, bylaws, mutual aid, resource inventory, warning procedures, exercises, communications | source-completeness review | candidate |
| Emergency response performance review | `direct_source`: section 7.3 | Incident records, response time, EOC activation, resident assistance, recovery costs, citizen feedback | longitudinal comparison | candidate |
| Protective-service production map | `direct_source`: section 7.4 | Direct producers, indirect producers, contracts, joint arrangements, volunteers, provincial/federal links | source-completeness review | candidate |

## Charlottetown Prototype Implications

Chapter 7 supports protective-service portal work, but it also warns that protective-service performance claims require context and multiple evidence sources.

For Charlottetown, the immediate prototype should focus on:

- Identifying protective-service providers, contracts, service boundaries, and intergovernmental responsibilities.
- Separating source availability from performance judgment.
- Capturing police and fire data definitions before comparing rates or response times.
- Pairing agency statistics with environmental context and, where available, citizen survey evidence.
- Treating emergency planning as a document and preparedness inventory before assessing response outcomes.

Police comparisons should not use single indicators such as reported crime rates or clearance rates without context. Fire measures are more directly usable, especially response time and cost-effectiveness measures, but still require local environmental controls.

## Required Data Inventory

| Data class | Purpose |
| --- | --- |
| Police provider and governance records | Identifies provider type, contracts, oversight body, service area, and responsibility split. |
| Police agency statistics | Supports reported crime, calls, clearance, cost, and staffing measures with definition caveats. |
| Police environmental context data | Controls for demographic, housing, density, and land-use conditions. |
| Citizen survey and victimization data | Supports evaluation beyond reported agency data. |
| Fire incident records | Supports alarms, fire types, response time, losses, and outcome measures. |
| Fire inspection and prevention records | Supports inspection, education, prevention, and cost-effectiveness analysis. |
| Fire cost and staffing records | Supports input and cost-effectiveness measures. |
| Emergency plans and preparedness records | Supports preparedness completeness review. |
| Emergency incident and recovery records | Supports response and recovery review. |
| Mutual aid and interagency records | Supports protective-service production mapping. |

## Review Limits

Chapter 7 is BC-specific and includes BC policing, RCMP, fire, and emergency-management arrangements as of 2008. Charlottetown or PEI protective-service mapping requires separate review.

The chapter provides direct fire-measure categories but does not provide enough evidence to define Charlottetown police, fire, or emergency benchmarks without local source data.

Police performance comparison requires special caution because reported statistics depend on citizen reporting, classification practices, trust, environment, and service mix.

## Sources

- `docs/LGBC-All.pdf`, Chapter 7, visible pages 97-114, PDF pages 110-127.
- [Local Government in British Columbia source summary](../lgbc-local-government-bc.md)
- [Chapter 6: Service Delivery](./chapter-6-service-delivery.md)
- [Local Government in British Columbia ingestion plan](../../../plan/lgbc-ingestion-plan.md)

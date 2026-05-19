# Municipal Document Taxonomy

Use this reference when classifying municipal document families, document types, section types, page templates, and attachment classes.

## Document Families

- `bylaw`: enacted, draft, amending, consolidated, or reading-stage bylaw material.
- `agenda_package`: agenda, package, attachments, motions, resolutions, staff reports, maps, correspondence, and received submissions bundled for a meeting.
- `report`: staff, committee, consultant, monthly, financial, infrastructure, planning, or service report.
- `minutes`: draft or adopted meeting minutes.
- `resolution`: formal council or committee resolution cover, body, signature, or voting page.
- `correspondence`: email, letter, public submission, applicant submission, petition, or external-body submission.
- `map_plan`: map, site plan, survey, drawing, legend, schedule, zoning map, or concept plan.
- `permit_activity`: permit list, development activity list, enforcement list, or tabular application list.
- `other`: uncategorized, duplicate, blank separator, scan artifact, or parser review item.

## Section Types

Common section types include:

- cover
- table_of_contents
- agenda_item
- report_summary
- recommendation
- background
- analysis
- financial_implication
- public_consultation
- motion_text
- bylaw_clause
- schedule
- map_or_plan
- correspondence_body
- attachment
- signature_or_approval
- appendix
- blank_or_separator

## Page Templates

Common page templates include:

- `resolution-cover`
- `resolution-text`
- `committee-report-cover`
- `staff-report`
- `minutes`
- `map-or-plan`
- `correspondence`
- `permit-or-activity-list`
- `bylaw-clause-page`
- `bylaw-schedule`
- `agenda-page`
- `other-template`

## Classification Rules

- Preserve source labels and titles exactly before normalization.
- Classify source class, document type, section type, and page template separately when possible.
- Treat municipality-specific labels as raw evidence until a cross-municipal normalization rule is approved.
- Use `other` or `needs_review` when the source does not fit a known type.

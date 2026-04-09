# Architecture

## Direct answer

To support land-use and development queries that also reflect council and committee activity, the datastore should treat regulations, maps, and meetings as linked but separate records joined through geometry, addresses, parcels, and citations.

## Core entities

### Sources and citations

- `documents`: one row per PDF, image, or future external source
- `document_pages`: page-level metadata and optional page images
- `text_spans`: extracted text chunks with page number, bounding box, and citation anchors

### Spatial controls

- `spatial_features`: zoning districts, future land use areas, wards, neighborhoods, truck routes, parks, and other mapped layers
- `parcels`: parcel fabric from external cadastral data
- `addresses`: civic addresses and normalized street references

### Rules and permissions

- `land_use_rules`: one atomic rule per use, metric, or development control
- `rule_applicability`: links rules to zones, overlays, plan areas, or citywide applicability

Examples:

- principal permitted use
- conditional use
- minimum lot area
- front yard setback
- building height
- parking ratio
- signage restriction

### Municipal business

- `meetings`: council and committee meetings
- `agenda_items`: meeting agenda items and minutes sections
- `decisions`: motions, votes, referrals, approvals, denials, and follow-up actions
- `topics`: normalized subjects such as rezoning, subdivision, variance, capital project, heritage, traffic, or park planning

## Required relationships

The useful queries depend on these links:

- parcel intersects zoning polygon
- parcel intersects future land use polygon
- parcel belongs to ward and neighborhood
- meeting item references a parcel, address, street, zone, or policy section
- decision cites bylaw sections or official plan policies

## Query patterns to support

### Parcel-first

Input:

- PID
- address
- lat/lon

Output:

- zoning district
- future land use designation
- applicable rules
- cited bylaw and plan sections
- related council or committee items

### Topic-first

Input:

- rezoning
- parking
- downtown
- accessory dwelling unit

Output:

- relevant bylaw sections
- relevant policy sections
- meetings and decisions discussing the topic
- affected areas or parcels if spatial references are available

### Meeting-first

Input:

- council date
- committee name
- agenda item title

Output:

- linked addresses, parcels, streets, or map areas
- cited policies and zoning provisions
- resulting decision and status

## Extraction rules

### Bylaw and official plan PDFs

Extract:

- headings and section hierarchy
- tables
- numbered clauses
- definitions
- use lists

Normalize to atomic rules with citation spans.

### Map PDFs

Extract:

- polygon and line layers if embedded
- legends
- labels
- map title, revision date, scale, and projection if available

If vector extraction fails, georeference a rendered image and digitize key layers.

### Images

Use OCR plus manual quality checks for legends and labels.

## Current repository limitations

- No meeting documents are present
- No permit or application records are present
- No parcel geometry is present
- No extractor toolchain is installed

This means the current repository can define the model and inventory the sources, but not yet produce a fully searchable knowledge base without additional data and dependencies.

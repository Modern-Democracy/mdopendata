---
name: role-data-engineer
description: Use when work requires ETL pipeline development or operation for PDF parsing, document extraction, normalization, structured data generation, repeatable imports, PostGIS ingestion, schema-aware transformations, or data workflow automation.
metadata:
  short-description: Build and run ETL workflows
---

# Data Engineer

Use this role for repeatable data extraction, transformation, loading, and ingestion mechanics.

## Objective

Build or run reliable data pipelines that convert source documents and spatial inputs into normalized files, database-ready records, and PostGIS-ingested data within approved schemas and workflow constraints.

## Workflow

1. Identify source inputs, generated outputs, schemas, pipeline scripts, import targets, and rerun constraints.
2. Read the wiki pages identified by `Project Management`, and use `wiki/index.md` to find additional relevant project, domain, implementation, or source-summary context.
3. Confirm requirements, schema semantics, compatibility rules, and accepted source-pattern variation are already explicit.
4. Prefer existing extraction, normalization, validation, and import scripts before adding new tooling.
5. Preserve raw source text, raw labels, provenance, and stable identifiers needed for auditability.
6. Make transformations deterministic and rerunnable.
7. Validate counts, required fields, keys, links, schema conformance, and import readiness.

## Pipeline Rules

- Do not decide zoning semantics, category meanings, or acceptable source variation without `Business Analyst`.
- Do not create new schema shapes, workflow architecture, parser frameworks, or import protocols without `Coding Architect`.
- For PDF extraction, separate raw extraction artifacts from normalized query fields.
- For PostGIS ingestion, keep load order, SRIDs, geometry columns, indexes, constraints, and schema names explicit.
- For bulk regeneration, compare outputs against the approved change surface and flag out-of-scope diffs.

## Boundaries

- Route unresolved interpretation or acceptance criteria to `Business Analyst`.
- Route new pipeline, schema, helper, protocol, or workflow design to `Coding Architect`.
- Route spatial validity, CRS, alignment, or spatial SQL questions to `GIS Specialist`.
- Route source-fidelity or cross-system validation to `Data Quality Analyst`.
- Route to `Debugger` when extraction, transformation, or ingestion fails without a discriminating cause.
- Route to `QA Reviewer` for final acceptance after implementation.

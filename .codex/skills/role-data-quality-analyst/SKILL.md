---
name: role-data-quality-analyst
description: Use when work requires validating normalized data against source documents, checking source fidelity, identifying data completeness issues, confirming controlled vocabularies, validating spatial integrity across generated files and databases, or producing quality findings before final QA review.
metadata:
  short-description: Validate source fidelity and data quality
---

# Data Quality Analyst

Use this role for evidence-based validation of extracted, normalized, imported, and spatial data against source material and project data standards.

## Objective

Detect and report data quality issues before final acceptance by checking whether generated records faithfully represent source documents, approved schemas, controlled vocabularies, and spatial relationships.

## Workflow

1. State the quality claim being checked and the source material or system of record.
2. Identify the exact records, fields, clauses, zones, geometries, or database tables under validation.
3. Compare normalized values against raw source text, raw labels, source maps, or canonical imported records.
4. Use positive controls for expected values and negative controls for nearby non-target values.
5. Classify issues as source ambiguity, extraction error, normalization error, schema mismatch, spatial integrity issue, or import inconsistency.
6. Report evidence, affected identifiers, severity, and whether the issue blocks acceptance.

## Quality Checks

- Validate required fields, nullability, uniqueness, code tables, controlled terms, source citations, raw label preservation, and normalized-field derivation.
- For by-law extraction, verify raw clause labels are preserved exactly and compact labels are not split incorrectly.
- For spatial data, check cross-system consistency of feature counts, identifiers, geometry validity, SRIDs, coverage, overlaps, gaps, and parcel/zoning relationships.
- For generated data, inspect diffs for out-of-allowlist changes and verify that nearest similar records remain unchanged.

## Boundary With QA Reviewer

`Data Quality Analyst` performs domain data validation and produces findings. `QA Reviewer` performs final acceptance of an implementation or verification claim.

Use `Data Quality Analyst` before final QA when source fidelity, normalized data correctness, spatial integrity, or cross-system data consistency needs detailed evidence. Use `QA Reviewer` to decide whether the completed work satisfies the requested acceptance claim after implementation and specialist validation are complete.

## Boundaries

- Route to `Business Analyst` when quality findings depend on unresolved policy meaning, acceptable variation, or data-standard interpretation.
- Route to `Coding Architect` when quality findings imply schema redesign, workflow redesign, or architectural changes.
- Route to `Data Engineer` when quality findings require pipeline or ingestion changes.
- Route to `GIS Specialist` when quality findings require GIS-specific spatial analysis or QGIS/PostGIS spatial operations.
- Route to `Debugger` when a suspected defect lacks a discriminating cause.
- Route to `QA Reviewer` for final acceptance after quality findings are resolved or documented.

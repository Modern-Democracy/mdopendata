---
name: role-business-analyst
description: Use when repository work is ambiguous, requirement-heavy, behavior-changing, or depends on template-fit, schema, compatibility, acceptable variation, scenarios, or edge-case clarification before coding.
metadata:
  short-description: Clarify requirements before implementation
---

# Business Analyst

Use this role when requirements are not explicit enough to code safely.

## Objective

Convert an ambiguous request into explicit implementation criteria, accepted variations, and stop conditions.

## Workflow

1. Restate the requested outcome and current uncertainty.
2. Identify decisions that would change data shape, behavior, schema, workflow, or downstream compatibility.
3. Separate direct requirements from assumptions.
4. Identify source-pattern variations that may affect bulk work.
5. Ask only the minimum questions needed to proceed safely.

## Template-Fit Questions

For template-based extraction or transformation, clarify:
- which fields are mandatory
- which fields may be omitted when the source does not fit
- whether legacy compatibility fields are allowed
- whether to stop on material mismatches or emit review records
- what counts as light variation versus material variation
- whether normalized query fields should be generated only from directly supported source patterns

## Code-Table and Category Questions

For code-table, term, use, category, schema enum, or normalized assignment changes:
- Identify the exact codes or identifiers that are in scope.
- Identify similar or adjacent codes that are explicitly out of scope when they could be affected by the same text pattern.
- Clarify whether new codes should be `active` or `review`.
- Do not infer that a category change for one code applies to related codes.

Do not transition to implementation until requirements, scenarios, and edge cases are explicit enough to code safely.

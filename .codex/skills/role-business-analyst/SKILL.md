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
2. Identify decisions that would change data shape, behavior, schema, workflow, or compatibility.
3. Separate direct requirements from assumptions.
4. Identify source-pattern variations that may affect bulk work.
5. Ask only the minimum questions needed to proceed safely.

## Template-Fit Questions

For template-based extraction or transformation, clarify:
- which fields are mandatory
- what may be omitted when the source does not fit
- whether compatibility fields or review records are allowed
- what counts as light versus material variation

## Code-Table and Category Questions

For code-table, term, use, category, schema enum, or normalized assignment changes:
- Identify the exact codes or identifiers that are in scope.
- Clarify whether new codes should be `active` or `review`.
- Identify nearby non-target codes when the same pattern could affect them.

Do not transition to implementation until requirements, scenarios, and edge cases are explicit enough to code safely.

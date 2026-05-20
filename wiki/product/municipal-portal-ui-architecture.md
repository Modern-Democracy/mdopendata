---
type: implementation
tags:
  - product
  - web-ui
  - municipal-portal
updated: 2026-05-20
---

This page defines the first 1.0 UI architecture for the municipal portal and the feasibility gate for a later basic-HTML approach.

# Municipal Portal UI Architecture

## Current Stack

Keep the current React/Babel page pattern for 1.0 planning and shell work while the reusable component contract settles. Do not build a large shared component library until the basic-HTML feasibility study has compared the component contract in React/Babel and basic HTML/CSS/first-party JavaScript.

Leaflet and Three.js remain acceptable only for map, parcel-3D, and lab-style pages. The server-side Node web service remains the database and API boundary.

## Page Context Contract

Portal pages should be able to read a stable context object with:

- `municipality`
- `theme`
- `rolePreset`
- `route`
- `selectedEntity`
- `sourceStatus`
- `availableActions`

Pages may use this context to populate headings, role-specific workflow text, domain cards, and action links. It is not an authorization object.

## Stub Page Contract

Every 1.0 stub must declare:

- purpose
- required context data
- expected API inputs
- expected outputs
- loading, empty, error, and unavailable-data states
- provenance expectations
- whether any write path is public, local-admin, or unavailable

## Theming

Themes are CSS stylesheets layered over semantic tokens. The first supported stylesheet is the Charlottetown municipal theme. Page HTML should not encode municipality-specific colors directly when a semantic token can express the role.

## Basic-HTML Feasibility Study

Before major reusable component buildout, run a feasibility study that:

1. Selects one representative component family from the component architecture, preferably `Page contract` or `Status and provenance`.
2. Implements or sketches the same behavior in current React/Babel and basic HTML/CSS/first-party JavaScript.
3. Compares theming, context data binding, component reuse, accessibility, testability, migration cost, and maintainability.
4. Recommends one of: stay React/Babel, migrate gradually, or switch before 1.0 component buildout.

## Sources

- [Web UI stack](../implementation/web-ui-stack.md)
- [Web demo design kit plan](../implementation/web-demo-design-kit-plan.md)
- [Municipal portal 1.0 roadmap](./municipal-portal-v1-roadmap.md)
- [Municipal portal UI component architecture](./municipal-portal-ui-component-architecture.md)

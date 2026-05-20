---
type: implementation
tags:
  - product
  - web-ui
  - components
  - municipal-portal
updated: 2026-05-20
---

This page defines the municipal portal reusable view-component contract and dependency posture.

# Municipal Portal UI Component Architecture

## Design Goal

The portal UI should be built from reusable view components that receive explicit page context and data, render predictable states, and keep implementation dependencies replaceable where practical.

Dependency reduction is a design constraint, not the immediate reason to rewrite working pages. The near-term priority is to make the UI modular enough that components can be reused across domains and moved away from React/Babel later if that becomes worthwhile.

## Dependency Posture

Use third-party client code only where it provides clear value that is expensive or risky to reproduce locally.

| Dependency class | 1.0 posture |
| --- | --- |
| React/Babel | Allowed for current portal shell and page work while component contracts settle. |
| Leaflet | Allowed for map pages because map interaction is domain-specific and non-trivial. |
| Three.js | Allowed only for lab or 3D pages, not core portal chrome. |
| Icon, font, and UI helper libraries | Avoid adding new runtime dependencies unless separately approved. |
| New framework or state library | Out of scope until a component contract and feasibility study justify it. |

When adding a dependency, document the purpose, runtime surface, replacement path, and affected pages before using it in shared UI.

## Page Context

Every portal page should receive or derive a single context object:

| Field | Purpose |
| --- | --- |
| `municipality` | Current municipality id, label, and source status. |
| `theme` | Active theme id and stylesheet path. |
| `rolePreset` | Public view preset, not an authorization role. |
| `route` | Current route id/path and domain area. |
| `selectedEntity` | Current parcel, meeting, document, business item, budget item, or map feature when applicable. |
| `sourceStatus` | Data availability, freshness, limitation, or prototype status. |
| `availableActions` | Links or commands the page may render for the current context. |

Components should not read global URL state, route tables, or DOM text when the needed value can be passed through this context.

## Component Contract

Every reusable view component should define:

| Contract part | Requirement |
| --- | --- |
| Name | Stable component name tied to behavior, not visual style. |
| Purpose | One sentence describing the user-facing job. |
| Inputs | Required and optional props or data fields. |
| Context use | Which page-context fields it reads. |
| Outputs | Rendered UI and emitted events or selected actions. |
| States | Loading, empty, partial, error, unavailable, and ready states where relevant. |
| Provenance | Source labels, citations, API/source table names, or limitation text it must show. |
| Accessibility | Landmark, heading, label, keyboard, and focus requirements. |
| Dependency boundary | Whether it uses React only, browser APIs only, Leaflet, Three.js, or no third-party code. |

Do not make a shared component until at least two pages need the same behavior or the component encodes a portal-wide rule such as provenance display, status labels, role-preset filtering, or page-contract rendering.

## First Component Families

| Family | Purpose | Initial examples |
| --- | --- | --- |
| Portal shell | Shared municipal chrome and role preset context. | Header, role selector, domain navigation. |
| Status and provenance | Make source status explicit. | Status badge, source summary, limitation notice. |
| Page contract | Standardize domain stubs. | Purpose/input/output/API/state contract panel. |
| Entity summary | Render selected municipal objects consistently. | Parcel summary, meeting item summary, document summary, business item summary. |
| Action set | Render context-aware links and commands. | Public action links, local-admin action group, lab-tool links. |

## Implementation Independence

Current implementations may be React/Babel, but component contracts should stay implementation-independent:

- Keep data shaping outside view components where practical.
- Pass plain objects and arrays rather than framework-specific objects.
- Keep CSS class names semantic and token-based.
- Keep component state local unless state must be shared through page context.
- Avoid hiding source/provenance behavior inside visual-only components.
- Avoid direct writes from shared components unless the page is explicitly local-admin.

## Feasibility Study Reframing

The basic-HTML study should answer whether the component contract can be implemented with less third-party code without increasing complexity or reducing maintainability. It should not block all portal work, but it should happen before building a large shared component library.

The study should compare one representative component family, preferably `Page contract` or `Status and provenance`, in:

1. Current React/Babel.
2. Basic HTML/CSS/first-party JavaScript.

The recommendation should choose one of:

- continue React/Babel for 1.0
- build new components in React/Babel but keep contracts portable
- migrate selected component families to basic HTML/first-party JavaScript
- switch before shared component buildout

## Sources

- [Municipal portal UI architecture](./municipal-portal-ui-architecture.md)
- [Municipal portal 1.0 roadmap](./municipal-portal-v1-roadmap.md)
- [Web UI stack](../implementation/web-ui-stack.md)

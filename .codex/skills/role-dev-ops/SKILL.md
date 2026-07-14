---
name: role-dev-ops
description: Use for project environments, dependencies, package installation or updates, runtimes, toolchains, containers, CI/CD, infrastructure, deployment targets, secrets configuration, and other DevOps work. This role exclusively performs approved setup and stack mutations and keeps project and wiki documentation current.
metadata:
  short-description: Govern environments and deployments
---

# DevOps

Use this role for any project setup or operational change, including:

- adding, removing, installing, or updating Python, Node, system, GIS, database, container, or other dependencies
- changing package manifests, lockfiles, runtimes, interpreters, environment variables, build tools, or local developer setup
- adding or changing deployment targets, infrastructure, containers, CI/CD, service topology, or operational configuration
- performing installation, upgrade, migration, deployment, rollback, or environment-repair work

Other roles may identify a need for these changes, but must route execution to DevOps. DevOps is solely responsible for installation and environment or stack mutation.

## Required Discovery

Before proposing a change:

1. Read `wiki/AGENTS.md`, `wiki/index.md`, and relevant pages under `wiki/platform/` and `wiki/implementation/`.
2. Inspect the current manifests, lockfiles, wrappers, environment templates, container files, infrastructure files, deployment scripts, and active runtime state relevant to the request.
3. Separate verified current state from stale documentation and historical artifacts.
4. Identify affected local, CI, container, database, GIS, and deployment environments.

## Approval Gate

Before any mutation, present the user with:

- the verified current state
- the exact proposed changes and affected artifacts
- dependency, compatibility, security, data, downtime, and deployment risks
- verification and rollback plans
- documentation updates required to keep the repository accurate

Obtain explicit user approval before installing, removing, upgrading, deploying, migrating, changing configuration, editing manifests or lockfiles, or changing deployment infrastructure. Prior approval applies only to the stated scope. Stop and request renewed approval if the package, version, target, risk, affected artifacts, or operational impact changes materially.

Read-only discovery and diagnostics do not require approval.

## Execution

After approval:

- perform only the approved mutations
- prefer repository wrappers and reproducible, non-interactive commands
- update manifests and lockfiles together and avoid unrecorded global dependencies
- preserve secrets outside version control and document required variable names without recording secret values
- retain or define a practical rollback path before high-impact changes
- capture exact versions and verify the effective runtime state rather than relying only on command success
- stop on unexpected dependency resolution, destructive migration, target mismatch, or expanded operational impact

## Documentation Ownership

DevOps owns documentation of the current project setup. For every approved change:

- update the relevant project documentation, such as `README.md`, environment examples, deployment guides, or operational scripts
- update or create the canonical page under `wiki/platform/` or `wiki/implementation/`
- update `wiki/index.md` when pages are added, renamed, removed, or materially changed
- append a reverse-chronological entry to `wiki/log.md`
- remove or clearly label stale instructions and distinguish special runtimes such as QGIS-bundled Python from the canonical project runtime

Documentation must describe the verified resulting state, setup commands, version source, execution wrapper, deployment targets, and known exceptions.

## Deployment Endpoint Routing

Use the verified deployment target that matches the requested workflow:

- For requests to inspect, demonstrate, or verify the deployed application, route to `https://mdopendata-demo.onrender.com`.
- Verify that target with `GET https://mdopendata-demo.onrender.com/healthz` before reporting it as available.
- Treat the Render target as read-only demonstration infrastructure backed by the Supabase snapshot. Route ingestion, uploads, extraction, review writes, and other mutation workflows to the local environment.
- Do not route demonstration requests to the separate AWS deployment workflow. Use `wiki/implementation/aws-deployment.md` only for explicitly requested AWS operations.
- Keep the current endpoint and its read-only boundary synchronized with `wiki/implementation/render-supabase-deployment.md` and `wiki/platform/project-environment.md`.

## Handoff and QA

Report the approved scope, executed commands, changed artifacts, resulting versions or targets, verification results, rollback readiness, documentation updates, and unresolved risks. Finish in `QA Reviewer` after mutation. Route failures with an unknown cause to `Debugger`; route architecture decisions beyond the approved operational scope to `Coding Architect`.

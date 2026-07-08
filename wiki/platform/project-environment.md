---
type: platform
tags:
  - environment
  - python
  - dependencies
  - deployment
updated: 2026-07-08
---

This page records the canonical project runtime, dependency, and environment-management contract.

# Project Environment

## Ownership and Change Control

The `DevOps` role at `../../.codex/skills/role-dev-ops/SKILL.md` is the sole role authorized to install or update dependencies and mutate project environments, toolchains, containers, infrastructure, CI/CD, or deployment targets. DevOps must review the current state and obtain explicit user approval for the exact proposed change before mutation.

Other roles route operational requirements to DevOps. DevOps updates project documentation and this wiki when the verified setup changes.

## Canonical Python Runtime

The canonical repository Python environment is `.venv`, created with Python 3.14 or newer as required by `pyproject.toml`. The repository wrapper `scripts/python.ps1` resolves and invokes:

```text
.venv\Scripts\python.exe
```

Run project scripts through the wrapper:

```powershell
.\scripts\python.ps1 .\scripts\validate-code-table-candidates.py
```

`pyproject.toml` defines supported dependency ranges. `requirements.lock.txt` records the exact validated Python dependency set. Installation and refresh commands remain in the root `README.md`.

## Separate Python Runtimes

QGIS MCP does not use the canonical `.venv`. It uses the Python runtime bundled with the installed QGIS version, plus `.qgis-mcp-packages` and `qgis_mcp_vendor`, as configured by `scripts/start-qgis-mcp.ps1`.

Historical `.python` paths and Codex bundled-runtime paths in generated manifests or old workflow notes are not the canonical project runtime. They must not be copied into new setup instructions.

## Current Deployment Surfaces

- Local services use Docker Compose through `docker-compose.yml`.
- The documented remote deployment target is a single-host AWS EC2 Docker Compose deployment described in `wiki/implementation/aws-deployment.md`.
- Adding or changing a deployment target requires DevOps review and explicit user approval.

## Required Documentation for Changes

Every environment or deployment change must record:

- the effective runtime or tool version and its source of truth
- reproducible setup or update commands
- affected manifests, lockfiles, wrappers, containers, and deployment targets
- required environment-variable names without secret values
- verification results, exceptions, and rollback instructions
- corresponding updates to project documentation, this wiki, `wiki/index.md`, and `wiki/log.md`

## Sources

- [Root README](../../README.md)
- [Python project configuration](../../pyproject.toml)
- [Locked Python dependencies](../../requirements.lock.txt)
- [Python wrapper](../../scripts/python.ps1)
- [QGIS MCP launcher](../../scripts/start-qgis-mcp.ps1)
- [AWS deployment](../implementation/aws-deployment.md)
- [Repository instructions](../../AGENTS.md)

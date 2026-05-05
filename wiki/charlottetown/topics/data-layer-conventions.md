---
type: topic
tags:
  - charlottetown
  - conventions
  - operations
updated: 2026-05-04
---

# Zoning Data-Layer Conventions

Three operating conventions that are implicit in the codebase but not
otherwise written down. Read this before adding a new script that writes to
the `zoning.*` schema or that captures reviewer-curated content.

## 1. Reviewer decisions live as versioned JSON, not in the database

Anything that requires human judgement is captured as a JSON artifact under
`data/.../manual-corrections/`, with paired extract/apply scripts. The
database is rebuildable end-to-end from these artifacts plus the bylaw JSON
sources. A `dropdb && docker compose up -d postgis` followed by the
[Database standup](database-standup.md) procedure must restore the full
state without manual re-review.

Existing precedents (use as templates rather than re-inventing):

| Decision domain | Artifact | Apply script |
|---|---|---|
| Section equivalence (current↔draft section pairings) | `data/zoning/charlottetown/manual-corrections/section-equivalence-decisions.json` | `scripts/apply-charlottetown-section-equivalence-decisions.py` |
| Draft zoning-map missing-block fills | `data/spatial/charlottetown/manual-corrections/draft-zoning-map-corrections.json` | `scripts/apply-charlottetown-draft-zoning-manual-corrections.py` |
| Bylaw override relationships | `data/zoning/charlottetown/manual-corrections/override-relationships.json` | `scripts/apply-charlottetown-override-relationships.py` |

Each artifact starts with `schema_version: 1` and a top-level `description`,
declares the `natural_key_fields` used to match against existing rows, and
makes the apply script idempotent (running twice with no JSON changes
reports zero changes). When an export companion exists (as for section
equivalence), it round-trips: re-running the export after `apply` produces
a byte-identical artifact unless the underlying decisions actually changed.

## 2. Natural-key + content-hash + supersession discipline

Every script that mutates `zoning.*` follows the same upsert contract used
by `scripts/import-charlottetown-zoning.py`:

- A **`natural_key`** identifies a logical record across re-imports
  (typically a path-like composite of source file, family, and intra-file
  identifier). Stored on the row.
- A **`content_hash`** captures the value-bearing payload (sha256 of a
  stable-key JSON serialization, with importer-volatile fields stripped —
  see `_VOLATILE_KEYS` in the importer; **must not** strip natural-key id
  fields like `source_ref_id`, `term_id`, etc.; the bug fix in commit
  `8b2959a` exists because that distinction was missed).
- On apply, the script looks up the `(natural_key, is_active=true)` row.
  If `content_hash` matches, do nothing. Otherwise mark the prior row
  `is_active=false`, insert a new active row, and set the prior row's
  `superseded_by_id` to the new id.

This gives forward-only history with full provenance. Never `UPDATE` a
value-bearing column in place; always supersede.

The same pattern applies to manual-decision scripts. See
`scripts/apply-charlottetown-override-relationships.py:upsert_fact` for a
copyable reference implementation, including the `import_batch` +
`import_record_event` audit trail (`change_status` must be one of
`added`, `removed`, `changed`, `unchanged` per the
`ck_zoning_import_record_event_status` constraint).

## 3. The Postgres MCP server is read-only — mutations go through Python

`.codex/mcp.json` and `.mcp.json` (when present) configure a Postgres MCP
server backed by `@modelcontextprotocol/server-postgres`, which only
exposes read SQL. All write paths go through Python scripts that open
their own `psycopg` connection using credentials from `PG*` environment
variables, defaulting to the local docker container on port 54329 (see
`docker-compose.yml`).

Idiomatic skeleton, copied from existing scripts:

```python
import os, psycopg

def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

with psycopg.connect(database_url()) as conn:
    ...
    conn.commit()  # or conn.rollback() under --dry-run
```

`scripts/run-migrations.py` is the exception — it shells out to
`docker exec ... psql` to apply schema changes that need to run inside the
container's process. SQL files live in `schema/sql/NNN_*.sql` and are
auto-discovered by the runner; the filesystem is the single source of
truth for the migration list (see commit `bc97e59`).

For one-off DDL or backfills against the running container, use the same
`docker exec ... psql` invocation:

```bash
docker exec -i mdopendata-postgis psql -v ON_ERROR_STOP=1 \
    -U mdopendata -d mdopendata < some.sql
```

## Sources

- [Database standup](database-standup.md)
- [Zoning data-layer backlog](zoning-data-layer-backlog.md)
- `scripts/import-charlottetown-zoning.py`
- `scripts/apply-charlottetown-override-relationships.py`
- `scripts/run-migrations.py`
- `docker-compose.yml`

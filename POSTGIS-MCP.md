# PostgreSQL and PostGIS MCP Setup

## Direct outcome

This repository can now run a local PostGIS database in Docker and expose it to an MCP client through the official PostgreSQL MCP server.

## Included artifacts

- `docker-compose.yml`: local `postgis/postgis` service with persistent storage under `data/postgres/`
- `.env.example`: default development database settings
- `.mcp.json`: repository-local MCP server definition for the local database
- `package.json`: npm wrappers for start, stop, logs, schema check, and schema reapply
- `scripts/check-postgis.ps1` and `scripts/apply-postgis-schema.ps1`: direct PowerShell helpers if you want to invoke them manually

## Important constraint

The official PostgreSQL MCP server is read-only. Use MCP for inspection and querying. Use `psql`, `ogr2ogr`, restore commands, or ingestion scripts to insert and update data.

## Maintenance note

As of April 9, 2026, `@modelcontextprotocol/server-postgres` is deprecated on npm and PostgreSQL appears in the archived server list in the official MCP servers repository. The current setup uses it because it is still the direct reference implementation for PostgreSQL MCP access, but it should be treated as a temporary bridge rather than a long-term dependency.

## Default local settings

- host: `127.0.0.1`
- port: `54329`
- database: `mdopendata`
- user: `charlottown`
- password: `charlottown_dev`
- container: `charlottown-postgis`

## Repository bootstrap

1. Copy `.env.example` to `.env` if you want to override defaults.
2. Start the database:

```powershell
npm run db:up
```

3. Verify that the schema exists:

```powershell
npm run db:check
```

If you change `schema/postgis.sql` after the container already exists, reapply it with:

```powershell
npm run db:apply-schema
```

## MCP wiring

The repository root now includes `.mcp.json` with this server definition:

```json
{
  "mcpServers": {
    "charlottown-postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://charlottown:charlottown_dev@127.0.0.1:54329/mdopendata?sslmode=disable"
      ]
    }
  }
}
```

If your MCP client does not auto-read repository `.mcp.json`, copy that block into the client MCP configuration and keep the connection string aligned with `.env`.

## Docker client workaround

The npm database commands set `DOCKER_CONFIG` to a repository-local `.docker-local/` directory so they do not depend on the unreadable Docker home config under `C:\Users\19029\.docker\`.

## First data-loading paths

- SQL files: `docker exec -i charlottown-postgis psql -U charlottown -d mdopendata < file.sql`
- GeoJSON or GeoPackage: `ogr2ogr -f PostgreSQL PG:"host=127.0.0.1 port=54329 dbname=mdopendata user=charlottown password=charlottown_dev" input.geojson`
- Application code: use any PostgreSQL client against the same DSN

## Operational requirement

Docker Desktop or another local Docker daemon must be running before `npm run db:up` can create the PostGIS container and before MCP can connect to the database.

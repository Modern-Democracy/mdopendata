param(
  [string]$DatabaseUrl = $env:DATABASE_URL,
  [string]$DumpPath = (Join-Path (Split-Path -Parent $PSScriptRoot) "tmp\supabase-data.dump"),
  [switch]$SchemaOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$container = if ($env:PGCONTAINER) { $env:PGCONTAINER } else { "mdopendata-postgis" }
$database = if ($env:PGDATABASE) { $env:PGDATABASE } else { "mdopendata" }
$user = if ($env:PGUSER) { $env:PGUSER } else { "mdopendata" }
$containerDump = "/tmp/mdopendata-supabase-data.dump"
$containerSchema = "/tmp/mdopendata-supabase-schema.sql"
$containerMigrationState = "/tmp/mdopendata-supabase-migration-state.sql"

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
  throw "DATABASE_URL is required. Pass -DatabaseUrl or set the DATABASE_URL environment variable."
}

$env:DATABASE_URL = $DatabaseUrl
$env:DATABASE_SSL = "true"
$env:PGOPTIONS = "-c search_path=public,extensions"

$dumpDirectory = Split-Path -Parent $DumpPath
New-Item -ItemType Directory -Force -Path $dumpDirectory | Out-Null
$schemaDumpPath = [System.IO.Path]::ChangeExtension($DumpPath, ".schema.sql")
$migrationStatePath = Join-Path $dumpDirectory "supabase-migration-state.sql"

docker exec $container rm -f $containerSchema | Out-Null
docker exec $container pg_dump --schema-only --no-owner --no-privileges `
  --schema=public --schema=zoning --schema=budget --schema=council --schema=help `
  --exclude-table=public.spatial_ref_sys -U $user -d $database -f $containerSchema
if ($LASTEXITCODE -ne 0) {
  throw "Local schema dump failed with exit code $LASTEXITCODE."
}

docker cp "${container}:${containerSchema}" $schemaDumpPath
if ($LASTEXITCODE -ne 0) {
  throw "Copying the local schema dump failed with exit code $LASTEXITCODE."
}

$schemaSql = Get-Content -Raw -LiteralPath $schemaDumpPath
$schemaSql = $schemaSql -replace '(?m)^CREATE SCHEMA public;\r?\n', ''
$schemaSql = $schemaSql -replace '(?m)^COMMENT ON SCHEMA public IS ''standard public schema'';\r?\n', ''
$schemaSql = $schemaSql.Replace('public.&&', 'extensions.&&')
$schemaSql = $schemaSql -replace '(?i)\bpublic\.(geometry|raster|st_[A-Za-z0-9_]+)\b', 'extensions.$1'
Set-Content -LiteralPath $schemaDumpPath -Value $schemaSql -Encoding utf8

$dumpName = Split-Path -Leaf $DumpPath
$schemaName = Split-Path -Leaf $schemaDumpPath
$mountPath = (Resolve-Path $dumpDirectory).Path

docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  postgres:16-alpine `
  psql $DatabaseUrl -v ON_ERROR_STOP=1 `
  -c "CREATE SCHEMA IF NOT EXISTS extensions" `
  -c "CREATE EXTENSION IF NOT EXISTS postgis SCHEMA extensions" `
  -c "CREATE EXTENSION IF NOT EXISTS postgis_raster SCHEMA extensions"
if ($LASTEXITCODE -ne 0) {
  throw "Supabase PostGIS extension setup failed with exit code $LASTEXITCODE."
}

docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  --env SCHEMA_NAME=$schemaName `
  --volume "${mountPath}:/work:ro" `
  postgres:16-alpine `
  psql $DatabaseUrl -v ON_ERROR_STOP=1 -f "/work/$schemaName"
if ($LASTEXITCODE -ne 0) {
  throw "Supabase schema restore failed with exit code $LASTEXITCODE."
}

$migrationValues = Get-ChildItem -LiteralPath (Join-Path $repoRoot "schema\sql") -Filter "*.sql" |
  Where-Object { $_.Name -match '^\d+_.+\.sql$' } |
  Sort-Object Name |
  ForEach-Object { "('$($_.Name.Replace("'", "''"))')" }
$migrationStateSql = @(
  "INSERT INTO public.schema_migrations (filename) VALUES"
  ($migrationValues -join ",`n")
  "ON CONFLICT (filename) DO NOTHING;"
) -join "`n"
Set-Content -LiteralPath $migrationStatePath -Value $migrationStateSql -Encoding utf8
$migrationStateName = Split-Path -Leaf $migrationStatePath
docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  --env MIGRATION_STATE_NAME=$migrationStateName `
  --volume "${mountPath}:/work:ro" `
  postgres:16-alpine `
  psql $DatabaseUrl -v ON_ERROR_STOP=1 -f "/work/$migrationStateName"
if ($LASTEXITCODE -ne 0) {
  throw "Supabase migration-state restore failed with exit code $LASTEXITCODE."
}

if ($SchemaOnly) {
  Write-Host "Supabase schema bootstrap complete. Data load was skipped."
  exit 0
}

docker exec $container rm -f $containerDump | Out-Null
docker exec $container pg_dump -Fc --data-only --no-owner --no-privileges `
  --schema=public --schema=zoning --schema=budget --schema=council --schema=help `
  --exclude-table=public.spatial_ref_sys --exclude-table=public.schema_migrations `
  -U $user -d $database -f $containerDump
if ($LASTEXITCODE -ne 0) {
  throw "Local database dump failed with exit code $LASTEXITCODE."
}

docker cp "${container}:${containerDump}" $DumpPath
if ($LASTEXITCODE -ne 0) {
  throw "Copying the local database dump failed with exit code $LASTEXITCODE."
}

$disableProjectTriggersSql = @'
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT n.nspname, c.relname, t.tgname
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE NOT t.tgisinternal
          AND n.nspname IN ('public', 'zoning', 'budget', 'council', 'help')
    LOOP
        EXECUTE format('ALTER TABLE %I.%I DISABLE TRIGGER %I', r.nspname, r.relname, r.tgname);
    END LOOP;
END $$;
'@
$enableProjectTriggersSql = @'
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT n.nspname, c.relname, t.tgname
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE NOT t.tgisinternal
          AND n.nspname IN ('public', 'zoning', 'budget', 'council', 'help')
    LOOP
        EXECUTE format('ALTER TABLE %I.%I ENABLE TRIGGER %I', r.nspname, r.relname, r.tgname);
    END LOOP;
END $$;
'@
docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  postgres:16-alpine `
  psql $DatabaseUrl -v ON_ERROR_STOP=1 -c $disableProjectTriggersSql
if ($LASTEXITCODE -ne 0) {
  throw "Disabling project validation triggers failed with exit code $LASTEXITCODE."
}

$restoreExitCode = 0
docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  --env DUMP_NAME=$dumpName `
  --volume "${mountPath}:/work:ro" `
  postgres:16-alpine `
  pg_restore --dbname=$DatabaseUrl --no-owner --no-privileges --exit-on-error "/work/$dumpName"
$restoreExitCode = $LASTEXITCODE

docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  postgres:16-alpine `
  psql $DatabaseUrl -v ON_ERROR_STOP=1 -c $enableProjectTriggersSql
if ($LASTEXITCODE -ne 0) {
  throw "Re-enabling project validation triggers failed with exit code $LASTEXITCODE."
}
if ($restoreExitCode -ne 0) {
  throw "Restoring the local database dump to Supabase failed with exit code $restoreExitCode."
}

$refreshMaterializedViewsSql = @'
SET statement_timeout = 0;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_buildings;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_civic_addresses;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_current_zoning_boundaries;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_draft_zoning_boundaries;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_parcel_map;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_schedule_a_wetlands;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_street_network;
REFRESH MATERIALIZED VIEW zoning.v_charlottetown_parcel_zone_assignment;
'@
docker run --rm `
  --env DATABASE_URL=$DatabaseUrl `
  --env PGSSLMODE=require `
  --env PGOPTIONS=$env:PGOPTIONS `
  postgres:16-alpine `
  psql $DatabaseUrl -v ON_ERROR_STOP=1 -c $refreshMaterializedViewsSql
if ($LASTEXITCODE -ne 0) {
  throw "Refreshing Supabase materialized views failed with exit code $LASTEXITCODE."
}

Write-Host "Supabase schema and demonstration data bootstrap complete."

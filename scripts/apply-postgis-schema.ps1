$ErrorActionPreference = 'Stop'

$containerName = 'charlottown-postgis'
$database = if ($env:PGDATABASE) { $env:PGDATABASE } else { 'mdopendata' }
$user = if ($env:PGUSER) { $env:PGUSER } else { 'charlottown' }
$schemaPath = Join-Path $PSScriptRoot "..\schema\postgis.sql"
$resolvedSchemaPath = (Resolve-Path $schemaPath).Path

Get-Content $resolvedSchemaPath | docker exec -i $containerName psql -U $user -d $database

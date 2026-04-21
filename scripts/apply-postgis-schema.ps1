$ErrorActionPreference = 'Stop'

$containerName = 'mdopendata-postgis'
$database = if ($env:PGDATABASE) { $env:PGDATABASE } else { 'mdopendata' }
$user = if ($env:PGUSER) { $env:PGUSER } else { 'mdopendata' }
$schemaPath = Join-Path $PSScriptRoot "..\schema\sql\postgis.sql"
$resolvedSchemaPath = (Resolve-Path $schemaPath).Path

Get-Content $resolvedSchemaPath | docker exec -i $containerName psql -U $user -d $database

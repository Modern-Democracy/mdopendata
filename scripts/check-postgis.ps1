$ErrorActionPreference = 'Stop'

$containerName = 'mdopendata-postgis'
$database = if ($env:PGDATABASE) { $env:PGDATABASE } else { 'mdopendata' }
$user = if ($env:PGUSER) { $env:PGUSER } else { 'mdopendata' }

docker exec $containerName psql -U $user -d $database -c "\dt"

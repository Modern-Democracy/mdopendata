$ErrorActionPreference = 'Stop'

$containerName = 'charlottown-postgis'
$database = if ($env:PGDATABASE) { $env:PGDATABASE } else { 'mdopendata' }
$user = if ($env:PGUSER) { $env:PGUSER } else { 'charlottown' }

docker exec $containerName psql -U $user -d $database -c "\dt"

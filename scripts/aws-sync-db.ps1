param(
  [Parameter(Mandatory = $true)]
  [string]$StackName,

  [Parameter(Mandatory = $true)]
  [string]$SshKeyPath,

  [string]$Region = $env:AWS_REGION,
  [string]$AwsProfile = "mdopendata",
  [string]$LocalContainer = "mdopendata-postgis",
  [string]$PgDatabase = "mdopendata",
  [string]$PgUser = "mdopendata",
  [switch]$NoBackup
)

$ErrorActionPreference = "Stop"

if (-not $Region) {
  throw "Set -Region or AWS_REGION."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$artifactDir = Join-Path $repoRoot "tmp/aws-sync-db"
$dumpPath = Join-Path $artifactDir "mdopendata.dump"
$containerDumpPath = "/tmp/mdopendata-sync.dump"

Remove-Item -LiteralPath $artifactDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

$outputs = aws cloudformation describe-stacks `
  --profile $AwsProfile `
  --region $Region `
  --stack-name $StackName `
  --query "Stacks[0].Outputs" `
  --output json | ConvertFrom-Json
$publicIp = ($outputs | Where-Object { $_.OutputKey -eq "PublicIp" }).OutputValue
if (-not $publicIp) {
  throw "Stack output PublicIp was not found."
}

$dumpCommand = @(
  "docker", "exec", $LocalContainer,
  "sh", "-c",
  "pg_dump -Fc --no-owner --no-acl -U '$PgUser' -d '$PgDatabase' > '$containerDumpPath'"
)
& $dumpCommand[0] $dumpCommand[1..($dumpCommand.Length - 1)]
if ($LASTEXITCODE -ne 0) { throw "local pg_dump failed." }

docker cp "$LocalContainer`:$containerDumpPath" $dumpPath
if ($LASTEXITCODE -ne 0) { throw "docker cp dump failed." }

scp -i $SshKeyPath -o StrictHostKeyChecking=accept-new $dumpPath "ec2-user@$publicIp`:/tmp/mdopendata.dump"
if ($LASTEXITCODE -ne 0) { throw "scp upload failed." }

$backupClause = if ($NoBackup) {
  "true"
} else {
  "mkdir -p /opt/mdopendata/shared/backups && docker compose -f docker-compose.aws.yml --env-file .env exec -T postgis pg_dump -Fc --no-owner --no-acl -U '$PgUser' -d '$PgDatabase' > /opt/mdopendata/shared/backups/pre-sync-$(date -u +%Y%m%dT%H%M%SZ).dump"
}

$remoteCommand = @"
set -euxo pipefail
cd /opt/mdopendata/current
$backupClause
docker compose -f docker-compose.aws.yml --env-file .env exec -T postgis dropdb -U '$PgUser' --if-exists '$PgDatabase'
docker compose -f docker-compose.aws.yml --env-file .env exec -T postgis createdb -U '$PgUser' '$PgDatabase'
docker compose -f docker-compose.aws.yml --env-file .env exec -T postgis pg_restore --no-owner --no-acl -U '$PgUser' -d '$PgDatabase' < /tmp/mdopendata.dump
docker compose -f docker-compose.aws.yml --env-file .env restart web
"@

ssh -i $SshKeyPath -o StrictHostKeyChecking=accept-new "ec2-user@$publicIp" $remoteCommand
if ($LASTEXITCODE -ne 0) { throw "remote restore failed." }

Write-Output "Synchronized local database to AWS at http://$publicIp/"

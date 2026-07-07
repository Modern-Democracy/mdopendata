param(
  [Parameter(Mandatory = $true)]
  [string]$StackName,

  [Parameter(Mandatory = $true)]
  [string]$KeyName,

  [Parameter(Mandatory = $true)]
  [string]$SshKeyPath,

  [string]$Region = $env:AWS_REGION,
  [string]$AwsProfile = "mdopendata",
  [string]$InstanceType = "t3.large",
  [string]$SshLocation = "0.0.0.0/0",
  [string]$WebLocation = "0.0.0.0/0",
  [int]$VolumeSizeGiB = 80,
  [string]$VpcId = "",
  [string]$SubnetId = "",
  [string]$PgDatabase = "mdopendata",
  [string]$PgUser = "mdopendata",
  [Parameter(Mandatory = $true)]
  [string]$PgPassword,
  [int]$WebPort = 80,
  [switch]$SkipInfrastructure
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$templatePath = Join-Path $repoRoot "infra/aws/mdopendata-ec2.yml"
$artifactDir = Join-Path $repoRoot "tmp/aws-deploy"
$stageDir = Join-Path $artifactDir "stage"
$archivePath = Join-Path $artifactDir "mdopendata.zip"
$remoteRoot = "/opt/mdopendata"
$releaseName = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$remoteRelease = "$remoteRoot/releases/$releaseName"

if (-not $Region) {
  throw "Set -Region or AWS_REGION."
}

function Invoke-Checked {
  param([string[]]$Command)
  & $Command[0] $Command[1..($Command.Length - 1)]
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $($Command -join ' ')"
  }
}

if (-not $SkipInfrastructure) {
  Invoke-Checked @(
    "aws", "cloudformation", "deploy",
    "--profile", $AwsProfile,
    "--region", $Region,
    "--stack-name", $StackName,
    "--template-file", $templatePath,
    "--capabilities", "CAPABILITY_NAMED_IAM",
    "--parameter-overrides",
    "KeyName=$KeyName",
    "InstanceType=$InstanceType",
    "SSHLocation=$SshLocation",
    "WebLocation=$WebLocation",
    "VolumeSizeGiB=$VolumeSizeGiB",
    "VpcId=$VpcId",
    "SubnetId=$SubnetId"
  )
}

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

Remove-Item -LiteralPath $artifactDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path $stageDir | Out-Null

$excludePatterns = @(
  "\.git\*",
  ".docker-local\*",
  ".venv\*",
  ".python\*",
  "data\postgres\*",
  "data\pgadmin\*",
  "tmp\*",
  "web\node_modules\*"
)

Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Force |
  Where-Object {
    $relative = $_.FullName.Substring($repoRoot.Length + 1)
    foreach ($pattern in $excludePatterns) {
      if ($relative -like $pattern) { return $false }
    }
    return $true
  } |
  ForEach-Object {
    $relative = $_.FullName.Substring($repoRoot.Length + 1)
    $target = Join-Path $stageDir $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $target
  }

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $archivePath -CompressionLevel Optimal

scp -i $SshKeyPath -o StrictHostKeyChecking=accept-new $archivePath "ec2-user@$publicIp`:/tmp/mdopendata.zip"
if ($LASTEXITCODE -ne 0) { throw "scp upload failed." }

$envText = @"
PGDATABASE=$PgDatabase
PGUSER=$PgUser
PGPASSWORD=$PgPassword
WEB_PORT=$WebPort
"@
$envBytes = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($envText))

$remoteCommand = @"
set -euxo pipefail
mkdir -p '$remoteRelease'
unzip -q /tmp/mdopendata.zip -d '$remoteRelease'
printf '%s' '$envBytes' | base64 -d > '$remoteRelease/.env'
ln -sfn '$remoteRelease' '$remoteRoot/current'
cd '$remoteRoot/current'
docker compose -f docker-compose.aws.yml --env-file .env up -d --build
docker compose -f docker-compose.aws.yml --env-file .env exec -T postgis psql -U '$PgUser' -d '$PgDatabase' -c 'SELECT 1;'
"@

ssh -i $SshKeyPath -o StrictHostKeyChecking=accept-new "ec2-user@$publicIp" $remoteCommand
if ($LASTEXITCODE -ne 0) { throw "remote deployment failed." }

Write-Output "Deployed mdopendata to http://$publicIp/"

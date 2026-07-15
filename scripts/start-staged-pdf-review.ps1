param(
  [ValidateRange(1, 65535)]
  [int]$Port = 3217
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$serverPath = Join-Path $repoRoot 'web\server.js'
$artifactPath = Join-Path $repoRoot 'data\budget\charlottetown\2026-2027\staged-pdf\v1\stage-0\source-evidence.json'
$blockArtifactPath = Join-Path $repoRoot 'data\budget\charlottetown\2026-2027\staged-pdf\v1\stage-1\block-inventory.json'

if (-not (Test-Path -LiteralPath $serverPath -PathType Leaf)) {
  throw "Web server not found: $serverPath"
}
if (-not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
  throw "Stage 0 source evidence not found: $artifactPath"
}
if (-not (Test-Path -LiteralPath $blockArtifactPath -PathType Leaf)) {
  throw "Stage 1 block inventory not found: $blockArtifactPath"
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw 'Node.js is not available on PATH.'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
  throw "Port $Port is already in use."
}

$previous = @{
  HOST = $env:HOST
  PORT = $env:PORT
  REPO_ROOT = $env:REPO_ROOT
  PDF_INVENTORY_REVIEW_ENABLED = $env:PDF_INVENTORY_REVIEW_ENABLED
  PDF_INVENTORY_REVIEW_WRITE_ENABLED = $env:PDF_INVENTORY_REVIEW_WRITE_ENABLED
  DEMO_MODE = $env:DEMO_MODE
}

try {
  $env:HOST = '127.0.0.1'
  $env:PORT = [string]$Port
  $env:REPO_ROOT = $repoRoot
  $env:PDF_INVENTORY_REVIEW_ENABLED = '1'
  $env:PDF_INVENTORY_REVIEW_WRITE_ENABLED = '1'
  $env:DEMO_MODE = '0'

  Write-Host "Local review: http://127.0.0.1:$Port/internal/pdf-inventory-review"
  Write-Host 'Press Ctrl+C to stop the review server.'

  Push-Location $repoRoot
  try {
    & node $serverPath
  } finally {
    Pop-Location
  }
} finally {
  foreach ($key in $previous.Keys) {
    [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
  }
}

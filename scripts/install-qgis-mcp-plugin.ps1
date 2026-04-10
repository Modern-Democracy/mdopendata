param(
    [string]$ProfileName = "default",
    [ValidateSet("QGIS3", "QGIS4")]
    [string]$QgisProfileRoot = "QGIS4"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourcePlugin = Join-Path $repoRoot "qgis_mcp_vendor\qgis_mcp_plugin"
$targetPluginsDir = Join-Path $env:APPDATA "QGIS\$QgisProfileRoot\profiles\$ProfileName\python\plugins"
$targetPlugin = Join-Path $targetPluginsDir "qgis_mcp_plugin"

if (-not (Test-Path $sourcePlugin)) {
    throw "QGIS MCP plugin source was not found at $sourcePlugin"
}

New-Item -ItemType Directory -Path $targetPluginsDir -Force | Out-Null

if (Test-Path $targetPlugin) {
    Remove-Item -LiteralPath $targetPlugin -Recurse -Force
}

Copy-Item -LiteralPath $sourcePlugin -Destination $targetPluginsDir -Recurse

Write-Output "Installed QGIS MCP plugin to $targetPlugin"

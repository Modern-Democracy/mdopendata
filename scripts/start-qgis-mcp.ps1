$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = "C:\Program Files\QGIS 4.0.1\apps\Python312\python.exe"
$vendorServer = Join-Path $repoRoot "qgis_mcp_vendor\src\qgis_mcp\qgis_mcp_server.py"
$packagePath = Join-Path $repoRoot ".qgis-mcp-packages"
$pywin32Path = Join-Path $packagePath "pywin32_system32"
$win32Path = Join-Path $packagePath "win32"
$win32LibPath = Join-Path $win32Path "lib"
$qgisSitePackages = "C:\Program Files\QGIS 4.0.1\apps\Python312\Lib\site-packages"

if (-not (Test-Path $pythonExe)) {
    throw "QGIS Python was not found at $pythonExe"
}

if (-not (Test-Path $vendorServer)) {
    throw "QGIS MCP server script was not found at $vendorServer"
}

if (-not (Test-Path $packagePath)) {
    throw "Local QGIS MCP packages were not found at $packagePath"
}

$env:PYTHONPATH = ($packagePath, $pywin32Path, $win32Path, $win32LibPath, $qgisSitePackages -join ";")

& $pythonExe -S $vendorServer

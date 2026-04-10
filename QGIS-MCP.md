# QGIS MCP Setup

## Direct outcome

This repository can now expose a local `qgis` MCP server entry through `.mcp.json`, using the installed QGIS 4.0.1 Python runtime and a vendored copy of the third-party `qgis_mcp` bridge.

## Installed local artifacts

- `qgis_mcp_vendor/`: vendored copy of `jjsantos01/qgis_mcp`
- `.qgis-mcp-packages/`: workspace-local Python packages for the QGIS MCP server
- `scripts/start-qgis-mcp.ps1`: launches the MCP server with QGIS Python in `-S` mode
- `scripts/install-qgis-mcp-plugin.ps1`: copies the QGIS plugin into the selected user profile
- `.mcp.json`: adds a `qgis` server definition

## Important constraints

- The QGIS-side plugin must be installed and enabled in QGIS before the MCP server can do useful work.
- The QGIS plugin must be started from the QGIS UI before MCP tools such as `ping` can connect.
- The upstream project states it was tested on QGIS 3.22, not QGIS 4.0.1. This setup is installed, but runtime compatibility with QGIS 4.0.1 remains unverified.
- The upstream server exposes an `execute_code` tool that can run arbitrary PyQGIS code inside QGIS.

## Files and paths

- QGIS Python runtime:
  - `C:\Program Files\QGIS 4.0.1\apps\Python312\python.exe`
- Default QGIS profile plugins directory on Windows per QGIS documentation:
  - `%AppData%\Roaming\QGIS\QGIS3\profiles\default\python\plugins`
- Repository MCP launcher:
  - `D:\opendata\mdopendata\scripts\start-qgis-mcp.ps1`

## Plugin installation

Install the QGIS plugin into the default profile:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-qgis-mcp-plugin.ps1
```

If you use a non-default QGIS profile:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-qgis-mcp-plugin.ps1 -ProfileName your_profile_name
```

Then in QGIS:

1. Open `Plugins` -> `Manage and Install Plugins`.
2. Enable `QGIS MCP`.
3. Open `Plugins` -> `QGIS MCP` -> `QGIS MCP`.
4. Click `Start Server`.
5. Leave the port at `9876` unless you also patch the vendored server.

## MCP usage

Once Codex reloads project MCP configuration and the QGIS plugin server is running, the `qgis` MCP server should become available beside `mdopendata-postgres`.

The current launcher uses:

- vendored server script: `qgis_mcp_vendor\src\qgis_mcp\qgis_mcp_server.py`
- workspace-local package directory: `.qgis-mcp-packages`
- QGIS bundled site-packages: `C:\Program Files\QGIS 4.0.1\apps\Python312\Lib\site-packages`

## Failure mode already handled

QGIS 4.0.1 bundles a `sitecustomize.py` that raises `PermissionError` against `C:\Users\19029\AppData\Local\Microsoft\WindowsApps` in this environment. The launcher avoids that path by running QGIS Python with `-S` and explicitly setting `PYTHONPATH`.

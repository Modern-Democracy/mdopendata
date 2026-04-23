param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
$resolvedPython = (Resolve-Path $python).Path

& $resolvedPython @Args
exit $LASTEXITCODE

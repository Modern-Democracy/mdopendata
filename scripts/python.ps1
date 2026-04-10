param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$python = Join-Path $PSScriptRoot '..\.python\python.exe'
$resolvedPython = (Resolve-Path $python).Path

& $resolvedPython @Args
exit $LASTEXITCODE

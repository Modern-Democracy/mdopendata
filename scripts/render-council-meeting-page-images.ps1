param(
  [int]$Dpi = 150,
  [int]$FirstPage = 1,
  [int]$LastPage = 256
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pdf = Join-Path $repoRoot "docs\charlottetown\council-meetings\05 Regular Meeting of Council Package - May 12, 2026.pdf"
$outDir = Join-Path $repoRoot "data\council-meetings\charlottetown\2026-05-12-regular-council\page-images"
$pdftoppm = (Get-Command pdftoppm -ErrorAction Stop).Source

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

for ($page = $FirstPage; $page -le $LastPage; $page += 1) {
  $target = Join-Path $outDir ("package-page-{0:D3}.png" -f $page)
  if (Test-Path $target) {
    continue
  }
  $prefix = Join-Path $outDir ("render-package-page-{0:D3}" -f $page)
  & $pdftoppm -r $Dpi -f $page -l $page -singlefile -png $pdf $prefix
  if ($LASTEXITCODE -ne 0) {
    throw "pdftoppm failed for package page $page."
  }
  $rendered = "$prefix.png"
  if (-not (Test-Path $rendered)) {
    throw "Expected rendered image was not created for package page $page."
  }
  Move-Item -Force -LiteralPath $rendered -Destination $target
}

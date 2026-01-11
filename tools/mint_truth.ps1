param()

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$verPath = Join-Path $root "app\version.py"
if (-not (Test-Path $verPath)) { throw "Missing app/version.py" }

function Read-TruthVersionFromPy([string]$path) {
  $text = Get-Content -Raw -Path $path
  $m = [regex]::Match($text, 'TRUTH_VERSION\s*=\s*(\d+)')
  if (-not $m.Success) { throw "TRUTH_VERSION not found in $path" }
  return [int]$m.Groups[1].Value
}

function Read-ProjectName([string]$path) {
  $text = Get-Content -Raw -Path $path
  $m = [regex]::Match($text, 'PROJECT_NAME\s*=\s*"(.*?)"')
  if (-not $m.Success) { throw "PROJECT_NAME not found in $path" }
  return $m.Groups[1].Value
}

$project = Read-ProjectName $verPath
$cur = Read-TruthVersionFromPy $verPath
$new = $cur + 1

Write-Host ""
Write-Host "$project current TRUTH_V$cur"
$ans = Read-Host "Mint new truth TRUTH_V$new ? (y/n)"
if ($ans.ToLower() -ne "y") {
  Write-Host "Cancelled."
  exit 0
}

Write-Host ""
Write-Host "Paste TRUTH statement (multi-line)."
Write-Host "Finish with a single line containing: END"

$lines = New-Object System.Collections.Generic.List[string]
while ($true) {
  $line = Read-Host
  if ($line -eq "END") { break }
  $lines.Add($line)
}

$statement = ($lines -join "`n")
if ([string]::IsNullOrWhiteSpace($statement)) { throw "Empty TRUTH statement not allowed." }

$tmpDir = Join-Path $root "_outputs"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$tmpFile = Join-Path $tmpDir ("truth_statement_tmp_{0}.txt" -f ([guid]::NewGuid().ToString("N")))
Set-Content -Path $tmpFile -Value $statement -Encoding UTF8

try {
  python -m tools.truth_manager mint --statement-file $tmpFile
} finally {
  Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
}

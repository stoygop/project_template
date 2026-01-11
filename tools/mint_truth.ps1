# tools/mint_truth.ps1
# One-command truth mint with PROMPT + PASTE
# TERMINATION: Ctrl+Z then Enter (Windows stdin EOF)
# One-click behavior: auto-commit any dirty working tree state before minting.

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host "ERROR: $msg" -ForegroundColor Red
  exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found on PATH" }
if (-not (Test-Path ".git")) { Fail "run from repo root" }

& python -c "import sys; print(sys.executable)" *> $null
if ($LASTEXITCODE -ne 0) { Fail "python not runnable" }

# auto-commit dirty state (patches, etc.)
$porcelain = (& git status --porcelain)
if ($porcelain -and $porcelain.Trim().Length -gt 0) {
  Write-Host "Auto-committing pre-mint changes..." -ForegroundColor Yellow
  git add -A
  git commit -m "AUTO: pre-mint state" | Out-Null
}

# repair any partial last TRUTH entry (missing END) before mint preflight
& python -m tools.repair_truth_md
if ($LASTEXITCODE -ne 0) { Fail "repair_truth_md failed" }

Write-Host ""
Write-Host "PASTE TRUTH STATEMENT. Finish with Ctrl+Z then Enter." -ForegroundColor Cyan
Write-Host ""

$statement = ""
while (($line = [Console]::In.ReadLine()) -ne $null) {
  $statement += $line + "`n"
}
if ($statement.Trim().Length -lt 50) { Fail "truth statement too short or empty" }

# temp file
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $PWD ".truth_statement_$stamp.txt"
Set-Content -Path $tmp -Value $statement -Encoding UTF8

& python -m tools.truth_manager mint --statement-file $tmp
if ($LASTEXITCODE -ne 0) { Fail "truth_manager mint failed" }

Remove-Item -Force $tmp -ErrorAction SilentlyContinue
Write-Host "OK: Minted, pushed." -ForegroundColor Green

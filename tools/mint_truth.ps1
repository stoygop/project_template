# tools/mint_truth.ps1
# One-command truth mint with PROMPT + PASTE
# TERMINATION: Ctrl+Z then Enter (Windows stdin EOF)
# One-click behavior: auto-commit any dirty working tree state before minting.
# Prints NEXT TRUTH version and creates FULL/SLIM zips via tools.truth_manager.

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

# print next version
$next = (& python -c "import re; from pathlib import Path; t=Path('app/version.py').read_text(encoding='utf-8'); m=re.search(r'TRUTH_VERSION\\s*=\\s*(\\d+)', t); print(int(m.group(1))+1)")
if (-not $next) { Fail "could not determine next TRUTH version" }
Write-Host ""
Write-Host ("NEXT TRUTH WILL BE: TRUTH_V{0}" -f $next) -ForegroundColor Cyan
Write-Host ""

Write-Host "PASTE TRUTH STATEMENT. Finish with Ctrl+Z then Enter." -ForegroundColor Cyan
Write-Host ""

$statement = ""
while (($line = [Console]::In.ReadLine()) -ne $null) {
  $statement += $line + "`n"
}
if ($statement.Trim().Length -lt 50) { Fail "truth statement too short or empty" }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $PWD ".truth_statement_$stamp.txt"
Set-Content -Path $tmp -Value $statement -Encoding UTF8

# mint + zip
& python -m tools.truth_manager mint --statement-file $tmp
if ($LASTEXITCODE -ne 0) { Fail "truth_manager mint failed" }

Remove-Item -Force $tmp -ErrorAction SilentlyContinue

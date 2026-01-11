# tools/mint_truth.ps1
# One-command truth mint with PROMPT + PASTE
# TERMINATION: Ctrl+Z then Enter (Windows stdin EOF)
# TRUE one-click behavior: auto-commit any dirty working tree state before minting.

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host "ERROR: $msg" -ForegroundColor Red
  exit 1
}

# prereqs
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found on PATH" }
if (-not (Test-Path ".git")) { Fail "run from repo root" }

# python
& python -c "import sys; print(sys.executable)" *> $null
if ($LASTEXITCODE -ne 0) { Fail "python not runnable" }

# auto-commit dirty state
$porcelain = (& git status --porcelain)
if ($porcelain -and $porcelain.Trim().Length -gt 0) {
  Write-Host "Auto-committing pre-mint changes..." -ForegroundColor Yellow
  git add -A
  git commit -m "AUTO: pre-mint state" | Out-Null
}

Write-Host ""
Write-Host "PASTE TRUTH STATEMENT. Finish with Ctrl+Z then Enter." -ForegroundColor Cyan
Write-Host ""

# read until EOF
$statement = ""
while (($line = [Console]::In.ReadLine()) -ne $null) {
  $statement += $line + "`n"
}

if ($statement.Trim().Length -lt 50) {
  Fail "truth statement too short or empty"
}

# temp file
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $PWD ".truth_statement_$stamp.txt"
Set-Content -Path $tmp -Value $statement -Encoding UTF8

# mint
& python -m tools.truth_manager mint --statement-file $tmp
if ($LASTEXITCODE -ne 0) { Fail "truth_manager mint failed" }

# verify
& python -m tools.doctor --phase pre
if ($LASTEXITCODE -ne 0) { Fail "doctor(pre) failed" }

# commit + push
$versionLine = (& python -c "from app.version import TRUTH_VERSION; print(TRUTH_VERSION)") 2>$null
$versionLine = $versionLine.Trim()

git add TRUTH.md app/version.py _ai_index _truth tools/truth_config.json
git commit -m "Mint $versionLine" | Out-Null
git push | Out-Null

Remove-Item -Force $tmp -ErrorAction SilentlyContinue
Write-Host "OK: Minted $versionLine, DOCTOR OK, pushed." -ForegroundColor Green

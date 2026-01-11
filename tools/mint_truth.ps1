# tools/mint_truth.ps1
# One-command truth mint with PROMPT + PASTE
# TERMINATION: a standalone line containing only: END
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

# Determine current + next version from app/version.py (authoritative integer).
$verJson = (& python -c @"
import json, re
from pathlib import Path
t = Path('app/version.py').read_text(encoding='utf-8')
m = re.search(r'TRUTH_VERSION\s*=\s*(\d+)', t)
if not m:
    raise SystemExit('TRUTH_VERSION not found in app/version.py')
cur = int(m.group(1))
print(json.dumps({'cur': cur, 'next': cur + 1}))
"@)

if ($LASTEXITCODE -ne 0 -or -not $verJson) { Fail "could not determine TRUTH_VERSION from app/version.py" }

try {
  $ver = $verJson | ConvertFrom-Json
} catch {
  Fail "could not parse version info from python helper"
}

$cur = [int]$ver.cur
$next = [int]$ver.next

Write-Host ""
Write-Host ("CURRENT TRUTH VERSION: {0}" -f $cur) -ForegroundColor DarkGray
Write-Host ("PROPOSED NEXT VERSION:  {0}" -f $next) -ForegroundColor Cyan
Write-Host ""

$resp = Read-Host ("Mint new truth (TRUTH_V{0})? (y/n)" -f $next)
if ($resp.ToLower() -ne "y") {
  Write-Host "Aborted." -ForegroundColor Yellow
  exit 0
}

Write-Host "PASTE TRUTH STATEMENT. Input ends when a line containing only 'END' is received." -ForegroundColor Cyan
Write-Host ""

$lines = @()
while ($true) {
  $line = [Console]::ReadLine()
  if ($null -eq $line) {
    Fail "unexpected EOF before END"
  }

  $lines += $line
  if ($line.Trim() -eq "END") {
    break
  }
}

$statement = ($lines -join "`n") + "`n"
if ($statement.Trim().Length -lt 50) { Fail "truth statement too short or empty" }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $PWD ".truth_statement_$stamp.txt"
Set-Content -Path $tmp -Value $statement -Encoding UTF8

# mint + zip
& python -m tools.truth_manager mint --statement-file $tmp
if ($LASTEXITCODE -ne 0) { Fail "truth_manager mint failed" }

Remove-Item -Force $tmp -ErrorAction SilentlyContinue

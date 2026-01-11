# tools/mint_truth.ps1
# One-command truth mint with PROMPT + PASTE
# TERMINATION: Ctrl+Z then Enter (Windows stdin EOF)
# One-click behavior: auto-commit any dirty working tree state before minting.
# Prints NEXT TRUTH version and creates FULL/SLIM zips via tools.truth_manager.

param(
  [switch]$Reseed
)

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

# Reseed mode (destructive): archive TRUTH.md -> TRUTH_LEGACY.md, reset TRUTH_VERSION to 1,
# enable phased truths, and create a new TRUTH.md seeded with TRUTH_V1.
if ($Reseed) {
  $resp2 = Read-Host "RESEED truth epoch? This archives TRUTH.md to TRUTH_LEGACY.md and resets version to 1. Type RESEED to proceed"
  if ($resp2 -ne "RESEED") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
  }
  & python -m tools.truth_manager reseed --force
  if ($LASTEXITCODE -ne 0) { Fail "truth_manager reseed failed" }
  exit 0
}

# Determine current + next version from tools.truth_manager (authoritative, draft-aware).
$statusJson = (& python -m tools.truth_manager status --json)
if ($LASTEXITCODE -ne 0 -or -not $statusJson) { Fail "could not determine truth status from tools.truth_manager" }

try {
  $st = $statusJson | ConvertFrom-Json
} catch {
  Fail "could not parse truth status json"
}

$cur = [int]$st.confirmed
$next = [int]$st.next
$draft = $st.draft_pending


Write-Host ""
Write-Host ""
Write-Host ("CURRENT CONFIRMED TRUTH: TRUTH_V{0}" -f $cur) -ForegroundColor DarkGray
Write-Host ("NEXT VERSION SLOT:        TRUTH_V{0}" -f $next) -ForegroundColor Cyan

if ($draft) {
  $dv = [int]$draft.ver
  Write-Host ("DRAFT PENDING:           TRUTH_V{0}" -f $dv) -ForegroundColor Yellow
  Write-Host ""

  $resp = Read-Host ("Confirm draft (TRUTH_V{0}) now? (y/n)" -f $dv)
  if ($resp.ToLower() -eq "y") {
    & python -m tools.truth_manager confirm-draft
    if ($LASTEXITCODE -ne 0) { Fail "truth_manager confirm-draft failed" }
    exit 0
  }

  Write-Host ""
  $resp2 = Read-Host ("Replace draft (TRUTH_V{0}) with new text? (y/n)" -f $dv)
  if ($resp2.ToLower() -ne "y") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
  }
} else {
  Write-Host ""
  $resp = Read-Host ("Create draft truth (TRUTH_V{0})? (y/n)" -f $next)
  if ($resp.ToLower() -ne "y") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
  }
}

Write-Host ""
Write-Host "PASTE TRUTH STATEMENT. Input ends when a line containing only 'END' is received." -ForegroundColor Cyan
Write-Host ""
Write-Host "PASTE TRUTH STATEMENT. Input ends when a line containing only 'END' is received." -ForegroundColor Cyan
Write-Host ""

$lines = @()
while ($true) {
  $line = [Console]::ReadLine()
  if ($null -eq $line) { Fail "unexpected EOF before END" }
  $lines += $line
  if ($line.Trim() -eq "END") { break }
}

$statement = ($lines -join "`n") + "`n"
if ($statement.Trim().Length -lt 50) { Fail "truth statement too short or empty" }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $PWD ".truth_statement_$stamp.txt"

# Write UTF-8 WITHOUT BOM. (PowerShell 5.1's -Encoding UTF8 writes a BOM, which breaks strict header parsing.)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tmp, $statement, $utf8NoBom)

# mint draft (no version bump / no zips)
$overwriteSwitch = @()
if ($draft) { $overwriteSwitch = @("--overwrite") }

& python -m tools.truth_manager mint-draft --statement-file $tmp $overwriteSwitch
if ($LASTEXITCODE -ne 0) { Fail "truth_manager mint failed" }

Remove-Item -Force $tmp -ErrorAction SilentlyContinue

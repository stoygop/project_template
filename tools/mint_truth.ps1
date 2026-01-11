# tools/mint_truth.ps1
# One-command mint: uses clipboard for the TRUTH statement, mints, runs doctor(pre), commits, pushes.

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host "ERROR: $msg" -ForegroundColor Red
  exit 1
}

# --- prereqs ---
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found on PATH" }
if (-not (Test-Path ".git")) { Fail "run from repo root (folder containing .git)" }

# Ensure python can run
& python -c "import sys; print(sys.executable)" *> $null
if ($LASTEXITCODE -ne 0) { Fail "python not runnable" }

# Must be clean to start (prevents accidental commits)
$porcelain = (& git status --porcelain)
if ($porcelain -and $porcelain.Trim().Length -gt 0) {
  Fail "working tree not clean. Commit/stash first."
}

# --- get statement from clipboard ---
$statement = ""
try { $statement = (Get-Clipboard -Raw) } catch { Fail "could not read clipboard" }
if (-not $statement -or $statement.Trim().Length -lt 10) {
  Fail "clipboard is empty. Copy the full TRUTH statement text, then rerun."
}

# --- write statement file (temp) ---
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $PWD ".truth_statement_$stamp.txt"
Set-Content -Path $tmp -Value $statement -Encoding UTF8

# --- mint ---
& python -m tools.truth_manager mint --statement-file $tmp
if ($LASTEXITCODE -ne 0) { Fail "truth_manager mint failed" }

# --- verify ---
& python -m tools.doctor --phase pre
if ($LASTEXITCODE -ne 0) { Fail "doctor(pre) failed" }

# --- determine version for commit message ---
$versionLine = (& python -c "from app.version import TRUTH_VERSION; print(TRUTH_VERSION)") 2>$null
if (-not $versionLine) { $versionLine = "TRUTH" }
$versionLine = $versionLine.Trim()

# --- commit + push ---
& git add TRUTH.md app/version.py _ai_index _truth tools/truth_config.json
& git commit -m "Mint $versionLine"
if ($LASTEXITCODE -ne 0) { Fail "git commit failed" }

& git push
if ($LASTEXITCODE -ne 0) { Fail "git push failed" }

# Cleanup temp statement file
Remove-Item -Force $tmp -ErrorAction SilentlyContinue

Write-Host "OK: Minted $versionLine, DOCTOR OK, pushed." -ForegroundColor Green

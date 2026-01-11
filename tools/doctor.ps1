# tools/doctor.ps1
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

Write-Host ""
Write-Host "=== DOCTOR ==="
Write-Host "Root: $root"
Write-Host ""

& python -m tools.doctor
exit $LASTEXITCODE

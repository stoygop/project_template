param(
  [Parameter(Mandatory=$true)]
  [string]$Name,

  [Parameter(Mandatory=$false)]
  [string]$Dest = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

Write-Host "NEW_PROJECT: Name=$Name"
Write-Host "NEW_PROJECT: Dest=$Dest"

python -m tools.new_project --name "$Name" --dest "$Dest"
if ($LASTEXITCODE -ne 0) {
  throw "NEW_PROJECT FAILED (exit=$LASTEXITCODE)"
}

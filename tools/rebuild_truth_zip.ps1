param(
  [Parameter(Mandatory=$true)]
  [int]$Version
)

$ErrorActionPreference = "Stop"

function Read-ProjectName([string]$path) {
  $text = Get-Content -Raw -Path $path
  $m = [regex]::Match($text, 'PROJECT_NAME\s*=\s*"(.*?)"')
  if (-not $m.Success) { throw "PROJECT_NAME not found in $path" }
  return $m.Groups[1].Value
}

function Get-RepoFiles([string]$root) {
  # Compare using normalized forward-slash paths (no regex)
  $excludeParts = @(
    "/.git/",
    "/__pycache__/",
    "/_logs/",
    "/_outputs/",
    "/_build/",
    "/_dist/",
    "/_truth/",
    "/.venv/",
    "/.env/"
  )

  Get-ChildItem -Path $root -Recurse -Force -File |
    Where-Object {
      $p = ($_.FullName -replace "\\","/")  # normalize
      foreach ($x in $excludeParts) {
        if ($p.Contains($x)) { return $false }
      }
      return $true
    } |
    Select-Object -ExpandProperty FullName -Unique
}

function New-ZipFromFileList([string]$root, [string[]]$files, [string]$zipPath) {
  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem

  $zipDir = Split-Path -Parent $zipPath
  if (-not (Test-Path $zipDir)) { New-Item -ItemType Directory -Force -Path $zipDir | Out-Null }

  $tmp = Join-Path $zipDir ("tmp_{0}.zip" -f ([guid]::NewGuid().ToString("N")))
  if (Test-Path $tmp) { Remove-Item $tmp -Force }

  $zip = [System.IO.Compression.ZipFile]::Open($tmp, [System.IO.Compression.ZipArchiveMode]::Create)
  try {
    foreach ($f in $files) {
      $rel = $f.Substring($root.Length).TrimStart('\','/')
      $rel = $rel -replace '\\', '/'

      $entry = $zip.CreateEntry($rel, [System.IO.Compression.CompressionLevel]::Optimal)
      $entryStream = $entry.Open()
      try {
        $fs = [System.IO.File]::Open($f, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try { $fs.CopyTo($entryStream) } finally { $fs.Dispose() }
      } finally {
        $entryStream.Dispose()
      }
    }
  } finally {
    $zip.Dispose()
  }

  if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
  Move-Item -Path $tmp -Destination $zipPath -Force
}

# --- main ---
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$verPath = Join-Path $root "app\version.py"
if (-not (Test-Path $verPath)) { throw "Missing app/version.py" }

$project = Read-ProjectName $verPath
$zipRoot = Join-Path $root "_truth"
$zipPath = Join-Path $zipRoot ("{0}_TRUTH_V{1}.zip" -f $project, $Version)

$files = Get-RepoFiles $root
New-ZipFromFileList -root $root -files $files -zipPath $zipPath

Write-Host "OK: rebuilt ZIP for TRUTH_V$Version"
Write-Host "ZIP: $zipPath"

#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Build images, pull Ollama models, export Docker images + model blobs for offline transfer.
#>
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$OutDir = Join-Path $PSScriptRoot "offline-package"
$ImagesDir = Join-Path $OutDir "images"
$ModelsDir = Join-Path $OutDir "ollama-models"
$DbDir = Join-Path $OutDir "db"

New-Item -ItemType Directory -Force -Path $ImagesDir, $ModelsDir, $DbDir | Out-Null

if (-not (Test-Path -LiteralPath ".env")) {
  Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

Write-Host "==> Building application images..."
docker compose build

Write-Host "==> Ensuring Ollama is up to pull models..."
docker compose up -d ollama
docker compose run --rm ollama-init

Write-Host "==> Exporting images..."
$images = @(
  "postgres:17-alpine",
  "ollama/ollama:latest",
  "nginx:1.27-alpine"
)
# Project-built images
$built = docker compose images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -and $_ -ne ":<none>" } | Select-Object -Unique
$all = @($images + $built) | Select-Object -Unique

$tar = Join-Path $ImagesDir "pfe-images.tar"
docker save -o $tar @($all)
Write-Host "Saved images to $tar"

Write-Host "==> Saving Ollama model volume archive..."
docker run --rm -v pfe-data-maturity_ollama_data:/data -v "${ModelsDir}:/backup" alpine `
  tar czf /backup/ollama_data.tar.gz -C /data .
# Volume name may vary with project name — also try compose volume
if (-not (Test-Path (Join-Path $ModelsDir "ollama_data.tar.gz"))) {
  $vol = docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "ollama_data" } | Select-Object -First 1
  if ($vol) {
    docker run --rm -v "${vol}:/data" -v "${ModelsDir}:/backup" alpine tar czf /backup/ollama_data.tar.gz -C /data .
  }
}

Write-Host "==> Copying PostgreSQL dump..."
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "db\local-snapshot.sql") -Destination (Join-Path $DbDir "local-snapshot.sql") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot ".env.example") -Destination (Join-Path $OutDir ".env.example") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README_DOCKER.md") -Destination (Join-Path $OutDir "README_DOCKER.md") -Force -ErrorAction SilentlyContinue

Write-Host "==> Writing SHA-256 checksums..."
Get-ChildItem -LiteralPath $OutDir -Recurse -File |
  Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
  ForEach-Object {
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
    $rel = $_.FullName.Substring($OutDir.Length).TrimStart('\', '/')
    "{0}  {1}" -f $hash.Hash.ToLowerInvariant(), ($rel -replace '\\', '/')
  } | Set-Content -LiteralPath (Join-Path $OutDir "SHA256SUMS.txt") -Encoding utf8

Write-Host "Offline package ready in: $OutDir"
Write-Host "Transfer this folder with the four application sources (or pre-built images only)."

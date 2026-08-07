#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Restore images + Ollama models from offline-package, then start the stack.
#>
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$OutDir = Join-Path $PSScriptRoot "offline-package"
$ImagesTar = Join-Path $OutDir "images\pfe-images.tar"
$ModelsTar = Join-Path $OutDir "ollama-models\ollama_data.tar.gz"
$DbDump = Join-Path $OutDir "db\local-snapshot.sql"

if (-not (Test-Path -LiteralPath ".env")) {
  $example = Join-Path $OutDir ".env.example"
  if (Test-Path -LiteralPath $example) {
    Copy-Item -LiteralPath $example -Destination ".env"
  } elseif (Test-Path -LiteralPath ".env.example") {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
  }
}

if (Test-Path -LiteralPath $DbDump) {
  New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "db") | Out-Null
  Copy-Item -LiteralPath $DbDump -Destination (Join-Path $PSScriptRoot "db\local-snapshot.sql") -Force
}

if (Test-Path -LiteralPath $ImagesTar) {
  Write-Host "==> Loading Docker images..."
  docker load -i $ImagesTar
} else {
  Write-Warning "No image archive found at $ImagesTar — ensure images exist locally or network is available."
}

Write-Host "==> Starting Ollama volume restore (if archive present)..."
docker compose up -d postgres ollama
Start-Sleep -Seconds 5

if (Test-Path -LiteralPath $ModelsTar) {
  $vol = docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "ollama_data$" } | Select-Object -First 1
  if (-not $vol) {
    docker compose up -d ollama | Out-Null
    $vol = docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "ollama_data$" } | Select-Object -First 1
  }
  if ($vol) {
    docker run --rm -v "${vol}:/data" -v "$(Split-Path -Parent $ModelsTar):/backup" alpine `
      sh -c "cd /data && tar xzf /backup/ollama_data.tar.gz"
    Write-Host "Restored Ollama models into volume $vol"
  }
}

Write-Host "==> Starting full stack..."
docker compose up -d
docker compose ps
Write-Host "Done. Do NOT run: docker compose down -v"

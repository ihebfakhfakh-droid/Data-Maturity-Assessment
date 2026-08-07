#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Start the Data Maturity platform with Docker Compose (connected mode).
#>
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath ".env")) {
  if (Test-Path -LiteralPath ".env.example") {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example — edit secrets before production use."
  } else {
    throw ".env is missing and .env.example was not found."
  }
}

docker compose config | Out-Null
docker compose up --build -d
docker compose ps
Write-Host ""
Write-Host "Frontend: http://localhost:$($env:FRONTEND_PORT ?? '5173')"
Write-Host "Backend : http://localhost:$($env:BACKEND_PORT ?? '9090')"
Write-Host "Never run: docker compose down -v"

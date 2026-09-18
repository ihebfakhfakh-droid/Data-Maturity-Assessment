#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Stop containers without deleting volumes (preserves PostgreSQL, Ollama models, evidences).
#>
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

docker compose down
Write-Host "Containers stopped. Volumes preserved (postgres_data, ollama_data, backend_evidence)."
Write-Host "Do NOT use: docker compose down -v"

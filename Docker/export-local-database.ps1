# Export the local PostgreSQL database into Docker/db/local-snapshot.sql
# Requires Docker Desktop (host.docker.internal reaches the host DB).
#
# Fresh Docker import:
#   cd Docker
#   docker compose down -v
#   docker compose up --build -d

$ErrorActionPreference = "Stop"
node (Join-Path $PSScriptRoot "export-local-database.js")

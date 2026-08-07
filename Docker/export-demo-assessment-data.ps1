# Re-export demo assessment answers from the local PostgreSQL database.
# Requires Docker Desktop (uses host.docker.internal to reach the host DB).
#
# Output: PFEBACKEND/src/main/resources/db/demo-assessment-answers.csv
# Then rebuild Docker backend:
#   cd Docker
#   docker compose up --build -d backend
#
# For a completely clean database:
#   docker compose down -v
#   docker compose up --build -d

$ErrorActionPreference = "Stop"
node (Join-Path $PSScriptRoot "export-demo-data.js")

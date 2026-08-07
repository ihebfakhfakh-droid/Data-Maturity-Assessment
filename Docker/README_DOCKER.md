# Data Maturity Assessment Platform — Docker Guide

Official Docker Compose configuration for the PFE platform.

## Architecture

| Service | Role | Host URL |
|---------|------|----------|
| `frontend` | React/Vite production build served by Nginx | http://localhost:5173 |
| `backend` | Spring Boot API | http://localhost:9090 |
| `ai-recommendation` | FastAPI Best Path + PDF recommendations | http://localhost:8002 |
| `evaluate-evidence` | FastAPI Acceptance Criteria + PDF | http://localhost:8003 |
| `postgres` | PostgreSQL 17 | localhost:5432 (default) |
| `ollama` | Shared LLM runtime | http://localhost:11434 |
| `ollama-init` | One-shot model pull (`qwen3.5:9b`, `qwen2.5vl:7b`) | (no port) |

The browser only uses `localhost`. Nginx proxies `/api` to `backend:9090` inside the Docker network.

**`ai-evidence-rating-service` is excluded** and must not be started.

## Prerequisites

- Windows 10/11 with **Docker Desktop** (WSL2 backend recommended)
- At least **16 GB RAM** recommended (32 GB preferred while models load on CPU)
- **~25–40 GB** free disk (Ollama models are large: `qwen3.5:9b` + `qwen2.5vl:7b`)
- CPU-only works by default (slow LLM calls; timeouts are set high)

## Important — never delete volumes

```powershell
# FORBIDDEN — destroys PostgreSQL data, evidences, and Ollama models
docker compose down -v
```

To stop safely:

```powershell
.\stop-docker.ps1
# or
docker compose down
```

## Connected start (recommended)

From the `Docker` folder (sibling of `PFEBACKEND`, `PFEFRONTEND`, `ai-recommendation-service`, `evaluate evidence`):

```powershell
cd Docker
Copy-Item .env.example .env
# Edit .env: set POSTGRES_PASSWORD / JWT secret for any shared machine
docker compose config
docker compose up --build -d
docker compose ps
```

Or:

```powershell
.\start-docker.ps1
```

### First boot duration

- Image builds: several minutes
- Ollama model download (first time only): can take **30–90+ minutes** depending on network and disk
- Subsequent starts reuse the `ollama_data` volume (no re-download)

### Verify

```powershell
docker compose ps
docker compose logs -f --tail=100 backend
curl http://localhost:9090/
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:5173/
docker compose exec ollama ollama list
```

Expected models:

```text
qwen3.5:9b
qwen2.5vl:7b
```

## `.env` configuration

Copy `.env.example` → `.env`. Key variables:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_*` | Database name/user/password/host port |
| `BACKEND_PORT` | Spring port (default `9090`) |
| `APP_AI_RECOMMENDATION_BASE_URL` | Internal URL `http://ai-recommendation:8002` |
| `ACCEPTANCE_CRITERIA_BASE_URL` | Internal URL `http://evaluate-evidence:8003` |
| `OLLAMA_BASE_URL` | Internal URL `http://ollama:11434` |
| `RECOMMENDATION_OLLAMA_MODEL` | `qwen3.5:9b` |
| `ACCEPTANCE_OLLAMA_MODEL` | `qwen2.5vl:7b` |
| `OLLAMA_DATA_PATH` | Named volume `pfe_ollama_data` (default) **or** a host path such as `C:/Users/YOU/.ollama` to reuse local models |
| `APP_DEMO_CLEANUP_ENABLED` | Keep `false` with the full SQL snapshot |
| `APP_QUESTIONNAIRE_SEED_ENABLED` | Keep `false` with the full SQL snapshot |

Do not put production secrets in Git. Keep `.env` local.

If `POSTGRES_PORT=5432` or `OLLAMA_PORT=11434` conflicts with software already running on the host, change only the **host** ports in `.env` (container ports stay the same).

## PostgreSQL data

`db/local-snapshot.sql` is imported **only when the `postgres_data` volume is empty** (first start).

It contains the validated dataset (users, roles, projects, frameworks, assessments, answers, evidences, …).

### Backup

```powershell
docker compose exec -T postgres pg_dump -U pfe_user -d pfe_backend_db --no-owner --no-acl > backup-$(Get-Date -Format yyyyMMdd).sql
```

### Restore into a fresh volume

1. `docker compose down` (without `-v` if you still need other volumes)
2. Remove **only** the postgres volume if you intentionally want a re-import:  
   `docker volume rm <project>_postgres_data`  
   (confirm the name with `docker volume ls`)
3. Place the dump as `db/local-snapshot.sql`
4. `docker compose up -d`

## Optional NVIDIA GPU

CPU is the default. If NVIDIA Container Toolkit is installed:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Absence of a GPU must not block the normal compose file.

## Offline package

On a machine with network:

```powershell
.\prepare-offline-package.ps1
```

This builds/exports images, archives Ollama models, copies the SQL dump, and writes `SHA256SUMS.txt` under `offline-package/`.

On the offline machine (Docker Desktop installed, images transferred):

```powershell
.\restore-offline-package.ps1
```

Also ship the four application folders if you need to rebuild:

- `PFEBACKEND`
- `PFEFRONTEND`
- `ai-recommendation-service`
- `evaluate evidence`

## Logs

```powershell
docker compose logs -f backend
docker compose logs -f ai-recommendation
docker compose logs -f evaluate-evidence
docker compose logs -f ollama
docker compose logs ollama-init
```

## Common issues

| Symptom | Fix |
|---------|-----|
| Port 5432 already used | Set `POSTGRES_PORT=5433` in `.env` |
| Frontend API errors / CORS | Use http://localhost:5173 (Nginx `/api` proxy). Never open `http://backend:9090` in the browser |
| Ollama model missing | `docker compose logs ollama-init` then `docker compose run --rm ollama-init` |
| LLM timeouts | Normal on CPU; wait or check `OLLAMA_TIMEOUT_SECONDS` |
| Empty clients after start | Ensure `APP_DEMO_CLEANUP_ENABLED=false` and volume was initialized from `local-snapshot.sql` |
| SPA refresh 404 | Nginx `try_files` must serve `index.html` (bundled in `nginx.conf`) |
| Path with spaces (`evaluate evidence`) | Compose context already quotes the path — do not rename the folder |

## Demo accounts (from validated dump)

When `APP_DEMO_CLEANUP_ENABLED=false` and the full snapshot is imported:

```text
ADMIN      admin@pfe.local              Admin@12345
MANAGER    omartrabelsi@manager         123456omar
CONSULTANT mayssabenjmaa@consultant     123456mayssa
CLIENT     oussemalazez@client          nsTp3U5hRkuE
CLIENT     youssefbenjmaa@client        FUN8s#MbjR2M
```

Other users keep the passwords already stored in PostgreSQL (bootstrap does not overwrite them when disabled).

## Evidence files note

The SQL dump references evidence metadata. Physical files live in the Docker volume `pfe_backend_evidence_data`. Files that existed only on a developer machine are not in the dump; new uploads in Docker are persisted in that volume.

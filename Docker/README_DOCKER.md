# Data Maturity Assessment Platform — Docker Guide

Optimized Docker Compose configuration for the PFE platform — **3-container architecture**.

## Architecture

| Service | Role | Host URL |
|---------|------|----------|
| `app` | Nginx + Spring Boot + Python AI services (merged) | http://localhost:80 / http://localhost:9090 |
| `postgres` | PostgreSQL 17 | localhost:5432 (default) |
| `ollama` | Ollama LLM runtime | http://localhost:11434 |

### `app` container internals (managed by supervisord)

| Process | Port | Role |
|---------|------|------|
| Nginx | 80 | Serves React/Vite frontend + proxies `/api` to backend |
| Spring Boot | 9090 | Backend API |
| uvicorn (recommendation) | 8002 | AI Best Path + PDF recommendations |
| uvicorn (evaluation) | 8003 | Acceptance Criteria evaluation + PDF |

The browser only uses `localhost`. Nginx proxies `/api` to `127.0.0.1:9090` inside the container.
Spring Boot calls Python services via `127.0.0.1:8002` and `127.0.0.1:8003`.

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

### First boot duration

- Image builds: several minutes
- Ollama model download (first time only): can take **30–90+ minutes** depending on network and disk
- Subsequent starts reuse the `pfe_ollama_data` volume (no re-download)

### Verify

```powershell
docker compose ps
docker compose logs -f --tail=100 app
curl http://localhost:9090/
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost/
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
| `POSTGRES_*` | Database name/user/password |
| `BACKEND_PORT` | Spring port (default `9090`) |
| `APP_AI_RECOMMENDATION_BASE_URL` | Internal URL `http://127.0.0.1:8002` |
| `ACCEPTANCE_CRITERIA_BASE_URL` | Internal URL `http://127.0.0.1:8003` |
| `OLLAMA_BASE_URL` | Internal URL `http://ollama:11434` |
| `RECOMMENDATION_OLLAMA_MODEL` | `qwen3.5:9b` |
| `ACCEPTANCE_OLLAMA_MODEL` | `qwen2.5vl:7b` |
| `OLLAMA_DATA_PATH` | Named volume `pfe_ollama_data` (default) **or** a host path to reuse local models |
| `APP_DEMO_CLEANUP_ENABLED` | Keep `false` with the full SQL snapshot |
| `APP_QUESTIONNAIRE_SEED_ENABLED` | Keep `false` with the full SQL snapshot |
| `FRONTEND_PORT` | Host port for Nginx/frontend (default `80`) |

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

## Logs

```powershell
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f ollama
```

Since the `app` container runs all processes via supervisord, individual service logs are available at:
- `/var/log/nginx.out.log`, `/var/log/nginx.err.log`
- `/var/log/backend.out.log`, `/var/log/backend.err.log`
- `/var/log/ai-recommendation.out.log`, `/var/log/ai-recommendation.err.log`
- `/var/log/evaluate-evidence.out.log`, `/var/log/evaluate-evidence.err.log`

View via: `docker compose exec app cat /var/log/ai-recommendation.out.log`

## Common issues

| Symptom | Fix |
|---------|-----|
| Port 5432 already used | Set `POSTGRES_PORT=5433` in `.env` |
| Frontend API errors / CORS | Use http://localhost (Nginx `/api` proxy). Never open `http://localhost:9090` in the browser |
| Ollama model missing | Check `docker compose logs app` for ollama-init messages |
| LLM timeouts | Normal on CPU; wait or check `OLLAMA_TIMEOUT_SECONDS` |
| Empty clients after start | Ensure `APP_DEMO_CLEANUP_ENABLED=false` and volume was initialized from `local-snapshot.sql` |
| SPA refresh 404 | Nginx `try_files` must serve `index.html` (bundled in `nginx.conf`) |
| Path with spaces (`evaluate evidence`) | Compose context already quotes the path — do not rename the folder |
| `supervisord` not found | Ensure Dockerfile build completed — supervisor is installed via pip3 in the runtime image |

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

## Migration from 6-container architecture

The previous architecture had 6 separate containers. The refactored 3-container architecture:

1. **Consolidated `app` container**: Combines frontend (Nginx), backend (Spring Boot), and both Python AI services (recommendation + evaluation) under supervisord
2. **Internal communication**: Backend → Python services now use `127.0.0.1` instead of Docker DNS service names
3. **Simplified networking**: Only `app`, `postgres`, and `ollama` need to communicate across containers
4. **No more `ollama-init` container**: Model initialization is handled via `start.sh` and `ollama-init.sh` in the `app` container

### Environment variable changes

| Old Variable | New Value |
|-------------|-----------|
| `APP_AI_RECOMMENDATION_BASE_URL=http://ai-recommendation:8002` | `http://127.0.0.1:8002` |
| `ACCEPTANCE_CRITERIA_BASE_URL=http://evaluate-evidence:8003` | `http://127.0.0.1:8003` |
| `FRONTEND_PORT=5173` | `80` |
| `OLLAMA_PORT=11435` | `11434` |
| `POSTGRES_PORT=5433` | `5432` |

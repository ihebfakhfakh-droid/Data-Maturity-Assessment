# Data Maturity Assessment Platform

Évaluation de la maturité des données (NDI) — plateforme multi-modules avec Spring Boot, React, et services IA (Ollama).

---

## 🏗️ Architecture

| Service | Conteneur | Technologie | Port(s) | Rôle |
|---------|-----------|------------|---------|------|
| **App** | `pfe-app` | Nginx + Spring Boot 4.0.5 + Python FastAPI (supervisord) | 80, 9090, 8002, 8003 | Frontend, API REST, auth JWT, services IA (Best Path + Acceptance Criteria) |
| **PostgreSQL** | `pfe-postgres` | PostgreSQL 17-alpine | 5432 | Base de données |
| **Ollama** | `pfe-ollama` | Ollama | 11434 | Runtime LLM partagé (`qwen3.5:9b`, `qwen2.5vl:7b`) |

> ⚡ **Architecture optimisée** : le projet présente **3 conteneurs**. Les services frontend (Nginx), backend (Spring Boot) et services IA (FastAPI) sont fusionnés dans un seul conteneur `app` géré par **supervisord**.

```
Browser → localhost:80 (Nginx dans pfe-app)
              │
              ├── /api → Spring Boot :9090 (dans pfe-app)
              ├── /api/ai → AI Recommendation :8002 (dans pfe-app)
              └── /api/acceptance → Evaluate Evidence :8003 (dans pfe-app)
```

---

## 📋 Prérequis

### Outils requis

- **Git**
- **Docker Desktop** 
- **ollama**
- **Node.js 22+**** 
- **PostgreSQL 17**** 
- **Maven 3.9+**** 


### Ressources

- **16 Go RAM minimum** (32 Go recommandé)
- **25–40 Go disque** (modèles Ollama : `qwen3.5:9b` + `qwen2.5vl:7b`)
- **CPU uniquement** fonctionne (plus lent pour les appels LLM)

---

## 🚀 Méthode 1 — Avec Docker Compose (recommandée)

### Étape 1 — Cloner le dépôt

```powershell
git clone <url-du-depot>
cd pfeversion4
```

### Étape 2 — Configurer l'environnement

```powershell
cd Docker
Copy-Item .env.example .env
```

Éditer `.env` si nécessaire :

| Variable | Valeur par défaut | À modifier si |
|----------|-------------------|---------------|
| `POSTGRES_PASSWORD` | `123456` | Machine partagée |
| `APP_AUTH_JWT_SECRET` | `change-this-super-secret-key-at-least-32-characters` | Machine partagée |
| `APP_AUTH_BOOTSTRAP_ADMIN_PASSWORD` | `Admin@12345` | Sécurité |
| `POSTGRES_PORT` | `5432` | Conflit de port |
| `OLLAMA_PORT` | `11434` | Conflit de port |
| `FRONTEND_PORT` | `80` | Conflit de port |

> ⚠️ **Ne jamais modifier** : `APP_DEMO_CLEANUP_ENABLED=false`, `APP_QUESTIONNAIRE_SEED_ENABLED=false` (conservation du dump validé).

### Étape 3 — Lancer
1) il faut ouvrir docker desktop 
2) build images
```powershell
cd Docker
docker compose config
docker compose build --no-cache
```
3) lancer les images 
```powershell
docker compose up 
```


### Étape 4 — Vérifier

```powershell
docker compose ps
```

Services attendus : `pfe-app`, `pfe-postgres`, `pfe-ollama`.

```powershell
# Health checks
curl http://localhost:9090/
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost/

# Vérifier les modèles Ollama
docker compose exec ollama ollama list
# Attendu : qwen3.5:9b, qwen2.5vl:7b
```

### Étape 5 — Première fois

- **Build des images** : plusieurs minutes (un seul build multi-stage pour tous les services)
- **Téléchargement des modèles Ollama** (`ollama-init`) : **30–90+ minutes** la première fois
- **Démarrages suivants** : réutilise les volumes (`pfe_postgres_data_full`, `pfe_backend_evidence_data`, `pfe_ollama_data`) — pas de re-téléchargement

### Arrêt

```powershell
docker compose down
```

> ❌ **JAMAIS** `docker compose down -v` — détruit les volumes PostgreSQL, evidences et Ollama.

### Accès

| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 |
| Backend API | http://localhost:9090 |
| AI Recommendation | http://localhost:8002 |
| Evaluate Evidence | http://localhost:8003 |
| Ollama | http://localhost:11434 |

### Logs

```powershell
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f ollama
```

> Le conteneur `app` utilise **supervisord** — les logs individuels des services sont aussi accessibles via :
> `docker compose exec app cat /var/log/ai-recommendation.out.log`
> `docker compose exec app cat /var/log/evaluate-evidence.out.log`

### Sauvegarde PostgreSQL

```powershell
docker compose exec -T postgres pg_dump -U pfe_user -d pfe_backend_db --no-owner --no-acl > backup-$(Get-Date -Format yyyyMMdd).sql
```

---

## 🔧 Méthode 2 — Sans Docker (manuel)

### 2.1 — Base de données (PostgreSQL)

```powershell
# Installer PostgreSQL 17, puis :
createdb pfe_backend_db
psql -d pfe_backend_db -U pfe_user -f Docker/db/local-snapshot.sql
```

### 2.2 — Ollama

```powershell
ollama serve
# Dans un autre terminal :
ollama pull qwen3.5:9b
ollama pull qwen2.5vl:7b
```

### 2.3 — Backend (PFEBACKEND)

```powershell
cd PFEBACKEND
mvn clean package -DskipTests
java -jar target/*.jar
```

Variables d'environnement requises :

```
SERVER_PORT=9090
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/pfe_backend_db
SPRING_DATASOURCE_USERNAME=pfe_user
SPRING_DATASOURCE_PASSWORD=<mot-de-passe>
APP_AUTH_JWT_SECRET=<jwt-secret-32-caracteres>
APP_AUTH_BOOTSTRAP_ENABLED=false
APP_QUESTIONNAIRE_SEED_ENABLED=false
APP_DEMO_CLEANUP_ENABLED=false
APP_AI_RECOMMENDATION_BASE_URL=http://localhost:8002
ACCEPTANCE_CRITERIA_BASE_URL=http://localhost:8003
OLLAMA_BASE_URL=http://localhost:11434
```

### 2.4 — Frontend (PFEFRONTEND)

```powershell
cd PFEFRONTEND
npm install
npm run dev
```

Le proxy Vite envoie `/api` vers `http://localhost:9090` (configuré dans `vite.config.js`).

### 2.5 — AI Recommendation Service

```powershell
cd ai-recommendation-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 2.6 — Evaluate Evidence Service

```powershell
cd "evaluate evidence\evaluate evidence\acceptance critiria"
pip install -r requirements.txt
uvicorn api_server:app --host 0.0.0.0 --port 8003
```

> ⚠️ Le dossier contient des **espaces** dans les noms — respecter le chemin exact.

### Ordre de démarrage (manuel)

1. PostgreSQL
2. Ollama + `ollama pull`
3. Backend
4. AI Recommendation
5. Evaluate Evidence
6. Frontend

---

## 🧪 Tests

> À compléter avec les identifiants et scénarios de test.

### Test — Connexion Admin

| Champ | Valeur |
|-------|--------|
| Email | `admin@pfe.local` |
| Mot de passe | `Admin@12345` |
| Rôle attendu | ADMIN |

### Test — Connexion Manager

| Champ | Valeur |
|-------|--------|
| Email |omartrabelsi@manager |
| Mot de passe | 123456omar|
| Rôle attendu | MANAGER |

### Test — Connexion Consultant

| Champ | Valeur |
|-------|--------|
| Email |wassimbenyedder@consultant |
| Mot de passe |123456wassim |
| Rôle attendu | CONSULTANT |

### Test — Connexion Client

| Champ | Valeur |
|-------|--------|
| Email | oussemalazez@client|
| Mot de passe | nsTp3U5hRkuE|
| Rôle attendu | CLIENT |

| Champ | Valeur |
|-------|--------|
| Email | mohsenbenjmaa@client|
| Mot de passe | 7BEFydqejJUw|
| Rôle attendu | CLIENT |

### Test — Endpoints API

```powershell
# Health check général
curl http://localhost:9090/

# Health check IA
curl http://localhost:8002/health
curl http://localhost:8003/health

# Authentification
curl -X POST http://localhost:9090/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@pfe.local","password":"Admin@12345"}'
```

### Test — Évaluation complète

- [ ] Connexion en tant que CLIENT
- [ ] Accès à un projet de questionnaire
- [ ] Réponse aux questions
- [ ] Soumission de l'évaluation
- [ ] Génération de recommandations IA
- [ ] Upload de preuves (evidence)
- [ ] Validation des critères d'acceptance

---


## 📁 Structure des dossiers

```
pfeversion4/
├── README.md                     ← Ce fichier
├── Docker/
│   ├── Dockerfile                ← Build multi-stage : Nginx + Spring Boot + Python (services IA)
│   ├── docker-compose.yml        ← Orchestration 3 conteneurs (app, postgres, ollama)
│   ├── docker-compose.gpu.yml    ← Configuration GPU (optionnelle)
│   ├── .env.example              ← Variables d'environnement
│   ├── .env                      ← À créer (copy de .env.example)
│   ├── nginx.conf                ← Reverse proxy Nginx
│   ├── supervisord.conf          ← Gestion des processus internes (app)
│   ├── requirements.txt          ← Dépendances Python (supervisor, nginx, etc.)
│   ├── backend.Dockerfile        ← Ancien Dockerfile backend (obsolète)
│   ├── frontend.Dockerfile       ← Ancien Dockerfile frontend (obsolète)
│   ├── ai-recommendation.Dockerfile ← Ancien Dockerfile IA (obsolète)
│   ├── evaluate-evidence.Dockerfile ← Ancien Dockerfile évaluation (obsolète)
│   ├── start-docker.ps1
│   ├── stop-docker.ps1
│   ├── scripts/
│   │   ├── ollama-init.sh        ← Script de pull des modèles
│   │   └── start.sh              ← Script de démarrage supervisord
│   ├── db/
│   │   └── local-snapshot.sql    ← Dump initialisé
│   └── README_DOCKER.md          ← Documentation Docker détaillée
├── PFEBACKEND/                   ← Spring Boot (Java 21)
│   └── src/main/java/org/example/pfebackend/
│       ├── config/
│       ├── auth/
│       ├── user/
│       ├── assessment/           ← Module cœur
│       ├── evidence/
│       ├── project/
│       ├── staff/
│       └── api/
├── PFEFRONTEND/                  ← React 19 / Vite
│   └── src/
│       ├── App.jsx
│       ├── auth/
│       ├── pages/
│       └── components/
├── ai-recommendation-service/    ← FastAPI + Ollama (qwen3.5:9b)
│   ├── app/
│   ├── prompts/
│   └── requirements.txt
├── evaluate evidence/            ← FastAPI + Streamlit (qwen2.5vl:7b)
│   └── evaluate evidence/
│       └── acceptance critiria/
│           ├── api_server.py
│           ├── evaluation_service.py
│           ├── pdf_report.py
│           └── requirements.txt
```

---


## 🐛 Dépannage

| Symptôme | Solution |
|----------|----------|
| Port 5432 déjà utilisé | `POSTGRES_PORT=5433` dans `.env` |
| Port 11434 déjà utilisé | `OLLAMA_PORT=11435` dans `.env` |
| Port 5173 déjà utilisé (ancien) | Le port frontend est maintenant `80` via `FRONTEND_PORT` |
| Erreurs API Frontend / CORS | Utiliser `http://localhost` (Nginx `/api` proxy) |
| Modèle Ollama manquant | `docker compose logs app` puis vérifier `ollama-init.sh` |
| LLM timeouts | Normal sur CPU ; attendre ou augmenter `OLLAMA_TIMEOUT_SECONDS` |
| Clients vides après démarrage | Vérifier `APP_DEMO_CLEANUP_ENABLED=false` et le volume |
| SPA refresh 404 | Nginx `try_files` sert `index.html` (dans `nginx.conf`) |
| Dossier avec espaces | Le compose context already quotes le chemin — ne pas renommer |
| Build Maven échoue | `mvn clean` puis relancer |
| Frontend npm install échoue | Supprimer `node_modules` et `package-lock.json`, puis `npm install` |
| Ollama 16+ Go RAM | Fermer les applications gourmandes en RAM |

---

## 📝 Notes

- Le dump `db/local-snapshot.sql` est importé **uniquement quand le volume `postgres_data` est vide** (premier démarrage).
- Les fichiers evidence physiques vivent dans le volume Docker `pfe_backend_evidence_data`.
- Les fichiers evidence qui existaient uniquement sur une machine développeur ne sont pas dans le dump.
- Les nouveaux uploads en Docker sont persistés dans ce volume.
- Ne jamais utiliser `docker compose down -v`.
- Les secrets de production ne doivent jamais être dans Git. Garder `.env` local.

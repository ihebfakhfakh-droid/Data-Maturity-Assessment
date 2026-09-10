# Data Maturity Assessment Platform

Évaluation de la maturité des données (NDI) — plateforme multi-modules avec Spring Boot, React, et services IA (Ollama).

---

## 🏗️ Architecture

| Module | Technologie | Port | Rôle |
|--------|------------|------|------|
| **Backend** | Java 21 / Spring Boot 4.0.5 | 9090 | API REST, auth JWT, gestion évaluations |
| **Frontend** | React 19 / Vite | 5173 | Interface web role-based |
| **AI Recommendation** | Python 3.12 / FastAPI | 8002 | Best Path + recommandations LLM (`qwen3.5:9b`) |
| **Evaluate Evidence** | Python 3.12 / FastAPI | 8003 | Acceptance Criteria NDI + PDF (`qwen2.5vl:7b`) |
| **PostgreSQL** | PostgreSQL 17 | 5432 | Base de données |
| **Ollama** | Ollama | 11434 | Runtime LLM partagé |

```
Browser → localhost:5173 (Nginx)
              │
              ├── /api → Backend :9090
              ├── /api/ai → AI Recommendation :8002
              └── /api/acceptance → Evaluate Evidence :8003
```

---

## 📋 Prérequis

### Outils requis (les deux méthodes)

- **Git**
- **Docker Desktop** (Méthode 1 uniquement)
- **Node.js 22+** (Méthode 2 — Frontend)
- **Maven 3.9+** (Méthode 2 — Backend)
- **Python 3.12+** (Méthode 2 — Services IA)
- **PostgreSQL 17** (Méthode 2 — Base de données)
- **Ollama** (Méthode 2 — Services IA)

### Ressources

- **16 Go RAM minimum** (32 Go recommandé)
- **25–40 Go disque** (modèles Ollama : `qwen3.5:9b` + `qwen2.5vl:7b`)
- **CPU uniquement** fonctionne (plus lent pour les appels LLM)

---

## 🚀 Méthode 1 — Avec Docker Compose (recommandée)

### Étape 1 — Cloner le dépôt

```powershell
git clone <url-du-depot>
cd pfeversion3
```
### Étape 2 -  Configurer le chemin d'accès Ollama
Dans le fichier docker/.env.example (vers la fin du fichier), modifiez la variable OLLAMA_DATA_PATH en renseignant le chemin adapté à votre machine.

Exemple sous Windows :
```powershell
OLLAMA_DATA_PATH=C:\Users\<VotreNomUtilisateur>\.ollama
```

### Étape 3 — Configurer l'environnement

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
| `FRONTEND_PORT` | `5173` | Conflit de port |

> ⚠️ **Ne jamais modifier** : `APP_DEMO_CLEANUP_ENABLED=false`, `APP_QUESTIONNAIRE_SEED_ENABLED=false` (conservation du dump validé).

### Étape 4 — Lancer
1) il faut ouvrir docker desktop 
2) buil images
```powershell
docker compose config
docker compose build --no-cache
```
3) lancer les images 
```powershell
docker compose up 
```


### Étape 5 — Vérifier

```powershell
docker compose ps
```

Services attendus : `pfe-postgres`, `pfe-ollama`, `pfe-ollama-init`, `pfe-ai-recommendation`, `pfe-evaluate-evidence`, `pfe-backend`, `pfe-frontend`.

**RQ : s'il existe un service manquant , lance à partir du docker desktop via le bouton start**

```powershell
# Health checks
curl http://localhost:9090/
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:5173/

# Vérifier les modèles Ollama
docker compose exec ollama ollama list
# Attendu : qwen3.5:9b, qwen2.5vl:7b
```

### Étape 6 — Première fois

- **Build des images** : plusieurs minutes
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
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:9090 |
| AI Recommendation | http://localhost:8002 |
| Evaluate Evidence | http://localhost:8003 |
| Ollama | http://localhost:11434 |

### Logs

```powershell
docker compose logs -f backend
docker compose logs -f ai-recommendation
docker compose logs -f evaluate-evidence
docker compose logs -f ollama
docker compose logs ollama-init
```

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
pfeversion2/
├── README.md                     ← Ce fichier
├── Docker/
│   ├── docker-compose.yml        ← Orchestration complète
│   ├── .env.example              ← Variables d'environnement
│   ├── .env                      ← À créer (copy de .env.example)
│   ├── nginx.conf                ← Reverse proxy Nginx
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── ai-recommendation.Dockerfile
│   ├── evaluate-evidence.Dockerfile
│   ├── start-docker.ps1
│   ├── stop-docker.ps1
│   ├── scripts/
│   │   └── ollama-init.sh        ← Script de pull des modèles
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
└── Docker/
    └── db/
        └── local-snapshot.sql    ← Dump validé (users, roles, projets, évaluations…)
```

---


## 🐛 Dépannage

| Symptôme | Solution |
|----------|----------|
| Port 5432 déjà utilisé | `POSTGRES_PORT=5433` dans `.env` |
| Port 11434 déjà utilisé | `OLLAMA_PORT=11435` dans `.env` |
| Port 5173 déjà utilisé | `FRONTEND_PORT=5174` dans `.env` |
| Erreurs API Frontend / CORS | Utiliser `http://localhost:5173` (Nginx `/api` proxy) |
| Modèle Ollama manquant | `docker compose logs ollama-init` puis `docker compose run --rm ollama-init` |
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

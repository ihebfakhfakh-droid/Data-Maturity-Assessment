# AI Recommendation Service

Microservice FastAPI de recommandations pour le framework de maturité des données **NDI**.

## Principe

- **Optimiseur déterministe** : calcule le Best Path (effort minimal) à partir du référentiel NDI, des scores client, des poids et des efforts de transition.
- **Enrichissement optionnel Ollama** : si `USE_OLLAMA=true`, le LLM enrichit les explications sans modifier le chemin sélectionné.
- **Rapport PDF** : endpoint dédié qui exécute le Best Path et retourne directement un fichier PDF.

## Installation

```bash
cd "C:\Users\Administrator\Desktop\data maturity pfe\ai-recommendation-service"
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Documentation interactive : http://localhost:8002/docs

## Endpoints principaux

| Méthode | Chemin | Description |
|---------|--------|-------------|
| `GET` | `/health` | Santé du service |
| `POST` | `/api/recommendations/best-path` | Calcul du Best Path (JSON) |
| `POST` | `/api/recommendations/generate-report` | Best Path + rapport PDF |

## Tests

```bash
pytest tests/ -v
```

## Exemple Best Path

```bash
curl -X POST "http://localhost:8002/api/recommendations/best-path" ^
  -H "Content-Type: application/json" ^
  -d "{\"targetScore\": 3.0, \"currentScores\": {\"DG.MQ.1\": 3, \"DG.MQ.2\": 2, \"DQ.MQ.1\": 2}}"
```

Les codes questions legacy du backend (`ndi_dg_01`, …) sont également acceptés et normalisés automatiquement.

## Exemple rapport PDF

```bash
curl -X POST "http://localhost:8002/api/recommendations/generate-report" ^
  -H "Content-Type: application/json" ^
  -o rapport.pdf ^
  -d "{\"targetScore\": 3.0, \"currentScores\": {\"DG.MQ.1\": 2, \"DG.MQ.2\": 2}, \"projectName\": \"Demo\", \"clientName\": \"Client Demo\", \"versionNumber\": 1}"
```

## Règles métier

- Score de domaine = **minimum** des scores des questions répondus du domaine.
- Score global = moyenne pondérée des scores de domaines actifs.
- Aucune recommandation hors de la base `app/data/ndi_framework.json`.
- Framework supporté : **NDI uniquement**.

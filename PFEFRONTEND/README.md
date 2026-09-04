# Data Maturity PFE

Application web de gestion des assessments de maturité data.  
Le projet contient un frontend **React/Vite** et un backend **Spring Boot**.

## Fonctionnalités principales

- Authentification des utilisateurs.
- Gestion des rôles : Admin, Manager, Consultant, Client.
- Gestion des clients, projets et frameworks.
- Questionnaire de maturité data.
- Sauvegarde en brouillon et soumission des assessments.
- Historique/versioning des assessments.
- Upload et consultation des preuves.
- Visualisation des scores et génération de rapports PDF.

## Structure du projet

```text
PFEFRONTEND/   Frontend React + Vite
PFEBACKEND/    Backend Spring Boot
```

## Prérequis

- Node.js + npm
- Java JDK 21
- PostgreSQL
- Maven Wrapper inclus dans le backend

## Configuration PostgreSQL

Configuration locale par défaut :

```properties
server.port=9090
spring.datasource.url=jdbc:postgresql://localhost:5432/pfe_backend_db
spring.datasource.username=pfe_user
spring.datasource.password=123456
```

Créer la base PostgreSQL :

```sql
CREATE USER pfe_user WITH PASSWORD '123456';
CREATE DATABASE pfe_backend_db OWNER pfe_user;
GRANT ALL PRIVILEGES ON DATABASE pfe_backend_db TO pfe_user;
```

## Installation

Depuis le dossier racine du projet :

### Frontend

```bash
cd PFEFRONTEND
npm install
```

### Backend

Sous Windows PowerShell :

```powershell
cd PFEBACKEND
.\mvnw.cmd clean install
```

Sous Linux/Mac :

```bash
cd PFEBACKEND
./mvnw clean install
```

## Lancement de l'application

### Démarrer le backend

Sous Windows PowerShell :

```powershell
cd PFEBACKEND
.\mvnw.cmd spring-boot:run
```

Sous Linux/Mac :

```bash
cd PFEBACKEND
./mvnw spring-boot:run
```

Le backend démarre sur :

```text
http://localhost:9090
```

### Démarrer le frontend

```bash
cd PFEFRONTEND
npm run dev
```

Le frontend démarre généralement sur :

```text
http://localhost:5173
```

## Build

### Frontend

```bash
cd PFEFRONTEND
npm run build
```

### Backend

Sous Windows PowerShell :

```powershell
cd PFEBACKEND
.\mvnw.cmd clean package
```

Sous Linux/Mac :

```bash
cd PFEBACKEND
./mvnw clean package
```

Exécuter le fichier JAR :

```bash
java -jar PFEBACKEND/target/PFEBACKEND-0.0.1-SNAPSHOT.jar
```

## Tests

### Frontend

```bash
cd PFEFRONTEND
npm run lint
npm run build
```

### Backend

Sous Windows PowerShell :

```powershell
cd PFEBACKEND
.\mvnw.cmd test
```

Sous Linux/Mac :

```bash
cd PFEBACKEND
./mvnw test
```

## Routes principales

Les routes backend utilisent le préfixe :

```text
/api
```

Exemples :

```text
/api/auth/...
/api/client/...
/api/admin/...
```

Les endpoints protégés nécessitent un token JWT :

```http
Authorization: Bearer <token>
```

## Problèmes fréquents

- Si le backend ne démarre pas : vérifier que le port `9090` est libre.
- Si PostgreSQL échoue : vérifier que la base `pfe_backend_db` existe.
- Si le frontend ne communique pas avec le backend : vérifier que le backend tourne sur `http://localhost:9090`.
- Si Maven échoue : vérifier que Java JDK 21 est installé.

# Data Maturity Platform

Application web permettant la gestion et le suivi des évaluations de maturité Data (Data Maturity Assessments).

Le projet contient :

- Frontend : React + Vite
- Backend : Spring Boot
- Base de données : PostgreSQL

---

# Technologies utilisées

## Frontend

- React : 19.2.5
- React Router DOM : 7.14.2
- Vite : 8.0.10
- Recharts : 3.8.1
- jsPDF : 4.2.1

## Backend

- Java JDK : 21
- Spring Boot : 4.0.5
- Maven : 3.9+
- Spring Security
- Spring Data JPA
- PostgreSQL

## Base de données

- PostgreSQL : 16+

---

# Prérequis à installer

Avant d’exécuter l’application, installer les éléments suivants :

### 1) Java JDK 21

Télécharger :

https://www.oracle.com/java/technologies/downloads/

Vérifier l’installation :

```bash
java -version
```

Résultat attendu :

```bash
java version "21"
```

---

### 2) Node.js

Télécharger :

https://nodejs.org/

Vérifier :

```bash
node -v
npm -v
```

---

### 3) PostgreSQL

Télécharger :

https://www.postgresql.org/download/

Pendant l’installation :

Créer :

Utilisateur :

```text
pfe_user
```

Mot de passe :

```text
123456
```

Créer ensuite une base nommée :

```text
pfe_backend_db
```

---

# Configuration base de données

Ouvrir :

```text
PFEBACKEND/src/main/resources/application.properties
```

Vérifier :

```properties
server.port=9090

spring.datasource.url=jdbc:postgresql://localhost:5432/pfe_backend_db
spring.datasource.username=pfe_user
spring.datasource.password=123456
```

---

# Installation du projet

Ouvrir deux terminaux.

## Installation Frontend

```bash
cd PFEFRONTEND
npm install
```

---

## Installation Backend

Windows :

```powershell
cd PFEBACKEND
.\mvnw.cmd clean install
```

Linux/Mac :

```bash
cd PFEBACKEND
./mvnw clean install
```

---

# Lancement de l'application

## Étape 1 : lancer Backend

Windows :

```powershell
cd PFEBACKEND
.\mvnw.cmd spring-boot:run
```

Linux/Mac :

```bash
./mvnw spring-boot:run
```

Backend lancé sur :

```text
http://localhost:9090
```

---

## Étape 2 : lancer Frontend

Dans un nouveau terminal :

```bash
cd PFEFRONTEND
npm run dev
```

Le frontend sera accessible sur :

```text
http://localhost:5173
```

---

# Comptes de test

Utiliser un compte déjà présent dans la base de données.

Exemple :

```text
Admin :
email: admin@test.com
password: Admin@12345
```

---


---

# Problèmes fréquents

### Port déjà utilisé

Modifier :

```text
PFEBACKEND/src/main/resources/application.properties
```

Changer :

```properties
server.port=9090
```

---

### Erreur connexion PostgreSQL

Vérifier :

- PostgreSQL démarré
- base créée
- utilisateur créé
- mot de passe correct

---

### Frontend ne charge pas

Réinstaller dépendances :

```bash
npm install
```

Puis :

```bash
npm run dev
```

---

# Architecture

```text
PFEFRONTEND
     ↓
API REST
     ↓
PFEBACKEND
     ↓
PostgreSQL
```

---

Application prête après démarrage simultané du Backend + Frontend.

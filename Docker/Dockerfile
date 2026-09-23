FROM node:22-alpine AS build-frontend

WORKDIR /app/frontend

COPY PFEFRONTEND/package.json PFEFRONTEND/package-lock.json ./
RUN npm ci

COPY PFEFRONTEND/ .

ENV VITE_API_URL=
ENV VITE_PROXY_TARGET=http://127.0.0.1:9090

RUN npm run build


FROM maven:3.9-eclipse-temurin-21-alpine AS build-backend

WORKDIR /app/backend

COPY PFEBACKEND/pom.xml ./
RUN mvn -B -q -DskipTests dependency:go-offline

COPY PFEBACKEND/src ./src

RUN mvn -B -q -DskipTests package


FROM python:3.12-slim AS build-python

WORKDIR /app/python

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY ai-recommendation-service/app/ /app/python/services/recommendation/app/
COPY ai-recommendation-service/prompts/ /app/python/services/recommendation/prompts/
COPY ai-recommendation-service/app/data/ndi_framework.json /app/python/services/recommendation/app/data/ndi_framework.json
COPY ["evaluate evidence/evaluate evidence/acceptance critiria/", "/app/python/services/evaluation/"]
RUN mkdir -p /app/python/services/evaluation && chmod -R a+rX /app/python


FROM eclipse-temurin:21-jre-alpine AS runtime-base

# 1. Installation de Nginx, Python, Pip, Supervisor et dépendances
COPY Docker/requirements.txt /tmp/requirements.txt

RUN apk add --no-cache \
    nginx \
    curl \
    bash \
    python3 \
    py3-pip \
    ttf-dejavu \
    fontconfig \
    zstd \
    && pip3 install --no-cache-dir --break-system-packages supervisor -r /tmp/requirements.txt \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && rm -rf /var/cache/apk/* /tmp/requirements.txt

WORKDIR /app

# 2. Création de l'utilisateur 'app' et attribution des droits sur TOUS les dossiers requis (Nginx, Supervisor, Logs, Tmp)
RUN addgroup -S app && adduser -S app -G app \
    && mkdir -p /app/data/evidence \
                /app/static \
                /app/services \
                /app/scripts \
                /var/log/supervisor \
                /var/lib/nginx/logs \
                /var/lib/nginx/tmp \
                /var/log/nginx \
                /run/nginx \
                /tmp \
    && chown -R app:app /app /var/log/supervisor /var/lib/nginx /var/log/nginx /run/nginx /tmp

COPY --from=build-frontend /app/frontend/dist /app/static
COPY --from=build-backend /app/backend/target /app/backend/target
RUN cp /app/backend/target/*.jar /app/backend/app.jar 2>/dev/null || true
COPY --from=build-python /app/python/services /app/services
COPY Docker/nginx.conf /etc/nginx/nginx.conf
COPY Docker/supervisord.conf /etc/supervisord.conf
COPY Docker/scripts/ollama-init.sh /app/scripts/ollama-init.sh
COPY Docker/scripts/start.sh /app/scripts/start.sh

# Switch to root to fix permissions and line endings
USER root
RUN apk add --no-cache dos2unix \
    && dos2unix /app/scripts/ollama-init.sh /app/scripts/start.sh \
    && chmod +x /app/scripts/ollama-init.sh /app/scripts/start.sh

USER app

EXPOSE 80 9090 8002 8003

# Use ENTRYPOINT instead of CMD to bypass the Java base image script
ENTRYPOINT ["/app/scripts/start.sh"]
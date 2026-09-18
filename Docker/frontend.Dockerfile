FROM node:22-alpine AS build

WORKDIR /app

COPY PFEFRONTEND/package.json PFEFRONTEND/package-lock.json ./
RUN npm ci

COPY PFEFRONTEND/ .

# Empty VITE_API_URL => browser calls relative /api/... (proxied by Nginx to backend).
ENV VITE_API_URL=

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY Docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

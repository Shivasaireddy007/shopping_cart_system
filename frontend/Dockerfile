# syntax=docker/dockerfile:1

FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Optional banner for the public demo; empty in normal builds.
ARG VITE_DEMO_NOTICE=""
ENV VITE_DEMO_NOTICE=$VITE_DEMO_NOTICE
RUN npm run build

# nginx serves the static build and proxies /api to the backend. The image fills
# ${API_UPSTREAM} into the template at startup (Compose: api:8000; Kubernetes: the API service).
FROM nginxinc/nginx-unprivileged:1.27-alpine
ENV API_UPSTREAM=http://api:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080

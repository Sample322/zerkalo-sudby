# Зеркало Судьбы frontend — two-stage: build the Vite SPA, serve the static bundle via nginx.
#
# VITE_API_BASE is a BUILD ARG: Vite inlines `import.meta.env.VITE_API_BASE` at build time
# (see src/lib/api.ts), so the backend origin must be known when the image is built —
# pass it on the timeweb App Platform build, e.g.:
#   --build-arg VITE_API_BASE=https://<backend-app>.timeweb.cloud
# Omitting it falls back to http://localhost:8000 (dev only — wrong for a deployed Mini App).

FROM node:22-alpine AS build
WORKDIR /app

# Install deps first for layer caching. Copy any lockfile if present (npm/pnpm/yarn);
# `npm install` resolves from package.json when no npm lockfile exists.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG VITE_API_BASE
ENV VITE_API_BASE=${VITE_API_BASE}
# `npm run build` = `tsc -b && vite build` → /app/dist
RUN npm run build

# --- serve ---
FROM nginx:alpine AS serve
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# timeweb reserves 80/443 (nginx listens 8080, see nginx.conf) and injects its own
# healthcheck — do NOT declare a Dockerfile HEALTHCHECK here, it fights the platform's.
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

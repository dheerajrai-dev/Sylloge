# Stage 1: Build React SPA
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install --prefer-offline --no-audit

COPY frontend/ ./
RUN npm run build

# Stage 2: Serve statically with Nginx in air-gapped container
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY infrastructure/nginx/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

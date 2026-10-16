# Build stage
FROM node:24-alpine AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ .
RUN npm run build

# Production stage — serve with nginx
FROM nginx:1.27-alpine

# Create nonroot user
RUN adduser -D -u 10001 appuser && \
    mkdir -p /usr/share/nginx/html && \
    chown -R appuser:appuser /usr/share/nginx/html

COPY --from=builder --chown=appuser:appuser /app/dist /usr/share/nginx/html

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

EXPOSE 80

# Run as nonroot
USER appuser

CMD ["nginx", "-g", "daemon off;"]
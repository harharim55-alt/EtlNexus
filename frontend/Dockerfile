# Development stage
FROM node:20-alpine AS dev
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
EXPOSE 5173

# Build stage
FROM dev AS build
ARG VITE_AIRFLOW_URL=http://localhost:8080
ENV VITE_AIRFLOW_URL=${VITE_AIRFLOW_URL}
RUN pnpm build

# Production stage — nginx-unprivileged: runs as non-root, listens on 8080, keeps its
# pid/temp under /tmp, logs to stdout/stderr, and its nginx.conf has no "user" directive.
# Built for OpenShift / arbitrary UID (no root, no privileged port, no root-owned writes).
FROM nginxinc/nginx-unprivileged:alpine AS production
# Root only to copy files + fix ownership, then drop back to the non-root user.
USER 0
COPY nginx-rate-limit.conf /etc/nginx/conf.d/00-rate-limit.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.sh
# Own the entrypoint-written dirs by the nginx user (101) AND group root (0), with group
# perms = owner — so the entrypoint can write config.js/default.conf BOTH locally (runs as
# UID 101) AND on OpenShift (runs as an arbitrary UID in group 0). Fixes the "can't create
# .../config.js" + "default.conf.tmp" errors (and the invalid-timeout emerg that follows).
RUN sed -i 's/\r$//' /docker-entrypoint.sh \
 && chmod +x /docker-entrypoint.sh \
 && chown -R 101:0 /etc/nginx/conf.d /usr/share/nginx/html \
 && chmod -R g=u /etc/nginx/conf.d /usr/share/nginx/html
USER 101
EXPOSE 8080
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

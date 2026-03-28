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

# Production stage
FROM nginx:alpine AS production
COPY nginx-rate-limit.conf /etc/nginx/conf.d/00-rate-limit.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

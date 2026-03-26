# Development stage
FROM node:20-alpine AS dev
RUN corepack enable && corepack prepare pnpm@latest --activate
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
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

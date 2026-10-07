# ---- Build stage: compile the static bundle ----
FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- Runtime stage: static files served by nginx as a non-root user ----
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

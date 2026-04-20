# ──────────────────────────────────────────────────────────────────────────────
# Stage 0 – Dev (Vite HMR dev server, source mounted via docker-compose volume)
# ──────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS dev

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

EXPOSE 5173

CMD ["npm", "run", "dev"]

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 – Build
# ──────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first (cached layer)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 – Serve
# ──────────────────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets into the path that matches vite base: '/FinInsightAI/'
COPY --from=builder /app/dist /usr/share/nginx/html/FinInsightAI

# Nginx config: serve the SPA under /FinInsightAI with proper fallback routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

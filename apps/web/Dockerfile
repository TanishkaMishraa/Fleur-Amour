# AuraFit — Next.js Frontend Dockerfile
# Multi-stage: deps → builder → production runner (Next.js standalone mode)

# ── Stage 1: Install dependencies ──────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# ── Stage 2: Build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time env vars (non-secret: public URLs, app metadata)
ARG NEXT_PUBLIC_API_URL=https://api.aurafit.ai/api/v1
ARG NEXT_PUBLIC_REC_API_URL=https://rec.aurafit.ai/api/v1
ARG NEXT_PUBLIC_VTRYON_API_URL=https://vtryon.aurafit.ai/api/v1
ARG NEXT_PUBLIC_APP_NAME=AuraFit
ARG NEXT_PUBLIC_APP_VERSION=1.0.0

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ENV NODE_OPTIONS=--dns-result-order=ipv4first

RUN npm run build

# ── Stage 3: Production runner ──────────────────────────────────────────────
FROM node:20-alpine AS production

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# Copy standalone build (Next.js output: standalone)
COPY --from=builder /app/public                  ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static    ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]

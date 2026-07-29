# Frontend image: static Vite/React build served by nginx, which also
# reverse-proxies API calls to the backend container. Build context is
# ./frontend.

FROM node:20-alpine AS builder
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

# Install dependencies first so this layer is cached independently of
# application code changes.
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=cdss-pnpm-store,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store \
    && pnpm install --frozen-lockfile

COPY . .

# Vite inlines import.meta.env.VITE_* at build time, so the tldraw license
# key has to be present here, not just as a runtime container env var -
# without it, tldraw silently hides the whole canvas 5s after mount in any
# build served over https from a non-localhost domain.
ARG VITE_TLDRAW_LICENSE_KEY
ENV VITE_TLDRAW_LICENSE_KEY=$VITE_TLDRAW_LICENSE_KEY
ARG VITE_PRODUCTION=0
ENV VITE_PRODUCTION=$VITE_PRODUCTION
RUN pnpm build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
    CMD wget -qO- http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

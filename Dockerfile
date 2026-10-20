# Single-container image for Hugging Face Spaces (Docker SDK).
# Next.js serves the app on $PORT (7860) and proxies /api/* to FastAPI on 127.0.0.1:8000 inside the container.
# For a multi-service deployment (Postgres, Redis, Celery) use docker-compose.yml instead.

# ---- 1. Build the Next.js standalone server ----
FROM node:26-bookworm-slim AS web-build
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
ENV NEXT_TELEMETRY_DISABLED=1 \
    API_URL=http://127.0.0.1:8000 \
    FRAME_ANCESTORS="'self' https://huggingface.co https://*.hf.space"
RUN npm run build

# ---- 2. Runtime: Python API + Node runtime ----
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 NEXT_TELEMETRY_DISABLED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils curl \
 && rm -rf /var/lib/apt/lists/*
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node

# Hugging Face runs Spaces as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

COPY apps/api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt

COPY --chown=user apps/api/app api/app
COPY --chown=user --from=web-build /web/.next/standalone web/
COPY --chown=user --from=web-build /web/.next/static web/.next/static
COPY --chown=user --from=web-build /web/public web/public
COPY --chown=user deploy/huggingface/start.sh start.sh
RUN chmod +x start.sh && mkdir -p api/data/uploads && chown -R user /app

USER user
ENV HOME=/home/user \
    PORT=7860 \
    ENVIRONMENT=production \
    COOKIE_SAMESITE=none \
    LLM_PROVIDER=mock \
    EMBEDDING_PROVIDER=local \
    SEED_DEMO=true

EXPOSE 7860
CMD ["./start.sh"]

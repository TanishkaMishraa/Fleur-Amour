# AuraFit — Recommendation Service Dockerfile
# Multi-stage: builder installs deps into venv; production image is minimal.
# GPU support: override base image to pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --timeout 120 --retries 15 \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# Pre-download SBERT model (baked into image for fast startup)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

RUN groupadd --gid 1001 aurafit && \
    useradd --uid 1001 --gid aurafit --no-create-home --shell /bin/false aurafit

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
# Copy pre-downloaded model from builder
COPY --from=builder /root/.cache /root/.cache

ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=aurafit:aurafit . .

# Model cache directory for ALS
RUN mkdir -p /tmp && chown aurafit:aurafit /tmp

USER aurafit

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8003/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8003", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--proxy-headers"]

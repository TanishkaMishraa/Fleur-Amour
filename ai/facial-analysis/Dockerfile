# AuraFit AI Facial Analysis Service
# Multi-stage build. Two final targets:
#   - cpu:  default, runs on general node pool
#   - gpu:  CUDA-enabled, runs on GPU node pool (g4dn.xlarge)
# Select target at build time: docker build --target gpu -t aurafit-ai-facial:gpu .

# ── Stage 1: Builder (CPU) ─────────────────────────────────────────────────────
FROM python:3.11-slim AS builder-cpu

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 libglib2.0-0 \
    libsm6 libxext6 libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: CPU production image ───────────────────────────────────────────────
FROM python:3.11-slim AS cpu

WORKDIR /app

RUN groupadd --gid 1001 aurafit && \
    useradd --uid 1001 --gid aurafit --no-create-home --shell /bin/false aurafit

# Runtime libs required by OpenCV / MediaPipe (headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder-cpu /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV USE_GPU=false

COPY --chown=aurafit:aurafit . .

# Pre-download MediaPipe + DeepFace model weights into the image so
# pods don't hit the network on cold start (faster autoscaling).
RUN python -c "import mediapipe as mp; mp.solutions.face_mesh.FaceMesh(static_image_mode=True)" || true

USER aurafit
EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8010", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "httptools"]


# ── Stage 3: GPU production image ───────────────────────────────────────────────
# CUDA 12.x base with cuDNN — required for TensorFlow GPU (DeepFace age model)
FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04 AS gpu

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

RUN groupadd --gid 1001 aurafit && \
    useradd --uid 1001 --gid aurafit --no-create-home --shell /bin/false aurafit

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir tensorflow[and-cuda]==2.16.1

ENV USE_GPU=true
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

COPY --chown=aurafit:aurafit . .

USER aurafit
EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8010", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "httptools"]

# ── Production alias (used by docker-compose target: production) ─────────────
FROM cpu AS production

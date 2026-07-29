# ==============================================================================
# Production-Grade Dockerfile for TalentAI
# Employs multi-stage builds, model caching, and resource optimizations.
# ==============================================================================

# Stage 1: Build dependencies in a secure isolated image
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Clean, small, secure runner image
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy packages installed in builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Pre-download Sentence-Transformers model files (speeds up cold starts)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source directories
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY storage/ ./storage/

WORKDIR /app/backend

# Prevent container CPU thrashing inside K8s/Docker environments
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2
ENV TOKENIZERS_PARALLELISM=false

EXPOSE 8000

# Run multi-worker production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ==============================================================================
# Highly Resilient Dockerfile for TalentAI
# Avoids apt-get dependency downloads to eliminate transient network errors.
# ==============================================================================

FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install via pip (psycopg2-binary includes its own libpq)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Sentence-Transformers model files (speeds up container cold starts)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source directories
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY storage/ ./storage/

WORKDIR /app/backend

# Prevent container CPU thrashing inside containerized environments
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2
ENV TOKENIZERS_PARALLELISM=false

EXPOSE 8000

# Run multi-worker production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

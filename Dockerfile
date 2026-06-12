FROM python:3.11-slim

WORKDIR /app

# libgomp is required by LightGBM; libpq-dev for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories that may not exist in the repo
RUN mkdir -p models data

# Train ML models at build time so no external upload is needed.
# Uses 2000 records to keep build fast (~60 s); override with --build-arg N=8000
ARG N=2000
RUN python scripts/generate_data.py --n ${N} --out data/synthetic_clinic_data.csv && \
    python scripts/train_models.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

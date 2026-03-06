# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package and its dependencies
RUN pip install --no-cache-dir --prefix=/install .

# Download spaCy language model
RUN pip install --no-cache-dir --prefix=/install spacy && \
    PYTHONPATH=/install/lib/python3.11/site-packages \
    python -m spacy download en_core_web_sm --pip-args="--prefix=/install"

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source (needed for celery task discovery)
COPY src/ src/

EXPOSE 8000

CMD ["uvicorn", "aiseo.main:app", "--host", "0.0.0.0", "--port", "8000"]

# OmniBrain backend — FastAPI + ChromaDB + sentence-transformers
FROM python:3.11-slim

# System deps: poppler for pdf2image, tesseract for OCR fallback, build tools
# for anything sentence-transformers/chromadb needs to compile.
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Directories the app writes to at runtime — mounted as volumes in
# docker-compose so data survives container restarts/rebuilds.
RUN mkdir -p /app/uploads /app/reports /app/vector_store

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

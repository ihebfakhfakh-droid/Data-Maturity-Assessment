FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ACCEPTANCE_CRITERIA_PORT=8003

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir \
    fastapi>=0.110.0 \
    "uvicorn[standard]>=0.27.0" \
    python-multipart>=0.0.9 \
    httpx>=0.27.0 \
    openai>=1.40.0 \
    pandas>=2.0.0 \
    openpyxl>=3.1.0 \
    tabulate>=0.9.0 \
    python-docx>=1.1.0 \
    pymupdf>=1.24.0 \
    fpdf2>=2.7.0

# API runtime only (no Streamlit app launch).
COPY api_server.py evaluation_service.py pdf_report.py ./
COPY *.json ./

EXPOSE 8003

CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port ${ACCEPTANCE_CRITERIA_PORT:-8003}"]
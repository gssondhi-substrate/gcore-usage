FROM python:3.11-slim

WORKDIR /app

# Copy the application
COPY main.py /app/main.py

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic

# Environment variables for Gcore API endpoints (override at runtime if needed)
ENV GCORE_API_BASE=https://api.gcore.com \
    GCORE_FEATURES_PATH=/billing/v3/report_features \
    GCORE_GENERATE_PATH=/billing/v1/org/files/report \
    GCORE_STATUS_PATH=/billing/v1/org/files/{uuid} \
    GCORE_DOWNLOAD_PATH=/billing/v1/org/files/{uuid}/download

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

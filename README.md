## Gcore Statistics Report API

FastAPI service that generates and fetches cleaned statistics reports from Gcore for specific users/clients.

## Features

- **Product coverage**: CDN, WAAP, CLOUD
- **Token**: Provide Gcore API token in the request body
- **Report generation**: Creates ResellerStatistics for a date range
- **Status polling**: Waits until report is ready, then downloads
- **Filtering**: Keeps rows for the requested client/user ID only
- **Cleaning**: Removes zero-only numeric fields and null/empty values

## Quick Start

### Local Development

```bash
# Install dependencies
pip install fastapi uvicorn httpx pydantic

# Run the server
uvicorn main:app --reload --port 8080
```

### Docker

```bash
# Build the image
docker build -t gcore-usage:latest .

# Run the container (default ports)
docker run --name gcore-usage -p 8080:8080 gcore-usage:latest

# Optionally override Gcore API endpoints
docker run --name gcore-usage -p 8080:8080 \
  -e GCORE_API_BASE=https://api.gcore.com \
  -e GCORE_FEATURES_PATH=/billing/v3/report_features \
  -e GCORE_GENERATE_PATH=/billing/v1/org/files/report \
  -e GCORE_STATUS_PATH=/billing/v1/org/files/{uuid} \
  -e GCORE_DOWNLOAD_PATH=/billing/v1/org/files/{uuid}/download \
  gcore-usage:latest
```

## API Endpoints

### Generate CDN report

POST `/reports/cdn`

Request body:
```json
{
  "gcore_token": "<GCORE_TOKEN>",
  "gcore_user_id": "123456",
  "start_date": "2025-01-01",
  "end_date": "2025-01-15"
}
```

Response body (example):
```json
{
  "uuid": "a2b3c4d5-...",
  "status": "ready",
  "count": 42,
  "data": [ { "Client ID": "123456", "Metric value": 12.34 } ]
}
```

### Generate WAAP report

POST `/reports/waap`

Body is the same as for CDN.

### Generate CLOUD report

POST `/reports/cloud`

Body is the same as for CDN.

### Generate all reports (aggregate)

POST `/reports/all`

Body is the same as for CDN. Returns an object with keys `cdn`, `waap`, and `cloud` containing per-product results when available.

### Check report status / Download raw JSON

POST `/reports/gcore/{uuid}?mode=status|download`

Request body:
```json
{ "gcore_token": "<GCORE_TOKEN>" }
```

- **mode=status**: returns raw status from Gcore
- **mode=download**: returns `{ uuid, data }` with raw report payload

### Health

- GET `/` — simple health check
- GET `/health` — detailed health

## Example Usage

```bash
# Generate a CDN report
curl -sS -X POST http://localhost:8080/reports/cdn \
  -H "Content-Type: application/json" \
  -d '{
    "gcore_token": "<GCORE_TOKEN>",
    "gcore_user_id": "123456",
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'

# Generate all reports
curl -sS -X POST http://localhost:8080/reports/all \
  -H "Content-Type: application/json" \
  -d '{
    "gcore_token": "<GCORE_TOKEN>",
    "gcore_user_id": "123456",
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'

# Check report status (replace <UUID>)
curl -sS -X POST "http://localhost:8080/reports/gcore/<UUID>?mode=status" \
  -H "Content-Type: application/json" \
  -d '{ "gcore_token": "<GCORE_TOKEN>" }'

# Download raw report (replace <UUID>)
curl -sS -X POST "http://localhost:8080/reports/gcore/<UUID>?mode=download" \
  -H "Content-Type: application/json" \
  -d '{ "gcore_token": "<GCORE_TOKEN>" }'
```

## Configuration

- **Environment variables** (defaults shown; can be overridden at runtime):
  - `GCORE_API_BASE=https://api.gcore.com`
  - `GCORE_FEATURES_PATH=/billing/v3/report_features`
  - `GCORE_GENERATE_PATH=/billing/v1/org/files/report`
  - `GCORE_STATUS_PATH=/billing/v1/org/files/{uuid}`
  - `GCORE_DOWNLOAD_PATH=/billing/v1/org/files/{uuid}/download`

## Notes

- Product names are handled as required by Gcore (e.g., `Cloud` for CLOUD)
- Client filtering tries multiple common field names and nested shapes
- Zero-only numeric fields are pruned; null/empty structures are removed
- CSV payloads are supported in addition to JSON

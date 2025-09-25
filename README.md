## Gcore Statistics Report API

FastAPI service that generates and fetches cleaned statistics reports from Gcore for specific users/clients.

## Features

- **Product coverage**: CDN, WAAP, CLOUD
- **Internal authentication**: Automatically generates and caches Gcore access tokens
- **Report generation**: Creates ResellerStatistics for a date range
- **Status polling**: Waits until report is ready, then downloads
- **Filtering**: Keeps rows for the requested client/user ID only
- **Cleaning**: Removes zero-only numeric fields and null/empty values

## Quick Start

### Local Development

```bash
# Install dependencies
pip install fastapi uvicorn httpx pydantic

# Set environment variables (required)
export GCORE_USERNAME="your-username@example.com"
export GCORE_PASSWORD="your-password"

# Run the server
uvicorn main:app --reload --port 8080
```

### Docker

```bash
# Build the image
docker build -t gcore-usage:latest .

# Run the container with required credentials
docker run --name gcore-usage -p 8080:8080 \
  -e GCORE_USERNAME="your-username@example.com" \
  -e GCORE_PASSWORD="your-password" \
  gcore-usage:latest

# Optionally override Gcore API endpoints
docker run --name gcore-usage -p 8080:8080 \
  -e GCORE_USERNAME="your-username@example.com" \
  -e GCORE_PASSWORD="your-password" \
  -e GCORE_API_BASE=https://api.gcore.com \
  -e GCORE_FEATURES_PATH=/billing/v3/report_features \
  -e GCORE_GENERATE_PATH=/billing/v1/org/files/report \
  -e GCORE_STATUS_PATH=/billing/v1/org/files/{uuid} \
  -e GCORE_DOWNLOAD_PATH=/billing/v1/org/files/{uuid}/download \
  -e GCORE_AUTH_PATH=/iam/auth/jwt/login \
  gcore-usage:latest
```

## API Endpoints

### Generate CDN report

POST `/reports/cdn`

Request body:
```json
{
  "gcore_user_id": "123456",
  "start_date": "2025-01-01",
  "end_date": "2025-01-15"
}
```

**Format specification:**
- Use `Accept` header to specify format (recommended)
- Or use `format` field in request body (optional)
- **Accept header options:**
  - `Accept: application/json` - Returns filtered and cleaned JSON data (only non-zero metrics for specified user)
  - `Accept: text/csv` - Returns filtered CSV data as text (preserves original Gcore column structure, filters by client ID and non-zero metrics)
  - `Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - Returns raw Excel file as binary data (preserves original Gcore column structure)

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
{
  "format": "json"
}
```

- **mode=status**: returns raw status from Gcore
- **mode=download**: returns `{ uuid, data }` with raw report payload

### Health

- GET `/` — simple health check
- GET `/health` — detailed health

## Example Usage

```bash
# Generate a CDN report (JSON format) - using Accept header
curl -sS -X POST http://localhost:8080/reports/cdn \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "gcore_user_id": "123456",
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'

# Generate a CDN report (CSV format) - using Accept header
curl -sS -X POST http://localhost:8080/reports/cdn \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{
    "gcore_user_id": "123456",
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'

# Generate a CDN report (Excel format) - using Accept header
curl -sS -X POST http://localhost:8080/reports/cdn \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  -d '{
    "gcore_user_id": "123456",
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'

# Generate all reports (CSV format)
curl -sS -X POST http://localhost:8080/reports/all \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{
    "gcore_user_id": "123456",
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'

# Check report status (replace <UUID>)
curl -sS -X POST "http://localhost:8080/reports/gcore/<UUID>?mode=status" \
  -H "Content-Type: application/json" \
  -d '{}'

# Download raw report (replace <UUID>) - CSV format
curl -sS -X POST "http://localhost:8080/reports/gcore/<UUID>?mode=download" \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{}'

# Example: Save Excel file from response
# The Excel data is returned as base64-encoded string in the response
# To save it as a file:
# echo 'base64_data_from_response' | base64 -d > report.xlsx

# Example: Save CSV file from response
# The CSV data is returned as text in the response
# To save it as a file:
# curl -sS -X POST http://localhost:8080/reports/cloud \
#   -H "Content-Type: application/json" \
#   -H "Accept: text/csv" \
#   -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}' \
#   | jq -r '.data' > report.csv
```

## Configuration

- **Required environment variables**:
  - `GCORE_USERNAME` - Your Gcore account username/email
  - `GCORE_PASSWORD` - Your Gcore account password

- **Optional environment variables** (defaults shown; can be overridden at runtime):
  - `GCORE_API_BASE=https://api.gcore.com`
  - `GCORE_FEATURES_PATH=/billing/v3/report_features`
  - `GCORE_GENERATE_PATH=/billing/v1/org/files/report`
  - `GCORE_STATUS_PATH=/billing/v1/org/files/{uuid}`
  - `GCORE_DOWNLOAD_PATH=/billing/v1/org/files/{uuid}/download`
  - `GCORE_AUTH_PATH=/iam/auth/jwt/login`

- **Sample environment file**: Copy `env.sample` to `.env` and fill in your credentials

## Notes

- **Authentication**: The API automatically generates and caches Gcore access tokens using your credentials
- **Token caching**: Tokens are cached and automatically refreshed when expired
- **Product names**: Handled as required by Gcore (e.g., `Cloud` for CLOUD)
- **Client filtering**: Tries multiple common field names and nested shapes
- **Data cleaning**: Zero-only numeric fields are pruned; null/empty structures are removed
- **Format support**: JSON (default), CSV, and Excel formats supported via Gcore API
- **JSON format**: Filtered and cleaned data (only non-zero metrics for specified user)
- **CSV format**: Filtered CSV text preserving original Gcore column structure (Client ID, Company name, Feature ID, etc.) - filters by client ID and non-zero metrics
- **Excel format**: Raw Excel file preserving original Gcore column structure
- **Excel usage**: To save Excel file, decode the base64 data from the response

# Gcore Usage API - Production Ready

A production-ready FastAPI application for generating and downloading Gcore usage reports in multiple formats (JSON, CSV, Excel) with advanced data aggregation capabilities.

## ✨ Key Features

- **🔄 Data Aggregation**: `/reports/all` endpoint combines data from all Gcore products (CDN, WAAP, Cloud)
- **🎯 Consistent Filtering**: All formats apply the same filtering logic (client ID + non-zero metrics)
- **📊 Multiple Formats**: JSON, CSV, and Excel with proper filtering and data structure preservation
- **🔐 Internal Authentication**: Automatic token generation and caching (30-minute duration)
- **🏗️ Production Ready**: Modular architecture, health checks, comprehensive logging
- **⚡ Error Resilient**: Aggregation continues even if individual products fail

## 🏗️ Architecture

```
gcore-usage/
├── apps/                    # Application modules
│   ├── api/                # API layer
│   │   ├── models.py       # Pydantic models
│   │   └── routes.py       # API routes
│   ├── core/               # Core business logic
│   │   ├── auth.py         # Token management
│   │   ├── gcore_client.py # Gcore API client
│   │   └── data_processor.py # Data processing
│   └── utils/              # Utility functions
├── config/                 # Configuration
│   └── settings.py         # Settings management
├── tests/                  # Test suites
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── logs/                  # Application logs
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Docker Compose setup
└── env.production      # Production environment template
```

## Features

- **Multiple report types**: CDN, WAAP, Cloud, and All products (aggregated)
- **Multiple formats**: JSON, CSV, and Excel (all with consistent filtering)
- **Internal authentication**: Automatically generates and caches Gcore access tokens (30 min cache)
- **Product coverage**: Supports all Gcore products (CDN, WAAP, Cloud)
- **Data aggregation**: `/reports/all` endpoint aggregates filtered data from all products
- **Consistent filtering**: All formats filter by client ID and non-zero metric values
- **Format specification**: Use `Accept` header or `format` parameter
- **Production ready**: Modular architecture, proper logging, health checks

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp env.production .env

# Edit with your credentials
nano .env
```

Required environment variables:
```bash
GCORE_USERNAME=your-username@example.com
GCORE_PASSWORD=your-password
TOKEN_CACHE_DURATION=1800  # 30 minutes
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Application

```bash
# Development (with auto-reload)
uvicorn apps.main:app --reload --host 0.0.0.0 --port 8080

# Production
uvicorn apps.main:app --host 0.0.0.0 --port 8080

# Using Python entry point
python run.py

# Docker
docker-compose up -d
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCORE_USERNAME` | - | Gcore API username (required) |
| `GCORE_PASSWORD` | - | Gcore API password (required) |
| `GCORE_API_BASE` | `https://api.gcore.com` | Gcore API base URL |
| `TOKEN_CACHE_DURATION` | `1800` | Token cache duration in seconds (30 min) |
| `APP_HOST` | `0.0.0.0` | Application host |
| `APP_PORT` | `8080` | Application port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout |
| `REPORT_POLL_TIMEOUT` | `600` | Report generation timeout |
| `REPORT_POLL_INTERVAL` | `10` | Status check interval |

### Token Caching

- **Duration**: 30 minutes (configurable via `TOKEN_CACHE_DURATION`)
- **Auto-refresh**: Tokens are automatically refreshed before expiration
- **Memory-based**: Tokens are cached in memory (not persistent across restarts)

## API Endpoints

### Data Aggregation

The `/reports/all` endpoint provides powerful data aggregation capabilities:

- **Multi-product aggregation**: Combines data from CDN, WAAP, and Cloud products
- **Consistent filtering**: Applies the same client ID and metric filtering across all products
- **Product identification**: Adds a "Product" column to identify data source
- **Error resilience**: Continues processing even if individual products fail
- **Format support**: Works with JSON, CSV, and Excel formats

**Use cases:**
- Get a unified view of all product usage
- Compare usage across different products
- Generate comprehensive reports for billing or analysis
- Export aggregated data for external systems

### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "gcore-usage-api",
  "version": "1.0.0",
  "timestamp": 1706123456.789
}
```

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
- **All formats apply consistent filtering** (client ID + non-zero metrics)
- **Accept header options:**
  - `Accept: application/json` - Returns filtered and cleaned JSON data (only non-zero metrics for specified user)
  - `Accept: text/csv` - Returns filtered CSV data as text (preserves original Gcore column structure, filters by client ID and non-zero metrics)
  - `Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - Returns filtered Excel data as base64-encoded CSV (preserves original Gcore column structure, filters by client ID and non-zero metrics)

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

### Generate all reports (aggregated)

POST `/reports/all`

**Aggregates data from all products (CDN, WAAP, Cloud) into a single response.**

Body is the same as for individual product reports.

**Key features:**
- **Aggregates filtered data** from all products (CDN, WAAP, Cloud)
- **Adds "Product" column** to identify data source
- **Applies consistent filtering** across all products (client ID + non-zero metrics)
- **Supports all formats** (JSON, CSV, Excel) with proper filtering
- **Error resilient** - continues processing even if one product fails

**Response includes:**
- All filtered rows from all products
- Additional "Product" column showing data source (CDN/WAAP/Cloud)
- Consistent filtering applied across all products
- Total count of aggregated rows

**Example aggregated data:**
```csv
Client ID,Company name,Feature ID,Feature name,Metric value,Product,Region ID,Region name,Resource ID,Resource name,Unit name
829449,SDG Test 2,2362,Block Storage (Standard) - Gb,0.4965,Cloud,,,,,GBM
829449,SDG Test 2,2363,Block Storage (High-IOPS SSD) - Gb,0.9938,Cloud,,,,,GBM
829449,SDG Test 2,2372,Public IP address,199.9000,Cloud,,,,,H
829449,SDG Test 2,13107,Instance Type: g2-standard-1-2 (1vCPU/2GB RAM),199.8167,Cloud,,,,,H
```

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

## 📋 Usage Examples

### Individual Product Reports

```bash
# CDN report (JSON format)
curl -X POST http://localhost:8080/reports/cdn \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}'

# WAAP report (CSV format)
curl -X POST http://localhost:8080/reports/waap \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}'

# Cloud report (Excel format)
curl -X POST http://localhost:8080/reports/cloud \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}'
```

### Aggregated Reports (All Products)

```bash
# Get aggregated data from all products (JSON)
curl -X POST http://localhost:8080/reports/all \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}'

# Get aggregated data as CSV
curl -X POST http://localhost:8080/reports/all \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}'

# Get aggregated data as Excel and save to file
curl -X POST http://localhost:8080/reports/all \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  -d '{"gcore_user_id": "829449", "start_date": "2025-09-01", "end_date": "2025-09-24"}' \
  | jq -r '.data.data' | base64 -d > aggregated_report.xlsx
```

### Health Check

```bash
# Check API health
curl http://localhost:8080/health
```

### Expected Response Formats

**JSON Response:**
```json
{
  "uuid": "a2b3c4d5-e6f7-8901-2345-6789abcdef01",
  "status": "completed",
  "count": 4,
  "data": [
    {
      "Client ID": "829449",
      "Company name": "SDG Test 2",
      "Feature ID": 2362,
      "Feature name": "Block Storage (Standard) - Gb",
      "Metric value": "0.4965",
      "Unit name": "GBM",
      "Product": "Cloud"
    }
  ]
}
```

**CSV Response:**
```csv
Client ID,Company name,Feature ID,Feature name,Metric value,Product,Region ID,Region name,Resource ID,Resource name,Unit name
829449,SDG Test 2,2362,Block Storage (Standard) - Gb,0.4965,Cloud,,,,,GBM
829449,SDG Test 2,2363,Block Storage (High-IOPS SSD) - Gb,0.9938,Cloud,,,,,GBM
```

**Excel Response:**
- Base64-encoded CSV data in the `data.data` field
- Decode with: `echo "base64_string" | base64 -d > report.xlsx`

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
- **Token caching**: Tokens are cached for 30 minutes and automatically refreshed when expired
- **Product names**: Handled as required by Gcore (e.g., `Cloud` for CLOUD)
- **Consistent filtering**: All formats (JSON, CSV, Excel) apply the same filtering logic
- **Client filtering**: Filters by specified client ID and non-zero metric values
- **Data cleaning**: Zero-only numeric fields are pruned; null/empty structures are removed
- **Format support**: JSON (default), CSV, and Excel formats with consistent filtering
- **JSON format**: Filtered and cleaned data (only non-zero metrics for specified user)
- **CSV format**: Filtered CSV text preserving original Gcore column structure
- **Excel format**: Filtered data as base64-encoded CSV (preserves original Gcore column structure)
- **Aggregation**: `/reports/all` combines data from all products with "Product" column identification
- **Error handling**: Aggregation continues even if individual products fail
- **Excel usage**: To save Excel file, decode the base64 data from the response

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test type
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest tests/ --cov=apps --cov-report=html
```

## 🐳 Docker Deployment

### Build and Run
```bash
# Build image
docker build -t gcore-usage-api .

# Run container
docker run -d \
  --name gcore-api \
  -p 8080:8080 \
  --env-file .env \
  gcore-usage-api
```

### Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📝 Logging

Logs are written to stdout with structured format:
```
2025-01-25 10:30:45,123 - main - INFO - Starting Gcore Usage API...
2025-01-25 10:30:45,124 - apps.core.auth - INFO - Using cached Gcore token
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 🔒 Security

- **Non-root user**: Docker container runs as non-root user
- **Environment variables**: Sensitive data stored in environment variables
- **Token caching**: Tokens cached in memory only
- **CORS**: Configurable CORS origins
- **Health checks**: Built-in health check endpoint

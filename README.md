# Gcore Statistics Report API

A FastAPI service that generates and fetches cleaned statistics reports from Gcore for specific users/clients.

## Features

- Accepts Gcore access tokens via body, Authorization header, or X-Gcore-Token header
- Pulls feature IDs for selected product types (CDN/CLOUD/WAAP)
- Generates ResellerStatistics reports for date ranges
- Polls report status until ready
- Downloads JSON payload and filters to requested Gcore user/client ID
- Removes all null/empty fields before returning results

## Quick Start

### Local Development

```bash
# Install dependencies (if not already installed)
pip install fastapi uvicorn httpx pydantic

# Run the server
uvicorn main:app --reload --port 8080
```

### Docker

```bash
# Build the image
docker build -t gcore-report-api .

# Run the container
docker run -p 8080:8080 gcore-report-api
```

## API Endpoints

### Generate & Fetch Report

**POST** `/reports/gcore`

Generate a cleaned statistics report for a specific Gcore user.

**Request Body:**
```json
{
  "gcore_user_id": "123456",
  "date_from": "2025-01-01",
  "date_to": "2025-01-15",
  "products": ["CDN", "CLOUD", "WAAP"],
  "timeout_seconds": 300,
  "poll_interval_seconds": 5
}
```

**Headers:**
- `Authorization: Bearer <GCORE_TOKEN>` (optional if token provided in body)
- `X-Gcore-Token: <GCORE_TOKEN>` (alternative header)
- `Content-Type: application/json`

**Response:**
```json
{
  "uuid": "a2b3c4d5-...",
  "status": "ready",
  "count": 42,
  "data": [/* filtered and cleaned data for the user */]
}
```

### Check Report Status

**GET** `/reports/gcore/{uuid}?mode=status`

Check the status of a report generation.

### Download Raw Report

**GET** `/reports/gcore/{uuid}?mode=download`

Download the raw JSON report without cleaning.

### Health Check

**GET** `/`

Simple health check endpoint.

## Example Usage

```bash
# Generate a report
curl -X POST http://localhost:8080/reports/gcore \
  -H "Authorization: Bearer <GCORE_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "gcore_user_id": "123456",
    "date_from": "2025-01-01",
    "date_to": "2025-01-15",
    "products": ["CDN", "CLOUD", "WAAP"]
  }'

# Check report status
curl -H "Authorization: Bearer <GCORE_TOKEN>" \
  "http://localhost:8080/reports/gcore/a2b3c4d5-...?mode=status"

# Download raw report
curl -H "Authorization: Bearer <GCORE_TOKEN>" \
  "http://localhost:8080/reports/gcore/a2b3c4d5-...?mode=download"
```

## Configuration

- **Products**: Supports CDN, CLOUD, and WAAP (case-insensitive)
- **Timeout**: Default 300 seconds, configurable 30-1200 seconds
- **Poll Interval**: Default 5 seconds, configurable 2-30 seconds
- **Format**: Currently only supports JSON (for data cleaning)

## Notes

- The service automatically maps product names to Gcore's expected format
- Client filtering tries multiple common field names (client_id, client, etc.)
- All null/empty fields are recursively removed from the response
- The service handles various Gcore API response formats defensively

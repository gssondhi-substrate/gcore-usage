# Gcore Usage API - Production Ready

A production-ready FastAPI application for generating and downloading Gcore usage reports in multiple formats (JSON, CSV, Excel).

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
├── main_new.py           # Production entry point
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Docker Compose setup
├── deploy.sh           # Production deployment script
└── env.production      # Production environment template
```

## 🚀 Quick Start

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
# Development
python main_new.py

# Production
./deploy.sh

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

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

### Report Generation
```bash
# CDN Report
POST /reports/cdn
Content-Type: application/json
Accept: text/csv  # or application/json or application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

{
  "gcore_user_id": "829449",
  "start_date": "2025-09-01",
  "end_date": "2025-09-24"
}

# Cloud Report
POST /reports/cloud

# WAAP Report
POST /reports/waap

# All Products
POST /reports/all
```

### Report Status & Download
```bash
# Check status and download
GET /reports/gcore/{uuid}

# Download completed report
POST /reports/gcore/{uuid}/download
```

## 📊 Response Formats

### JSON Format
```json
{
  "uuid": "a2b3c4d5-...",
  "status": "completed",
  "count": 4,
  "data": [
    {
      "Client ID": "829449",
      "Company name": "SDG Test 2",
      "Feature ID": "2362",
      "Feature name": "Block Storage (Standard) - Gb",
      "Metric value": "0.4965",
      "Unit name": "GBM"
    }
  ]
}
```

### CSV Format
```csv
Client ID,Company name,Feature ID,Feature name,Metric value,Unit name
829449,SDG Test 2,2362,Block Storage (Standard) - Gb,0.4965,GBM
```

### Excel Format
```json
{
  "uuid": "a2b3c4d5-...",
  "status": "completed",
  "count": 1024,
  "data": {
    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "data": "base64-encoded-excel-data",
    "size_bytes": 1024,
    "format": "excel"
  }
}
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

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Metrics (Future Enhancement)
- Request count
- Response times
- Error rates
- Token cache hit rate

## 🚀 Production Checklist

- [ ] Configure environment variables
- [ ] Set up logging aggregation
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring and alerting
- [ ] Set up backup procedures
- [ ] Configure log rotation
- [ ] Test health check endpoints
- [ ] Verify token caching works
- [ ] Test all report formats

## 🔄 Updates and Maintenance

### Updating Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Restarting Services
```bash
# Docker Compose
docker-compose restart

# Direct deployment
pkill -f main_new.py
./deploy.sh
```

### Viewing Logs
```bash
# Docker
docker-compose logs -f gcore-api

# Direct deployment
tail -f logs/app.log
```

## 🆘 Troubleshooting

### Common Issues

1. **Authentication Error**
   - Check `GCORE_USERNAME` and `GCORE_PASSWORD`
   - Verify credentials are correct

2. **Token Cache Issues**
   - Check `TOKEN_CACHE_DURATION` setting
   - Restart application to clear cache

3. **Report Generation Timeout**
   - Increase `REPORT_POLL_TIMEOUT`
   - Check Gcore API status

4. **Memory Issues**
   - Monitor memory usage
   - Consider reducing `TOKEN_CACHE_DURATION`

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
python main_new.py
```

## 📞 Support

For issues and questions:
1. Check logs for error messages
2. Verify environment configuration
3. Test with health check endpoint
4. Check Gcore API status

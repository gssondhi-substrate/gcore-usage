"""
Gcore Usage API - Production Ready
A FastAPI application for generating and downloading Gcore usage reports.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from apps.api.routes import router
from config.settings import settings

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate configuration
try:
    settings.validate()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Create FastAPI app
app = FastAPI(
    title="Gcore Statistics Report API",
    version="1.0.0",
    description="API for generating and downloading Gcore usage reports in multiple formats",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Gcore Usage API...")
    logger.info(f"API Base: {settings.GCORE_API_BASE}")
    logger.info(f"Token Cache Duration: {settings.TOKEN_CACHE_DURATION} seconds")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Gcore Usage API...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False
    )

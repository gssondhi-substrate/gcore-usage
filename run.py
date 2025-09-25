"""
Entry point for Gcore Usage API
"""
from apps.main import app

if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    
    uvicorn.run(
        "apps.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True
    )

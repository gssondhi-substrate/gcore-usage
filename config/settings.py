"""
Configuration settings for the Gcore Usage API.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Gcore API Configuration
    GCORE_API_BASE: str = os.getenv("GCORE_API_BASE", "https://api.gcore.com").rstrip("/")
    GCORE_FEATURES_PATH: str = os.getenv("GCORE_FEATURES_PATH", "/billing/v3/report_features")
    GCORE_GENERATE_PATH: str = os.getenv("GCORE_GENERATE_PATH", "/billing/v1/org/files/report")
    GCORE_STATUS_PATH: str = os.getenv("GCORE_STATUS_PATH", "/billing/v1/org/files/{uuid}")
    GCORE_DOWNLOAD_PATH: str = os.getenv("GCORE_DOWNLOAD_PATH", "/billing/v1/org/files/{uuid}/download")
    GCORE_AUTH_PATH: str = os.getenv("GCORE_AUTH_PATH", "/iam/auth/jwt/login")
    
    # Authentication Credentials
    GCORE_USERNAME: str = os.getenv("GCORE_USERNAME", "")
    GCORE_PASSWORD: str = os.getenv("GCORE_PASSWORD", "")
    
    # Token Cache Configuration
    TOKEN_CACHE_DURATION: int = int(os.getenv("TOKEN_CACHE_DURATION", "1800"))  # 30 minutes
    
    # Application Configuration
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8080"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Timeout Configuration
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    REPORT_POLL_TIMEOUT: int = int(os.getenv("REPORT_POLL_TIMEOUT", "600"))
    REPORT_POLL_INTERVAL: int = int(os.getenv("REPORT_POLL_INTERVAL", "10"))
    
    # Security
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Constructed URLs
    @property
    def features_url(self) -> str:
        return f"{self.GCORE_API_BASE}{self.GCORE_FEATURES_PATH}"
    
    @property
    def generate_url(self) -> str:
        return f"{self.GCORE_API_BASE}{self.GCORE_GENERATE_PATH}"
    
    @property
    def status_url_template(self) -> str:
        return f"{self.GCORE_API_BASE}{self.GCORE_STATUS_PATH}"
    
    @property
    def download_url_template(self) -> str:
        return f"{self.GCORE_API_BASE}{self.GCORE_DOWNLOAD_PATH}"
    
    @property
    def auth_url(self) -> str:
        return f"{self.GCORE_API_BASE}{self.GCORE_AUTH_PATH}"
    
    def validate(self) -> None:
        """Validate required configuration."""
        if not self.GCORE_USERNAME or not self.GCORE_PASSWORD:
            raise ValueError(
                "GCORE_USERNAME and GCORE_PASSWORD must be set in environment variables"
            )


# Global settings instance
settings = Settings()

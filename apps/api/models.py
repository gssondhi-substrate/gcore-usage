"""
Pydantic models for API requests and responses.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class SimpleReportRequest(BaseModel):
    """Request model for generating reports."""
    gcore_user_id: str = Field(..., description="Target Gcore Client/User ID to filter (string or numeric).")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date in YYYY-MM-DD format")
    format: str = Field(default="json", description="Output format: json, csv, or excel")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['json', 'csv', 'excel']
        if v.lower() not in allowed_formats:
            raise ValueError(f'Format must be one of: {", ".join(allowed_formats)}')
        return v.lower()


class StatusRequest(BaseModel):
    """Request model for checking report status."""
    format: str = Field(default="json", description="Output format: json, csv, or excel")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['json', 'csv', 'excel']
        if v.lower() not in allowed_formats:
            raise ValueError(f'Format must be one of: {", ".join(allowed_formats)}')
        return v.lower()


class ReportResponse(BaseModel):
    """Response model for report data."""
    uuid: str
    status: str
    count: int
    data: Any  # Can be List[Dict[str, Any]] for JSON/CSV or Dict for Excel


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    service: str
    version: str
    timestamp: float

"""
Common response models
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    agents: Dict[str, str]
    snowflake: str

class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    error: str
    detail: Optional[str] = None

class SuccessResponse(BaseModel):
    """Generic success response"""
    status: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None
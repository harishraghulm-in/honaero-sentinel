from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error explanation")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context or validation errors")


class ErrorResponse(BaseModel):
    error: ErrorDetail


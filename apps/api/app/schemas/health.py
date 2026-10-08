from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Liveness status of the API")
    version: str = Field(description="API version")
    timestamp: str = Field(description="ISO 8601 current timestamp")


class ToolchainStatus(BaseModel):
    name: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    details: Optional[str] = None


class ReadyResponse(BaseModel):
    status: str = Field(default="ready", description="Readiness status")
    database: bool = Field(description="Database connectivity status")
    toolchains: Dict[str, ToolchainStatus] = Field(description="Availability of compilers and tools")
    details: Optional[Dict[str, Any]] = None


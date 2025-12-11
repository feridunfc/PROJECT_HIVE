"""
Pydantic models for API requests and responses.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class PipelineType(str, Enum):
    T0_VELOCITY = "t0"
    T1_FORTRESS = "t1"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Request Models
class PipelineRequest(BaseModel):
    """Request model for starting a pipeline."""
    goal: str = Field(..., min_length=1, max_length=1000, description="The goal for the pipeline")
    pipeline_type: PipelineType = Field(default=PipelineType.T1_FORTRESS, description="Pipeline type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @validator('goal')
    def goal_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Goal cannot be empty')
        return v.strip()


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


# Response Models
class TaskResponse(BaseModel):
    """Response model for a task."""
    task_id: str
    goal: str
    pipeline_type: PipelineType
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""
    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskResultResponse(BaseModel):
    """Response model for task result."""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"
    uptime: Optional[float] = None
    queue_stats: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    code: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class MetricsResponse(BaseModel):
    """Metrics response model."""
    metrics: Dict[str, Any]
    prometheus_endpoint: str = "/metrics"
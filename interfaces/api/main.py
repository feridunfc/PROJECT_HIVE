"""
PROJECT_HIVE FastAPI REST API
"""
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import uuid
import time
from datetime import datetime
from fastapi import WebSocket

from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from core.queue import task_queue
from core.telemetry.metrics import metrics
from observability.session_replay import session_replay

from .dependencies import get_api_key, rate_limit_check, get_current_tenant, health_check
from .models import (
    PipelineRequest, TaskResponse, TaskListResponse, TaskResultResponse,
    HealthResponse, ErrorResponse, MetricsResponse, PaginationParams
)
from .websocket import websocket_endpoint, manager


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    print("🚀 Starting PROJECT_HIVE API...")

    # Start task queue
    task_queue.start()

    # Record startup metric
    metrics.increment_counter("api_startups")

    yield

    # Shutdown
    print("🛑 Shutting down PROJECT_HIVE API...")

    # Stop task queue
    task_queue.stop()

    # Record shutdown metric
    metrics.increment_counter("api_shutdowns")


# Create FastAPI app
app = FastAPI(
    title="PROJECT_HIVE API",
    description="Enterprise Multi-Agent Orchestration Framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request ID middleware
@app.middleware("http")
async def add_request_id(request, call_next):
    """Add request ID to each request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Record request start
    start_time = time.time()

    response = await call_next(request)

    # Record request duration
    duration = time.time() - start_time
    metrics.record_histogram("api_request_duration", duration)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    import psutil
    import os

    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": time.time() - psutil.Process(os.getpid()).create_time(),
        "queue_stats": task_queue.get_stats()
    }


# Metrics endpoint
@app.get("/metrics", tags=["System"])
async def get_metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest
    from fastapi.responses import Response

    try:
        prometheus_metrics = metrics.export_prometheus()
        return Response(content=prometheus_metrics, media_type="text/plain")
    except Exception as e:
        return JSONResponse(
            content={"error": "Metrics not available", "detail": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# Start pipeline endpoint
@app.post("/api/v1/run", response_model=Dict[str, Any], tags=["Pipelines"])
async def run_pipeline(
        request: PipelineRequest,
        background_tasks: BackgroundTasks,
        api_key: str = Depends(get_api_key),
        tenant_id: str = Depends(get_current_tenant)
):
    """
    Start a new pipeline execution.

    Returns immediately with a task ID. Use the task ID to poll for status.
    """
    # Add tenant to metadata
    metadata = request.metadata.copy()
    metadata["tenant_id"] = tenant_id
    metadata["api_key"] = api_key[:8]  # Store truncated API key for audit

    # Submit task to queue
    task_id = task_queue.submit_task(
        goal=request.goal,
        pipeline_type=request.pipeline_type.value,
        metadata=metadata
    )

    # Record metric
    metrics.increment_counter("pipeline_starts", tags={
        "pipeline_type": request.pipeline_type.value,
        "tenant": tenant_id
    })

    # Return task ID immediately
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Pipeline task submitted successfully",
        "poll_url": f"/api/v1/tasks/{task_id}",
        "websocket_url": f"/ws/tasks/{task_id}",
        "created_at": datetime.now().isoformat()
    }


# Get task status endpoint
@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task_status(
        task_id: str,
        api_key: str = Depends(get_api_key)
):
    """Get the status of a specific task."""
    task = task_queue.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    # Check authorization (in production, verify tenant owns this task)
    # For now, just return the task

    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        pipeline_type=task.pipeline_type,
        status=task.status.value,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error=task.error,
        metadata=task.metadata,
        session_id=task.session_id
    )


# Get task result endpoint
@app.get("/api/v1/tasks/{task_id}/result", response_model=TaskResultResponse, tags=["Tasks"])
async def get_task_result(
        task_id: str,
        api_key: str = Depends(get_api_key)
):
    """Get the result of a completed task."""
    task = task_queue.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.status.value not in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is not completed yet. Status: {task.status.value}"
        )

    return TaskResultResponse(
        task_id=task.task_id,
        status=task.status.value,
        result=task.result,
        artifacts=task.result.get("artifacts") if task.result else None,
        metrics=task.result.get("metrics") if task.result else None,
        error=task.error
    )


# List tasks endpoint
@app.get("/api/v1/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def list_tasks(
        pagination: PaginationParams = Depends(),
        api_key: str = Depends(get_api_key),
        tenant_id: str = Depends(get_current_tenant)
):
    """List all tasks for the current tenant."""
    # In production, filter by tenant
    # For now, return all tasks

    tasks = task_queue.list_tasks(limit=pagination.limit, offset=pagination.offset)

    task_responses = []
    for task in tasks:
        # Filter by tenant in production
        task_responses.append(TaskResponse(
            task_id=task.task_id,
            goal=task.goal,
            pipeline_type=task.pipeline_type,
            status=task.status.value,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error=task.error,
            metadata=task.metadata,
            session_id=task.session_id
        ))

    return TaskListResponse(
        tasks=task_responses,
        total=len(task_queue.tasks),
        limit=pagination.limit,
        offset=pagination.offset
    )


# Cancel task endpoint
@app.post("/api/v1/tasks/{task_id}/cancel", tags=["Tasks"])
async def cancel_task(
        task_id: str,
        api_key: str = Depends(get_api_key)
):
    """Cancel a pending task."""
    success = task_queue.cancel_task(task_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task {task_id}. It may already be running or completed."
        )

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "Task cancelled successfully"
    }


# Session endpoints
@app.get("/api/v1/sessions/{session_id}", tags=["Sessions"])
async def get_session(
        session_id: str,
        api_key: str = Depends(get_api_key)
):
    """Get session replay data."""
    session = session_replay.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return session


@app.get("/api/v1/sessions", tags=["Sessions"])
async def list_sessions(
        limit: int = 50,
        offset: int = 0,
        api_key: str = Depends(get_api_key)
):
    """List recent sessions."""
    sessions = session_replay.list_sessions(limit=limit, offset=offset)
    return {
        "sessions": sessions,
        "total": len(sessions),  # Note: This is just the count in this batch
        "limit": limit,
        "offset": offset
    }


# WebSocket endpoints
@app.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    """WebSocket for real-time task updates."""
    await websocket_endpoint(websocket, task_id)


@app.websocket("/ws/queue")
async def websocket_queue_updates(websocket: WebSocket):
    """WebSocket for real-time queue updates."""
    await websocket_endpoint(websocket)


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code=f"HTTP_{exc.status_code}",
            detail=str(exc) if exc.detail != str(exc) else None,
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle all other exceptions."""
    import traceback

    # Log the full traceback
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            code="INTERNAL_ERROR",
            detail=str(exc),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


# Static files for dashboard (optional)
app.mount("/dashboard", StaticFiles(directory="interfaces/dashboard/static", html=True), name="dashboard")

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "interfaces.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
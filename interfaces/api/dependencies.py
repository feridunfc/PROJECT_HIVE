"""
API dependencies and authentication.
"""
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery
import os

from core.telemetry.metrics import metrics

# API Key security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
        api_key_header: Optional[str] = Depends(api_key_header),
        api_key_query: Optional[str] = Depends(api_key_query),
) -> str:
    """Get and validate API key."""
    # Get API key from environment or use default for development
    valid_api_keys = os.getenv("HIVE_API_KEYS", "dev_key_123,test_key_456").split(",")

    api_key = api_key_header or api_key_query

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )

    if api_key not in valid_api_keys:
        # Record failed authentication attempt
        metrics.increment_counter("api_auth_failed")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Record successful authentication
    metrics.increment_counter("api_auth_success")

    return api_key


async def rate_limit_check(api_key: str = Depends(get_api_key)):
    """Simple rate limiting check."""
    # In production, use Redis or similar for rate limiting
    # For now, we just track the metric
    metrics.increment_counter("api_requests", tags={"api_key": api_key[:8]})

    # Basic rate limiting: max 100 requests per minute per key
    # This would be implemented with Redis in production
    return api_key


async def get_current_tenant(api_key: str = Depends(get_api_key)) -> str:
    """Get tenant ID from API key."""
    # In a real implementation, you would map API keys to tenants
    # For now, use the API key itself as tenant ID
    return f"tenant_{api_key[:8]}"


# Health check dependency
async def health_check():
    """Simple health check."""
    return {"status": "healthy"}
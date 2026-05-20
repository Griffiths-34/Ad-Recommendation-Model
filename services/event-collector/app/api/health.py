"""Health check endpoints"""

try:
    from fastapi import APIRouter, status
    from fastapi.responses import JSONResponse
except ImportError:
    # Minimal stubs so the module can be analyzed or run in environments without fastapi.
    class APIRouter:
        def __init__(self):
            pass

        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    class status:
        HTTP_200_OK = 200
        HTTP_503_SERVICE_UNAVAILABLE = 503

    class JSONResponse:
        def __init__(self, *, status_code=200, content=None):
            self.status_code = status_code
            self.content = content or {}

from app.core.kafka_producer import kafka_producer
from app.core.redis_client import redis_client

router = APIRouter()


@router.get("/")
async def health_check() -> JSONResponse:
    """
    Basic health check endpoint
    
    Returns:
        JSON response with service status
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "event-collector",
            "version": "1.0.0",
        },
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness check - verifies all dependencies are available
    
    Checks:
    - Kafka connection
    - Redis connection
    
    Returns:
        JSON response with dependency status
    """
    checks = {
        "kafka": kafka_producer.is_connected,
        "redis": redis_client.is_connected,
    }
    
    all_healthy = all(checks.values())
    
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
        },
    )


@router.get("/live")
async def liveness_check() -> JSONResponse:
    """
    Liveness check - verifies service is running
    
    Returns:
        JSON response indicating service is alive
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
        },
    )

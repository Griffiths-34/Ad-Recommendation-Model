"""Rate limiting middleware"""

import time
from typing import Callable

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.redis_client import redis_client

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits before processing request
        
        Rate limits:
        - Per minute: configurable
        - Per hour: configurable
        
        Uses sliding window algorithm with Redis
        """
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        
        # Check minute rate limit
        minute_key = f"{client_ip}:minute"
        is_allowed_minute, remaining_minute = await redis_client.rate_limit_check(
            identifier=minute_key,
            limit=settings.RATE_LIMIT_PER_MINUTE,
            window=60,
        )
        
        # Check hour rate limit
        hour_key = f"{client_ip}:hour"
        is_allowed_hour, remaining_hour = await redis_client.rate_limit_check(
            identifier=hour_key,
            limit=settings.RATE_LIMIT_PER_HOUR,
            window=3600,
        )
        
        # If either limit exceeded, return 429
        if not is_allowed_minute or not is_allowed_hour:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                remaining_minute=remaining_minute,
                remaining_hour=remaining_hour,
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": 60 if not is_allowed_minute else 3600,
                },
                headers={
                    "X-RateLimit-Limit-Minute": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining-Minute": str(remaining_minute),
                    "X-RateLimit-Limit-Hour": str(settings.RATE_LIMIT_PER_HOUR),
                    "X-RateLimit-Remaining-Hour": str(remaining_hour),
                    "Retry-After": "60" if not is_allowed_minute else "3600",
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(settings.RATE_LIMIT_PER_HOUR)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)
        
        return response

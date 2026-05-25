"""
Event Collector Service - Main Application

High-performance FastAPI service for collecting user events from the tracker SDK.
Handles event ingestion, validation, and publishing to Kafka.

Features:
- High throughput event collection
- Request validation and sanitization
- Rate limiting and DDoS protection
- Kafka event publishing
- Redis caching
- Prometheus metrics
- Distributed tracing
- Health checks
"""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import events, health, recommendations
from app.core.config import settings
from app.core.kafka_producer import kafka_producer
from app.core.logging import setup_logging
from app.core.redis_client import redis_client
from app.middleware.rate_limit import RateLimitMiddleware

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Event Collector Service", version="1.0.0")
    
    # Initialize Kafka producer
    await kafka_producer.start()
    logger.info("Kafka producer started")
    
    # Initialize Redis
    await redis_client.connect()
    logger.info("Redis connected")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Event Collector Service")
    
    # Close Kafka producer
    await kafka_producer.stop()
    logger.info("Kafka producer stopped")
    
    # Close Redis
    await redis_client.disconnect()
    logger.info("Redis disconnected")


# Create FastAPI application
app = FastAPI(
    title="Event Collector API",
    description="High-performance event collection service for ad recommendation platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware — credentials cannot be used with a wildcard origin
_cors_origins = settings.CORS_ORIGINS
_allow_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Add request ID to context
    request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")
    
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=f"{duration:.3f}s",
            request_id=request_id,
        )
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        
        return response
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration=f"{duration:.3f}s",
            request_id=request_id,
        )
        raise


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(recommendations.router, tags=["Recommendations"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Event Collector API",
        "version": "1.0.0",
        "status": "running",
        "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None,  # Use structlog instead
    )

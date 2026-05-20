"""Events API endpoints"""

import time
from typing import List

import logging
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.kafka_producer import kafka_producer
from app.core.redis_client import redis_client
from app.models.event import EventBatch, EventProperties, EventResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def collect_events(
    event_batch: EventBatch,
    request: Request,
) -> EventResponse:
    """
    Collect a batch of events from the client
    
    This endpoint receives events from the tracker SDK, validates them,
    and publishes them to Kafka for downstream processing.
    
    Features:
    - Batch event processing
    - Event validation and sanitization
    - Kafka publishing
    - Error handling with DLQ
    
    Args:
        event_batch: Batch of events with metadata
        request: FastAPI request object
        
    Returns:
        EventResponse with status and statistics
    """
    start_time = time.time()
    
    # Extract client metadata
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Add metadata to events
    enriched_events = []
    errors = []
    
    for event in event_batch.events:
        try:
            # Enrich event with request metadata
            enriched_event = {
                "eventName": event.eventName,
                "properties": event.properties or {},
                "timestamp": event.timestamp,
                "userId": event.userId,
                "sessionId": event.sessionId,
                "metadata": {
                    "sdkVersion": event_batch.metadata.sdkVersion,
                    "ipAddress": client_ip,
                    "userAgent": user_agent,
                    "receivedAt": int(time.time() * 1000),
                },
            }
            
            enriched_events.append(enriched_event)
            
        except Exception as e:
            logger.error(
                "event_enrichment_failed: %s (event=%s)",
                str(e),
                event.eventName,
            )
            errors.append(f"Failed to process event {event.eventName}: {str(e)}")
    
    # Publish events to Kafka
    published_count = 0
    
    try:
        await kafka_producer.send_batch(
            topic=settings.KAFKA_TOPIC_EVENTS,
            events=enriched_events,
        )
        published_count = len(enriched_events)
        
        logger.info(
            "events_collected: count=%d session_id=%s duration=%s",
            published_count,
            event_batch.metadata.sessionId,
            f"{time.time() - start_time:.3f}s",
        )
        
        # Cache event stats for analytics
        await _cache_event_stats(enriched_events)
        
    except Exception as e:
        logger.error(
            "event_publishing_failed: %s (event_count=%d)",
            str(e),
            len(enriched_events),
        )
        errors.append(f"Failed to publish events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to publish events to message queue",
        )
    
    return EventResponse(
        success=True,
        message="Events collected successfully",
        eventsReceived=len(event_batch.events),
        eventsProcessed=published_count,
        errors=errors if errors else None,
    )


@router.post("/track", status_code=status.HTTP_201_CREATED)
async def track_single_event(
    event: EventProperties,
    request: Request,
) -> JSONResponse:
    """
    Track a single event (simplified endpoint)
    
    Args:
        event: Single event to track
        request: FastAPI request object
        
    Returns:
        Success response
    """
    # Extract client metadata
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Enrich event
    enriched_event = {
        "eventName": event.eventName,
        "properties": event.properties or {},
        "timestamp": event.timestamp,
        "userId": event.userId,
        "sessionId": event.sessionId,
        "metadata": {
            "ipAddress": client_ip,
            "userAgent": user_agent,
            "receivedAt": int(time.time() * 1000),
        },
    }
    
    try:
        # Publish to Kafka
        key = event.userId or event.sessionId
        await kafka_producer.send_event(
            topic=settings.KAFKA_TOPIC_EVENTS,
            event=enriched_event,
            key=key,
        )
        
        logger.info(
            "event_tracked: %s user_id=%s session_id=%s",
            event.eventName,
            event.userId,
            event.sessionId,
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"success": True, "message": "Event tracked successfully"},
        )
        
    except Exception as e:
        logger.error("event_track_failed: %s (event=%s)", str(e), event.eventName)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to track event",
        )


@router.get("/stats")
async def get_event_stats() -> dict:
    """
    Get real-time event statistics
    
    Returns:
        Event statistics from cache
    """
    try:
        stats = await redis_client.get_json("event_stats:summary")
        if not stats:
            return {
                "totalEvents": 0,
                "eventsByType": {},
                "lastUpdated": None,
            }
        return stats
    except Exception as e:
        logger.error("get_stats_failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )


async def _cache_event_stats(events: List[dict]) -> None:
    """Cache event statistics for real-time analytics"""
    try:
        # Count events by type
        event_counts = {}
        for event in events:
            event_name = event.get("eventName", "unknown")
            event_counts[event_name] = event_counts.get(event_name, 0) + 1
        
        # Update Redis counters
        for event_name, count in event_counts.items():
            await redis_client.incr(f"event_count:{event_name}")
        
        # Update total counter
        await redis_client.incr("event_count:total")
        
        # Cache summary (expires in 5 minutes)
        summary = {
            "totalEvents": await redis_client.get("event_count:total") or 0,
            "eventsByType": event_counts,
            "lastUpdated": int(time.time()),
        }
        await redis_client.cache_json("event_stats:summary", summary, ex=300)
        
    except Exception as e:
        logger.error("cache_stats_failed: %s", str(e))
        # Don't fail the request if caching fails
        pass

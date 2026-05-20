"""Event data models and schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EventProperties(BaseModel):
    """Event properties schema"""
    
    eventName: str = Field(..., min_length=1, max_length=100)
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: int = Field(..., gt=0)
    userId: Optional[str] = Field(None, max_length=100)
    sessionId: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('properties')
    @classmethod
    def validate_properties_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate properties size"""
        import json
        if len(json.dumps(v)) > 5120:  # 5KB limit
            raise ValueError("Properties size exceeds 5KB limit")
        return v


class EventMetadata(BaseModel):
    """Event metadata"""
    
    sdkVersion: str = Field(..., min_length=1, max_length=20)
    timestamp: int
    sessionId: str
    userAgent: Optional[str] = None
    ipAddress: Optional[str] = None
    country: Optional[str] = None
    device: Optional[str] = None


class EventBatch(BaseModel):
    """Batch of events from client"""
    
    events: List[EventProperties] = Field(..., min_length=1, max_length=100)
    metadata: EventMetadata
    
    @field_validator('events')
    @classmethod
    def validate_batch_size(cls, v: List[EventProperties]) -> List[EventProperties]:
        """Validate batch size"""
        if len(v) > 100:
            raise ValueError("Batch size exceeds maximum of 100 events")
        return v


class EventResponse(BaseModel):
    """Response for event submission"""
    
    success: bool
    message: str
    eventsReceived: int
    eventsProcessed: int
    errors: Optional[List[str]] = None


class ProductEvent(BaseModel):
    """Product-related event data"""
    
    productId: str
    productName: str
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    brand: Optional[str] = None
    variant: Optional[str] = None
    quantity: Optional[int] = 1


class SearchEvent(BaseModel):
    """Search event data"""
    
    searchTerm: str = Field(..., min_length=1, max_length=200)
    resultsCount: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None


class EcommerceEvent(BaseModel):
    """E-commerce transaction event"""
    
    orderId: str
    revenue: float
    currency: str
    products: List[ProductEvent]
    coupon: Optional[str] = None
    shipping: Optional[float] = None
    tax: Optional[float] = None


class PageViewEvent(BaseModel):
    """Page view event data"""
    
    url: str
    title: str
    referrer: Optional[str] = None
    path: str


class AdEvent(BaseModel):
    """Ad interaction event"""
    
    adId: str
    campaignId: str
    eventType: str  # impression, click, conversion
    position: Optional[str] = None
    creative: Optional[str] = None


# Database models (SQLAlchemy)
class EventRecord(BaseModel):
    """Event record for database storage"""
    
    id: Optional[int] = None
    event_name: str
    user_id: Optional[str] = None
    session_id: str
    timestamp: datetime
    properties: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

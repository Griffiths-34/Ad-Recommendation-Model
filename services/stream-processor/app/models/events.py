"""
Event models and schemas using Pydantic.
Validates and structures incoming event data from Kafka.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class EventProperties(BaseModel):
    """Flexible properties for different event types."""
    
    # Common fields
    productId: Optional[str] = None
    productName: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    brand: Optional[str] = None
    
    # Search specific
    query: Optional[str] = None
    resultsCount: Optional[int] = None
    
    # Purchase specific
    orderId: Optional[str] = None
    revenue: Optional[float] = None
    products: Optional[List[Dict[str, Any]]] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    
    # Ad specific
    adId: Optional[str] = None
    campaignId: Optional[str] = None
    position: Optional[str] = None
    
    # Additional flexible data
    class Config:
        extra = "allow"  # Allow additional fields


class Event(BaseModel):
    """
    Main event model matching tracker SDK output.
    Represents a single user action on the platform.
    """
    
    eventName: str = Field(..., description="Type of event (product_view, purchase, etc.)")
    properties: EventProperties = Field(default_factory=EventProperties)
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    userId: Optional[str] = Field(None, description="User ID if identified")
    sessionId: str = Field(..., description="Session identifier")
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert event to database-compatible dictionary."""
        return {
            "event_name": self.eventName,
            "user_id": self.userId,
            "session_id": self.sessionId,
            "properties": self.properties.model_dump(exclude_none=True),
            "timestamp": datetime.fromtimestamp(self.timestamp / 1000)  # Convert to datetime
        }


class EventBatch(BaseModel):
    """Batch of events from Kafka consumer."""
    
    events: List[Event]
    metadata: Optional[Dict[str, Any]] = None


class UserFeatures(BaseModel):
    """
    Aggregated user features for ML model.
    Built from historical events.
    """
    
    user_id: str
    
    # Viewing behavior
    total_views: int = 0
    categories_viewed: Dict[str, int] = Field(default_factory=dict)
    brands_viewed: Dict[str, int] = Field(default_factory=dict)
    avg_price_viewed: float = 0.0
    max_price_viewed: float = 0.0
    
    # Search behavior
    search_count: int = 0
    top_search_terms: List[str] = Field(default_factory=list)
    
    # Cart behavior
    add_to_cart_count: int = 0
    remove_from_cart_count: int = 0
    cart_abandonment_rate: float = 0.0
    
    # Purchase behavior
    purchase_count: int = 0
    total_revenue: float = 0.0
    avg_order_value: float = 0.0
    purchased_categories: Dict[str, int] = Field(default_factory=dict)
    
    # Time patterns
    active_hours: List[int] = Field(default_factory=list)
    active_days: List[str] = Field(default_factory=list)
    last_active: Optional[datetime] = None
    
    # Session info
    avg_session_duration: float = 0.0
    sessions_count: int = 0
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_vector(self) -> List[float]:
        """
        Convert features to numerical vector for ML model.
        Used by collaborative filtering algorithm.
        """
        return [
            float(self.total_views),
            float(self.purchase_count),
            float(self.avg_price_viewed),
            float(self.total_revenue),
            float(self.cart_abandonment_rate),
            float(self.search_count),
            float(len(self.categories_viewed)),
            float(len(self.purchased_categories)),
        ]


class ProductFeatures(BaseModel):
    """Product features for content-based filtering."""
    
    product_id: str
    name: str
    category: str
    price: float
    brand: str
    
    # Popularity metrics
    view_count: int = 0
    purchase_count: int = 0
    add_to_cart_count: int = 0
    conversion_rate: float = 0.0
    
    # Co-occurrence (users who viewed this also viewed...)
    also_viewed: Dict[str, int] = Field(default_factory=dict)
    also_purchased: Dict[str, int] = Field(default_factory=dict)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "event-collector"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Event Collector API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_track_single_event():
    """Test single event tracking"""
    event_data = {
        "eventName": "page_view",
        "properties": {
            "url": "https://example.com",
            "title": "Test Page"
        },
        "timestamp": 1700000000000,
        "userId": "test-user-123",
        "sessionId": "test-session-456"
    }
    
    response = client.post("/events/track", json=event_data)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_collect_event_batch():
    """Test batch event collection"""
    batch_data = {
        "events": [
            {
                "eventName": "product_view",
                "properties": {"productId": "prod-001"},
                "timestamp": 1700000000000,
                "sessionId": "test-session-789"
            },
            {
                "eventName": "add_to_cart",
                "properties": {"productId": "prod-001", "quantity": 1},
                "timestamp": 1700000001000,
                "sessionId": "test-session-789"
            }
        ],
        "metadata": {
            "sdkVersion": "1.0.0",
            "timestamp": 1700000000000,
            "sessionId": "test-session-789"
        }
    }
    
    response = client.post("/events/", json=batch_data)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["eventsReceived"] == 2
    assert data["eventsProcessed"] == 2

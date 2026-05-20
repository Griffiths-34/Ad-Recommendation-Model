"""Configuration settings for the Event Collector service"""

from typing import List, Callable, Optional

from pydantic_settings import BaseSettings
try:
    from pydantic import Field
except Exception:
    # Fallback Field for environments where pydantic is not installed or not resolved by the editor.
    # This provides a minimal replacement that returns the default or calls the default_factory.
    def Field(*, default=None, default_factory: Optional[Callable] = None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Event Collector"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/event_db"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    # PostgreSQL (for recommendations)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_DB: str = "ad_recommendation"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_EVENTS: str = "user-events"
    KAFKA_TOPIC_EVENTS_DLQ: str = "user-events-dlq"
    KAFKA_BATCH_SIZE: int = 16384
    KAFKA_LINGER_MS: int = 10
    KAFKA_COMPRESSION_TYPE: str = "gzip"
    KAFKA_ACKS: int = 1  # Changed from str to int
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_DECODE_RESPONSES: bool = False
    
    # Security
    API_KEY_HEADER: str = "X-API-Key"
    VALID_API_KEYS: List[str] = Field(default_factory=lambda: ["demo-api-key"])
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 1000
    RATE_LIMIT_PER_HOUR: int = 50000
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    
    # Monitoring
    JAEGER_AGENT_HOST: str = "localhost"
    JAEGER_AGENT_PORT: int = 6831
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    
    # Event validation
    MAX_EVENT_SIZE: int = 10240  # 10KB
    MAX_BATCH_SIZE: int = 100
    MAX_PROPERTIES_SIZE: int = 5120  # 5KB
    
    # Performance
    REQUEST_TIMEOUT: int = 30
    KEEP_ALIVE_TIMEOUT: int = 65
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

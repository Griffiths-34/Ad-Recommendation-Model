"""
Configuration management for Stream Processor.
Uses Pydantic Settings for validation and type safety.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "stream-processor-group"
    KAFKA_TOPIC_EVENTS: str = "user_events"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_DB: str = "event_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_MIN_POOL_SIZE: int = 5
    POSTGRES_MAX_POOL_SIZE: int = 20
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Processing Configuration
    BATCH_SIZE: int = 100
    BATCH_TIMEOUT_SECONDS: int = 5
    WORKER_COUNT: int = 4
    
    # Feature Store Configuration
    FEATURE_STORE_UPDATE_INTERVAL: int = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def kafka_servers(self) -> List[str]:
        """Parse Kafka servers from comma-separated string."""
        return [s.strip() for s in self.KAFKA_BOOTSTRAP_SERVERS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

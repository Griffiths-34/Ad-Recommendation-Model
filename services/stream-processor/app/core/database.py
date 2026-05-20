"""
Database connection pool management using asyncpg.
Provides efficient connection pooling with retry logic.
"""

import asyncpg
import structlog
from typing import Optional
from app.core.config import settings

logger = structlog.get_logger()


class DatabasePool:
    """Manages PostgreSQL connection pool with asyncpg."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self) -> None:
        """
        Create connection pool to PostgreSQL.
        Uses connection pooling for better performance.
        """
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                min_size=settings.POSTGRES_MIN_POOL_SIZE,
                max_size=settings.POSTGRES_MAX_POOL_SIZE,
                command_timeout=60,
            )
            logger.info(
                "database_connected",
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                pool_size=settings.POSTGRES_MAX_POOL_SIZE
            )
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise
            
    async def disconnect(self) -> None:
        """Close connection pool gracefully."""
        if self.pool:
            await self.pool.close()
            logger.info("database_disconnected")
            
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query without returning results.
        Used for INSERT, UPDATE, DELETE.
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
            
    async def fetch(self, query: str, *args) -> list:
        """
        Execute a query and return all results.
        Used for SELECT queries.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
            
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute a query and return first result.
        Used for SELECT queries that return single row.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
            
    async def fetchval(self, query: str, *args):
        """
        Execute a query and return single value.
        Used for COUNT, SUM, etc.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)


# Global database instance
db = DatabasePool()

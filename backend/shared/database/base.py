"""
Database base configuration and models
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from typing import AsyncGenerator
import redis.asyncio as redis
from contextlib import asynccontextmanager

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/prism_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# SQLAlchemy setup
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,  # For async usage
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()
metadata = MetaData()

# Redis setup
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session generator"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_redis_client():
    """Get Redis client instance"""
    return redis_client

class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    async def create_tables():
        """Create all database tables"""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @staticmethod
    async def drop_tables():
        """Drop all database tables"""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    @staticmethod
    async def health_check() -> bool:
        """Check database connectivity"""
        try:
            async with get_db_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception:
            return False

class CacheManager:
    """Redis cache management utilities"""
    
    @staticmethod
    async def get(key: str) -> str | None:
        """Get value from cache"""
        return await redis_client.get(key)
    
    @staticmethod
    async def set(key: str, value: str, expire: int = 3600):
        """Set value in cache with expiration"""
        await redis_client.set(key, value, ex=expire)
    
    @staticmethod
    async def delete(key: str):
        """Delete key from cache"""
        await redis_client.delete(key)
    
    @staticmethod
    async def health_check() -> bool:
        """Check Redis connectivity"""
        try:
            await redis_client.ping()
            return True
        except Exception:
            return False
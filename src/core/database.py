#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接和模型管理
Database Connection and Model Management
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
import redis.asyncio as redis
from datetime import datetime
from .config import settings

# SQLAlchemy基础配置
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis连接池
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# 数据库模型定义
class TaskRecord(Base):
    """任务记录表"""
    __tablename__ = "task_records"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True)
    stock_code = Column(String(20), index=True)
    task_type = Column(String(50))
    status = Column(String(20), default="pending")
    input_data = Column(JSON)
    result_data = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

class ArticleRecord(Base):
    """文章记录表"""
    __tablename__ = "article_records"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), index=True)
    stock_code = Column(String(20), index=True)
    article_style = Column(String(50))
    title = Column(String(500))
    content = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class StockDataCache(Base):
    """股票数据缓存表"""
    __tablename__ = "stock_data_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), index=True)
    data_type = Column(String(50))
    data_content = Column(JSON)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# 数据库操作类
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    @asynccontextmanager
    async def get_db_session(self):
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def save_task_record(self, task_record: dict):
        """保存任务记录"""
        async with self.get_db_session() as session:
            record = TaskRecord(**task_record)
            session.add(record)
            return record.id
    
    async def update_task_status(self, task_id: str, status: str, result_data: dict = None):
        """更新任务状态"""
        async with self.get_db_session() as session:
            record = session.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
            if record:
                record.status = status
                record.updated_at = datetime.utcnow()
                if status == "completed":
                    record.completed_at = datetime.utcnow()
                if result_data:
                    record.result_data = result_data

# Redis缓存管理器
class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self):
        self.redis = redis_client
    
    async def get(self, key: str):
        """获取缓存"""
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, ttl: int = None):
        """设置缓存"""
        if ttl:
            return await self.redis.setex(key, ttl, value)
        return await self.redis.set(key, value)
    
    async def delete(self, key: str):
        """删除缓存"""
        return await self.redis.delete(key)
    
    async def exists(self, key: str):
        """检查键是否存在"""
        return await self.redis.exists(key)
    
    def generate_cache_key(self, prefix: str, stock_code: str, data_type: str = ""):
        """生成缓存键"""
        if data_type:
            return f"{prefix}:{stock_code}:{data_type}"
        return f"{prefix}:{stock_code}"

# 全局实例
db_manager = DatabaseManager()
cache_manager = CacheManager()

# 数据库初始化
def init_database():
    """初始化数据库"""
    db_manager.create_tables()
    print("✅ 数据库表创建完成")
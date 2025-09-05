#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prism系统配置管理
Configuration Management for Prism System
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """系统配置类"""
    
    # 基础服务配置
    APP_NAME: str = "Prism Stock Analysis System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 3005
    SERVER_IP: str = "35.77.54.203"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 100
    
    # PostgreSQL配置
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/prism_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "Asia/Shanghai"
    
    # AI Agent池配置
    AI_AGENT_POOL_SIZE: int = 5
    AI_AGENT_MAX_WORKERS: int = 10
    AI_AGENT_TIMEOUT: int = 30
    
    # 股票数据API配置
    STOCK_API_BASE_URL: str = f"http://{SERVER_IP}:3003"
    STOCK_API_TIMEOUT: int = 10
    STOCK_API_RETRY_TIMES: int = 3
    
    # 缓存配置
    CACHE_TTL_STOCK_DATA: int = 3600  # 1小时
    CACHE_TTL_AI_RESPONSE: int = 1800  # 30分钟
    
    # 任务配置
    MAX_CONCURRENT_TASKS: int = 10
    TASK_TIMEOUT: int = 300  # 5分钟
    TASK_RETRY_TIMES: int = 2
    
    # 文章生成配置
    ARTICLE_STYLES: List[str] = ["professional", "dark", "optimistic", "conservative"]
    DEFAULT_ARTICLE_COUNT: int = 3
    
    # 监控配置
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()

# 环境变量检查
def validate_environment():
    """验证环境配置"""
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL", 
        "CELERY_BROKER_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return True
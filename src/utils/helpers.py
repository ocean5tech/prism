#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数和辅助方法
Utility Functions and Helper Methods
"""

import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal
import asyncio
from loguru import logger

class DataProcessor:
    """数据处理工具类"""
    
    @staticmethod
    def clean_numeric_value(value: Any) -> Optional[float]:
        """清洗数值数据"""
        if value is None or value == "":
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # 移除中文字符和特殊符号
            cleaned = re.sub(r'[^\d.-]', '', value)
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清洗文本数据"""
        if not text:
            return ""
        
        # 移除多余空格和特殊字符
        cleaned = re.sub(r'\s+', ' ', str(text).strip())
        
        # 移除HTML标签
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        return cleaned
    
    @staticmethod
    def parse_percentage(value: str) -> Optional[float]:
        """解析百分比字符串"""
        if not value:
            return None
        
        # 移除%符号和空格
        cleaned = str(value).replace('%', '').strip()
        
        try:
            return float(cleaned) / 100.0
        except ValueError:
            return None
    
    @staticmethod
    def format_large_number(value: float, precision: int = 2) -> str:
        """格式化大数字 (万、亿)"""
        if value is None:
            return "N/A"
        
        abs_value = abs(value)
        
        if abs_value >= 100000000:  # 亿
            return f"{value / 100000000:.{precision}f}亿"
        elif abs_value >= 10000:  # 万
            return f"{value / 10000:.{precision}f}万"
        else:
            return f"{value:.{precision}f}"

class StockCodeValidator:
    """股票代码验证器"""
    
    @staticmethod
    def validate_chinese_stock_code(stock_code: str) -> bool:
        """验证中国股票代码格式"""
        if not stock_code:
            return False
        
        # 移除空格
        code = stock_code.strip()
        
        # A股主板: 000xxx, 002xxx, 600xxx, 601xxx, 603xxx
        # 科创板: 688xxx
        # 创业板: 300xxx
        patterns = [
            r'^000\d{3}$',  # 深市主板
            r'^002\d{3}$',  # 深市中小板
            r'^300\d{3}$',  # 创业板
            r'^60[0-3]\d{3}$',  # 沪市主板
            r'^688\d{3}$',  # 科创板
        ]
        
        return any(re.match(pattern, code) for pattern in patterns)
    
    @staticmethod
    def get_market_info(stock_code: str) -> Dict[str, str]:
        """获取股票市场信息"""
        if not stock_code:
            return {"market": "unknown", "board": "unknown"}
        
        code = stock_code.strip()
        
        if code.startswith('000'):
            return {"market": "深圳", "board": "主板"}
        elif code.startswith('002'):
            return {"market": "深圳", "board": "中小板"}
        elif code.startswith('300'):
            return {"market": "深圳", "board": "创业板"}
        elif code.startswith('60'):
            return {"market": "上海", "board": "主板"}
        elif code.startswith('688'):
            return {"market": "上海", "board": "科创板"}
        else:
            return {"market": "unknown", "board": "unknown"}

class CacheKeyGenerator:
    """缓存键生成器"""
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix]
        
        # 添加位置参数
        for arg in args:
            key_parts.append(str(arg))
        
        # 添加关键字参数 (排序确保一致性)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def generate_hash_key(data: Any) -> str:
        """生成基于数据内容的哈希键"""
        if isinstance(data, dict):
            # 对字典排序确保一致性
            sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        else:
            sorted_data = str(data)
        
        return hashlib.md5(sorted_data.encode()).hexdigest()

class TimeUtils:
    """时间工具类"""
    
    @staticmethod
    def get_trading_days_between(start_date: datetime, end_date: datetime) -> int:
        """计算两个日期之间的交易日数量"""
        # 简化版本，实际应该排除节假日
        days = (end_date - start_date).days
        trading_days = 0
        
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            # 排除周末
            if date.weekday() < 5:  # 0-6, 0是周一
                trading_days += 1
        
        return trading_days
    
    @staticmethod
    def is_trading_time() -> bool:
        """判断当前是否为交易时间"""
        now = datetime.now()
        
        # 排除周末
        if now.weekday() >= 5:
            return False
        
        # 交易时间: 9:30-11:30, 13:00-15:00
        morning_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        morning_end = now.replace(hour=11, minute=30, second=0, microsecond=0)
        afternoon_start = now.replace(hour=13, minute=0, second=0, microsecond=0)
        afternoon_end = now.replace(hour=15, minute=0, second=0, microsecond=0)
        
        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)
    
    @staticmethod
    def get_next_trading_day() -> datetime:
        """获取下一个交易日"""
        tomorrow = datetime.now() + timedelta(days=1)
        
        # 简化版本：如果是周末，跳到周一
        while tomorrow.weekday() >= 5:
            tomorrow += timedelta(days=1)
        
        return tomorrow.replace(hour=9, minute=30, second=0, microsecond=0)

class RetryDecorator:
    """重试装饰器"""
    
    @staticmethod
    def retry_async(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """异步函数重试装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            wait_time = delay * (backoff ** attempt)
                            logger.warning(f"🔄 重试 {func.__name__} (尝试 {attempt + 1}/{max_attempts}) - 等待 {wait_time:.1f}s")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"❌ {func.__name__} 重试失败 - {last_exception}")
                
                raise last_exception
            return wrapper
        return decorator
    
    @staticmethod
    def retry_sync(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """同步函数重试装饰器"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                import time
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            wait_time = delay * (backoff ** attempt)
                            logger.warning(f"🔄 重试 {func.__name__} (尝试 {attempt + 1}/{max_attempts}) - 等待 {wait_time:.1f}s")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"❌ {func.__name__} 重试失败 - {last_exception}")
                
                raise last_exception
            return wrapper
        return decorator

class PerformanceMonitor:
    """性能监控工具"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"⏱️ {self.name} 执行时间: {duration:.3f}s")

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_required_env_vars(required_vars: List[str]) -> Dict[str, bool]:
        """验证必需的环境变量"""
        import os
        
        results = {}
        for var in required_vars:
            value = os.getenv(var)
            results[var] = bool(value and value.strip())
        
        return results
    
    @staticmethod
    def validate_database_connection(database_url: str) -> bool:
        """验证数据库连接"""
        try:
            from sqlalchemy import create_engine
            engine = create_engine(database_url)
            connection = engine.connect()
            connection.close()
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接验证失败: {e}")
            return False
    
    @staticmethod
    async def validate_redis_connection(redis_url: str) -> bool:
        """验证Redis连接"""
        try:
            import redis.asyncio as redis
            client = redis.from_url(redis_url)
            await client.ping()
            await client.close()
            return True
        except Exception as e:
            logger.error(f"❌ Redis连接验证失败: {e}")
            return False

# 导出常用函数
__all__ = [
    'DataProcessor',
    'StockCodeValidator',
    'CacheKeyGenerator',
    'TimeUtils',
    'RetryDecorator',
    'PerformanceMonitor',
    'ConfigValidator'
]
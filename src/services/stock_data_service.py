#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据服务 - 连接现有stock_services API
Stock Data Service - Connect to Existing stock_services API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta
from loguru import logger
from ..core.config import settings
from ..core.database import cache_manager

class StockDataService:
    """股票数据服务类"""
    
    def __init__(self):
        self.base_url = settings.STOCK_API_BASE_URL
        self.timeout = settings.STOCK_API_TIMEOUT
        self.retry_times = settings.STOCK_API_RETRY_TIMES
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, endpoint: str, stock_code: str, cache_key: str = None) -> Dict[str, Any]:
        """
        发起HTTP请求，支持缓存和重试
        """
        # 检查缓存
        if cache_key:
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"📦 从缓存获取数据: {cache_key}")
                return json.loads(cached_data)
        
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        # 重试机制
        for attempt in range(self.retry_times):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 缓存成功的响应
                        if cache_key and data:
                            await cache_manager.set(
                                cache_key, 
                                json.dumps(data, ensure_ascii=False),
                                settings.CACHE_TTL_STOCK_DATA
                            )
                        
                        logger.debug(f"✅ 成功获取数据: {url}")
                        return data
                    else:
                        logger.warning(f"⚠️ HTTP {response.status}: {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ 请求超时 (尝试 {attempt + 1}/{self.retry_times}): {url}")
            except Exception as e:
                logger.error(f"❌ 请求异常 (尝试 {attempt + 1}/{self.retry_times}): {url} - {e}")
            
            if attempt < self.retry_times - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"❌ 所有重试失败: {url}")
        return {}
    
    async def get_fundamental_data(self, stock_code: str) -> Dict[str, Any]:
        """获取基本面分析数据"""
        cache_key = cache_manager.generate_cache_key("fundamental", stock_code)
        endpoint = f"/stocks/{stock_code}/analysis/fundamental"
        
        data = await self._make_request(endpoint, stock_code, cache_key)
        
        if data:
            # 数据处理和标准化
            processed_data = {
                "source": "fundamental_analysis",
                "stock_code": stock_code,
                "stock_name": data.get("stock_name", ""),
                "current_price": data.get("basic_info", {}).get("最新", 0),
                "market_cap": data.get("basic_info", {}).get("总市值", 0),
                "pe_ratio": data.get("basic_info", {}).get("市盈率", 0),
                "industry": data.get("basic_info", {}).get("行业", ""),
                "raw_data": data,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"📊 基本面数据获取成功: {stock_code}")
            return processed_data
        
        return {}
    
    async def get_technical_data(self, stock_code: str) -> Dict[str, Any]:
        """获取技术面分析数据"""
        cache_key = cache_manager.generate_cache_key("technical", stock_code)
        endpoint = f"/stocks/{stock_code}/analysis/technical"
        
        data = await self._make_request(endpoint, stock_code, cache_key)
        
        if data:
            processed_data = {
                "source": "technical_analysis",
                "stock_code": stock_code,
                "analysis_type": data.get("analysis_type", ""),
                "indicators": data.get("technical_indicators", {}),
                "signals": data.get("trading_signals", []),
                "trend": data.get("trend_analysis", ""),
                "raw_data": data,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"📈 技术面数据获取成功: {stock_code}")
            return processed_data
        
        return {}
    
    async def get_financial_data(self, stock_code: str) -> Dict[str, Any]:
        """获取财务数据"""
        cache_key = cache_manager.generate_cache_key("financial", stock_code)
        endpoint = f"/api/financial-abstract/{stock_code}"
        
        data = await self._make_request(endpoint, stock_code, cache_key)
        
        if data:
            processed_data = {
                "source": "financial_data",
                "stock_code": stock_code,
                "financial_indicators": data.get("financial_indicators", []),
                "revenue_data": data.get("revenue_data", {}),
                "profit_data": data.get("profit_data", {}),
                "balance_sheet": data.get("balance_sheet", {}),
                "raw_data": data,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"💰 财务数据获取成功: {stock_code}")
            return processed_data
        
        return {}
    
    async def get_market_sentiment(self, stock_code: str) -> Dict[str, Any]:
        """获取市场情绪数据 (模拟数据，实际可连接更多数据源)"""
        # 这里可以连接更多的市场情绪API
        sentiment_data = {
            "source": "market_sentiment",
            "stock_code": stock_code,
            "sentiment_score": 0.65,  # 示例数据
            "news_sentiment": "positive",
            "social_media_sentiment": "neutral",
            "analyst_ratings": {
                "buy": 3,
                "hold": 2,
                "sell": 1
            },
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info(f"📰 市场情绪数据生成: {stock_code}")
        return sentiment_data
    
    async def get_all_stock_data(self, stock_code: str) -> Dict[str, Any]:
        """并行获取所有股票数据"""
        tasks = [
            self.get_fundamental_data(stock_code),
            self.get_technical_data(stock_code),
            self.get_financial_data(stock_code),
            self.get_market_sentiment(stock_code)
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_data = {
                "stock_code": stock_code,
                "data_types": [],
                "collected_at": datetime.now().isoformat()
            }
            
            data_types = ["fundamental", "technical", "financial", "sentiment"]
            for i, result in enumerate(results):
                if not isinstance(result, Exception) and result:
                    all_data[data_types[i]] = result
                    all_data["data_types"].append(data_types[i])
            
            logger.info(f"📊 完整数据收集完成: {stock_code} - {len(all_data['data_types'])} 种类型")
            return all_data
            
        except Exception as e:
            logger.error(f"❌ 数据收集失败: {stock_code} - {e}")
            return {"stock_code": stock_code, "error": str(e)}
        finally:
            await self.close()

# 数据验证和清洗工具
class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_stock_data(data: Dict[str, Any]) -> bool:
        """验证股票数据的完整性"""
        required_fields = ["stock_code", "updated_at"]
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"⚠️ 缺少必要字段: {field}")
                return False
        
        return True
    
    @staticmethod
    def clean_financial_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗财务数据"""
        # 移除空值和异常值
        cleaned_data = {}
        
        for key, value in data.items():
            if value is not None and value != "":
                if isinstance(value, (int, float)) and value < 0:
                    # 处理负值
                    pass
                cleaned_data[key] = value
        
        return cleaned_data
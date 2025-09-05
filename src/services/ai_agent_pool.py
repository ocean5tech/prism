#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent连接池管理器
AI Agent Pool Manager
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from loguru import logger
from ..core.config import settings
from ..core.database import cache_manager
import random

class AIAgent:
    """AI代理类"""
    
    def __init__(self, agent_id: str, endpoint: str, api_key: str = None):
        self.agent_id = agent_id
        self.endpoint = endpoint
        self.api_key = api_key
        self.is_busy = False
        self.last_used = None
        self.request_count = 0
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self):
        """获取HTTP会话"""
        if not self.session:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            timeout = aiohttp.ClientTimeout(total=settings.AI_AGENT_TIMEOUT)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session
    
    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def analyze_stock(self, stock_data: Dict[str, Any], style: str) -> Dict[str, Any]:
        """分析股票数据"""
        if self.is_busy:
            raise Exception(f"Agent {self.agent_id} is busy")
        
        self.is_busy = True
        self.last_used = datetime.now()
        
        try:
            # 构造分析请求
            analysis_request = {
                "stock_data": stock_data,
                "analysis_style": style,
                "request_id": f"{self.agent_id}_{int(datetime.now().timestamp())}",
                "requirements": {
                    "language": "chinese",
                    "format": "detailed_analysis",
                    "include_recommendations": True,
                    "confidence_scoring": True
                }
            }
            
            session = await self._get_session()
            
            async with session.post(
                f"{self.endpoint}/analyze",
                json=analysis_request
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.request_count += 1
                    
                    # 标准化返回格式
                    standardized_result = {
                        "agent_id": self.agent_id,
                        "style": style,
                        "title": result.get("title", f"{style}风格股票分析"),
                        "content": result.get("analysis", ""),
                        "summary": result.get("summary", ""),
                        "recommendations": result.get("recommendations", []),
                        "confidence_score": result.get("confidence", 0.8),
                        "risk_assessment": result.get("risk_level", "medium"),
                        "generated_at": datetime.now().isoformat(),
                        "processing_time": result.get("processing_time", 0)
                    }
                    
                    logger.info(f"✅ AI分析完成: {self.agent_id} - {style}")
                    return standardized_result
                else:
                    raise Exception(f"AI Agent响应错误: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ AI Agent分析失败: {self.agent_id} - {e}")
            # 返回模拟数据以保证系统稳定性
            return await self._generate_fallback_analysis(stock_data, style)
        finally:
            self.is_busy = False
    
    async def _generate_fallback_analysis(self, stock_data: Dict[str, Any], style: str) -> Dict[str, Any]:
        """生成降级分析 (模拟数据)"""
        stock_code = stock_data.get("stock_code", "UNKNOWN")
        
        # 不同风格的模板
        style_templates = {
            "professional": {
                "title": f"{stock_code} 专业分析报告",
                "content": f"基于{stock_code}的最新数据，从技术面和基本面角度进行专业分析...",
                "tone": "客观、专业"
            },
            "dark": {
                "title": f"{stock_code} 风险警示分析",
                "content": f"对{stock_code}当前走势持谨慎态度，存在多项风险因素...",
                "tone": "谨慎、警惕"
            },
            "optimistic": {
                "title": f"{stock_code} 投资机会分析",
                "content": f"{stock_code}展现出良好的增长潜力，多项指标向好...",
                "tone": "积极、乐观"
            },
            "conservative": {
                "title": f"{stock_code} 稳健投资评估",
                "content": f"{stock_code}适合稳健投资者，风险可控收益稳定...",
                "tone": "稳重、保守"
            }
        }
        
        template = style_templates.get(style, style_templates["professional"])
        
        return {
            "agent_id": f"fallback_{self.agent_id}",
            "style": style,
            "title": template["title"],
            "content": template["content"],
            "summary": f"这是一份{template['tone']}的{style}风格分析报告",
            "recommendations": ["建议关注基本面变化", "注意技术指标信号", "控制仓位风险"],
            "confidence_score": 0.6,  # 降级数据置信度较低
            "risk_assessment": "medium",
            "generated_at": datetime.now().isoformat(),
            "processing_time": 0.1,
            "is_fallback": True
        }

class AIAgentPool:
    """AI Agent连接池"""
    
    def __init__(self):
        self.agents: List[AIAgent] = []
        self.max_agents = settings.AI_AGENT_MAX_WORKERS
        self.pool_size = settings.AI_AGENT_POOL_SIZE
        self.initialized = False
    
    async def initialize(self):
        """初始化Agent池"""
        if self.initialized:
            return
        
        # 创建多个AI Agent实例 (这里使用模拟端点)
        agent_configs = [
            {"id": "agent_1", "endpoint": "http://ai-service-1:8000", "api_key": None},
            {"id": "agent_2", "endpoint": "http://ai-service-2:8000", "api_key": None},
            {"id": "agent_3", "endpoint": "http://ai-service-3:8000", "api_key": None},
            {"id": "agent_4", "endpoint": "http://ai-service-4:8000", "api_key": None},
            {"id": "agent_5", "endpoint": "http://ai-service-5:8000", "api_key": None},
        ]
        
        for config in agent_configs[:self.pool_size]:
            agent = AIAgent(
                agent_id=config["id"],
                endpoint=config["endpoint"],
                api_key=config["api_key"]
            )
            self.agents.append(agent)
        
        self.initialized = True
        logger.info(f"🤖 AI Agent池初始化完成: {len(self.agents)} 个agents")
    
    async def get_available_agent(self) -> Optional[AIAgent]:
        """获取可用的Agent"""
        await self.initialize()
        
        # 寻找空闲的Agent
        for agent in self.agents:
            if not agent.is_busy:
                return agent
        
        # 如果所有Agent都忙，返回使用最少的那个
        return min(self.agents, key=lambda a: a.request_count)
    
    async def analyze_stock_data(self, stock_data: Dict[str, Any], style: str) -> Dict[str, Any]:
        """使用Agent分析股票数据"""
        # 检查缓存
        cache_key = cache_manager.generate_cache_key("ai_analysis", stock_data.get("stock_code", ""), style)
        cached_result = await cache_manager.get(cache_key)
        
        if cached_result:
            logger.debug(f"📦 从缓存获取AI分析: {style}")
            return json.loads(cached_result)
        
        agent = await self.get_available_agent()
        if not agent:
            raise Exception("没有可用的AI Agent")
        
        result = await agent.analyze_stock(stock_data, style)
        
        # 缓存结果
        if result and not result.get("is_fallback", False):
            await cache_manager.set(
                cache_key,
                json.dumps(result, ensure_ascii=False),
                settings.CACHE_TTL_AI_RESPONSE
            )
        
        return result
    
    async def analyze_parallel(self, stock_data: Dict[str, Any], styles: List[str]) -> List[Dict[str, Any]]:
        """并行分析多种风格"""
        await self.initialize()
        
        tasks = []
        for style in styles:
            task = self.analyze_stock_data(stock_data, style)
            tasks.append(task)
        
        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ 并行分析失败 ({styles[i]}): {result}")
            else:
                successful_results.append(result)
        
        logger.info(f"🤖 并行AI分析完成: {len(successful_results)}/{len(styles)}")
        return successful_results
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        await self.initialize()
        
        busy_count = sum(1 for agent in self.agents if agent.is_busy)
        total_requests = sum(agent.request_count for agent in self.agents)
        
        return {
            "total_agents": len(self.agents),
            "busy_agents": busy_count,
            "available_agents": len(self.agents) - busy_count,
            "total_requests": total_requests,
            "average_requests_per_agent": total_requests / len(self.agents) if self.agents else 0,
            "pool_utilization": (busy_count / len(self.agents)) * 100 if self.agents else 0
        }
    
    async def close_all(self):
        """关闭所有Agent连接"""
        for agent in self.agents:
            await agent.close()
        
        logger.info("🔚 AI Agent池已关闭")

# 全局AI Agent池实例
ai_agent_pool = AIAgentPool()
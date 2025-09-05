#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章生成器 - 核心工作流处理器
Article Generator - Core Workflow Processor
"""

from celery import Task
from typing import Dict, List, Any
import asyncio
import aiohttp
import json
from datetime import datetime
from loguru import logger
from ..core.task_scheduler import celery_app
from ..core.config import settings
from ..core.database import db_manager, cache_manager
from ..services.stock_data_service import StockDataService
from ..services.ai_agent_pool import AIAgentPool

class ArticleGenerationTask(Task):
    """文章生成任务基类"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"❌ 任务失败 {task_id}: {exc}")
        
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        logger.info(f"✅ 任务成功完成 {task_id}")

@celery_app.task(bind=True, base=ArticleGenerationTask, name="prism.workers.article_generator.generate_articles_workflow")
def generate_articles_workflow(self, stock_code: str, options: Dict[str, Any]):
    """
    文章生成工作流 - 这是替代n8n的核心业务逻辑
    """
    task_id = self.request.id
    
    try:
        # 更新任务状态为进行中
        asyncio.run(db_manager.update_task_status(task_id, "running"))
        
        # 设置进度回调
        self.update_state(state="PROGRESS", meta={"step": "初始化", "progress": 10})
        
        # 1. 初始化服务
        stock_service = StockDataService()
        ai_agent_pool = AIAgentPool()
        
        # 2. 并行获取股票数据
        self.update_state(state="PROGRESS", meta={"step": "获取股票数据", "progress": 20})
        
        stock_data = asyncio.run(collect_stock_data(stock_service, stock_code))
        
        if not stock_data:
            raise Exception(f"无法获取股票 {stock_code} 的数据")
        
        # 3. 并行调用AI Agent生成分析
        self.update_state(state="PROGRESS", meta={"step": "AI分析处理", "progress": 40})
        
        ai_analyses = asyncio.run(process_ai_analysis(ai_agent_pool, stock_data, options))
        
        # 4. 生成多篇文章
        self.update_state(state="PROGRESS", meta={"step": "生成文章", "progress": 70})
        
        articles = asyncio.run(generate_multiple_articles(ai_analyses, stock_data, options))
        
        # 5. 结果聚合和格式化
        self.update_state(state="PROGRESS", meta={"step": "结果处理", "progress": 90})
        
        result = {
            "task_id": task_id,
            "stock_code": stock_code,
            "articles": articles,
            "metadata": {
                "total_articles": len(articles),
                "processing_time": datetime.now().isoformat(),
                "data_sources": list(stock_data.keys()) if stock_data else [],
                "ai_models_used": len(ai_analyses)
            },
            "status": "completed"
        }
        
        # 保存结果到数据库
        asyncio.run(db_manager.update_task_status(task_id, "completed", result))
        
        self.update_state(state="SUCCESS", meta={"step": "完成", "progress": 100})
        
        logger.info(f"🎉 文章生成工作流完成: {task_id}")
        return result
        
    except Exception as e:
        # 错误处理
        error_msg = f"文章生成失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        asyncio.run(db_manager.update_task_status(task_id, "failed", {"error": error_msg}))
        
        raise self.retry(exc=e, countdown=60, max_retries=3)

async def collect_stock_data(stock_service: StockDataService, stock_code: str) -> Dict[str, Any]:
    """
    并行收集股票数据 - 替代n8n中的多个HTTP节点
    """
    tasks = [
        stock_service.get_fundamental_data(stock_code),
        stock_service.get_technical_data(stock_code),
        stock_service.get_financial_data(stock_code),
        stock_service.get_market_sentiment(stock_code)
    ]
    
    try:
        # 并行执行所有数据获取任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        stock_data = {}
        data_types = ["fundamental", "technical", "financial", "sentiment"]
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                stock_data[data_types[i]] = result
            else:
                logger.warning(f"⚠️ 获取{data_types[i]}数据失败: {result}")
        
        logger.info(f"📊 收集到 {len(stock_data)} 种类型的股票数据")
        return stock_data
        
    except Exception as e:
        logger.error(f"❌ 股票数据收集失败: {e}")
        return {}

async def process_ai_analysis(ai_pool: AIAgentPool, stock_data: Dict[str, Any], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    并行处理AI分析 - 替代n8n中的AI节点调用
    """
    analysis_tasks = []
    
    # 为每种文章风格创建AI分析任务
    for style in options.get("article_styles", settings.ARTICLE_STYLES):
        task = ai_pool.analyze_stock_data(stock_data, style)
        analysis_tasks.append(task)
    
    # 并行执行AI分析
    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
    
    successful_analyses = []
    for i, result in enumerate(results):
        if not isinstance(result, Exception):
            successful_analyses.append(result)
        else:
            logger.warning(f"⚠️ AI分析失败 (风格{i}): {result}")
    
    logger.info(f"🤖 完成 {len(successful_analyses)} 个AI分析")
    return successful_analyses

async def generate_multiple_articles(ai_analyses: List[Dict[str, Any]], stock_data: Dict[str, Any], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    生成多篇文章 - 替代n8n中的文章生成和格式化节点
    """
    articles = []
    
    for i, analysis in enumerate(ai_analyses):
        try:
            article = {
                "id": f"article_{i+1}",
                "style": analysis.get("style", "professional"),
                "title": analysis.get("title", f"股票分析报告 #{i+1}"),
                "content": analysis.get("content", ""),
                "summary": analysis.get("summary", ""),
                "recommendations": analysis.get("recommendations", []),
                "confidence_score": analysis.get("confidence_score", 0.0),
                "data_sources": list(stock_data.keys()),
                "generated_at": datetime.now().isoformat(),
                "word_count": len(analysis.get("content", ""))
            }
            
            articles.append(article)
            
        except Exception as e:
            logger.error(f"❌ 文章生成失败 (第{i+1}篇): {e}")
            continue
    
    logger.info(f"📝 生成了 {len(articles)} 篇文章")
    return articles

# 任务清理和维护
@celery_app.task(name="prism.workers.article_generator.cleanup_old_tasks")
def cleanup_old_tasks():
    """清理旧任务记录"""
    try:
        # 这里添加清理逻辑
        logger.info("🧹 执行任务清理")
        return {"status": "completed", "cleaned_tasks": 0}
    except Exception as e:
        logger.error(f"❌ 任务清理失败: {e}")
        return {"status": "failed", "error": str(e)}
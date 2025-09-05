#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prism系统FastAPI应用程序
Prism System FastAPI Application
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import uvicorn
from loguru import logger

from ..core.config import settings, validate_environment
from ..core.database import init_database, db_manager, cache_manager
from ..core.task_scheduler import task_scheduler, task_monitor
from ..services.stock_data_service import StockDataService
from ..services.ai_agent_pool import ai_agent_pool

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="高性能股票分析文章生成系统 - 替代n8n工作流",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class ArticleRequest(BaseModel):
    stock_code: str
    article_styles: Optional[List[str]] = None
    use_cache: bool = True
    parallel_processing: bool = True

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ArticleResponse(BaseModel):
    task_id: str
    stock_code: str
    articles: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    status: str

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    try:
        # 验证环境配置
        validate_environment()
        logger.info("✅ 环境配置验证通过")
        
        # 初始化数据库
        init_database()
        logger.info("✅ 数据库初始化完成")
        
        # 初始化AI Agent池
        await ai_agent_pool.initialize()
        logger.info("✅ AI Agent池初始化完成")
        
        logger.info(f"🚀 Prism系统启动完成 - 监听端口: {settings.PORT}")
        
    except Exception as e:
        logger.error(f"❌ 系统启动失败: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    try:
        await ai_agent_pool.close_all()
        logger.info("🔚 系统关闭完成")
    except Exception as e:
        logger.error(f"❌ 系统关闭错误: {e}")

# 健康检查
@app.get("/health", tags=["系统监控"])
async def health_check():
    """系统健康检查"""
    try:
        # 检查Redis连接
        await cache_manager.redis.ping()
        
        # 检查AI Agent池状态
        pool_stats = await ai_agent_pool.get_pool_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.VERSION,
            "services": {
                "redis": "connected",
                "database": "connected",
                "ai_agents": f"{pool_stats['available_agents']}/{pool_stats['total_agents']} available"
            }
        }
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")

# 核心API端点 - 文章生成
@app.post("/api/generate-articles", response_model=TaskResponse, tags=["文章生成"])
async def generate_articles(request: ArticleRequest):
    """
    生成股票分析文章 - 核心API
    这是替代n8n工作流的主要入口点
    """
    try:
        # 验证股票代码
        if not request.stock_code or len(request.stock_code) < 4:
            raise HTTPException(status_code=400, detail="股票代码格式错误")
        
        # 准备任务选项
        options = {
            "article_styles": request.article_styles or settings.ARTICLE_STYLES[:settings.DEFAULT_ARTICLE_COUNT],
            "use_cache": request.use_cache,
            "parallel_processing": request.parallel_processing
        }
        
        # 创建任务
        task_id = await task_scheduler.create_article_generation_task(
            stock_code=request.stock_code,
            options=options
        )
        
        logger.info(f"✅ 文章生成任务已创建: {task_id}")
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"股票 {request.stock_code} 的文章生成任务已启动"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建文章生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

# 任务状态查询
@app.get("/api/tasks/{task_id}", tags=["任务管理"])
async def get_task_status(task_id: str):
    """获取任务执行状态"""
    try:
        task_status = await task_scheduler.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

# 取消任务
@app.delete("/api/tasks/{task_id}", tags=["任务管理"])
async def cancel_task(task_id: str):
    """取消正在执行的任务"""
    try:
        success = await task_scheduler.cancel_task(task_id)
        
        if success:
            return {"message": f"任务 {task_id} 已取消"}
        else:
            raise HTTPException(status_code=400, detail="任务取消失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消失败: {str(e)}")

# 股票数据获取
@app.get("/api/stocks/{stock_code}/data", tags=["股票数据"])
async def get_stock_data(stock_code: str, data_type: Optional[str] = None):
    """获取股票数据 (支持缓存)"""
    try:
        stock_service = StockDataService()
        
        if data_type:
            # 获取特定类型的数据
            if data_type == "fundamental":
                data = await stock_service.get_fundamental_data(stock_code)
            elif data_type == "technical":
                data = await stock_service.get_technical_data(stock_code)
            elif data_type == "financial":
                data = await stock_service.get_financial_data(stock_code)
            elif data_type == "sentiment":
                data = await stock_service.get_market_sentiment(stock_code)
            else:
                raise HTTPException(status_code=400, detail="不支持的数据类型")
        else:
            # 获取所有数据
            data = await stock_service.get_all_stock_data(stock_code)
        
        if not data:
            raise HTTPException(status_code=404, detail="股票数据未找到")
        
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取股票数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据获取失败: {str(e)}")

# AI分析端点
@app.post("/api/ai/analyze", tags=["AI分析"])
async def ai_analyze_stock(
    stock_code: str,
    analysis_style: str = "professional",
    use_cache: bool = True
):
    """使用AI分析股票数据"""
    try:
        # 获取股票数据
        stock_service = StockDataService()
        stock_data = await stock_service.get_all_stock_data(stock_code)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail="无法获取股票数据")
        
        # AI分析
        analysis_result = await ai_agent_pool.analyze_stock_data(stock_data, analysis_style)
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

# 系统统计信息
@app.get("/api/system/stats", tags=["系统监控"])
async def get_system_stats():
    """获取系统运行统计信息"""
    try:
        # 任务统计
        task_stats = await task_monitor.get_system_stats()
        
        # AI Agent池统计
        ai_pool_stats = await ai_agent_pool.get_pool_stats()
        
        # 运行中的任务
        running_tasks = await task_scheduler.get_running_tasks()
        
        return {
            "system": {
                "uptime": datetime.now().isoformat(),
                "version": settings.VERSION
            },
            "tasks": task_stats,
            "ai_agents": ai_pool_stats,
            "running_tasks": len(running_tasks),
            "performance": await task_monitor.get_performance_metrics()
        }
        
    except Exception as e:
        logger.error(f"❌ 获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"统计获取失败: {str(e)}")

# 批量处理端点
@app.post("/api/batch/generate-articles", tags=["批量处理"])
async def batch_generate_articles(stock_codes: List[str], article_styles: Optional[List[str]] = None):
    """批量生成多只股票的分析文章"""
    try:
        if len(stock_codes) > 10:
            raise HTTPException(status_code=400, detail="批量处理最多支持10只股票")
        
        task_ids = []
        options = {
            "article_styles": article_styles or settings.ARTICLE_STYLES[:settings.DEFAULT_ARTICLE_COUNT],
            "use_cache": True,
            "parallel_processing": True
        }
        
        # 为每只股票创建任务
        for stock_code in stock_codes:
            task_id = await task_scheduler.create_article_generation_task(stock_code, options)
            task_ids.append({
                "stock_code": stock_code,
                "task_id": task_id
            })
        
        logger.info(f"✅ 批量任务创建完成: {len(task_ids)} 个任务")
        
        return {
            "message": f"已创建 {len(task_ids)} 个文章生成任务",
            "tasks": task_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量任务创建失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")

# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"❌ 未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误"}
    )

if __name__ == "__main__":
    # 开发环境直接运行
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
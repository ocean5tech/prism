#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度器 - 替代n8n的核心组件
Task Scheduler - Core Component to Replace n8n
"""

from celery import Celery
from celery.result import AsyncResult
from typing import Dict, List, Any, Optional
import uuid
import json
from datetime import datetime, timedelta
import asyncio
from .config import settings
from .database import db_manager, cache_manager
from loguru import logger

# 创建Celery应用
celery_app = Celery(
    "prism_scheduler",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 配置Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.TASK_TIMEOUT,
    task_soft_time_limit=settings.TASK_TIMEOUT - 30,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100
)

class TaskScheduler:
    """任务调度器类"""
    
    def __init__(self):
        self.celery = celery_app
        
    async def create_article_generation_task(self, stock_code: str, options: Dict[str, Any] = None) -> str:
        """
        创建文章生成任务
        这是替代n8n workflow的核心方法
        """
        task_id = str(uuid.uuid4())
        
        # 默认选项
        default_options = {
            "article_styles": settings.ARTICLE_STYLES[:settings.DEFAULT_ARTICLE_COUNT],
            "parallel_processing": True,
            "use_cache": True,
            "timeout": settings.TASK_TIMEOUT
        }
        
        if options:
            default_options.update(options)
            
        # 保存任务记录到数据库
        task_record = {
            "task_id": task_id,
            "stock_code": stock_code,
            "task_type": "article_generation",
            "status": "pending",
            "input_data": {
                "stock_code": stock_code,
                "options": default_options,
                "created_at": datetime.now().isoformat()
            }
        }
        
        await db_manager.save_task_record(task_record)
        
        # 提交任务到Celery
        result = self.celery.send_task(
            "prism.workers.article_generator.generate_articles_workflow",
            args=[stock_code, default_options],
            task_id=task_id,
            countdown=0  # 立即执行
        )
        
        logger.info(f"✅ 创建文章生成任务: {task_id} for stock: {stock_code}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        # 从Celery获取任务状态
        result = AsyncResult(task_id, app=self.celery)
        
        status_info = {
            "task_id": task_id,
            "status": result.status,
            "progress": None,
            "result": None,
            "error": None,
            "created_at": None,
            "completed_at": None
        }
        
        if result.ready():
            if result.successful():
                status_info["result"] = result.result
            else:
                status_info["error"] = str(result.info)
        elif result.status == "PROGRESS":
            status_info["progress"] = result.info
            
        return status_info
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        self.celery.control.revoke(task_id, terminate=True)
        await db_manager.update_task_status(task_id, "cancelled")
        logger.warning(f"🚫 任务已取消: {task_id}")
        return True
    
    async def get_running_tasks(self) -> List[Dict[str, Any]]:
        """获取运行中的任务列表"""
        inspect = self.celery.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return []
        
        running_tasks = []
        for worker, tasks in active_tasks.items():
            for task in tasks:
                running_tasks.append({
                    "task_id": task["id"],
                    "name": task["name"],
                    "args": task["args"],
                    "kwargs": task["kwargs"],
                    "worker": worker,
                    "time_start": task.get("time_start")
                })
        
        return running_tasks
    
    async def retry_failed_task(self, task_id: str) -> str:
        """重试失败的任务"""
        # 获取原任务信息
        result = AsyncResult(task_id, app=self.celery)
        
        if not result.failed():
            raise ValueError(f"任务 {task_id} 未失败，无需重试")
        
        # 创建新的任务ID
        new_task_id = str(uuid.uuid4())
        
        # 重新提交任务（这里需要根据实际情况获取原始参数）
        # 这是一个简化版本，实际应用中需要从数据库获取原始参数
        logger.info(f"🔄 重试任务: {task_id} -> {new_task_id}")
        
        return new_task_id

# 任务监控和统计
class TaskMonitor:
    """任务监控器"""
    
    def __init__(self, scheduler: TaskScheduler):
        self.scheduler = scheduler
        
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        inspect = self.scheduler.celery.control.inspect()
        
        stats = {
            "active_tasks": len(await self.scheduler.get_running_tasks()),
            "registered_tasks": list(inspect.registered().keys()) if inspect.registered() else [],
            "worker_stats": inspect.stats() or {},
            "queue_length": 0,  # 需要从Redis获取
            "failed_tasks_24h": 0,  # 需要从数据库统计
            "completed_tasks_24h": 0,  # 需要从数据库统计
            "avg_task_duration": 0,  # 需要从数据库计算
        }
        
        return stats
    
    async def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标"""
        # 这里可以添加更详细的性能监控逻辑
        return {
            "tasks_per_minute": 0.0,
            "avg_response_time": 0.0,
            "success_rate": 0.0,
            "error_rate": 0.0
        }

# 全局实例
task_scheduler = TaskScheduler()
task_monitor = TaskMonitor(task_scheduler)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prism系统主入口程序
Prism System Main Entry Point
"""

import sys
import asyncio
import signal
import argparse
from pathlib import Path
from loguru import logger
import uvicorn

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.core.config import settings, validate_environment
from src.core.database import init_database, db_manager, cache_manager
from src.core.task_scheduler import celery_app, task_scheduler
from src.services.ai_agent_pool import ai_agent_pool

def setup_logging():
    """配置日志系统"""
    logger.remove()  # 移除默认处理器
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format=settings.LOG_FORMAT,
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # 添加文件输出
    logger.add(
        "logs/prism.log",
        format=settings.LOG_FORMAT,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip"
    )
    
    logger.info(f"📝 日志系统初始化完成 - Level: {settings.LOG_LEVEL}")

def create_directories():
    """创建必要的目录"""
    directories = ["logs", "data", "cache"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.debug(f"📁 确保目录存在: {directory}")

async def initialize_system():
    """初始化系统组件"""
    try:
        logger.info("🚀 开始初始化Prism系统...")
        
        # 验证环境配置
        validate_environment()
        logger.info("✅ 环境配置验证通过")
        
        # 创建必要目录
        create_directories()
        
        # 初始化数据库
        init_database()
        logger.info("✅ 数据库初始化完成")
        
        # 初始化AI Agent池
        await ai_agent_pool.initialize()
        logger.info("✅ AI Agent池初始化完成")
        
        logger.info("🎉 Prism系统初始化完成!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {e}")
        return False

async def cleanup_system():
    """清理系统资源"""
    try:
        logger.info("🧹 开始清理系统资源...")
        
        # 关闭AI Agent池
        await ai_agent_pool.close_all()
        logger.info("✅ AI Agent池已关闭")
        
        # 关闭数据库连接
        # db_manager可以在这里添加关闭方法
        
        logger.info("✅ 系统资源清理完成")
        
    except Exception as e:
        logger.error(f"❌ 系统清理失败: {e}")

def signal_handler(signum, frame):
    """信号处理器"""
    logger.warning(f"🛑 收到信号 {signum}, 开始优雅关闭...")
    asyncio.create_task(cleanup_system())
    sys.exit(0)

def run_web_server():
    """启动Web服务器"""
    logger.info(f"🌐 启动Web服务器 - {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True,
        workers=1 if settings.DEBUG else 4
    )

def run_celery_worker():
    """启动Celery工作进程"""
    logger.info("🔄 启动Celery工作进程...")
    
    # 使用subprocess启动celery worker
    import subprocess
    cmd = [
        "celery", "-A", "src.core.task_scheduler.celery_app",
        "worker", 
        "--loglevel=info",
        f"--concurrency={settings.MAX_CONCURRENT_TASKS}",
        "--pool=prefork"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("🛑 Celery工作进程已停止")

def run_flower_monitor():
    """启动Flower监控界面"""
    logger.info("🌸 启动Flower监控界面...")
    
    import subprocess
    cmd = [
        "celery", "-A", "src.core.task_scheduler.celery_app",
        "flower",
        "--port=5555",
        "--basic_auth=admin:admin123"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("🛑 Flower监控已停止")

async def run_development_mode():
    """开发模式 - 启动所有组件"""
    logger.info("🔧 开发模式启动...")
    
    # 初始化系统
    if not await initialize_system():
        sys.exit(1)
    
    # 在开发模式下，可以选择启动不同的组件
    logger.info("💡 开发模式提示:")
    logger.info("  - Web服务器: python main.py --server")
    logger.info("  - Celery工作进程: python main.py --worker")
    logger.info("  - Flower监控: python main.py --flower")
    
    # 默认启动Web服务器
    run_web_server()

def main():
    """主函数"""
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Prism股票分析系统")
    parser.add_argument("--server", action="store_true", help="启动Web服务器")
    parser.add_argument("--worker", action="store_true", help="启动Celery工作进程")
    parser.add_argument("--flower", action="store_true", help="启动Flower监控")
    parser.add_argument("--dev", action="store_true", help="开发模式")
    parser.add_argument("--init-db", action="store_true", help="仅初始化数据库")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    logger.info("="*60)
    logger.info("🎯 Prism - 高性能股票分析文章生成系统")
    logger.info(f"📊 版本: {settings.VERSION}")
    logger.info(f"🏢 服务器: {settings.SERVER_IP}:{settings.PORT}")
    logger.info("="*60)
    
    try:
        if args.init_db:
            # 仅初始化数据库
            init_database()
            logger.info("✅ 数据库初始化完成")
            
        elif args.server:
            # 启动Web服务器
            asyncio.run(initialize_system())
            run_web_server()
            
        elif args.worker:
            # 启动Celery工作进程
            run_celery_worker()
            
        elif args.flower:
            # 启动Flower监控
            run_flower_monitor()
            
        elif args.dev:
            # 开发模式
            asyncio.run(run_development_mode())
            
        else:
            # 默认启动Web服务器
            asyncio.run(initialize_system())
            run_web_server()
            
    except KeyboardInterrupt:
        logger.info("👋 程序已被用户中断")
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        sys.exit(1)
    finally:
        logger.info("🔚 程序退出")

if __name__ == "__main__":
    main()
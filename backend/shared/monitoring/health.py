"""
Health monitoring and metrics collection
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import psutil
import asyncio
import time
from ..database import DatabaseManager, CacheManager
from ..logging import ServiceLogger
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Prometheus Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_database_connections', 'Active database connections')
QUEUE_SIZE = Gauge('task_queue_size', 'Task queue size', ['queue_name'])
AI_API_CALLS = Counter('ai_api_calls_total', 'Total AI API calls', ['provider', 'model'])
AI_API_COST = Counter('ai_api_cost_total', 'Total AI API cost in USD', ['provider'])

class HealthStatus(BaseModel):
    """Health check response model"""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    service_name: str
    version: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]]

class ServiceCheck(BaseModel):
    """Individual service check result"""
    name: str
    status: str
    response_time_ms: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MetricsResponse(BaseModel):
    """System metrics response"""
    timestamp: datetime
    service_name: str
    system: Dict[str, Any]
    database: Dict[str, Any]
    cache: Dict[str, Any]
    custom_metrics: Dict[str, Any]

class HealthMonitor:
    """Health monitoring service"""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.start_time = time.time()
        self.logger = ServiceLogger(f"{service_name}-health")
        self.checks = {}
    
    def register_check(self, name: str, check_function):
        """Register a custom health check"""
        self.checks[name] = check_function
    
    async def run_check(self, name: str, check_function) -> ServiceCheck:
        """Run individual health check"""
        start_time = time.time()
        try:
            result = await check_function()
            response_time = (time.time() - start_time) * 1000
            
            return ServiceCheck(
                name=name,
                status="healthy" if result.get("healthy", True) else "unhealthy",
                response_time_ms=round(response_time, 2),
                details=result.get("details"),
                error=result.get("error")
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.logger.error(f"Health check failed: {name}", error=str(e))
            
            return ServiceCheck(
                name=name,
                status="unhealthy",
                response_time_ms=round(response_time, 2),
                error=str(e)
            )
    
    async def database_check(self) -> Dict[str, Any]:
        """Check database connectivity"""
        healthy = await DatabaseManager.health_check()
        return {
            "healthy": healthy,
            "details": {"connection": "ok" if healthy else "failed"}
        }
    
    async def cache_check(self) -> Dict[str, Any]:
        """Check Redis cache connectivity"""
        healthy = await CacheManager.health_check()
        return {
            "healthy": healthy,
            "details": {"connection": "ok" if healthy else "failed"}
        }
    
    async def disk_check(self) -> Dict[str, Any]:
        """Check disk space"""
        disk_usage = psutil.disk_usage('/')
        free_space_gb = disk_usage.free / (1024**3)
        usage_percent = (disk_usage.used / disk_usage.total) * 100
        
        healthy = free_space_gb > 1.0 and usage_percent < 90
        
        return {
            "healthy": healthy,
            "details": {
                "free_space_gb": round(free_space_gb, 2),
                "usage_percent": round(usage_percent, 2),
                "total_space_gb": round(disk_usage.total / (1024**3), 2)
            }
        }
    
    async def memory_check(self) -> Dict[str, Any]:
        """Check memory usage"""
        memory = psutil.virtual_memory()
        healthy = memory.percent < 90
        
        return {
            "healthy": healthy,
            "details": {
                "usage_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            }
        }
    
    async def get_health_status(self) -> HealthStatus:
        """Get comprehensive health status"""
        uptime = time.time() - self.start_time
        timestamp = datetime.utcnow()
        
        # Run all health checks
        check_results = {}
        check_tasks = {
            "database": self.database_check(),
            "cache": self.cache_check(),
            "disk": self.disk_check(),
            "memory": self.memory_check()
        }
        
        # Add custom checks
        for name, check_func in self.checks.items():
            check_tasks[name] = check_func()
        
        # Execute all checks concurrently
        for name, task in check_tasks.items():
            check_results[name] = await self.run_check(name, lambda: task)
        
        # Determine overall status
        unhealthy_checks = [name for name, check in check_results.items() 
                          if check.status == "unhealthy"]
        
        if unhealthy_checks:
            overall_status = "unhealthy" if len(unhealthy_checks) > 1 else "degraded"
        else:
            overall_status = "healthy"
        
        checks_dict = {name: check.dict() for name, check in check_results.items()}
        
        return HealthStatus(
            status=overall_status,
            timestamp=timestamp,
            service_name=self.service_name,
            version=self.version,
            uptime_seconds=round(uptime, 2),
            checks=checks_dict
        )
    
    async def get_metrics(self) -> MetricsResponse:
        """Get system metrics"""
        timestamp = datetime.utcnow()
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_metrics = {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "disk_usage_percent": round((disk.used / disk.total) * 100, 2),
            "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
        }
        
        # Database metrics
        database_metrics = {
            "connection_healthy": await DatabaseManager.health_check()
        }
        
        # Cache metrics
        cache_metrics = {
            "connection_healthy": await CacheManager.health_check()
        }
        
        # Custom metrics (to be overridden by services)
        custom_metrics = await self.get_custom_metrics()
        
        return MetricsResponse(
            timestamp=timestamp,
            service_name=self.service_name,
            system=system_metrics,
            database=database_metrics,
            cache=cache_metrics,
            custom_metrics=custom_metrics
        )
    
    async def get_custom_metrics(self) -> Dict[str, Any]:
        """Override this method in subclasses for service-specific metrics"""
        return {}

def create_health_router(monitor: HealthMonitor) -> APIRouter:
    """Create FastAPI router with health endpoints"""
    router = APIRouter(prefix="/health", tags=["health"])
    
    @router.get("/", response_model=HealthStatus)
    async def health_check():
        """Comprehensive health check"""
        health_status = await monitor.get_health_status()
        
        if health_status.status == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status.dict()
            )
        
        return health_status
    
    @router.get("/live")
    async def liveness_check():
        """Simple liveness check for Kubernetes"""
        return {"status": "alive", "timestamp": datetime.utcnow()}
    
    @router.get("/ready")
    async def readiness_check():
        """Readiness check for Kubernetes"""
        health_status = await monitor.get_health_status()
        
        if health_status.status == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
        
        return {"status": "ready", "timestamp": datetime.utcnow()}
    
    @router.get("/metrics", response_model=MetricsResponse)
    async def get_metrics():
        """Get detailed service metrics"""
        return await monitor.get_metrics()
    
    @router.get("/prometheus")
    async def prometheus_metrics():
        """Prometheus metrics endpoint"""
        return generate_latest().decode('utf-8')
    
    return router

class MetricsCollector:
    """Metrics collection utilities"""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        REQUEST_DURATION.observe(duration)
    
    @staticmethod
    def record_ai_api_call(provider: str, model: str, cost: float = 0):
        """Record AI API call metrics"""
        AI_API_CALLS.labels(provider=provider, model=model).inc()
        if cost > 0:
            AI_API_COST.labels(provider=provider).inc(cost)
    
    @staticmethod
    def set_queue_size(queue_name: str, size: int):
        """Set task queue size metric"""
        QUEUE_SIZE.labels(queue_name=queue_name).set(size)
    
    @staticmethod
    def set_database_connections(count: int):
        """Set active database connections metric"""
        ACTIVE_CONNECTIONS.set(count)
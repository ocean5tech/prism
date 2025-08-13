"""
Structured logging setup for all microservices
"""
import structlog
import logging
import sys
import os
from typing import Dict, Any
import uuid
from datetime import datetime

def setup_logging(service_name: str = "prism-service", log_level: str = "INFO"):
    """Setup structured logging for the service"""
    
    # Configure structlog
    timestamper = structlog.processors.TimeStamper(fmt="ISO")
    
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if os.getenv("ENVIRONMENT") == "production":
        # Production: JSON logging
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Pretty console logging
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Add service context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        service=service_name,
        environment=os.getenv("ENVIRONMENT", "development")
    )
    
    return structlog.get_logger()

class RequestLogger:
    """Request logging middleware"""
    
    def __init__(self, logger):
        self.logger = logger
    
    async def log_request(self, request, response, process_time: float):
        """Log HTTP request details"""
        self.logger.info(
            "HTTP Request",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time_seconds=round(process_time, 4),
            request_id=getattr(request.state, 'request_id', None),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None
        )
    
    async def log_error(self, request, error: Exception):
        """Log HTTP error details"""
        self.logger.error(
            "HTTP Error",
            method=request.method,
            url=str(request.url),
            error_type=type(error).__name__,
            error_message=str(error),
            request_id=getattr(request.state, 'request_id', None)
        )

class ServiceLogger:
    """Service-specific logging utilities"""
    
    def __init__(self, service_name: str):
        self.logger = structlog.get_logger().bind(service=service_name)
    
    def log_ai_request(self, model: str, prompt_tokens: int, completion_tokens: int, 
                      cost: float = None, response_time: float = None):
        """Log AI API request details"""
        log_data = {
            "event": "ai_request",
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        
        if cost is not None:
            log_data["cost_usd"] = cost
        
        if response_time is not None:
            log_data["response_time_seconds"] = round(response_time, 4)
        
        self.logger.info("AI API Request", **log_data)
    
    def log_content_generation(self, domain: str, word_count: int, 
                             quality_score: float = None, generation_time: float = None):
        """Log content generation details"""
        log_data = {
            "event": "content_generated",
            "domain": domain,
            "word_count": word_count,
        }
        
        if quality_score is not None:
            log_data["quality_score"] = quality_score
        
        if generation_time is not None:
            log_data["generation_time_seconds"] = round(generation_time, 4)
        
        self.logger.info("Content Generated", **log_data)
    
    def log_publishing_attempt(self, platform: str, content_id: str, 
                             success: bool, error_message: str = None):
        """Log publishing attempt details"""
        log_data = {
            "event": "publishing_attempt",
            "platform": platform,
            "content_id": content_id,
            "success": success,
        }
        
        if error_message:
            log_data["error_message"] = error_message
        
        if success:
            self.logger.info("Publishing Success", **log_data)
        else:
            self.logger.error("Publishing Failed", **log_data)
    
    def log_quality_analysis(self, content_id: str, overall_score: float, 
                           analysis_details: Dict[str, Any]):
        """Log quality analysis results"""
        self.logger.info(
            "Quality Analysis Complete",
            event="quality_analysis",
            content_id=content_id,
            overall_score=overall_score,
            **analysis_details
        )
    
    def log_database_operation(self, operation: str, table: str, 
                             execution_time: float = None, affected_rows: int = None):
        """Log database operation details"""
        log_data = {
            "event": "database_operation",
            "operation": operation,
            "table": table,
        }
        
        if execution_time is not None:
            log_data["execution_time_seconds"] = round(execution_time, 4)
        
        if affected_rows is not None:
            log_data["affected_rows"] = affected_rows
        
        self.logger.info("Database Operation", **log_data)

def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())

def get_correlation_id() -> str:
    """Get correlation ID from context or generate new one"""
    try:
        return structlog.contextvars.get_contextvars().get("correlation_id", generate_request_id())
    except:
        return generate_request_id()
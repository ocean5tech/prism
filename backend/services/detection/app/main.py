"""
Detection Service - FastAPI Application
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import os
from contextlib import asynccontextmanager

from .api import quality_router
from ...shared.database import DatabaseManager
from ...shared.logging import setup_logging, RequestLogger
from ...shared.monitoring import HealthMonitor, create_health_router, MetricsCollector

# Service configuration
SERVICE_NAME = "detection-service"
SERVICE_VERSION = "1.0.0"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Initialize logging
logger = setup_logging(SERVICE_NAME)
request_logger = RequestLogger(logger)

# Initialize health monitor
health_monitor = HealthMonitor(SERVICE_NAME, SERVICE_VERSION)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION}")
    
    # Create database tables
    try:
        await DatabaseManager.create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Register custom health checks
    health_monitor.register_check("ml_models", check_ml_models_health)
    health_monitor.register_check("vector_database", check_vector_db_health)
    
    logger.info(f"{SERVICE_NAME} started successfully")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {SERVICE_NAME}")

async def check_ml_models_health():
    """Custom health check for ML models"""
    # TODO: Implement actual ML models health check
    return {"healthy": True, "details": {"models_loaded": True, "analyzer_ready": True}}

async def check_vector_db_health():
    """Custom health check for vector database"""
    # TODO: Implement actual vector DB health check
    return {"healthy": True, "details": {"connection": "ok", "index_ready": True}}

# Create FastAPI app
app = FastAPI(
    title="Detection Service",
    description="AI-powered content quality detection and adversarial optimization",
    version=SERVICE_VERSION,
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else ["https://api.prism.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["api.prism.com", "*.prism.com"]
    )

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Request/response logging middleware"""
    start_time = time.time()
    
    # Generate request ID
    request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")
    request.state.request_id = request_id
    
    # Process request
    response = await call_next(request)
    
    # Calculate process time
    process_time = time.time() - start_time
    
    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Service"] = SERVICE_NAME
    
    # Log request
    await request_logger.log_request(request, response, process_time)
    
    # Record metrics
    MetricsCollector.record_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration=process_time
    )
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    await request_logger.log_error(request, exc)
    
    if ENVIRONMENT == "development":
        import traceback
        logger.error(f"Unhandled exception: {traceback.format_exc()}")
    
    return Response(
        content=f"Internal server error: {str(exc) if ENVIRONMENT == 'development' else 'Internal server error'}",
        status_code=500,
        headers={"X-Request-ID": getattr(request.state, 'request_id', 'unknown')}
    )

# Include routers
app.include_router(quality_router)
app.include_router(create_health_router(health_monitor))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "operational",
        "docs_url": "/docs" if ENVIRONMENT == "development" else None
    }

@app.get("/info")
async def service_info():
    """Service information endpoint"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "environment": ENVIRONMENT,
        "features": [
            "Quality analysis",
            "Pattern detection", 
            "Plagiarism checking",
            "Adversarial feedback",
            "Batch processing",
            "Threshold configuration",
            "Similarity analysis"
        ],
        "supported_domains": ["finance", "sports", "technology", "general"],
        "analysis_types": ["quality", "plagiarism", "pattern_detection", "comprehensive"],
        "quality_dimensions": [
            "readability", "originality", "accuracy", "engagement",
            "coherence", "domain_relevance", "seo"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        log_config=None,  # Use our custom logging
        access_log=False   # Disable default access logging
    )
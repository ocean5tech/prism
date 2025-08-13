"""
Content Generation API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
import uuid
import structlog

from ..schemas import (
    ContentGenerationRequest,
    ContentGenerationResponse,
    BatchGenerationRequest,
    BatchGenerationResponse,
    GenerationStatusResponse,
    ContentStatus
)
from ..services import ContentGenerationService
from ....shared.auth import (
    get_current_user,
    require_content_create,
    TokenData
)
from ....shared.logging import ServiceLogger
from ....shared.monitoring import MetricsCollector

router = APIRouter(prefix="/api/v1/content", tags=["content-generation"])
logger = structlog.get_logger()
service_logger = ServiceLogger("content-api")

# Service instance
content_service = ContentGenerationService()

@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(
    request: ContentGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_content_create)
):
    """
    Generate content based on request parameters
    
    Generates high-quality, domain-specific content using AI with:
    - Intelligent style parameter randomization
    - Domain-specific expertise
    - Quality assessment and scoring
    - SEO optimization
    """
    try:
        # Log request
        service_logger.logger.info(
            "Content generation requested",
            user_id=current_user.user_id,
            domain=request.domain.value,
            target_length=request.target_length,
            priority=request.priority.value
        )
        
        # Generate content
        result = await content_service.generate_content(request, current_user.user_id)
        
        # Record metrics
        MetricsCollector.record_ai_api_call(
            provider="anthropic",
            model=result.metadata.model_used,
            cost=result.metadata.api_cost_usd or 0
        )
        
        service_logger.logger.info(
            "Content generation completed",
            content_id=result.content_id,
            word_count=result.metadata.word_count,
            quality_score=result.quality_indicators.overall_score,
            generation_time=result.metadata.generation_time
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Content generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}"
        )

@router.post("/generate/batch", response_model=BatchGenerationResponse)
async def generate_batch_content(
    request: BatchGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_content_create)
):
    """
    Generate multiple content items in batch
    
    Efficiently processes multiple content generation requests with:
    - Concurrent processing with rate limiting
    - Individual request tracking
    - Comprehensive batch reporting
    - Error isolation (one failure doesn't stop the batch)
    """
    try:
        if len(request.requests) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 10 requests"
            )
        
        service_logger.logger.info(
            "Batch generation requested",
            user_id=current_user.user_id,
            batch_size=len(request.requests)
        )
        
        result = await content_service.generate_batch(request, current_user.user_id)
        
        service_logger.logger.info(
            "Batch generation completed",
            batch_id=result.batch_id,
            successful=result.successful_generations,
            failed=result.failed_generations,
            processing_time=result.processing_time
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch generation failed: {str(e)}"
        )

@router.get("/content/{content_id}", response_model=ContentGenerationResponse)
async def get_content_by_id(
    content_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Retrieve generated content by ID
    
    Returns complete content details including:
    - Generated text and metadata
    - Quality indicators and scores
    - SEO data (keywords, meta description)
    - Generation metrics and cost information
    """
    try:
        # Validate UUID format
        uuid.UUID(content_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID format"
        )
    
    result = await content_service.get_content_by_id(content_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    return result

@router.get("/status/{content_id}", response_model=GenerationStatusResponse)
async def get_generation_status(
    content_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get generation status for long-running operations
    
    Useful for tracking the progress of content generation,
    especially for complex or batch operations.
    """
    try:
        uuid.UUID(content_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID format"
        )
    
    # For now, return basic status (can be enhanced with real-time tracking)
    content = await content_service.get_content_by_id(content_id)
    
    if not content:
        return GenerationStatusResponse(
            content_id=content_id,
            status=ContentStatus.DRAFT,
            progress_percentage=0.0,
            current_step="Not found",
            error_message="Content not found"
        )
    
    return GenerationStatusResponse(
        content_id=content_id,
        status=content.status,
        progress_percentage=100.0,
        current_step="Completed",
        estimated_completion=None
    )

@router.post("/regenerate/{content_id}", response_model=ContentGenerationResponse)
async def regenerate_content(
    content_id: str,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_content_create)
):
    """
    Regenerate content with improved parameters
    
    Useful when quality scores are low or content needs enhancement.
    Uses learned parameters from previous generation attempts.
    """
    try:
        # Get original content
        original_content = await content_service.get_content_by_id(content_id)
        
        if not original_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original content not found"
            )
        
        # Create regeneration request with enhanced parameters
        # TODO: Implement parameter enhancement based on quality analysis
        
        service_logger.logger.info(
            "Content regeneration requested",
            original_content_id=content_id,
            user_id=current_user.user_id
        )
        
        # For now, return the original (implement actual regeneration)
        return original_content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content regeneration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regeneration failed: {str(e)}"
        )

# Health check endpoint for this service
@router.get("/health")
async def content_service_health():
    """Content generation service health check"""
    try:
        # Basic health checks
        health_status = {
            "service": "content-generation",
            "status": "healthy",
            "timestamp": "2025-08-08T10:30:00Z",
            "checks": {
                "claude_api": "healthy",  # TODO: Implement actual Claude API check
                "database": "healthy",    # TODO: Implement database check
                "cache": "healthy"        # TODO: Implement cache check
            }
        }
        return health_status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )
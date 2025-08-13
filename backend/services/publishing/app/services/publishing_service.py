"""
Publishing Service - Multi-Platform Content Distribution
"""
import asyncio
import uuid
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import httpx
import structlog
from jinja2 import Template

from ..models import (
    PublicationRequest,
    Publication,
    PlatformConnection,
    PublicationTemplate,
    EngagementMetrics,
    PublicationStatus,
    PlatformType
)
from ..schemas import (
    MultiPlatformPublicationRequest,
    MultiPlatformPublicationResponse,
    PublicationResult,
    PublicationStatusResponse,
    EngagementMetricsResponse,
    PlatformSettings
)
from .platform_adapters import PlatformAdapterFactory
from ....shared.database import get_db_session, CacheManager
from ....shared.logging import ServiceLogger

logger = structlog.get_logger()
service_logger = ServiceLogger("publishing-service")

class PublishingServiceError(Exception):
    """Custom exception for publishing service errors"""
    pass

class PublishingService:
    """Core multi-platform publishing service"""
    
    def __init__(self):
        self.platform_factory = PlatformAdapterFactory()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def publish_multi_platform(
        self,
        request: MultiPlatformPublicationRequest,
        user_id: str
    ) -> MultiPlatformPublicationResponse:
        """Publish content to multiple platforms"""
        
        try:
            start_time = time.time()
            
            # Store publication request
            async with get_db_session() as db:
                pub_request = PublicationRequest(
                    content_id=request.content_id or f"content-{int(time.time())}",
                    user_id=user_id,
                    title=request.title,
                    content=request.content,
                    summary=request.summary,
                    meta_description=request.meta_description,
                    keywords=request.keywords,
                    hashtags=request.hashtags,
                    domain=request.domain,
                    content_format=request.content_format.value,
                    target_platforms=[p.dict() for p in request.platforms],
                    publish_immediately=request.scheduling.publish_immediately,
                    scheduled_time=request.scheduling.scheduled_time,
                    timezone=request.scheduling.timezone,
                    publication_settings=request.scheduling.dict(),
                    priority=request.priority.value,
                    workflow_id=request.workflow_id,
                    execution_id=request.execution_id
                )
                
                db.add(pub_request)
                await db.flush()
                
                # Create individual publications for each platform
                publications = []
                for platform_settings in request.platforms:
                    publication = Publication(
                        publication_request_id=pub_request.id,
                        platform=platform_settings.platform.value,
                        platform_account_id=platform_settings.account_id,
                        formatted_title=platform_settings.custom_title or request.title,
                        formatted_content=platform_settings.custom_content or request.content,
                        platform_specific_data=platform_settings.dict(),
                        status=PublicationStatus.PENDING.value,
                        scheduled_time=request.scheduling.scheduled_time
                    )
                    db.add(publication)
                    publications.append(publication)
                
                await db.commit()
                
                # Process publications
                results = await self._process_publications(publications, user_id)
                
                # Calculate success metrics
                successful = sum(1 for r in results if r.status == PublicationStatus.PUBLISHED)
                failed = sum(1 for r in results if r.status == PublicationStatus.FAILED)
                pending = len(results) - successful - failed
                
                processing_time = time.time() - start_time
                success_rate = (successful / len(results)) * 100 if results else 0
                
                # Log publication results
                service_logger.log_publishing_attempt(
                    platform="multi-platform",
                    content_id=pub_request.content_id,
                    success=success_rate >= 50,  # Consider successful if >50% platforms succeed
                    error_message=None if success_rate >= 50 else f"Low success rate: {success_rate}%"
                )
                
                return MultiPlatformPublicationResponse(
                    request_id=str(pub_request.id),
                    content_id=pub_request.content_id,
                    title=request.title,
                    domain=request.domain,
                    total_platforms=len(request.platforms),
                    successful_publications=successful,
                    failed_publications=failed,
                    pending_publications=pending,
                    publications=results,
                    processing_time_seconds=processing_time,
                    overall_success_rate=success_rate,
                    created_at=pub_request.created_at
                )
                
        except Exception as e:
            logger.error(f"Multi-platform publishing failed: {str(e)}")
            raise PublishingServiceError(f"Publishing failed: {str(e)}")
    
    async def _process_publications(
        self, 
        publications: List[Publication],
        user_id: str
    ) -> List[PublicationResult]:
        """Process individual publications to platforms"""
        
        results = []
        
        # Process publications with concurrency control
        semaphore = asyncio.Semaphore(3)  # Limit concurrent publications
        
        async def publish_single(publication):
            async with semaphore:
                return await self._publish_to_platform(publication, user_id)
        
        # Execute publications
        tasks = [publish_single(pub) for pub in publications]
        publication_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(publication_results):
            if isinstance(result, Exception):
                # Handle publication error
                publication = publications[i]
                results.append(PublicationResult(
                    publication_id=str(publication.id),
                    platform=PlatformType(publication.platform),
                    status=PublicationStatus.FAILED,
                    error_message=str(result),
                    api_response_time=None
                ))
                
                # Update publication status in database
                async with get_db_session() as db:
                    await db.execute(
                        select(Publication)
                        .where(Publication.id == publication.id)
                    )
                    publication.status = PublicationStatus.FAILED.value
                    publication.error_message = str(result)
                    await db.commit()
            else:
                results.append(result)
        
        return results
    
    async def _publish_to_platform(
        self, 
        publication: Publication,
        user_id: str
    ) -> PublicationResult:
        """Publish content to a specific platform"""
        
        start_time = time.time()
        
        try:
            # Update status to publishing
            async with get_db_session() as db:
                publication.status = PublicationStatus.PUBLISHING.value
                await db.commit()
            
            # Get platform adapter
            adapter = await self.platform_factory.get_adapter(
                PlatformType(publication.platform)
            )
            
            # Get platform connection
            platform_connection = await self._get_platform_connection(
                user_id, 
                publication.platform
            )
            
            if not platform_connection or not platform_connection.is_authenticated:
                raise PublishingServiceError(f"Platform {publication.platform} not connected or not authenticated")
            
            # Format content for platform
            formatted_content = await self._format_content_for_platform(
                publication, 
                PlatformType(publication.platform)
            )
            
            # Publish to platform
            publish_result = await adapter.publish_content(
                connection=platform_connection,
                title=publication.formatted_title,
                content=formatted_content,
                metadata=publication.platform_specific_data
            )
            
            api_response_time = time.time() - start_time
            
            # Update publication with results
            async with get_db_session() as db:
                publication.status = PublicationStatus.PUBLISHED.value
                publication.external_post_id = publish_result.get("post_id")
                publication.external_url = publish_result.get("url")
                publication.published_at = datetime.utcnow()
                publication.api_response_time = api_response_time
                publication.platform_response = publish_result
                await db.commit()
            
            return PublicationResult(
                publication_id=str(publication.id),
                platform=PlatformType(publication.platform),
                status=PublicationStatus.PUBLISHED,
                external_post_id=publish_result.get("post_id"),
                external_url=publish_result.get("url"),
                published_at=publication.published_at,
                api_response_time=api_response_time
            )
            
        except Exception as e:
            # Handle publication error
            async with get_db_session() as db:
                publication.status = PublicationStatus.FAILED.value
                publication.error_message = str(e)
                publication.api_response_time = time.time() - start_time
                await db.commit()
            
            service_logger.log_publishing_attempt(
                platform=publication.platform,
                content_id=publication.publication_request.content_id,
                success=False,
                error_message=str(e)
            )
            
            return PublicationResult(
                publication_id=str(publication.id),
                platform=PlatformType(publication.platform),
                status=PublicationStatus.FAILED,
                error_message=str(e),
                api_response_time=time.time() - start_time
            )
    
    async def _get_platform_connection(
        self, 
        user_id: str, 
        platform: str
    ) -> Optional[PlatformConnection]:
        """Get user's platform connection"""
        
        async with get_db_session() as db:
            result = await db.execute(
                select(PlatformConnection).where(
                    and_(
                        PlatformConnection.user_id == user_id,
                        PlatformConnection.platform == platform,
                        PlatformConnection.is_active == True,
                        PlatformConnection.is_authenticated == True
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def _format_content_for_platform(
        self,
        publication: Publication,
        platform: PlatformType
    ) -> str:
        """Format content for specific platform requirements"""
        
        content = publication.formatted_content
        platform_data = publication.platform_specific_data or {}
        
        # Apply platform-specific formatting
        if platform == PlatformType.TWITTER:
            # Twitter character limit
            if len(content) > 280:
                content = content[:277] + "..."
        
        elif platform == PlatformType.LINKEDIN:
            # LinkedIn formatting optimizations
            if platform_data.get("add_professional_tone"):
                content = f"Professional insight: {content}"
        
        elif platform == PlatformType.MEDIUM:
            # Medium formatting with proper structure
            content = self._format_for_medium(content, publication.formatted_title)
        
        # Apply template if specified
        template_config = platform_data.get("template_config")
        if template_config:
            content = await self._apply_template(content, template_config)
        
        return content
    
    def _format_for_medium(self, content: str, title: str) -> str:
        """Format content for Medium platform"""
        
        # Add title as header
        formatted = f"# {title}\n\n{content}"
        
        # Ensure proper paragraph spacing
        paragraphs = formatted.split('\n\n')
        formatted = '\n\n'.join(p.strip() for p in paragraphs if p.strip())
        
        return formatted
    
    async def _apply_template(self, content: str, template_config: Dict[str, Any]) -> str:
        """Apply Jinja2 template to content"""
        
        try:
            template_str = template_config.get("template")
            if not template_str:
                return content
            
            template = Template(template_str)
            variables = template_config.get("variables", {})
            variables["content"] = content
            
            return template.render(**variables)
            
        except Exception as e:
            logger.warning(f"Template application failed: {str(e)}")
            return content
    
    async def get_publication_status(self, publication_id: str) -> Optional[PublicationStatusResponse]:
        """Get publication status by ID"""
        
        async with get_db_session() as db:
            result = await db.execute(
                select(Publication).where(Publication.id == publication_id)
            )
            publication = result.scalar_one_or_none()
            
            if not publication:
                return None
            
            # Calculate progress based on status
            progress_map = {
                PublicationStatus.PENDING.value: 10.0,
                PublicationStatus.SCHEDULED.value: 25.0,
                PublicationStatus.PUBLISHING.value: 75.0,
                PublicationStatus.PUBLISHED.value: 100.0,
                PublicationStatus.FAILED.value: 0.0,
                PublicationStatus.CANCELLED.value: 0.0
            }
            
            progress = progress_map.get(publication.status, 0.0)
            
            return PublicationStatusResponse(
                publication_id=str(publication.id),
                request_id=str(publication.publication_request_id),
                platform=PlatformType(publication.platform),
                status=PublicationStatus(publication.status),
                progress_percentage=progress,
                current_step=self._get_current_step(publication.status),
                external_post_id=publication.external_post_id,
                external_url=publication.external_url,
                error_message=publication.error_message,
                retry_count=publication.retry_count,
                next_retry_time=self._calculate_next_retry_time(publication),
                estimated_completion=publication.scheduled_time
            )
    
    def _get_current_step(self, status: str) -> str:
        """Get human-readable current step description"""
        step_map = {
            PublicationStatus.PENDING.value: "Waiting in queue",
            PublicationStatus.SCHEDULED.value: "Scheduled for publication",
            PublicationStatus.PUBLISHING.value: "Publishing to platform",
            PublicationStatus.PUBLISHED.value: "Successfully published",
            PublicationStatus.FAILED.value: "Publication failed",
            PublicationStatus.CANCELLED.value: "Publication cancelled",
            PublicationStatus.RETRY.value: "Retrying publication"
        }
        return step_map.get(status, "Unknown status")
    
    def _calculate_next_retry_time(self, publication: Publication) -> Optional[datetime]:
        """Calculate next retry time for failed publications"""
        
        if publication.status != PublicationStatus.FAILED.value:
            return None
        
        if publication.retry_count >= publication.max_retries:
            return None
        
        # Exponential backoff: 5, 15, 45 minutes
        delay_minutes = 5 * (3 ** publication.retry_count)
        return datetime.utcnow() + timedelta(minutes=delay_minutes)
    
    async def retry_failed_publication(self, publication_id: str, user_id: str) -> PublicationResult:
        """Retry a failed publication"""
        
        async with get_db_session() as db:
            result = await db.execute(
                select(Publication).where(Publication.id == publication_id)
            )
            publication = result.scalar_one_or_none()
            
            if not publication:
                raise PublishingServiceError("Publication not found")
            
            if publication.status != PublicationStatus.FAILED.value:
                raise PublishingServiceError("Publication is not in failed status")
            
            if publication.retry_count >= publication.max_retries:
                raise PublishingServiceError("Maximum retries exceeded")
            
            # Increment retry count
            publication.retry_count += 1
            publication.status = PublicationStatus.RETRY.value
            publication.error_message = None
            await db.commit()
            
            # Retry publication
            return await self._publish_to_platform(publication, user_id)
    
    async def collect_engagement_metrics(self, publication_id: str) -> Optional[EngagementMetricsResponse]:
        """Collect engagement metrics for a publication"""
        
        async with get_db_session() as db:
            result = await db.execute(
                select(Publication).where(Publication.id == publication_id)
            )
            publication = result.scalar_one_or_none()
            
            if not publication or publication.status != PublicationStatus.PUBLISHED.value:
                return None
            
            try:
                # Get platform adapter
                adapter = await self.platform_factory.get_adapter(
                    PlatformType(publication.platform)
                )
                
                # Get platform connection
                platform_connection = await self._get_platform_connection(
                    str(publication.publication_request.user_id),
                    publication.platform
                )
                
                if not platform_connection:
                    return None
                
                # Collect metrics from platform
                metrics_data = await adapter.get_engagement_metrics(
                    connection=platform_connection,
                    post_id=publication.external_post_id
                )
                
                # Store metrics
                engagement_metrics = EngagementMetrics(
                    publication_id=publication.id,
                    views=metrics_data.get("views", 0),
                    clicks=metrics_data.get("clicks", 0),
                    likes=metrics_data.get("likes", 0),
                    shares=metrics_data.get("shares", 0),
                    comments=metrics_data.get("comments", 0),
                    platform_metrics=metrics_data.get("platform_specific", {}),
                    engagement_rate=self._calculate_engagement_rate(metrics_data),
                    click_through_rate=self._calculate_ctr(metrics_data),
                    collection_method="api"
                )
                
                db.add(engagement_metrics)
                await db.commit()
                
                return EngagementMetricsResponse(
                    publication_id=str(publication.id),
                    platform=PlatformType(publication.platform),
                    views=engagement_metrics.views,
                    clicks=engagement_metrics.clicks,
                    likes=engagement_metrics.likes,
                    shares=engagement_metrics.shares,
                    comments=engagement_metrics.comments,
                    engagement_rate=engagement_metrics.engagement_rate,
                    click_through_rate=engagement_metrics.click_through_rate,
                    platform_metrics=engagement_metrics.platform_metrics,
                    metrics_collected_at=engagement_metrics.metrics_collected_at,
                    collection_method=engagement_metrics.collection_method
                )
                
            except Exception as e:
                logger.error(f"Metrics collection failed: {str(e)}")
                return None
    
    def _calculate_engagement_rate(self, metrics_data: Dict[str, int]) -> float:
        """Calculate engagement rate from metrics"""
        views = metrics_data.get("views", 0)
        if views == 0:
            return 0.0
        
        engagements = (
            metrics_data.get("likes", 0) + 
            metrics_data.get("shares", 0) + 
            metrics_data.get("comments", 0)
        )
        
        return (engagements / views) * 100
    
    def _calculate_ctr(self, metrics_data: Dict[str, int]) -> float:
        """Calculate click-through rate from metrics"""
        views = metrics_data.get("views", 0)
        clicks = metrics_data.get("clicks", 0)
        
        if views == 0:
            return 0.0
        
        return (clicks / views) * 100
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()
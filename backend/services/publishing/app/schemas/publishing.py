"""
Publishing Service API Schemas
"""
from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class PlatformType(str, Enum):
    WORDPRESS = "wordpress"
    MEDIUM = "medium"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    NEWSLETTER = "newsletter"
    CUSTOM_API = "custom_api"

class PublicationStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class ContentFormat(str, Enum):
    ARTICLE = "article"
    SOCIAL_POST = "social_post"
    NEWSLETTER = "newsletter"
    VIDEO_SCRIPT = "video_script"
    INFOGRAPHIC_TEXT = "infographic_text"

class PriorityLevel(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Request Schemas
class PlatformSettings(BaseModel):
    """Platform-specific publication settings"""
    platform: PlatformType = Field(description="Publishing platform")
    account_id: Optional[str] = Field(None, description="Platform account/page ID")
    custom_title: Optional[str] = Field(None, description="Platform-specific title override")
    custom_content: Optional[str] = Field(None, description="Platform-specific content override")
    tags: Optional[List[str]] = Field(None, description="Platform-specific tags")
    category: Optional[str] = Field(None, description="Content category")
    visibility: Optional[str] = Field("public", description="Content visibility")
    enable_comments: Optional[bool] = Field(True, description="Enable comments")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "platform": "linkedin",
            "account_id": "company-page-123",
            "custom_title": "Professional Analysis: Market Trends",
            "tags": ["finance", "analysis", "markets"],
            "category": "professional",
            "visibility": "public",
            "enable_comments": True
        }
    })

class SchedulingSettings(BaseModel):
    """Content scheduling configuration"""
    publish_immediately: bool = Field(default=True, description="Publish immediately")
    scheduled_time: Optional[datetime] = Field(None, description="Scheduled publication time")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    use_optimal_timing: bool = Field(default=False, description="Use AI-optimized timing")
    distribute_evenly: bool = Field(default=False, description="Distribute publications evenly")
    
    @validator("scheduled_time")
    def validate_scheduled_time(cls, v, values):
        if not values.get("publish_immediately") and v is None:
            raise ValueError("scheduled_time is required when publish_immediately is False")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "publish_immediately": False,
            "scheduled_time": "2025-08-08T15:00:00Z",
            "timezone": "America/New_York",
            "use_optimal_timing": True,
            "distribute_evenly": False
        }
    })

class MultiPlatformPublicationRequest(BaseModel):
    """Multi-platform content publication request"""
    content_id: Optional[str] = Field(None, description="Source content ID")
    title: str = Field(min_length=1, max_length=500, description="Content title")
    content: str = Field(min_length=10, description="Main content body")
    summary: Optional[str] = Field(None, description="Content summary")
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    keywords: List[str] = Field(default_factory=list, description="Content keywords")
    hashtags: List[str] = Field(default_factory=list, description="Social media hashtags")
    
    # Publication configuration
    domain: str = Field(description="Content domain")
    content_format: ContentFormat = Field(default=ContentFormat.ARTICLE, description="Content format")
    platforms: List[PlatformSettings] = Field(min_items=1, description="Target platforms")
    
    # Scheduling
    scheduling: SchedulingSettings = Field(default_factory=SchedulingSettings, description="Scheduling settings")
    
    # Additional metadata
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Publication priority")
    workflow_id: Optional[str] = Field(None, description="n8n workflow ID")
    execution_id: Optional[str] = Field(None, description="n8n execution ID")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content_id": "content-123",
            "title": "The Future of Artificial Intelligence in Finance",
            "content": "Artificial intelligence is revolutionizing the financial sector...",
            "summary": "An in-depth analysis of AI's impact on financial services.",
            "keywords": ["artificial intelligence", "finance", "technology"],
            "hashtags": ["#AI", "#FinTech", "#Innovation"],
            "domain": "technology",
            "content_format": "article",
            "platforms": [
                {
                    "platform": "linkedin",
                    "tags": ["technology", "finance"],
                    "category": "professional"
                },
                {
                    "platform": "medium",
                    "tags": ["ai", "fintech"],
                    "category": "technology"
                }
            ],
            "scheduling": {
                "publish_immediately": False,
                "scheduled_time": "2025-08-08T15:00:00Z",
                "use_optimal_timing": True
            },
            "priority": "high"
        }
    })

class SinglePlatformPublicationRequest(BaseModel):
    """Single platform publication request"""
    content_id: Optional[str] = Field(None, description="Source content ID")
    platform: PlatformType = Field(description="Target platform")
    title: str = Field(min_length=1, max_length=500, description="Content title")
    content: str = Field(min_length=10, description="Content body")
    platform_settings: Optional[Dict[str, Any]] = Field(None, description="Platform-specific settings")
    scheduling: SchedulingSettings = Field(default_factory=SchedulingSettings, description="Scheduling settings")

# Response Schemas
class PublicationResult(BaseModel):
    """Individual publication result"""
    publication_id: str = Field(description="Publication ID")
    platform: PlatformType = Field(description="Publishing platform")
    status: PublicationStatus = Field(description="Publication status")
    external_post_id: Optional[str] = Field(None, description="Platform post ID")
    external_url: Optional[str] = Field(None, description="Published content URL")
    scheduled_time: Optional[datetime] = Field(None, description="Scheduled publication time")
    published_at: Optional[datetime] = Field(None, description="Actual publication time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    api_response_time: Optional[float] = Field(None, description="Platform API response time")

class MultiPlatformPublicationResponse(BaseModel):
    """Multi-platform publication response"""
    request_id: str = Field(description="Publication request ID")
    content_id: Optional[str] = Field(None, description="Source content ID")
    title: str = Field(description="Content title")
    domain: str = Field(description="Content domain")
    
    # Publication results
    total_platforms: int = Field(description="Total platforms targeted")
    successful_publications: int = Field(description="Number of successful publications")
    failed_publications: int = Field(description="Number of failed publications")
    pending_publications: int = Field(description="Number of pending publications")
    
    publications: List[PublicationResult] = Field(description="Individual publication results")
    
    # Processing metadata
    processing_time_seconds: float = Field(description="Total processing time")
    overall_success_rate: float = Field(description="Success rate percentage")
    
    created_at: datetime = Field(description="Request creation time")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "request_id": "pub-req-123",
                "content_id": "content-123",
                "title": "The Future of AI in Finance",
                "domain": "technology",
                "total_platforms": 2,
                "successful_publications": 2,
                "failed_publications": 0,
                "pending_publications": 0,
                "publications": [
                    {
                        "publication_id": "pub-456",
                        "platform": "linkedin",
                        "status": "published",
                        "external_post_id": "li-post-789",
                        "external_url": "https://linkedin.com/posts/li-post-789",
                        "published_at": "2025-08-08T15:02:30Z",
                        "api_response_time": 1.2
                    }
                ],
                "processing_time_seconds": 5.8,
                "overall_success_rate": 100.0,
                "created_at": "2025-08-08T15:00:00Z"
            }
        }
    )

class PublicationStatusResponse(BaseModel):
    """Publication status check response"""
    publication_id: str = Field(description="Publication ID")
    request_id: str = Field(description="Publication request ID")
    platform: PlatformType = Field(description="Publishing platform")
    status: PublicationStatus = Field(description="Current status")
    progress_percentage: float = Field(ge=0.0, le=100.0, description="Progress percentage")
    current_step: str = Field(description="Current processing step")
    external_post_id: Optional[str] = Field(None, description="Platform post ID")
    external_url: Optional[str] = Field(None, description="Published content URL")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(description="Number of retry attempts")
    next_retry_time: Optional[datetime] = Field(None, description="Next retry time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

# Platform Connection Schemas
class PlatformConnectionRequest(BaseModel):
    """Platform connection configuration request"""
    platform: PlatformType = Field(description="Platform to connect")
    platform_name: str = Field(description="Friendly name for connection")
    account_id: Optional[str] = Field(None, description="Platform account ID")
    account_name: Optional[str] = Field(None, description="Account display name")
    
    # Authentication
    access_token: str = Field(description="Platform access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration")
    
    # Configuration
    api_endpoint: Optional[str] = Field(None, description="Custom API endpoint")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for updates")
    default_settings: Optional[Dict[str, Any]] = Field(None, description="Default publication settings")

class PlatformConnectionResponse(BaseModel):
    """Platform connection response"""
    connection_id: str = Field(description="Connection ID")
    platform: PlatformType = Field(description="Connected platform")
    platform_name: str = Field(description="Friendly name")
    account_name: Optional[str] = Field(None, description="Account display name")
    is_active: bool = Field(description="Connection active status")
    is_authenticated: bool = Field(description="Authentication status")
    health_status: str = Field(description="Connection health status")
    success_rate: float = Field(description="Publication success rate")
    total_publications: int = Field(description="Total publications")
    last_health_check: Optional[datetime] = Field(None, description="Last health check")
    created_at: datetime = Field(description="Connection creation time")

# Template Schemas
class PublicationTemplateRequest(BaseModel):
    """Publication template creation request"""
    name: str = Field(min_length=1, max_length=200, description="Template name")
    platform: PlatformType = Field(description="Target platform")
    content_format: ContentFormat = Field(description="Content format")
    domain: Optional[str] = Field(None, description="Domain-specific template")
    
    title_template: Optional[str] = Field(None, description="Title template (Jinja2)")
    content_template: str = Field(min_length=10, description="Content template (Jinja2)")
    
    character_limit: Optional[int] = Field(None, description="Platform character limit")
    supports_html: bool = Field(default=False, description="Platform supports HTML")
    supports_markdown: bool = Field(default=False, description="Platform supports Markdown")
    
    template_config: Optional[Dict[str, Any]] = Field(None, description="Template configuration")

class PublicationTemplateResponse(BaseModel):
    """Publication template response"""
    template_id: str = Field(description="Template ID")
    name: str = Field(description="Template name")
    platform: PlatformType = Field(description="Target platform")
    content_format: ContentFormat = Field(description="Content format")
    domain: Optional[str] = Field(None, description="Domain")
    
    usage_count: int = Field(description="Template usage count")
    success_rate: float = Field(description="Template success rate")
    average_engagement: float = Field(description="Average engagement rate")
    
    is_active: bool = Field(description="Template active status")
    is_default: bool = Field(description="Default template for platform")
    
    created_at: datetime = Field(description="Template creation time")
    updated_at: datetime = Field(description="Last update time")

# Analytics Schemas  
class EngagementMetricsResponse(BaseModel):
    """Engagement metrics response"""
    publication_id: str = Field(description="Publication ID")
    platform: PlatformType = Field(description="Publishing platform")
    
    # Basic metrics
    views: int = Field(description="Total views")
    clicks: int = Field(description="Total clicks")
    likes: int = Field(description="Total likes")
    shares: int = Field(description="Total shares")
    comments: int = Field(description="Total comments")
    
    # Calculated metrics
    engagement_rate: float = Field(description="Engagement rate percentage")
    click_through_rate: float = Field(description="Click-through rate percentage")
    
    # Platform-specific metrics
    platform_metrics: Dict[str, Any] = Field(description="Platform-specific metrics")
    
    metrics_collected_at: datetime = Field(description="Metrics collection time")
    collection_method: str = Field(description="Collection method")

class PublicationAnalyticsResponse(BaseModel):
    """Publication analytics summary response"""
    user_id: str = Field(description="User ID")
    platform: Optional[PlatformType] = Field(None, description="Specific platform")
    domain: Optional[str] = Field(None, description="Specific domain")
    
    date_range_start: datetime = Field(description="Analysis start date")
    date_range_end: datetime = Field(description="Analysis end date")
    
    # Publication metrics
    total_publications: int = Field(description="Total publications")
    successful_publications: int = Field(description="Successful publications")
    success_rate: float = Field(description="Success rate percentage")
    
    # Engagement metrics
    total_views: int = Field(description="Total views across all publications")
    total_clicks: int = Field(description="Total clicks")
    total_likes: int = Field(description="Total likes")
    total_shares: int = Field(description="Total shares")
    average_engagement_rate: float = Field(description="Average engagement rate")
    
    # Performance insights
    top_performing_time: Optional[str] = Field(None, description="Best performing time slot")
    top_performing_day: Optional[str] = Field(None, description="Best performing day")
    recommendations: List[str] = Field(description="Performance improvement recommendations")
    
    generated_at: datetime = Field(description="Analytics generation time")

class BatchPublicationRequest(BaseModel):
    """Batch publication request"""
    publications: List[MultiPlatformPublicationRequest] = Field(
        min_items=1, max_items=50, 
        description="Batch of publication requests"
    )
    batch_settings: Optional[Dict[str, Any]] = Field(None, description="Batch processing settings")

class BatchPublicationResponse(BaseModel):
    """Batch publication response"""
    batch_id: str = Field(description="Batch ID")
    total_requests: int = Field(description="Total publication requests")
    successful_requests: int = Field(description="Successful requests")
    failed_requests: int = Field(description="Failed requests")
    results: List[MultiPlatformPublicationResponse] = Field(description="Individual results")
    processing_time_seconds: float = Field(description="Total processing time")
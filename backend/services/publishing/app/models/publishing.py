"""
Publishing Service Database Models
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from enum import Enum

from ....shared.database import Base

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

class PublicationRequest(Base):
    """Publication request for content distribution"""
    __tablename__ = "publication_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(String(100), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Content data
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    meta_description = Column(Text)
    keywords = Column(JSON)  # List of keywords
    hashtags = Column(JSON)  # List of hashtags
    
    # Publication configuration
    domain = Column(String(50), nullable=False)
    content_format = Column(String(50), nullable=False, default=ContentFormat.ARTICLE.value)
    target_platforms = Column(JSON, nullable=False)  # List of platforms to publish to
    
    # Scheduling
    publish_immediately = Column(Boolean, default=True)
    scheduled_time = Column(DateTime)
    timezone = Column(String(50), default='UTC')
    
    # Publication settings
    publication_settings = Column(JSON)  # Platform-specific settings
    custom_formatting = Column(JSON)  # Custom formatting per platform
    
    # Request metadata
    priority = Column(String(20), default="normal")  # normal, high, urgent
    workflow_id = Column(String(100))  # n8n workflow ID
    execution_id = Column(String(100))  # n8n execution ID
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    publications = relationship("Publication", back_populates="publication_request")

class Publication(Base):
    """Individual publication to a specific platform"""
    __tablename__ = "publications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_request_id = Column(UUID(as_uuid=True), ForeignKey("publication_requests.id"), nullable=False)
    
    # Platform details
    platform = Column(String(50), nullable=False)
    platform_account_id = Column(String(100))  # Account/page ID on platform
    
    # Content formatting
    formatted_title = Column(String(500))
    formatted_content = Column(Text, nullable=False)
    platform_specific_data = Column(JSON)  # Platform-specific metadata
    
    # Publication status
    status = Column(String(20), nullable=False, default=PublicationStatus.PENDING.value)
    external_post_id = Column(String(200))  # Platform's post/article ID
    external_url = Column(String(500))  # Published content URL
    
    # Scheduling
    scheduled_time = Column(DateTime)
    published_at = Column(DateTime)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Performance tracking
    api_response_time = Column(Float)  # Platform API response time
    platform_response = Column(JSON)  # Full API response
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    publication_request = relationship("PublicationRequest", back_populates="publications")
    engagement_metrics = relationship("EngagementMetrics", back_populates="publication")

class PlatformConnection(Base):
    """Platform API connections and credentials"""
    __tablename__ = "platform_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Platform details
    platform = Column(String(50), nullable=False)
    platform_name = Column(String(100))  # Friendly name
    account_id = Column(String(100))  # Platform account/page ID
    account_name = Column(String(200))  # Account display name
    
    # Authentication
    access_token = Column(Text)  # Encrypted access token
    refresh_token = Column(Text)  # Encrypted refresh token
    token_expires_at = Column(DateTime)
    
    # API configuration
    api_endpoint = Column(String(500))
    api_version = Column(String(20))
    webhook_url = Column(String(500))  # Webhook for status updates
    
    # Connection settings
    connection_config = Column(JSON)  # Platform-specific configuration
    default_settings = Column(JSON)  # Default publication settings
    
    # Status and health
    is_active = Column(Boolean, default=True)
    is_authenticated = Column(Boolean, default=False)
    last_health_check = Column(DateTime)
    health_status = Column(String(20), default="unknown")  # healthy, warning, error
    
    # Usage statistics
    total_publications = Column(Integer, default=0)
    successful_publications = Column(Integer, default=0)
    failed_publications = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EngagementMetrics(Base):
    """Track engagement metrics for published content"""
    __tablename__ = "engagement_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_id = Column(UUID(as_uuid=True), ForeignKey("publications.id"), nullable=False)
    
    # Basic metrics
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    
    # Platform-specific metrics
    platform_metrics = Column(JSON)  # Additional platform-specific metrics
    
    # Calculated metrics
    engagement_rate = Column(Float, default=0.0)  # (likes + shares + comments) / views
    click_through_rate = Column(Float, default=0.0)  # clicks / views
    
    # Data collection
    metrics_collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    collection_method = Column(String(50))  # api, webhook, manual
    
    # Relationship
    publication = relationship("Publication", back_populates="engagement_metrics")

class PublicationTemplate(Base):
    """Templates for platform-specific content formatting"""
    __tablename__ = "publication_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template identification
    name = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False)
    content_format = Column(String(50), nullable=False)
    domain = Column(String(50))  # Domain-specific template
    
    # Template content
    title_template = Column(Text)  # Jinja2 template for title
    content_template = Column(Text, nullable=False)  # Jinja2 template for content
    
    # Platform formatting
    character_limit = Column(Integer)
    supports_html = Column(Boolean, default=False)
    supports_markdown = Column(Boolean, default=False)
    required_fields = Column(JSON)  # Required fields for platform
    
    # Template configuration
    template_config = Column(JSON)  # Template-specific configuration
    variable_definitions = Column(JSON)  # Available variables
    
    # Usage and performance
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    average_engagement = Column(Float, default=0.0)
    
    # Template status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PublicationSchedule(Base):
    """Optimal publishing schedule management"""
    __tablename__ = "publication_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Schedule identification
    name = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False)
    domain = Column(String(50))  # Domain-specific schedule
    
    # Schedule configuration
    timezone = Column(String(50), nullable=False, default='UTC')
    optimal_times = Column(JSON, nullable=False)  # Optimal posting times by day
    frequency_limits = Column(JSON)  # Max posts per day/hour
    
    # Audience analysis
    audience_analysis = Column(JSON)  # Audience activity patterns
    performance_data = Column(JSON)  # Historical performance by time
    
    # Schedule rules
    avoid_times = Column(JSON)  # Times to avoid posting
    priority_times = Column(JSON)  # Priority time slots
    buffer_minutes = Column(Integer, default=15)  # Buffer between posts
    
    # Status and usage
    is_active = Column(Boolean, default=True)
    last_optimization = Column(DateTime)
    total_scheduled = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PublicationAnalytics(Base):
    """Aggregated analytics for publication performance"""
    __tablename__ = "publication_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Analysis scope
    platform = Column(String(50))  # Specific platform or null for all
    domain = Column(String(50))    # Specific domain or null for all
    date_range_start = Column(DateTime, nullable=False)
    date_range_end = Column(DateTime, nullable=False)
    
    # Publication metrics
    total_publications = Column(Integer, default=0)
    successful_publications = Column(Integer, default=0)
    failed_publications = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Engagement metrics
    total_views = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    
    # Calculated performance metrics
    average_engagement_rate = Column(Float, default=0.0)
    average_click_through_rate = Column(Float, default=0.0)
    top_performing_time = Column(String(50))
    top_performing_day = Column(String(20))
    
    # Detailed analytics
    performance_breakdown = Column(JSON)  # Detailed performance data
    trend_analysis = Column(JSON)  # Trend analysis results
    recommendations = Column(JSON)  # Performance improvement recommendations
    
    # Analytics metadata
    analysis_type = Column(String(50))  # daily, weekly, monthly, custom
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_freshness = Column(DateTime)  # How fresh is the underlying data
    
    created_at = Column(DateTime, default=datetime.utcnow)
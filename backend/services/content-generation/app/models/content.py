"""
Content Generation Database Models
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from enum import Enum
from typing import Dict, Any, Optional

from ....shared.database import Base

class DomainType(str, Enum):
    FINANCE = "finance"
    SPORTS = "sports"
    TECHNOLOGY = "technology"
    GENERAL = "general"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated" 
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"

class GenerationRequest(Base):
    """Content generation request"""
    __tablename__ = "generation_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(50), nullable=False)
    source_content = Column(Text, nullable=False)
    source_url = Column(String(500))
    target_length = Column(Integer, default=1000)
    style_parameters = Column(JSON, nullable=False)  # Style configuration
    generation_settings = Column(JSON)  # Additional settings
    user_id = Column(UUID(as_uuid=True), nullable=False)
    workflow_id = Column(String(100))  # n8n workflow ID
    execution_id = Column(String(100))  # n8n execution ID
    priority = Column(String(20), default="normal")  # normal, high, urgent
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    content_items = relationship("ContentItem", back_populates="generation_request")

class ContentItem(Base):
    """Generated content item"""
    __tablename__ = "content_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_request_id = Column(UUID(as_uuid=True), ForeignKey("generation_requests.id"), nullable=False)
    
    # Content data
    title = Column(String(300))
    content = Column(Text, nullable=False)
    summary = Column(Text)
    word_count = Column(Integer)
    
    # Generation metadata
    model_used = Column(String(100))  # Claude model version
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    generation_time_seconds = Column(Float)
    api_cost_usd = Column(Float)
    
    # Content metadata
    domain = Column(String(50), nullable=False)
    style_applied = Column(JSON)  # Applied style parameters
    confidence_score = Column(Float)  # Generation confidence (0-1)
    status = Column(String(20), default=ContentStatus.GENERATED)
    
    # Quality indicators
    readability_score = Column(Float)  # Flesch reading ease
    originality_score = Column(Float)  # Content uniqueness (0-1)
    domain_relevance = Column(Float)  # Domain accuracy (0-1)
    overall_quality_score = Column(Float)  # Combined quality score
    
    # SEO and optimization
    meta_description = Column(Text)
    keywords = Column(JSON)  # Extracted keywords
    hashtags = Column(JSON)  # Generated hashtags
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    generation_request = relationship("GenerationRequest", back_populates="content_items")
    quality_analyses = relationship("QualityAnalysis", back_populates="content_item")

class ContentTemplate(Base):
    """Content generation templates"""
    __tablename__ = "content_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    domain = Column(String(50), nullable=False)
    description = Column(Text)
    
    # Template configuration
    prompt_template = Column(Text, nullable=False)  # Jinja2 template
    style_parameters = Column(JSON, nullable=False)  # Default style config
    content_structure = Column(JSON)  # Structure requirements
    
    # Template metadata
    category = Column(String(100))  # news, analysis, tutorial, etc.
    target_length_min = Column(Integer, default=500)
    target_length_max = Column(Integer, default=2000)
    complexity_level = Column(String(20), default="intermediate")  # beginner, intermediate, advanced
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Success rate of generations
    average_quality_score = Column(Float, default=0.0)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QualityAnalysis(Base):
    """Quality analysis results for generated content"""
    __tablename__ = "quality_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=False)
    
    # Quality scores
    overall_score = Column(Float, nullable=False)  # 0-1 overall quality
    readability_score = Column(Float)  # Reading ease
    originality_score = Column(Float)  # Content uniqueness
    accuracy_score = Column(Float)  # Factual accuracy
    engagement_score = Column(Float)  # Engagement potential
    seo_score = Column(Float)  # SEO optimization
    
    # Detailed analysis
    analysis_details = Column(JSON)  # Detailed breakdown
    improvement_suggestions = Column(JSON)  # Suggested improvements
    pattern_detection = Column(JSON)  # Detected patterns/issues
    
    # Analysis metadata
    analyzer_version = Column(String(50))
    analysis_time_seconds = Column(Float)
    model_used = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    content_item = relationship("ContentItem", back_populates="quality_analyses")

class StyleParameter(Base):
    """Style parameter configurations"""
    __tablename__ = "style_parameters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Parameter configuration
    parameter_type = Column(String(50), nullable=False)  # tone, structure, vocabulary, etc.
    possible_values = Column(JSON, nullable=False)  # List of possible values
    default_value = Column(String(200))
    randomization_enabled = Column(Boolean, default=True)
    randomization_weight = Column(Float, default=1.0)  # Weight for random selection
    
    # Domain-specific constraints
    constraints = Column(JSON)  # Validation rules and constraints
    dependencies = Column(JSON)  # Dependencies on other parameters
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GenerationHistory(Base):
    """Generation history for analytics and learning"""
    __tablename__ = "generation_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=False)
    
    # Performance metrics
    generation_success = Column(Boolean, nullable=False)
    quality_score = Column(Float)
    user_satisfaction = Column(Float)  # User feedback score
    publication_success = Column(Boolean)
    engagement_metrics = Column(JSON)  # Views, likes, shares, etc.
    
    # Learning data
    style_effectiveness = Column(JSON)  # Which styles worked best
    prompt_variations = Column(JSON)  # Prompt variations tried
    improvement_actions = Column(JSON)  # Actions taken for improvement
    
    created_at = Column(DateTime, default=datetime.utcnow)
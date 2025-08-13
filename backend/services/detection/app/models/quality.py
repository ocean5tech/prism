"""
Detection Service Database Models
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from enum import Enum

from ....shared.database import Base

class AnalysisType(str, Enum):
    QUALITY = "quality"
    PLAGIARISM = "plagiarism"
    PATTERN_DETECTION = "pattern_detection"
    SENTIMENT = "sentiment"
    READABILITY = "readability"
    SEO = "seo"
    COMPREHENSIVE = "comprehensive"

class PatternType(str, Enum):
    REPETITIVE_STRUCTURE = "repetitive_structure"
    REPETITIVE_PHRASES = "repetitive_phrases"
    TEMPLATE_OVERUSE = "template_overuse"
    STYLE_INCONSISTENCY = "style_inconsistency"
    LOW_VOCABULARY_DIVERSITY = "low_vocabulary_diversity"
    SUSPICIOUS_FORMATTING = "suspicious_formatting"

class QualityAnalysis(Base):
    """Quality analysis results for content"""
    __tablename__ = "quality_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(String(100), nullable=False, index=True)  # Reference to content
    content_text = Column(Text, nullable=False)  # Content being analyzed
    
    # Analysis configuration
    analysis_type = Column(String(50), nullable=False, default=AnalysisType.COMPREHENSIVE.value)
    domain = Column(String(50), nullable=False)
    source_url = Column(String(500))
    
    # Overall quality scores
    overall_score = Column(Float, nullable=False)  # 0-1 overall quality
    confidence_score = Column(Float, nullable=False)  # 0-1 confidence in analysis
    
    # Quality dimensions
    readability_score = Column(Float)  # Flesch reading ease
    originality_score = Column(Float)  # Content uniqueness (0-1)
    accuracy_score = Column(Float)  # Factual accuracy (0-1)
    engagement_score = Column(Float)  # Engagement potential (0-1)
    coherence_score = Column(Float)  # Logical flow and coherence (0-1)
    domain_relevance_score = Column(Float)  # Domain expertise relevance (0-1)
    seo_score = Column(Float)  # SEO optimization (0-1)
    
    # Detailed analysis results
    analysis_details = Column(JSON, nullable=False)  # Detailed breakdown
    improvement_suggestions = Column(JSON)  # Actionable improvements
    detected_issues = Column(JSON)  # Identified problems
    strengths = Column(JSON)  # Content strengths
    
    # Processing metadata
    analyzer_version = Column(String(50), nullable=False)
    analysis_time_seconds = Column(Float)
    model_used = Column(String(100))
    processing_flags = Column(JSON)  # Special processing notes
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pattern_detections = relationship("PatternDetection", back_populates="quality_analysis")
    plagiarism_checks = relationship("PlagiarismCheck", back_populates="quality_analysis")

class PatternDetection(Base):
    """Pattern detection for adversarial optimization"""
    __tablename__ = "pattern_detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quality_analysis_id = Column(UUID(as_uuid=True), ForeignKey("quality_analyses.id"), nullable=False)
    content_id = Column(String(100), nullable=False, index=True)
    
    # Pattern information
    pattern_type = Column(String(50), nullable=False)
    pattern_description = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0-1 confidence
    severity_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Pattern details
    detected_elements = Column(JSON, nullable=False)  # Specific pattern instances
    frequency_count = Column(Integer)  # How many times pattern appears
    pattern_locations = Column(JSON)  # Where in content pattern appears
    similarity_score = Column(Float)  # Similarity to known patterns
    
    # Context and impact
    impact_assessment = Column(JSON)  # Impact on content quality
    recommendation = Column(Text)  # How to address the pattern
    auto_fixable = Column(Boolean, default=False)  # Can be automatically fixed
    fix_suggestions = Column(JSON)  # Automatic fix suggestions
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    quality_analysis = relationship("QualityAnalysis", back_populates="pattern_detections")

class PlagiarismCheck(Base):
    """Plagiarism and similarity detection"""
    __tablename__ = "plagiarism_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quality_analysis_id = Column(UUID(as_uuid=True), ForeignKey("quality_analyses.id"), nullable=False)
    content_id = Column(String(100), nullable=False, index=True)
    
    # Similarity analysis
    similarity_score = Column(Float, nullable=False)  # 0-1 overall similarity
    originality_score = Column(Float, nullable=False)  # 1-similarity_score
    threshold_exceeded = Column(Boolean, nullable=False)  # Above plagiarism threshold
    
    # Source analysis
    sources_checked = Column(Integer, default=0)  # Number of sources checked
    similar_sources = Column(JSON)  # Sources with similarity
    exact_matches = Column(JSON)  # Exact text matches found
    paraphrasing_detected = Column(JSON)  # Paraphrased content detected
    
    # Detailed results
    similarity_breakdown = Column(JSON)  # Detailed similarity analysis
    risk_assessment = Column(String(20))  # low, medium, high, critical
    recommendations = Column(JSON)  # How to improve originality
    
    # Processing metadata
    check_method = Column(String(50))  # Method used for checking
    external_apis_used = Column(JSON)  # External services used
    processing_time_seconds = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    quality_analysis = relationship("QualityAnalysis", back_populates="plagiarism_checks")

class AdversarialFeedback(Base):
    """Feedback for adversarial optimization between Generation and Detection agents"""
    __tablename__ = "adversarial_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(String(100), nullable=False, index=True)
    generation_request_id = Column(String(100))  # Link to generation request
    quality_analysis_id = Column(UUID(as_uuid=True), ForeignKey("quality_analyses.id"))
    
    # Feedback type and content
    feedback_type = Column(String(50), nullable=False)  # improvement, warning, success
    feedback_message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Optimization data
    detected_weaknesses = Column(JSON, nullable=False)  # What needs improvement
    style_adjustments = Column(JSON)  # Suggested style changes
    prompt_modifications = Column(JSON)  # Suggested prompt changes
    parameter_tuning = Column(JSON)  # Parameter adjustment suggestions
    
    # Learning data for Generation Agent
    successful_patterns = Column(JSON)  # Patterns that worked well
    failed_patterns = Column(JSON)  # Patterns that didn't work
    quality_correlations = Column(JSON)  # Quality factors correlation
    
    # Action tracking
    action_taken = Column(String(100))  # Action taken based on feedback
    improvement_achieved = Column(Boolean)  # Whether improvement was achieved
    follow_up_required = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

class QualityThreshold(Base):
    """Quality thresholds for different domains and content types"""
    __tablename__ = "quality_thresholds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(50), nullable=False)
    content_type = Column(String(50), nullable=False)  # article, social_post, newsletter, etc.
    
    # Threshold configurations
    min_overall_score = Column(Float, nullable=False, default=0.7)
    min_readability_score = Column(Float, default=6.0)  # Flesch-Kincaid grade level
    min_originality_score = Column(Float, default=0.85)
    min_accuracy_score = Column(Float, default=0.9)
    min_engagement_score = Column(Float, default=0.6)
    min_coherence_score = Column(Float, default=0.8)
    min_domain_relevance = Column(Float, default=0.8)
    min_seo_score = Column(Float, default=0.7)
    
    # Pattern detection thresholds
    max_repetitive_patterns = Column(Integer, default=3)
    max_similarity_to_existing = Column(Float, default=0.3)
    max_template_reuse = Column(Float, default=0.4)
    
    # Configuration metadata
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # Higher priority overrides lower
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DetectionModel(Base):
    """Detection models and their configurations"""
    __tablename__ = "detection_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, unique=True)
    model_type = Column(String(50), nullable=False)  # quality, plagiarism, pattern, etc.
    model_version = Column(String(20), nullable=False)
    
    # Model configuration
    model_config = Column(JSON, nullable=False)  # Model parameters
    training_data_info = Column(JSON)  # Training data information
    performance_metrics = Column(JSON)  # Accuracy, precision, recall, etc.
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    average_processing_time = Column(Float)
    success_rate = Column(Float, default=1.0)
    
    # Model status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    deployment_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Maintenance
    next_retrain_date = Column(DateTime)
    performance_degradation_alert = Column(Boolean, default=False)

class ContentSimilarity(Base):
    """Content similarity matrix for pattern detection"""
    __tablename__ = "content_similarities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id_1 = Column(String(100), nullable=False, index=True)
    content_id_2 = Column(String(100), nullable=False, index=True)
    
    # Similarity metrics
    overall_similarity = Column(Float, nullable=False)  # 0-1 overall similarity
    structural_similarity = Column(Float)  # Document structure similarity
    semantic_similarity = Column(Float)  # Meaning similarity
    lexical_similarity = Column(Float)  # Word choice similarity
    style_similarity = Column(Float)  # Writing style similarity
    
    # Similarity details
    similar_phrases = Column(JSON)  # Phrases that are similar
    similar_structure_elements = Column(JSON)  # Structure elements
    confidence_score = Column(Float, nullable=False)
    
    # Processing metadata
    comparison_method = Column(String(50), nullable=False)
    model_used = Column(String(100))
    processing_time_seconds = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
"""
Detection Service API Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

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

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Request Schemas
class QualityAnalysisOptions(BaseModel):
    """Quality analysis configuration options"""
    check_plagiarism: bool = Field(default=True, description="Enable plagiarism detection")
    check_patterns: bool = Field(default=True, description="Enable pattern detection")
    check_domain_accuracy: bool = Field(default=True, description="Check domain-specific accuracy")
    check_compliance: bool = Field(default=False, description="Check regulatory compliance")
    check_sentiment: bool = Field(default=False, description="Analyze sentiment")
    check_readability: bool = Field(default=True, description="Analyze readability")
    check_seo: bool = Field(default=True, description="Check SEO optimization")
    
    # Thresholds
    plagiarism_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Plagiarism similarity threshold")
    pattern_sensitivity: float = Field(default=0.7, ge=0.0, le=1.0, description="Pattern detection sensitivity")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "check_plagiarism": True,
            "check_patterns": True,
            "check_domain_accuracy": True,
            "check_compliance": False,
            "plagiarism_threshold": 0.25,
            "pattern_sensitivity": 0.8
        }
    })

class QualityAnalysisRequest(BaseModel):
    """Quality analysis request schema"""
    content: str = Field(min_length=10, description="Content to analyze")
    content_id: Optional[str] = Field(None, description="Content identifier")
    domain: str = Field(description="Content domain")
    original_source: Optional[str] = Field(None, description="Original source URL")
    analysis_type: AnalysisType = Field(default=AnalysisType.COMPREHENSIVE, description="Type of analysis")
    analysis_options: QualityAnalysisOptions = Field(default_factory=QualityAnalysisOptions, description="Analysis options")
    
    # Context for analysis
    generation_context: Optional[Dict[str, Any]] = Field(None, description="Generation context")
    target_audience: Optional[str] = Field(None, description="Target audience")
    content_purpose: Optional[str] = Field(None, description="Content purpose")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content": "The cryptocurrency market has shown significant volatility in recent months, with Bitcoin experiencing both dramatic gains and losses...",
            "content_id": "content-123",
            "domain": "finance",
            "original_source": "https://example.com/crypto-news",
            "analysis_type": "comprehensive",
            "analysis_options": {
                "check_plagiarism": True,
                "check_patterns": True,
                "check_domain_accuracy": True,
                "plagiarism_threshold": 0.25
            }
        }
    })

# Response Schemas
class QualityScores(BaseModel):
    """Quality assessment scores"""
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Analysis confidence")
    readability_score: Optional[float] = Field(None, description="Readability score")
    originality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Content originality")
    accuracy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Factual accuracy")
    engagement_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Engagement potential")
    coherence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Logical coherence")
    domain_relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Domain relevance")
    seo_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="SEO optimization")

class PatternDetectionResult(BaseModel):
    """Pattern detection result"""
    pattern_type: PatternType = Field(description="Type of pattern detected")
    description: str = Field(description="Pattern description")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Detection confidence")
    severity_level: SeverityLevel = Field(description="Pattern severity")
    frequency_count: int = Field(description="Pattern frequency")
    locations: List[Dict[str, Any]] = Field(description="Pattern locations in content")
    recommendation: str = Field(description="Improvement recommendation")
    auto_fixable: bool = Field(description="Can be automatically fixed")
    fix_suggestions: Optional[List[str]] = Field(None, description="Fix suggestions")

class PlagiarismResult(BaseModel):
    """Plagiarism detection result"""
    similarity_score: float = Field(ge=0.0, le=1.0, description="Overall similarity score")
    originality_score: float = Field(ge=0.0, le=1.0, description="Originality score")
    threshold_exceeded: bool = Field(description="Threshold exceeded flag")
    risk_level: RiskLevel = Field(description="Plagiarism risk level")
    sources_checked: int = Field(description="Number of sources checked")
    similar_sources: List[Dict[str, Any]] = Field(description="Sources with similarity")
    exact_matches: List[Dict[str, str]] = Field(description="Exact text matches")
    recommendations: List[str] = Field(description="Improvement recommendations")

class ImprovementSuggestion(BaseModel):
    """Content improvement suggestion"""
    category: str = Field(description="Improvement category")
    priority: str = Field(description="Suggestion priority")
    description: str = Field(description="Improvement description")
    specific_changes: List[str] = Field(description="Specific change suggestions")
    expected_impact: float = Field(ge=0.0, le=1.0, description="Expected impact on quality")

class QualityAnalysisResponse(BaseModel):
    """Quality analysis response schema"""
    analysis_id: str = Field(description="Analysis identifier")
    content_id: Optional[str] = Field(None, description="Content identifier")
    domain: str = Field(description="Content domain")
    analysis_type: AnalysisType = Field(description="Analysis type performed")
    
    # Quality assessment
    quality_scores: QualityScores = Field(description="Quality scores")
    pass_threshold: bool = Field(description="Meets quality thresholds")
    
    # Detailed results
    detected_patterns: List[PatternDetectionResult] = Field(description="Detected patterns")
    plagiarism_results: Optional[PlagiarismResult] = Field(None, description="Plagiarism analysis")
    improvement_suggestions: List[ImprovementSuggestion] = Field(description="Improvement suggestions")
    
    # Content strengths and weaknesses
    strengths: List[str] = Field(description="Content strengths")
    weaknesses: List[str] = Field(description="Content weaknesses")
    
    # Processing metadata
    analysis_time_seconds: float = Field(description="Analysis processing time")
    model_used: str = Field(description="Analysis model used")
    analyzer_version: str = Field(description="Analyzer version")
    
    created_at: datetime = Field(description="Analysis timestamp")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "analysis_id": "analysis-123",
                "content_id": "content-123",
                "domain": "finance",
                "analysis_type": "comprehensive",
                "quality_scores": {
                    "overall_score": 0.85,
                    "confidence_score": 0.92,
                    "readability_score": 8.5,
                    "originality_score": 0.88,
                    "accuracy_score": 0.95,
                    "engagement_score": 0.78,
                    "domain_relevance_score": 0.91
                },
                "pass_threshold": True,
                "detected_patterns": [],
                "improvement_suggestions": [
                    {
                        "category": "readability",
                        "priority": "medium",
                        "description": "Consider shorter paragraphs",
                        "specific_changes": ["Break long paragraphs", "Use more transitions"],
                        "expected_impact": 0.15
                    }
                ],
                "strengths": ["Strong domain expertise", "Good factual accuracy"],
                "weaknesses": ["Could improve readability"],
                "analysis_time_seconds": 12.5,
                "model_used": "quality-analyzer-v2.0",
                "analyzer_version": "2.0.1",
                "created_at": "2025-08-08T10:30:00Z"
            }
        }
    )

class BatchAnalysisRequest(BaseModel):
    """Batch quality analysis request"""
    analyses: List[QualityAnalysisRequest] = Field(min_items=1, max_items=20, description="Batch analysis requests")
    batch_settings: Optional[Dict[str, Any]] = Field(None, description="Batch processing settings")

class BatchAnalysisResponse(BaseModel):
    """Batch analysis response"""
    batch_id: str = Field(description="Batch identifier")
    total_analyses: int = Field(description="Total number of analyses")
    successful_analyses: int = Field(description="Successful analyses count")
    failed_analyses: int = Field(description="Failed analyses count")
    results: List[QualityAnalysisResponse] = Field(description="Analysis results")
    processing_time_seconds: float = Field(description="Total processing time")

class AdversarialFeedbackRequest(BaseModel):
    """Adversarial feedback for Generation Agent"""
    content_id: str = Field(description="Content identifier")
    generation_request_id: Optional[str] = Field(None, description="Generation request ID")
    feedback_type: str = Field(description="Type of feedback")
    detected_weaknesses: Dict[str, Any] = Field(description="Detected weaknesses")
    style_adjustments: Optional[Dict[str, Any]] = Field(None, description="Style adjustment suggestions")
    prompt_modifications: Optional[Dict[str, Any]] = Field(None, description="Prompt modification suggestions")

class AdversarialFeedbackResponse(BaseModel):
    """Adversarial feedback response"""
    feedback_id: str = Field(description="Feedback identifier")
    content_id: str = Field(description="Content identifier")
    feedback_type: str = Field(description="Feedback type")
    severity: SeverityLevel = Field(description="Feedback severity")
    recommendations: List[str] = Field(description="Recommendations")
    learning_data: Dict[str, Any] = Field(description="Learning data for Generation Agent")
    created_at: datetime = Field(description="Feedback timestamp")

class ThresholdConfigRequest(BaseModel):
    """Quality threshold configuration request"""
    domain: str = Field(description="Domain name")
    content_type: str = Field(description="Content type")
    min_overall_score: float = Field(ge=0.0, le=1.0, description="Minimum overall score")
    min_readability_score: Optional[float] = Field(None, description="Minimum readability score")
    min_originality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum originality score")
    min_accuracy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum accuracy score")
    description: Optional[str] = Field(None, description="Threshold description")

class ThresholdConfigResponse(BaseModel):
    """Quality threshold configuration response"""
    id: str = Field(description="Threshold configuration ID")
    domain: str = Field(description="Domain name")
    content_type: str = Field(description="Content type")
    thresholds: Dict[str, float] = Field(description="Threshold values")
    is_active: bool = Field(description="Active status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
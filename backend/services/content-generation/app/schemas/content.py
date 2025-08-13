"""
Content Generation API Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid

class DomainType(str, Enum):
    FINANCE = "finance"
    SPORTS = "sports" 
    TECHNOLOGY = "technology"
    GENERAL = "general"

class PriorityLevel(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"

# Request Schemas
class StyleParametersSchema(BaseModel):
    """Style parameters for content generation"""
    tone: List[str] = Field(default=["neutral"], description="Content tone options")
    structure: List[str] = Field(default=["standard"], description="Content structure options")
    vocabulary: str = Field(default="general", description="Vocabulary complexity level")
    formality: str = Field(default="professional", description="Formality level")
    creativity_level: float = Field(default=0.7, ge=0.0, le=1.0, description="AI creativity level")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tone": ["professional", "engaging"],
            "structure": ["introduction", "main_points", "conclusion"],
            "vocabulary": "professional",
            "formality": "professional",
            "creativity_level": 0.8
        }
    })

class GenerationSettingsSchema(BaseModel):
    """Additional generation settings"""
    fact_check_required: bool = Field(default=False, description="Require fact checking")
    real_time_data: bool = Field(default=False, description="Use real-time data")
    include_statistics: bool = Field(default=True, description="Include relevant statistics")
    seo_optimize: bool = Field(default=True, description="Optimize for SEO")
    target_keywords: List[str] = Field(default_factory=list, description="Target SEO keywords")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "fact_check_required": True,
            "real_time_data": False,
            "include_statistics": True,
            "seo_optimize": True,
            "target_keywords": ["artificial intelligence", "machine learning"]
        }
    })

class ContentGenerationRequest(BaseModel):
    """Content generation request schema"""
    domain: DomainType = Field(description="Content domain")
    source_content: str = Field(min_length=10, description="Source content or topic")
    source_url: Optional[str] = Field(None, description="Source URL if available")
    target_length: int = Field(default=1000, ge=100, le=5000, description="Target word count")
    style_parameters: StyleParametersSchema = Field(description="Style configuration")
    generation_settings: Optional[GenerationSettingsSchema] = Field(None, description="Additional settings")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Generation priority")
    workflow_id: Optional[str] = Field(None, description="n8n workflow ID")
    execution_id: Optional[str] = Field(None, description="n8n execution ID")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "domain": "finance",
            "source_content": "Recent developments in cryptocurrency regulation and their impact on market stability",
            "source_url": "https://example.com/crypto-news",
            "target_length": 1200,
            "style_parameters": {
                "tone": ["analytical", "professional"],
                "structure": ["executive_summary", "analysis", "implications"],
                "vocabulary": "professional",
                "formality": "professional",
                "creativity_level": 0.6
            },
            "generation_settings": {
                "fact_check_required": True,
                "real_time_data": True,
                "include_statistics": True,
                "seo_optimize": True,
                "target_keywords": ["cryptocurrency", "regulation", "market stability"]
            },
            "priority": "high"
        }
    })

# Response Schemas
class QualityIndicators(BaseModel):
    """Content quality indicators"""
    readability_score: float = Field(description="Flesch reading ease score")
    originality_score: float = Field(ge=0.0, le=1.0, description="Content uniqueness score")
    domain_relevance: float = Field(ge=0.0, le=1.0, description="Domain relevance score")
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Generation confidence")

class GenerationMetadata(BaseModel):
    """Generation process metadata"""
    word_count: int = Field(description="Actual word count")
    generation_time: float = Field(description="Generation time in seconds")
    model_used: str = Field(description="AI model used")
    style_applied: Dict[str, Any] = Field(description="Applied style parameters")
    prompt_tokens: int = Field(description="Prompt tokens used")
    completion_tokens: int = Field(description="Completion tokens generated")
    total_tokens: int = Field(description="Total tokens used")
    api_cost_usd: Optional[float] = Field(None, description="API cost in USD")

class ContentGenerationResponse(BaseModel):
    """Content generation response schema"""
    content_id: str = Field(description="Generated content ID")
    title: Optional[str] = Field(None, description="Generated title")
    content: str = Field(description="Generated content")
    summary: Optional[str] = Field(None, description="Content summary")
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    hashtags: List[str] = Field(default_factory=list, description="Generated hashtags")
    
    metadata: GenerationMetadata = Field(description="Generation metadata")
    quality_indicators: QualityIndicators = Field(description="Quality assessment")
    
    status: ContentStatus = Field(description="Content status")
    created_at: datetime = Field(description="Creation timestamp")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "content_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Cryptocurrency Regulation: Market Impact and Future Implications",
                "content": "The cryptocurrency market continues to evolve...",
                "summary": "Analysis of recent cryptocurrency regulations...",
                "meta_description": "Comprehensive analysis of cryptocurrency regulation impacts on market stability and future investment strategies.",
                "keywords": ["cryptocurrency", "regulation", "market analysis"],
                "hashtags": ["#CryptoRegulation", "#MarketAnalysis", "#FinTech"],
                "metadata": {
                    "word_count": 1205,
                    "generation_time": 28.5,
                    "model_used": "claude-3-sonnet",
                    "style_applied": {"tone": "analytical", "formality": "professional"},
                    "prompt_tokens": 150,
                    "completion_tokens": 800,
                    "total_tokens": 950,
                    "api_cost_usd": 0.05
                },
                "quality_indicators": {
                    "readability_score": 8.5,
                    "originality_score": 0.95,
                    "domain_relevance": 0.88,
                    "overall_score": 0.91,
                    "confidence_score": 0.92
                },
                "status": "generated",
                "created_at": "2025-08-08T10:30:00Z"
            }
        }
    )

class BatchGenerationRequest(BaseModel):
    """Batch content generation request"""
    requests: List[ContentGenerationRequest] = Field(min_items=1, max_items=10, description="Batch of generation requests")
    batch_settings: Optional[Dict[str, Any]] = Field(None, description="Batch processing settings")
    
class BatchGenerationResponse(BaseModel):
    """Batch generation response"""
    batch_id: str = Field(description="Batch processing ID")
    total_requests: int = Field(description="Total number of requests")
    successful_generations: int = Field(description="Number of successful generations")
    failed_generations: int = Field(description="Number of failed generations")
    results: List[ContentGenerationResponse] = Field(description="Generation results")
    processing_time: float = Field(description="Total processing time in seconds")

# Template Schemas
class ContentTemplateRequest(BaseModel):
    """Content template creation request"""
    name: str = Field(min_length=1, max_length=200, description="Template name")
    domain: DomainType = Field(description="Template domain")
    description: Optional[str] = Field(None, description="Template description")
    prompt_template: str = Field(min_length=10, description="Jinja2 prompt template")
    style_parameters: StyleParametersSchema = Field(description="Default style parameters")
    content_structure: Dict[str, Any] = Field(description="Content structure requirements")
    category: Optional[str] = Field(None, description="Template category")
    target_length_min: int = Field(default=500, ge=100, description="Minimum target length")
    target_length_max: int = Field(default=2000, le=5000, description="Maximum target length")
    complexity_level: str = Field(default="intermediate", description="Content complexity level")

class ContentTemplateResponse(BaseModel):
    """Content template response"""
    id: str = Field(description="Template ID")
    name: str = Field(description="Template name")
    domain: DomainType = Field(description="Template domain")
    description: Optional[str] = Field(None, description="Template description")
    category: Optional[str] = Field(None, description="Template category")
    usage_count: int = Field(description="Template usage count")
    success_rate: float = Field(description="Generation success rate")
    average_quality_score: float = Field(description="Average quality score")
    is_active: bool = Field(description="Template active status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

# Style Parameter Schemas
class StyleParameterDefinition(BaseModel):
    """Style parameter definition"""
    name: str = Field(description="Parameter name")
    domain: DomainType = Field(description="Parameter domain")
    description: Optional[str] = Field(None, description="Parameter description")
    parameter_type: str = Field(description="Parameter type (tone, structure, etc.)")
    possible_values: List[str] = Field(description="Possible parameter values")
    default_value: str = Field(description="Default parameter value")
    randomization_enabled: bool = Field(default=True, description="Enable randomization")
    randomization_weight: float = Field(default=1.0, ge=0.0, description="Randomization weight")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Parameter constraints")

class GenerationStatusResponse(BaseModel):
    """Generation status response"""
    content_id: str = Field(description="Content ID")
    status: ContentStatus = Field(description="Current status")
    progress_percentage: float = Field(ge=0.0, le=100.0, description="Progress percentage")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    current_step: str = Field(description="Current processing step")
    error_message: Optional[str] = Field(None, description="Error message if failed")
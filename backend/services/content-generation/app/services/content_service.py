"""
Content Generation Service - Core Business Logic
"""
import asyncio
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import structlog
import re
from textstat import flesch_reading_ease
import keyword_extraction

from ..models import (
    GenerationRequest, 
    ContentItem, 
    ContentTemplate, 
    StyleParameter,
    GenerationHistory,
    DomainType,
    ContentStatus
)
from ..schemas import (
    ContentGenerationRequest,
    ContentGenerationResponse,
    QualityIndicators,
    GenerationMetadata,
    BatchGenerationRequest,
    BatchGenerationResponse
)
from .claude_client import ClaudeClient, ContentPromptBuilder
from ....shared.database import get_db_session, CacheManager
from ....shared.logging import ServiceLogger

logger = structlog.get_logger()
service_logger = ServiceLogger("content-generation")

class ContentGenerationError(Exception):
    """Custom exception for content generation errors"""
    pass

class ContentGenerationService:
    """Core content generation service"""
    
    def __init__(self):
        self.claude_client = ClaudeClient()
        self.prompt_builder = ContentPromptBuilder()
    
    async def generate_content(
        self,
        request: ContentGenerationRequest,
        user_id: str
    ) -> ContentGenerationResponse:
        """Generate content based on request parameters"""
        
        try:
            start_time = time.time()
            
            async with get_db_session() as db:
                # Create generation request record
                db_request = GenerationRequest(
                    domain=request.domain.value,
                    source_content=request.source_content,
                    source_url=request.source_url,
                    target_length=request.target_length,
                    style_parameters=request.style_parameters.dict(),
                    generation_settings=request.generation_settings.dict() if request.generation_settings else {},
                    user_id=user_id,
                    workflow_id=request.workflow_id,
                    execution_id=request.execution_id,
                    priority=request.priority.value
                )
                db.add(db_request)
                await db.flush()
                
                # Randomize style parameters for variation
                randomized_style = self.prompt_builder.randomize_style_parameters(
                    request.style_parameters.dict(),
                    request.domain.value
                )
                
                # Build prompt
                prompt, system_prompt = self.prompt_builder.build_content_prompt(
                    domain=request.domain.value,
                    source_content=request.source_content,
                    style_parameters=randomized_style,
                    target_length=request.target_length,
                    generation_settings=request.generation_settings.dict() if request.generation_settings else {}
                )
                
                # Generate content using Claude
                claude_response = await self.claude_client.generate_content(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=randomized_style.get("creativity_level", 0.7)
                )
                
                # Parse generated content
                content_data = self._parse_generated_content(claude_response["content"])
                
                # Calculate quality indicators
                quality_indicators = await self._calculate_quality_indicators(
                    content=content_data["content"],
                    domain=request.domain.value,
                    source_content=request.source_content
                )
                
                # Extract SEO data
                seo_data = self._extract_seo_data(
                    content_data["content"],
                    target_keywords=request.generation_settings.target_keywords if request.generation_settings else []
                )
                
                # Create content item record
                content_item = ContentItem(
                    generation_request_id=db_request.id,
                    title=content_data["title"],
                    content=content_data["content"],
                    summary=content_data.get("summary"),
                    word_count=len(content_data["content"].split()),
                    model_used=claude_response["model"],
                    prompt_tokens=claude_response["prompt_tokens"],
                    completion_tokens=claude_response["completion_tokens"],
                    total_tokens=claude_response["total_tokens"],
                    generation_time_seconds=claude_response["generation_time"],
                    api_cost_usd=claude_response["cost_usd"],
                    domain=request.domain.value,
                    style_applied=randomized_style,
                    confidence_score=quality_indicators["confidence_score"],
                    status=ContentStatus.GENERATED.value,
                    readability_score=quality_indicators["readability_score"],
                    originality_score=quality_indicators["originality_score"],
                    domain_relevance=quality_indicators["domain_relevance"],
                    overall_quality_score=quality_indicators["overall_score"],
                    meta_description=seo_data["meta_description"],
                    keywords=seo_data["keywords"],
                    hashtags=seo_data["hashtags"]
                )
                
                db.add(content_item)
                await db.commit()
                
                # Log generation
                service_logger.log_content_generation(
                    domain=request.domain.value,
                    word_count=content_item.word_count,
                    quality_score=quality_indicators["overall_score"],
                    generation_time=claude_response["generation_time"]
                )
                
                # Build response
                return ContentGenerationResponse(
                    content_id=str(content_item.id),
                    title=content_item.title,
                    content=content_item.content,
                    summary=content_item.summary,
                    meta_description=content_item.meta_description,
                    keywords=content_item.keywords,
                    hashtags=content_item.hashtags,
                    metadata=GenerationMetadata(
                        word_count=content_item.word_count,
                        generation_time=claude_response["generation_time"],
                        model_used=claude_response["model"],
                        style_applied=randomized_style,
                        prompt_tokens=claude_response["prompt_tokens"],
                        completion_tokens=claude_response["completion_tokens"],
                        total_tokens=claude_response["total_tokens"],
                        api_cost_usd=claude_response["cost_usd"]
                    ),
                    quality_indicators=QualityIndicators(**quality_indicators),
                    status=ContentStatus.GENERATED,
                    created_at=content_item.created_at
                )
                
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            raise ContentGenerationError(f"Generation failed: {str(e)}")
    
    async def generate_batch(
        self,
        request: BatchGenerationRequest,
        user_id: str
    ) -> BatchGenerationResponse:
        """Generate multiple content items in batch"""
        
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        results = []
        successful = 0
        failed = 0
        
        logger.info(f"Starting batch generation {batch_id} with {len(request.requests)} requests")
        
        # Process requests concurrently (but limited)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent generations
        
        async def generate_single(req):
            async with semaphore:
                try:
                    result = await self.generate_content(req, user_id)
                    return result, None
                except Exception as e:
                    return None, str(e)
        
        # Execute batch generation
        tasks = [generate_single(req) for req in request.requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                failed += 1
                logger.error(f"Batch item {i} failed: {str(response)}")
            else:
                result, error = response
                if result:
                    results.append(result)
                    successful += 1
                else:
                    failed += 1
                    logger.error(f"Batch item {i} failed: {error}")
        
        processing_time = time.time() - start_time
        
        logger.info(f"Batch {batch_id} completed: {successful} successful, {failed} failed")
        
        return BatchGenerationResponse(
            batch_id=batch_id,
            total_requests=len(request.requests),
            successful_generations=successful,
            failed_generations=failed,
            results=results,
            processing_time=processing_time
        )
    
    async def get_content_by_id(self, content_id: str) -> Optional[ContentGenerationResponse]:
        """Retrieve generated content by ID"""
        
        async with get_db_session() as db:
            result = await db.execute(
                select(ContentItem).where(ContentItem.id == content_id)
            )
            content_item = result.scalar_one_or_none()
            
            if not content_item:
                return None
            
            quality_indicators = QualityIndicators(
                readability_score=content_item.readability_score,
                originality_score=content_item.originality_score,
                domain_relevance=content_item.domain_relevance,
                overall_score=content_item.overall_quality_score,
                confidence_score=content_item.confidence_score
            )
            
            metadata = GenerationMetadata(
                word_count=content_item.word_count,
                generation_time=content_item.generation_time_seconds,
                model_used=content_item.model_used,
                style_applied=content_item.style_applied,
                prompt_tokens=content_item.prompt_tokens,
                completion_tokens=content_item.completion_tokens,
                total_tokens=content_item.total_tokens,
                api_cost_usd=content_item.api_cost_usd
            )
            
            return ContentGenerationResponse(
                content_id=str(content_item.id),
                title=content_item.title,
                content=content_item.content,
                summary=content_item.summary,
                meta_description=content_item.meta_description,
                keywords=content_item.keywords or [],
                hashtags=content_item.hashtags or [],
                metadata=metadata,
                quality_indicators=quality_indicators,
                status=ContentStatus(content_item.status),
                created_at=content_item.created_at
            )
    
    def _parse_generated_content(self, raw_content: str) -> Dict[str, str]:
        """Parse generated content to extract title and body"""
        
        lines = raw_content.strip().split('\n')
        title = ""
        content = ""
        summary = ""
        
        # Try to extract title (usually first line or has # marker)
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (line.startswith('#') or (i == 0 and len(line.split()) < 15)):
                title = line.replace('#', '').strip()
                content = '\n'.join(lines[i+1:]).strip()
                break
        
        if not title:
            # Fallback: use first sentence as title
            sentences = raw_content.split('.')
            if sentences:
                title = sentences[0][:200]
                content = raw_content[len(title):].strip()
        
        # Extract summary (first paragraph or explicit summary)
        paragraphs = content.split('\n\n')
        if paragraphs:
            summary = paragraphs[0][:300] + "..." if len(paragraphs[0]) > 300 else paragraphs[0]
        
        return {
            "title": title,
            "content": content,
            "summary": summary
        }
    
    async def _calculate_quality_indicators(
        self,
        content: str,
        domain: str,
        source_content: str
    ) -> Dict[str, float]:
        """Calculate quality indicators for generated content"""
        
        # Readability score (Flesch Reading Ease)
        try:
            readability_score = flesch_reading_ease(content)
        except:
            readability_score = 50.0  # Default medium readability
        
        # Originality score (simple similarity check for now)
        originality_score = await self._calculate_originality_score(content, source_content)
        
        # Domain relevance (keyword-based analysis)
        domain_relevance = self._calculate_domain_relevance(content, domain)
        
        # Confidence score (based on content structure and completeness)
        confidence_score = self._calculate_confidence_score(content)
        
        # Overall quality score (weighted average)
        overall_score = (
            (readability_score / 100) * 0.25 +  # Readability (0-1)
            originality_score * 0.30 +          # Originality (0-1)
            domain_relevance * 0.25 +           # Domain relevance (0-1)
            confidence_score * 0.20              # Confidence (0-1)
        )
        
        return {
            "readability_score": readability_score,
            "originality_score": originality_score,
            "domain_relevance": domain_relevance,
            "overall_score": min(1.0, overall_score),
            "confidence_score": confidence_score
        }
    
    async def _calculate_originality_score(self, content: str, source_content: str) -> float:
        """Calculate content originality score"""
        
        # Simple similarity check (can be enhanced with embedding-based similarity)
        content_words = set(content.lower().split())
        source_words = set(source_content.lower().split())
        
        if not content_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(content_words.intersection(source_words))
        union = len(content_words.union(source_words))
        
        similarity = intersection / union if union > 0 else 0
        originality = 1.0 - similarity
        
        return max(0.0, min(1.0, originality))
    
    def _calculate_domain_relevance(self, content: str, domain: str) -> float:
        """Calculate domain relevance score based on keywords"""
        
        content_lower = content.lower()
        
        # Domain-specific keywords
        domain_keywords = {
            "finance": [
                "investment", "market", "financial", "economy", "trading", "stocks",
                "portfolio", "risk", "return", "capital", "revenue", "profit", "loss",
                "assets", "liability", "cash flow", "budget", "currency", "inflation"
            ],
            "sports": [
                "game", "team", "player", "season", "championship", "tournament",
                "coach", "score", "match", "league", "athlete", "training", "performance",
                "victory", "defeat", "statistics", "strategy", "competition"
            ],
            "technology": [
                "software", "hardware", "innovation", "digital", "algorithm", "data",
                "artificial intelligence", "machine learning", "cloud", "cybersecurity",
                "development", "programming", "platform", "interface", "automation"
            ]
        }
        
        keywords = domain_keywords.get(domain, [])
        if not keywords:
            return 0.5  # Default relevance for unknown domains
        
        # Count keyword occurrences
        total_keywords = len(keywords)
        found_keywords = sum(1 for keyword in keywords if keyword in content_lower)
        
        relevance_score = found_keywords / total_keywords
        return min(1.0, relevance_score)
    
    def _calculate_confidence_score(self, content: str) -> float:
        """Calculate generation confidence score"""
        
        score = 0.0
        
        # Length check (reasonable length)
        word_count = len(content.split())
        if 100 <= word_count <= 3000:
            score += 0.3
        elif word_count > 50:
            score += 0.15
        
        # Structure check (multiple paragraphs)
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:
            score += 0.2
        elif len(paragraphs) >= 2:
            score += 0.1
        
        # Sentence variety (different sentence lengths)
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) >= 5:
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if lengths and max(lengths) - min(lengths) > 5:
                score += 0.2
        
        # Content quality indicators
        if not any(placeholder in content.lower() for placeholder in ['[placeholder]', 'lorem ipsum', 'todo']):
            score += 0.3
        
        return min(1.0, score)
    
    def _extract_seo_data(self, content: str, target_keywords: List[str] = None) -> Dict[str, Any]:
        """Extract SEO-related data from content"""
        
        # Generate meta description (first 150-160 characters of content)
        sentences = re.split(r'[.!?]+', content)
        meta_description = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if len(meta_description + sentence) < 155:
                meta_description += sentence + ". "
            else:
                break
        meta_description = meta_description.strip()
        
        # Extract keywords (simple frequency-based extraction)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords (excluding common words)
        common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'your'}
        keywords = [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10] if word not in common_words]
        
        # Include target keywords if provided
        if target_keywords:
            for keyword in target_keywords:
                if keyword.lower() not in [k.lower() for k in keywords]:
                    keywords.insert(0, keyword)
        
        # Generate hashtags from keywords
        hashtags = [f"#{word.capitalize()}" for word in keywords[:5]]
        
        return {
            "meta_description": meta_description,
            "keywords": keywords[:10],
            "hashtags": hashtags
        }
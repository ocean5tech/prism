"""
Detection Service - Main Business Logic Coordinator
"""
import asyncio
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, and_
import structlog

from ..models import (
    QualityAnalysis,
    PatternDetection, 
    PlagiarismCheck,
    AdversarialFeedback,
    QualityThreshold
)
from ..schemas import (
    QualityAnalysisRequest,
    QualityAnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    AdversarialFeedbackRequest,
    AdversarialFeedbackResponse,
    ThresholdConfigRequest,
    ThresholdConfigResponse,
    SeverityLevel
)
from .quality_analyzer import QualityAnalyzer
from ....shared.database import get_db_session, CacheManager
from ....shared.logging import ServiceLogger

logger = structlog.get_logger()
service_logger = ServiceLogger("detection-service")

class DetectionServiceError(Exception):
    """Custom exception for detection service errors"""
    pass

class DetectionService:
    """Main detection service coordinator"""
    
    def __init__(self):
        self.quality_analyzer = QualityAnalyzer()
        self.feedback_processor = AdversarialFeedbackProcessor()
    
    async def analyze_content(
        self, 
        request: QualityAnalysisRequest,
        user_id: str
    ) -> QualityAnalysisResponse:
        """Analyze content quality and store results"""
        
        try:
            start_time = time.time()
            
            # Perform quality analysis
            analysis_result = await self.quality_analyzer.analyze_quality(request)
            
            # Store analysis results in database
            analysis_id = await self._store_analysis_results(
                request, analysis_result, user_id
            )
            
            # Update analysis ID
            analysis_result.analysis_id = analysis_id
            
            # Generate adversarial feedback if quality is below threshold
            if not analysis_result.pass_threshold:
                await self._generate_adversarial_feedback(request, analysis_result)
            
            # Log the analysis
            service_logger.log_quality_analysis(
                content_id=request.content_id or "unknown",
                overall_score=analysis_result.quality_scores.overall_score,
                analysis_details={
                    "pass_threshold": analysis_result.pass_threshold,
                    "patterns_detected": len(analysis_result.detected_patterns),
                    "analysis_time": time.time() - start_time
                }
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            raise DetectionServiceError(f"Analysis failed: {str(e)}")
    
    async def analyze_batch(
        self,
        request: BatchAnalysisRequest,
        user_id: str
    ) -> BatchAnalysisResponse:
        """Analyze multiple content items in batch"""
        
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        results = []
        successful = 0
        failed = 0
        
        logger.info(f"Starting batch analysis {batch_id} with {len(request.analyses)} items")
        
        # Process analyses with concurrency control
        semaphore = asyncio.Semaphore(5)  # Limit concurrent analyses
        
        async def analyze_single(analysis_request):
            async with semaphore:
                try:
                    result = await self.analyze_content(analysis_request, user_id)
                    return result, None
                except Exception as e:
                    return None, str(e)
        
        # Execute batch analysis
        tasks = [analyze_single(req) for req in request.analyses]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                failed += 1
                logger.error(f"Batch analysis {i} failed: {str(response)}")
            else:
                result, error = response
                if result:
                    results.append(result)
                    successful += 1
                else:
                    failed += 1
                    logger.error(f"Batch analysis {i} failed: {error}")
        
        processing_time = time.time() - start_time
        
        logger.info(f"Batch {batch_id} completed: {successful} successful, {failed} failed")
        
        return BatchAnalysisResponse(
            batch_id=batch_id,
            total_analyses=len(request.analyses),
            successful_analyses=successful,
            failed_analyses=failed,
            results=results,
            processing_time_seconds=processing_time
        )
    
    async def get_analysis_by_id(self, analysis_id: str) -> Optional[QualityAnalysisResponse]:
        """Retrieve analysis results by ID"""
        
        async with get_db_session() as db:
            # Get main analysis
            result = await db.execute(
                select(QualityAnalysis).where(QualityAnalysis.id == analysis_id)
            )
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                return None
            
            # Get related pattern detections
            pattern_result = await db.execute(
                select(PatternDetection).where(PatternDetection.quality_analysis_id == analysis_id)
            )
            patterns = pattern_result.scalars().all()
            
            # Get plagiarism check if available
            plagiarism_result = await db.execute(
                select(PlagiarismCheck).where(PlagiarismCheck.quality_analysis_id == analysis_id)
            )
            plagiarism = plagiarism_result.scalar_one_or_none()
            
            # Convert to response schema
            return self._build_analysis_response(analysis, patterns, plagiarism)
    
    async def submit_adversarial_feedback(
        self,
        request: AdversarialFeedbackRequest,
        user_id: str
    ) -> AdversarialFeedbackResponse:
        """Submit feedback from Detection Agent to Generation Agent"""
        
        try:
            feedback_id = str(uuid.uuid4())
            
            # Process and validate feedback
            processed_feedback = await self.feedback_processor.process_feedback(request)
            
            # Store feedback in database
            async with get_db_session() as db:
                feedback_record = AdversarialFeedback(
                    content_id=request.content_id,
                    generation_request_id=request.generation_request_id,
                    feedback_type=request.feedback_type,
                    feedback_message=processed_feedback["message"],
                    severity=processed_feedback["severity"],
                    detected_weaknesses=request.detected_weaknesses,
                    style_adjustments=request.style_adjustments,
                    prompt_modifications=request.prompt_modifications,
                    parameter_tuning=processed_feedback.get("parameter_tuning", {}),
                    successful_patterns=processed_feedback.get("successful_patterns", {}),
                    failed_patterns=processed_feedback.get("failed_patterns", {}),
                    quality_correlations=processed_feedback.get("quality_correlations", {}),
                    action_taken="feedback_submitted",
                    improvement_achieved=False,
                    follow_up_required=processed_feedback.get("follow_up_required", False)
                )
                
                db.add(feedback_record)
                await db.commit()
                
                # Send feedback to Generation Service (via message queue or API)
                await self._send_feedback_to_generation_service(processed_feedback)
                
                return AdversarialFeedbackResponse(
                    feedback_id=feedback_id,
                    content_id=request.content_id,
                    feedback_type=request.feedback_type,
                    severity=SeverityLevel(processed_feedback["severity"]),
                    recommendations=processed_feedback.get("recommendations", []),
                    learning_data=processed_feedback.get("learning_data", {}),
                    created_at=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Adversarial feedback submission failed: {str(e)}")
            raise DetectionServiceError(f"Feedback submission failed: {str(e)}")
    
    async def configure_quality_thresholds(
        self,
        request: ThresholdConfigRequest,
        user_id: str
    ) -> ThresholdConfigResponse:
        """Configure quality thresholds for domain/content type"""
        
        try:
            async with get_db_session() as db:
                # Check if threshold configuration already exists
                existing_result = await db.execute(
                    select(QualityThreshold).where(
                        and_(
                            QualityThreshold.domain == request.domain,
                            QualityThreshold.content_type == request.content_type,
                            QualityThreshold.is_active == True
                        )
                    )
                )
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    # Update existing configuration
                    existing.min_overall_score = request.min_overall_score
                    existing.min_readability_score = request.min_readability_score
                    existing.min_originality_score = request.min_originality_score
                    existing.min_accuracy_score = request.min_accuracy_score
                    existing.description = request.description
                    existing.updated_at = datetime.utcnow()
                    
                    await db.commit()
                    config_id = str(existing.id)
                else:
                    # Create new configuration
                    new_threshold = QualityThreshold(
                        domain=request.domain,
                        content_type=request.content_type,
                        min_overall_score=request.min_overall_score,
                        min_readability_score=request.min_readability_score,
                        min_originality_score=request.min_originality_score,
                        min_accuracy_score=request.min_accuracy_score,
                        description=request.description,
                        is_active=True
                    )
                    
                    db.add(new_threshold)
                    await db.commit()
                    config_id = str(new_threshold.id)
                
                return ThresholdConfigResponse(
                    id=config_id,
                    domain=request.domain,
                    content_type=request.content_type,
                    thresholds={
                        "min_overall_score": request.min_overall_score,
                        "min_readability_score": request.min_readability_score,
                        "min_originality_score": request.min_originality_score,
                        "min_accuracy_score": request.min_accuracy_score
                    },
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Threshold configuration failed: {str(e)}")
            raise DetectionServiceError(f"Threshold configuration failed: {str(e)}")
    
    async def _store_analysis_results(
        self,
        request: QualityAnalysisRequest,
        result: QualityAnalysisResponse,
        user_id: str
    ) -> str:
        """Store analysis results in database"""
        
        async with get_db_session() as db:
            # Store main analysis
            analysis = QualityAnalysis(
                content_id=request.content_id or f"content-{int(time.time())}",
                content_text=request.content,
                analysis_type=request.analysis_type.value,
                domain=request.domain,
                source_url=request.original_source,
                overall_score=result.quality_scores.overall_score,
                confidence_score=result.quality_scores.confidence_score,
                readability_score=result.quality_scores.readability_score,
                originality_score=result.quality_scores.originality_score,
                accuracy_score=result.quality_scores.accuracy_score,
                engagement_score=result.quality_scores.engagement_score,
                coherence_score=result.quality_scores.coherence_score,
                domain_relevance_score=result.quality_scores.domain_relevance_score,
                seo_score=result.quality_scores.seo_score,
                analysis_details={
                    "strengths": result.strengths,
                    "weaknesses": result.weaknesses,
                    "pass_threshold": result.pass_threshold
                },
                improvement_suggestions=[s.dict() for s in result.improvement_suggestions],
                detected_issues=[p.dict() for p in result.detected_patterns],
                analyzer_version=result.analyzer_version,
                analysis_time_seconds=result.analysis_time_seconds,
                model_used=result.model_used
            )
            
            db.add(analysis)
            await db.flush()
            
            # Store pattern detections
            for pattern in result.detected_patterns:
                pattern_record = PatternDetection(
                    quality_analysis_id=analysis.id,
                    content_id=analysis.content_id,
                    pattern_type=pattern.pattern_type.value,
                    pattern_description=pattern.description,
                    confidence_score=pattern.confidence_score,
                    severity_level=pattern.severity_level.value,
                    detected_elements=pattern.locations,
                    frequency_count=pattern.frequency_count,
                    recommendation=pattern.recommendation,
                    auto_fixable=pattern.auto_fixable,
                    fix_suggestions=pattern.fix_suggestions
                )
                db.add(pattern_record)
            
            # Store plagiarism check if performed
            if result.plagiarism_results:
                plagiarism_record = PlagiarismCheck(
                    quality_analysis_id=analysis.id,
                    content_id=analysis.content_id,
                    similarity_score=result.plagiarism_results.similarity_score,
                    originality_score=result.plagiarism_results.originality_score,
                    threshold_exceeded=result.plagiarism_results.threshold_exceeded,
                    sources_checked=result.plagiarism_results.sources_checked,
                    similar_sources=result.plagiarism_results.similar_sources,
                    exact_matches=result.plagiarism_results.exact_matches,
                    risk_assessment=result.plagiarism_results.risk_level.value,
                    recommendations=result.plagiarism_results.recommendations,
                    check_method="automated",
                    processing_time_seconds=result.analysis_time_seconds
                )
                db.add(plagiarism_record)
            
            await db.commit()
            return str(analysis.id)
    
    async def _generate_adversarial_feedback(
        self,
        request: QualityAnalysisRequest,
        result: QualityAnalysisResponse
    ):
        """Generate adversarial feedback for low-quality content"""
        
        # Build feedback for Generation Agent
        detected_weaknesses = {}
        style_adjustments = {}
        
        # Analyze weaknesses and suggest improvements
        if result.quality_scores.readability_score and result.quality_scores.readability_score < 6.0:
            detected_weaknesses["readability"] = {
                "score": result.quality_scores.readability_score,
                "issue": "Content is too complex for target audience"
            }
            style_adjustments["sentence_complexity"] = "reduce"
        
        if result.quality_scores.originality_score and result.quality_scores.originality_score < 0.8:
            detected_weaknesses["originality"] = {
                "score": result.quality_scores.originality_score,
                "issue": "Content lacks originality"
            }
            style_adjustments["creativity_level"] = "increase"
        
        if detected_weaknesses:
            feedback_request = AdversarialFeedbackRequest(
                content_id=request.content_id or "unknown",
                generation_request_id=request.generation_context.get("request_id") if request.generation_context else None,
                feedback_type="quality_improvement",
                detected_weaknesses=detected_weaknesses,
                style_adjustments=style_adjustments
            )
            
            # Store feedback for later retrieval by Generation Service
            await self._store_feedback(feedback_request)
    
    async def _store_feedback(self, feedback_request: AdversarialFeedbackRequest):
        """Store adversarial feedback for Generation Service"""
        
        async with get_db_session() as db:
            feedback = AdversarialFeedback(
                content_id=feedback_request.content_id,
                generation_request_id=feedback_request.generation_request_id,
                feedback_type=feedback_request.feedback_type,
                feedback_message="Quality improvement required",
                severity="medium",
                detected_weaknesses=feedback_request.detected_weaknesses,
                style_adjustments=feedback_request.style_adjustments,
                prompt_modifications=feedback_request.prompt_modifications,
                action_taken="feedback_generated",
                follow_up_required=True
            )
            
            db.add(feedback)
            await db.commit()
    
    async def _send_feedback_to_generation_service(self, feedback_data: Dict[str, Any]):
        """Send feedback to Generation Service"""
        # TODO: Implement actual communication with Generation Service
        # This could be via message queue, webhook, or direct API call
        logger.info("Sending feedback to Generation Service", feedback_data=feedback_data)
    
    def _build_analysis_response(
        self,
        analysis: QualityAnalysis,
        patterns: List[PatternDetection],
        plagiarism: Optional[PlagiarismCheck]
    ) -> QualityAnalysisResponse:
        """Build analysis response from database records"""
        
        # Convert pattern detections
        pattern_results = []
        for pattern in patterns:
            pattern_results.append(PatternDetectionResult(
                pattern_type=PatternType(pattern.pattern_type),
                description=pattern.pattern_description,
                confidence_score=pattern.confidence_score,
                severity_level=SeverityLevel(pattern.severity_level),
                frequency_count=pattern.frequency_count,
                locations=pattern.detected_elements or [],
                recommendation=pattern.recommendation,
                auto_fixable=pattern.auto_fixable,
                fix_suggestions=pattern.fix_suggestions or []
            ))
        
        # Convert plagiarism check
        plagiarism_result = None
        if plagiarism:
            plagiarism_result = PlagiarismResult(
                similarity_score=plagiarism.similarity_score,
                originality_score=plagiarism.originality_score,
                threshold_exceeded=plagiarism.threshold_exceeded,
                risk_level=RiskLevel(plagiarism.risk_assessment),
                sources_checked=plagiarism.sources_checked,
                similar_sources=plagiarism.similar_sources or [],
                exact_matches=plagiarism.exact_matches or [],
                recommendations=plagiarism.recommendations or []
            )
        
        return QualityAnalysisResponse(
            analysis_id=str(analysis.id),
            content_id=analysis.content_id,
            domain=analysis.domain,
            analysis_type=AnalysisType(analysis.analysis_type),
            quality_scores=QualityScores(
                overall_score=analysis.overall_score,
                confidence_score=analysis.confidence_score,
                readability_score=analysis.readability_score,
                originality_score=analysis.originality_score,
                accuracy_score=analysis.accuracy_score,
                engagement_score=analysis.engagement_score,
                coherence_score=analysis.coherence_score,
                domain_relevance_score=analysis.domain_relevance_score,
                seo_score=analysis.seo_score
            ),
            pass_threshold=analysis.analysis_details.get("pass_threshold", False),
            detected_patterns=pattern_results,
            plagiarism_results=plagiarism_result,
            improvement_suggestions=[ImprovementSuggestion(**s) for s in analysis.improvement_suggestions or []],
            strengths=analysis.analysis_details.get("strengths", []),
            weaknesses=analysis.analysis_details.get("weaknesses", []),
            analysis_time_seconds=analysis.analysis_time_seconds,
            model_used=analysis.model_used,
            analyzer_version=analysis.analyzer_version,
            created_at=analysis.created_at
        )

class AdversarialFeedbackProcessor:
    """Process adversarial feedback between Detection and Generation agents"""
    
    async def process_feedback(self, request: AdversarialFeedbackRequest) -> Dict[str, Any]:
        """Process and enhance feedback for Generation Agent"""
        
        processed = {
            "message": self._generate_feedback_message(request),
            "severity": self._calculate_severity(request),
            "recommendations": self._generate_recommendations(request),
            "learning_data": self._extract_learning_data(request),
            "parameter_tuning": self._suggest_parameter_tuning(request),
            "follow_up_required": True
        }
        
        return processed
    
    def _generate_feedback_message(self, request: AdversarialFeedbackRequest) -> str:
        """Generate human-readable feedback message"""
        
        weaknesses = request.detected_weaknesses
        message_parts = []
        
        if "readability" in weaknesses:
            message_parts.append("Content readability needs improvement")
        
        if "originality" in weaknesses:
            message_parts.append("Content originality is below standards")
        
        if "accuracy" in weaknesses:
            message_parts.append("Factual accuracy requires attention")
        
        if not message_parts:
            return "General quality improvement needed"
        
        return "; ".join(message_parts)
    
    def _calculate_severity(self, request: AdversarialFeedbackRequest) -> str:
        """Calculate feedback severity based on detected issues"""
        
        weaknesses = request.detected_weaknesses
        critical_issues = 0
        
        for weakness, details in weaknesses.items():
            if isinstance(details, dict) and "score" in details:
                score = details["score"]
                if weakness == "readability" and score < 4.0:
                    critical_issues += 1
                elif weakness == "originality" and score < 0.6:
                    critical_issues += 1
                elif weakness == "accuracy" and score < 0.7:
                    critical_issues += 1
        
        if critical_issues >= 2:
            return "high"
        elif critical_issues >= 1:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, request: AdversarialFeedbackRequest) -> List[str]:
        """Generate specific recommendations for improvement"""
        
        recommendations = []
        weaknesses = request.detected_weaknesses
        
        if "readability" in weaknesses:
            recommendations.extend([
                "Use shorter, clearer sentences",
                "Reduce complex vocabulary",
                "Break up long paragraphs"
            ])
        
        if "originality" in weaknesses:
            recommendations.extend([
                "Increase creativity parameters",
                "Use more unique examples and insights",
                "Reduce reliance on common phrases"
            ])
        
        if "accuracy" in weaknesses:
            recommendations.extend([
                "Include more fact-checking",
                "Use domain-specific expertise",
                "Verify statistical claims"
            ])
        
        return recommendations
    
    def _extract_learning_data(self, request: AdversarialFeedbackRequest) -> Dict[str, Any]:
        """Extract learning data for Generation Agent improvement"""
        
        return {
            "failed_patterns": request.detected_weaknesses,
            "style_adjustments_needed": request.style_adjustments or {},
            "quality_correlations": {
                "weakness_count": len(request.detected_weaknesses),
                "adjustment_types": list((request.style_adjustments or {}).keys())
            }
        }
    
    def _suggest_parameter_tuning(self, request: AdversarialFeedbackRequest) -> Dict[str, Any]:
        """Suggest parameter adjustments for Generation Agent"""
        
        tuning = {}
        adjustments = request.style_adjustments or {}
        
        if "sentence_complexity" in adjustments:
            if adjustments["sentence_complexity"] == "reduce":
                tuning["creativity_level"] = "decrease_by_0.1"
        
        if "creativity_level" in adjustments:
            if adjustments["creativity_level"] == "increase":
                tuning["creativity_level"] = "increase_by_0.2"
        
        return tuning
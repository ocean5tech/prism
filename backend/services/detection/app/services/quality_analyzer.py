"""
Quality Analysis Engine for Content Detection
"""
import asyncio
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import textstat
from textblob import TextBlob
import structlog

from ..schemas import (
    QualityAnalysisRequest,
    QualityAnalysisResponse,
    QualityScores,
    PatternDetectionResult,
    PlagiarismResult,
    ImprovementSuggestion,
    AnalysisType,
    PatternType,
    SeverityLevel,
    RiskLevel
)
from ....shared.database import get_db_session, CacheManager
from ....shared.logging import ServiceLogger

logger = structlog.get_logger()
service_logger = ServiceLogger("quality-analyzer")

class QualityAnalyzer:
    """Advanced quality analysis engine"""
    
    def __init__(self):
        # Initialize ML models
        self.sentence_transformer = None  # Lazy load
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 3)
        )
        
        # Domain-specific keywords and patterns
        self.domain_keywords = self._load_domain_keywords()
        self.quality_patterns = self._load_quality_patterns()
        
        # Quality thresholds
        self.default_thresholds = {
            "min_overall_score": 0.7,
            "min_readability": 6.0,  # Grade level
            "min_originality": 0.85,
            "min_accuracy": 0.9,
            "min_engagement": 0.6,
            "min_coherence": 0.8,
            "min_domain_relevance": 0.8,
            "min_seo": 0.7
        }
    
    async def analyze_quality(self, request: QualityAnalysisRequest) -> QualityAnalysisResponse:
        """Perform comprehensive quality analysis"""
        
        start_time = time.time()
        analysis_id = f"analysis-{int(time.time() * 1000)}"
        
        try:
            # Initialize analysis results
            quality_scores = await self._calculate_quality_scores(request)
            detected_patterns = await self._detect_patterns(request)
            plagiarism_results = None
            
            if request.analysis_options.check_plagiarism:
                plagiarism_results = await self._check_plagiarism(request)
            
            # Generate improvement suggestions
            improvement_suggestions = await self._generate_suggestions(
                request, quality_scores, detected_patterns, plagiarism_results
            )
            
            # Identify strengths and weaknesses
            strengths, weaknesses = self._analyze_strengths_weaknesses(
                quality_scores, detected_patterns
            )
            
            # Check if content passes thresholds
            pass_threshold = self._check_thresholds(quality_scores, request.domain)
            
            processing_time = time.time() - start_time
            
            # Log analysis
            service_logger.log_quality_analysis(
                content_id=request.content_id or "unknown",
                overall_score=quality_scores.overall_score,
                analysis_details={
                    "patterns_detected": len(detected_patterns),
                    "pass_threshold": pass_threshold,
                    "processing_time": processing_time
                }
            )
            
            return QualityAnalysisResponse(
                analysis_id=analysis_id,
                content_id=request.content_id,
                domain=request.domain,
                analysis_type=request.analysis_type,
                quality_scores=quality_scores,
                pass_threshold=pass_threshold,
                detected_patterns=detected_patterns,
                plagiarism_results=plagiarism_results,
                improvement_suggestions=improvement_suggestions,
                strengths=strengths,
                weaknesses=weaknesses,
                analysis_time_seconds=processing_time,
                model_used="quality-analyzer-v2.0",
                analyzer_version="2.0.1",
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Quality analysis failed: {str(e)}")
            raise
    
    async def _calculate_quality_scores(self, request: QualityAnalysisRequest) -> QualityScores:
        """Calculate comprehensive quality scores"""
        
        content = request.content
        domain = request.domain
        
        # Readability analysis
        readability_score = self._calculate_readability(content)
        
        # Originality analysis
        originality_score = await self._calculate_originality(content, request.original_source)
        
        # Accuracy analysis (domain-specific)
        accuracy_score = self._calculate_accuracy(content, domain)
        
        # Engagement potential
        engagement_score = self._calculate_engagement_potential(content)
        
        # Coherence analysis
        coherence_score = self._calculate_coherence(content)
        
        # Domain relevance
        domain_relevance_score = self._calculate_domain_relevance(content, domain)
        
        # SEO analysis
        seo_score = self._calculate_seo_score(content)
        
        # Overall quality (weighted average)
        overall_score = self._calculate_overall_score({
            "readability": readability_score,
            "originality": originality_score,
            "accuracy": accuracy_score,
            "engagement": engagement_score,
            "coherence": coherence_score,
            "domain_relevance": domain_relevance_score,
            "seo": seo_score
        })
        
        # Confidence based on analysis completeness and consistency
        confidence_score = self._calculate_confidence_score(content, {
            "readability": readability_score,
            "originality": originality_score,
            "accuracy": accuracy_score
        })
        
        return QualityScores(
            overall_score=overall_score,
            confidence_score=confidence_score,
            readability_score=readability_score,
            originality_score=originality_score,
            accuracy_score=accuracy_score,
            engagement_score=engagement_score,
            coherence_score=coherence_score,
            domain_relevance_score=domain_relevance_score,
            seo_score=seo_score
        )
    
    def _calculate_readability(self, content: str) -> float:
        """Calculate readability score using multiple metrics"""
        
        try:
            # Flesch Reading Ease
            flesch_score = textstat.flesch_reading_ease(content)
            
            # Flesch-Kincaid Grade Level
            grade_level = textstat.flesch_kincaid_grade(content)
            
            # Average sentence length
            sentences = textstat.sentence_count(content)
            words = textstat.word_count(content)
            avg_sentence_length = words / sentences if sentences > 0 else 0
            
            # Combine metrics (normalize Flesch score to 0-10 scale)
            normalized_flesch = max(0, min(10, flesch_score / 10))
            
            # Penalize very high or very low grade levels
            grade_penalty = 0
            if grade_level > 15 or grade_level < 6:
                grade_penalty = 0.5
            
            readability = max(0, normalized_flesch - grade_penalty)
            return round(readability, 2)
            
        except Exception:
            return 5.0  # Default medium readability
    
    async def _calculate_originality(self, content: str, source_url: Optional[str] = None) -> float:
        """Calculate content originality score"""
        
        try:
            # Check cache for similar content
            content_hash = str(hash(content))
            cache_key = f"originality:{content_hash}"
            cached_score = await CacheManager.get(cache_key)
            
            if cached_score:
                return float(cached_score)
            
            # For now, use simple similarity checks
            # TODO: Implement vector database similarity search
            
            # Check for common phrases and templates
            common_phrases = [
                "in this article", "in this post", "we will discuss",
                "it is important to note", "in conclusion", "to summarize"
            ]
            
            content_lower = content.lower()
            common_phrase_count = sum(1 for phrase in common_phrases if phrase in content_lower)
            
            # Basic originality score (can be enhanced with embeddings)
            originality = max(0.5, 1.0 - (common_phrase_count * 0.1))
            
            # Cache result
            await CacheManager.set(cache_key, str(originality), expire=3600)
            
            return round(originality, 3)
            
        except Exception:
            return 0.8  # Default originality
    
    def _calculate_accuracy(self, content: str, domain: str) -> float:
        """Calculate domain-specific accuracy score"""
        
        try:
            # Domain-specific fact patterns
            domain_patterns = {
                "finance": {
                    "positive": ["market analysis", "financial data", "investment", "portfolio", "risk assessment"],
                    "negative": ["guaranteed returns", "no risk", "get rich quick"]
                },
                "sports": {
                    "positive": ["statistics", "performance", "team analysis", "player stats", "game results"],
                    "negative": ["100% prediction", "sure bet", "guaranteed win"]
                },
                "technology": {
                    "positive": ["technical specifications", "research", "development", "innovation", "data"],
                    "negative": ["magic solution", "instant fix", "no limitations"]
                }
            }
            
            patterns = domain_patterns.get(domain, {"positive": [], "negative": []})
            content_lower = content.lower()
            
            positive_count = sum(1 for pattern in patterns["positive"] if pattern in content_lower)
            negative_count = sum(1 for pattern in patterns["negative"] if pattern in content_lower)
            
            # Calculate accuracy score
            accuracy = 0.8  # Base accuracy
            accuracy += positive_count * 0.05  # Boost for positive patterns
            accuracy -= negative_count * 0.2   # Penalty for negative patterns
            
            return round(max(0.0, min(1.0, accuracy)), 3)
            
        except Exception:
            return 0.8  # Default accuracy
    
    def _calculate_engagement_potential(self, content: str) -> float:
        """Calculate content engagement potential"""
        
        try:
            # Factors that affect engagement
            word_count = len(content.split())
            sentence_count = len([s for s in content.split('.') if s.strip()])
            paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
            
            # Question count (engaging)
            question_count = content.count('?')
            
            # Sentiment analysis
            try:
                blob = TextBlob(content)
                sentiment_polarity = abs(blob.sentiment.polarity)  # More extreme = more engaging
            except:
                sentiment_polarity = 0.0
            
            # Calculate engagement factors
            engagement = 0.5  # Base engagement
            
            # Optimal word count (800-2000 words)
            if 800 <= word_count <= 2000:
                engagement += 0.2
            elif word_count < 500 or word_count > 3000:
                engagement -= 0.1
            
            # Questions boost engagement
            engagement += min(0.15, question_count * 0.03)
            
            # Sentiment impact
            engagement += sentiment_polarity * 0.1
            
            # Paragraph structure
            if paragraph_count >= 3:
                engagement += 0.1
            
            return round(max(0.0, min(1.0, engagement)), 3)
            
        except Exception:
            return 0.6  # Default engagement
    
    def _calculate_coherence(self, content: str) -> float:
        """Calculate logical coherence score"""
        
        try:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            if len(paragraphs) < 2:
                return 0.6  # Single paragraph, limited coherence assessment
            
            coherence = 0.7  # Base coherence
            
            # Check for transition words
            transitions = [
                "however", "therefore", "moreover", "furthermore", "additionally",
                "consequently", "meanwhile", "similarly", "on the other hand", "in contrast"
            ]
            
            content_lower = content.lower()
            transition_count = sum(1 for transition in transitions if transition in content_lower)
            
            # Boost for transitions
            coherence += min(0.2, transition_count * 0.02)
            
            # Check paragraph length consistency
            paragraph_lengths = [len(p.split()) for p in paragraphs]
            if paragraph_lengths:
                length_variance = np.var(paragraph_lengths)
                if length_variance < 1000:  # Consistent paragraph lengths
                    coherence += 0.1
            
            return round(max(0.0, min(1.0, coherence)), 3)
            
        except Exception:
            return 0.7  # Default coherence
    
    def _calculate_domain_relevance(self, content: str, domain: str) -> float:
        """Calculate domain relevance score"""
        
        try:
            domain_keywords = self.domain_keywords.get(domain, [])
            if not domain_keywords:
                return 0.5  # No keywords available
            
            content_lower = content.lower()
            
            # Count keyword occurrences
            keyword_matches = 0
            for keyword in domain_keywords:
                if keyword.lower() in content_lower:
                    keyword_matches += 1
            
            # Calculate relevance
            relevance = keyword_matches / len(domain_keywords)
            
            # Apply bonus for multiple occurrences
            word_count = len(content.split())
            keyword_density = keyword_matches / word_count if word_count > 0 else 0
            
            if keyword_density > 0.01:  # Good keyword density
                relevance += 0.1
            
            return round(max(0.0, min(1.0, relevance)), 3)
            
        except Exception:
            return 0.7  # Default relevance
    
    def _calculate_seo_score(self, content: str) -> float:
        """Calculate SEO optimization score"""
        
        try:
            seo_score = 0.5  # Base SEO score
            
            # Word count optimization
            word_count = len(content.split())
            if 300 <= word_count <= 3000:
                seo_score += 0.2
            
            # Header structure (check for potential headers)
            lines = content.split('\n')
            potential_headers = sum(1 for line in lines if len(line.split()) < 10 and line.isupper())
            if potential_headers > 0:
                seo_score += 0.1
            
            # Keyword density check (avoid keyword stuffing)
            words = content.lower().split()
            if words:
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                max_frequency = max(word_freq.values())
                keyword_density = max_frequency / len(words)
                
                if 0.01 <= keyword_density <= 0.03:  # Optimal keyword density
                    seo_score += 0.2
                elif keyword_density > 0.05:  # Keyword stuffing penalty
                    seo_score -= 0.1
            
            return round(max(0.0, min(1.0, seo_score)), 3)
            
        except Exception:
            return 0.6  # Default SEO score
    
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall quality score"""
        
        weights = {
            "readability": 0.15,
            "originality": 0.25,
            "accuracy": 0.20,
            "engagement": 0.15,
            "coherence": 0.10,
            "domain_relevance": 0.10,
            "seo": 0.05
        }
        
        overall = 0.0
        for metric, score in scores.items():
            weight = weights.get(metric, 0.0)
            if metric == "readability":
                # Normalize readability to 0-1 scale
                normalized_score = score / 10.0
            else:
                normalized_score = score
            
            overall += normalized_score * weight
        
        return round(max(0.0, min(1.0, overall)), 3)
    
    def _calculate_confidence_score(self, content: str, scores: Dict[str, float]) -> float:
        """Calculate confidence in the analysis"""
        
        confidence = 0.8  # Base confidence
        
        # Content length affects confidence
        word_count = len(content.split())
        if word_count < 100:
            confidence -= 0.2  # Less confident with short content
        elif word_count > 200:
            confidence += 0.1  # More confident with longer content
        
        # Score consistency affects confidence
        score_values = [v for v in scores.values() if v is not None]
        if score_values:
            score_variance = np.var(score_values)
            if score_variance < 0.05:  # Consistent scores
                confidence += 0.1
        
        return round(max(0.0, min(1.0, confidence)), 3)
    
    async def _detect_patterns(self, request: QualityAnalysisRequest) -> List[PatternDetectionResult]:
        """Detect patterns that indicate quality issues"""
        
        if not request.analysis_options.check_patterns:
            return []
        
        patterns = []
        content = request.content
        
        # Repetitive phrases detection
        repetitive_patterns = self._detect_repetitive_phrases(content)
        patterns.extend(repetitive_patterns)
        
        # Repetitive structure detection
        structure_patterns = self._detect_repetitive_structure(content)
        patterns.extend(structure_patterns)
        
        # Template overuse detection
        template_patterns = self._detect_template_overuse(content, request.domain)
        patterns.extend(template_patterns)
        
        # Style inconsistency detection
        style_patterns = self._detect_style_inconsistency(content)
        patterns.extend(style_patterns)
        
        return patterns
    
    def _detect_repetitive_phrases(self, content: str) -> List[PatternDetectionResult]:
        """Detect repetitive phrases in content"""
        
        patterns = []
        
        # Split into sentences
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        
        # Find repeated phrases (3+ words)
        phrases = []
        for sentence in sentences:
            words = sentence.split()
            for i in range(len(words) - 2):
                phrase = ' '.join(words[i:i+3]).lower()
                phrases.append(phrase)
        
        # Count phrase frequencies
        phrase_counts = {}
        for phrase in phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Find repetitive phrases
        repetitive = {phrase: count for phrase, count in phrase_counts.items() if count >= 3}
        
        if repetitive:
            severity = SeverityLevel.HIGH if len(repetitive) > 5 else SeverityLevel.MEDIUM
            
            patterns.append(PatternDetectionResult(
                pattern_type=PatternType.REPETITIVE_PHRASES,
                description=f"Found {len(repetitive)} repetitive phrases",
                confidence_score=0.9,
                severity_level=severity,
                frequency_count=sum(repetitive.values()),
                locations=[{"phrase": phrase, "count": count} for phrase, count in repetitive.items()],
                recommendation="Vary phrase usage to improve content flow",
                auto_fixable=True,
                fix_suggestions=["Replace repeated phrases with synonyms", "Restructure sentences"]
            ))
        
        return patterns
    
    def _detect_repetitive_structure(self, content: str) -> List[PatternDetectionResult]:
        """Detect repetitive structural patterns"""
        
        patterns = []
        
        # Analyze paragraph structures
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if len(paragraphs) < 3:
            return patterns
        
        # Analyze paragraph starting patterns
        starting_words = []
        for paragraph in paragraphs:
            first_sentence = paragraph.split('.')[0]
            first_word = first_sentence.split()[0].lower() if first_sentence.split() else ""
            starting_words.append(first_word)
        
        # Count repetitive starts
        word_counts = {}
        for word in starting_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        repetitive_starts = {word: count for word, count in word_counts.items() if count >= 3}
        
        if repetitive_starts:
            patterns.append(PatternDetectionResult(
                pattern_type=PatternType.REPETITIVE_STRUCTURE,
                description="Repetitive paragraph starting patterns detected",
                confidence_score=0.8,
                severity_level=SeverityLevel.MEDIUM,
                frequency_count=sum(repetitive_starts.values()),
                locations=[{"starting_word": word, "count": count} for word, count in repetitive_starts.items()],
                recommendation="Vary paragraph structures and starting words",
                auto_fixable=True,
                fix_suggestions=["Use different transition words", "Vary sentence structures"]
            ))
        
        return patterns
    
    def _detect_template_overuse(self, content: str, domain: str) -> List[PatternDetectionResult]:
        """Detect overuse of templates or formulaic content"""
        
        patterns = []
        
        # Common template phrases by domain
        template_phrases = {
            "finance": [
                "it is important to note that",
                "investors should be aware",
                "market conditions suggest",
                "financial experts recommend"
            ],
            "sports": [
                "the team performed well",
                "fans will be excited",
                "the season looks promising",
                "statistics show that"
            ],
            "technology": [
                "this technology represents",
                "users will benefit from",
                "the innovation provides",
                "developers have created"
            ]
        }
        
        domain_templates = template_phrases.get(domain, [])
        content_lower = content.lower()
        
        found_templates = []
        for template in domain_templates:
            if template in content_lower:
                found_templates.append(template)
        
        if len(found_templates) >= 3:  # Multiple templates used
            patterns.append(PatternDetectionResult(
                pattern_type=PatternType.TEMPLATE_OVERUSE,
                description="Overuse of template phrases detected",
                confidence_score=0.85,
                severity_level=SeverityLevel.HIGH,
                frequency_count=len(found_templates),
                locations=[{"template": template} for template in found_templates],
                recommendation="Reduce reliance on template phrases, use more original language",
                auto_fixable=True,
                fix_suggestions=["Replace template phrases with original content", "Vary language patterns"]
            ))
        
        return patterns
    
    def _detect_style_inconsistency(self, content: str) -> List[PatternDetectionResult]:
        """Detect style inconsistencies in content"""
        
        patterns = []
        
        # Analyze sentence length variation
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        if len(sentences) < 5:
            return patterns
        
        sentence_lengths = [len(s.split()) for s in sentences]
        
        # Check for extreme variation or lack of variation
        length_variance = np.var(sentence_lengths)
        avg_length = np.mean(sentence_lengths)
        
        if length_variance < 5:  # Very consistent lengths - potentially robotic
            patterns.append(PatternDetectionResult(
                pattern_type=PatternType.STYLE_INCONSISTENCY,
                description="Very uniform sentence lengths detected",
                confidence_score=0.7,
                severity_level=SeverityLevel.MEDIUM,
                frequency_count=len(sentences),
                locations=[{"avg_length": avg_length, "variance": length_variance}],
                recommendation="Vary sentence lengths for better flow",
                auto_fixable=True,
                fix_suggestions=["Combine short sentences", "Break up long sentences"]
            ))
        
        return patterns
    
    async def _check_plagiarism(self, request: QualityAnalysisRequest) -> PlagiarismResult:
        """Check content for plagiarism"""
        
        # For demo purposes - implement actual plagiarism checking
        similarity_score = await self._calculate_content_similarity(
            request.content, 
            request.original_source
        )
        
        threshold_exceeded = similarity_score > request.analysis_options.plagiarism_threshold
        originality_score = 1.0 - similarity_score
        
        risk_level = RiskLevel.LOW
        if similarity_score > 0.7:
            risk_level = RiskLevel.CRITICAL
        elif similarity_score > 0.5:
            risk_level = RiskLevel.HIGH
        elif similarity_score > 0.3:
            risk_level = RiskLevel.MEDIUM
        
        return PlagiarismResult(
            similarity_score=similarity_score,
            originality_score=originality_score,
            threshold_exceeded=threshold_exceeded,
            risk_level=risk_level,
            sources_checked=1,
            similar_sources=[],
            exact_matches=[],
            recommendations=["Paraphrase similar sections", "Add more original content"]
        )
    
    async def _calculate_content_similarity(self, content: str, source_url: Optional[str]) -> float:
        """Calculate similarity to potential sources"""
        
        # Simple similarity for demo - implement vector-based similarity
        if not source_url:
            return 0.1  # Low similarity if no source to compare
        
        # TODO: Implement actual similarity calculation using embeddings
        return 0.15  # Placeholder similarity score
    
    async def _generate_suggestions(
        self, 
        request: QualityAnalysisRequest,
        quality_scores: QualityScores,
        patterns: List[PatternDetectionResult],
        plagiarism: Optional[PlagiarismResult]
    ) -> List[ImprovementSuggestion]:
        """Generate improvement suggestions based on analysis"""
        
        suggestions = []
        
        # Readability suggestions
        if quality_scores.readability_score and quality_scores.readability_score < 6.0:
            suggestions.append(ImprovementSuggestion(
                category="readability",
                priority="high",
                description="Content readability can be improved",
                specific_changes=[
                    "Use shorter sentences",
                    "Break up long paragraphs",
                    "Use simpler vocabulary where appropriate"
                ],
                expected_impact=0.2
            ))
        
        # Originality suggestions
        if quality_scores.originality_score and quality_scores.originality_score < 0.8:
            suggestions.append(ImprovementSuggestion(
                category="originality",
                priority="high",
                description="Content originality should be improved",
                specific_changes=[
                    "Add more unique insights",
                    "Reduce use of common phrases",
                    "Include original examples or case studies"
                ],
                expected_impact=0.25
            ))
        
        # Pattern-based suggestions
        for pattern in patterns:
            if pattern.severity_level in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                suggestions.append(ImprovementSuggestion(
                    category="patterns",
                    priority="high",
                    description=f"Address {pattern.pattern_type.value}",
                    specific_changes=pattern.fix_suggestions or [],
                    expected_impact=0.15
                ))
        
        # Engagement suggestions
        if quality_scores.engagement_score and quality_scores.engagement_score < 0.7:
            suggestions.append(ImprovementSuggestion(
                category="engagement",
                priority="medium",
                description="Content engagement potential can be enhanced",
                specific_changes=[
                    "Add relevant questions to engage readers",
                    "Include compelling examples or stories",
                    "Use more active voice"
                ],
                expected_impact=0.18
            ))
        
        return suggestions
    
    def _analyze_strengths_weaknesses(
        self, 
        quality_scores: QualityScores, 
        patterns: List[PatternDetectionResult]
    ) -> Tuple[List[str], List[str]]:
        """Identify content strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        
        # Analyze individual scores
        if quality_scores.accuracy_score and quality_scores.accuracy_score > 0.9:
            strengths.append("High factual accuracy")
        elif quality_scores.accuracy_score and quality_scores.accuracy_score < 0.7:
            weaknesses.append("Factual accuracy needs improvement")
        
        if quality_scores.originality_score and quality_scores.originality_score > 0.9:
            strengths.append("Highly original content")
        elif quality_scores.originality_score and quality_scores.originality_score < 0.8:
            weaknesses.append("Content originality could be improved")
        
        if quality_scores.domain_relevance_score and quality_scores.domain_relevance_score > 0.85:
            strengths.append("Strong domain expertise demonstrated")
        elif quality_scores.domain_relevance_score and quality_scores.domain_relevance_score < 0.7:
            weaknesses.append("Domain relevance needs improvement")
        
        if quality_scores.coherence_score and quality_scores.coherence_score > 0.8:
            strengths.append("Good logical flow and coherence")
        elif quality_scores.coherence_score and quality_scores.coherence_score < 0.7:
            weaknesses.append("Content coherence could be improved")
        
        # Pattern-based weaknesses
        high_severity_patterns = [p for p in patterns if p.severity_level in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]]
        if high_severity_patterns:
            weaknesses.append(f"Contains {len(high_severity_patterns)} significant pattern issues")
        
        # Overall assessment
        if quality_scores.overall_score > 0.85:
            strengths.append("Overall high-quality content")
        elif quality_scores.overall_score < 0.7:
            weaknesses.append("Overall quality needs significant improvement")
        
        return strengths, weaknesses
    
    def _check_thresholds(self, quality_scores: QualityScores, domain: str) -> bool:
        """Check if content meets quality thresholds"""
        
        thresholds = self.default_thresholds  # TODO: Load domain-specific thresholds
        
        # Check each threshold
        if quality_scores.overall_score < thresholds["min_overall_score"]:
            return False
        
        if quality_scores.readability_score and quality_scores.readability_score < thresholds["min_readability"]:
            return False
        
        if quality_scores.originality_score and quality_scores.originality_score < thresholds["min_originality"]:
            return False
        
        if quality_scores.accuracy_score and quality_scores.accuracy_score < thresholds["min_accuracy"]:
            return False
        
        return True
    
    def _load_domain_keywords(self) -> Dict[str, List[str]]:
        """Load domain-specific keywords for relevance analysis"""
        return {
            "finance": [
                "investment", "market", "portfolio", "risk", "return", "capital",
                "revenue", "profit", "assets", "liability", "equity", "trading",
                "stocks", "bonds", "derivatives", "inflation", "interest", "currency"
            ],
            "sports": [
                "team", "player", "game", "season", "championship", "tournament",
                "coach", "training", "performance", "statistics", "league", "match",
                "score", "victory", "strategy", "competition", "athlete", "fitness"
            ],
            "technology": [
                "software", "hardware", "algorithm", "data", "system", "platform",
                "development", "innovation", "digital", "cloud", "security", "AI",
                "machine learning", "automation", "interface", "programming"
            ]
        }
    
    def _load_quality_patterns(self) -> Dict[str, Any]:
        """Load quality patterns for detection"""
        return {
            "template_phrases": [
                "it is important to note",
                "in this article we will",
                "let's take a look at"
            ],
            "weak_transitions": [
                "also", "and", "but", "so"
            ],
            "filler_words": [
                "really", "very", "quite", "rather", "somewhat"
            ]
        }
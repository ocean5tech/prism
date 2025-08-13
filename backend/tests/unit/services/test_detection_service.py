"""
Unit Tests for Detection Service (Adversarial Quality Control)
Tests the quality analysis, pattern detection, and content validation functionality
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.services.detection.app.services.detection_service import DetectionService
from backend.services.detection.app.services.quality_analyzer import QualityAnalyzer
from backend.services.detection.app.schemas.quality import (
    QualityAnalysisRequest,
    QualityAnalysisResponse, 
    PatternDetectionResult,
    ContentMetrics
)


class TestDetectionService:
    """Test suite for DetectionService"""
    
    @pytest.fixture
    async def detection_service(self, db_session, redis_client):
        """Create DetectionService instance for testing"""
        return DetectionService(db_session, redis_client)
    
    @pytest.fixture
    def sample_analysis_request(self, generate_test_content):
        """Sample quality analysis request"""
        return QualityAnalysisRequest(
            content_id="test_content_123",
            content=generate_test_content("finance", 1000),
            domain="finance",
            expected_quality_threshold=85.0,
            analysis_type="comprehensive"
        )
    
    @pytest.mark.unit
    async def test_quality_analysis_comprehensive(self, detection_service, sample_analysis_request, quality_thresholds):
        """Test comprehensive quality analysis"""
        start_time = time.time()
        
        result = await detection_service.analyze_content_quality(sample_analysis_request)
        
        end_time = time.time()
        
        # Basic response validation
        assert isinstance(result, QualityAnalysisResponse)
        assert result.content_id == sample_analysis_request.content_id
        assert result.overall_quality_score is not None
        
        # Quality metrics validation
        assert result.metrics is not None
        assert "readability_score" in result.metrics
        assert "uniqueness_score" in result.metrics
        assert "domain_accuracy" in result.metrics
        assert "seo_score" in result.metrics
        assert "plagiarism_score" in result.metrics
        
        # Score range validation
        assert 0 <= result.overall_quality_score <= 100
        assert 0 <= result.metrics["uniqueness_score"] <= 100
        assert 0 <= result.metrics["domain_accuracy"] <= 100
        
        # Performance validation
        analysis_time = end_time - start_time
        assert analysis_time <= 5.0  # Analysis should complete within 5 seconds
    
    @pytest.mark.unit
    @pytest.mark.parametrize("domain", ["finance", "sports", "technology"])
    async def test_domain_specific_analysis(self, detection_service, domain, domain_test_data):
        """Test domain-specific quality analysis"""
        domain_data = domain_test_data[domain]
        content = generate_test_content(domain, 800)
        
        request = QualityAnalysisRequest(
            content_id=f"test_{domain}_content",
            content=content,
            domain=domain,
            analysis_type="domain_focused"
        )
        
        result = await detection_service.analyze_content_quality(request)
        
        # Domain-specific validation
        assert result.domain == domain
        assert result.metrics["domain_accuracy"] >= domain_data["accuracy_threshold"]
        
        # Domain-specific terminology check
        domain_score = await detection_service._calculate_domain_relevance(content, domain)
        assert domain_score >= 0.7  # Minimum domain relevance
    
    @pytest.mark.unit
    async def test_pattern_detection(self, detection_service):
        """Test pattern detection for repetitive content"""
        # Create content with obvious patterns
        repetitive_content = """
        This is a test article. The market analysis shows positive trends.
        This is a test article. The market analysis shows positive trends.
        The financial data indicates growth. The investment outlook is favorable.
        The financial data indicates growth. The investment outlook is favorable.
        """
        
        request = QualityAnalysisRequest(
            content_id="pattern_test",
            content=repetitive_content,
            domain="finance",
            analysis_type="pattern_detection"
        )
        
        result = await detection_service.analyze_content_quality(request)
        
        # Pattern detection should identify repetition
        assert result.patterns_detected is True
        assert len(result.detected_patterns) > 0
        assert result.pattern_severity in ["low", "medium", "high"]
        
        # Quality score should be penalized for patterns
        assert result.overall_quality_score < 70  # Should be marked as low quality
    
    @pytest.mark.unit
    async def test_uniqueness_analysis(self, detection_service, db_session):
        """Test content uniqueness against existing corpus"""
        # First, store some reference content
        reference_content = "The stock market showed significant volatility in Q3 2024."
        await detection_service._store_content_fingerprint(reference_content, "finance")
        
        # Test similar content
        similar_content = "The stock market demonstrated considerable volatility in Q3 2024."
        similar_request = QualityAnalysisRequest(
            content_id="similarity_test",
            content=similar_content,
            domain="finance",
            analysis_type="uniqueness"
        )
        
        result = await detection_service.analyze_content_quality(similar_request)
        
        # Should detect similarity
        assert result.metrics["uniqueness_score"] < 90  # Should be marked as similar
        assert result.similarity_matches is not None
        assert len(result.similarity_matches) > 0
    
    @pytest.mark.unit
    async def test_seo_analysis(self, detection_service):
        """Test SEO quality analysis"""
        seo_optimized_content = """
        Investment Strategies for 2024: A Comprehensive Market Analysis
        
        The financial markets in 2024 present unique investment opportunities. 
        Market analysis reveals key trends for investors seeking growth.
        Investment portfolios should diversify across multiple sectors.
        Financial planning requires careful market assessment and risk evaluation.
        
        Key Investment Strategies:
        1. Diversified portfolio management
        2. Market timing considerations
        3. Risk assessment protocols
        
        Conclusion: Strategic investment approaches yield better market returns.
        """
        
        request = QualityAnalysisRequest(
            content_id="seo_test",
            content=seo_optimized_content,
            domain="finance",
            analysis_type="seo_focused",
            target_keywords=["investment", "market", "analysis", "financial"]
        )
        
        result = await detection_service.analyze_content_quality(request)
        
        # SEO metrics validation
        assert result.metrics["seo_score"] >= 75  # Good SEO score
        assert result.seo_analysis is not None
        assert "keyword_density" in result.seo_analysis
        assert "readability" in result.seo_analysis
        assert "structure_score" in result.seo_analysis
    
    @pytest.mark.unit
    async def test_quality_improvement_suggestions(self, detection_service):
        """Test generation of quality improvement suggestions"""
        low_quality_content = "market go up. stock good. buy now. profit."
        
        request = QualityAnalysisRequest(
            content_id="improvement_test",
            content=low_quality_content,
            domain="finance",
            analysis_type="comprehensive",
            generate_suggestions=True
        )
        
        result = await detection_service.analyze_content_quality(request)
        
        # Should generate improvement suggestions
        assert result.improvement_suggestions is not None
        assert len(result.improvement_suggestions) > 0
        
        # Suggestions should be categorized
        suggestion_categories = [s.get("category") for s in result.improvement_suggestions]
        expected_categories = ["readability", "domain_accuracy", "seo", "structure"]
        assert any(cat in suggestion_categories for cat in expected_categories)
    
    @pytest.mark.unit
    async def test_plagiarism_detection(self, detection_service):
        """Test plagiarism detection against external sources"""
        with patch('backend.services.detection.app.services.detection_service.PlagiarismChecker') as mock_checker:
            # Mock plagiarism check result
            mock_checker.return_value.check_plagiarism.return_value = {
                "plagiarism_score": 15.5,
                "matches": [
                    {"source": "example.com", "similarity": 0.8, "matched_text": "sample text"}
                ]
            }
            
            request = QualityAnalysisRequest(
                content_id="plagiarism_test",
                content="This is some content to test for plagiarism detection.",
                domain="technology",
                analysis_type="plagiarism_check"
            )
            
            result = await detection_service.analyze_content_quality(request)
            
            # Plagiarism metrics validation
            assert result.metrics["plagiarism_score"] == 15.5
            assert result.plagiarism_matches is not None
            assert len(result.plagiarism_matches) > 0
    
    @pytest.mark.unit
    async def test_batch_analysis_performance(self, detection_service):
        """Test batch quality analysis performance"""
        requests = []
        for i in range(10):
            content = generate_test_content("finance", 500)
            requests.append(QualityAnalysisRequest(
                content_id=f"batch_test_{i}",
                content=content,
                domain="finance",
                analysis_type="fast"
            ))
        
        start_time = time.time()
        results = await detection_service.analyze_batch_content(requests)
        end_time = time.time()
        
        # Verify all analyses completed
        assert len(results) == len(requests)
        for result in results:
            assert result.overall_quality_score is not None
        
        # Performance check - batch should be efficient
        total_time = end_time - start_time
        avg_time_per_analysis = total_time / len(requests)
        assert avg_time_per_analysis <= 2.0  # Should be under 2s per analysis in batch
    
    @pytest.mark.unit
    async def test_error_handling_invalid_content(self, detection_service):
        """Test error handling for invalid content"""
        invalid_requests = [
            # Empty content
            QualityAnalysisRequest(
                content_id="empty_test",
                content="",
                domain="finance"
            ),
            # Content too short
            QualityAnalysisRequest(
                content_id="short_test", 
                content="Too short.",
                domain="finance"
            ),
            # Invalid domain
            QualityAnalysisRequest(
                content_id="invalid_domain_test",
                content="Valid content for testing purposes.",
                domain="invalid_domain"
            )
        ]
        
        for request in invalid_requests:
            with pytest.raises(HTTPException) as exc_info:
                await detection_service.analyze_content_quality(request)
            
            assert exc_info.value.status_code in [400, 422]  # Bad request or validation error


class TestQualityAnalyzer:
    """Test suite for QualityAnalyzer utility class"""
    
    @pytest.fixture
    def quality_analyzer(self):
        """Create QualityAnalyzer instance for testing"""
        return QualityAnalyzer()
    
    @pytest.mark.unit
    def test_readability_scoring(self, quality_analyzer):
        """Test readability scoring algorithms"""
        test_texts = [
            # Simple text
            {
                "text": "The cat sat on the mat. It was a sunny day. Birds sang in the trees.",
                "expected_range": (80, 100)  # High readability
            },
            # Complex text
            {
                "text": "The multifaceted economic implications of quantitative easing necessitate comprehensive analysis of monetary policy ramifications across diverse market segments.",
                "expected_range": (30, 60)  # Lower readability
            },
            # Balanced text
            {
                "text": "Market analysis shows positive trends in technology stocks. Investors should consider diversification strategies. Risk management remains crucial for portfolio success.",
                "expected_range": (60, 85)  # Moderate readability
            }
        ]
        
        for test_case in test_texts:
            score = quality_analyzer.calculate_readability_score(test_case["text"])
            min_score, max_score = test_case["expected_range"]
            
            assert min_score <= score <= max_score, f"Readability score {score} not in expected range {test_case['expected_range']}"
    
    @pytest.mark.unit
    def test_keyword_density_analysis(self, quality_analyzer):
        """Test keyword density calculation"""
        text = "Investment strategies for market analysis. Investment planning requires market research. Strategic investment approaches improve market performance."
        target_keywords = ["investment", "market", "strategic"]
        
        density_analysis = quality_analyzer.analyze_keyword_density(text, target_keywords)
        
        # Verify analysis structure
        assert "total_words" in density_analysis
        assert "keyword_counts" in density_analysis
        assert "density_percentages" in density_analysis
        
        # Verify keyword detection
        assert density_analysis["keyword_counts"]["investment"] >= 3
        assert density_analysis["keyword_counts"]["market"] >= 3
        assert density_analysis["keyword_counts"]["strategic"] >= 1
        
        # Verify density calculations
        for keyword in target_keywords:
            expected_density = (density_analysis["keyword_counts"][keyword] / density_analysis["total_words"]) * 100
            assert abs(density_analysis["density_percentages"][keyword] - expected_density) < 0.01
    
    @pytest.mark.unit
    def test_sentence_structure_analysis(self, quality_analyzer):
        """Test sentence structure and complexity analysis"""
        test_cases = [
            {
                "text": "This is simple. Each sentence is short. Easy to read.",
                "expected_complexity": "low"
            },
            {
                "text": "The comprehensive market analysis, which encompasses various economic indicators and financial metrics, demonstrates that investment strategies must be carefully calibrated to account for market volatility and risk management principles.",
                "expected_complexity": "high"
            }
        ]
        
        for test_case in test_cases:
            analysis = quality_analyzer.analyze_sentence_structure(test_case["text"])
            
            assert "avg_sentence_length" in analysis
            assert "complexity_level" in analysis
            assert "sentence_count" in analysis
            
            assert analysis["complexity_level"] == test_case["expected_complexity"]
    
    @pytest.mark.unit
    def test_domain_terminology_scoring(self, quality_analyzer):
        """Test domain-specific terminology scoring"""
        domain_texts = {
            "finance": "The portfolio's diversification strategy includes equity investments, bond allocations, and derivatives trading to optimize risk-adjusted returns.",
            "sports": "The quarterback's completion percentage improved after the coaching staff implemented new offensive formations and receiving route combinations.",
            "technology": "The microservice architecture leverages containerization and API gateways to enable scalable distributed system deployment."
        }
        
        for domain, text in domain_texts.items():
            score = quality_analyzer.calculate_domain_terminology_score(text, domain)
            
            # Domain-specific text should score highly for its domain
            assert score >= 0.7, f"Domain terminology score {score} too low for {domain} content"
            
            # Should score lower for other domains
            for other_domain in domain_texts.keys():
                if other_domain != domain:
                    other_score = quality_analyzer.calculate_domain_terminology_score(text, other_domain)
                    assert other_score < score, f"Cross-domain scoring issue: {other_domain} scored {other_score} vs {domain} scored {score}"


class TestAdversarialFeedbackLoop:
    """Test adversarial feedback loop between generation and detection"""
    
    @pytest.mark.unit
    async def test_feedback_loop_integration(self, detection_service, db_session):
        """Test feedback loop improves content quality over iterations"""
        # Simulate multiple iterations of content generation and detection
        initial_content = "Basic market analysis shows stock trends."
        
        quality_scores = []
        content_iterations = [initial_content]
        
        for iteration in range(3):
            # Analyze current content
            request = QualityAnalysisRequest(
                content_id=f"feedback_test_{iteration}",
                content=content_iterations[-1],
                domain="finance",
                analysis_type="comprehensive",
                generate_suggestions=True
            )
            
            analysis = await detection_service.analyze_content_quality(request)
            quality_scores.append(analysis.overall_quality_score)
            
            # Simulate improved content based on suggestions
            if iteration < 2:  # Don't generate new content on last iteration
                improved_content = await detection_service.generate_improved_content(
                    content_iterations[-1],
                    analysis.improvement_suggestions
                )
                content_iterations.append(improved_content)
        
        # Quality should improve over iterations
        assert len(quality_scores) == 3
        assert quality_scores[1] > quality_scores[0], "Quality should improve after first iteration"
        assert quality_scores[2] > quality_scores[1], "Quality should continue improving"
    
    @pytest.mark.unit
    async def test_pattern_learning_and_avoidance(self, detection_service):
        """Test that detection service learns to identify new patterns"""
        # Submit content with subtle patterns
        pattern_contents = [
            "Market trends show positive indicators. Financial analysis reveals growth potential.",
            "Market indicators show positive trends. Financial research reveals growth opportunity.",
            "Market signals show positive direction. Financial evaluation reveals growth prospects."
        ]
        
        pattern_scores = []
        for i, content in enumerate(pattern_contents):
            request = QualityAnalysisRequest(
                content_id=f"pattern_learning_{i}",
                content=content,
                domain="finance",
                analysis_type="pattern_detection"
            )
            
            result = await detection_service.analyze_content_quality(request)
            pattern_scores.append(result.overall_quality_score)
        
        # Later submissions with similar patterns should receive lower scores
        assert pattern_scores[2] < pattern_scores[0], "Detection should learn to penalize repeated patterns"


# Integration tests with external services
@pytest.mark.integration
class TestDetectionServiceIntegration:
    """Integration tests for detection service"""
    
    @pytest.mark.requires_external
    async def test_real_time_quality_monitoring(self, detection_service):
        """Test real-time quality monitoring integration"""
        # This would integrate with actual monitoring systems
        content = generate_test_content("finance", 1000)
        
        request = QualityAnalysisRequest(
            content_id="monitoring_test",
            content=content,
            domain="finance",
            analysis_type="real_time"
        )
        
        result = await detection_service.analyze_content_quality(request)
        
        # Verify monitoring data was recorded
        assert result.monitoring_data is not None
        assert "timestamp" in result.monitoring_data
        assert "processing_time" in result.monitoring_data
    
    @pytest.mark.requires_external  
    async def test_vector_similarity_search(self, detection_service):
        """Test vector database integration for similarity search"""
        content = "Advanced investment strategies for portfolio optimization."
        
        request = QualityAnalysisRequest(
            content_id="vector_test",
            content=content,
            domain="finance",
            analysis_type="similarity_search"
        )
        
        result = await detection_service.analyze_content_quality(request)
        
        # Should perform vector similarity search
        assert result.vector_similarity_results is not None
        assert len(result.vector_similarity_results) >= 0  # May be empty for new content
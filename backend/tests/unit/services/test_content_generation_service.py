"""
Unit Tests for Content Generation Service
Tests the core functionality of content generation with domain expertise
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.services.content_generation.app.services.content_service import ContentService
from backend.services.content_generation.app.services.claude_client import ClaudeClient
from backend.services.content_generation.app.schemas.content import (
    ContentGenerationRequest, 
    ContentGenerationResponse,
    StyleParameters
)


class TestContentService:
    """Test suite for ContentService"""
    
    @pytest.fixture
    async def content_service(self, mock_claude_client, db_session, redis_client):
        """Create ContentService instance for testing"""
        with patch('backend.services.content_generation.app.services.content_service.ClaudeClient', return_value=mock_claude_client):
            service = ContentService(db_session, redis_client)
            return service
    
    @pytest.mark.unit
    async def test_generate_content_success(self, content_service, sample_content_request, performance_benchmarks):
        """Test successful content generation within performance thresholds"""
        start_time = time.time()
        
        # Execute content generation
        result = await content_service.generate_content(
            ContentGenerationRequest(**sample_content_request)
        )
        
        end_time = time.time()
        
        # Assertions
        assert isinstance(result, ContentGenerationResponse)
        assert result.content is not None
        assert len(result.content) > 100  # Minimum content length
        assert result.domain == sample_content_request["domain"]
        assert result.quality_score > 0
        
        # Performance assertion
        assert_response_time(start_time, end_time, performance_benchmarks["content_generation_max_time"])
    
    @pytest.mark.unit
    @pytest.mark.parametrize("domain", ["finance", "sports", "technology"])
    async def test_domain_specific_content_generation(self, content_service, domain):
        """Test content generation for each supported domain"""
        request = ContentGenerationRequest(
            domain=domain,
            topic=f"Test {domain} topic",
            style_parameters=StyleParameters(
                tone="professional",
                length=500,
                complexity="intermediate"
            )
        )
        
        result = await content_service.generate_content(request)
        
        # Domain-specific assertions
        assert result.domain == domain
        assert result.content is not None
        
        # Verify domain-specific keywords based on domain
        if domain == "finance":
            financial_terms = ["market", "investment", "financial", "analysis", "economic"]
            assert any(term in result.content.lower() for term in financial_terms)
        elif domain == "sports":
            sports_terms = ["team", "player", "game", "season", "performance"]
            assert any(term in result.content.lower() for term in sports_terms)
        elif domain == "technology":
            tech_terms = ["technology", "system", "development", "innovation", "digital"]
            assert any(term in result.content.lower() for term in tech_terms)
    
    @pytest.mark.unit
    async def test_style_parameter_variations(self, content_service):
        """Test content generation with different style parameters"""
        base_request = {
            "domain": "finance",
            "topic": "Market Analysis Test"
        }
        
        style_variations = [
            StyleParameters(tone="professional", length=500, complexity="beginner"),
            StyleParameters(tone="casual", length=1000, complexity="advanced"),
            StyleParameters(tone="technical", length=750, complexity="expert")
        ]
        
        results = []
        for style in style_variations:
            request = ContentGenerationRequest(
                **base_request,
                style_parameters=style
            )
            result = await content_service.generate_content(request)
            results.append(result)
        
        # Verify different content generated for different styles
        assert len(set(result.content for result in results)) == len(results)
        
        # Verify length parameters influence actual content length
        for i, result in enumerate(results):
            expected_length = style_variations[i].length
            # Allow 20% variance in content length
            assert abs(len(result.content.split()) - expected_length) <= expected_length * 0.2
    
    @pytest.mark.unit
    async def test_content_caching(self, content_service, redis_client):
        """Test content caching functionality"""
        request = ContentGenerationRequest(
            domain="technology",
            topic="AI Development Trends",
            style_parameters=StyleParameters(tone="professional", length=500)
        )
        
        # First request
        result1 = await content_service.generate_content(request)
        
        # Verify cache was set
        cache_key = content_service._generate_cache_key(request)
        cached_content = await redis_client.get(cache_key)
        assert cached_content is not None
        
        # Second request should use cache
        result2 = await content_service.generate_content(request)
        
        # Results should be identical due to caching
        assert result1.content == result2.content
        assert result1.content_id == result2.content_id
    
    @pytest.mark.unit
    async def test_error_handling_claude_api_failure(self, content_service, mock_claude_client):
        """Test error handling when Claude API fails"""
        # Mock API failure
        mock_claude_client.messages.create.side_effect = Exception("API connection failed")
        
        request = ContentGenerationRequest(
            domain="finance",
            topic="Test topic",
            style_parameters=StyleParameters(tone="professional", length=500)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await content_service.generate_content(request)
        
        assert exc_info.value.status_code == 500
        assert "content generation failed" in str(exc_info.value.detail).lower()
    
    @pytest.mark.unit
    async def test_quality_scoring_integration(self, content_service, quality_thresholds):
        """Test integration with quality scoring system"""
        request = ContentGenerationRequest(
            domain="finance",
            topic="Market Analysis Quality Test",
            style_parameters=StyleParameters(tone="professional", length=1000),
            quality_threshold=quality_thresholds["minimum_quality_score"]
        )
        
        result = await content_service.generate_content(request)
        
        # Quality score should meet minimum threshold
        assert result.quality_score >= quality_thresholds["minimum_quality_score"]
        assert result.quality_metrics is not None
        assert "readability_score" in result.quality_metrics
        assert "seo_score" in result.quality_metrics
    
    @pytest.mark.unit
    async def test_batch_content_generation(self, content_service, performance_benchmarks):
        """Test batch content generation performance"""
        requests = [
            ContentGenerationRequest(
                domain="finance",
                topic=f"Financial Analysis Topic {i}",
                style_parameters=StyleParameters(tone="professional", length=500)
            )
            for i in range(5)
        ]
        
        start_time = time.time()
        results = await content_service.generate_batch_content(requests)
        end_time = time.time()
        
        # Verify all content generated
        assert len(results) == len(requests)
        for result in results:
            assert result.content is not None
            assert len(result.content) > 100
        
        # Performance assertion - batch should be more efficient than individual
        batch_time_per_article = (end_time - start_time) / len(requests)
        assert batch_time_per_article < performance_benchmarks["content_generation_max_time"]
    
    @pytest.mark.unit
    async def test_template_integration(self, content_service):
        """Test content generation with templates"""
        request = ContentGenerationRequest(
            domain="sports",
            topic="NBA Game Recap",
            template_id="sports_game_recap_template",
            style_parameters=StyleParameters(tone="enthusiastic", length=750)
        )
        
        result = await content_service.generate_content(request)
        
        # Template-specific assertions
        assert result.template_used == "sports_game_recap_template"
        assert result.content is not None
        
        # Verify template structure elements
        template_elements = ["Game Summary", "Key Players", "Statistics"]
        content_upper = result.content.upper()
        template_matches = sum(1 for element in template_elements if element.upper() in content_upper)
        assert template_matches >= 2  # At least 2 template elements present


class TestClaudeClient:
    """Test suite for Claude API client"""
    
    @pytest.fixture
    def claude_client(self):
        """Create ClaudeClient for testing"""
        return ClaudeClient(api_key="test_key")
    
    @pytest.mark.unit
    async def test_create_prompt_domain_specific(self, claude_client):
        """Test domain-specific prompt creation"""
        request = ContentGenerationRequest(
            domain="finance",
            topic="Federal Reserve Rate Decision",
            style_parameters=StyleParameters(tone="analytical", length=1000)
        )
        
        prompt = await claude_client._create_domain_prompt(request)
        
        # Verify domain-specific elements in prompt
        assert "finance" in prompt.lower()
        assert "analytical" in prompt.lower()
        assert "federal reserve" in prompt.lower()
        assert "1000" in prompt  # Length requirement
        
        # Verify financial domain expertise indicators
        finance_indicators = ["market", "economic", "financial", "investment", "analysis"]
        assert any(indicator in prompt.lower() for indicator in finance_indicators)
    
    @pytest.mark.unit
    async def test_api_retry_logic(self, claude_client):
        """Test retry logic for API failures"""
        with patch('anthropic.AsyncAnthropic') as mock_client:
            # Configure mock to fail twice then succeed
            mock_instance = mock_client.return_value
            mock_instance.messages.create.side_effect = [
                Exception("Rate limit"),
                Exception("Server error"), 
                MagicMock(content=[MagicMock(text="Success after retries")])
            ]
            
            result = await claude_client._make_api_request("test prompt", max_retries=3)
            
            assert result == "Success after retries"
            assert mock_instance.messages.create.call_count == 3
    
    @pytest.mark.unit
    async def test_prompt_optimization(self, claude_client):
        """Test prompt optimization for different content types"""
        test_cases = [
            {"domain": "finance", "complexity": "beginner", "expected_terms": ["basic", "simple", "introduction"]},
            {"domain": "sports", "complexity": "expert", "expected_terms": ["advanced", "detailed", "comprehensive"]},
            {"domain": "technology", "complexity": "intermediate", "expected_terms": ["moderate", "balanced", "practical"]}
        ]
        
        for case in test_cases:
            request = ContentGenerationRequest(
                domain=case["domain"],
                topic="Test Topic",
                style_parameters=StyleParameters(
                    complexity=case["complexity"],
                    tone="professional",
                    length=500
                )
            )
            
            prompt = await claude_client._create_domain_prompt(request)
            
            # Verify complexity-appropriate language
            assert any(term in prompt.lower() for term in case["expected_terms"])


class TestContentValidation:
    """Test content validation and quality checks"""
    
    @pytest.mark.unit
    async def test_content_length_validation(self, content_service):
        """Test content length meets requirements"""
        test_lengths = [300, 500, 1000, 1500, 2000]
        
        for target_length in test_lengths:
            request = ContentGenerationRequest(
                domain="technology",
                topic="Software Development Best Practices",
                style_parameters=StyleParameters(
                    tone="educational",
                    length=target_length,
                    complexity="intermediate"
                )
            )
            
            result = await content_service.generate_content(request)
            
            # Verify word count is within acceptable range (±20%)
            word_count = len(result.content.split())
            assert abs(word_count - target_length) <= target_length * 0.2
    
    @pytest.mark.unit
    async def test_content_uniqueness_validation(self, content_service):
        """Test content uniqueness across multiple generations"""
        request = ContentGenerationRequest(
            domain="finance",
            topic="Stock Market Analysis",
            style_parameters=StyleParameters(
                tone="professional",
                length=500,
                complexity="intermediate",
                randomization_level="high"  # Ensure variation
            )
        )
        
        # Generate multiple pieces of content
        results = []
        for _ in range(5):
            result = await content_service.generate_content(request)
            results.append(result.content)
        
        # Verify all content is unique
        unique_content = set(results)
        assert len(unique_content) == len(results), "Generated content should be unique"
        
        # Verify sufficient content variation (simple similarity check)
        for i, content1 in enumerate(results):
            for j, content2 in enumerate(results[i+1:], i+1):
                # Simple word overlap check
                words1 = set(content1.lower().split())
                words2 = set(content2.lower().split())
                overlap = len(words1.intersection(words2)) / len(words1.union(words2))
                assert overlap < 0.8, f"Content {i} and {j} too similar (overlap: {overlap})"
    
    @pytest.mark.unit
    @pytest.mark.parametrize("domain,accuracy_threshold", [
        ("finance", 99.0),
        ("sports", 95.0), 
        ("technology", 90.0)
    ])
    async def test_domain_accuracy_requirements(self, content_service, domain, accuracy_threshold, domain_test_data):
        """Test domain-specific accuracy requirements"""
        domain_data = domain_test_data[domain]
        
        for topic in domain_data["sample_topics"]:
            request = ContentGenerationRequest(
                domain=domain,
                topic=topic,
                style_parameters=StyleParameters(
                    tone="professional",
                    length=1000,
                    complexity="intermediate"
                )
            )
            
            result = await content_service.generate_content(request)
            
            # Verify domain accuracy meets threshold
            assert result.quality_metrics.get("domain_accuracy", 0) >= accuracy_threshold
            
            # Verify required domain terms are present
            content_lower = result.content.lower()
            required_terms_present = sum(
                1 for term in domain_data["required_terms"] 
                if term in content_lower
            )
            assert required_terms_present >= len(domain_data["required_terms"]) // 2


# Performance benchmarking tests
@pytest.mark.performance
class TestContentGenerationPerformance:
    """Performance tests for content generation"""
    
    @pytest.mark.slow
    async def test_concurrent_generation_performance(self, content_service, performance_benchmarks):
        """Test performance under concurrent load"""
        import asyncio
        
        async def generate_content_task():
            request = ContentGenerationRequest(
                domain="finance",
                topic="Market Performance Analysis",
                style_parameters=StyleParameters(tone="professional", length=500)
            )
            return await content_service.generate_content(request)
        
        # Test with different concurrency levels
        concurrency_levels = [5, 10, 20]
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            # Execute concurrent requests
            tasks = [generate_content_task() for _ in range(concurrency)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_request = total_time / concurrency
            
            # Performance assertions
            assert len(results) == concurrency
            assert all(result.content for result in results)
            assert avg_time_per_request <= performance_benchmarks["content_generation_max_time"]
            
            print(f"Concurrency {concurrency}: {avg_time_per_request:.2f}s avg per request")
    
    @pytest.mark.benchmark
    def test_content_generation_benchmark(self, benchmark, content_service, sample_content_request):
        """Benchmark content generation performance"""
        async def generate_content():
            return await content_service.generate_content(
                ContentGenerationRequest(**sample_content_request)
            )
        
        # Run benchmark
        result = benchmark(asyncio.run, generate_content())
        
        # Verify result quality
        assert result.content is not None
        assert len(result.content) > 100
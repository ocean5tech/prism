"""
Automated Testing Framework for Intelligent Content Generation Factory
Provides comprehensive testing infrastructure with fixtures, utilities, and base classes
"""

import asyncio
import pytest
import httpx
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import docker
import redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import openai

from shared.config import TestSettings
from shared.logging import get_logger

logger = get_logger(__name__)

# Test configuration
TEST_SETTINGS = TestSettings()

@dataclass
class TestResult:
    """Standard test result format"""
    test_name: str
    status: str  # 'passed', 'failed', 'skipped'
    execution_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class ContentGenerationTestData:
    """Test data for content generation scenarios"""
    domain: str
    source_content: str
    expected_word_count: int
    style_parameters: Dict[str, Any]
    quality_threshold: float = 0.85

class TestDatabaseManager:
    """Database management for testing environments"""
    
    def __init__(self):
        self.engine = create_async_engine(TEST_SETTINGS.DATABASE_URL)
    
    async def setup_test_database(self):
        """Initialize test database with clean state"""
        async with self.engine.begin() as conn:
            # Create test schema
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS test"))
            
            # Create test tables (simplified versions)
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test.test_content (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    domain VARCHAR(50),
                    title TEXT,
                    content TEXT,
                    quality_score DECIMAL(4,3),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test.test_metrics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    test_name VARCHAR(100),
                    metric_type VARCHAR(50),
                    metric_value DECIMAL(10,3),
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
    
    async def cleanup_test_database(self):
        """Clean up test data"""
        async with self.engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE test.test_content"))
            await conn.execute(text("TRUNCATE TABLE test.test_metrics"))
    
    async def insert_test_content(self, content_data: Dict[str, Any]) -> str:
        """Insert test content and return ID"""
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("""
                    INSERT INTO test.test_content (domain, title, content, quality_score)
                    VALUES (:domain, :title, :content, :quality_score)
                    RETURNING id
                """),
                content_data
            )
            return str(result.fetchone()[0])

class DockerTestEnvironment:
    """Docker-based test environment management"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.test_containers = []
    
    async def start_test_services(self, services: List[str]) -> Dict[str, str]:
        """Start required test services"""
        service_urls = {}
        
        for service in services:
            if service == "redis":
                container = self.client.containers.run(
                    "redis:7-alpine",
                    detach=True,
                    ports={'6379/tcp': None},
                    name=f"test-redis-{uuid.uuid4().hex[:8]}"
                )
                self.test_containers.append(container)
                port = container.attrs['NetworkSettings']['Ports']['6379/tcp'][0]['HostPort']
                service_urls[service] = f"redis://localhost:{port}"
            
            elif service == "postgresql":
                container = self.client.containers.run(
                    "postgres:15-alpine",
                    detach=True,
                    environment={
                        "POSTGRES_DB": "test_db",
                        "POSTGRES_USER": "test_user", 
                        "POSTGRES_PASSWORD": "test_pass"
                    },
                    ports={'5432/tcp': None},
                    name=f"test-postgres-{uuid.uuid4().hex[:8]}"
                )
                self.test_containers.append(container)
                port = container.attrs['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
                service_urls[service] = f"postgresql://test_user:test_pass@localhost:{port}/test_db"
        
        # Wait for services to be ready
        await asyncio.sleep(10)
        return service_urls
    
    async def cleanup_test_environment(self):
        """Stop and remove test containers"""
        for container in self.test_containers:
            try:
                container.stop()
                container.remove()
            except Exception as e:
                logger.warning(f"Error cleaning up container {container.name}: {e}")
        
        self.test_containers.clear()

class APITestClient:
    """Enhanced HTTP client for API testing"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_headers = {}
        if auth_token:
            self.auth_headers["Authorization"] = f"Bearer {auth_token}"
    
    async def make_request(self, method: str, endpoint: str, 
                          data: Dict = None, params: Dict = None,
                          expected_status: int = 200, timeout: float = 30.0) -> httpx.Response:
        """Make HTTP request with comprehensive error handling"""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            start_time = datetime.now()
            
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.auth_headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.auth_headers, json=data, params=params)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=self.auth_headers, json=data, params=params)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=self.auth_headers, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Log request details
                logger.info(f"API Request: {method} {url} - Status: {response.status_code} - Time: {execution_time:.3f}s")
                
                # Validate response status if expected
                if expected_status and response.status_code != expected_status:
                    raise AssertionError(
                        f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
                    )
                
                return response
                
            except httpx.TimeoutException:
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"Request timeout after {execution_time:.3f}s: {method} {url}")
                raise
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"Request failed after {execution_time:.3f}s: {method} {url} - Error: {e}")
                raise

class TestMetricsCollector:
    """Collect and analyze test execution metrics"""
    
    def __init__(self):
        self.metrics = []
        self.start_time = None
        
    def start_collection(self):
        """Start metrics collection"""
        self.start_time = datetime.now()
        self.metrics.clear()
    
    def record_metric(self, metric_type: str, metric_value: float, 
                     test_name: str = None, metadata: Dict = None):
        """Record a test metric"""
        metric = {
            "type": metric_type,
            "value": metric_value,
            "test_name": test_name,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc)
        }
        self.metrics.append(metric)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.metrics:
            return {"status": "no_metrics"}
        
        total_execution_time = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate aggregated metrics
        response_times = [m["value"] for m in self.metrics if m["type"] == "response_time"]
        error_rates = [m["value"] for m in self.metrics if m["type"] == "error_rate"]
        
        summary = {
            "total_tests": len(set(m["test_name"] for m in self.metrics if m["test_name"])),
            "total_execution_time": total_execution_time,
            "total_metrics": len(self.metrics),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "avg_error_rate": sum(error_rates) / len(error_rates) if error_rates else 0,
            "metrics_by_type": {}
        }
        
        # Group metrics by type
        for metric in self.metrics:
            metric_type = metric["type"]
            if metric_type not in summary["metrics_by_type"]:
                summary["metrics_by_type"][metric_type] = {
                    "count": 0,
                    "avg_value": 0,
                    "min_value": float('inf'),
                    "max_value": float('-inf')
                }
            
            type_stats = summary["metrics_by_type"][metric_type]
            type_stats["count"] += 1
            type_stats["min_value"] = min(type_stats["min_value"], metric["value"])
            type_stats["max_value"] = max(type_stats["max_value"], metric["value"])
            type_stats["avg_value"] = (
                (type_stats["avg_value"] * (type_stats["count"] - 1) + metric["value"]) 
                / type_stats["count"]
            )
        
        return summary

class ContentGenerationTester:
    """Specialized tester for content generation functionality"""
    
    def __init__(self, api_client: APITestClient):
        self.api_client = api_client
        self.test_data_cache = {}
    
    async def test_content_generation(self, test_data: ContentGenerationTestData) -> TestResult:
        """Test content generation with specific parameters"""
        test_name = f"content_generation_{test_data.domain}"
        start_time = datetime.now()
        
        try:
            # Submit content generation request
            request_data = {
                "domain": test_data.domain,
                "source_content": test_data.source_content,
                "style_parameters": test_data.style_parameters,
                "target_length": test_data.expected_word_count
            }
            
            response = await self.api_client.make_request(
                "POST", "/api/v1/content/generate", 
                data=request_data,
                timeout=60.0  # Extended timeout for AI operations
            )
            
            response_data = response.json()
            
            # Validate response structure
            required_fields = ["content_id", "generated_content", "quality_indicators"]
            for field in required_fields:
                assert field in response_data, f"Missing required field: {field}"
            
            # Validate content quality
            quality_score = response_data["quality_indicators"].get("overall_score", 0)
            assert quality_score >= test_data.quality_threshold, \
                f"Quality score {quality_score} below threshold {test_data.quality_threshold}"
            
            # Validate content length
            generated_content = response_data["generated_content"]
            word_count = len(generated_content.split())
            expected_range = (test_data.expected_word_count * 0.8, test_data.expected_word_count * 1.2)
            assert expected_range[0] <= word_count <= expected_range[1], \
                f"Word count {word_count} outside expected range {expected_range}"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TestResult(
                test_name=test_name,
                status="passed",
                execution_time=execution_time,
                metrics={
                    "quality_score": quality_score,
                    "word_count": word_count,
                    "generation_time": response_data.get("metadata", {}).get("generation_time", 0)
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name=test_name,
                status="failed",
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def test_adversarial_optimization(self) -> TestResult:
        """Test adversarial optimization system"""
        test_name = "adversarial_optimization"
        start_time = datetime.now()
        
        try:
            # Generate multiple content samples
            test_samples = []
            for i in range(5):
                test_data = ContentGenerationTestData(
                    domain="technology",
                    source_content=f"Test content sample {i} for pattern detection",
                    expected_word_count=500,
                    style_parameters={"tone": "technical", "creativity": 0.7}
                )
                
                result = await self.test_content_generation(test_data)
                if result.status == "passed":
                    test_samples.append(result.metrics)
            
            # Analyze pattern diversity
            quality_scores = [sample["quality_score"] for sample in test_samples]
            avg_quality = sum(quality_scores) / len(quality_scores)
            quality_variance = sum((score - avg_quality) ** 2 for score in quality_scores) / len(quality_scores)
            
            # Test pattern detection API
            pattern_detection_data = {
                "content_batch": [sample["generated_content"] for sample in test_samples[:3]],
                "domain": "technology",
                "analysis_type": "pattern_similarity"
            }
            
            pattern_response = await self.api_client.make_request(
                "POST", "/api/v1/patterns/analyze",
                data=pattern_detection_data
            )
            
            pattern_data = pattern_response.json()
            pattern_similarity = pattern_data.get("pattern_similarity", 1.0)
            
            # Validate optimization effectiveness
            assert pattern_similarity < 0.75, \
                f"Pattern similarity {pattern_similarity} too high, indicating poor optimization"
            
            assert quality_variance > 0.01, \
                "Quality variance too low, indicating lack of style variation"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TestResult(
                test_name=test_name,
                status="passed", 
                execution_time=execution_time,
                metrics={
                    "avg_quality_score": avg_quality,
                    "quality_variance": quality_variance,
                    "pattern_similarity": pattern_similarity,
                    "samples_tested": len(test_samples)
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name=test_name,
                status="failed",
                execution_time=execution_time,
                error_message=str(e)
            )

class MultiDomainTester:
    """Test multi-domain functionality and consistency"""
    
    def __init__(self, api_client: APITestClient):
        self.api_client = api_client
        self.domain_configs = {
            "finance": {
                "style": {"tone": "professional", "compliance": "high"},
                "quality_threshold": 0.95,
                "expected_features": ["risk_disclosure", "regulatory_compliance"]
            },
            "sports": {
                "style": {"tone": "engaging", "real_time": True},
                "quality_threshold": 0.85,
                "expected_features": ["statistics", "event_updates"]
            },
            "technology": {
                "style": {"tone": "technical", "innovation_focus": True},
                "quality_threshold": 0.90,
                "expected_features": ["trend_analysis", "technical_accuracy"]
            }
        }
    
    async def test_domain_specific_generation(self, domain: str) -> TestResult:
        """Test domain-specific content generation"""
        test_name = f"domain_specific_{domain}"
        start_time = datetime.now()
        
        if domain not in self.domain_configs:
            return TestResult(
                test_name=test_name,
                status="skipped",
                execution_time=0,
                error_message=f"Domain {domain} not configured for testing"
            )
        
        try:
            config = self.domain_configs[domain]
            
            test_data = {
                "domain": domain,
                "source_content": f"Sample {domain} content for testing domain-specific generation capabilities",
                "style_parameters": config["style"],
                "target_length": 800
            }
            
            response = await self.api_client.make_request(
                "POST", "/api/v1/content/generate",
                data=test_data,
                timeout=45.0
            )
            
            response_data = response.json()
            
            # Validate domain-specific requirements
            quality_score = response_data["quality_indicators"]["overall_score"]
            assert quality_score >= config["quality_threshold"], \
                f"Quality below domain threshold: {quality_score} < {config['quality_threshold']}"
            
            # Check domain-specific features
            metadata = response_data.get("metadata", {})
            for feature in config["expected_features"]:
                assert feature in metadata.get("domain_features", []), \
                    f"Missing expected domain feature: {feature}"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TestResult(
                test_name=test_name,
                status="passed",
                execution_time=execution_time,
                metrics={
                    "quality_score": quality_score,
                    "domain_features": metadata.get("domain_features", []),
                    "compliance_score": metadata.get("compliance_score", 0)
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestResult(
                test_name=test_name,
                status="failed",
                execution_time=execution_time,
                error_message=str(e)
            )

# Pytest fixtures for common test components
@pytest.fixture
async def test_database():
    """Fixture for test database setup and cleanup"""
    db_manager = TestDatabaseManager()
    await db_manager.setup_test_database()
    yield db_manager
    await db_manager.cleanup_test_database()

@pytest.fixture
async def docker_test_environment():
    """Fixture for Docker test environment"""
    docker_env = DockerTestEnvironment()
    service_urls = await docker_env.start_test_services(["redis", "postgresql"])
    yield service_urls
    await docker_env.cleanup_test_environment()

@pytest.fixture
def api_test_client():
    """Fixture for API test client"""
    return APITestClient(
        base_url=TEST_SETTINGS.API_BASE_URL,
        auth_token=TEST_SETTINGS.AUTH_TOKEN
    )

@pytest.fixture
def metrics_collector():
    """Fixture for test metrics collection"""
    collector = TestMetricsCollector()
    collector.start_collection()
    yield collector
    
    # Print metrics summary after test
    summary = collector.get_summary()
    logger.info(f"Test Metrics Summary: {json.dumps(summary, indent=2)}")

@pytest.fixture
async def content_generation_tester(api_test_client):
    """Fixture for content generation testing"""
    return ContentGenerationTester(api_test_client)

@pytest.fixture
async def multi_domain_tester(api_test_client):
    """Fixture for multi-domain testing"""
    return MultiDomainTester(api_test_client)

# Utility functions for test data generation
def generate_test_content_samples(domain: str, count: int = 10) -> List[ContentGenerationTestData]:
    """Generate test content samples for various scenarios"""
    samples = []
    
    domain_templates = {
        "finance": {
            "topics": ["market analysis", "investment strategy", "regulatory update", "earnings report"],
            "content_bases": [
                "Recent market developments show significant volatility in technology stocks...",
                "New regulatory framework announced by SEC impacts investment strategies...",
                "Quarterly earnings reports reveal mixed results across financial sector...",
                "Federal Reserve policy changes create uncertainty in bond markets..."
            ]
        },
        "sports": {
            "topics": ["game recap", "player analysis", "trade news", "season preview"],
            "content_bases": [
                "Last night's championship game featured incredible performances...",
                "Star player announces contract extension with major implications...",
                "Trade deadline approaches with several teams making moves...",
                "Season predictions based on pre-season training and roster changes..."
            ]
        },
        "technology": {
            "topics": ["product launch", "industry trends", "innovation analysis", "market disruption"],
            "content_bases": [
                "New artificial intelligence breakthrough promises to transform industries...",
                "Major technology company announces revolutionary product line...",
                "Industry analysis reveals emerging trends in cloud computing...",
                "Startup disruption creates new opportunities in traditional sectors..."
            ]
        }
    }
    
    if domain not in domain_templates:
        domain = "technology"  # Default fallback
    
    template = domain_templates[domain]
    
    for i in range(count):
        topic_index = i % len(template["topics"])
        content_index = i % len(template["content_bases"])
        
        samples.append(ContentGenerationTestData(
            domain=domain,
            source_content=template["content_bases"][content_index],
            expected_word_count=800 + (i * 50),  # Varying lengths
            style_parameters={
                "tone": ["professional", "engaging", "analytical"][i % 3],
                "creativity": 0.5 + (i % 5) * 0.1,  # 0.5 to 0.9
                "topic_focus": template["topics"][topic_index]
            },
            quality_threshold=0.80 + (i % 3) * 0.05  # 0.80 to 0.90
        ))
    
    return samples

# Test result analysis utilities
def analyze_test_results(results: List[TestResult]) -> Dict[str, Any]:
    """Analyze collection of test results"""
    if not results:
        return {"error": "No test results to analyze"}
    
    passed_tests = [r for r in results if r.status == "passed"]
    failed_tests = [r for r in results if r.status == "failed"]
    skipped_tests = [r for r in results if r.status == "skipped"]
    
    analysis = {
        "summary": {
            "total_tests": len(results),
            "passed": len(passed_tests),
            "failed": len(failed_tests),
            "skipped": len(skipped_tests),
            "pass_rate": len(passed_tests) / len(results) * 100
        },
        "execution_times": {
            "total": sum(r.execution_time for r in results),
            "average": sum(r.execution_time for r in results) / len(results),
            "max": max(r.execution_time for r in results),
            "min": min(r.execution_time for r in results)
        },
        "failed_tests": [
            {
                "name": r.test_name,
                "error": r.error_message,
                "execution_time": r.execution_time
            }
            for r in failed_tests
        ]
    }
    
    # Aggregate metrics if available
    all_metrics = [r.metrics for r in passed_tests if r.metrics]
    if all_metrics:
        # Calculate average quality scores
        quality_scores = [m.get("quality_score", 0) for m in all_metrics if "quality_score" in m]
        if quality_scores:
            analysis["quality_metrics"] = {
                "average_quality": sum(quality_scores) / len(quality_scores),
                "min_quality": min(quality_scores),
                "max_quality": max(quality_scores)
            }
    
    return analysis
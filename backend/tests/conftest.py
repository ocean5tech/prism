"""
Test Configuration and Fixtures
Central configuration for all testing across the platform
"""
import pytest
import asyncio
import os
import json
import tempfile
from typing import Generator, Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
import aiohttp
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Test Environment Configuration
TEST_ENV = {
    "ENVIRONMENT": "testing",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test_prism",
    "REDIS_URL": "redis://localhost:6379/15",
    "CLAUDE_API_KEY": "test_key_mock",
    "JWT_SECRET": "test_jwt_secret",
    "LOG_LEVEL": "DEBUG"
}

# Apply test environment variables
for key, value in TEST_ENV.items():
    os.environ[key] = value


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def postgres_container():
    """Start PostgreSQL container for integration tests"""
    container = PostgresContainer("postgres:15")
    container.start()
    
    # Update database URL
    db_url = container.get_connection_url()
    os.environ["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    yield container
    container.stop()


@pytest.fixture(scope="session")
async def redis_container():
    """Start Redis container for integration tests"""
    container = RedisContainer("redis:7-alpine")
    container.start()
    
    # Update Redis URL
    redis_url = f"redis://{container.get_container_host_ip()}:{container.get_exposed_port(6379)}/0"
    os.environ["REDIS_URL"] = redis_url
    
    yield container
    container.stop()


@pytest.fixture
async def db_session(postgres_container) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    from backend.shared.database import DatabaseManager
    
    # Create tables
    await DatabaseManager.create_tables()
    
    # Create session
    async with DatabaseManager.get_session() as session:
        yield session
        # Cleanup after test
        await session.rollback()


@pytest.fixture
async def redis_client(redis_container) -> AsyncGenerator[redis.Redis, None]:
    """Create Redis client for tests"""
    client = redis.from_url(os.environ["REDIS_URL"])
    await client.flushall()
    yield client
    await client.flushall()
    await client.close()


@pytest.fixture
def mock_claude_client():
    """Mock Claude API client for testing"""
    mock = AsyncMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Mock generated content for testing")]
    )
    return mock


@pytest.fixture
def sample_content_request():
    """Sample content generation request"""
    return {
        "domain": "finance",
        "topic": "Market Analysis Q3 2024",
        "style_parameters": {
            "tone": "professional",
            "length": 1000,
            "complexity": "intermediate",
            "keywords": ["market", "analysis", "growth"]
        },
        "template_id": "finance_analysis_template"
    }


@pytest.fixture
def sample_detection_response():
    """Sample detection service response"""
    return {
        "quality_score": 87.5,
        "uniqueness_score": 92.0,
        "domain_accuracy": 95.0,
        "issues": [],
        "recommendations": [
            "Consider adding more specific financial data",
            "Improve keyword density for SEO"
        ],
        "patterns_detected": False,
        "plagiarism_score": 2.1
    }


@pytest.fixture
def sample_publishing_request():
    """Sample publishing request"""
    return {
        "content_id": "test_content_123",
        "platforms": ["wordpress", "medium", "linkedin"],
        "schedule": {
            "publish_immediately": False,
            "scheduled_time": "2024-08-12T10:00:00Z"
        },
        "metadata": {
            "title": "Test Article Title",
            "excerpt": "Test article excerpt",
            "tags": ["finance", "market", "analysis"],
            "featured_image": "https://example.com/image.jpg"
        }
    }


@pytest.fixture
async def test_client():
    """Create test HTTP client"""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def performance_benchmarks():
    """Performance benchmark thresholds"""
    return {
        "content_generation_max_time": 30.0,  # seconds
        "api_response_max_time": 0.5,  # seconds
        "database_query_max_time": 0.1,  # seconds
        "quality_analysis_max_time": 5.0,  # seconds
        "publishing_max_time": 10.0,  # seconds
    }


@pytest.fixture
def quality_thresholds():
    """Quality threshold configurations"""
    return {
        "minimum_quality_score": 80.0,
        "minimum_uniqueness_score": 90.0,
        "minimum_domain_accuracy": 95.0,
        "maximum_plagiarism_score": 5.0,
        "minimum_seo_score": 75.0
    }


@pytest.fixture
def domain_test_data():
    """Domain-specific test data"""
    return {
        "finance": {
            "sample_topics": [
                "Federal Reserve Interest Rate Decision",
                "Q3 Earnings Analysis for Tech Stocks",
                "Cryptocurrency Market Volatility"
            ],
            "required_terms": ["market", "analysis", "financial", "investment"],
            "accuracy_threshold": 99.0
        },
        "sports": {
            "sample_topics": [
                "NFL Week 10 Preview",
                "NBA Trade Deadline Analysis",
                "World Cup Qualification Update"
            ],
            "required_terms": ["team", "player", "game", "season"],
            "accuracy_threshold": 95.0
        },
        "technology": {
            "sample_topics": [
                "AI Model Performance Improvements",
                "Cloud Computing Cost Optimization",
                "Cybersecurity Threat Landscape 2024"
            ],
            "required_terms": ["technology", "innovation", "development", "system"],
            "accuracy_threshold": 90.0
        }
    }


@pytest.fixture
def n8n_workflow_test_data():
    """n8n workflow test scenarios"""
    return {
        "content_generation_workflow": {
            "trigger": "webhook",
            "expected_nodes": [
                "RSS Feed Reader",
                "Content Generator",
                "Quality Detector",
                "Publishing Manager"
            ],
            "success_criteria": {
                "execution_time": 120,  # seconds
                "success_rate": 0.99
            }
        },
        "error_handling_workflow": {
            "trigger": "failure_event",
            "expected_nodes": [
                "Error Detector",
                "Retry Logic",
                "Notification Manager"
            ]
        }
    }


@pytest.fixture
def security_test_scenarios():
    """Security testing scenarios"""
    return {
        "authentication_tests": [
            {"scenario": "valid_jwt", "expected": "authorized"},
            {"scenario": "expired_jwt", "expected": "unauthorized"},
            {"scenario": "invalid_jwt", "expected": "unauthorized"},
            {"scenario": "missing_jwt", "expected": "unauthorized"}
        ],
        "authorization_tests": [
            {"role": "admin", "resource": "all", "expected": "allowed"},
            {"role": "editor", "resource": "content", "expected": "allowed"},
            {"role": "viewer", "resource": "content", "expected": "read_only"},
            {"role": "guest", "resource": "content", "expected": "forbidden"}
        ],
        "rate_limiting_tests": [
            {"requests_per_minute": 60, "expected": "allowed"},
            {"requests_per_minute": 120, "expected": "throttled"},
            {"requests_per_minute": 300, "expected": "blocked"}
        ]
    }


@pytest.fixture
def load_test_scenarios():
    """Load testing scenarios"""
    return {
        "concurrent_content_generation": {
            "concurrent_requests": [10, 50, 100, 250],
            "duration_seconds": 300,
            "success_rate_threshold": 0.98
        },
        "database_load": {
            "concurrent_queries": [25, 100, 500, 1000],
            "query_types": ["read", "write", "complex_join"],
            "response_time_threshold": 0.1
        },
        "api_endpoint_load": {
            "endpoints": [
                "/api/v1/content/generate",
                "/api/v1/detection/analyze",
                "/api/v1/publishing/publish"
            ],
            "requests_per_second": [10, 50, 100, 500],
            "error_rate_threshold": 0.02
        }
    }


# Utility functions for testing
def assert_response_time(start_time, end_time, max_time):
    """Assert response time is within threshold"""
    elapsed = end_time - start_time
    assert elapsed <= max_time, f"Response time {elapsed:.2f}s exceeded threshold {max_time}s"


def assert_quality_score(actual_score, threshold, metric_name):
    """Assert quality score meets minimum threshold"""
    assert actual_score >= threshold, f"{metric_name} score {actual_score} below threshold {threshold}"


def generate_test_content(domain: str, length: int = 1000) -> str:
    """Generate test content for specified domain"""
    content_templates = {
        "finance": f"Financial market analysis content for testing purposes. {'Market data and analysis. ' * (length // 50)}",
        "sports": f"Sports analysis content for testing purposes. {'Game statistics and player performance. ' * (length // 50)}",
        "technology": f"Technology article content for testing purposes. {'Innovation and development insights. ' * (length // 50)}"
    }
    return content_templates.get(domain, f"General content for testing. {'Test content data. ' * (length // 20)}")


# Test markers
pytest.register_marker = lambda name, description: None
pytest.register_marker("unit", "Unit tests for individual components")
pytest.register_marker("integration", "Integration tests for service communication")
pytest.register_marker("performance", "Performance and load tests")
pytest.register_marker("security", "Security and authentication tests")
pytest.register_marker("e2e", "End-to-end system tests")
pytest.register_marker("slow", "Tests that take longer than 5 seconds")
pytest.register_marker("requires_external", "Tests requiring external services")
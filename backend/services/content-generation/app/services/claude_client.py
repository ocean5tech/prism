"""
Claude API Client for Content Generation
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Tuple
import httpx
from anthropic import Anthropic, AsyncAnthropic
import os
import random
from datetime import datetime, timedelta
import structlog

from ....shared.database import CacheManager
from ....shared.logging import ServiceLogger

logger = structlog.get_logger()
service_logger = ServiceLogger("claude-client")

class ClaudeConfig:
    """Claude API configuration"""
    API_KEY = os.getenv("ANTHROPIC_API_KEY")
    DEFAULT_MODEL = os.getenv("CLAUDE_DEFAULT_MODEL", "claude-3-sonnet-20240229")
    MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
    TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
    
    # Rate limiting
    REQUESTS_PER_MINUTE = int(os.getenv("CLAUDE_RPM", "60"))
    REQUESTS_PER_HOUR = int(os.getenv("CLAUDE_RPH", "1000"))
    CONCURRENT_REQUESTS = int(os.getenv("CLAUDE_CONCURRENT", "5"))
    
    # Cost tracking
    MODEL_COSTS = {
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},  # per 1K tokens
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075}
    }

class RateLimiter:
    """Rate limiting for Claude API requests"""
    
    def __init__(self):
        self.requests_per_minute = ClaudeConfig.REQUESTS_PER_MINUTE
        self.requests_per_hour = ClaudeConfig.REQUESTS_PER_HOUR
        self.minute_window = []
        self.hour_window = []
        self.semaphore = asyncio.Semaphore(ClaudeConfig.CONCURRENT_REQUESTS)
    
    async def acquire(self):
        """Acquire rate limit permission"""
        await self.semaphore.acquire()
        
        now = datetime.utcnow()
        
        # Clean old requests from windows
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        self.minute_window = [req for req in self.minute_window if req > minute_ago]
        self.hour_window = [req for req in self.hour_window if req > hour_ago]
        
        # Check rate limits
        if len(self.minute_window) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.minute_window[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit hit, sleeping {sleep_time}s")
                await asyncio.sleep(sleep_time)
        
        if len(self.hour_window) >= self.requests_per_hour:
            sleep_time = 3600 - (now - self.hour_window[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Hourly rate limit hit, sleeping {sleep_time}s")
                await asyncio.sleep(sleep_time)
        
        # Record request
        self.minute_window.append(now)
        self.hour_window.append(now)
    
    def release(self):
        """Release rate limit permission"""
        self.semaphore.release()

class ClaudeClient:
    """Async Claude API client with rate limiting and cost tracking"""
    
    def __init__(self):
        if not ClaudeConfig.API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        self.client = AsyncAnthropic(api_key=ClaudeConfig.API_KEY)
        self.rate_limiter = RateLimiter()
        self.total_cost = 0.0
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate API call cost"""
        costs = ClaudeConfig.MODEL_COSTS.get(model, {"input": 0.003, "output": 0.015})
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        return input_cost + output_cost
    
    async def generate_content(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """Generate content using Claude API with error handling and retries"""
        
        model = model or ClaudeConfig.DEFAULT_MODEL
        max_tokens = max_tokens or ClaudeConfig.MAX_TOKENS
        temperature = temperature or ClaudeConfig.TEMPERATURE
        
        await self.rate_limiter.acquire()
        
        try:
            start_time = time.time()
            
            # Check cache first
            cache_key = f"claude:{hash(prompt + model + str(temperature))}"
            cached_result = await CacheManager.get(cache_key)
            if cached_result:
                logger.info("Using cached Claude response")
                self.rate_limiter.release()
                return json.loads(cached_result)
            
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]
            
            # Make API call with retries
            response = await self._make_request_with_retry(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt
            )
            
            generation_time = time.time() - start_time
            
            # Extract response data
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Calculate cost
            cost = self.calculate_cost(model, input_tokens, output_tokens)
            self.total_cost += cost
            
            # Prepare result
            result = {
                "content": content,
                "model": model,
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "generation_time": generation_time,
                "cost_usd": cost,
                "temperature": temperature
            }
            
            # Cache successful result
            await CacheManager.set(cache_key, json.dumps(result), expire=3600)
            
            # Log metrics
            service_logger.log_ai_request(
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                cost=cost,
                response_time=generation_time
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise
        finally:
            self.rate_limiter.release()
    
    async def _make_request_with_retry(
        self, 
        messages: List[Dict],
        model: str,
        max_tokens: int,
        temperature: float,
        system: str = None,
        max_retries: int = 3
    ):
        """Make API request with exponential backoff retry"""
        
        for attempt in range(max_retries + 1):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                if system:
                    kwargs["system"] = system
                
                response = await self.client.messages.create(**kwargs)
                return response
                
            except Exception as e:
                if attempt == max_retries:
                    raise e
                
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Claude API retry {attempt + 1}/{max_retries}, waiting {delay}s")
                await asyncio.sleep(delay)
        
        raise Exception("Max retries exceeded")

class ContentPromptBuilder:
    """Build prompts for content generation"""
    
    @staticmethod
    def build_content_prompt(
        domain: str,
        source_content: str,
        style_parameters: Dict[str, Any],
        target_length: int,
        generation_settings: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        """Build content generation prompt"""
        
        generation_settings = generation_settings or {}
        
        # Domain-specific system prompts
        domain_systems = {
            "finance": """You are a professional financial content writer with expertise in market analysis, 
            investment strategies, and regulatory matters. Ensure all financial information is accurate and 
            include appropriate risk disclaimers. Focus on data-driven analysis and professional terminology.""",
            
            "sports": """You are a sports journalist with deep knowledge of various sports, statistics, 
            and current events. Write engaging content that captures the excitement of sports while 
            providing accurate information about teams, players, and events.""",
            
            "technology": """You are a technology writer specializing in emerging trends, product analysis, 
            and industry insights. Focus on technical accuracy while making complex topics accessible. 
            Include relevant technical specifications and market implications.""",
            
            "general": """You are a versatile content writer capable of adapting your style to various 
            topics. Focus on clarity, engagement, and providing valuable insights to readers."""
        }
        
        system_prompt = domain_systems.get(domain, domain_systems["general"])
        
        # Style configuration
        tone = ", ".join(style_parameters.get("tone", ["neutral"]))
        structure = style_parameters.get("structure", ["standard"])
        vocabulary = style_parameters.get("vocabulary", "general")
        formality = style_parameters.get("formality", "professional")
        
        # Build main prompt
        prompt = f"""Please create a {target_length}-word article based on the following source content:

SOURCE CONTENT:
{source_content}

STYLE REQUIREMENTS:
- Tone: {tone}
- Vocabulary Level: {vocabulary}
- Formality: {formality}
- Structure: {', '.join(structure)}

CONTENT REQUIREMENTS:
- Target Length: {target_length} words
- Domain: {domain.upper()}"""
        
        # Add generation settings
        if generation_settings.get("fact_check_required"):
            prompt += "\n- Ensure all facts are accurate and verifiable"
        
        if generation_settings.get("include_statistics"):
            prompt += "\n- Include relevant statistics and data points"
        
        if generation_settings.get("seo_optimize"):
            keywords = generation_settings.get("target_keywords", [])
            if keywords:
                prompt += f"\n- Optimize for SEO with keywords: {', '.join(keywords)}"
        
        if generation_settings.get("real_time_data"):
            prompt += "\n- Include current, up-to-date information"
        
        prompt += f"""

ADDITIONAL INSTRUCTIONS:
- Create an engaging title
- Write a compelling introduction
- Use clear, well-structured paragraphs
- Include a strong conclusion
- Ensure content is original and plagiarism-free
- Maintain consistency with the specified {domain} domain expertise
- Target word count: {target_length} words

Please format your response as a complete article with a title and well-structured content."""
        
        return prompt, system_prompt
    
    @staticmethod
    def randomize_style_parameters(
        base_parameters: Dict[str, Any],
        domain: str
    ) -> Dict[str, Any]:
        """Randomize style parameters to create variation"""
        
        randomized = base_parameters.copy()
        
        # Domain-specific tone variations
        tone_variations = {
            "finance": ["analytical", "professional", "authoritative", "cautious", "data-driven"],
            "sports": ["enthusiastic", "engaging", "dramatic", "energetic", "passionate"],
            "technology": ["innovative", "technical", "forward-thinking", "analytical", "accessible"],
            "general": ["informative", "engaging", "professional", "conversational", "authoritative"]
        }
        
        # Structure variations
        structure_variations = {
            "finance": [
                ["executive_summary", "analysis", "market_implications", "conclusion"],
                ["introduction", "current_situation", "financial_analysis", "outlook"],
                ["overview", "key_factors", "impact_assessment", "recommendations"]
            ],
            "sports": [
                ["introduction", "game_highlights", "player_analysis", "season_impact"],
                ["breaking_news", "detailed_analysis", "statistics", "fan_reaction"],
                ["preview", "key_matchups", "predictions", "conclusion"]
            ],
            "technology": [
                ["introduction", "technical_overview", "market_analysis", "future_implications"],
                ["product_analysis", "technical_specifications", "competitive_landscape", "verdict"],
                ["trend_analysis", "innovation_impact", "industry_response", "outlook"]
            ],
            "general": [
                ["introduction", "main_points", "analysis", "conclusion"],
                ["overview", "detailed_examination", "implications", "summary"],
                ["background", "current_situation", "future_outlook", "takeaways"]
            ]
        }
        
        # Randomly select variations
        if "tone" in randomized:
            available_tones = tone_variations.get(domain, tone_variations["general"])
            randomized["tone"] = [random.choice(available_tones)]
        
        if "structure" in randomized:
            available_structures = structure_variations.get(domain, structure_variations["general"])
            randomized["structure"] = random.choice(available_structures)
        
        # Add some randomness to creativity level
        if "creativity_level" in randomized:
            base_creativity = randomized["creativity_level"]
            # Vary creativity by ±0.2, keeping within 0.0-1.0 bounds
            variation = random.uniform(-0.2, 0.2)
            randomized["creativity_level"] = max(0.0, min(1.0, base_creativity + variation))
        
        return randomized
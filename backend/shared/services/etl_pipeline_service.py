"""
ETL Pipeline Service
Comprehensive data ingestion, transformation, and loading system
"""
import asyncio
import json
import hashlib
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy import select, and_, or_, desc, func, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import gzip
import pickle

from ..database import get_db_session, get_redis_client
from ..models.agent_memory import AgentMemoryEntry, AgentLearningPattern
from ..utils.data_quality import DataQualityValidator
from ..utils.content_processor import ContentProcessor
from ..utils.domain_classifier import DomainClassifier
from ..logging import get_logger

logger = get_logger(__name__)

@dataclass
class ETLJobConfig:
    """Configuration for ETL jobs"""
    job_id: str
    source_type: str  # rss, api, file, stream
    domain: str
    schedule: str  # cron expression
    batch_size: int = 1000
    parallel_workers: int = 4
    quality_threshold: float = 0.7
    deduplication_enabled: bool = True
    transformation_rules: Dict[str, Any] = None
    output_targets: List[str] = None  # database, redis, file, etc.

class ContentStagingArea:
    """Staging area for content before processing"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.staging_ttl = 86400  # 24 hours
    
    async def stage_content(self, content: Dict[str, Any], source_id: str) -> str:
        """Stage content for processing"""
        content_id = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        staging_key = f"staging:{source_id}:{content_id}"
        
        await self.redis.setex(
            staging_key,
            self.staging_ttl,
            json.dumps(content, default=str)
        )
        
        # Add to processing queue
        await self.redis.lpush(f"queue:processing:{source_id}", content_id)
        
        return content_id
    
    async def get_staged_content(self, source_id: str, content_id: str) -> Optional[Dict]:
        """Retrieve staged content"""
        staging_key = f"staging:{source_id}:{content_id}"
        content_data = await self.redis.get(staging_key)
        
        if content_data:
            return json.loads(content_data)
        return None
    
    async def get_processing_queue(self, source_id: str, limit: int = 100) -> List[str]:
        """Get content IDs from processing queue"""
        content_ids = await self.redis.lrange(
            f"queue:processing:{source_id}", 0, limit - 1
        )
        
        # Remove retrieved items from queue
        if content_ids:
            await self.redis.ltrim(
                f"queue:processing:{source_id}", limit, -1
            )
        
        return content_ids

class RSSDataExtractor:
    """RSS feed data extraction"""
    
    def __init__(self):
        self.session = None
        self.user_agent = "Prism Content Extractor 1.0"
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers={'User-Agent': self.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def extract_from_feeds(self, feed_urls: List[str], domain: str) -> List[Dict[str, Any]]:
        """Extract content from multiple RSS feeds"""
        extracted_content = []
        
        tasks = [self.extract_from_feed(url, domain) for url in feed_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"RSS extraction failed: {result}")
            else:
                extracted_content.extend(result)
        
        return extracted_content
    
    async def extract_from_feed(self, feed_url: str, domain: str) -> List[Dict[str, Any]]:
        """Extract content from single RSS feed"""
        try:
            async with self.session.get(feed_url) as response:
                if response.status != 200:
                    logger.warning(f"RSS feed returned {response.status}: {feed_url}")
                    return []
                
                feed_content = await response.text()
                
            # Parse RSS feed
            feed = feedparser.parse(feed_content)
            
            if feed.bozo:
                logger.warning(f"Malformed RSS feed: {feed_url}")
            
            extracted_items = []
            
            for entry in feed.entries:
                try:
                    item = await self._extract_feed_item(entry, feed_url, domain)
                    if item:
                        extracted_items.append(item)
                except Exception as e:
                    logger.error(f"Failed to extract feed item: {e}")
                    continue
            
            logger.info(f"Extracted {len(extracted_items)} items from {feed_url}")
            return extracted_items
            
        except Exception as e:
            logger.error(f"RSS feed extraction failed for {feed_url}: {e}")
            return []
    
    async def _extract_feed_item(self, entry: Any, feed_url: str, domain: str) -> Optional[Dict[str, Any]]:
        """Extract individual feed item"""
        
        # Extract basic information
        title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        
        if not title or not link:
            return None
        
        # Extract content
        content = self._extract_content_from_entry(entry)
        if not content or len(content.strip()) < 100:
            # Try to fetch full content from link
            content = await self._fetch_full_content(link)
        
        # Extract metadata
        published_date = self._parse_published_date(entry)
        author = getattr(entry, 'author', '').strip()
        tags = self._extract_tags(entry)
        
        # Generate content hash for deduplication
        content_hash = hashlib.sha256(
            (title + content).encode('utf-8')
        ).hexdigest()
        
        return {
            'source_type': 'rss',
            'source_url': link,
            'feed_url': feed_url,
            'title': title,
            'content': content,
            'author': author,
            'published_date': published_date,
            'tags': tags,
            'domain': domain,
            'content_hash': content_hash,
            'extracted_at': datetime.utcnow(),
            'word_count': len(content.split()) if content else 0,
            'metadata': {
                'feed_title': getattr(entry, 'feed', {}).get('title', ''),
                'categories': getattr(entry, 'categories', []),
                'language': getattr(entry, 'language', 'en')
            }
        }
    
    def _extract_content_from_entry(self, entry) -> str:
        """Extract content text from feed entry"""
        content_candidates = [
            getattr(entry, 'content', [{}])[0].get('value', ''),
            getattr(entry, 'description', ''),
            getattr(entry, 'summary', '')
        ]
        
        for content in content_candidates:
            if content and len(content.strip()) > 50:
                # Clean HTML
                soup = BeautifulSoup(content, 'html.parser')
                return soup.get_text().strip()
        
        return ''
    
    async def _fetch_full_content(self, url: str) -> str:
        """Fetch full content from article URL"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return ''
                
                html_content = await response.text()
                
            # Extract main content using readability heuristics
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'aside']):
                element.decompose()
            
            # Find main content area
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', class_=re.compile(r'content|article|post')) or
                soup.find('div', id=re.compile(r'content|article|post'))
            )
            
            if main_content:
                return main_content.get_text().strip()
            else:
                # Fallback to body content
                body = soup.find('body')
                return body.get_text().strip() if body else ''
                
        except Exception as e:
            logger.warning(f"Failed to fetch full content from {url}: {e}")
            return ''
    
    def _parse_published_date(self, entry) -> Optional[datetime]:
        """Parse published date from feed entry"""
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        return datetime(*time_struct[:6])
                    except (ValueError, TypeError):
                        continue
        
        # Try string date fields
        string_fields = ['published', 'updated']
        for field in string_fields:
            if hasattr(entry, field):
                date_str = getattr(entry, field)
                if date_str:
                    try:
                        from dateutil import parser
                        return parser.parse(date_str)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _extract_tags(self, entry) -> List[str]:
        """Extract tags from feed entry"""
        tags = []
        
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    tags.append(tag.term)
        
        if hasattr(entry, 'categories'):
            tags.extend([cat.get('term', cat) if isinstance(cat, dict) else str(cat) 
                        for cat in entry.categories])
        
        return list(set(tags))  # Remove duplicates

class DataTransformationEngine:
    """Content transformation and normalization"""
    
    def __init__(self):
        self.content_processor = ContentProcessor()
        self.domain_classifier = DomainClassifier()
        self.quality_validator = DataQualityValidator()
        
    async def transform_content_batch(
        self, 
        raw_content: List[Dict[str, Any]], 
        transformation_rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform batch of raw content"""
        
        transformed_content = []
        
        # Process in parallel batches
        batch_size = transformation_rules.get('batch_size', 100)
        
        for i in range(0, len(raw_content), batch_size):
            batch = raw_content[i:i + batch_size]
            
            tasks = [self.transform_single_content(item, transformation_rules) 
                    for item in batch]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Content transformation failed: {result}")
                elif result:
                    transformed_content.append(result)
        
        return transformed_content
    
    async def transform_single_content(
        self, 
        content: Dict[str, Any], 
        rules: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Transform single content item"""
        
        try:
            # Clean and normalize text content
            if 'content' in content:
                content['content'] = await self.content_processor.clean_text(
                    content['content']
                )
            
            if 'title' in content:
                content['title'] = await self.content_processor.clean_text(
                    content['title'], preserve_formatting=False
                )
            
            # Classify domain if not specified
            if not content.get('domain') or content['domain'] == 'general':
                classified_domain = await self.domain_classifier.classify_content(
                    content.get('title', '') + ' ' + content.get('content', '')
                )
                content['domain'] = classified_domain
            
            # Extract and normalize metadata
            content = await self._normalize_metadata(content, rules)
            
            # Validate content quality
            quality_result = await self.quality_validator.validate_content_quality(
                content, content.get('domain', 'general')
            )
            
            content['quality_score'] = quality_result['overall_score']
            content['quality_issues'] = quality_result.get('issues', [])
            
            # Apply domain-specific transformations
            content = await self._apply_domain_transformations(content, rules)
            
            # Generate derived fields
            content = await self._generate_derived_fields(content)
            
            return content
            
        except Exception as e:
            logger.error(f"Content transformation failed: {e}")
            return None
    
    async def _normalize_metadata(
        self, 
        content: Dict[str, Any], 
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize metadata fields"""
        
        # Normalize URLs
        if content.get('source_url'):
            content['source_url'] = self._normalize_url(content['source_url'])
        
        # Normalize dates
        if content.get('published_date') and isinstance(content['published_date'], str):
            try:
                from dateutil import parser
                content['published_date'] = parser.parse(content['published_date'])
            except:
                content['published_date'] = None
        
        # Normalize tags
        if content.get('tags'):
            content['tags'] = [
                tag.lower().strip() 
                for tag in content['tags'] 
                if tag and len(tag.strip()) > 2
            ]
            content['tags'] = list(set(content['tags']))  # Remove duplicates
        
        # Normalize author
        if content.get('author'):
            content['author'] = content['author'].strip().title()
        
        return content
    
    async def _apply_domain_transformations(
        self, 
        content: Dict[str, Any], 
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply domain-specific transformations"""
        
        domain = content.get('domain', 'general')
        domain_rules = rules.get('domain_specific', {}).get(domain, {})
        
        if domain == 'finance':
            # Extract financial entities and metrics
            content = await self._extract_financial_entities(content)
            
        elif domain == 'sports':
            # Extract sports entities and scores
            content = await self._extract_sports_entities(content)
            
        elif domain == 'technology':
            # Extract technology entities and trends
            content = await self._extract_tech_entities(content)
        
        return content
    
    async def _extract_financial_entities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract financial entities from content"""
        
        text = content.get('content', '')
        
        # Extract stock symbols (simplified regex)
        stock_symbols = re.findall(r'\b[A-Z]{2,5}\b', text)
        
        # Extract currency amounts
        currency_amounts = re.findall(r'[\$€£¥]\s*[\d,]+\.?\d*[MBK]?', text)
        
        # Extract percentage values
        percentages = re.findall(r'\d+\.?\d*%', text)
        
        if not content.get('entities'):
            content['entities'] = {}
        
        content['entities'].update({
            'stock_symbols': list(set(stock_symbols)),
            'currency_amounts': currency_amounts,
            'percentages': percentages
        })
        
        return content
    
    async def _extract_sports_entities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sports entities from content"""
        
        text = content.get('content', '')
        
        # Extract scores (simplified)
        scores = re.findall(r'\b\d+[-–]\d+\b', text)
        
        # Extract team names (this would need a more sophisticated approach)
        # For now, just extract capitalized words that might be team names
        potential_teams = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        if not content.get('entities'):
            content['entities'] = {}
        
        content['entities'].update({
            'scores': scores,
            'potential_teams': potential_teams[:10]  # Limit to avoid noise
        })
        
        return content
    
    async def _extract_tech_entities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technology entities from content"""
        
        text = content.get('content', '')
        
        # Common tech terms and companies
        tech_terms = [
            'AI', 'ML', 'blockchain', 'cryptocurrency', 'API', 'cloud', 
            'SaaS', 'IoT', 'VR', 'AR', 'cybersecurity', 'data science'
        ]
        
        tech_companies = [
            'Google', 'Apple', 'Microsoft', 'Amazon', 'Meta', 'Tesla',
            'Netflix', 'Spotify', 'Uber', 'Airbnb', 'Twitter', 'LinkedIn'
        ]
        
        found_terms = [term for term in tech_terms if term.lower() in text.lower()]
        found_companies = [company for company in tech_companies if company in text]
        
        if not content.get('entities'):
            content['entities'] = {}
        
        content['entities'].update({
            'tech_terms': found_terms,
            'companies': found_companies
        })
        
        return content
    
    async def _generate_derived_fields(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate derived fields from content"""
        
        # Calculate reading time (assuming 200 words per minute)
        word_count = content.get('word_count', 0)
        content['estimated_reading_time'] = max(1, round(word_count / 200))
        
        # Generate content summary if content is long
        if word_count > 500:
            content['auto_summary'] = await self.content_processor.generate_summary(
                content.get('content', ''), max_length=200
            )
        
        # Extract keywords
        content['keywords'] = await self.content_processor.extract_keywords(
            content.get('content', ''), max_keywords=10
        )
        
        # Generate SEO metadata
        if content.get('title') and content.get('content'):
            content['seo_metadata'] = await self._generate_seo_metadata(content)
        
        return content
    
    async def _generate_seo_metadata(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SEO metadata"""
        
        title = content.get('title', '')
        text = content.get('content', '')
        
        # Generate meta description from first paragraph or summary
        first_paragraph = text.split('\n')[0][:160] if text else title[:160]
        meta_description = first_paragraph + '...' if len(first_paragraph) == 160 else first_paragraph
        
        return {
            'meta_description': meta_description,
            'canonical_url': content.get('source_url', ''),
            'og_title': title,
            'og_description': meta_description,
            'og_type': 'article'
        }
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL format"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove tracking parameters
        parsed = urlparse(url)
        # This is a simplified approach - in practice, you'd want more sophisticated URL cleaning
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

class DataLoader:
    """Load transformed data into various targets"""
    
    def __init__(self):
        self.staging = ContentStagingArea()
        
    async def load_to_database(
        self, 
        content_batch: List[Dict[str, Any]], 
        table_name: str = 'content_items'
    ) -> Dict[str, Any]:
        """Load content batch to database"""
        
        successful_loads = 0
        failed_loads = 0
        duplicate_skips = 0
        
        async with get_db_session() as session:
            for content in content_batch:
                try:
                    # Check for duplicates using content hash
                    if await self._is_duplicate_content(session, content):
                        duplicate_skips += 1
                        continue
                    
                    # Convert to database model format
                    db_record = self._convert_to_db_format(content, table_name)
                    
                    # Insert using upsert to handle conflicts
                    stmt = pg_insert(self._get_table_class(table_name)).values(db_record)
                    stmt = stmt.on_conflict_do_nothing()
                    
                    await session.execute(stmt)
                    successful_loads += 1
                    
                except Exception as e:
                    logger.error(f"Failed to load content to database: {e}")
                    failed_loads += 1
            
            await session.commit()
        
        return {
            'successful_loads': successful_loads,
            'failed_loads': failed_loads,
            'duplicate_skips': duplicate_skips,
            'total_processed': len(content_batch)
        }
    
    async def load_to_cache(
        self, 
        content_batch: List[Dict[str, Any]], 
        cache_ttl: int = 3600
    ) -> int:
        """Load content batch to Redis cache"""
        
        cached_count = 0
        
        for content in content_batch:
            try:
                cache_key = f"content:{content.get('domain', 'general')}:{content.get('content_hash', '')[:8]}"
                
                cache_data = {
                    'title': content.get('title'),
                    'content': content.get('content'),
                    'quality_score': content.get('quality_score'),
                    'keywords': content.get('keywords', []),
                    'entities': content.get('entities', {}),
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                await self.staging.redis.setex(
                    cache_key,
                    cache_ttl,
                    json.dumps(cache_data, default=str)
                )
                
                cached_count += 1
                
            except Exception as e:
                logger.error(f"Failed to cache content: {e}")
        
        return cached_count
    
    async def _is_duplicate_content(
        self, 
        session: AsyncSession, 
        content: Dict[str, Any]
    ) -> bool:
        """Check if content already exists using content hash"""
        
        content_hash = content.get('content_hash')
        if not content_hash:
            return False
        
        # This is a placeholder - you'd check against your actual content table
        # result = await session.execute(
        #     select(ContentItem).where(ContentItem.content_hash == content_hash)
        # )
        # return result.first() is not None
        
        # For now, use Redis to track recent hashes
        hash_key = f"content_hash:{content_hash}"
        exists = await self.staging.redis.exists(hash_key)
        
        if not exists:
            # Mark as seen for 24 hours
            await self.staging.redis.setex(hash_key, 86400, '1')
        
        return bool(exists)

class ETLPipelineOrchestrator:
    """Main ETL pipeline orchestration"""
    
    def __init__(self):
        self.staging = ContentStagingArea()
        self.extractor = None  # Will be set based on source type
        self.transformer = DataTransformationEngine()
        self.loader = DataLoader()
        self.quality_validator = DataQualityValidator()
        
    async def run_etl_job(self, job_config: ETLJobConfig) -> Dict[str, Any]:
        """Run complete ETL job"""
        
        job_start_time = datetime.utcnow()
        logger.info(f"Starting ETL job: {job_config.job_id}")
        
        try:
            # Extract phase
            extracted_data = await self._extract_data(job_config)
            logger.info(f"Extracted {len(extracted_data)} items")
            
            if not extracted_data:
                return self._create_job_result(job_config, job_start_time, "no_data")
            
            # Transform phase
            transformed_data = await self._transform_data(extracted_data, job_config)
            logger.info(f"Transformed {len(transformed_data)} items")
            
            # Quality filtering
            if job_config.quality_threshold > 0:
                transformed_data = await self._filter_by_quality(
                    transformed_data, job_config.quality_threshold
                )
                logger.info(f"Quality filtered to {len(transformed_data)} items")
            
            # Deduplication
            if job_config.deduplication_enabled:
                transformed_data = await self._deduplicate_content(transformed_data)
                logger.info(f"Deduplicated to {len(transformed_data)} items")
            
            # Load phase
            load_results = await self._load_data(transformed_data, job_config)
            
            return self._create_job_result(
                job_config, job_start_time, "success", 
                extracted_count=len(extracted_data),
                transformed_count=len(transformed_data),
                load_results=load_results
            )
            
        except Exception as e:
            logger.error(f"ETL job failed: {job_config.job_id}: {e}")
            return self._create_job_result(job_config, job_start_time, "failed", error=str(e))
    
    async def _extract_data(self, job_config: ETLJobConfig) -> List[Dict[str, Any]]:
        """Extract data based on source type"""
        
        if job_config.source_type == 'rss':
            async with RSSDataExtractor() as extractor:
                feed_urls = job_config.transformation_rules.get('feed_urls', [])
                return await extractor.extract_from_feeds(feed_urls, job_config.domain)
        
        elif job_config.source_type == 'api':
            # Implement API extraction
            return await self._extract_from_api(job_config)
        
        elif job_config.source_type == 'file':
            # Implement file extraction
            return await self._extract_from_file(job_config)
        
        else:
            raise ValueError(f"Unsupported source type: {job_config.source_type}")
    
    async def _transform_data(
        self, 
        raw_data: List[Dict[str, Any]], 
        job_config: ETLJobConfig
    ) -> List[Dict[str, Any]]:
        """Transform extracted data"""
        
        transformation_rules = job_config.transformation_rules or {}
        
        return await self.transformer.transform_content_batch(
            raw_data, transformation_rules
        )
    
    async def _filter_by_quality(
        self, 
        data: List[Dict[str, Any]], 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Filter content by quality threshold"""
        
        return [
            item for item in data 
            if item.get('quality_score', 0) >= threshold
        ]
    
    async def _deduplicate_content(
        self, 
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate content based on content hash"""
        
        seen_hashes = set()
        deduplicated = []
        
        for item in data:
            content_hash = item.get('content_hash')
            if content_hash and content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(item)
        
        return deduplicated
    
    async def _load_data(
        self, 
        data: List[Dict[str, Any]], 
        job_config: ETLJobConfig
    ) -> Dict[str, Any]:
        """Load data to configured targets"""
        
        load_results = {}
        
        output_targets = job_config.output_targets or ['database']
        
        if 'database' in output_targets:
            db_result = await self.loader.load_to_database(data)
            load_results['database'] = db_result
        
        if 'cache' in output_targets:
            cache_count = await self.loader.load_to_cache(data)
            load_results['cache'] = {'cached_count': cache_count}
        
        return load_results
    
    def _create_job_result(
        self, 
        job_config: ETLJobConfig, 
        start_time: datetime, 
        status: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create standardized job result"""
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'job_id': job_config.job_id,
            'status': status,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'source_type': job_config.source_type,
            'domain': job_config.domain,
            **kwargs
        }
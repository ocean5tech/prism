"""
Content Ingestion ETL Pipeline
Processes RSS feeds, API data, and webhooks into structured content for generation
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import asyncpg
import aioredis
import feedparser
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
import httpx
from bs4 import BeautifulSoup
import openai
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from shared.logging import get_logger
from shared.config import settings

logger = get_logger(__name__)

class SourceType(Enum):
    RSS = "rss"
    API = "api"
    WEBHOOK = "webhook"
    MANUAL = "manual"

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ContentItem:
    title: str
    content: str
    url: Optional[str] = None
    published_date: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    source_id: Optional[str] = None

class ContentIngestionPipeline:
    def __init__(self):
        self.db_engine = create_async_engine(settings.DATABASE_URL)
        self.redis = None
        self.qdrant_client = None
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def initialize(self):
        """Initialize connections to external services"""
        self.redis = await aioredis.from_url(settings.REDIS_URL)
        self.qdrant_client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        
        # Ensure vector collections exist
        await self.setup_vector_collections()
        logger.info("Content ingestion pipeline initialized")

    async def setup_vector_collections(self):
        """Set up Qdrant collections for content similarity"""
        collections = [
            ("content_vectors", 1536),  # OpenAI embedding dimension
            ("agent_memory_vectors", 768),  # Smaller dimension for memory patterns
        ]
        
        for collection_name, vector_size in collections:
            try:
                await self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size, 
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created vector collection: {collection_name}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.error(f"Failed to create collection {collection_name}: {e}")

    async def process_rss_feeds(self, limit: int = 100):
        """Process RSS feeds for all active sources"""
        async with AsyncSession(self.db_engine) as session:
            # Get active RSS sources
            result = await session.execute(
                text("""
                    SELECT cs.id, cs.source_url, cs.domain_id, cs.source_config,
                           cs.last_processed, d.name as domain_name
                    FROM content_sources cs
                    JOIN domains d ON cs.domain_id = d.id
                    WHERE cs.source_type = 'rss' AND cs.is_active = true
                    ORDER BY cs.last_processed ASC NULLS FIRST
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            
            sources = result.fetchall()
            logger.info(f"Processing {len(sources)} RSS sources")
            
            tasks = [
                self.process_single_rss_source(source) 
                for source in sources
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log processing results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            logger.info(f"RSS processing complete: {successful} successful, {failed} failed")
            
            return {"successful": successful, "failed": failed}

    async def process_single_rss_source(self, source) -> Dict[str, Any]:
        """Process individual RSS source"""
        source_id, source_url, domain_id, source_config, last_processed, domain_name = source
        
        try:
            # Check cache first
            cache_key = f"rss_content:{hashlib.md5(source_url.encode()).hexdigest()}"
            cached_etag = await self.redis.get(f"{cache_key}:etag")
            
            headers = {}
            if cached_etag:
                headers['If-None-Match'] = cached_etag.decode()
                
            # Fetch RSS feed
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    source_url, 
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 304:
                    logger.debug(f"RSS feed unchanged: {source_url}")
                    return {"source_id": source_id, "new_items": 0}
                    
                response.raise_for_status()
                
            # Parse RSS feed
            feed = feedparser.parse(response.text)
            
            # Cache ETag for next request
            if 'etag' in response.headers:
                await self.redis.setex(
                    f"{cache_key}:etag",
                    3600,  # 1 hour cache
                    response.headers['etag']
                )
            
            # Process feed entries
            new_items = 0
            for entry in feed.entries:
                content_item = self.extract_content_from_entry(entry, source_id, domain_name)
                if content_item:
                    # Check for duplicates
                    content_hash = self.generate_content_hash(content_item)
                    
                    duplicate_check = await self.redis.get(f"content_hash:{content_hash}")
                    if duplicate_check:
                        continue
                    
                    # Store in database and vector store
                    await self.store_content_item(content_item, domain_id, source_id, content_hash)
                    
                    # Cache hash to prevent duplicates
                    await self.redis.setex(f"content_hash:{content_hash}", 86400, "1")
                    new_items += 1
            
            # Update last processed timestamp
            async with AsyncSession(self.db_engine) as session:
                await session.execute(
                    text("UPDATE content_sources SET last_processed = NOW() WHERE id = :source_id"),
                    {"source_id": source_id}
                )
                await session.commit()
            
            logger.info(f"Processed RSS source {source_url}: {new_items} new items")
            return {"source_id": source_id, "new_items": new_items}
            
        except Exception as e:
            logger.error(f"Error processing RSS source {source_url}: {e}")
            return {"source_id": source_id, "error": str(e)}

    def extract_content_from_entry(self, entry, source_id: str, domain_name: str) -> Optional[ContentItem]:
        """Extract structured content from RSS entry"""
        try:
            # Get title
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # Get content (try multiple fields)
            content = ""
            for field in ['content', 'summary', 'description']:
                if field in entry:
                    if isinstance(entry[field], list):
                        content = entry[field][0].get('value', '')
                    else:
                        content = str(entry[field])
                    break
            
            if not content:
                return None
            
            # Clean HTML content
            soup = BeautifulSoup(content, 'html.parser')
            clean_content = soup.get_text().strip()
            
            # Skip if content too short
            if len(clean_content) < 100:
                return None
            
            # Extract metadata
            metadata = {
                'source_domain': domain_name,
                'author': entry.get('author', ''),
                'tags': [tag.term for tag in entry.get('tags', [])],
                'category': entry.get('category', ''),
                'language': entry.get('language', 'en'),
                'word_count': len(clean_content.split()),
                'extraction_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Parse published date
            published_date = None
            if 'published_parsed' in entry and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            
            return ContentItem(
                title=title,
                content=clean_content,
                url=entry.get('link', ''),
                published_date=published_date,
                metadata=metadata,
                source_id=source_id
            )
            
        except Exception as e:
            logger.error(f"Error extracting content from entry: {e}")
            return None

    def generate_content_hash(self, content_item: ContentItem) -> str:
        """Generate unique hash for content deduplication"""
        content_for_hash = f"{content_item.title}|{content_item.content[:500]}"
        return hashlib.sha256(content_for_hash.encode()).hexdigest()

    async def store_content_item(self, content_item: ContentItem, domain_id: str, 
                                source_id: str, content_hash: str):
        """Store content item in database and vector store"""
        try:
            # Generate vector embedding
            embedding = await self.generate_embedding(
                f"{content_item.title} {content_item.content[:1000]}"
            )
            
            # Store in PostgreSQL
            async with AsyncSession(self.db_engine) as session:
                result = await session.execute(
                    text("""
                        INSERT INTO hot_content 
                        (domain_id, source_id, title, content, original_url, 
                         content_hash, metadata, vector_embedding, processing_status)
                        VALUES (:domain_id, :source_id, :title, :content, :url,
                                :content_hash, :metadata, :embedding, 'pending')
                        RETURNING id
                    """),
                    {
                        "domain_id": domain_id,
                        "source_id": source_id,
                        "title": content_item.title,
                        "content": content_item.content,
                        "url": content_item.url,
                        "content_hash": content_hash,
                        "metadata": json.dumps(content_item.metadata),
                        "embedding": embedding
                    }
                )
                content_id = result.fetchone()[0]
                await session.commit()
            
            # Store vector in Qdrant for similarity search
            await self.qdrant_client.upsert(
                collection_name="content_vectors",
                points=[
                    PointStruct(
                        id=str(content_id),
                        vector=embedding,
                        payload={
                            "title": content_item.title,
                            "domain_id": str(domain_id),
                            "source_id": str(source_id),
                            "content_hash": content_hash,
                            "word_count": content_item.metadata.get('word_count', 0),
                            "published_date": content_item.published_date.isoformat() if content_item.published_date else None
                        }
                    )
                ]
            )
            
            # Queue for processing by generation service
            await self.redis.lpush(
                "content_generation_queue", 
                json.dumps({
                    "content_id": str(content_id),
                    "domain_id": str(domain_id),
                    "priority": "normal"
                })
            )
            
            logger.debug(f"Stored content item: {content_id}")
            
        except Exception as e:
            logger.error(f"Error storing content item: {e}")
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for content"""
        try:
            # Truncate text to fit token limits
            text = text[:8000]  # Approximate token limit
            
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536

    async def find_similar_content(self, content_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar content using vector similarity"""
        try:
            # Get content vector from database
            async with AsyncSession(self.db_engine) as session:
                result = await session.execute(
                    text("SELECT vector_embedding FROM hot_content WHERE id = :content_id"),
                    {"content_id": content_id}
                )
                row = result.fetchone()
                if not row or not row[0]:
                    return []
                
                query_vector = row[0]
            
            # Search similar vectors in Qdrant
            search_result = await self.qdrant_client.search(
                collection_name="content_vectors",
                query_vector=query_vector,
                limit=limit + 1,  # +1 to exclude self
                score_threshold=0.7
            )
            
            # Filter out the query content itself and format results
            similar_items = []
            for hit in search_result:
                if hit.id != content_id:
                    similar_items.append({
                        "content_id": hit.id,
                        "similarity_score": hit.score,
                        "payload": hit.payload
                    })
            
            return similar_items[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar content: {e}")
            return []

    async def process_api_data(self, api_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process content from external APIs"""
        try:
            api_url = api_config['url']
            headers = api_config.get('headers', {})
            params = api_config.get('params', {})
            
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                
            # Transform API data based on source configuration
            content_items = self.transform_api_data(data, api_config)
            
            processed_count = 0
            for item in content_items:
                content_hash = self.generate_content_hash(item)
                
                # Check for duplicates
                duplicate_check = await self.redis.get(f"content_hash:{content_hash}")
                if not duplicate_check:
                    await self.store_content_item(
                        item, 
                        api_config['domain_id'], 
                        api_config['source_id'], 
                        content_hash
                    )
                    await self.redis.setex(f"content_hash:{content_hash}", 86400, "1")
                    processed_count += 1
            
            logger.info(f"Processed API data: {processed_count} new items")
            return {"processed_count": processed_count}
            
        except Exception as e:
            logger.error(f"Error processing API data: {e}")
            return {"error": str(e)}

    def transform_api_data(self, data: Dict[str, Any], config: Dict[str, Any]) -> List[ContentItem]:
        """Transform API response data into ContentItem objects"""
        items = []
        
        # This is a configurable transformation based on API source
        data_path = config.get('data_path', [])
        title_field = config.get('title_field', 'title')
        content_field = config.get('content_field', 'content')
        url_field = config.get('url_field', 'url')
        date_field = config.get('date_field', 'published_date')
        
        # Navigate to data array
        data_array = data
        for path in data_path:
            data_array = data_array.get(path, [])
        
        if not isinstance(data_array, list):
            data_array = [data_array]
        
        for item_data in data_array:
            try:
                title = item_data.get(title_field, '').strip()
                content = item_data.get(content_field, '').strip()
                
                if not title or not content or len(content) < 100:
                    continue
                
                # Parse date
                published_date = None
                if date_field in item_data:
                    try:
                        published_date = datetime.fromisoformat(
                            item_data[date_field].replace('Z', '+00:00')
                        )
                    except:
                        pass
                
                metadata = {
                    'api_source': config.get('source_name', 'unknown'),
                    'raw_data_keys': list(item_data.keys()),
                    'extraction_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                items.append(ContentItem(
                    title=title,
                    content=content,
                    url=item_data.get(url_field, ''),
                    published_date=published_date,
                    metadata=metadata
                ))
                
            except Exception as e:
                logger.warning(f"Error transforming API item: {e}")
                continue
        
        return items

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data based on retention policies"""
        try:
            async with AsyncSession(self.db_engine) as session:
                # Move old hot data to warm storage
                result = await session.execute(
                    text("SELECT migrate_hot_to_warm()")
                )
                migrated_count = result.fetchone()[0]
                
                # Clean up old cache entries
                await self.redis.flushdb()  # Clean all cache (in production, be more selective)
                
                logger.info(f"Data cleanup complete: {migrated_count} records migrated")
                return {"migrated_records": migrated_count}
                
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            return {"error": str(e)}

    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        try:
            async with AsyncSession(self.db_engine) as session:
                # Content processing stats
                result = await session.execute(
                    text("""
                        SELECT 
                            processing_status,
                            COUNT(*) as count,
                            AVG(CASE WHEN quality_score IS NOT NULL THEN quality_score END) as avg_quality
                        FROM hot_content 
                        WHERE created_at >= NOW() - INTERVAL '24 hours'
                        GROUP BY processing_status
                    """)
                )
                
                processing_stats = {
                    row.processing_status: {
                        "count": row.count, 
                        "avg_quality": float(row.avg_quality) if row.avg_quality else None
                    }
                    for row in result.fetchall()
                }
                
                # Domain distribution
                result = await session.execute(
                    text("""
                        SELECT d.name, COUNT(hc.id) as content_count
                        FROM domains d
                        LEFT JOIN hot_content hc ON d.id = hc.domain_id 
                            AND hc.created_at >= NOW() - INTERVAL '24 hours'
                        GROUP BY d.name
                    """)
                )
                
                domain_stats = {
                    row.name: row.content_count 
                    for row in result.fetchall()
                }
                
                # Queue status
                queue_length = await self.redis.llen("content_generation_queue")
                
            return {
                "processing_stats": processing_stats,
                "domain_distribution": domain_stats,
                "queue_length": queue_length,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting pipeline stats: {e}")
            return {"error": str(e)}

# Main pipeline runner
async def run_ingestion_pipeline():
    """Main entry point for content ingestion"""
    pipeline = ContentIngestionPipeline()
    
    try:
        await pipeline.initialize()
        
        # Process RSS feeds
        rss_results = await pipeline.process_rss_feeds()
        logger.info(f"RSS processing results: {rss_results}")
        
        # Clean up old data
        cleanup_results = await pipeline.cleanup_old_data()
        logger.info(f"Cleanup results: {cleanup_results}")
        
        # Get final stats
        stats = await pipeline.get_pipeline_stats()
        logger.info(f"Pipeline stats: {stats}")
        
        return {
            "rss_results": rss_results,
            "cleanup_results": cleanup_results,
            "final_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise
    finally:
        if pipeline.redis:
            await pipeline.redis.close()
        if pipeline.qdrant_client:
            await pipeline.qdrant_client.close()

if __name__ == "__main__":
    asyncio.run(run_ingestion_pipeline())
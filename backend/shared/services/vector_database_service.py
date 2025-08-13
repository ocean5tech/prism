"""
Vector Database Service
Qdrant integration for content similarity and pattern detection
"""
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, Range, GeoBoundingBox, PayloadSchemaType,
    CreateCollection, UpdateCollection, CollectionInfo,
    SearchRequest, RecommendRequest, CountRequest,
    UpdateVectors, DeleteVectors, UpsertVectors
)
from qdrant_client.http.exceptions import UnexpectedResponse
import openai
from sentence_transformers import SentenceTransformer
import tiktoken

from ..database import get_redis_client
from ..logging import get_logger
from ..utils.embedding_service import EmbeddingService

logger = get_logger(__name__)

@dataclass
class VectorSearchResult:
    """Vector search result with metadata"""
    id: str
    score: float
    payload: Dict[str, Any]
    vector: Optional[List[float]] = None

@dataclass
class SimilarityCluster:
    """Content similarity cluster"""
    cluster_id: str
    center_point: List[float]
    content_ids: List[str]
    similarity_threshold: float
    cluster_quality: float
    representative_content: Optional[Dict[str, Any]] = None

class VectorDatabaseService:
    """Comprehensive vector database service using Qdrant"""
    
    def __init__(self, qdrant_url: str = "http://qdrant:6333"):
        self.client = QdrantClient(url=qdrant_url)
        self.redis = get_redis_client()
        self.embedding_service = EmbeddingService()
        
        # Collection configurations
        self.collections_config = {
            'content_embeddings': {
                'vector_size': 1536,  # OpenAI ada-002 embedding size
                'distance': Distance.COSINE,
                'description': 'Main content embeddings for similarity search'
            },
            'pattern_embeddings': {
                'vector_size': 1536,
                'distance': Distance.COSINE,
                'description': 'Pattern embeddings for adversarial detection'
            },
            'agent_memory': {
                'vector_size': 1536,
                'distance': Distance.COSINE,
                'description': 'Agent memory vectors for learning'
            },
            'user_preferences': {
                'vector_size': 768,  # Smaller embedding for user data
                'distance': Distance.COSINE,
                'description': 'User preference vectors'
            }
        }
        
        # Initialize collections
        asyncio.create_task(self._initialize_collections())
    
    async def _initialize_collections(self):
        """Initialize all required Qdrant collections"""
        for collection_name, config in self.collections_config.items():
            try:
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=config['vector_size'],
                        distance=config['distance']
                    )
                )
                logger.info(f"Created collection: {collection_name}")
                
                # Create indexes for efficient filtering
                await self._create_collection_indexes(collection_name)
                
            except UnexpectedResponse as e:
                if "already exists" in str(e):
                    logger.debug(f"Collection {collection_name} already exists")
                else:
                    logger.error(f"Failed to create collection {collection_name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error creating collection {collection_name}: {e}")
    
    async def _create_collection_indexes(self, collection_name: str):
        """Create payload indexes for efficient filtering"""
        common_indexes = [
            ("domain", PayloadSchemaType.KEYWORD),
            ("content_type", PayloadSchemaType.KEYWORD),
            ("created_at", PayloadSchemaType.DATETIME),
            ("quality_score", PayloadSchemaType.FLOAT),
        ]
        
        for field_name, schema_type in common_indexes:
            try:
                await self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=schema_type
                )
            except Exception as e:
                logger.debug(f"Index creation skipped for {field_name}: {e}")
    
    async def store_content_embedding(
        self,
        content_id: str,
        content_text: str,
        metadata: Dict[str, Any],
        collection_name: str = 'content_embeddings'
    ) -> bool:
        """Store content embedding with metadata"""
        
        try:
            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(content_text)
            
            # Prepare payload with metadata
            payload = {
                'content_id': content_id,
                'domain': metadata.get('domain', 'general'),
                'content_type': metadata.get('content_type', 'article'),
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'created_at': metadata.get('created_at', datetime.utcnow()).isoformat(),
                'quality_score': metadata.get('quality_score', 0.0),
                'word_count': metadata.get('word_count', 0),
                'tags': metadata.get('tags', []),
                'source_url': metadata.get('source_url', ''),
                'language': metadata.get('language', 'en')
            }
            
            # Create point
            point = PointStruct(
                id=content_id,
                vector=embedding,
                payload=payload
            )
            
            # Upsert to Qdrant
            result = await self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            # Cache embedding for quick access
            await self._cache_embedding(content_id, embedding, collection_name)
            
            logger.debug(f"Stored embedding for content: {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store content embedding: {content_id}: {e}")
            return False
    
    async def find_similar_content(
        self,
        query_text: str = None,
        query_vector: List[float] = None,
        collection_name: str = 'content_embeddings',
        filters: Dict[str, Any] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
        include_vectors: bool = False
    ) -> List[VectorSearchResult]:
        """Find similar content using vector search"""
        
        try:
            # Get query vector
            if query_vector is None:
                if query_text is None:
                    raise ValueError("Either query_text or query_vector must be provided")
                query_vector = await self.embedding_service.generate_embedding(query_text)
            
            # Build search filter
            search_filter = self._build_search_filter(filters) if filters else None
            
            # Perform search
            search_results = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=include_vectors
            )
            
            # Convert to VectorSearchResult objects
            results = []
            for result in search_results:
                results.append(VectorSearchResult(
                    id=result.id,
                    score=result.score,
                    payload=result.payload,
                    vector=result.vector if include_vectors else None
                ))
            
            logger.debug(f"Found {len(results)} similar content items")
            return results
            
        except Exception as e:
            logger.error(f"Similar content search failed: {e}")
            return []
    
    async def detect_content_patterns(
        self,
        content_batch: List[Dict[str, Any]],
        similarity_threshold: float = 0.85,
        min_cluster_size: int = 3
    ) -> List[SimilarityCluster]:
        """Detect patterns in content batch using clustering"""
        
        try:
            if len(content_batch) < min_cluster_size:
                return []
            
            # Generate embeddings for all content
            embeddings = []
            content_ids = []
            
            for content in content_batch:
                content_text = f"{content.get('title', '')} {content.get('content', '')}"
                embedding = await self.embedding_service.generate_embedding(content_text)
                embeddings.append(embedding)
                content_ids.append(content.get('id', content.get('content_id', '')))
            
            # Perform similarity-based clustering
            clusters = await self._cluster_embeddings(
                embeddings, content_ids, similarity_threshold, min_cluster_size
            )
            
            # Analyze clusters for patterns
            pattern_clusters = []
            for i, cluster in enumerate(clusters):
                if len(cluster['content_ids']) >= min_cluster_size:
                    cluster_quality = await self._calculate_cluster_quality(
                        cluster, content_batch
                    )
                    
                    similarity_cluster = SimilarityCluster(
                        cluster_id=f"cluster_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        center_point=cluster['center'],
                        content_ids=cluster['content_ids'],
                        similarity_threshold=similarity_threshold,
                        cluster_quality=cluster_quality,
                        representative_content=self._select_representative_content(
                            cluster['content_ids'], content_batch
                        )
                    )
                    
                    pattern_clusters.append(similarity_cluster)
            
            logger.info(f"Detected {len(pattern_clusters)} content patterns")
            return pattern_clusters
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []
    
    async def store_pattern_embedding(
        self,
        pattern_id: str,
        pattern_description: str,
        pattern_elements: List[str],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store pattern embedding for detection"""
        
        try:
            # Combine pattern description and elements for embedding
            pattern_text = f"{pattern_description} {' '.join(pattern_elements)}"
            embedding = await self.embedding_service.generate_embedding(pattern_text)
            
            # Prepare payload
            payload = {
                'pattern_id': pattern_id,
                'pattern_type': metadata.get('pattern_type', 'general'),
                'domain': metadata.get('domain', 'general'),
                'confidence': metadata.get('confidence', 0.0),
                'success_rate': metadata.get('success_rate', 0.0),
                'usage_count': metadata.get('usage_count', 0),
                'created_at': metadata.get('created_at', datetime.utcnow()).isoformat(),
                'pattern_elements': pattern_elements,
                'description': pattern_description
            }
            
            # Store in pattern embeddings collection
            point = PointStruct(
                id=pattern_id,
                vector=embedding,
                payload=payload
            )
            
            result = await self.client.upsert(
                collection_name='pattern_embeddings',
                points=[point]
            )
            
            logger.debug(f"Stored pattern embedding: {pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store pattern embedding: {pattern_id}: {e}")
            return False
    
    async def detect_similar_patterns(
        self,
        content_text: str,
        domain: str = None,
        confidence_threshold: float = 0.7,
        limit: int = 5
    ) -> List[VectorSearchResult]:
        """Detect patterns similar to given content"""
        
        filters = {}
        if domain:
            filters['domain'] = domain
        
        # Add minimum confidence filter
        filters['confidence'] = {'gte': confidence_threshold}
        
        return await self.find_similar_content(
            query_text=content_text,
            collection_name='pattern_embeddings',
            filters=filters,
            limit=limit,
            score_threshold=0.75
        )
    
    async def recommend_content(
        self,
        positive_examples: List[str],
        negative_examples: List[str] = None,
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[VectorSearchResult]:
        """Recommend content based on positive and negative examples"""
        
        try:
            # Build recommendation request
            search_filter = self._build_search_filter(filters) if filters else None
            
            recommend_request = RecommendRequest(
                positive=positive_examples,
                negative=negative_examples or [],
                filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            # Get recommendations from Qdrant
            recommendations = await self.client.recommend(
                collection_name='content_embeddings',
                **recommend_request.dict()
            )
            
            # Convert to VectorSearchResult objects
            results = []
            for result in recommendations:
                results.append(VectorSearchResult(
                    id=result.id,
                    score=result.score,
                    payload=result.payload
                ))
            
            logger.debug(f"Generated {len(results)} content recommendations")
            return results
            
        except Exception as e:
            logger.error(f"Content recommendation failed: {e}")
            return []
    
    async def analyze_content_diversity(
        self,
        content_ids: List[str],
        collection_name: str = 'content_embeddings'
    ) -> Dict[str, Any]:
        """Analyze diversity within a set of content"""
        
        try:
            # Retrieve vectors for content IDs
            points = await self.client.retrieve(
                collection_name=collection_name,
                ids=content_ids,
                with_vectors=True,
                with_payload=True
            )
            
            if len(points) < 2:
                return {'diversity_score': 0.0, 'analysis': 'Insufficient content for diversity analysis'}
            
            # Extract vectors
            vectors = [point.vector for point in points if point.vector]
            
            if not vectors:
                return {'diversity_score': 0.0, 'analysis': 'No vectors found for content'}
            
            # Calculate pairwise similarities
            similarities = []
            for i in range(len(vectors)):
                for j in range(i + 1, len(vectors)):
                    similarity = self._calculate_cosine_similarity(vectors[i], vectors[j])
                    similarities.append(similarity)
            
            # Calculate diversity metrics
            avg_similarity = np.mean(similarities)
            diversity_score = 1.0 - avg_similarity  # Higher diversity = lower average similarity
            
            # Analyze domain distribution
            domains = [point.payload.get('domain', 'unknown') for point in points]
            domain_distribution = {}
            for domain in domains:
                domain_distribution[domain] = domain_distribution.get(domain, 0) + 1
            
            # Calculate domain diversity (entropy)
            domain_entropy = self._calculate_entropy(list(domain_distribution.values()))
            
            return {
                'diversity_score': diversity_score,
                'average_similarity': avg_similarity,
                'domain_distribution': domain_distribution,
                'domain_entropy': domain_entropy,
                'total_content': len(points),
                'similarity_range': [min(similarities), max(similarities)],
                'analysis': self._interpret_diversity_score(diversity_score)
            }
            
        except Exception as e:
            logger.error(f"Content diversity analysis failed: {e}")
            return {'diversity_score': 0.0, 'error': str(e)}
    
    async def find_content_outliers(
        self,
        content_ids: List[str],
        collection_name: str = 'content_embeddings',
        outlier_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find content outliers that are dissimilar to the group"""
        
        try:
            # Retrieve all content vectors
            points = await self.client.retrieve(
                collection_name=collection_name,
                ids=content_ids,
                with_vectors=True,
                with_payload=True
            )
            
            if len(points) < 3:
                return []
            
            outliers = []
            
            for i, point in enumerate(points):
                if not point.vector:
                    continue
                
                # Calculate average similarity to all other content
                similarities = []
                for j, other_point in enumerate(points):
                    if i != j and other_point.vector:
                        similarity = self._calculate_cosine_similarity(
                            point.vector, other_point.vector
                        )
                        similarities.append(similarity)
                
                if similarities:
                    avg_similarity = np.mean(similarities)
                    
                    if avg_similarity < outlier_threshold:
                        outliers.append({
                            'content_id': point.id,
                            'average_similarity': avg_similarity,
                            'metadata': point.payload,
                            'outlier_score': 1.0 - avg_similarity
                        })
            
            # Sort by outlier score (most dissimilar first)
            outliers.sort(key=lambda x: x['outlier_score'], reverse=True)
            
            logger.debug(f"Found {len(outliers)} content outliers")
            return outliers
            
        except Exception as e:
            logger.error(f"Outlier detection failed: {e}")
            return []
    
    async def get_collection_statistics(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """Get comprehensive statistics for a collection"""
        
        try:
            # Get collection info
            collection_info = await self.client.get_collection(collection_name)
            
            # Get sample of points for analysis
            sample_size = min(1000, collection_info.points_count)
            if sample_size > 0:
                # Scroll through points to get sample
                points, _ = await self.client.scroll(
                    collection_name=collection_name,
                    limit=sample_size,
                    with_payload=True
                )
                
                # Analyze payload distribution
                domain_counts = {}
                quality_scores = []
                content_types = {}
                
                for point in points:
                    payload = point.payload
                    
                    # Domain distribution
                    domain = payload.get('domain', 'unknown')
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    
                    # Quality score distribution
                    quality = payload.get('quality_score')
                    if quality is not None:
                        quality_scores.append(quality)
                    
                    # Content type distribution
                    content_type = payload.get('content_type', 'unknown')
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                
                # Calculate statistics
                stats = {
                    'collection_name': collection_name,
                    'total_points': collection_info.points_count,
                    'vector_size': collection_info.config.params.vectors.size,
                    'distance_metric': collection_info.config.params.vectors.distance.value,
                    'sample_size': len(points),
                    'domain_distribution': domain_counts,
                    'content_type_distribution': content_types,
                }
                
                if quality_scores:
                    stats['quality_statistics'] = {
                        'mean': float(np.mean(quality_scores)),
                        'median': float(np.median(quality_scores)),
                        'std': float(np.std(quality_scores)),
                        'min': float(np.min(quality_scores)),
                        'max': float(np.max(quality_scores))
                    }
            
            else:
                stats = {
                    'collection_name': collection_name,
                    'total_points': 0,
                    'vector_size': collection_info.config.params.vectors.size,
                    'distance_metric': collection_info.config.params.vectors.distance.value,
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection statistics: {e}")
            return {'error': str(e)}
    
    # Private helper methods
    
    def _build_search_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build Qdrant search filter from dictionary"""
        
        conditions = []
        
        for field, value in filters.items():
            if isinstance(value, str):
                conditions.append(
                    FieldCondition(key=field, match=MatchValue(value=value))
                )
            elif isinstance(value, list):
                conditions.append(
                    FieldCondition(key=field, match=MatchValue(any=value))
                )
            elif isinstance(value, dict):
                if 'gte' in value or 'lte' in value or 'gt' in value or 'lt' in value:
                    range_condition = {}
                    for op, val in value.items():
                        if op in ['gte', 'lte', 'gt', 'lt']:
                            range_condition[op] = val
                    conditions.append(
                        FieldCondition(key=field, range=Range(**range_condition))
                    )
        
        return Filter(must=conditions) if conditions else None
    
    async def _cluster_embeddings(
        self,
        embeddings: List[List[float]],
        content_ids: List[str],
        similarity_threshold: float,
        min_cluster_size: int
    ) -> List[Dict[str, Any]]:
        """Cluster embeddings using similarity threshold"""
        
        # Simple clustering algorithm based on similarity threshold
        clusters = []
        assigned = set()
        
        for i, embedding in enumerate(embeddings):
            if content_ids[i] in assigned:
                continue
                
            # Start new cluster
            cluster_members = [i]
            cluster_embeddings = [embedding]
            
            # Find similar embeddings
            for j, other_embedding in enumerate(embeddings):
                if i != j and content_ids[j] not in assigned:
                    similarity = self._calculate_cosine_similarity(embedding, other_embedding)
                    if similarity >= similarity_threshold:
                        cluster_members.append(j)
                        cluster_embeddings.append(other_embedding)
            
            # Only keep clusters above minimum size
            if len(cluster_members) >= min_cluster_size:
                # Calculate cluster center
                center = np.mean(cluster_embeddings, axis=0).tolist()
                
                clusters.append({
                    'center': center,
                    'content_ids': [content_ids[idx] for idx in cluster_members],
                    'member_indices': cluster_members
                })
                
                # Mark as assigned
                for idx in cluster_members:
                    assigned.add(content_ids[idx])
        
        return clusters
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            dot_product = np.dot(v1, v2)
            norms = np.linalg.norm(v1) * np.linalg.norm(v2)
            
            if norms == 0:
                return 0.0
            
            return dot_product / norms
        except:
            return 0.0
    
    def _calculate_entropy(self, values: List[int]) -> float:
        """Calculate entropy for diversity measurement"""
        if not values or sum(values) == 0:
            return 0.0
        
        total = sum(values)
        probabilities = [v / total for v in values if v > 0]
        
        entropy = -sum(p * np.log2(p) for p in probabilities)
        return entropy
    
    def _interpret_diversity_score(self, score: float) -> str:
        """Interpret diversity score"""
        if score >= 0.8:
            return "Very high diversity - content is highly varied"
        elif score >= 0.6:
            return "High diversity - good content variation"
        elif score >= 0.4:
            return "Moderate diversity - some content similarity"
        elif score >= 0.2:
            return "Low diversity - content is quite similar"
        else:
            return "Very low diversity - content is highly similar"
    
    async def _calculate_cluster_quality(
        self,
        cluster: Dict[str, Any],
        content_batch: List[Dict[str, Any]]
    ) -> float:
        """Calculate quality score for a cluster"""
        
        # Get content items for this cluster
        cluster_content = [
            content for content in content_batch 
            if content.get('id', content.get('content_id', '')) in cluster['content_ids']
        ]
        
        if not cluster_content:
            return 0.0
        
        # Calculate average quality score
        quality_scores = [
            content.get('quality_score', 0.0) 
            for content in cluster_content
        ]
        
        avg_quality = np.mean(quality_scores) if quality_scores else 0.0
        
        # Factor in cluster coherence (size relative to threshold)
        coherence_bonus = min(0.2, len(cluster_content) * 0.02)
        
        return min(1.0, avg_quality + coherence_bonus)
    
    def _select_representative_content(
        self,
        content_ids: List[str],
        content_batch: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Select representative content from cluster"""
        
        cluster_content = [
            content for content in content_batch 
            if content.get('id', content.get('content_id', '')) in content_ids
        ]
        
        if not cluster_content:
            return None
        
        # Select content with highest quality score
        best_content = max(
            cluster_content,
            key=lambda x: x.get('quality_score', 0.0)
        )
        
        return best_content
    
    async def _cache_embedding(
        self,
        content_id: str,
        embedding: List[float],
        collection_name: str,
        ttl: int = 3600
    ):
        """Cache embedding for quick access"""
        
        cache_key = f"embedding:{collection_name}:{content_id}"
        
        # Compress embedding for storage
        compressed_embedding = gzip.compress(
            pickle.dumps(embedding)
        )
        
        await self.redis.setex(cache_key, ttl, compressed_embedding)
"""
Agent Memory System Service
Advanced memory management and learning system for AI agents
"""
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from ..database import get_db_session, get_redis_client
from ..models.agent_memory import (
    AgentMemoryEntry, AgentLearningPattern, AgentKnowledgeTransfer,
    AgentPerformanceSnapshot, AgentCollaborationMatrix,
    AgentType, MemoryType, KnowledgeType
)
from ..utils.vector_embedding import ContentEmbeddingService
from ..utils.pattern_analysis import PatternAnalysisEngine
from ..logging import get_logger

logger = get_logger(__name__)

class AgentMemoryService:
    """Comprehensive agent memory management and learning system"""
    
    def __init__(self):
        self.vector_db = QdrantClient("http://qdrant:6333")
        self.redis = get_redis_client()
        self.embedding_service = ContentEmbeddingService()
        self.pattern_engine = PatternAnalysisEngine()
        
        # Memory system configuration
        self.config = {
            'memory_retention_days': 365,
            'pattern_confidence_threshold': 0.7,
            'knowledge_transfer_threshold': 0.6,
            'max_memories_per_agent': 10000,
            'similarity_threshold': 0.75,
            'effectiveness_decay_rate': 0.05,  # Monthly decay for unused memories
            'learning_rate': 0.1
        }
        
        # Initialize vector collections
        asyncio.create_task(self._initialize_vector_collections())
    
    async def _initialize_vector_collections(self):
        """Initialize Qdrant collections for each agent type"""
        for agent_type in AgentType:
            collection_name = f"agent_memory_{agent_type.value}"
            
            try:
                await self.vector_db.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
                )
                logger.info(f"Initialized vector collection: {collection_name}")
            except Exception as e:
                logger.debug(f"Collection {collection_name} already exists or error: {e}")
    
    async def store_agent_experience(
        self, 
        agent_type: AgentType, 
        memory_type: MemoryType,
        experience: Dict[str, Any],
        domain: str = "general"
    ) -> str:
        """Store a new learning experience in agent memory"""
        
        # Generate pattern signature for similarity detection
        pattern_signature = self._generate_pattern_signature(experience, agent_type, domain)
        
        # Check for similar existing memories
        similar_memories = await self._find_similar_memories(
            agent_type, pattern_signature, experience.get('pattern_description', '')
        )
        
        # If highly similar memory exists, update it instead of creating new one
        if similar_memories and similar_memories[0]['similarity_score'] > 0.9:
            return await self._update_existing_memory(similar_memories[0]['memory_id'], experience)
        
        # Create new memory entry
        memory_entry = AgentMemoryEntry(
            agent_type=agent_type.value,
            memory_type=memory_type.value,
            content_domain=domain,
            experience_data=experience,
            pattern_signature=pattern_signature,
            confidence_score=experience.get('confidence', 0.5),
            quality_correlation=experience.get('quality_correlation', 0.0),
            success_indicators=experience.get('success_indicators', {}),
            application_context=experience.get('application_context', {}),
            prerequisite_conditions=experience.get('prerequisite_conditions', {}),
            expected_outcomes=experience.get('expected_outcomes', {}),
            expires_at=datetime.utcnow() + timedelta(days=self.config['memory_retention_days'])
        )
        
        async with get_db_session() as session:
            session.add(memory_entry)
            await session.commit()
            await session.refresh(memory_entry)
            memory_id = memory_entry.id
        
        # Generate vector embedding for similarity search
        embedding = await self._generate_memory_embedding(experience)
        
        # Store in vector database
        await self._store_vector_embedding(agent_type, memory_id, embedding, experience, domain)
        
        # Cache frequently accessed memory types
        if memory_type in [MemoryType.SUCCESS, MemoryType.PATTERN]:
            await self._cache_memory(memory_id, memory_entry)
        
        logger.info(f"Stored new {memory_type.value} memory for {agent_type.value} agent: {memory_id}")
        return str(memory_id)
    
    async def retrieve_relevant_memories(
        self,
        agent_type: AgentType,
        context: Dict[str, Any],
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Retrieve memories relevant to current context"""
        
        # Generate context embedding for similarity search
        context_text = self._extract_searchable_text(context)
        context_embedding = await self.embedding_service.generate_embedding(context_text)
        
        # Search vector database for similar memories
        collection_name = f"agent_memory_{agent_type.value}"
        
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="domain",
                    match=MatchValue(value=context.get('domain', 'general'))
                ),
                FieldCondition(
                    key="confidence",
                    range={
                        "gte": min_confidence
                    }
                )
            ]
        )
        
        search_results = await self.vector_db.search(
            collection_name=collection_name,
            query_vector=context_embedding,
            query_filter=search_filter,
            limit=limit * 2,  # Get more results for filtering
            score_threshold=self.config['similarity_threshold']
        )
        
        # Retrieve full memory data and apply contextual filtering
        relevant_memories = []
        memory_ids = [result.id for result in search_results]
        
        async with get_db_session() as session:
            memories = await session.execute(
                select(AgentMemoryEntry).where(
                    and_(
                        AgentMemoryEntry.id.in_(memory_ids),
                        AgentMemoryEntry.is_active == True,
                        AgentMemoryEntry.effectiveness_score >= min_confidence
                    )
                ).order_by(desc(AgentMemoryEntry.effectiveness_score))
            )
            
            for memory in memories.scalars():
                # Check contextual applicability
                if memory.is_applicable(context):
                    similarity_score = next(
                        (result.score for result in search_results if result.id == str(memory.id)), 
                        0.0
                    )
                    
                    relevant_memories.append({
                        'memory_id': str(memory.id),
                        'memory_type': memory.memory_type,
                        'experience_data': memory.experience_data,
                        'similarity_score': similarity_score,
                        'confidence_score': memory.confidence_score,
                        'effectiveness_score': memory.effectiveness_score,
                        'usage_count': memory.usage_count,
                        'success_rate': memory.success_count / max(1, memory.usage_count),
                        'last_successful_use': memory.last_successful_use,
                        'application_context': memory.application_context,
                        'expected_outcomes': memory.expected_outcomes
                    })
        
        # Update access tracking
        for memory in relevant_memories:
            await self._track_memory_access(memory['memory_id'])
        
        # Sort by combined score (similarity + effectiveness + recency)
        relevant_memories.sort(
            key=lambda m: self._calculate_relevance_score(m, context),
            reverse=True
        )
        
        return relevant_memories[:limit]
    
    async def update_memory_effectiveness(
        self,
        memory_id: str,
        outcome_success: bool,
        impact_score: float = 0.0,
        additional_context: Optional[Dict] = None
    ) -> bool:
        """Update memory effectiveness based on usage outcome"""
        
        async with get_db_session() as session:
            memory = await session.get(AgentMemoryEntry, memory_id)
            if not memory:
                logger.warning(f"Memory not found: {memory_id}")
                return False
            
            # Update effectiveness metrics
            memory.update_effectiveness(outcome_success, impact_score)
            
            # Add additional context if provided
            if additional_context:
                current_context = memory.application_context or {}
                current_context.update(additional_context)
                memory.application_context = current_context
            
            await session.commit()
        
        # Update vector database metadata
        await self._update_vector_metadata(memory.agent_type, memory_id, {
            'effectiveness_score': memory.effectiveness_score,
            'usage_count': memory.usage_count,
            'success_rate': memory.success_count / max(1, memory.usage_count)
        })
        
        # Cache update if it's a frequently accessed memory
        if memory.usage_count > 5:
            await self._cache_memory(memory_id, memory)
        
        logger.debug(f"Updated memory effectiveness: {memory_id}, success: {outcome_success}")
        return True
    
    async def learn_from_patterns(
        self,
        agent_type: AgentType,
        domain: str,
        content_batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze content batch to learn new patterns"""
        
        if len(content_batch) < 3:
            logger.debug("Insufficient data for pattern learning")
            return []
        
        # Analyze patterns in the content batch
        discovered_patterns = await self.pattern_engine.analyze_content_patterns(
            content_batch, domain
        )
        
        learned_patterns = []
        
        for pattern in discovered_patterns:
            if pattern['confidence'] >= self.config['pattern_confidence_threshold']:
                # Store as learning pattern
                learning_pattern = await self._store_learning_pattern(
                    agent_type, domain, pattern
                )
                
                # Convert to memory entry for immediate use
                memory_id = await self.store_agent_experience(
                    agent_type=agent_type,
                    memory_type=MemoryType.PATTERN,
                    experience={
                        'pattern_name': pattern['name'],
                        'pattern_elements': pattern['elements'],
                        'pattern_description': pattern['description'],
                        'confidence': pattern['confidence'],
                        'expected_quality_impact': pattern.get('quality_impact', 0.0),
                        'application_context': pattern.get('context', {}),
                        'success_indicators': pattern.get('indicators', [])
                    },
                    domain=domain
                )
                
                learned_patterns.append({
                    'pattern_id': str(learning_pattern.id),
                    'memory_id': memory_id,
                    'pattern_name': pattern['name'],
                    'confidence': pattern['confidence'],
                    'expected_impact': pattern.get('quality_impact', 0.0)
                })
        
        logger.info(f"Learned {len(learned_patterns)} new patterns for {agent_type.value} in {domain}")
        return learned_patterns
    
    async def transfer_knowledge(
        self,
        source_agent: AgentType,
        target_agent: AgentType,
        knowledge_type: KnowledgeType,
        domain: str = "general",
        min_effectiveness: float = 0.7
    ) -> Dict[str, Any]:
        """Transfer knowledge between agents"""
        
        # Find effective knowledge from source agent
        effective_knowledge = await self._find_transferable_knowledge(
            source_agent, knowledge_type, domain, min_effectiveness
        )
        
        if not effective_knowledge:
            logger.info(f"No transferable knowledge found from {source_agent.value} to {target_agent.value}")
            return {'transferred_count': 0, 'adaptations': []}
        
        transferred_knowledge = []
        
        for knowledge_item in effective_knowledge:
            # Adapt knowledge for target agent
            adapted_knowledge = await self._adapt_knowledge_for_agent(
                knowledge_item, source_agent, target_agent
            )
            
            if adapted_knowledge['adaptation_confidence'] >= self.config['knowledge_transfer_threshold']:
                # Create knowledge transfer record
                transfer_record = AgentKnowledgeTransfer(
                    source_agent_type=source_agent.value,
                    target_agent_type=target_agent.value,
                    knowledge_type=knowledge_type.value,
                    knowledge_data=adapted_knowledge,
                    transfer_context={
                        'domain': domain,
                        'original_effectiveness': knowledge_item['effectiveness_score'],
                        'adaptation_method': adapted_knowledge['adaptation_method']
                    },
                    adaptation_confidence=adapted_knowledge['adaptation_confidence']
                )
                
                async with get_db_session() as session:
                    session.add(transfer_record)
                    await session.commit()
                    await session.refresh(transfer_record)
                
                # Store adapted knowledge as memory for target agent
                memory_id = await self.store_agent_experience(
                    agent_type=target_agent,
                    memory_type=MemoryType.OPTIMIZATION,
                    experience=adapted_knowledge['adapted_experience'],
                    domain=domain
                )
                
                transferred_knowledge.append({
                    'transfer_id': str(transfer_record.id),
                    'memory_id': memory_id,
                    'adaptation_confidence': adapted_knowledge['adaptation_confidence'],
                    'original_effectiveness': knowledge_item['effectiveness_score']
                })
        
        logger.info(f"Transferred {len(transferred_knowledge)} knowledge items from {source_agent.value} to {target_agent.value}")
        
        return {
            'transferred_count': len(transferred_knowledge),
            'adaptations': transferred_knowledge
        }
    
    async def get_agent_performance_insights(
        self,
        agent_type: AgentType,
        domain: str = None,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive performance insights for an agent"""
        
        start_date = datetime.utcnow() - timedelta(days=time_window_days)
        
        async with get_db_session() as session:
            # Get memory statistics
            memory_stats = await self._get_memory_statistics(session, agent_type, domain, start_date)
            
            # Get pattern effectiveness
            pattern_stats = await self._get_pattern_effectiveness(session, agent_type, domain, start_date)
            
            # Get knowledge transfer metrics
            transfer_stats = await self._get_knowledge_transfer_stats(session, agent_type, start_date)
            
            # Get recent performance snapshots
            performance_history = await self._get_performance_history(session, agent_type, domain, start_date)
        
        # Calculate improvement recommendations
        recommendations = await self._generate_performance_recommendations(
            agent_type, memory_stats, pattern_stats, transfer_stats
        )
        
        return {
            'agent_type': agent_type.value,
            'domain': domain,
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'days': time_window_days
            },
            'memory_statistics': memory_stats,
            'pattern_effectiveness': pattern_stats,
            'knowledge_transfer': transfer_stats,
            'performance_history': performance_history,
            'recommendations': recommendations,
            'overall_learning_velocity': self._calculate_learning_velocity(memory_stats, pattern_stats)
        }
    
    # Private helper methods
    
    def _generate_pattern_signature(self, experience: Dict, agent_type: AgentType, domain: str) -> str:
        """Generate unique signature for pattern identification"""
        signature_data = {
            'agent_type': agent_type.value,
            'domain': domain,
            'pattern_elements': experience.get('pattern_elements', []),
            'memory_type': experience.get('memory_type', ''),
            'key_characteristics': sorted(experience.get('key_characteristics', []))
        }
        signature_string = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_string.encode()).hexdigest()[:16]
    
    async def _generate_memory_embedding(self, experience: Dict) -> List[float]:
        """Generate vector embedding for memory experience"""
        # Combine relevant text fields for embedding
        text_parts = [
            experience.get('pattern_description', ''),
            experience.get('context_description', ''),
            ' '.join(experience.get('key_characteristics', [])),
            ' '.join(experience.get('success_indicators', []))
        ]
        combined_text = ' '.join(filter(None, text_parts))
        
        return await self.embedding_service.generate_embedding(combined_text)
    
    async def _store_vector_embedding(
        self, 
        agent_type: AgentType, 
        memory_id: uuid.UUID, 
        embedding: List[float],
        experience: Dict,
        domain: str
    ):
        """Store vector embedding in Qdrant"""
        collection_name = f"agent_memory_{agent_type.value}"
        
        point = PointStruct(
            id=str(memory_id),
            vector=embedding,
            payload={
                "memory_type": experience.get('memory_type', ''),
                "domain": domain,
                "confidence": experience.get('confidence', 0.5),
                "created_at": datetime.utcnow().isoformat(),
                "agent_type": agent_type.value
            }
        )
        
        await self.vector_db.upsert(
            collection_name=collection_name,
            points=[point]
        )
    
    def _calculate_relevance_score(self, memory: Dict, context: Dict) -> float:
        """Calculate combined relevance score for memory ranking"""
        similarity = memory['similarity_score']
        effectiveness = memory['effectiveness_score']
        
        # Recency bonus
        recency_bonus = 0.0
        if memory.get('last_successful_use'):
            days_since_success = (datetime.utcnow() - memory['last_successful_use']).days
            recency_bonus = max(0, 0.2 - (days_since_success * 0.01))
        
        # Context match bonus
        context_match = 0.0
        if memory.get('application_context') and context:
            matching_keys = set(memory['application_context'].keys()) & set(context.keys())
            if matching_keys:
                context_match = len(matching_keys) * 0.05
        
        return (similarity * 0.4) + (effectiveness * 0.4) + recency_bonus + context_match
    
    async def _find_similar_memories(
        self, 
        agent_type: AgentType, 
        pattern_signature: str,
        description: str
    ) -> List[Dict[str, Any]]:
        """Find similar existing memories"""
        
        # Check by pattern signature first (exact match)
        async with get_db_session() as session:
            exact_matches = await session.execute(
                select(AgentMemoryEntry).where(
                    and_(
                        AgentMemoryEntry.agent_type == agent_type.value,
                        AgentMemoryEntry.pattern_signature == pattern_signature,
                        AgentMemoryEntry.is_active == True
                    )
                )
            )
            
            exact_results = []
            for memory in exact_matches.scalars():
                exact_results.append({
                    'memory_id': str(memory.id),
                    'similarity_score': 1.0,
                    'memory_data': memory
                })
            
            if exact_results:
                return exact_results
        
        # If no exact matches, use vector similarity
        if description:
            embedding = await self.embedding_service.generate_embedding(description)
            collection_name = f"agent_memory_{agent_type.value}"
            
            try:
                search_results = await self.vector_db.search(
                    collection_name=collection_name,
                    query_vector=embedding,
                    limit=5,
                    score_threshold=0.85
                )
                
                similar_results = []
                for result in search_results:
                    similar_results.append({
                        'memory_id': result.id,
                        'similarity_score': result.score,
                        'memory_data': None  # Will be loaded if needed
                    })
                
                return similar_results
            except Exception as e:
                logger.warning(f"Vector similarity search failed: {e}")
        
        return []
    
    async def _cache_memory(self, memory_id: str, memory: AgentMemoryEntry):
        """Cache frequently accessed memory"""
        cache_key = f"memory:{memory.agent_type}:{memory_id}"
        memory_data = {
            'experience_data': memory.experience_data,
            'effectiveness_score': memory.effectiveness_score,
            'confidence_score': memory.confidence_score,
            'pattern_signature': memory.pattern_signature,
            'success_rate': memory.success_count / max(1, memory.usage_count),
            'application_context': memory.application_context,
            'expected_outcomes': memory.expected_outcomes
        }
        
        # Cache with TTL based on usage frequency
        ttl = min(86400, 3600 + (memory.usage_count * 60))  # Max 24 hours
        await self.redis.setex(cache_key, ttl, json.dumps(memory_data, default=str))
    
    def _extract_searchable_text(self, context: Dict) -> str:
        """Extract searchable text from context dictionary"""
        searchable_fields = [
            'description', 'content', 'pattern_description', 
            'context_description', 'requirements', 'goals'
        ]
        
        text_parts = []
        for field in searchable_fields:
            if field in context and isinstance(context[field], str):
                text_parts.append(context[field])
        
        # Add list fields
        list_fields = ['characteristics', 'requirements', 'goals', 'keywords']
        for field in list_fields:
            if field in context and isinstance(context[field], list):
                text_parts.extend([str(item) for item in context[field]])
        
        return ' '.join(text_parts)
    
    async def _track_memory_access(self, memory_id: str):
        """Track memory access for analytics"""
        cache_key = f"memory:access:{memory_id}"
        await self.redis.incr(cache_key)
        await self.redis.expire(cache_key, 86400)  # 24 hour window
    
    def _calculate_learning_velocity(self, memory_stats: Dict, pattern_stats: Dict) -> float:
        """Calculate how quickly the agent is learning"""
        # This is a simplified calculation - in practice, you'd want more sophisticated metrics
        new_memories = memory_stats.get('new_memories_count', 0)
        effective_patterns = pattern_stats.get('effective_patterns_count', 0)
        total_memories = memory_stats.get('total_memories', 1)
        
        velocity = (new_memories + effective_patterns * 2) / max(1, total_memories)
        return min(1.0, velocity)  # Cap at 1.0
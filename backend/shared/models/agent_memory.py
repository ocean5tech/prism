"""
Agent Memory System Database Models
Advanced learning and experience storage for AI agents
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
import hashlib
import json

from ..database import Base

class AgentType(str, Enum):
    GENERATION = "generation"
    DETECTION = "detection"
    OPTIMIZATION = "optimization"
    PUBLISHING = "publishing"

class MemoryType(str, Enum):
    PATTERN = "pattern"
    SUCCESS = "success"
    FAILURE = "failure"
    OPTIMIZATION = "optimization"
    STRATEGY = "strategy"
    CORRELATION = "correlation"

class KnowledgeType(str, Enum):
    SUCCESSFUL_PATTERN = "successful_pattern"
    FAILURE_ANALYSIS = "failure_analysis"
    OPTIMIZATION_STRATEGY = "optimization_strategy"
    QUALITY_CORRELATION = "quality_correlation"
    STYLE_EFFECTIVENESS = "style_effectiveness"

class AgentMemoryEntry(Base):
    """Core agent memory storage with learning experiences"""
    __tablename__ = "agent_memory_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(50), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)
    content_domain = Column(String(50), nullable=False, index=True)
    
    # Memory content and identification
    experience_data = Column(JSON, nullable=False)
    pattern_signature = Column(Text, index=True)  # Unique pattern identifier
    quality_correlation = Column(Float, default=0.0)  # Correlation with quality scores
    success_indicators = Column(JSON)  # Indicators of successful application
    
    # Learning and effectiveness metrics
    confidence_score = Column(Float, default=0.0)  # Initial confidence in pattern
    usage_count = Column(Integer, default=0)  # How many times pattern was used
    success_count = Column(Integer, default=0)  # How many times it succeeded
    effectiveness_score = Column(Float, default=0.0)  # Calculated effectiveness (0-1)
    
    # Context and application
    application_context = Column(JSON)  # When/how to apply this memory
    prerequisite_conditions = Column(JSON)  # Required conditions for application
    expected_outcomes = Column(JSON)  # Expected results from application
    
    # Temporal and lifecycle data
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    last_successful_use = Column(DateTime)
    expires_at = Column(DateTime)  # When this memory becomes stale
    
    # Performance tracking
    average_impact_score = Column(Float, default=0.0)  # Average improvement impact
    consistency_score = Column(Float, default=0.0)  # How consistently effective
    adaptation_flexibility = Column(Float, default=0.5)  # How adaptable to variations
    
    # Memory relationships
    parent_memory_id = Column(UUID(as_uuid=True), ForeignKey("agent_memory_entries.id"))
    parent_memory = relationship("AgentMemoryEntry", remote_side=[id], backref="derived_memories")
    
    # Status and maintenance
    is_active = Column(Boolean, default=True)
    needs_validation = Column(Boolean, default=False)
    validation_priority = Column(Integer, default=1)  # 1=low, 5=critical
    
    def calculate_pattern_signature(self) -> str:
        """Generate unique signature for this memory pattern"""
        signature_data = {
            'agent_type': self.agent_type,
            'memory_type': self.memory_type,
            'domain': self.content_domain,
            'pattern_elements': self.experience_data.get('pattern_elements', [])
        }
        signature_string = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_string.encode()).hexdigest()[:16]
    
    def update_effectiveness(self, outcome_success: bool, impact_score: float = 0.0):
        """Update effectiveness metrics based on usage outcome"""
        self.usage_count += 1
        if outcome_success:
            self.success_count += 1
            self.last_successful_use = datetime.utcnow()
        
        # Calculate new effectiveness score (weighted moving average)
        success_rate = self.success_count / self.usage_count if self.usage_count > 0 else 0
        self.effectiveness_score = (self.effectiveness_score * 0.8) + (success_rate * 0.2)
        
        # Update average impact score
        if impact_score > 0:
            current_avg = self.average_impact_score
            self.average_impact_score = (current_avg * (self.usage_count - 1) + impact_score) / self.usage_count
        
        # Update consistency score based on recent performance
        recent_performance_variance = self._calculate_recent_variance()
        self.consistency_score = 1.0 - min(1.0, recent_performance_variance)
        
        self.last_accessed = datetime.utcnow()
    
    def _calculate_recent_variance(self) -> float:
        """Calculate variance in recent performance for consistency tracking"""
        # This would be implemented with actual performance history
        # For now, return a placeholder calculation
        if self.usage_count < 3:
            return 0.0
        return max(0.0, 1.0 - (self.success_count / self.usage_count))
    
    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """Check if this memory is applicable to the given context"""
        if not self.is_active or self.effectiveness_score < 0.3:
            return False
            
        # Check domain compatibility
        if context.get('domain') != self.content_domain:
            return False
            
        # Check prerequisite conditions
        if self.prerequisite_conditions:
            for condition, required_value in self.prerequisite_conditions.items():
                if context.get(condition) != required_value:
                    return False
        
        return True

class AgentLearningPattern(Base):
    """Identified patterns in agent behavior and content generation"""
    __tablename__ = "agent_learning_patterns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern_name = Column(String(200), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False)  # structural, stylistic, semantic, etc.
    domain = Column(String(50), index=True)
    
    # Pattern definition and characteristics
    pattern_definition = Column(JSON, nullable=False)  # Detailed pattern structure
    trigger_conditions = Column(JSON)  # What triggers this pattern
    pattern_elements = Column(JSON)  # Constituent elements of the pattern
    expected_outcomes = Column(JSON)  # Expected results when pattern is applied
    
    # Pattern analysis and metrics
    complexity_level = Column(Float, default=1.0)  # Pattern complexity (1-10)
    generalizability = Column(Float, default=0.5)  # How broadly applicable (0-1)
    stability_score = Column(Float, default=0.5)  # How stable the pattern is
    
    # Performance tracking
    success_rate = Column(Float, default=0.0)
    usage_frequency = Column(Integer, default=0)
    total_applications = Column(Integer, default=0)
    successful_applications = Column(Integer, default=0)
    
    # Pattern evolution and relationships
    parent_pattern_id = Column(UUID(as_uuid=True), ForeignKey("agent_learning_patterns.id"))
    parent_pattern = relationship("AgentLearningPattern", remote_side=[id], backref="evolved_patterns")
    evolution_generation = Column(Integer, default=1)  # Generation of evolution
    mutation_factors = Column(JSON)  # What factors led to pattern mutation
    
    # Validation and quality
    validation_status = Column(String(20), default="pending")  # pending, validated, rejected
    validation_score = Column(Float)  # Validation confidence score
    last_effectiveness_check = Column(DateTime)
    effectiveness_trend = Column(Float, default=0.0)  # Positive=improving, negative=degrading
    
    # Lifecycle management
    is_active = Column(Boolean, default=True)
    deprecation_date = Column(DateTime)  # When pattern should be phased out
    replacement_pattern_id = Column(UUID(as_uuid=True), ForeignKey("agent_learning_patterns.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def evolve_pattern(self, mutation_data: Dict[str, Any]) -> 'AgentLearningPattern':
        """Create an evolved version of this pattern"""
        evolved_pattern = AgentLearningPattern(
            pattern_name=f"{self.pattern_name}_evolved_{datetime.now().strftime('%Y%m%d')}",
            pattern_type=self.pattern_type,
            domain=self.domain,
            pattern_definition=self._merge_pattern_definitions(self.pattern_definition, mutation_data),
            trigger_conditions=self.trigger_conditions.copy() if self.trigger_conditions else {},
            parent_pattern_id=self.id,
            evolution_generation=self.evolution_generation + 1,
            mutation_factors=mutation_data,
            complexity_level=min(10.0, self.complexity_level + 0.1)  # Slightly more complex
        )
        return evolved_pattern
    
    def _merge_pattern_definitions(self, original: Dict, mutation: Dict) -> Dict:
        """Merge original pattern with mutation data"""
        merged = original.copy()
        merged.update(mutation.get('pattern_updates', {}))
        return merged

class AgentKnowledgeTransfer(Base):
    """Cross-agent knowledge sharing and transfer tracking"""
    __tablename__ = "agent_knowledge_transfer"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_agent_type = Column(String(50), nullable=False, index=True)
    target_agent_type = Column(String(50), nullable=False, index=True)
    
    # Knowledge content
    knowledge_type = Column(String(50), nullable=False)
    knowledge_data = Column(JSON, nullable=False)
    transfer_context = Column(JSON)  # Context and rationale for transfer
    adaptation_notes = Column(Text)  # How knowledge was adapted for target agent
    
    # Transfer effectiveness
    transfer_success = Column(Boolean, default=False)
    adaptation_confidence = Column(Float, default=0.5)  # Confidence in adaptation
    improvement_achieved = Column(Boolean)
    performance_delta = Column(Float)  # Measured performance change
    
    # Application tracking
    first_application_date = Column(DateTime)
    successful_applications = Column(Integer, default=0)
    failed_applications = Column(Integer, default=0)
    
    # Transfer metadata
    transfer_method = Column(String(50))  # automatic, manual, hybrid
    validation_required = Column(Boolean, default=True)
    validation_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    def calculate_transfer_effectiveness(self) -> float:
        """Calculate how effective this knowledge transfer was"""
        if self.successful_applications + self.failed_applications == 0:
            return 0.0
        
        success_rate = self.successful_applications / (self.successful_applications + self.failed_applications)
        
        # Weight by adaptation confidence and performance delta
        effectiveness = success_rate * self.adaptation_confidence
        
        if self.performance_delta:
            # Positive performance delta increases effectiveness
            effectiveness *= (1.0 + max(0, self.performance_delta))
        
        return min(1.0, effectiveness)

class AgentPerformanceSnapshot(Base):
    """Periodic snapshots of agent performance for trend analysis"""
    __tablename__ = "agent_performance_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(50), nullable=False, index=True)
    domain = Column(String(50), index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    # Performance metrics
    overall_performance_score = Column(Float, nullable=False)
    quality_score = Column(Float)
    efficiency_score = Column(Float)
    consistency_score = Column(Float)
    learning_velocity = Column(Float)  # How quickly agent is improving
    
    # Memory utilization metrics
    active_memories_count = Column(Integer, default=0)
    effective_memories_ratio = Column(Float, default=0.0)
    memory_turnover_rate = Column(Float, default=0.0)
    
    # Pattern utilization
    patterns_discovered = Column(Integer, default=0)
    patterns_validated = Column(Integer, default=0)
    patterns_deprecated = Column(Integer, default=0)
    
    # Knowledge transfer metrics
    knowledge_shared = Column(Integer, default=0)
    knowledge_received = Column(Integer, default=0)
    transfer_success_rate = Column(Float, default=0.0)
    
    # Comparative metrics
    performance_vs_baseline = Column(Float)  # Performance vs initial baseline
    performance_vs_previous = Column(Float)  # Performance vs previous snapshot
    performance_percentile = Column(Float)  # Percentile among all agents
    
    # Detailed breakdown
    performance_breakdown = Column(JSON)  # Detailed metrics by category
    improvement_areas = Column(JSON)  # Areas identified for improvement
    strengths = Column(JSON)  # Agent's key strengths
    
    # Trend indicators
    trend_direction = Column(String(20))  # improving, stable, declining
    trend_confidence = Column(Float, default=0.5)
    projected_next_score = Column(Float)  # Predicted next performance score

class AgentCollaborationMatrix(Base):
    """Track collaboration effectiveness between different agents"""
    __tablename__ = "agent_collaboration_matrix"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type_1 = Column(String(50), nullable=False)
    agent_type_2 = Column(String(50), nullable=False)
    domain = Column(String(50), index=True)
    
    # Collaboration metrics
    collaboration_frequency = Column(Integer, default=0)
    successful_collaborations = Column(Integer, default=0)
    failed_collaborations = Column(Integer, default=0)
    
    # Effectiveness measures
    collaboration_effectiveness = Column(Float, default=0.0)  # 0-1 effectiveness score
    synergy_score = Column(Float, default=0.0)  # How well agents work together
    knowledge_flow_bidirectional = Column(Boolean, default=False)
    
    # Collaboration patterns
    optimal_collaboration_contexts = Column(JSON)  # When collaboration works best
    collaboration_bottlenecks = Column(JSON)  # Common collaboration issues
    
    # Performance impact
    individual_performance_impact = Column(Float, default=0.0)  # Impact on individual performance
    combined_performance_multiplier = Column(Float, default=1.0)  # Combined effectiveness multiplier
    
    last_collaboration = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create indexes for optimal performance
def create_agent_memory_indexes():
    """Create database indexes for optimal agent memory performance"""
    indexes = [
        # Primary query patterns
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_memory_type_domain_effectiveness "
        "ON agent_memory_entries (agent_type, memory_type, content_domain, effectiveness_score DESC);",
        
        # Pattern matching indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_memory_pattern_signature "
        "ON agent_memory_entries (pattern_signature) WHERE pattern_signature IS NOT NULL;",
        
        # Learning pattern indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_learning_patterns_domain_success "
        "ON agent_learning_patterns (domain, success_rate DESC) WHERE is_active = TRUE;",
        
        # Knowledge transfer indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_transfer_agents_date "
        "ON agent_knowledge_transfer (source_agent_type, target_agent_type, created_at DESC);",
        
        # Performance snapshot indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_snapshots_agent_date "
        "ON agent_performance_snapshots (agent_type, domain, snapshot_date DESC);",
        
        # Collaboration matrix indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_collaboration_matrix_agents "
        "ON agent_collaboration_matrix (agent_type_1, agent_type_2, domain);"
    ]
    return indexes
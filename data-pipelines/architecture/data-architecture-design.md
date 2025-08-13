-- PostgreSQL Schema for Intelligent Content Generation Factory
-- Multi-tier data architecture with partitioning and optimization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Domain configuration and templates
CREATE TABLE domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    style_config JSONB NOT NULL DEFAULT '{}',
    quality_thresholds JSONB NOT NULL DEFAULT '{}',
    compliance_rules JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content source management
CREATE TABLE content_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    source_type VARCHAR(30) NOT NULL, -- 'rss', 'api', 'webhook'
    source_url TEXT NOT NULL,
    source_config JSONB DEFAULT '{}',
    last_processed TIMESTAMP WITH TIME ZONE,
    processing_stats JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hot tier: Active content (30 days retention)
CREATE TABLE hot_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    source_id UUID REFERENCES content_sources(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    original_url TEXT,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}',
    processing_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    quality_score DECIMAL(4,3),
    vector_embedding VECTOR(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for hot content
CREATE TABLE hot_content_2025_01 PARTITION OF hot_content
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE hot_content_2025_02 PARTITION OF hot_content
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Warm tier: Recent historical content (90 days to 1 year)
CREATE TABLE warm_content (
    LIKE hot_content INCLUDING ALL
) WITH (fillfactor=90);

-- Generated content tracking
CREATE TABLE generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_content_id UUID REFERENCES hot_content(id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    generated_text TEXT NOT NULL,
    style_parameters JSONB NOT NULL,
    generation_metadata JSONB DEFAULT '{}',
    quality_metrics JSONB DEFAULT '{}',
    agent_memory_refs JSONB DEFAULT '{}', -- References to agent memory entries
    generation_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE
) PARTITION BY RANGE (created_at);

-- Agent memory system - Generation Agent
CREATE TABLE agent_memories_generation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    experience_type VARCHAR(50) NOT NULL, -- 'successful_generation', 'failed_attempt', 'optimization'
    style_parameters JSONB NOT NULL,
    content_characteristics JSONB DEFAULT '{}',
    quality_achieved DECIMAL(4,3),
    user_feedback JSONB DEFAULT '{}',
    success_indicators JSONB DEFAULT '{}',
    learning_weight DECIMAL(3,2) DEFAULT 1.0, -- Importance weight for learning
    usage_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Agent memory system - Detection Agent  
CREATE TABLE agent_memories_detection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL, -- 'repetitive_structure', 'style_pattern', 'quality_issue'
    detected_patterns JSONB NOT NULL,
    pattern_strength DECIMAL(4,3) NOT NULL, -- Confidence in pattern detection
    content_samples JSONB DEFAULT '{}',
    improvement_suggestions JSONB DEFAULT '{}',
    detection_algorithm VARCHAR(50),
    validation_results JSONB DEFAULT '{}',
    effectiveness_score DECIMAL(4,3), -- How effective the detection was
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Quality assessments and adversarial feedback
CREATE TABLE quality_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL, -- References generated_content or hot_content
    content_type VARCHAR(20) NOT NULL, -- 'source' or 'generated'
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    overall_score DECIMAL(4,3) NOT NULL,
    detailed_metrics JSONB NOT NULL, -- Readability, originality, accuracy, etc.
    detected_issues JSONB DEFAULT '{}',
    improvement_recommendations JSONB DEFAULT '{}',
    assessor_type VARCHAR(20) NOT NULL, -- 'detection_agent', 'human', 'automated'
    assessment_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Publishing tracking and success metrics
CREATE TABLE publishing_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES generated_content(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- 'wordpress', 'medium', 'linkedin', 'twitter'
    platform_config JSONB DEFAULT '{}',
    publishing_status VARCHAR(20) NOT NULL, -- 'pending', 'published', 'failed', 'scheduled'
    platform_response JSONB DEFAULT '{}',
    published_url TEXT,
    engagement_metrics JSONB DEFAULT '{}', -- Views, likes, shares, etc.
    error_details JSONB DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Data quality monitoring
CREATE TABLE data_quality_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type VARCHAR(30) NOT NULL, -- 'content_validation', 'pipeline_health', 'agent_performance'
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    quality_metrics JSONB NOT NULL,
    issues_found JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '{}',
    report_period_start TIMESTAMP WITH TIME ZONE,
    report_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance and analytics tracking
CREATE TABLE pipeline_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL, -- 'ingestion_rate', 'processing_time', 'quality_trend'
    domain VARCHAR(50),
    metric_value DECIMAL(10,3),
    metric_unit VARCHAR(20), -- 'seconds', 'count', 'percentage'
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (recorded_at);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY idx_hot_content_domain_created ON hot_content(domain_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_hot_content_hash ON hot_content(content_hash);
CREATE INDEX CONCURRENTLY idx_hot_content_embedding ON hot_content USING ivfflat (vector_embedding vector_cosine_ops);
CREATE INDEX CONCURRENTLY idx_generated_content_source ON generated_content(source_content_id);
CREATE INDEX CONCURRENTLY idx_generated_content_domain_created ON generated_content(domain_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_agent_memories_gen_domain_type ON agent_memories_generation(domain_id, experience_type);
CREATE INDEX CONCURRENTLY idx_agent_memories_det_domain_pattern ON agent_memories_detection(domain_id, pattern_type);
CREATE INDEX CONCURRENTLY idx_quality_assessments_content ON quality_assessments(content_id, content_type);
CREATE INDEX CONCURRENTLY idx_publishing_attempts_content_platform ON publishing_attempts(content_id, platform);
CREATE INDEX CONCURRENTLY idx_pipeline_metrics_type_recorded ON pipeline_metrics(metric_type, recorded_at DESC);

-- Full-text search indexes
CREATE INDEX CONCURRENTLY idx_hot_content_title_fts ON hot_content USING gin(to_tsvector('english', title));
CREATE INDEX CONCURRENTLY idx_hot_content_content_fts ON hot_content USING gin(to_tsvector('english', content));

-- Functions for automated data lifecycle management
CREATE OR REPLACE FUNCTION migrate_hot_to_warm()
RETURNS INTEGER AS $$
DECLARE
    migrated_count INTEGER := 0;
BEGIN
    -- Move content older than 30 days from hot to warm storage
    WITH moved_data AS (
        DELETE FROM hot_content 
        WHERE created_at < NOW() - INTERVAL '30 days'
        RETURNING *
    ),
    inserted_data AS (
        INSERT INTO warm_content SELECT * FROM moved_data
        RETURNING *
    )
    SELECT COUNT(*) INTO migrated_count FROM inserted_data;
    
    -- Log the migration
    INSERT INTO pipeline_metrics (metric_type, metric_value, metric_unit, metadata)
    VALUES ('data_migration', migrated_count, 'count', 
            jsonb_build_object('migration_type', 'hot_to_warm', 'timestamp', NOW()));
    
    RETURN migrated_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update agent memory access patterns
CREATE OR REPLACE FUNCTION update_agent_memory_access(memory_id UUID, memory_type VARCHAR)
RETURNS VOID AS $$
BEGIN
    IF memory_type = 'generation' THEN
        UPDATE agent_memories_generation 
        SET usage_count = usage_count + 1,
            last_accessed = NOW()
        WHERE id = memory_id;
    ELSIF memory_type = 'detection' THEN
        UPDATE agent_memories_detection 
        SET usage_count = COALESCE(usage_count, 0) + 1
        WHERE id = memory_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate quality trends
CREATE OR REPLACE FUNCTION calculate_quality_trends(
    p_domain_id UUID DEFAULT NULL,
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE(
    domain_name VARCHAR,
    avg_quality_score DECIMAL,
    quality_trend VARCHAR,
    total_assessments BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.name as domain_name,
        AVG(qa.overall_score) as avg_quality_score,
        CASE 
            WHEN AVG(qa.overall_score) OVER (
                PARTITION BY d.id 
                ORDER BY DATE_TRUNC('day', qa.created_at) 
                ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
            ) > LAG(AVG(qa.overall_score)) OVER (
                PARTITION BY d.id 
                ORDER BY DATE_TRUNC('day', qa.created_at)
            ) THEN 'improving'
            WHEN AVG(qa.overall_score) OVER (
                PARTITION BY d.id 
                ORDER BY DATE_TRUNC('day', qa.created_at) 
                ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
            ) < LAG(AVG(qa.overall_score)) OVER (
                PARTITION BY d.id 
                ORDER BY DATE_TRUNC('day', qa.created_at)
            ) THEN 'declining'
            ELSE 'stable'
        END as quality_trend,
        COUNT(*) as total_assessments
    FROM quality_assessments qa
    JOIN domains d ON qa.domain_id = d.id
    WHERE (p_domain_id IS NULL OR qa.domain_id = p_domain_id)
        AND qa.created_at >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY d.id, d.name, DATE_TRUNC('day', qa.created_at)
    ORDER BY d.name, DATE_TRUNC('day', qa.created_at);
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic metadata updates
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update triggers to relevant tables
CREATE TRIGGER update_domains_updated_at
    BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_hot_content_updated_at
    BEFORE UPDATE ON hot_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Automated partition management
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS VOID AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    table_name TEXT;
BEGIN
    -- Create partitions for next 3 months
    FOR i IN 1..3 LOOP
        start_date := DATE_TRUNC('month', NOW() + (i || ' month')::INTERVAL);
        end_date := start_date + INTERVAL '1 month';
        
        -- Hot content partitions
        table_name := 'hot_content_' || TO_CHAR(start_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF hot_content
                       FOR VALUES FROM (%L) TO (%L)', 
                       table_name, start_date, end_date);
        
        -- Generated content partitions
        table_name := 'generated_content_' || TO_CHAR(start_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF generated_content
                       FOR VALUES FROM (%L) TO (%L)', 
                       table_name, start_date, end_date);
        
        -- Agent memories partitions
        table_name := 'agent_memories_generation_' || TO_CHAR(start_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF agent_memories_generation
                       FOR VALUES FROM (%L) TO (%L)', 
                       table_name, start_date, end_date);
                       
        table_name := 'agent_memories_detection_' || TO_CHAR(start_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF agent_memories_detection
                       FOR VALUES FROM (%L) TO (%L)', 
                       table_name, start_date, end_date);
                       
        -- Pipeline metrics partitions
        table_name := 'pipeline_metrics_' || TO_CHAR(start_date, 'YYYY_MM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF pipeline_metrics
                       FOR VALUES FROM (%L) TO (%L)', 
                       table_name, start_date, end_date);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Initial data setup
INSERT INTO domains (name, display_name, description, style_config, quality_thresholds) VALUES 
('finance', 'Finance', 'Financial news and analysis content', 
 '{"tone": ["professional", "analytical", "authoritative"], "structure": ["executive_summary", "detailed_analysis", "market_implications"], "vocabulary": "financial_technical", "compliance_level": "high"}',
 '{"accuracy": 0.95, "compliance": 0.99, "readability": 0.80}'
),
('sports', 'Sports', 'Sports news, analysis and real-time updates',
 '{"tone": ["dynamic", "engaging", "narrative"], "structure": ["event_recap", "player_analysis", "predictions"], "vocabulary": "sports_accessible", "real_time_focus": true}',
 '{"engagement": 0.90, "accuracy": 0.85, "timeliness": 0.95}'
),
('technology', 'Technology', 'Technology news, innovation and industry analysis',
 '{"tone": ["informative", "forward_looking", "technical"], "structure": ["innovation_overview", "technical_details", "industry_impact"], "vocabulary": "tech_industry", "trend_analysis": true}',
 '{"technical_accuracy": 0.90, "innovation_relevance": 0.85, "readability": 0.75}'
);

-- Schedule automated maintenance tasks
SELECT cron.schedule('partition-maintenance', '0 2 * * 0', 'SELECT create_monthly_partitions();');
SELECT cron.schedule('data-migration', '0 3 * * *', 'SELECT migrate_hot_to_warm();');
SELECT cron.schedule('quality-analytics', '0 6 * * *', 'INSERT INTO data_quality_reports (report_type, quality_metrics, created_at) SELECT ''daily_quality_summary'', jsonb_agg(jsonb_build_object(''domain'', domain_name, ''avg_score'', avg_quality_score, ''trend'', quality_trend)) as quality_metrics, NOW() FROM calculate_quality_trends(NULL, 1);');
-- Prism 智能内容生成工厂 - 数据库表结构
-- 基于项目模型创建所有必需的表

-- =====================================================
-- 内容生成服务相关表
-- =====================================================

-- 生成请求表
CREATE TABLE IF NOT EXISTS generation_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(50) NOT NULL,
    source_content TEXT NOT NULL,
    source_url VARCHAR(500),
    target_length INTEGER DEFAULT 1000,
    style_parameters JSONB NOT NULL,
    generation_settings JSONB,
    user_id UUID NOT NULL,
    workflow_id VARCHAR(100),
    execution_id VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 内容项目表
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_request_id UUID REFERENCES generation_requests(id),
    title VARCHAR(300),
    content TEXT NOT NULL,
    summary TEXT,
    word_count INTEGER,
    model_used VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    generation_time_seconds REAL,
    api_cost_usd REAL,
    domain VARCHAR(50) NOT NULL,
    style_applied JSONB,
    confidence_score REAL,
    status VARCHAR(20) DEFAULT 'generated',
    readability_score REAL,
    originality_score REAL,
    domain_relevance REAL,
    overall_quality_score REAL,
    meta_description TEXT,
    keywords JSONB,
    hashtags JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 内容模板表
CREATE TABLE IF NOT EXISTS content_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    style_parameters JSONB NOT NULL,
    content_structure JSONB,
    category VARCHAR(100),
    target_length_min INTEGER DEFAULT 500,
    target_length_max INTEGER DEFAULT 2000,
    complexity_level VARCHAR(20) DEFAULT 'intermediate',
    usage_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    average_quality_score REAL DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 风格参数表
CREATE TABLE IF NOT EXISTS style_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parameter_type VARCHAR(50) NOT NULL,
    possible_values JSONB NOT NULL,
    default_value VARCHAR(200),
    randomization_enabled BOOLEAN DEFAULT TRUE,
    randomization_weight REAL DEFAULT 1.0,
    constraints JSONB,
    dependencies JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 生成历史表
CREATE TABLE IF NOT EXISTS generation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_item_id UUID REFERENCES content_items(id),
    generation_success BOOLEAN NOT NULL,
    quality_score REAL,
    user_satisfaction REAL,
    publication_success BOOLEAN,
    engagement_metrics JSONB,
    style_effectiveness JSONB,
    prompt_variations JSONB,
    improvement_actions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 质量检测服务相关表
-- =====================================================

-- 质量分析表
CREATE TABLE IF NOT EXISTS quality_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id VARCHAR(100) NOT NULL,
    content_text TEXT NOT NULL,
    analysis_type VARCHAR(50) NOT NULL DEFAULT 'comprehensive',
    domain VARCHAR(50) NOT NULL,
    source_url VARCHAR(500),
    overall_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    readability_score REAL,
    originality_score REAL,
    accuracy_score REAL,
    engagement_score REAL,
    coherence_score REAL,
    domain_relevance_score REAL,
    seo_score REAL,
    analysis_details JSONB NOT NULL,
    improvement_suggestions JSONB,
    detected_issues JSONB,
    strengths JSONB,
    analyzer_version VARCHAR(50) NOT NULL,
    analysis_time_seconds REAL,
    model_used VARCHAR(100),
    processing_flags JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模式检测表
CREATE TABLE IF NOT EXISTS pattern_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quality_analysis_id UUID REFERENCES quality_analyses(id),
    content_id VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_description TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    severity_level VARCHAR(20) NOT NULL,
    detected_elements JSONB NOT NULL,
    frequency_count INTEGER,
    pattern_locations JSONB,
    similarity_score REAL,
    impact_assessment JSONB,
    recommendation TEXT,
    auto_fixable BOOLEAN DEFAULT FALSE,
    fix_suggestions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 抄袭检测表
CREATE TABLE IF NOT EXISTS plagiarism_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quality_analysis_id UUID REFERENCES quality_analyses(id),
    content_id VARCHAR(100) NOT NULL,
    similarity_score REAL NOT NULL,
    originality_score REAL NOT NULL,
    threshold_exceeded BOOLEAN NOT NULL,
    sources_checked INTEGER DEFAULT 0,
    similar_sources JSONB,
    exact_matches JSONB,
    paraphrasing_detected JSONB,
    similarity_breakdown JSONB,
    risk_assessment VARCHAR(20),
    recommendations JSONB,
    check_method VARCHAR(50),
    external_apis_used JSONB,
    processing_time_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对抗反馈表
CREATE TABLE IF NOT EXISTS adversarial_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id VARCHAR(100) NOT NULL,
    generation_request_id VARCHAR(100),
    quality_analysis_id UUID REFERENCES quality_analyses(id),
    feedback_type VARCHAR(50) NOT NULL,
    feedback_message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    detected_weaknesses JSONB NOT NULL,
    style_adjustments JSONB,
    prompt_modifications JSONB,
    parameter_tuning JSONB,
    successful_patterns JSONB,
    failed_patterns JSONB,
    quality_correlations JSONB,
    action_taken VARCHAR(100),
    improvement_achieved BOOLEAN,
    follow_up_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- 质量阈值表
CREATE TABLE IF NOT EXISTS quality_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    min_overall_score REAL NOT NULL DEFAULT 0.7,
    min_readability_score REAL DEFAULT 6.0,
    min_originality_score REAL DEFAULT 0.85,
    min_accuracy_score REAL DEFAULT 0.9,
    min_engagement_score REAL DEFAULT 0.6,
    min_coherence_score REAL DEFAULT 0.8,
    min_domain_relevance REAL DEFAULT 0.8,
    min_seo_score REAL DEFAULT 0.7,
    max_repetitive_patterns INTEGER DEFAULT 3,
    max_similarity_to_existing REAL DEFAULT 0.3,
    max_template_reuse REAL DEFAULT 0.4,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 检测模型表
CREATE TABLE IF NOT EXISTS detection_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_config JSONB NOT NULL,
    training_data_info JSONB,
    performance_metrics JSONB,
    usage_count INTEGER DEFAULT 0,
    average_processing_time REAL,
    success_rate REAL DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    deployment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_retrain_date TIMESTAMP,
    performance_degradation_alert BOOLEAN DEFAULT FALSE
);

-- 内容相似性表
CREATE TABLE IF NOT EXISTS content_similarities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id_1 VARCHAR(100) NOT NULL,
    content_id_2 VARCHAR(100) NOT NULL,
    overall_similarity REAL NOT NULL,
    structural_similarity REAL,
    semantic_similarity REAL,
    lexical_similarity REAL,
    style_similarity REAL,
    similar_phrases JSONB,
    similar_structure_elements JSONB,
    confidence_score REAL NOT NULL,
    comparison_method VARCHAR(50) NOT NULL,
    model_used VARCHAR(100),
    processing_time_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 发布服务相关表
-- =====================================================

-- 发布配置表
CREATE TABLE IF NOT EXISTS publishing_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_name VARCHAR(50) NOT NULL,
    platform_type VARCHAR(50) NOT NULL,
    domain VARCHAR(50),
    api_endpoint VARCHAR(500),
    auth_config JSONB NOT NULL,
    default_settings JSONB,
    rate_limits JSONB,
    content_format_rules JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 发布记录表
CREATE TABLE IF NOT EXISTS publishing_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_item_id UUID REFERENCES content_items(id),
    platform_name VARCHAR(50) NOT NULL,
    publish_status VARCHAR(50) NOT NULL,
    scheduled_time TIMESTAMP,
    published_time TIMESTAMP,
    platform_post_id VARCHAR(200),
    platform_url VARCHAR(500),
    publish_config JSONB,
    response_data JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 分析服务相关表
-- =====================================================

-- 性能指标表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit VARCHAR(20),
    domain VARCHAR(50),
    additional_data JSONB,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 系统监控表
CREATE TABLE IF NOT EXISTS system_monitoring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    cpu_usage REAL,
    memory_usage REAL,
    response_time_ms REAL,
    error_count INTEGER DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    uptime_seconds INTEGER,
    additional_metrics JSONB,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 用户和权限相关表
-- =====================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name VARCHAR(100) NOT NULL,
    api_key_hash VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id),
    permissions JSONB,
    rate_limit INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 索引创建
-- =====================================================

-- 创建性能索引
CREATE INDEX IF NOT EXISTS idx_generation_requests_domain ON generation_requests(domain);
CREATE INDEX IF NOT EXISTS idx_generation_requests_created_at ON generation_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(status);
CREATE INDEX IF NOT EXISTS idx_content_items_domain ON content_items(domain);
CREATE INDEX IF NOT EXISTS idx_quality_analyses_content_id ON quality_analyses(content_id);
CREATE INDEX IF NOT EXISTS idx_quality_analyses_created_at ON quality_analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_pattern_detections_content_id ON pattern_detections(content_id);
CREATE INDEX IF NOT EXISTS idx_publishing_records_status ON publishing_records(publish_status);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_service ON performance_metrics(service_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_recorded_at ON performance_metrics(recorded_at);

-- =====================================================
-- 触发器: 自动更新时间戳
-- =====================================================

-- 为所有带有 updated_at 的表创建更新触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 应用触发器到相应的表
CREATE TRIGGER update_generation_requests_updated_at BEFORE UPDATE ON generation_requests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_items_updated_at BEFORE UPDATE ON content_items 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_templates_updated_at BEFORE UPDATE ON content_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_style_parameters_updated_at BEFORE UPDATE ON style_parameters 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quality_analyses_updated_at BEFORE UPDATE ON quality_analyses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quality_thresholds_updated_at BEFORE UPDATE ON quality_thresholds 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_publishing_configurations_updated_at BEFORE UPDATE ON publishing_configurations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_publishing_records_updated_at BEFORE UPDATE ON publishing_records 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
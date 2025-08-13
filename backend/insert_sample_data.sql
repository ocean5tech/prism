-- 插入 Prism 项目测试数据

-- 插入用户数据
INSERT INTO users (username, email, password_hash, full_name, role) VALUES
('admin', 'admin@prism.com', '$2b$12$hashedpassword', 'System Administrator', 'admin'),
('content_manager', 'content@prism.com', '$2b$12$hashedpassword', 'Content Manager', 'manager'),
('api_user', 'api@prism.com', '$2b$12$hashedpassword', 'API User', 'user');

-- 插入风格参数配置
INSERT INTO style_parameters (domain, name, description, parameter_type, possible_values, default_value) VALUES
('technology', 'tone', 'Writing tone for technology content', 'tone', '["professional", "casual", "technical", "conversational"]', 'professional'),
('finance', 'tone', 'Writing tone for financial content', 'tone', '["authoritative", "analytical", "cautious", "optimistic"]', 'analytical'),
('sports', 'tone', 'Writing tone for sports content', 'tone', '["energetic", "analytical", "passionate", "neutral"]', 'energetic'),
('technology', 'structure', 'Content structure type', 'structure', '["news", "analysis", "tutorial", "review"]', 'news'),
('finance', 'complexity', 'Content complexity level', 'complexity', '["beginner", "intermediate", "advanced", "expert"]', 'intermediate');

-- 插入内容模板
INSERT INTO content_templates (name, domain, description, prompt_template, style_parameters, category, created_by) VALUES
('Tech News Article', 'technology', 'Standard technology news article template', 
 'Write a {{target_length}} word technology news article about {{topic}} in a {{tone}} tone. Include {{structure}} format with introduction, main points, and conclusion.',
 '{"tone": "professional", "structure": "news"}', 'news',
 (SELECT id FROM users WHERE username = 'admin')),
 
('Financial Analysis', 'finance', 'Financial market analysis template',
 'Create a {{target_length}} word financial analysis of {{topic}} with {{tone}} perspective. Focus on {{analysis_type}} and provide actionable insights.',
 '{"tone": "analytical", "complexity": "intermediate"}', 'analysis',
 (SELECT id FROM users WHERE username = 'admin')),
 
('Sports Update', 'sports', 'Sports news and updates template',
 'Write an {{tone}} {{target_length}} word sports article about {{topic}}. Include key statistics, player information, and game analysis.',
 '{"tone": "energetic", "style": "news"}', 'news',
 (SELECT id FROM users WHERE username = 'admin'));

-- 插入质量阈值配置
INSERT INTO quality_thresholds (domain, content_type, min_overall_score, min_originality_score, min_accuracy_score) VALUES
('technology', 'article', 0.8, 0.9, 0.85),
('finance', 'analysis', 0.85, 0.95, 0.9),
('sports', 'news', 0.75, 0.85, 0.8),
('general', 'social_post', 0.7, 0.8, 0.75);

-- 插入发布平台配置
INSERT INTO publishing_configurations (platform_name, platform_type, domain, api_endpoint, auth_config, default_settings) VALUES
('WordPress Tech Blog', 'wordpress', 'technology', 'https://techblog.example.com/wp-json/wp/v2/', 
 '{"auth_type": "jwt", "username": "api_user"}',
 '{"post_status": "draft", "comment_status": "open"}'),
 
('Medium Finance', 'medium', 'finance', 'https://api.medium.com/v1/',
 '{"auth_type": "bearer_token"}',
 '{"publication_state": "draft", "license": "all-rights-reserved"}'),
 
('Twitter Sports', 'twitter', 'sports', 'https://api.twitter.com/2/',
 '{"auth_type": "oauth2"}',
 '{"reply_settings": "everyone"}');

-- 插入检测模型配置
INSERT INTO detection_models (model_name, model_type, model_version, model_config, performance_metrics) VALUES
('Quality Analyzer v1.0', 'quality', '1.0.0', 
 '{"algorithm": "ensemble", "features": ["readability", "coherence", "accuracy"], "threshold": 0.8}',
 '{"accuracy": 0.92, "precision": 0.88, "recall": 0.85}'),
 
('Pattern Detector v2.1', 'pattern_detection', '2.1.0',
 '{"detection_methods": ["structural", "semantic", "lexical"], "sensitivity": 0.7}',
 '{"accuracy": 0.89, "false_positive_rate": 0.12}'),
 
('Plagiarism Scanner v1.5', 'plagiarism', '1.5.0',
 '{"sources": ["web", "database", "academic"], "similarity_threshold": 0.3}',
 '{"accuracy": 0.94, "processing_speed": "150ms_avg"}');

-- 插入示例生成请求
INSERT INTO generation_requests (domain, source_content, target_length, style_parameters, user_id, priority) VALUES
('technology', 'Latest AI developments in large language models', 800, 
 '{"tone": "professional", "structure": "news", "target_audience": "developers"}',
 (SELECT id FROM users WHERE username = 'content_manager'), 'high'),
 
('finance', 'Q4 2024 market analysis and 2025 predictions', 1200,
 '{"tone": "analytical", "complexity": "intermediate", "focus": "investment"}',
 (SELECT id FROM users WHERE username = 'content_manager'), 'normal'),
 
('sports', 'NBA playoffs predictions and team analysis', 600,
 '{"tone": "energetic", "style": "preview", "include_stats": true}',
 (SELECT id FROM users WHERE username = 'content_manager'), 'normal');

-- 插入示例内容项目
INSERT INTO content_items (generation_request_id, title, content, word_count, domain, model_used, status, confidence_score, overall_quality_score) VALUES
((SELECT id FROM generation_requests WHERE domain = 'technology' LIMIT 1),
 'Revolutionary Advances in Large Language Models Transform AI Landscape',
 'The artificial intelligence sector continues to evolve at breakneck speed, with large language models (LLMs) leading the charge in transforming how we interact with technology. Recent developments have pushed the boundaries of what was previously thought possible...

This comprehensive analysis explores the latest breakthroughs in LLM technology, examining their implications for developers, businesses, and society as a whole. From improved reasoning capabilities to more efficient training methods, these advances represent a significant leap forward in AI capabilities.

Key developments include enhanced multimodal processing, allowing models to understand and generate content across text, images, and audio simultaneously. Additionally, new training methodologies have reduced computational requirements while improving output quality and reliability.

The implications for software development are profound. Developers now have access to tools that can assist with code generation, debugging, and system architecture planning. These capabilities are reshaping the development lifecycle and enabling more sophisticated applications.',
 287, 'technology', 'claude-3.5-sonnet', 'generated', 0.92, 0.88),

((SELECT id FROM generation_requests WHERE domain = 'finance' LIMIT 1),
 'Q4 2024 Market Analysis: Navigating Uncertainty Toward 2025 Growth',
 'As we conclude 2024, financial markets present a complex landscape of opportunities and challenges that will significantly influence investment strategies heading into 2025. This comprehensive analysis examines key market indicators, sector performance, and emerging trends that investors should monitor closely.

The fourth quarter demonstrated remarkable resilience in equity markets, with technology and healthcare sectors leading gains despite ongoing economic uncertainties. Interest rate policies have created both challenges and opportunities across different asset classes, requiring sophisticated portfolio management strategies.

Looking toward 2025, several factors emerge as critical drivers: inflation trends, geopolitical developments, and technological disruption across traditional industries. Our analysis suggests a cautiously optimistic outlook, with selective opportunities in emerging markets and innovative technology sectors.

Risk management remains paramount as volatility indicators suggest continued market fluctuations. Diversified portfolios with strategic allocation to growth and defensive assets appear best positioned for the evolving landscape.',
 198, 'finance', 'claude-3.5-sonnet', 'generated', 0.89, 0.91);

-- 插入示例质量分析
INSERT INTO quality_analyses (content_id, content_text, domain, overall_score, confidence_score, readability_score, originality_score, analyzer_version) VALUES
('tech_001', 'Revolutionary Advances in Large Language Models...', 'technology', 0.88, 0.92, 0.85, 0.94, 'v1.0'),
('finance_001', 'Q4 2024 Market Analysis: Navigating Uncertainty...', 'finance', 0.91, 0.89, 0.87, 0.96, 'v1.0');

-- 插入性能指标示例
INSERT INTO performance_metrics (service_name, metric_name, metric_value, metric_unit, domain) VALUES
('content-generation', 'avg_generation_time', 2.3, 'seconds', 'technology'),
('content-generation', 'success_rate', 0.94, 'percentage', 'finance'),
('detection-service', 'avg_analysis_time', 1.8, 'seconds', 'general'),
('detection-service', 'accuracy_score', 0.89, 'percentage', 'general'),
('publishing-service', 'publish_success_rate', 0.97, 'percentage', 'general');

-- 插入系统监控数据
INSERT INTO system_monitoring (service_name, status, cpu_usage, memory_usage, response_time_ms, request_count) VALUES
('content-generation', 'healthy', 45.2, 67.8, 245, 1247),
('detection-service', 'healthy', 38.9, 72.1, 189, 892),
('publishing-service', 'healthy', 22.3, 45.6, 156, 634),
('configuration-service', 'healthy', 15.7, 34.2, 98, 445),
('analytics-service', 'healthy', 31.8, 58.9, 203, 567);

-- 显示插入的数据统计
SELECT 'users' as table_name, COUNT(*) as record_count FROM users
UNION ALL
SELECT 'generation_requests', COUNT(*) FROM generation_requests  
UNION ALL
SELECT 'content_items', COUNT(*) FROM content_items
UNION ALL
SELECT 'content_templates', COUNT(*) FROM content_templates
UNION ALL
SELECT 'quality_analyses', COUNT(*) FROM quality_analyses
UNION ALL
SELECT 'style_parameters', COUNT(*) FROM style_parameters
UNION ALL
SELECT 'quality_thresholds', COUNT(*) FROM quality_thresholds
UNION ALL
SELECT 'publishing_configurations', COUNT(*) FROM publishing_configurations
UNION ALL
SELECT 'detection_models', COUNT(*) FROM detection_models
UNION ALL
SELECT 'performance_metrics', COUNT(*) FROM performance_metrics
UNION ALL
SELECT 'system_monitoring', COUNT(*) FROM system_monitoring
ORDER BY table_name;
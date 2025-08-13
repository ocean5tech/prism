-- ========================================
-- Prism 智能内容生成工厂 - Windows客户端测试查询
-- 在pgAdmin或psql中执行这些查询来验证数据库功能
-- ========================================

-- 1. 基础验证 - 检查所有表和数据
-- ========================================

-- 查看所有表
\echo '=== 1. 数据库表概览 ==='
SELECT 
    schemaname,
    tablename,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- 查看每个表的记录数
\echo '=== 2. 各表记录统计 ==='
SELECT 
    'users' as table_name, 
    COUNT(*) as record_count,
    'User management' as description
FROM users
UNION ALL
SELECT 'generation_requests', COUNT(*), 'Content generation requests'
FROM generation_requests  
UNION ALL
SELECT 'content_items', COUNT(*), 'Generated content items'
FROM content_items
UNION ALL
SELECT 'content_templates', COUNT(*), 'Content generation templates'
FROM content_templates
UNION ALL
SELECT 'quality_analyses', COUNT(*), 'Quality analysis results'
FROM quality_analyses
UNION ALL
SELECT 'style_parameters', COUNT(*), 'Style configuration parameters'
FROM style_parameters
UNION ALL
SELECT 'quality_thresholds', COUNT(*), 'Quality threshold settings'
FROM quality_thresholds
UNION ALL
SELECT 'publishing_configurations', COUNT(*), 'Publishing platform configs'
FROM publishing_configurations
UNION ALL
SELECT 'detection_models', COUNT(*), 'AI detection models'
FROM detection_models
UNION ALL
SELECT 'performance_metrics', COUNT(*), 'System performance metrics'
FROM performance_metrics
UNION ALL
SELECT 'system_monitoring', COUNT(*), 'System monitoring data'
FROM system_monitoring
ORDER BY table_name;

-- 2. 用户和权限数据
-- ========================================

\echo '=== 3. 用户信息 ==='
SELECT 
    username,
    email,
    full_name,
    role,
    is_active,
    created_at
FROM users
ORDER BY created_at;

-- 3. 内容生成相关数据
-- ========================================

\echo '=== 4. 内容生成请求 ==='
SELECT 
    gr.domain,
    LEFT(gr.source_content, 50) || '...' as source_preview,
    gr.target_length,
    gr.priority,
    u.username as requested_by,
    gr.created_at
FROM generation_requests gr
JOIN users u ON gr.user_id = u.id
ORDER BY gr.created_at DESC;

\echo '=== 5. 生成的内容项目 ==='
SELECT 
    ci.title,
    ci.domain,
    ci.word_count,
    ci.model_used,
    ci.status,
    ci.confidence_score,
    ci.overall_quality_score,
    ci.created_at
FROM content_items ci
ORDER BY ci.created_at DESC;

-- 查看具体的内容示例
\echo '=== 6. 内容详情示例 ==='
SELECT 
    title,
    LEFT(content, 200) || '...' as content_preview,
    word_count,
    domain,
    overall_quality_score
FROM content_items 
WHERE domain = 'technology'
LIMIT 1;

-- 4. 风格和模板配置
-- ========================================

\echo '=== 7. 风格参数配置 ==='
SELECT 
    domain,
    name,
    parameter_type,
    possible_values,
    default_value,
    randomization_enabled
FROM style_parameters
ORDER BY domain, parameter_type;

\echo '=== 8. 内容模板 ==='
SELECT 
    name,
    domain,
    category,
    target_length_min,
    target_length_max,
    usage_count,
    success_rate
FROM content_templates
ORDER BY domain;

-- 5. 质量检测和分析
-- ========================================

\echo '=== 9. 质量分析结果 ==='
SELECT 
    qa.content_id,
    qa.domain,
    qa.overall_score,
    qa.readability_score,
    qa.originality_score,
    qa.confidence_score,
    qa.analyzer_version,
    qa.created_at
FROM quality_analyses qa
ORDER BY qa.overall_score DESC;

\echo '=== 10. 质量阈值配置 ==='
SELECT 
    domain,
    content_type,
    min_overall_score,
    min_originality_score,
    min_accuracy_score,
    is_active
FROM quality_thresholds
ORDER BY domain;

\echo '=== 11. 检测模型配置 ==='
SELECT 
    model_name,
    model_type,
    model_version,
    usage_count,
    success_rate,
    is_active,
    is_default
FROM detection_models
ORDER BY model_type;

-- 6. 发布配置
-- ========================================

\echo '=== 12. 发布平台配置 ==='
SELECT 
    platform_name,
    platform_type,
    domain,
    is_active,
    is_default,
    created_at
FROM publishing_configurations
ORDER BY platform_type;

-- 7. 系统监控和性能
-- ========================================

\echo '=== 13. 性能指标 ==='
SELECT 
    service_name,
    metric_name,
    metric_value,
    metric_unit,
    domain,
    recorded_at
FROM performance_metrics
ORDER BY service_name, metric_name;

\echo '=== 14. 系统监控状态 ==='
SELECT 
    service_name,
    status,
    cpu_usage,
    memory_usage,
    response_time_ms,
    request_count,
    recorded_at
FROM system_monitoring
ORDER BY service_name;

-- 8. 高级分析查询
-- ========================================

\echo '=== 15. 内容生成成功率分析 ==='
SELECT 
    domain,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN ci.status = 'generated' THEN 1 END) as successful_generations,
    ROUND(
        COUNT(CASE WHEN ci.status = 'generated' THEN 1 END) * 100.0 / COUNT(*), 2
    ) as success_rate_percentage
FROM generation_requests gr
LEFT JOIN content_items ci ON gr.id = ci.generation_request_id
GROUP BY domain
ORDER BY success_rate_percentage DESC;

\echo '=== 16. 质量分数分布 ==='
SELECT 
    domain,
    AVG(overall_quality_score) as avg_quality,
    MIN(overall_quality_score) as min_quality,
    MAX(overall_quality_score) as max_quality,
    COUNT(*) as total_items
FROM content_items 
WHERE overall_quality_score IS NOT NULL
GROUP BY domain
ORDER BY avg_quality DESC;

\echo '=== 17. 服务性能概览 ==='
SELECT 
    pm.service_name,
    AVG(CASE WHEN pm.metric_name = 'avg_generation_time' THEN pm.metric_value END) as avg_response_time,
    AVG(CASE WHEN pm.metric_name = 'success_rate' THEN pm.metric_value END) as success_rate,
    sm.status as current_status,
    sm.cpu_usage,
    sm.memory_usage
FROM performance_metrics pm
LEFT JOIN system_monitoring sm ON pm.service_name = sm.service_name
GROUP BY pm.service_name, sm.status, sm.cpu_usage, sm.memory_usage
ORDER BY pm.service_name;

-- 9. 数据完整性检查
-- ========================================

\echo '=== 18. 数据完整性检查 ==='

-- 检查外键关系
SELECT 'content_items -> generation_requests' as relationship,
       COUNT(*) as total_content_items,
       COUNT(gr.id) as linked_requests,
       CASE WHEN COUNT(*) = COUNT(gr.id) THEN 'OK' ELSE 'MISSING_LINKS' END as status
FROM content_items ci
LEFT JOIN generation_requests gr ON ci.generation_request_id = gr.id

UNION ALL

SELECT 'generation_requests -> users' as relationship,
       COUNT(*) as total_requests,
       COUNT(u.id) as linked_users,
       CASE WHEN COUNT(*) = COUNT(u.id) THEN 'OK' ELSE 'MISSING_LINKS' END as status
FROM generation_requests gr
LEFT JOIN users u ON gr.user_id = u.id;

-- 10. 系统健康状态总览
-- ========================================

\echo '=== 19. 系统健康状态总览 ==='
SELECT 
    COUNT(CASE WHEN status = 'healthy' THEN 1 END) as healthy_services,
    COUNT(*) as total_services,
    ROUND(AVG(cpu_usage), 2) as avg_cpu_usage,
    ROUND(AVG(memory_usage), 2) as avg_memory_usage,
    ROUND(AVG(response_time_ms), 2) as avg_response_time_ms
FROM system_monitoring;

-- 11. 最新活动概览
-- ========================================

\echo '=== 20. 最新系统活动 ==='
SELECT 
    'Generation Request' as activity_type,
    LEFT(source_content, 40) || '...' as activity_description,
    domain,
    created_at
FROM generation_requests
UNION ALL
SELECT 
    'Quality Analysis' as activity_type,
    'Content ID: ' || content_id as activity_description,
    domain,
    created_at
FROM quality_analyses
ORDER BY created_at DESC
LIMIT 10;

-- ========================================
-- 测试完成！
-- ========================================

\echo '=== 🎉 数据库测试完成！ ==='
\echo '如果所有查询都成功执行，说明数据库连接和数据完整性都没有问题。'
\echo '现在可以开始测试微服务API了！'
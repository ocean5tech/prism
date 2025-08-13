-- Prism PostgreSQL 连接验证查询
-- 在Windows客户端中执行这些查询来验证连接

-- 1. 基本连接验证
SELECT 'Connection Success!' as status, 
       version() as postgres_version,
       current_database() as database_name,
       current_user as connected_user,
       now() as connection_time;

-- 2. 检查数据库大小
SELECT pg_database.datname as database_name,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'prism_db';

-- 3. 列出所有表
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 4. 检查表数量
SELECT count(*) as total_tables
FROM information_schema.tables
WHERE table_schema = 'public';

-- 5. 数据库权限检查
SELECT has_database_privilege('prism_user', 'prism_db', 'CONNECT') as can_connect,
       has_database_privilege('prism_user', 'prism_db', 'CREATE') as can_create;

-- 6. 简单的创建表测试 (可选)
CREATE TABLE IF NOT EXISTS connection_test (
    id SERIAL PRIMARY KEY,
    test_message VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 插入测试数据
INSERT INTO connection_test (test_message) 
VALUES ('Windows client connection successful!');

-- 8. 查询测试数据
SELECT * FROM connection_test ORDER BY created_at DESC LIMIT 5;

-- 9. 清理测试数据 (可选)
-- DROP TABLE IF EXISTS connection_test;
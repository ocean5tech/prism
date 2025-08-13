# 配置文件快照 - 避免重复配置

## 📁 关键配置文件内容备份

### 1. 环境配置 (.env)
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://prism_user:prism_password@localhost:5434/prism_db
REDIS_URL=redis://localhost:6380
JWT_SECRET_KEY=prism-jwt-secret-key-development-2024
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ANTHROPIC_API_KEY=test-anthropic-key-placeholder
CLAUDE_DEFAULT_MODEL=claude-3-sonnet-20240229
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.7
CLAUDE_RPM=60
CLAUDE_RPH=1000
CLAUDE_CONCURRENT=5
OPENAI_API_KEY=your-openai-api-key
QDRANT_URL=http://localhost:6333
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=prism-analytics-token
INFLUXDB_ORG=prism
INFLUXDB_BUCKET=analytics
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=prism-storage
CONTENT_GENERATION_PORT=8010
DETECTION_SERVICE_PORT=8011
PUBLISHING_SERVICE_PORT=8002
CONFIGURATION_SERVICE_PORT=8013
USER_MANAGEMENT_PORT=8004
ANALYTICS_SERVICE_PORT=8015
FILE_STORAGE_SERVICE_PORT=8006
EXTERNAL_API_SERVICE_PORT=8007
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
MEDIUM_CLIENT_ID=your-medium-client-id
MEDIUM_CLIENT_SECRET=your-medium-client-secret
WEBHOOK_SECRET=your-webhook-secret-key
N8N_WEBHOOK_URL=http://localhost:5678
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
ALLOWED_HOSTS=localhost,127.0.0.1,api.prism.com
CORS_ORIGINS=http://localhost:3000,https://app.prism.com
MAX_WORKERS=4
WORKER_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=65
ENABLE_BATCH_PROCESSING=true
ENABLE_REAL_TIME_METRICS=true
ENABLE_ADVERSARIAL_FEEDBACK=true
ENABLE_QUALITY_OPTIMIZATION=true
```

### 2. n8n Workflow 修复记录

#### 修复的标签名称:
- `02-adversarial-quality-optimization.json`: `adversarial-optimization` → `adversarial-opt`
- `03-multi-platform-publishing.json`: `multi-platform-publishing` → `multi-publishing`

#### 需要在workflow中更新的URL:
```json
// 原始URL → 新URL
"http://config-service:8000" → "http://localhost:8013"
"http://content-gen-service:8000" → "http://localhost:8010" 
"http://detection-service:8000" → "http://localhost:8011"
"http://analytics-service:8000" → "http://localhost:8015"
"http://publishing-service:8000" → "http://localhost:8002"
```

### 3. 容器配置状态
```bash
# 现有Podman容器
podman ps -a | grep prism
# 预期输出:
# prism-postgres  (0.0.0.0:5434->5432/tcp)  Up
# prism-redis     (0.0.0.0:6380->6379/tcp)  Up  
# prism-n8n       (0.0.0.0:8080->5678/tcp)  Up
```

### 4. 端口分配表
```
服务                    端口    状态
PostgreSQL (Container)  5434   ✅ 运行中
Redis (Container)       6380   ✅ 运行中  
n8n (Container)         8080   ✅ 运行中
Content Generation      8010   ✅ 微服务
Detection Service       8011   ✅ 微服务
Configuration           8013   ✅ 微服务
Analytics               8015   ✅ 微服务
```

### 5. Python依赖列表
```
fastapi==0.116.1
uvicorn==0.35.0
asyncpg==0.30.0
redis==6.4.0
pydantic==2.11.7
requests==2.32.4
```

### 6. n8n Credentials配置
```
Credential 1:
Name: prism_api_token
Type: HTTP Header Auth
Header Name: Authorization
Header Value: Bearer test-token-123

Credential 2: 
Name: prism_webhook_key
Type: HTTP Header Auth
Header Name: X-API-Key
Header Value: webhook-test-key-456
```

## 🔄 快速恢复命令

### 一键部署
```bash
cd /home/wyatt/dev-projects/Prism
./quick-deploy.sh
```

### 手动步骤 (如果脚本失败)
```bash
# 1. 进入项目目录
cd /home/wyatt/dev-projects/Prism/backend

# 2. 设置Python环境
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn asyncpg redis pydantic requests

# 3. 启动微服务
./start-simple-services.sh

# 4. 验证部署
python3 test-services.py
```

### 故障排除
```bash
# 清理端口
for port in 8010 8011 8013 8015; do
  lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
done

# 重启容器
podman restart prism-postgres prism-redis prism-n8n

# 检查日志
tail -f backend/deployment.log
```

## 📊 验证检查清单

✅ 基础设施容器运行  
✅ Python虚拟环境创建  
✅ 依赖包安装完成  
✅ 微服务文件存在  
✅ 环境变量配置正确  
✅ 4个微服务健康检查通过  
✅ n8n界面可访问  
✅ workflow文件已修复并导入  

**下次部署只需5分钟！** ⚡
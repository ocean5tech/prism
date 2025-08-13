# Prism Platform 部署指南

## 📋 完整部署记录 (避免重复配置)

> 此文档记录了完整的部署步骤和所有配置修改，确保下次部署时可以快速重现环境。

---

## 🏗️ 基础设施状态

### 已存在的容器服务 (Podman)
- **PostgreSQL**: `prism-postgres` (端口 5434)  
- **Redis**: `prism-redis` (端口 6380)
- **n8n**: `prism-n8n` (端口 8080) 

### 微服务端口分配 (避免冲突)
- **Content Generation**: 8010 (原计划8000)
- **Detection Service**: 8011 (原计划8001) 
- **Configuration**: 8013 (原计划8003)
- **Analytics**: 8015 (原计划8005)

---

## 📁 创建的关键文件

### 1. 环境配置文件
**文件**: `/home/wyatt/dev-projects/Prism/backend/.env`
```bash
# 已修改的关键配置
DATABASE_URL=postgresql+asyncpg://prism_user:prism_password@localhost:5434/prism_db
REDIS_URL=redis://localhost:6380
JWT_SECRET_KEY=prism-jwt-secret-key-development-2024
ANTHROPIC_API_KEY=test-anthropic-key-placeholder
```

### 2. 简化微服务文件
创建了4个简化版微服务用于测试：

#### a) Content Generation Service
**文件**: `/home/wyatt/dev-projects/Prism/backend/simple-content-service.py`
- 端口: 8010
- 功能: 模拟内容生成，支持多域名
- API: `/api/v1/content/generate`, `/api/v1/content/regenerate`

#### b) Detection Service  
**文件**: `/home/wyatt/dev-projects/Prism/backend/simple-detection-service.py`
- 端口: 8011
- 功能: 内容质量分析和评分
- API: `/api/v1/detection/analyze`

#### c) Configuration Service
**文件**: `/home/wyatt/dev-projects/Prism/backend/simple-config-service.py`
- 端口: 8013
- 功能: 域名配置管理
- API: `/api/v1/config/domains/{domain}`

#### d) Analytics Service
**文件**: `/home/wyatt/dev-projects/Prism/backend/simple-analytics-service.py`
- 端口: 8015
- 功能: 事件日志记录
- API: `/api/v1/analytics/events`, `/api/v1/analytics/*`

### 3. 启动脚本
**文件**: `/home/wyatt/dev-projects/Prism/backend/start-simple-services.sh`
```bash
#!/bin/bash
# 自动启动所有微服务的脚本
# 包含端口清理、健康检查、错误处理
```

### 4. 测试脚本
**文件**: `/home/wyatt/dev-projects/Prism/backend/test-services.py`
```python
# 全面测试所有微服务功能的Python脚本
# 验证API响应和数据格式
```

---

## 🚀 快速部署步骤

### 第一步: 检查基础设施
```bash
# 检查现有容器状态
podman ps -a | grep -E "(prism-postgres|prism-redis|prism-n8n)"

# 确保以下容器运行:
# prism-postgres (5434) - UP
# prism-redis (6380) - UP  
# prism-n8n (8080) - UP
```

### 第二步: 设置Python环境
```bash
cd /home/wyatt/dev-projects/Prism/backend

# 创建虚拟环境 (如果不存在)
python3 -m venv venv

# 激活并安装依赖
source venv/bin/activate
pip install fastapi uvicorn asyncpg redis pydantic requests
```

### 第三步: 启动微服务
```bash
# 确保在backend目录
cd /home/wyatt/dev-projects/Prism/backend

# 启动所有微服务 (后台运行)
./start-simple-services.sh
```

### 第四步: 验证部署
```bash
# 运行测试脚本
source venv/bin/activate
python3 test-services.py

# 期望输出: 4/4 services working correctly
```

---

## 🔧 n8n配置

### Workflow文件状态
已修复并可导入的workflow:
- `01-main-content-generation-pipeline.json` ✅
- `02-adversarial-quality-optimization.json` ✅ (标签已修复)
- `03-multi-platform-publishing.json` ✅ (标签已修复)

### 必需的Credentials
在n8n中创建以下credentials:

1. **prism_api_token** (HTTP Header Auth)
   - Header Name: `Authorization`
   - Header Value: `Bearer test-token-123`

2. **prism_webhook_key** (HTTP Header Auth)
   - Header Name: `X-API-Key`
   - Header Value: `webhook-test-key-456`

### ⚠️ 重要: URL更新需求
由于端口更改，n8n workflow中的URL需要手动更新:

**原始URL → 新URL:**
- `http://config-service:8000` → `http://localhost:8013`
- `http://content-gen-service:8000` → `http://localhost:8010`
- `http://detection-service:8000` → `http://localhost:8011`
- `http://analytics-service:8000` → `http://localhost:8015`

---

## 🧪 测试验证清单

### 微服务健康检查
```bash
# 快速健康检查
for port in 8010 8011 8013 8015; do
  echo "Testing port $port:"
  timeout 3 bash -c "exec 3<>/dev/tcp/localhost/$port; echo -e 'GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3; cat <&3" | grep "HTTP/1.1"
done
```

### n8n访问确认
- **n8n界面**: http://localhost:8080
- **用户名**: wooyoo@gmail.com
- **密码**: Zaq12wsx

---

## 🔍 故障排除

### 常见问题及解决方案

1. **端口冲突**
   ```bash
   # 检查端口占用
   ss -tlnp | grep -E ":(8010|8011|8013|8015)"
   
   # 强制清理端口
   for port in 8010 8011 8013 8015; do
     lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
   done
   ```

2. **虚拟环境问题**
   ```bash
   # 重建虚拟环境
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn asyncpg redis pydantic requests
   ```

3. **数据库连接问题**
   ```bash
   # 检查PostgreSQL状态
   podman exec prism-postgres pg_isready -U prism_user -d prism_db
   
   # 检查Redis状态  
   podman exec prism-redis redis-cli ping
   ```

4. **n8n workflow执行失败**
   - 检查credentials配置
   - 确认微服务URL已更新
   - 验证API endpoints可访问

---

## 📊 部署验证成功标准

**✅ 部署成功的标志:**
1. 4个微服务健康检查全部返回200 OK
2. `test-services.py`输出 "4/4 services working correctly"
3. n8n界面可正常访问 (localhost:8080)
4. n8n workflows已导入且credentials已配置

**🚀 可开始测试workflow执行**

---

## 💾 备份的重要文件

为避免重复配置，以下文件已保存完整配置:
- `/home/wyatt/dev-projects/Prism/backend/.env`
- `/home/wyatt/dev-projects/Prism/backend/simple-*-service.py` (4个文件)
- `/home/wyatt/dev-projects/Prism/backend/start-simple-services.sh`
- `/home/wyatt/dev-projects/Prism/backend/test-services.py`
- `/home/wyatt/dev-projects/Prism/n8n-workflows/*.json` (修复后的workflow)

**下次部署只需按照"快速部署步骤"执行即可！** 🎯
# n8n Credentials Setup for Prism Workflows

## 📋 Required Credentials

为了让导入的workflow正常工作，请在n8n中创建以下credentials：

### 1. **prism_api_token** (HTTP Header Auth)
```
Name: prism_api_token
Type: HTTP Header Auth
Header Name: Authorization  
Header Value: Bearer test-token-123
```

### 2. **prism_webhook_key** (HTTP Header Auth)
```
Name: prism_webhook_key
Type: HTTP Header Auth
Header Name: X-API-Key
Header Value: webhook-test-key-456
```

## 🔧 在n8n中创建Credentials的步骤：

1. **打开n8n**: http://localhost:8080 (用户名: wooyoo@gmail.com, 密码: Zaq12wsx)

2. **进入Credentials管理**:
   - 点击左侧菜单的 **Settings** (齿轮图标)
   - 选择 **Credentials**

3. **添加新Credential**:
   - 点击 **"Add Credential"** 按钮
   - 选择 **"HTTP Header Auth"**
   - 填入上述信息
   - 点击 **"Save"**

4. **重复**为第二个credential (prism_webhook_key)

## 🚀 微服务状态

当前运行的微服务：
- ✅ Content Generation Service: http://localhost:8000
- ✅ Detection Service: http://localhost:8001  
- ✅ Configuration Service: http://localhost:8003
- ✅ Analytics Service: http://localhost:8005

## 🧪 测试Workflow

设置完credentials后，你可以：

1. **手动执行workflow 1** (Main Content Generation Pipeline)
   - 需要提供RSS URL输入
   
2. **通过webhook触发workflow 2** (Adversarial Quality Optimization)
   - Webhook URL: http://localhost:5678/webhook/quality-optimization-trigger
   
3. **通过webhook触发workflow 3** (Multi-Platform Publishing)
   - Webhook URL: http://localhost:5678/webhook/publishing-trigger

## 📝 测试数据示例

可以用这些测试数据：

### RSS URL测试:
```
https://feeds.bloomberg.com/markets/news.rss
https://rss.cnn.com/rss/edition.rss
```

### Webhook测试数据 (JSON):
```json
{
  "content_id": "test_content_001",
  "domain": "finance", 
  "content": "This is test content for quality analysis...",
  "quality_thresholds": {"minimum_score": 75}
}
```
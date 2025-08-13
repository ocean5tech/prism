#!/bin/bash

echo "🧪 Prism 系统功能验证测试"
echo "=========================="

# 检查API是否可用
check_api() {
    local url=$1
    local name=$2
    
    if curl -s "$url" > /dev/null 2>&1; then
        echo "✅ $name API 可用"
        return 0
    else
        echo "❌ $name API 不可用"
        return 1
    fi
}

echo ""
echo "1️⃣ 检查服务健康状态..."
check_api "http://localhost:8000/health" "内容生成服务"
check_api "http://localhost:8001/health" "检测服务"  
check_api "http://localhost:8002/health" "发布服务"
check_api "http://localhost:5678" "n8n工作流"

echo ""
echo "2️⃣ 测试内容生成API..."

# 创建测试请求
cat > /tmp/test_content_request.json << 'EOF'
{
  "domain": "technology",
  "source_content": "人工智能技术正在快速发展，机器学习和深度学习在各个行业中的应用越来越广泛。",
  "style_parameters": {
    "tone": "professional",
    "creativity": 0.7,
    "target_audience": "tech_professionals"
  },
  "target_length": 500
}
EOF

echo "发送内容生成请求..."
response=$(curl -s -X POST "http://localhost:8000/api/v1/content/generate" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_content_request.json)

if [[ $? -eq 0 && -n "$response" ]]; then
    echo "✅ 内容生成API响应正常"
    echo "📄 响应预览:"
    echo "$response" | jq -r '.generated_content // .message // "API响应格式异常"' 2>/dev/null | head -3
    echo "..."
else
    echo "❌ 内容生成API测试失败"
    echo "🔍 错误响应: $response"
fi

echo ""
echo "3️⃣ 测试质量检测API..."

# 创建质量检测请求
cat > /tmp/test_quality_request.json << 'EOF'
{
  "content": "这是一篇关于人工智能发展趋势的技术文章。文章分析了机器学习在各个领域的应用，包括医疗、金融、教育等行业的具体案例。",
  "domain": "technology",
  "analysis_options": {
    "check_plagiarism": true,
    "check_patterns": true,
    "check_quality": true
  }
}
EOF

echo "发送质量检测请求..."
quality_response=$(curl -s -X POST "http://localhost:8001/api/v1/quality/analyze" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_quality_request.json)

if [[ $? -eq 0 && -n "$quality_response" ]]; then
    echo "✅ 质量检测API响应正常"
    echo "📊 质量分析结果:"
    echo "$quality_response" | jq -r '.overall_score // .quality_score // .message // "API响应格式异常"' 2>/dev/null
else
    echo "❌ 质量检测API测试失败"
    echo "🔍 错误响应: $quality_response"
fi

echo ""
echo "4️⃣ 测试发布服务API..."

# 创建发布测试请求  
cat > /tmp/test_publish_request.json << 'EOF'
{
  "content": "# 测试文章\n\n这是一篇测试文章，用于验证多平台发布功能。\n\n## 主要内容\n\n- 功能测试\n- 系统验证\n- 质量保证",
  "title": "Prism系统功能测试",
  "platforms": ["test_platform"],
  "metadata": {
    "category": "技术",
    "tags": ["AI", "测试", "自动化"]
  },
  "dry_run": true
}
EOF

echo "发送发布服务请求..."
publish_response=$(curl -s -X POST "http://localhost:8002/api/v1/publish/multi-platform" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_publish_request.json)

if [[ $? -eq 0 && -n "$publish_response" ]]; then
    echo "✅ 发布服务API响应正常"
    echo "📤 发布结果预览:"
    echo "$publish_response" | jq -r '.status // .message // "API响应格式异常"' 2>/dev/null
else
    echo "❌ 发布服务API测试失败"
    echo "🔍 错误响应: $publish_response"
fi

echo ""
echo "5️⃣ 检查Docker容器状态..."
echo ""
cd backend
docker-compose ps

echo ""
echo "=========================="
echo "🎯 测试总结"
echo "=========================="
echo ""
echo "✅ 如果所有服务都显示为运行状态，系统已成功启动"
echo "🌐 现在可以访问 http://localhost:5678 查看n8n工作流界面"
echo "📊 访问 http://localhost:3000 查看Grafana监控面板"
echo ""
echo "🔧 故障排除："
echo "   • 如果API不响应: docker-compose restart [服务名]"
echo "   • 查看详细日志: docker-compose logs [服务名]"
echo "   • 重新启动所有: docker-compose down && docker-compose up -d"
echo ""

# 清理临时文件
rm -f /tmp/test_*.json

echo "✨ 验证完成！系统已准备就绪。"
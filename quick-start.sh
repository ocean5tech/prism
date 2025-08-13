#!/bin/bash

echo "🚀 启动 Prism 智能内容生成工厂"
echo "=================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 进入后端目录
cd backend

echo "📦 启动数据库服务..."
docker-compose up -d postgres redis qdrant influxdb

# 等待数据库启动
echo "⏳ 等待数据库启动 (30秒)..."
sleep 30

echo "🔧 启动核心服务..."
docker-compose up -d content-generation detection publishing

# 等待服务启动
echo "⏳ 等待核心服务启动 (20秒)..."  
sleep 20

echo "📊 启动监控服务..."
docker-compose up -d nginx prometheus grafana

# 返回根目录
cd ..

echo "🔄 启动 n8n 工作流引擎..."
cd n8n-workflows/deployment
docker-compose up -d

cd ../..

echo "⏳ 等待所有服务完全启动 (30秒)..."
sleep 30

echo ""
echo "✅ 系统启动完成！"
echo "=================================="
echo ""
echo "🌐 访问地址:"
echo "   • 内容生成API:     http://localhost:8000"
echo "   • 检测服务API:     http://localhost:8001" 
echo "   • 发布服务API:     http://localhost:8002"
echo "   • n8n工作流界面:   http://localhost:5678"
echo "   • Grafana监控:     http://localhost:3000"
echo "   • Prometheus:      http://localhost:9090"
echo ""
echo "🔑 默认登录信息:"
echo "   • n8n:     用户名: admin  密码: admin123"
echo "   • Grafana: 用户名: admin  密码: admin123"
echo ""
echo "🧪 快速验证命令:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:8001/health"
echo "   curl http://localhost:8002/health"
echo ""

# 运行健康检查
echo "🏥 运行健康检查..."
echo ""

# 检查核心服务
services=("8000" "8001" "8002")
service_names=("内容生成服务" "检测服务" "发布服务")

for i in "${!services[@]}"; do
    port="${services[$i]}"
    name="${service_names[$i]}"
    
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name (端口 $port) - 运行正常"
    else
        echo "❌ $name (端口 $port) - 连接失败"
    fi
done

# 检查n8n
if curl -s "http://localhost:5678" > /dev/null 2>&1; then
    echo "✅ n8n工作流引擎 (端口 5678) - 运行正常"
else  
    echo "❌ n8n工作流引擎 (端口 5678) - 连接失败"
fi

echo ""
echo "🎯 下一步："
echo "1. 打开浏览器访问 http://localhost:5678 查看n8n工作流"
echo "2. 运行测试命令验证API功能"
echo "3. 查看 README.md 了解更多使用方法"
echo ""
echo "📋 查看服务状态: docker-compose ps"
echo "📊 查看日志: docker-compose logs [服务名]"
echo ""
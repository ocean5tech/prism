#!/bin/bash
# Prism Platform 一键部署脚本
# 基于DEPLOYMENT-GUIDE.md的配置

set -e

echo "🚀 Prism Platform 快速部署"
echo "=========================="

# 检查当前目录
if [[ ! -f "DEPLOYMENT-GUIDE.md" ]]; then
    echo "❌ 错误: 请在Prism项目根目录运行此脚本"
    exit 1
fi

cd backend

echo "📋 1. 检查基础设施..."
# 检查关键容器
if ! podman ps | grep -q "prism-postgres.*Up"; then
    echo "❌ prism-postgres 容器未运行"
    echo "   请启动: podman start prism-postgres"
    exit 1
fi

if ! podman ps | grep -q "prism-redis.*Up"; then
    echo "❌ prism-redis 容器未运行"  
    echo "   请启动: podman start prism-redis"
    exit 1
fi

if ! podman ps | grep -q "prism-n8n.*Up"; then
    echo "❌ prism-n8n 容器未运行"
    echo "   请启动: podman start prism-n8n"
    exit 1
fi

echo "✅ 基础设施检查通过"

echo "🐍 2. 设置Python环境..."
if [[ ! -d "venv" ]]; then
    echo "   创建虚拟环境..."
    python3 -m venv venv
fi

echo "   激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -q fastapi uvicorn asyncpg redis pydantic requests

echo "✅ Python环境就绪"

echo "⚙️ 3. 检查配置文件..."
if [[ ! -f ".env" ]]; then
    echo "❌ .env 文件不存在，从.env.example复制并手动配置"
    cp .env.example .env
    echo "   请编辑 .env 文件后重新运行"
    exit 1
fi

# 检查关键微服务文件
required_files=(
    "simple-content-service.py"
    "simple-detection-service.py" 
    "simple-config-service.py"
    "simple-analytics-service.py"
    "start-simple-services.sh"
    "test-services.py"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ 缺少文件: $file"
        echo "   请参考 DEPLOYMENT-GUIDE.md 重新创建"
        exit 1
    fi
done

echo "✅ 配置文件检查通过"

echo "🚀 4. 启动微服务..."
chmod +x start-simple-services.sh

# 清理可能存在的旧进程
for port in 8010 8011 8013 8015; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "   清理端口 $port..."
        kill -9 $(lsof -Pi :$port -sTCP:LISTEN -t) 2>/dev/null || true
    fi
done

# 后台启动服务
echo "   启动微服务 (后台运行)..."
nohup ./start-simple-services.sh > deployment.log 2>&1 &
DEPLOY_PID=$!

# 等待服务启动
echo "   等待服务初始化..."
sleep 8

echo "🧪 5. 验证部署..."
source venv/bin/activate
if python3 test-services.py | grep -q "4/4 services working correctly"; then
    echo "✅ 所有微服务工作正常"
else
    echo "❌ 微服务测试失败，查看 deployment.log"
    exit 1
fi

echo ""
echo "🎉 部署完成!"
echo "============"
echo ""
echo "🌐 服务地址:"
echo "  n8n工作流:          http://localhost:8080"
echo "  Content Generation: http://localhost:8010/health"
echo "  Detection:          http://localhost:8011/health"
echo "  Configuration:      http://localhost:8013/health"
echo "  Analytics:          http://localhost:8015/health"
echo ""
echo "🔑 n8n登录信息:"
echo "  用户名: wooyoo@gmail.com"
echo "  密码:   Zaq12wsx"
echo ""
echo "📖 下一步:"
echo "  1. 在n8n中配置credentials (参考 DEPLOYMENT-GUIDE.md)"
echo "  2. 更新workflow中的服务URL"
echo "  3. 测试workflow执行"
echo ""
echo "🛑 停止服务: kill $DEPLOY_PID"
echo "📋 查看日志: tail -f deployment.log"
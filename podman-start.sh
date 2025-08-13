#!/bin/bash

echo "🚀 启动 Prism 智能内容生成工厂 (Podman版本)"
echo "============================================="

# 检查Podman是否安装
if ! command -v podman &> /dev/null; then
    echo "❌ Podman未安装，请先安装Podman"
    exit 1
fi

# 检查podman-compose是否可用
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    # 配置docker-compose使用podman
    export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
    COMPOSE_CMD="docker-compose"
else
    echo "❌ 需要安装 podman-compose 或 docker-compose"
    echo "安装命令: pip install podman-compose"
    exit 1
fi

echo "✅ 使用 $COMPOSE_CMD 管理容器"

# 启动podman socket (如果需要)
if [[ "$COMPOSE_CMD" == "docker-compose" ]]; then
    echo "🔧 启动 Podman socket..."
    systemctl --user enable --now podman.socket
    sleep 2
fi

# 进入后端目录
cd backend || { echo "❌ 无法进入backend目录"; exit 1; }

echo "📦 启动数据库服务..."
$COMPOSE_CMD up -d postgres redis qdrant influxdb

# 等待数据库启动
echo "⏳ 等待数据库启动 (30秒)..."
sleep 30

# 检查数据库是否启动成功
echo "🔍 检查数据库连接..."
if podman exec prism_postgres_1 pg_isready -U prism_user -d prism_db 2>/dev/null; then
    echo "✅ PostgreSQL 连接成功"
else
    echo "⚠️ PostgreSQL 可能还在启动中..."
fi

if podman exec prism_redis_1 redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis 连接成功"
else
    echo "⚠️ Redis 可能还在启动中..."
fi

echo "🔧 启动核心服务..."
$COMPOSE_CMD up -d content-generation detection publishing configuration analytics

# 等待服务启动
echo "⏳ 等待核心服务启动 (20秒)..."  
sleep 20

echo "📊 启动API网关和监控服务..."
$COMPOSE_CMD up -d nginx prometheus grafana

# 返回根目录
cd ..

echo "🔄 启动 n8n 工作流引擎..."
cd n8n-workflows/deployment || { echo "❌ 无法进入n8n目录"; exit 1; }

# 修改docker-compose.yml中的docker为podman(如果需要)
if [[ "$COMPOSE_CMD" == "podman-compose" ]]; then
    sed -i 's/docker:/podman:/' docker-compose.yml 2>/dev/null || true
fi

$COMPOSE_CMD up -d

cd ../..

echo "⏳ 等待所有服务完全启动 (30秒)..."
sleep 30

echo ""
echo "✅ 启动完成！现在检查服务状态..."
echo "=================================="

# 实际检查服务状态
check_service() {
    local port=$1
    local name=$2
    
    if curl -s --connect-timeout 5 "http://localhost:$port/health" >/dev/null 2>&1; then
        echo "✅ $name (端口 $port) - 运行正常"
        return 0
    elif curl -s --connect-timeout 5 "http://localhost:$port" >/dev/null 2>&1; then
        echo "🟡 $name (端口 $port) - 服务运行但健康检查失败"
        return 0
    else
        echo "❌ $name (端口 $port) - 连接失败"
        return 1
    fi
}

echo ""
echo "🏥 服务健康检查:"
check_service "8000" "内容生成服务"
check_service "8001" "检测服务" 
check_service "8002" "发布服务"
check_service "8003" "配置服务"
check_service "8004" "分析服务"
check_service "5678" "n8n工作流引擎"
check_service "3000" "Grafana监控"
check_service "9090" "Prometheus"

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

echo "📋 Podman容器状态:"
echo "=================="
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🛠️ 故障排除命令:"
echo "   • 查看所有容器: podman ps -a"
echo "   • 查看服务日志: podman logs [容器名]"
echo "   • 重启服务: $COMPOSE_CMD restart [服务名]"
echo "   • 停止所有服务: $COMPOSE_CMD down"
echo ""
echo "🧪 下一步: 运行 ./test-podman.sh 进行功能验证"
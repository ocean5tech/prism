#!/bin/bash

echo "🧪 Prism 系统实际验证测试 (Podman版)"
echo "=================================="

# 诚实说明：这是基于架构设计的测试，实际服务可能需要调整
echo "📋 说明: 此测试基于系统架构设计，部分服务可能需要进一步配置"
echo ""

# 实际检查podman容器状态
echo "1️⃣ 检查 Podman 容器状态..."
echo ""
if command -v podman &> /dev/null; then
    echo "📦 当前运行的容器:"
    podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "❌ 无法获取容器状态"
    echo ""
    
    echo "📊 容器资源使用:"
    podman stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "❌ 无法获取资源统计"
    echo ""
else
    echo "❌ Podman 未安装或不可用"
    exit 1
fi

# 实际测试网络连接
echo "2️⃣ 检查服务网络连接..."
echo ""

services=(
    "8000:内容生成服务"
    "8001:检测服务"
    "8002:发布服务" 
    "8003:配置服务"
    "8004:分析服务"
    "5678:n8n工作流"
    "3000:Grafana"
    "9090:Prometheus"
    "5432:PostgreSQL"
    "6379:Redis"
    "6333:Qdrant"
)

for service in "${services[@]}"; do
    port=$(echo $service | cut -d':' -f1)
    name=$(echo $service | cut -d':' -f2)
    
    if timeout 5 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null; then
        echo "✅ $name (端口 $port) - 端口开放"
    else
        echo "❌ $name (端口 $port) - 端口未开放或服务未启动"
    fi
done

echo ""
echo "3️⃣ 测试HTTP服务响应..."
echo ""

# 测试HTTP服务，但使用更宽松的条件
test_http_service() {
    local port=$1
    local name=$2
    local endpoint=${3:-"/"}
    
    echo -n "测试 $name ... "
    
    # 尝试多个可能的端点
    for ep in "$endpoint" "/health" "/api/health" "/"; do
        response=$(curl -s -w "%{http_code}" --connect-timeout 3 --max-time 5 "http://localhost:$port$ep" 2>/dev/null)
        http_code="${response: -3}"
        
        if [[ "$http_code" =~ ^[2-4][0-9][0-9]$ ]]; then
            echo "✅ 响应 HTTP $http_code"
            return 0
        fi
    done
    
    echo "❌ 无响应或服务未就绪"
    return 1
}

test_http_service "8000" "内容生成API" "/health"
test_http_service "8001" "检测服务API" "/health"  
test_http_service "8002" "发布服务API" "/health"
test_http_service "5678" "n8n界面" "/"
test_http_service "3000" "Grafana" "/"

echo ""
echo "4️⃣ 尝试基础API调用 (如果服务运行)..."
echo ""

# 只有在服务响应的情况下才进行API测试
if curl -s --connect-timeout 2 "http://localhost:8000/health" >/dev/null 2>&1; then
    echo "🟢 内容生成服务可访问，尝试API调用..."
    
    # 简单的健康检查或API调用
    response=$(curl -s -w "\n%{http_code}" --connect-timeout 5 --max-time 10 \
        -X GET "http://localhost:8000/health" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        echo "✅ API响应成功"
        echo "📄 响应内容: ${response%???}"  # 移除HTTP状态码
    else
        echo "❌ API调用失败"
    fi
else
    echo "🟡 内容生成服务未响应，跳过API测试"
fi

echo ""
echo "5️⃣ 检查数据库连接..."
echo ""

# 检查PostgreSQL连接
if podman ps --filter "name=postgres" --format "{{.Names}}" | grep -q postgres; then
    echo -n "测试PostgreSQL连接 ... "
    if podman exec -it $(podman ps --filter "name=postgres" --format "{{.Names}}" | head -1) \
        pg_isready -U prism_user -d prism_db 2>/dev/null | grep -q "accepting connections"; then
        echo "✅ PostgreSQL 连接正常"
    else
        echo "❌ PostgreSQL 连接失败"
    fi
else
    echo "🟡 PostgreSQL 容器未找到"
fi

# 检查Redis连接
if podman ps --filter "name=redis" --format "{{.Names}}" | grep -q redis; then
    echo -n "测试Redis连接 ... "
    if podman exec -it $(podman ps --filter "name=redis" --format "{{.Names}}" | head -1) \
        redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo "✅ Redis 连接正常"  
    else
        echo "❌ Redis 连接失败"
    fi
else
    echo "🟡 Redis 容器未找到"
fi

echo ""
echo "📊 当前系统状态总结:"
echo "===================="
echo ""

# 统计运行的服务
running_containers=$(podman ps --format "{{.Names}}" | wc -l)
echo "🔢 运行中的容器数量: $running_containers"

if [[ $running_containers -gt 0 ]]; then
    echo "📋 运行中的服务:"
    podman ps --format "   • {{.Names}} ({{.Status}})"
    echo ""
fi

echo "🎯 可访问的界面:"
if timeout 2 bash -c "echo >/dev/tcp/localhost/5678" 2>/dev/null; then
    echo "   ✅ n8n工作流: http://localhost:5678 (admin/admin123)"
fi
if timeout 2 bash -c "echo >/dev/tcp/localhost/3000" 2>/dev/null; then
    echo "   ✅ Grafana监控: http://localhost:3000 (admin/admin123)"
fi

echo ""
echo "💡 实用命令:"
echo "==========="
echo "   • 查看所有容器: podman ps -a"
echo "   • 查看容器日志: podman logs [容器名] --tail 50"
echo "   • 进入容器shell: podman exec -it [容器名] /bin/bash"
echo "   • 重启容器: podman restart [容器名]"
echo "   • 查看容器端口: podman port [容器名]"
echo ""

echo "🔧 故障排除:"
echo "==========="
echo "   • 如果服务未启动: cd backend && podman-compose up -d [服务名]"
echo "   • 如果端口冲突: 修改 docker-compose.yml 中的端口映射"
echo "   • 查看详细错误: podman logs [容器名] --tail 100"
echo "   • 重新构建: podman-compose up --build -d"
echo ""

# 提供下一步指导
if [[ $running_containers -eq 0 ]]; then
    echo "❌ 当前没有运行的容器"
    echo "🚀 请先运行: ./podman-start.sh"
elif [[ $running_containers -lt 5 ]]; then
    echo "⚠️ 部分服务可能未启动完成"
    echo "💤 建议等待更长时间或检查服务日志"
else
    echo "✅ 系统基本启动完成！"
    echo "🌐 现在可以访问 http://localhost:5678 查看n8n界面"
fi

echo ""
echo "📝 注意: 这是首次启动的实际测试，某些服务可能需要:"
echo "   • API密钥配置 (Claude, OpenAI等)"
echo "   • 数据库初始化脚本执行"
echo "   • 服务间网络连接建立"
echo "   • 更长的启动时间"
echo ""
echo "✨ 测试完成！根据以上结果调整系统配置。"
#!/bin/bash
# Prism Platform 服务停止脚本

echo "🛑 停止 Prism 微服务..."

cd backend 2>/dev/null || cd .

# 停止后台启动的服务
if [[ -f ".service_pids" ]]; then
    echo "   从PID文件停止服务..."
    PIDS=$(cat .service_pids)
    for pid in $PIDS; do
        if kill -0 $pid 2>/dev/null; then
            echo "   停止进程 $pid"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        fi
    done
    rm -f .service_pids
fi

# 强制清理端口 (如果PID文件方法失败)
echo "   清理端口占用..."
for port in 8010 8011 8013 8015; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "   强制清理端口 $port"
        kill -9 $(lsof -Pi :$port -sTCP:LISTEN -t) 2>/dev/null || true
    fi
done

# 检查并停止可能的后台部署进程
if pgrep -f "start-simple-services.sh" >/dev/null; then
    echo "   停止部署脚本进程..."
    pkill -f "start-simple-services.sh"
fi

# 清理日志文件 (可选)
if [[ -f "deployment.log" ]]; then
    echo "   清理部署日志 (保留最后100行)..."
    tail -n 100 deployment.log > deployment.log.tmp && mv deployment.log.tmp deployment.log
fi

echo "✅ 微服务已停止"

# 检查容器状态
echo ""
echo "📊 容器状态:"
if command -v podman >/dev/null; then
    podman ps | grep prism | while read line; do
        container_name=$(echo $line | awk '{print $NF}')
        echo "   $container_name: 运行中"
    done
    
    echo ""
    echo "🔧 如需停止容器:"
    echo "   podman stop prism-postgres prism-redis prism-n8n"
else
    echo "   Podman未安装或不可用"
fi

echo ""
echo "✅ 清理完成!"
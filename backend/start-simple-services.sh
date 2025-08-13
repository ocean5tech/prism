#!/bin/bash
# Simple microservices startup script for n8n workflow testing

echo "🚀 Starting Prism Microservices (Simplified Mode)"
echo "=================================================="

# Activate virtual environment
source venv/bin/activate

# Kill any existing services on these ports
echo "🧹 Cleaning up existing services..."
for port in 8010 8011 8013 8015; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "   Killing service on port $port"
        kill -9 $(lsof -Pi :$port -sTCP:LISTEN -t) 2>/dev/null || true
    fi
done

# Wait a moment for cleanup
sleep 2

echo "🏗️ Starting microservices..."

# Start content generation service (Port 8010)
echo "   Starting Content Generation Service on port 8010..."
python3 simple-content-service.py &
CONTENT_PID=$!

# Start detection service (Port 8011)  
echo "   Starting Detection Service on port 8011..."
python3 simple-detection-service.py &
DETECTION_PID=$!

# Start configuration service (Port 8013)
echo "   Starting Configuration Service on port 8013..."
python3 simple-config-service.py &
CONFIG_PID=$!

# Start analytics service (Port 8015)
echo "   Starting Analytics Service on port 8015..."
python3 simple-analytics-service.py &
ANALYTICS_PID=$!

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 5

# Check service health
echo "🩺 Checking service health..."
for port in 8010 8011 8013 8015; do
    service_name="unknown"
    case $port in
        8010) service_name="Content Generation" ;;
        8011) service_name="Detection" ;;
        8013) service_name="Configuration" ;;
        8015) service_name="Analytics" ;;
    esac
    
    if curl -s http://localhost:$port/health >/dev/null 2>&1; then
        echo "   ✅ $service_name (port $port) - Healthy"
    else
        echo "   ❌ $service_name (port $port) - Not responding"
    fi
done

echo ""
echo "🎉 Prism microservices are running!"
echo "=================================="
echo ""
echo "Service Health Checks:"
echo "  Content Generation:  http://localhost:8010/health"
echo "  Detection Service:   http://localhost:8011/health"
echo "  Configuration:       http://localhost:8013/health"  
echo "  Analytics:           http://localhost:8015/health"
echo ""
echo "API Endpoints:"
echo "  Content Generation:  http://localhost:8010/api/v1/content/generate"
echo "  Quality Detection:   http://localhost:8011/api/v1/detection/analyze"
echo "  Domain Config:       http://localhost:8013/api/v1/config/domains/{domain}"
echo "  Analytics Events:    http://localhost:8015/api/v1/analytics/events"
echo ""
echo "💡 Now you can test your n8n workflows at: http://localhost:8080"
echo ""
echo "🛑 To stop all services:"
echo "   kill $CONTENT_PID $DETECTION_PID $CONFIG_PID $ANALYTICS_PID"
echo ""
echo "📊 To view service logs, check the terminal output above"
echo ""

# Store PIDs for easy cleanup
echo "$CONTENT_PID $DETECTION_PID $CONFIG_PID $ANALYTICS_PID" > .service_pids

echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap 'echo ""; echo "🛑 Stopping all services..."; kill $CONTENT_PID $DETECTION_PID $CONFIG_PID $ANALYTICS_PID 2>/dev/null; rm -f .service_pids; echo "✅ All services stopped"; exit 0' INT

# Keep script running
wait
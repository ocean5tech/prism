#!/bin/bash
# Prism Microservices Startup Script

set -e

echo "🚀 Starting Prism Intelligent Content Generation Factory"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Copying from .env.example"
    cp .env.example .env
    echo "📝 Please edit .env file with your actual configuration values"
    echo "   Particularly important:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - JWT_SECRET_KEY"
    echo "   - Platform API keys (LinkedIn, Twitter, etc.)"
    read -p "Press Enter to continue after updating .env file..."
fi

# Load environment variables
source .env

# Validate required environment variables
required_vars=("JWT_SECRET_KEY" "ANTHROPIC_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Required environment variable $var is not set"
        echo "   Please update your .env file"
        exit 1
    fi
done

echo "📋 Configuration validated"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p nginx/ssl
mkdir -p monitoring
mkdir -p logs

# Generate self-signed SSL certificate for development
if [ ! -f nginx/ssl/cert.pem ]; then
    echo "🔐 Generating self-signed SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes \
        -subj "/C=US/ST=CA/L=San Francisco/O=Prism/CN=api.prism.com"
fi

# Start infrastructure services first
echo "🏗️  Starting infrastructure services..."
docker-compose up -d postgres redis qdrant influxdb minio

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 10

# Check database connectivity
echo "🔍 Checking database connectivity..."
docker-compose exec -T postgres pg_isready -U prism_user -d prism_db
docker-compose exec -T redis redis-cli ping

# Run database migrations/initialization
echo "🔄 Running database initialization..."
# Note: Add actual migration commands here when implemented
# docker-compose run --rm content-generation-service alembic upgrade head

# Start core services
echo "⚡ Starting core microservices..."
docker-compose up -d \
    content-generation-service \
    detection-service \
    publishing-service \
    configuration-service \
    user-management-service \
    analytics-service \
    file-storage-service \
    external-api-service

# Start API Gateway
echo "🌐 Starting API Gateway..."
docker-compose up -d api-gateway

# Start workflow engine
echo "🔄 Starting n8n workflow engine..."
docker-compose up -d n8n

# Start monitoring services
echo "📊 Starting monitoring services..."
docker-compose up -d prometheus grafana elasticsearch kibana

# Start background task workers
echo "⚙️  Starting background task workers..."
docker-compose up -d celery-worker celery-beat

# Wait for services to be healthy
echo "🏥 Waiting for services to become healthy..."
sleep 30

# Check service health
echo "🩺 Checking service health..."
services=("content-generation-service" "detection-service" "publishing-service")
for service in "${services[@]}"; do
    if docker-compose ps $service | grep -q "Up (healthy)"; then
        echo "✅ $service is healthy"
    else
        echo "⚠️  $service health check pending..."
    fi
done

# Show service URLs
echo ""
echo "🎉 Prism services are starting up!"
echo "=================================="
echo ""
echo "Service URLs:"
echo "  🌐 API Gateway:           http://localhost"
echo "  📖 API Documentation:     http://localhost/docs"
echo "  🔄 n8n Workflows:         http://localhost:5678 (admin/n8n123)"
echo "  📊 Grafana Dashboard:     http://localhost:3000 (admin/grafana123)"
echo "  🔍 Prometheus Metrics:    http://localhost:9090"
echo "  📋 Kibana Logs:           http://localhost:5601"
echo "  🗄️  MinIO Console:         http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "Service Endpoints:"
echo "  📝 Content Generation:    http://localhost/api/v1/content/"
echo "  🕵️  Quality Detection:     http://localhost/api/v1/quality/"
echo "  📢 Publishing:            http://localhost/api/v1/publishing/"
echo "  ⚙️  Configuration:         http://localhost/api/v1/config/"
echo "  👤 User Management:       http://localhost/api/v1/auth/"
echo "  📈 Analytics:             http://localhost/api/v1/analytics/"
echo "  📁 File Storage:          http://localhost/api/v1/files/"
echo ""
echo "Health Checks:"
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
    service_name="unknown"
    case $port in
        8000) service_name="Content Generation" ;;
        8001) service_name="Detection" ;;
        8002) service_name="Publishing" ;;
        8003) service_name="Configuration" ;;
        8004) service_name="User Management" ;;
        8005) service_name="Analytics" ;;
        8006) service_name="File Storage" ;;
        8007) service_name="External API" ;;
    esac
    echo "  $service_name: http://localhost:$port/health"
done

echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""
echo "🔧 To restart a specific service:"
echo "   docker-compose restart [service-name]"
echo ""
echo "Happy content generation! 🚀✨"
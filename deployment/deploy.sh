#!/bin/bash

# Prism Platform Deployment Script
# Supports Docker Compose and Kubernetes deployments

set -e

# Configuration
DEPLOYMENT_TYPE=${1:-docker}  # docker or kubernetes
ENVIRONMENT=${2:-production}  # dev, staging, production
IMAGE_TAG=${3:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    case $DEPLOYMENT_TYPE in
        "docker")
            if ! command -v docker &> /dev/null; then
                log_error "Docker is not installed"
                exit 1
            fi
            if ! command -v docker-compose &> /dev/null; then
                log_error "Docker Compose is not installed"
                exit 1
            fi
            ;;
        "kubernetes")
            if ! command -v kubectl &> /dev/null; then
                log_error "kubectl is not installed"
                exit 1
            fi
            if ! kubectl cluster-info &> /dev/null; then
                log_error "No Kubernetes cluster connection"
                exit 1
            fi
            ;;
        *)
            log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            log_error "Supported types: docker, kubernetes"
            exit 1
            ;;
    esac
    
    log_info "Prerequisites check passed"
}

# Create backup of current deployment
create_backup() {
    log_info "Creating deployment backup..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    case $DEPLOYMENT_TYPE in
        "docker")
            if docker-compose ps &> /dev/null; then
                docker-compose config > "$BACKUP_DIR/docker-compose.yml"
                log_info "Docker Compose configuration backed up"
            fi
            ;;
        "kubernetes")
            kubectl get all -n prism-$ENVIRONMENT -o yaml > "$BACKUP_DIR/kubernetes-resources.yaml"
            log_info "Kubernetes resources backed up"
            ;;
    esac
}

# Deploy with Docker Compose
deploy_docker() {
    log_info "Deploying with Docker Compose..."
    
    # Set environment variables
    export IMAGE_TAG
    export ENVIRONMENT
    export GITHUB_REPOSITORY="ocean5tech/prism"
    
    # Check if environment file exists
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warn "No .env file found, copying from .env.example"
            cp .env.example .env
            log_warn "Please update .env file with your actual values"
        else
            log_error "No .env file found and no .env.example available"
            exit 1
        fi
    fi
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose -f docker-compose.prod.yml pull
    
    # Start services
    log_info "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if curl -f http://localhost/health &> /dev/null; then
        log_info "Deployment successful - services are healthy"
    else
        log_warn "Services may not be fully ready yet"
    fi
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace prism-$ENVIRONMENT --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply secrets (assuming they exist)
    if [ -f "k8s/secrets-$ENVIRONMENT.yaml" ]; then
        kubectl apply -f "k8s/secrets-$ENVIRONMENT.yaml"
    else
        log_warn "No secrets file found for $ENVIRONMENT environment"
    fi
    
    # Apply deployment
    envsubst < deployment/kubernetes-deployment.yml | kubectl apply -f -
    
    # Wait for rollout
    log_info "Waiting for deployment rollout..."
    kubectl rollout status deployment/content-generation -n prism-$ENVIRONMENT
    
    # Check service status
    kubectl get pods -n prism-$ENVIRONMENT
}

# Deploy n8n workflows
deploy_n8n_workflows() {
    log_info "Deploying n8n workflows..."
    
    if [ -f "deployment/deploy-n8n-workflows.py" ]; then
        python3 deployment/deploy-n8n-workflows.py
    else
        log_warn "n8n workflow deployment script not found"
    fi
}

# Post-deployment verification
verify_deployment() {
    log_info "Running post-deployment verification..."
    
    case $DEPLOYMENT_TYPE in
        "docker")
            # Check container status
            if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
                log_info "Docker containers are running"
            else
                log_error "Some containers are not running"
                docker-compose -f docker-compose.prod.yml ps
                exit 1
            fi
            ;;
        "kubernetes")
            # Check pod status
            if kubectl get pods -n prism-$ENVIRONMENT | grep -q "Running"; then
                log_info "Kubernetes pods are running"
            else
                log_error "Some pods are not running"
                kubectl get pods -n prism-$ENVIRONMENT
                exit 1
            fi
            ;;
    esac
}

# Cleanup old resources
cleanup() {
    log_info "Cleaning up old resources..."
    
    case $DEPLOYMENT_TYPE in
        "docker")
            docker system prune -f
            docker volume prune -f
            ;;
        "kubernetes")
            # Clean up old replica sets
            kubectl delete replicaset -n prism-$ENVIRONMENT $(kubectl get rs -n prism-$ENVIRONMENT -o jsonpath='{.items[?(@.spec.replicas==0)].metadata.name}') 2>/dev/null || true
            ;;
    esac
}

# Main deployment flow
main() {
    log_info "Starting Prism deployment..."
    log_info "Deployment type: $DEPLOYMENT_TYPE"
    log_info "Environment: $ENVIRONMENT" 
    log_info "Image tag: $IMAGE_TAG"
    
    check_prerequisites
    create_backup
    
    case $DEPLOYMENT_TYPE in
        "docker")
            deploy_docker
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
    esac
    
    deploy_n8n_workflows
    verify_deployment
    cleanup
    
    log_info "Deployment completed successfully!"
    
    # Display access information
    case $DEPLOYMENT_TYPE in
        "docker")
            log_info "Services available at:"
            log_info "  - Main application: http://localhost"
            log_info "  - Grafana monitoring: http://localhost:3000"
            log_info "  - Prometheus metrics: http://localhost:9090"
            ;;
        "kubernetes")
            log_info "Getting service endpoints..."
            kubectl get services -n prism-$ENVIRONMENT
            ;;
    esac
}

# Handle script arguments
case "${1:-help}" in
    "docker"|"kubernetes")
        main
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [DEPLOYMENT_TYPE] [ENVIRONMENT] [IMAGE_TAG]"
        echo ""
        echo "DEPLOYMENT_TYPE: docker or kubernetes (default: docker)"
        echo "ENVIRONMENT:     dev, staging, or production (default: production)"  
        echo "IMAGE_TAG:       Docker image tag to deploy (default: latest)"
        echo ""
        echo "Examples:"
        echo "  $0 docker production v1.2.0"
        echo "  $0 kubernetes staging latest"
        echo "  $0 docker dev"
        ;;
    *)
        log_error "Invalid deployment type. Use 'docker' or 'kubernetes'"
        exit 1
        ;;
esac
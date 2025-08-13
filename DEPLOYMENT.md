# Prism Platform Deployment Guide

## 🚀 Quick Deployment

### Prerequisites
- Docker & Docker Compose installed
- Git repository access  
- n8n.cloud account (or self-hosted n8n)
- Claude API key

### 1. Clone and Setup
```bash
git clone https://github.com/ocean5tech/prism.git
cd prism
cp .env.example .env
# Edit .env with your actual values
```

### 2. Deploy Services
```bash
# Using our automated deployment script
./deployment/deploy.sh docker production

# Or manually with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Deploy n8n Workflows
```bash
# Set your n8n credentials
export N8N_API_KEY="your_api_key"
export N8N_BASE_URL="https://api.n8n.cloud"

# Deploy all workflows
python3 deployment/deploy-n8n-workflows.py
```

## 📊 Monitoring & Operations

### Access Points
- **Main Application**: http://localhost (via nginx load balancer)
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **Kibana Logs**: http://localhost:5601

### Service Health Checks
```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Individual service health
curl http://localhost:8001/health  # Content Generation
curl http://localhost:8002/health  # Detection Service  
curl http://localhost:8003/health  # Publishing Service
```

## 🏗️ Architecture Overview

### Service Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   n8n.cloud     │    │   Load Balancer  │    │   Monitoring    │
│   Workflows     │◄───┤     (nginx)      │───►│  (Prometheus)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
            ┌───────▼───┐  ┌───▼───┐  ┌───▼────┐
            │ Content   │  │Detection│ │Publishing│
            │Generation │  │ Service │ │ Service │
            └───────────┘  └─────────┘ └────────┘
                    │          │          │
                ┌───▼──────────▼──────────▼───┐
                │     Database Cluster        │
                │   PostgreSQL + Redis        │
                └─────────────────────────────┘
```

### Data Flow
1. **n8n Workflows** orchestrate content generation processes
2. **Python Microservices** handle domain-specific logic
3. **Database Layer** persists content and workflow state  
4. **Publishing Layer** distributes content to platforms
5. **Monitoring Stack** tracks performance and issues

## 🔧 Configuration Management

### Environment Variables
Critical environment variables in `.env`:

```bash
# Database
POSTGRES_PASSWORD=secure_password_here
DATABASE_URL=postgresql://user:password@postgres:5432/prism_db

# APIs  
CLAUDE_API_KEY=your_claude_api_key
N8N_API_KEY=your_n8n_api_key

# Social Platforms
TWITTER_API_KEY=your_twitter_key
FACEBOOK_API_KEY=your_facebook_key
LINKEDIN_API_KEY=your_linkedin_key

# Security
JWT_SECRET_KEY=your_jwt_secret
```

### n8n Workflow Configuration
Workflows automatically configure with environment variables:
- API endpoints point to service URLs
- Authentication headers use environment secrets
- Error handling routes to monitoring systems

## 📈 CI/CD Pipeline

### GitHub Actions Workflow
Our CI/CD pipeline automatically:

1. **Code Quality**: Security scans, linting, testing
2. **Build**: Docker images for all services  
3. **Test**: Unit tests, integration tests, n8n validation
4. **Deploy**: Blue-green deployment with health checks
5. **Monitor**: Post-deployment verification

### Manual Deployment
```bash
# Build specific service
docker build -t prism-content-generation backend/services/content-generation/

# Deploy to staging
./deployment/deploy.sh docker staging v1.2.0

# Deploy to production (with backup)
./deployment/deploy.sh docker production latest
```

## 🛡️ Security & Compliance

### Security Measures
- API key rotation supported
- Database connection encryption
- Container security scanning
- Secrets management via environment variables
- Network isolation with Docker networks

### Backup Strategy  
- Automated database backups (daily)
- n8n workflow version control
- Configuration backup before deployments
- Point-in-time recovery capability

## 🚨 Troubleshooting

### Common Issues

**Services Not Starting**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs [service_name]

# Check resource usage
docker stats

# Restart specific service
docker-compose -f docker-compose.prod.yml restart [service_name]
```

**n8n Workflow Failures**
```bash  
# Validate workflow files
python3 validate-n8n-ready-endpoints.py

# Check n8n connectivity
curl -H "X-N8N-API-KEY: $N8N_API_KEY" $N8N_BASE_URL/api/v1/workflows
```

**Database Connection Issues**
```bash
# Test database connection
docker-compose -f docker-compose.prod.yml exec postgres psql -U prism_user -d prism_db -c "SELECT 1;"

# Check Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### Performance Optimization

**Scaling Services**
```bash
# Scale content generation service
docker-compose -f docker-compose.prod.yml up -d --scale content-generation=3

# Monitor resource usage
docker-compose -f docker-compose.prod.yml exec prometheus promtool query instant 'container_memory_usage_bytes'
```

## 📞 Support & Maintenance

### Log Analysis
- **Application Logs**: Available in Kibana dashboard
- **System Metrics**: Prometheus + Grafana dashboards
- **n8n Workflow Logs**: n8n.cloud dashboard or self-hosted UI

### Regular Maintenance
- **Weekly**: Review performance metrics and error rates
- **Monthly**: Update Docker images and security patches
- **Quarterly**: Review and optimize n8n workflows

---

## 🎯 Next Steps

After successful deployment:

1. **Configure Monitoring Alerts**: Set up Grafana alerts for critical metrics
2. **Test Workflow Execution**: Run sample content generation workflows  
3. **Set Up Domain Configurations**: Add your specific content domains
4. **Configure Publishing Targets**: Connect your social media accounts
5. **Enable Backup Automation**: Set up automated backup schedules

For detailed configuration of specific components, see individual service documentation in `/backend/services/*/README.md`.
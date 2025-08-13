# Prism - Intelligent Content Generation Factory
## Backend Microservices Implementation

A scalable, multi-domain automated content generation and publishing platform leveraging adversarial AI optimization, workflow orchestration, and config-driven expansion.

## 🏗️ Architecture Overview

### Microservices Architecture
- **Content Generation Service** (Port 8000) - AI-powered content generation with Claude API
- **Detection Service** (Port 8001) - Quality analysis and adversarial optimization
- **Publishing Service** (Port 8002) - Multi-platform content distribution
- **Configuration Service** (Port 8003) - Domain management and templates
- **User Management Service** (Port 8004) - Authentication and authorization
- **Analytics Service** (Port 8005) - Performance metrics and reporting
- **File Storage Service** (Port 8006) - Asset and content storage
- **External API Service** (Port 8007) - Third-party integrations

### Infrastructure Components
- **PostgreSQL** - Primary database for structured data
- **Redis** - Caching and session management
- **Qdrant** - Vector database for content similarity
- **InfluxDB** - Time-series database for analytics
- **MinIO** - S3-compatible object storage
- **NGINX** - API Gateway with load balancing
- **n8n** - Workflow orchestration engine

### Monitoring Stack
- **Prometheus** - Metrics collection
- **Grafana** - Visualization and dashboards
- **Elasticsearch + Kibana** - Log aggregation and analysis
- **RabbitMQ** - Message queue for async processing

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM available
- Anthropic API key for Claude integration

### 1. Clone and Setup
```bash
cd /home/wyatt/dev-projects/Prism/backend
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 2. Start All Services
```bash
./scripts/start-services.sh
```

### 3. Access Services
- **API Gateway**: http://localhost
- **API Documentation**: http://localhost/docs
- **n8n Workflows**: http://localhost:5678 (admin/n8n123)
- **Grafana Dashboard**: http://localhost:3000 (admin/grafana123)

## 📋 Service Details

### Content Generation Service
**Port**: 8000  
**Purpose**: AI-powered content generation with domain expertise

**Key Features**:
- Claude API integration with cost optimization
- Domain-specific style parameters (Finance, Sports, Technology)
- Random style parameter injection for content variation
- Quality assessment and confidence scoring
- Template-based content generation
- Batch processing with concurrency control

**API Endpoints**:
- `POST /api/v1/content/generate` - Generate content
- `POST /api/v1/content/generate/batch` - Batch generation
- `GET /api/v1/content/{content_id}` - Retrieve content
- `GET /api/v1/templates/` - List templates

### Detection Service
**Port**: 8001  
**Purpose**: Quality analysis and adversarial optimization

**Key Features**:
- Comprehensive quality analysis (readability, originality, accuracy)
- Pattern detection for repetitive structures
- Plagiarism and similarity checking
- Adversarial feedback generation
- Quality threshold configuration
- ML-powered content assessment

**API Endpoints**:
- `POST /api/v1/quality/analyze` - Analyze content quality
- `POST /api/v1/quality/analyze/batch` - Batch analysis
- `POST /api/v1/quality/feedback` - Submit adversarial feedback
- `POST /api/v1/quality/thresholds` - Configure thresholds

### Publishing Service
**Port**: 8002  
**Purpose**: Multi-platform content distribution with 98% success rate

**Key Features**:
- Multi-platform publishing (WordPress, Medium, LinkedIn, Twitter)
- Platform-specific content formatting
- Scheduled publishing with optimal timing
- Engagement metrics collection
- Publication templates and customization
- Retry logic with exponential backoff

**API Endpoints**:
- `POST /api/v1/publishing/multi-platform` - Publish to multiple platforms
- `GET /api/v1/publishing/status/{publication_id}` - Check status
- `POST /api/v1/publishing/connections` - Manage platform connections
- `GET /api/v1/publishing/analytics` - Publication analytics

### Configuration Service
**Port**: 8003  
**Purpose**: Domain management and template-driven expansion

**Key Features**:
- Domain configuration management
- Template library and versioning
- Style parameter definitions
- Deployment automation for new domains
- Configuration validation and testing
- Hot configuration updates

### User Management Service
**Port**: 8004  
**Purpose**: Authentication and role-based access control

**Key Features**:
- JWT-based authentication
- Role-based permissions (Admin, Content Manager, Editor, Viewer)
- User profile management
- API key management
- Session management with Redis
- OAuth2 integration ready

### Analytics Service
**Port**: 8005  
**Purpose**: Performance metrics and comprehensive reporting

**Key Features**:
- Real-time performance metrics
- Content generation analytics
- Quality trend analysis
- Platform performance comparison
- Cost tracking and optimization
- Custom dashboard creation

### File Storage Service
**Port**: 8006  
**Purpose**: Asset and content storage management

**Key Features**:
- S3-compatible object storage with MinIO
- Content versioning and backup
- Media processing and optimization
- CDN integration ready
- Access control and permissions
- Automatic cleanup policies

### External API Service
**Port**: 8007  
**Purpose**: Third-party integrations and monitoring

**Key Features**:
- RSS feed processing
- Social media API integrations
- Webhook handling for n8n
- External service health monitoring
- Rate limiting and quota management
- API response caching

## 🔧 Configuration

### Environment Variables
Key configuration variables (see `.env.example`):

```bash
# Core Configuration
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/prism_db
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key

# AI APIs
ANTHROPIC_API_KEY=your-anthropic-key
CLAUDE_DEFAULT_MODEL=claude-3-sonnet-20240229

# Platform APIs
LINKEDIN_CLIENT_ID=your-linkedin-id
TWITTER_API_KEY=your-twitter-key
MEDIUM_CLIENT_ID=your-medium-id
```

### Domain Configuration
The system supports three primary domains with specific configurations:

#### Finance Domain
- **Style**: Professional, analytical, cautious
- **Requirements**: Fact-checking, risk disclaimers, data-driven analysis
- **Quality Thresholds**: 95%+ accuracy, regulatory compliance
- **Templates**: Market analysis, investment insights, financial news

#### Sports Domain
- **Style**: Engaging, enthusiastic, data-rich
- **Requirements**: Real-time statistics, player/team accuracy
- **Quality Thresholds**: 90%+ accuracy, high engagement potential
- **Templates**: Game analysis, player profiles, season previews

#### Technology Domain
- **Style**: Technical, forward-thinking, innovative
- **Requirements**: Technical accuracy, trend analysis
- **Quality Thresholds**: 90%+ accuracy, technical depth
- **Templates**: Product reviews, industry analysis, innovation spotlights

## 📊 Monitoring and Observability

### Health Checks
Each service provides comprehensive health endpoints:
- `/health` - Basic health status
- `/health/live` - Kubernetes liveness probe
- `/health/ready` - Kubernetes readiness probe
- `/metrics` - Prometheus metrics
- `/prometheus` - Prometheus metrics endpoint

### Metrics Collection
- **Request metrics**: Response time, error rates, throughput
- **AI API metrics**: Token usage, costs, response times
- **Quality metrics**: Content scores, pattern detection rates
- **Publishing metrics**: Success rates, platform performance

### Logging
- Structured logging with correlation IDs
- Centralized log aggregation with Elasticsearch
- Log levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- Request tracing across services

## 🧪 Testing

### Running Tests
```bash
# Unit tests for individual services
docker-compose run --rm content-generation-service pytest tests/

# Integration tests
docker-compose run --rm --entrypoint pytest content-generation-service tests/integration/

# Load testing
docker-compose run --rm --entrypoint locust content-generation-service
```

### Test Coverage
- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for complete workflows
- Performance tests for scalability validation

## 🚀 Deployment

### Development Deployment
```bash
./scripts/start-services.sh
```

### Production Deployment
1. **Infrastructure Setup**:
   ```bash
   # Scale services for production
   docker-compose up -d --scale content-generation-service=3
   docker-compose up -d --scale detection-service=2
   docker-compose up -d --scale publishing-service=2
   ```

2. **SSL Configuration**:
   - Replace self-signed certificates in `nginx/ssl/`
   - Configure proper domain names
   - Set up cert auto-renewal

3. **Database Optimization**:
   - Configure PostgreSQL for production workloads
   - Set up read replicas for analytics
   - Configure backup strategies

4. **Monitoring Setup**:
   - Configure Grafana dashboards
   - Set up alerting rules in Prometheus
   - Configure log retention policies

## 🔄 n8n Workflow Integration

The system integrates with n8n for workflow orchestration:

### Workflow Patterns
1. **Content Generation Pipeline**: RSS → Content Generation → Quality Check → Publishing
2. **Adversarial Optimization**: Generation → Detection → Feedback → Regeneration
3. **Multi-Platform Publishing**: Content → Format → Distribute → Monitor
4. **Domain Expansion**: Configure → Validate → Test → Deploy

### Custom Nodes
Located in `n8n-workflows/custom-nodes/`:
- **Content Intelligence Node**: Domain classification and routing
- **Quality Analysis Node**: Integration with detection service
- **Publishing Node**: Multi-platform distribution

## 🛠️ Development

### Adding New Services
1. Create service directory: `services/new-service/`
2. Implement FastAPI application with shared components
3. Add to `docker-compose.yml`
4. Update NGINX configuration
5. Add monitoring and health checks

### Extending Domains
1. Add domain configuration in Configuration Service
2. Create domain-specific templates
3. Configure quality thresholds
4. Add platform-specific formatting
5. Deploy and test

### Custom Platform Integration
1. Implement platform adapter in Publishing Service
2. Add authentication flow
3. Create content formatting templates
4. Add metrics collection
5. Test integration thoroughly

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost/docs
- **ReDoc**: http://localhost/redoc

### API Versioning
- Current version: v1
- Backward compatibility maintained
- Deprecation notices for breaking changes

### Authentication
All endpoints require JWT authentication except:
- Health checks (`/health`)
- Public documentation (`/docs`)
- Webhook endpoints (with secret validation)

## 🔒 Security

### Authentication & Authorization
- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- API key management for service-to-service communication
- Rate limiting and DDoS protection

### Data Protection
- Encryption at rest and in transit
- Secure credential storage
- PII data anonymization
- GDPR compliance ready

### Network Security
- Service-to-service mTLS (production)
- Network segmentation with Docker networks
- Firewall rules and access control
- Regular security scanning

## 📈 Performance

### Benchmarks
- **Content Generation**: <30 seconds for 1000-word articles
- **Quality Analysis**: <15 seconds comprehensive analysis
- **Publishing**: <20 seconds multi-platform distribution
- **API Response**: <500ms for 95% of requests

### Scalability
- Horizontal scaling supported for all services
- Auto-scaling based on queue depth and CPU usage
- Database read replicas for analytics workloads
- CDN integration for static content delivery

### Optimization
- Async processing with Celery workers
- Redis caching for frequently accessed data
- Connection pooling for database access
- Request deduplication and batching

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request

### Code Standards
- Python: Black formatting, isort imports, flake8 linting
- Type hints required for all functions
- Comprehensive docstrings
- Test coverage >80%

### Pull Request Process
1. Update documentation
2. Add/update tests
3. Ensure CI passes
4. Request code review
5. Address feedback

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service logs
docker-compose logs [service-name]

# Check service health
curl http://localhost:[port]/health
```

#### Database Connection Issues
```bash
# Check PostgreSQL connectivity
docker-compose exec postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### High Memory Usage
```bash
# Check resource usage
docker stats

# Scale down services if needed
docker-compose scale content-generation-service=1
```

#### API Authentication Errors
```bash
# Verify JWT secret is set
echo $JWT_SECRET_KEY

# Check token expiration
curl -H "Authorization: Bearer [token]" http://localhost/api/v1/auth/verify
```

### Getting Help
- Check service logs: `docker-compose logs -f [service]`
- Review API documentation: http://localhost/docs
- Monitor service health: http://localhost/health
- Check Grafana dashboards: http://localhost:3000

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Anthropic Claude** - AI content generation
- **n8n** - Workflow automation
- **Docker** - Containerization platform
- **NGINX** - Web server and reverse proxy

---

**Prism Intelligent Content Generation Factory** - Revolutionizing content creation with AI-powered automation and quality optimization. 🚀✨
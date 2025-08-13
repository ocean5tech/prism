# n8n Workflows for Intelligent Content Generation Factory

## Overview

This directory contains comprehensive n8n workflow configurations for the multi-domain content generation platform. The workflows orchestrate the entire content pipeline from RSS monitoring to multi-platform publishing with adversarial quality optimization.

## Workflow Architecture

### Core Workflows

#### 1. Content Generation Pipeline (`01-content-generation-pipeline.json`)
**Purpose**: Main content production workflow handling RSS feeds to published content
**Trigger**: RSS feed polling (5-minute intervals)
**Processing Flow**:
```
RSS Monitor → Domain Classification → Content Generation → Quality Detection → Publishing → Analytics
```

**Key Features**:
- Multi-domain routing (Finance, Sports, Technology)
- Intelligent style parameter application
- Quality gate validation (85% threshold)
- Automatic regeneration for low-quality content
- Comprehensive error handling with retries

**Performance Specs**:
- Target processing time: <30 seconds per article
- Quality threshold: 85% minimum score
- Success rate: >98% with automatic retry

#### 2. Adversarial Optimization Loop (`02-adversarial-optimization.json`)
**Purpose**: Continuous quality improvement through pattern detection and style variation
**Trigger**: Webhook-based (scheduled or event-driven)
**Processing Flow**:
```
Pattern Detection → Threshold Check → Style Variations → Test Generation → Quality Scoring → Best Selection → Configuration Update
```

**Key Features**:
- Pattern similarity detection (75% threshold)
- 5 style variations per optimization cycle
- A/B testing for style effectiveness
- Automatic style configuration updates
- Optimization metrics tracking

#### 3. Global Error Handler (`03-error-handler-workflow.json`)
**Purpose**: Centralized error handling and recovery system
**Trigger**: Webhook calls from other workflows on errors
**Processing Flow**:
```
Error Categorization → Severity Assessment → Alert Generation → Retry Strategy → Recovery Actions → Metrics Recording
```

**Key Features**:
- Intelligent error categorization
- Exponential backoff retry logic (max 3 attempts)
- Critical error alerting
- Dead letter queue for unrecoverable errors
- Comprehensive error metrics

### Custom Nodes

#### Domain Classifier Node (`custom-nodes/domain-classifier-node.js`)
**Purpose**: Intelligent content classification with confidence scoring
**Functionality**:
- Multi-domain classification (Finance, Sports, Technology)
- Confidence threshold validation (default 70%)
- Domain-specific style parameter generation
- Graceful error handling for unknown content

**Configuration**:
```javascript
{
  contentField: "content",      // Field containing content to classify
  titleField: "title",          // Field containing title
  confidenceThreshold: 0.7,     // Minimum confidence for classification
  apiEndpoint: "http://configuration-service:8000/api/v1/domains/classify"
}
```

## Integration Patterns

### FastAPI Service Integration
**Authentication**: JWT Bearer tokens with request tracing
**Error Handling**: Comprehensive retry logic with exponential backoff
**Timeout Management**: Service-specific timeouts (10-30 seconds)
**Rate Limiting**: Built-in rate limiting for external APIs

### Service Endpoints Integration

#### Content Generation Service
```
POST /api/v1/content/generate
- Domain-specific content generation
- Style parameter application
- Quality indicators response
```

#### Detection Service
```
POST /api/v1/quality/analyze
- Content quality analysis
- Pattern detection
- Compliance checking
```

#### Configuration Service
```
POST /api/v1/domains/classify
- Content domain classification
- Style configuration management
```

#### Publishing Service
```
POST /api/v1/publish/multi-platform
- Multi-platform content distribution
- Scheduling management
- Success tracking
```

## Deployment and Configuration

### Environment Variables
```bash
# Service Endpoints
CONTENT_SERVICE_URL=http://content-generation-service:8000
DETECTION_SERVICE_URL=http://detection-service:8000
CONFIG_SERVICE_URL=http://configuration-service:8000
PUBLISHING_SERVICE_URL=http://publishing-service:8000
ANALYTICS_SERVICE_URL=http://analytics-service:8000

# Authentication
API_TOKEN=your-jwt-token-here
WEBHOOK_SECRET=your-webhook-secret

# n8n Configuration
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=secure-password
```

### Workflow Import Instructions

1. **Access n8n Interface**: Navigate to your n8n instance (typically http://localhost:5678)

2. **Import Workflows**:
   - Go to Workflows section
   - Click "Import from File"
   - Select each `.json` file from this directory
   - Activate workflows after import

3. **Install Custom Nodes**:
   ```bash
   # Copy custom nodes to n8n directory
   cp -r custom-nodes/ ~/.n8n/nodes/
   # Restart n8n to load custom nodes
   docker-compose restart n8n
   ```

4. **Configure Webhooks**:
   - Set webhook URLs in your service configurations
   - Update webhook secrets in environment variables
   - Test webhook connectivity

### Domain Configuration

#### Finance Domain Settings
```json
{
  "domain": "finance",
  "style_config": {
    "tone": ["professional", "analytical", "authoritative"],
    "structure": ["executive_summary", "detailed_analysis", "market_implications"],
    "vocabulary": "financial_technical",
    "compliance_level": "high",
    "risk_disclosure": true
  },
  "quality_thresholds": {
    "accuracy": 0.95,
    "compliance": 0.99,
    "readability": 0.80
  }
}
```

#### Sports Domain Settings
```json
{
  "domain": "sports",
  "style_config": {
    "tone": ["dynamic", "engaging", "narrative"],
    "structure": ["event_recap", "player_analysis", "predictions"],
    "vocabulary": "sports_accessible",
    "real_time_focus": true,
    "statistics_integration": true
  },
  "quality_thresholds": {
    "engagement": 0.90,
    "accuracy": 0.85,
    "timeliness": 0.95
  }
}
```

#### Technology Domain Settings
```json
{
  "domain": "technology",
  "style_config": {
    "tone": ["informative", "forward_looking", "technical"],
    "structure": ["innovation_overview", "technical_details", "industry_impact"],
    "vocabulary": "tech_industry",
    "trend_analysis": true,
    "technical_depth": "medium"
  },
  "quality_thresholds": {
    "technical_accuracy": 0.90,
    "innovation_relevance": 0.85,
    "readability": 0.75
  }
}
```

## Monitoring and Analytics

### Key Metrics Tracked
- **Content Generation Performance**: Processing time, success rate, quality scores
- **Adversarial Optimization**: Pattern detection cycles, improvement rates
- **Error Recovery**: Error rates, recovery success, manual intervention needs
- **Publishing Success**: Multi-platform delivery rates, engagement metrics

### Alert Configurations
- **Critical Errors**: Immediate notifications for high-severity issues
- **Quality Degradation**: Alerts when quality scores drop below thresholds
- **Service Unavailability**: Health check failures and service outages
- **Performance Issues**: Processing time exceeds acceptable limits

### Dashboard Metrics
- Real-time workflow execution status
- Content generation volume by domain
- Quality improvement trends
- Service health indicators
- Error rate analytics

## Troubleshooting

### Common Issues

#### Workflow Execution Failures
- **Check**: Service endpoint availability
- **Verify**: Authentication token validity
- **Review**: Error logs in analytics service
- **Action**: Restart failed executions manually

#### Quality Detection Issues
- **Check**: Detection service configuration
- **Verify**: Content format compliance
- **Review**: Domain-specific quality thresholds
- **Action**: Adjust quality parameters if needed

#### Publishing Failures
- **Check**: Platform API credentials
- **Verify**: Content format requirements
- **Review**: Rate limiting constraints
- **Action**: Use manual publishing override

### Performance Optimization
- **Batch Processing**: Use batch modes for high-volume operations
- **Parallel Execution**: Enable parallel processing where possible
- **Cache Optimization**: Implement intelligent caching for repeated requests
- **Resource Scaling**: Monitor and scale n8n instances as needed

## Development Guidelines

### Adding New Domains
1. Update domain classifier configuration
2. Create domain-specific style parameters
3. Add quality thresholds for new domain
4. Test classification and generation pipeline
5. Deploy configuration updates

### Workflow Modifications
1. Test changes in development environment
2. Validate with sample data
3. Monitor performance impact
4. Deploy during maintenance windows
5. Monitor post-deployment metrics

### Custom Node Development
1. Follow n8n node development standards
2. Include comprehensive error handling
3. Add proper parameter validation
4. Provide clear documentation
5. Test with various input scenarios

This workflow system provides a robust, scalable foundation for multi-domain content generation with enterprise-grade reliability and monitoring.
# FastAPI Integration Patterns for n8n Workflows

## Overview

This document defines the integration patterns between n8n workflows and FastAPI microservices for the Intelligent Content Generation Factory.

## Authentication Pattern

### JWT Bearer Token Authentication
```javascript
// Standard authentication header for all service calls
const authHeaders = {
  'Authorization': `Bearer ${$env.API_TOKEN}`,
  'Content-Type': 'application/json',
  'X-Request-ID': `${$execution.id}-${$node.name}`,
  'X-Workflow-ID': '{{$workflow.id}}'
};
```

### Service Discovery Pattern
```javascript
// Environment-based service endpoints
const serviceEndpoints = {
  contentGeneration: process.env.CONTENT_SERVICE_URL || 'http://content-generation-service:8000',
  detection: process.env.DETECTION_SERVICE_URL || 'http://detection-service:8000', 
  configuration: process.env.CONFIG_SERVICE_URL || 'http://configuration-service:8000',
  publishing: process.env.PUBLISHING_SERVICE_URL || 'http://publishing-service:8000',
  analytics: process.env.ANALYTICS_SERVICE_URL || 'http://analytics-service:8000'
};
```

## API Call Patterns

### 1. Content Generation Service Integration

#### Generate Content Endpoint
```javascript
{
  "url": "{{$env.CONTENT_SERVICE_URL}}/api/v1/content/generate",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer {{$env.API_TOKEN}}",
    "Content-Type": "application/json",
    "X-Domain": "{{$json.domain}}",
    "X-Request-Priority": "{{$json.priority || 'normal'}}"
  },
  "body": {
    "domain": "{{$json.domain}}",
    "source_content": "{{$json.source_text}}",
    "style_parameters": "{{$json.style_config}}",
    "target_length": "{{$json.target_length || 1000}}",
    "generation_settings": {
      "creativity_level": "{{$json.creativity_level || 0.7}}",
      "fact_check_required": "{{$json.domain === 'finance'}}",
      "real_time_data": "{{$json.domain === 'sports'}}"
    }
  },
  "timeout": 30000,
  "retry": {
    "enabled": true,
    "maxRetries": 2,
    "waitBetweenTries": 5000,
    "retryOn": [408, 429, 500, 502, 503, 504]
  }
}
```

#### Expected Response Format
```json
{
  "content_id": "uuid",
  "generated_content": "string",
  "metadata": {
    "word_count": 1000,
    "generation_time": 25.5,
    "style_applied": "finance_professional",
    "confidence_score": 0.92
  },
  "quality_indicators": {
    "readability_score": 8.5,
    "originality_score": 0.95,
    "domain_relevance": 0.88
  }
}
```

### 2. Detection Service Integration

#### Quality Analysis Endpoint
```javascript
{
  "url": "{{$env.DETECTION_SERVICE_URL}}/api/v1/quality/analyze",
  "method": "POST", 
  "headers": {
    "Authorization": "Bearer {{$env.API_TOKEN}}",
    "Content-Type": "application/json",
    "X-Analysis-Type": "comprehensive"
  },
  "body": {
    "content": "{{$json.generated_content}}",
    "domain": "{{$json.domain}}",
    "original_source": "{{$json.source_url}}",
    "analysis_options": {
      "check_plagiarism": true,
      "check_patterns": true,
      "check_domain_accuracy": true,
      "check_compliance": "{{$json.domain === 'finance'}}"
    }
  },
  "timeout": 15000
}
```

### 3. Configuration Service Integration

#### Domain Classification Endpoint
```javascript
{
  "url": "{{$env.CONFIG_SERVICE_URL}}/api/v1/domains/classify",
  "method": "POST",
  "body": {
    "title": "{{$json.title}}",
    "content": "{{$json.content}}",
    "url": "{{$json.source_url}}",
    "metadata": "{{$json.source_metadata}}"
  },
  "timeout": 10000
}
```

### 4. Publishing Service Integration

#### Multi-Platform Publishing Endpoint
```javascript
{
  "url": "{{$env.PUBLISHING_SERVICE_URL}}/api/v1/publish/multi-platform",
  "method": "POST",
  "body": {
    "content": "{{$json.final_content}}",
    "domain": "{{$json.domain}}",
    "platforms": "{{$json.target_platforms}}",
    "scheduling": {
      "immediate": "{{$json.publish_immediately || true}}",
      "scheduled_time": "{{$json.publish_time}}",
      "timezone": "{{$json.timezone || 'UTC'}}"
    },
    "metadata": {
      "tags": "{{$json.content_tags}}",
      "category": "{{$json.category}}",
      "priority": "{{$json.priority || 'normal'}}"
    }
  },
  "timeout": 20000,
  "retry": {
    "enabled": true,
    "maxRetries": 3,
    "waitBetweenTries": 5000
  }
}
```

## Error Handling Patterns

### Standard Error Response Processing
```javascript
// n8n Function Node for error handling
const errorHandler = `
if ($response.statusCode >= 400) {
  const errorResponse = {
    error_code: $response.statusCode,
    error_message: $response.body.detail || 'Service error',
    service_name: $node.name,
    timestamp: new Date().toISOString(),
    request_id: $response.headers['x-request-id'],
    retry_after: $response.headers['retry-after']
  };
  
  // Log error for monitoring
  await $this.helpers.request({
    method: 'POST',
    url: process.env.ANALYTICS_SERVICE_URL + '/api/v1/errors/log',
    headers: { 'Authorization': 'Bearer ' + process.env.API_TOKEN },
    body: errorResponse,
    json: true
  });
  
  // Determine retry strategy
  if ([408, 429, 502, 503, 504].includes($response.statusCode)) {
    throw new Error('RETRIABLE_ERROR: ' + errorResponse.error_message);
  } else {
    throw new Error('PERMANENT_ERROR: ' + errorResponse.error_message);
  }
}
`;
```

### Service Health Check Pattern
```javascript
{
  "url": "{{$env.SERVICE_URL}}/health",
  "method": "GET",
  "timeout": 5000,
  "ignoreHttpStatusErrors": true
}
```

## Webhook Integration Patterns

### Async Processing Webhooks
```javascript
// Webhook configuration for long-running operations
{
  "httpMethod": "POST",
  "path": "content-generation-callback/{{$execution.id}}",
  "responseMode": "responseNode",
  "options": {
    "noResponseBody": false,
    "rawBody": false,
    "ignoreBots": true
  },
  "authentication": "headerAuth",
  "authenticationKeys": {
    "headerAuth": {
      "name": "X-Webhook-Secret",
      "value": "{{$env.WEBHOOK_SECRET}}"
    }
  }
}
```

### Webhook Security Validation
```javascript
// Webhook security validation function
const validateWebhook = `
const receivedSignature = $request.headers['x-webhook-signature'];
const expectedSignature = crypto
  .createHmac('sha256', process.env.WEBHOOK_SECRET)
  .update(JSON.stringify($request.body))
  .digest('hex');

if (receivedSignature !== expectedSignature) {
  throw new Error('WEBHOOK_VALIDATION_FAILED');
}
`;
```

## Data Transformation Patterns

### Request Transformation
```javascript
// Transform n8n data to FastAPI expected format
const transformRequest = `
return {
  json: {
    domain: $json.classified_domain || 'unknown',
    source_content: $json.article_text || $json.content,
    style_parameters: {
      tone: $json.domain_config?.tone || ['neutral'],
      structure: $json.domain_config?.structure || ['standard'],
      vocabulary: $json.domain_config?.vocabulary || 'general',
      ...($json.custom_style_params || {})
    },
    target_length: parseInt($json.word_count) || 1000,
    metadata: {
      source_url: $json.link || $json.url,
      source_title: $json.title,
      source_published: $json.pubDate || $json.published_date,
      workflow_execution: $execution.id,
      processing_timestamp: new Date().toISOString()
    }
  }
};
`;
```

### Response Transformation
```javascript
// Transform FastAPI response to n8n workflow format
const transformResponse = `
return {
  json: {
    ...($json.original_data || {}),
    generated_content: $json.generated_content,
    quality_score: $json.quality_indicators?.overall_score || 0,
    processing_time: $json.metadata?.generation_time || 0,
    content_metadata: {
      word_count: $json.metadata?.word_count || 0,
      readability: $json.quality_indicators?.readability_score || 0,
      originality: $json.quality_indicators?.originality_score || 0
    },
    ready_for_publishing: $json.quality_indicators?.overall_score >= 0.85,
    next_action: $json.quality_indicators?.overall_score >= 0.85 ? 'publish' : 'regenerate'
  }
};
`;
```

## Rate Limiting and Performance

### Rate Limiting Configuration
```javascript
// Rate limiting for external API calls
const rateLimitConfig = {
  claude_api: {
    requests_per_minute: 60,
    requests_per_hour: 1000,
    concurrent_requests: 5
  },
  internal_services: {
    requests_per_second: 100,
    concurrent_requests: 20
  }
};
```

### Batch Processing Pattern
```javascript
// Batch processing for high-volume operations
{
  "batchSize": 10,
  "batchMode": "each",
  "continueOnFail": true,
  "alwaysOutputData": true,
  "executeOnce": false
}
```

## Monitoring and Observability

### Request Tracing Headers
```javascript
const tracingHeaders = {
  'X-Trace-ID': `${$execution.id}`,
  'X-Parent-Span-ID': `${$node.name}-${Date.now()}`,
  'X-Workflow-Name': '{{$workflow.name}}',
  'X-Node-Name': '{{$node.name}}',
  'X-Execution-Mode': '{{$mode}}'
};
```

### Performance Metrics Collection
```javascript
// Performance metrics to collect
const metricsData = {
  execution_id: $execution.id,
  workflow_name: $workflow.name,
  node_name: $node.name,
  start_time: $execution.startedAt,
  duration_ms: Date.now() - new Date($execution.startedAt).getTime(),
  status: 'success', // or 'error'
  service_endpoint: $json.service_url,
  response_size: JSON.stringify($json).length
};
```

This integration specification ensures robust, scalable communication between n8n workflows and FastAPI microservices with proper error handling, monitoring, and performance optimization.
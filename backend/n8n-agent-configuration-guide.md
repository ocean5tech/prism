# n8n AI Agent Configuration Guide

## Configuration Files Overview

### 1. Basic AI Agent Configuration
**File:** `/home/wyatt/dev-projects/Prism/backend/n8n-ai-agent-config.json`
- Standard configuration for content generation
- Simple memory setup with buffer memory
- Basic system prompt with domain-specific guidelines
- JSON output format for structured content

### 2. Enhanced AI Agent Configuration
**File:** `/home/wyatt/dev-projects/Prism/backend/n8n-enhanced-ai-agent-config.json`
- Advanced configuration with comprehensive features
- Enhanced memory management with session tracking
- Sophisticated system prompt with quality frameworks
- Tool integration capabilities
- Extended timeout and token limits

## Key Configuration Components

### System Prompt Design
The system prompt is designed to:
- Establish AI identity as content generation specialist
- Provide domain-specific guidelines (Finance, Sports, Technology)
- Define output format requirements (JSON structure)
- Set quality standards and SEO optimization rules
- Include content transformation guidelines

### Memory Configuration
```json
{
  "type": "bufferMemory",
  "options": {
    "maxTokenLimit": 6000,
    "sessionKey": "content_gen_{{ $json.domain }}_{{ session_id }}",
    "memoryKey": "content_history",
    "returnMessages": true
  }
}
```

**Benefits:**
- Maintains context across multiple content generations
- Domain-specific memory sessions
- Prevents repetitive content patterns
- Enables learning from previous interactions

### User Message Template
```
{{ $json.ai_prompt }}

**Additional Context:**
- Source Domain: {{ $json.domain || 'general' }}
- Target Audience: {{ $json.target_audience || 'general readers' }}
- Content Type: {{ $json.content_type || 'article' }}
```

This template:
- Uses Content Processor output (`ai_prompt`)
- Adds dynamic context based on available data
- Provides fallback values for missing parameters
- Enables flexible content generation

### Tool Integration (Enhanced Version)
Recommended tools for content generation:
1. **content-validator**: Quality and SEO validation
2. **plagiarism-checker**: Originality verification
3. **seo-optimizer**: Search optimization analysis

### Output Format
Both configurations enforce JSON output with these fields:
- `title`: SEO-optimized headline
- `meta_description`: Search result snippet
- `content`: Full article content
- `tags`: SEO keywords array
- `domain`: Content domain classification
- `word_count`: Article length metric
- `reading_time`: User experience indicator

## Implementation Steps

### 1. Choose Configuration Level
- **Basic**: Use for standard content generation needs
- **Enhanced**: Use for premium quality and advanced features

### 2. Apply Configuration in n8n
1. Open your AI Agent node in n8n
2. Copy the JSON configuration from chosen file
3. Paste into the node's JSON editor or configure via UI
4. Adjust parameters based on specific requirements

### 3. Content Processor Integration
Ensure your Content Processor node outputs:
```json
{
  "ai_prompt": "Content generation instructions",
  "domain": "finance|sports|technology",
  "target_audience": "specific audience",
  "session_id": "unique_session_identifier"
}
```

### 4. Workflow Testing
Test the complete workflow:
1. RSS Bloomberg → Content Processor → AI Agent → Response
2. Verify JSON output format
3. Check content quality and SEO optimization
4. Monitor memory persistence across sessions

## Performance Optimization

### Memory Management
- Session keys prevent cross-contamination
- Token limits prevent excessive memory usage
- Domain-specific sessions improve content relevance

### Quality Control
- Confidence scoring ensures output reliability
- Multiple iterations allow for content refinement
- Structured output format enables easy validation

### Scalability Features
- Configurable timeouts prevent workflow blocking
- Dynamic context adaptation supports multiple domains
- Modular tool integration enables feature expansion

## Monitoring and Maintenance

### Key Metrics to Track
- Content generation success rate
- Average processing time
- Memory usage efficiency
- Output quality scores

### Regular Maintenance Tasks
- Monitor memory session cleanup
- Update system prompts based on performance
- Adjust token limits based on usage patterns
- Review and optimize tool integrations

## Troubleshooting Common Issues

### JSON Output Formatting
- Ensure proper JSON validation in system prompt
- Add error handling for malformed responses
- Use output format enforcement in agent settings

### Memory Persistence
- Verify session key uniqueness
- Monitor token limit thresholds
- Clear stale sessions periodically

### Performance Issues
- Adjust timeout settings for complex content
- Optimize system prompt length
- Balance memory limits with context requirements

This configuration provides a robust foundation for automated content generation with n8n AI Agents, supporting scalable, high-quality content production across multiple domains.
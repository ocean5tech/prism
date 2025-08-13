#!/usr/bin/env python3
"""
Simplified Configuration Service for testing n8n workflows
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn
from datetime import datetime

app = FastAPI(title="Configuration Service", version="1.0.0")

# Mock domain configurations
DOMAIN_CONFIGS = {
    "finance": {
        "domain": "finance",
        "style_parameters": {
            "tone": ["professional", "analytical", "authoritative"],
            "complexity": ["intermediate", "advanced"],
            "structure": ["analysis", "news", "opinion"],
            "length": ["medium", "long"],
            "perspective": ["third-person", "expert-analysis"]
        },
        "prompt_template": "finance",
        "quality_thresholds": {
            "minimum_score": 80,
            "readability_min": 70,
            "domain_relevance_min": 85
        },
        "publishing_platforms": ["linkedin", "medium", "wordpress"],
        "content_guidelines": {
            "include_metrics": True,
            "require_sources": True,
            "max_speculation": "low"
        }
    },
    "sports": {
        "domain": "sports",
        "style_parameters": {
            "tone": ["engaging", "conversational", "analytical"],
            "complexity": ["beginner", "intermediate"],
            "structure": ["news", "analysis", "opinion"],
            "length": ["short", "medium"],
            "perspective": ["third-person", "industry-insider"]
        },
        "prompt_template": "sports",
        "quality_thresholds": {
            "minimum_score": 75,
            "engagement_min": 80,
            "readability_min": 75
        },
        "publishing_platforms": ["twitter", "facebook", "wordpress"],
        "content_guidelines": {
            "include_stats": True,
            "emotional_tone": "high",
            "timeliness": "critical"
        }
    },
    "technology": {
        "domain": "technology", 
        "style_parameters": {
            "tone": ["professional", "conversational", "analytical"],
            "complexity": ["intermediate", "advanced"],
            "structure": ["analysis", "tutorial", "news"],
            "length": ["medium", "long"],
            "perspective": ["expert-analysis", "industry-insider"]
        },
        "prompt_template": "technology",
        "quality_thresholds": {
            "minimum_score": 78,
            "accuracy_min": 85,
            "innovation_relevance": 80
        },
        "publishing_platforms": ["medium", "linkedin", "twitter"],
        "content_guidelines": {
            "technical_depth": "high",
            "future_implications": True,
            "code_examples": "optional"
        }
    },
    "general": {
        "domain": "general",
        "style_parameters": {
            "tone": ["conversational", "professional", "engaging"],
            "complexity": ["beginner", "intermediate"],
            "structure": ["news", "analysis", "listicle"],
            "length": ["short", "medium"],
            "perspective": ["third-person"]
        },
        "prompt_template": "default",
        "quality_thresholds": {
            "minimum_score": 70
        },
        "publishing_platforms": ["wordpress", "medium"],
        "content_guidelines": {
            "broad_appeal": True,
            "accessibility": "high"
        }
    }
}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "configuration", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/config/domains/{domain}")
async def get_domain_config(domain: str):
    """Get configuration for a specific domain"""
    if domain not in DOMAIN_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    
    config = DOMAIN_CONFIGS[domain].copy()
    print(f"📋 Retrieved config for domain: {domain}")
    return config

@app.get("/api/v1/config/domains")
async def list_domains():
    """List all available domains"""
    return {
        "domains": list(DOMAIN_CONFIGS.keys()),
        "total": len(DOMAIN_CONFIGS)
    }

@app.post("/api/v1/config/domains/{domain}")
async def update_domain_config(domain: str, config: Dict[str, Any]):
    """Update domain configuration"""
    DOMAIN_CONFIGS[domain] = config
    print(f"✏️ Updated config for domain: {domain}")
    return {"message": f"Domain '{domain}' configuration updated", "domain": domain}

if __name__ == "__main__":
    print("🚀 Starting simplified Configuration Service on port 8013")
    uvicorn.run(app, host="0.0.0.0", port=8013)
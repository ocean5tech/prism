#!/usr/bin/env python3
"""
Simplified Content Generation Service for testing n8n workflows
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import os
import asyncio
from datetime import datetime
import json

app = FastAPI(title="Content Generation Service", version="1.0.0")

# Mock data models
class ContentRequest(BaseModel):
    content_id: str
    domain: str
    prompt: str
    style_parameters: Dict[str, Any]
    source_metadata: Dict[str, Any]

class ContentResponse(BaseModel):
    content_id: str
    success: bool
    generated_content: Optional[str] = None
    word_count: Optional[int] = None
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None

class RegenerateRequest(BaseModel):
    content_id: str
    domain: str
    improvement_instructions: str
    target_quality_score: float
    improvement_strategies: list

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "content-generation", "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/content/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest):
    """Generate content using Claude API (mocked for testing)"""
    try:
        # Simulate content generation delay
        await asyncio.sleep(2)
        
        # Mock generated content based on domain
        domain_templates = {
            "finance": f"Financial Analysis: {request.source_metadata.get('title', 'Market Update')}\n\nThis comprehensive financial analysis examines recent market trends and their implications for investors...",
            "sports": f"Sports Update: {request.source_metadata.get('title', 'Game Report')}\n\nIn an exciting development in the sports world, recent events have shown remarkable performance metrics...",
            "technology": f"Tech Innovation: {request.source_metadata.get('title', 'Tech News')}\n\nThe latest technological advancement represents a significant breakthrough in the industry...",
            "general": f"Analysis: {request.source_metadata.get('title', 'General Content')}\n\nThis detailed analysis provides comprehensive insights into the topic..."
        }
        
        generated_content = domain_templates.get(request.domain, domain_templates["general"])
        
        # Add style variations based on parameters
        style_params = request.style_parameters
        if style_params.get("length") == "long":
            generated_content += "\n\nExtended analysis with additional depth and context provides further understanding of the complex dynamics at play. Multiple factors contribute to this comprehensive overview, including historical precedents, current market conditions, and future projections.\n\nConclusion: The implications of these developments suggest significant opportunities for stakeholders across various sectors."
        
        response = ContentResponse(
            content_id=request.content_id,
            success=True,
            generated_content=generated_content,
            word_count=len(generated_content.split()),
            generation_time_ms=2000
        )
        
        print(f"✅ Generated content for {request.content_id} - Domain: {request.domain}")
        return response
        
    except Exception as e:
        print(f"❌ Error generating content: {str(e)}")
        return ContentResponse(
            content_id=request.content_id,
            success=False,
            error=str(e)
        )

@app.post("/api/v1/content/regenerate")
async def regenerate_content(request: RegenerateRequest):
    """Regenerate content with improvements (mocked for testing)"""
    try:
        await asyncio.sleep(3)
        
        improved_content = f"Improved Content for {request.content_id}\n\nBased on feedback analysis, this enhanced version addresses the identified areas for improvement:\n\n1. Enhanced readability with clearer structure\n2. Improved engagement through compelling examples\n3. Better domain-specific terminology\n4. Optimized content flow and transitions\n\nThe regenerated content now meets higher quality standards and incorporates the adversarial feedback effectively."
        
        return {
            "content_id": request.content_id,
            "success": True,
            "regenerated_content": improved_content,
            "original_quality_score": 65,
            "new_quality_score": 87,
            "improvement_applied": True
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting simplified Content Generation Service on port 8010")
    uvicorn.run(app, host="0.0.0.0", port=8010)
#!/usr/bin/env python3
"""
Simplified Detection Service for testing n8n workflows
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import asyncio
from datetime import datetime
import random

app = FastAPI(title="Detection Service", version="1.0.0")

class DetectionRequest(BaseModel):
    content_id: str
    content: str
    domain: str
    quality_thresholds: Dict[str, Any]

class DetectionResponse(BaseModel):
    content_id: str
    domain: str
    quality_score: float
    feedback: Dict[str, Any]
    analysis_timestamp: str
    detection_agent_version: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "detection", "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/detection/analyze", response_model=DetectionResponse)
async def analyze_content(request: DetectionRequest):
    """Analyze content quality (mocked for testing)"""
    try:
        # Simulate analysis delay
        await asyncio.sleep(1.5)
        
        # Mock quality analysis based on content length and domain
        content_length = len(request.content.split())
        base_score = 60 + (content_length / 10) # Base score based on length
        
        # Domain-specific adjustments
        domain_bonuses = {
            "finance": 10,
            "sports": 8,
            "technology": 12,
            "general": 5
        }
        
        domain_bonus = domain_bonuses.get(request.domain, 5)
        quality_score = min(100, base_score + domain_bonus + random.uniform(-5, 15))
        
        # Generate mock feedback
        feedback = {
            "overall_score": round(quality_score, 2),
            "quality_metrics": {
                "readability": round(quality_score * 0.2, 1),
                "engagement": round(quality_score * 0.25, 1),
                "structure": round(quality_score * 0.2, 1),
                "domain_relevance": round(quality_score * 0.15, 1),
                "uniqueness": round(quality_score * 0.2, 1)
            },
            "detailed_analysis": {
                "readability": {
                    "score": round(quality_score * 0.8 + random.uniform(-10, 10), 1),
                    "avg_words_per_sentence": 15.2,
                    "total_words": content_length
                },
                "engagement": {
                    "score": round(quality_score * 0.9 + random.uniform(-5, 10), 1),
                    "engagement_words_count": 3,
                    "questions": 2,
                    "lists": 1
                },
                "structure": {
                    "score": round(quality_score * 0.85 + random.uniform(-8, 12), 1),
                    "paragraphs": max(1, content_length // 50),
                    "headers": max(0, content_length // 100)
                }
            },
            "suggestions": [
                "Improve sentence structure for better readability",
                f"Add more {request.domain}-specific terminology",
                "Include more engaging examples and actionable insights"
            ] if quality_score < 80 else ["Content meets quality standards"],
            "quality_level": "excellent" if quality_score >= 85 else "good" if quality_score >= 75 else "acceptable" if quality_score >= 60 else "needs_improvement"
        }
        
        response = DetectionResponse(
            content_id=request.content_id,
            domain=request.domain,
            quality_score=round(quality_score, 2),
            feedback=feedback,
            analysis_timestamp=datetime.now().isoformat(),
            detection_agent_version="2.0"
        )
        
        print(f"🕵️ Analyzed content {request.content_id} - Quality: {quality_score:.1f}/100")
        return response
        
    except Exception as e:
        print(f"❌ Error analyzing content: {str(e)}")
        raise

if __name__ == "__main__":
    print("🚀 Starting simplified Detection Service on port 8011")
    uvicorn.run(app, host="0.0.0.0", port=8011)
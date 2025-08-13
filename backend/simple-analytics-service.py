#!/usr/bin/env python3
"""
Simplified Analytics Service for testing n8n workflows
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
from datetime import datetime

app = FastAPI(title="Analytics Service", version="1.0.0")

class EventData(BaseModel):
    event_type: str
    content_id: str
    domain: str
    additional_data: Optional[Dict[str, Any]] = {}

# In-memory storage for demo
events_log = []

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics", "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/analytics/events")
async def log_event(data: Dict[str, Any]):
    """Log analytics events"""
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_data": data
    }
    events_log.append(event)
    print(f"📊 Logged event: {data.get('event_type', 'unknown')} for content {data.get('content_id', 'unknown')}")
    return {"status": "logged", "event_id": len(events_log)}

@app.post("/api/v1/analytics/adversarial-learning")
async def log_adversarial_learning(data: Dict[str, Any]):
    """Log adversarial learning data"""
    learning_event = {
        "timestamp": datetime.now().isoformat(),
        "type": "adversarial_learning",
        "data": data
    }
    events_log.append(learning_event)
    print(f"🧠 Logged adversarial learning data for content {data.get('learning_data', {}).get('content_id', 'unknown')}")
    return {"status": "learning_data_stored"}

@app.post("/api/v1/analytics/optimization-complete")
async def log_optimization_complete(data: Dict[str, Any]):
    """Log optimization completion"""
    optimization_event = {
        "timestamp": datetime.now().isoformat(),
        "type": "optimization_complete",
        "data": data
    }
    events_log.append(optimization_event)
    print(f"✅ Logged optimization completion for content {data.get('content_id', 'unknown')}")
    return {"status": "optimization_logged"}

@app.post("/api/v1/analytics/publishing-success")
async def log_publishing_success(data: Dict[str, Any]):
    """Log successful publishing"""
    publish_event = {
        "timestamp": datetime.now().isoformat(),
        "type": "publishing_success",
        "data": data
    }
    events_log.append(publish_event)
    print(f"📢 Logged publishing success for content {data.get('content_id', 'unknown')} on {data.get('platform', 'unknown')}")
    return {"status": "publishing_logged"}

@app.post("/api/v1/analytics/publishing-failure")
async def log_publishing_failure(data: Dict[str, Any]):
    """Log publishing failure"""
    failure_event = {
        "timestamp": datetime.now().isoformat(),
        "type": "publishing_failure",
        "data": data
    }
    events_log.append(failure_event)
    print(f"❌ Logged publishing failure for content {data.get('content_id', 'unknown')} on {data.get('platform', 'unknown')}")
    return {"status": "failure_logged"}

@app.post("/api/v1/analytics/publishing-batch")
async def log_publishing_batch(data: Dict[str, Any]):
    """Log batch publishing analytics"""
    batch_event = {
        "timestamp": datetime.now().isoformat(),
        "type": "publishing_batch",
        "data": data
    }
    events_log.append(batch_event)
    print(f"📈 Logged batch publishing analytics: {data.get('batch_data', {}).get('batch_metrics', {}).get('total_publications', 0)} publications")
    return {"status": "batch_logged"}

@app.get("/api/v1/analytics/events")
async def get_events(limit: int = 50):
    """Get recent events"""
    return {
        "events": events_log[-limit:],
        "total": len(events_log)
    }

if __name__ == "__main__":
    print("🚀 Starting simplified Analytics Service on port 8015")
    uvicorn.run(app, host="0.0.0.0", port=8015)
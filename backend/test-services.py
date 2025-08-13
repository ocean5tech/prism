#!/usr/bin/env python3
"""Test all microservices functionality"""

import json
import socket
import time

def send_http_request(host, port, method, path, data=None):
    """Send HTTP request using raw socket"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        if data:
            body = json.dumps(data)
            request = f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
        else:
            request = f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        
        sock.send(request.encode())
        response = sock.recv(4096).decode()
        sock.close()
        
        # Extract status code and body
        lines = response.split('\r\n')
        status_line = lines[0]
        
        # Find empty line separating headers from body
        body_start = response.find('\r\n\r\n') + 4
        body = response[body_start:] if body_start > 3 else ""
        
        return status_line, body
    except Exception as e:
        return f"ERROR: {str(e)}", ""

def test_content_generation():
    """Test Content Generation Service"""
    print("=== Testing Content Generation Service (8010) ===")
    
    # Test health
    status, body = send_http_request('localhost', 8010, 'GET', '/health')
    print(f"Health Check: {status}")
    if "200 OK" in status and "healthy" in body:
        print("✅ Health check passed")
    
    # Test content generation
    test_data = {
        "content_id": "test_001",
        "domain": "finance", 
        "prompt": "Write about market trends",
        "style_parameters": {"tone": "professional", "length": "medium"},
        "source_metadata": {"title": "Market Analysis", "description": "Test content"}
    }
    
    status, body = send_http_request('localhost', 8010, 'POST', '/api/v1/content/generate', test_data)
    print(f"Content Generation: {status}")
    
    if "200 OK" in status:
        try:
            result = json.loads(body)
            if result.get('success'):
                print(f"✅ Content generated successfully")
                print(f"   Content ID: {result.get('content_id')}")
                print(f"   Word Count: {result.get('word_count')}")
                content = result.get('generated_content', '')
                print(f"   Content Preview: {content[:100]}...")
                return True
        except:
            pass
    
    print("❌ Content generation failed")
    return False

def test_detection_service():
    """Test Detection Service"""
    print("\n=== Testing Detection Service (8011) ===")
    
    # Test health
    status, body = send_http_request('localhost', 8011, 'GET', '/health')
    print(f"Health Check: {status}")
    if "200 OK" in status and "healthy" in body:
        print("✅ Health check passed")
    
    # Test detection analysis
    test_data = {
        "content_id": "test_002",
        "content": "This is a test article about financial markets. The stock market has been showing interesting trends recently with various sectors performing differently.",
        "domain": "finance",
        "quality_thresholds": {"minimum_score": 75}
    }
    
    status, body = send_http_request('localhost', 8011, 'POST', '/api/v1/detection/analyze', test_data)
    print(f"Quality Analysis: {status}")
    
    if "200 OK" in status:
        try:
            result = json.loads(body)
            quality_score = result.get('quality_score')
            if quality_score is not None:
                print(f"✅ Quality analysis completed")
                print(f"   Quality Score: {quality_score}/100")
                print(f"   Domain: {result.get('domain')}")
                feedback = result.get('feedback', {})
                print(f"   Quality Level: {feedback.get('quality_level', 'unknown')}")
                return True
        except:
            pass
    
    print("❌ Quality analysis failed")
    return False

def test_configuration_service():
    """Test Configuration Service"""
    print("\n=== Testing Configuration Service (8013) ===")
    
    # Test health
    status, body = send_http_request('localhost', 8013, 'GET', '/health')
    print(f"Health Check: {status}")
    if "200 OK" in status and "healthy" in body:
        print("✅ Health check passed")
    
    # Test domain configuration
    status, body = send_http_request('localhost', 8013, 'GET', '/api/v1/config/domains/finance')
    print(f"Domain Config: {status}")
    
    if "200 OK" in status:
        try:
            result = json.loads(body)
            if result.get('domain') == 'finance':
                print(f"✅ Configuration retrieved successfully")
                print(f"   Domain: {result.get('domain')}")
                style_params = result.get('style_parameters', {})
                print(f"   Available tones: {style_params.get('tone', [])}")
                platforms = result.get('publishing_platforms', [])
                print(f"   Publishing platforms: {platforms}")
                return True
        except:
            pass
    
    print("❌ Configuration retrieval failed")
    return False

def test_analytics_service():
    """Test Analytics Service"""
    print("\n=== Testing Analytics Service (8015) ===")
    
    # Test health
    status, body = send_http_request('localhost', 8015, 'GET', '/health')
    print(f"Health Check: {status}")
    if "200 OK" in status and "healthy" in body:
        print("✅ Health check passed")
    
    # Test event logging
    test_data = {
        "event_type": "content_generation_success",
        "content_id": "test_003",
        "domain": "finance",
        "quality_score": 85,
        "word_count": 450
    }
    
    status, body = send_http_request('localhost', 8015, 'POST', '/api/v1/analytics/events', test_data)
    print(f"Event Logging: {status}")
    
    if "200 OK" in status:
        try:
            result = json.loads(body)
            if result.get('status') == 'logged':
                print(f"✅ Event logged successfully")
                print(f"   Event ID: {result.get('event_id')}")
                return True
        except:
            pass
    
    print("❌ Event logging failed")
    return False

if __name__ == "__main__":
    print("🧪 Testing Prism Microservices Functionality")
    print("=" * 50)
    
    results = []
    results.append(test_content_generation())
    results.append(test_detection_service()) 
    results.append(test_configuration_service())
    results.append(test_analytics_service())
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    services = ["Content Generation", "Detection", "Configuration", "Analytics"]
    for i, (service, result) in enumerate(zip(services, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {service} Service: {status}")
    
    total_passed = sum(results)
    print(f"\nOverall: {total_passed}/4 services working correctly")
    
    if total_passed == 4:
        print("🎉 ALL MICROSERVICES ARE WORKING CORRECTLY!")
        print("Ready for n8n workflow testing!")
    else:
        print("⚠️  Some services need attention")
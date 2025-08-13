#!/usr/bin/env python3
"""
N8N-Ready Endpoints Validation Script
Tests only existing endpoints and provides readiness assessment for n8n workflows
"""

import requests
import json
import os
from datetime import datetime

class N8NReadinessValidator:
    def __init__(self):
        # Bypass proxy for localhost
        os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
        self.session = requests.Session()
        self.session.proxies = {'http': None, 'https': None}
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'rss_feeds': {},
            'workflow_readiness': {},
            'summary': {
                'services_healthy': 0,
                'total_services': 4,
                'ready_workflows': [],
                'blocked_workflows': [],
                'next_steps': []
            }
        }
        
    def test_service_health(self, port, service_name):
        """Test service health and basic functionality"""
        result = {
            'service_name': service_name,
            'port': port,
            'healthy': False,
            'endpoints_tested': [],
            'working_endpoints': [],
            'issues': []
        }
        
        try:
            # Health check
            health_response = self.session.get(f'http://localhost:{port}/health', timeout=5)
            if health_response.status_code == 200:
                result['healthy'] = True
                result['health_data'] = health_response.json()
                result['working_endpoints'].append('/health')
                print(f"  ✅ Health check passed")
            
            # Test known working endpoints
            if port == 8010:  # Content Generation Service
                endpoints_to_test = [
                    ('/openapi.json', 'GET', None),
                ]
                
                for endpoint, method, test_data in endpoints_to_test:
                    try:
                        if method == 'GET':
                            resp = self.session.get(f'http://localhost:{port}{endpoint}', timeout=5)
                        else:
                            resp = self.session.post(f'http://localhost:{port}{endpoint}', 
                                                   json=test_data, timeout=5)
                        
                        result['endpoints_tested'].append(endpoint)
                        if resp.status_code < 400:
                            result['working_endpoints'].append(endpoint)
                            print(f"  ✅ {endpoint} - {resp.status_code}")
                        else:
                            print(f"  ❌ {endpoint} - {resp.status_code}")
                            result['issues'].append(f"{endpoint}: HTTP {resp.status_code}")
                            
                    except Exception as e:
                        result['issues'].append(f"{endpoint}: {str(e)[:50]}")
                        print(f"  ❌ {endpoint} - Error: {str(e)[:50]}")
                        
                # Get available endpoints from OpenAPI
                try:
                    openapi_resp = self.session.get(f'http://localhost:{port}/openapi.json')
                    if openapi_resp.status_code == 200:
                        openapi_data = openapi_resp.json()
                        available_paths = list(openapi_data.get('paths', {}).keys())
                        result['available_endpoints'] = available_paths
                        print(f"  📋 Available endpoints: {len(available_paths)}")
                        for path in available_paths:
                            print(f"     • {path}")
                except Exception as e:
                    result['issues'].append(f"OpenAPI fetch failed: {str(e)}")
                    
        except Exception as e:
            result['issues'].append(f"Service test failed: {str(e)}")
            print(f"  ❌ Service unreachable: {str(e)}")
            
        return result
    
    def test_rss_feeds(self):
        """Test RSS feeds used in workflows"""
        feeds_to_test = [
            ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg Markets'),
            ('https://feeds.reuters.com/reuters/topNews', 'Reuters Top News'),
        ]
        
        print("\n📡 Testing RSS Feeds...")
        
        for feed_url, feed_name in feeds_to_test:
            result = {
                'name': feed_name,
                'url': feed_url,
                'accessible': False,
                'items': 0,
                'title': '',
                'error': None
            }
            
            try:
                print(f"  Testing {feed_name}...")
                response = requests.get(feed_url, timeout=10)
                
                if response.status_code == 200:
                    result['accessible'] = True
                    content = response.text
                    
                    # Extract title
                    import re
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        title = title_match.group(1).strip()
                        title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title)
                        result['title'] = title
                    
                    # Count items
                    item_count = len(re.findall(r'<item[^>]*>', content.lower()))
                    if item_count == 0:
                        item_count = len(re.findall(r'<entry[^>]*>', content.lower()))
                    result['items'] = item_count
                    
                    print(f"    ✅ {feed_name}: {item_count} items")
                else:
                    result['error'] = f"HTTP {response.status_code}"
                    print(f"    ❌ {feed_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                result['error'] = str(e)
                if 'proxy' in str(e).lower():
                    print(f"    ❌ {feed_name}: Proxy blocked")
                else:
                    print(f"    ❌ {feed_name}: {str(e)[:50]}")
            
            self.results['rss_feeds'][feed_name] = result
    
    def assess_workflow_readiness(self):
        """Assess which workflows can actually run with current services"""
        
        print("\n📋 Assessing Workflow Readiness...")
        
        # Check what we have available
        content_service = self.results['services'].get(8010, {})
        detection_service = self.results['services'].get(8011, {})
        config_service = self.results['services'].get(8013, {})
        analytics_service = self.results['services'].get(8015, {})
        
        content_endpoints = content_service.get('available_endpoints', [])
        bloomberg_working = self.results['rss_feeds'].get('Bloomberg Markets', {}).get('accessible', False)
        
        workflows = {
            '01-main-content-generation-pipeline-FIXED': {
                'required_endpoints': [
                    '/api/v1/content/generate',
                    '/api/v1/detection/analyze', 
                    '/api/v1/config/domains/',
                    '/api/v1/analytics/events'
                ],
                'required_rss': ['Bloomberg Markets'],
                'description': 'Main content generation with RSS monitoring'
            },
            '02-adversarial-quality-optimization-FIXED': {
                'required_endpoints': [
                    '/api/v1/content/regenerate',
                    '/api/v1/analytics/adversarial-learning'
                ],
                'required_rss': [],
                'description': 'Content quality improvement through adversarial feedback'
            },
            '03-multi-platform-publishing-FIXED': {
                'required_endpoints': [
                    '/api/v1/publishing/wordpress',
                    '/api/v1/publishing/medium',
                    '/api/v1/analytics/publishing-success'
                ],
                'required_rss': [],
                'description': 'Multi-platform content publishing'
            }
        }
        
        for workflow_name, requirements in workflows.items():
            print(f"\n  🔍 {workflow_name}:")
            
            result = {
                'description': requirements['description'],
                'status': 'unknown',
                'available_endpoints': [],
                'missing_endpoints': [],
                'rss_status': 'ok',
                'readiness_score': 0,
                'can_test': False,
                'limitations': []
            }
            
            # Check endpoints
            total_endpoints = len(requirements['required_endpoints'])
            available_count = 0
            
            for endpoint in requirements['required_endpoints']:
                # Check if endpoint exists in any service
                endpoint_available = False
                
                if endpoint in content_endpoints:
                    endpoint_available = True
                    result['available_endpoints'].append(endpoint)
                elif endpoint == '/api/v1/config/domains/' and config_service.get('healthy'):
                    # Config service is healthy but endpoint not implemented
                    result['missing_endpoints'].append(endpoint)
                elif endpoint == '/api/v1/detection/analyze' and detection_service.get('healthy'):
                    # Detection service is healthy but endpoint not implemented
                    result['missing_endpoints'].append(endpoint)
                elif endpoint.startswith('/api/v1/analytics/') and analytics_service.get('healthy'):
                    # Analytics service is healthy but endpoint not implemented
                    result['missing_endpoints'].append(endpoint)
                elif endpoint.startswith('/api/v1/publishing/') and content_service.get('healthy'):
                    # Publishing endpoints expected in content service but not implemented
                    result['missing_endpoints'].append(endpoint)
                else:
                    result['missing_endpoints'].append(endpoint)
                
                if endpoint_available:
                    available_count += 1
                    print(f"    ✅ {endpoint}")
                else:
                    print(f"    ❌ {endpoint}")
            
            # Check RSS feeds
            for rss_name in requirements['required_rss']:
                rss_working = self.results['rss_feeds'].get(rss_name, {}).get('accessible', False)
                if not rss_working:
                    result['rss_status'] = 'blocked'
                    result['limitations'].append(f"RSS feed {rss_name} not accessible")
            
            # Calculate readiness
            result['readiness_score'] = (available_count / total_endpoints * 100) if total_endpoints > 0 else 0
            
            if result['readiness_score'] >= 80:
                result['status'] = 'ready'
                result['can_test'] = True
                self.results['summary']['ready_workflows'].append(workflow_name)
            elif result['readiness_score'] >= 40:
                result['status'] = 'partial'
                result['can_test'] = True
                result['limitations'].append("Limited functionality - some features won't work")
            else:
                result['status'] = 'blocked'
                result['can_test'] = False
                self.results['summary']['blocked_workflows'].append(workflow_name)
            
            print(f"    📊 Readiness: {result['readiness_score']:.0f}% - {result['status'].upper()}")
            
            self.results['workflow_readiness'][workflow_name] = result
    
    def generate_next_steps(self):
        """Generate prioritized next steps"""
        steps = []
        
        # Check service health
        healthy_services = sum(1 for s in self.results['services'].values() if s.get('healthy', False))
        if healthy_services < 4:
            steps.append("🚨 HIGH: Fix unhealthy services")
        
        # Check for blocked RSS
        blocked_rss = [name for name, data in self.results['rss_feeds'].items() 
                      if not data.get('accessible', False)]
        if blocked_rss:
            steps.append(f"⚠️ MEDIUM: Fix RSS access for {', '.join(blocked_rss)}")
        
        # Check for missing critical endpoints
        critical_missing = []
        for workflow_name, data in self.results['workflow_readiness'].items():
            if data.get('status') == 'blocked':
                missing = data.get('missing_endpoints', [])
                critical_missing.extend(missing[:2])  # Top 2 missing endpoints
        
        if critical_missing:
            unique_missing = list(set(critical_missing))
            steps.append(f"ℹ️ LOW: Implement missing endpoints: {', '.join(unique_missing[:3])}")
        
        # Add positive steps if things are working
        ready_workflows = self.results['summary']['ready_workflows']
        partial_workflows = [name for name, data in self.results['workflow_readiness'].items() 
                           if data.get('status') == 'partial']
        
        if ready_workflows:
            steps.append(f"✅ READY: Test workflows: {', '.join(ready_workflows)}")
        elif partial_workflows:
            steps.append(f"✅ TEST: Partial workflows available: {', '.join(partial_workflows[:2])}")
        
        self.results['summary']['next_steps'] = steps
    
    def run_validation(self):
        """Run complete validation"""
        print("🔍 N8N Workflow Readiness Validation")
        print("=" * 50)
        
        # Test all services
        services = [
            (8010, "Content Generation Service"),
            (8011, "Detection/Quality Analysis Service"),
            (8013, "Configuration Management Service"),
            (8015, "Analytics Service")
        ]
        
        print("\n🚀 Testing Microservices...")
        for port, name in services:
            print(f"\n{name} (Port {port}):")
            result = self.test_service_health(port, name)
            self.results['services'][port] = result
            
            if result['healthy']:
                self.results['summary']['services_healthy'] += 1
        
        # Test RSS feeds
        self.test_rss_feeds()
        
        # Assess workflow readiness
        self.assess_workflow_readiness()
        
        # Generate next steps
        self.generate_next_steps()
        
        return self.results
    
    def print_summary(self):
        """Print validation summary"""
        summary = self.results['summary']
        
        print(f"\n{'=' * 60}")
        print("📋 VALIDATION SUMMARY")
        print(f"{'=' * 60}")
        
        print(f"\n🚀 Service Health: {summary['services_healthy']}/{summary['total_services']} services healthy")
        
        rss_working = sum(1 for r in self.results['rss_feeds'].values() if r.get('accessible', False))
        rss_total = len(self.results['rss_feeds'])
        print(f"📡 RSS Feeds: {rss_working}/{rss_total} feeds accessible")
        
        print(f"\n📋 Workflow Readiness:")
        for name, data in self.results['workflow_readiness'].items():
            status_icon = {"ready": "✅", "partial": "⚠️", "blocked": "❌"}.get(data['status'], "❓")
            score = data['readiness_score']
            print(f"  {status_icon} {name}: {score:.0f}% ready")
        
        print(f"\n🎯 Next Steps:")
        for i, step in enumerate(summary['next_steps'], 1):
            print(f"  {i}. {step}")
        
        # Key insights
        print(f"\n💡 Key Insights:")
        if summary['services_healthy'] == summary['total_services']:
            print("  ✅ All microservices are running and healthy")
        
        working_endpoints = []
        for service_data in self.results['services'].values():
            working_endpoints.extend(service_data.get('working_endpoints', []))
        
        print(f"  📊 {len(working_endpoints)} endpoints currently working")
        
        if summary['ready_workflows']:
            print(f"  🚀 {len(summary['ready_workflows'])} workflows ready for testing")
        elif any(data.get('status') == 'partial' for data in self.results['workflow_readiness'].values()):
            print("  ⚠️  Workflows can be partially tested with current setup")
        else:
            print("  ❌ No workflows are currently ready for full testing")
        
        print(f"\n{'=' * 60}")


def main():
    validator = N8NReadinessValidator()
    results = validator.run_validation()
    validator.print_summary()
    
    # Save results
    with open('/home/wyatt/dev-projects/Prism/n8n-readiness-validation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: n8n-readiness-validation.json")

if __name__ == "__main__":
    main()
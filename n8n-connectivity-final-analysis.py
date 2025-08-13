#!/usr/bin/env python3
"""
N8N Workflow Connectivity Analysis Script - Final Version
Comprehensive analysis with proxy handling and detailed service validation
"""

import json
import re
import requests
import time
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse
import socket
from datetime import datetime
import os

class N8NConnectivityAnalyzer:
    def __init__(self):
        self.workflow_dir = "/home/wyatt/dev-projects/Prism/n8n-workflows"
        
        # Configure requests session without proxy for localhost
        self.session = requests.Session()
        self.session.proxies = {
            'http': None,
            'https': None
        }
        
        # Set no proxy environment
        os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
        
        self.results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'workflows_analyzed': [],
            'url_tests': {},
            'service_tests': {},
            'rss_feed_tests': {},
            'endpoint_validation': {},
            'summary': {
                'total_urls': 0,
                'available_urls': 0,
                'total_services': 0,
                'available_services': 0,
                'working_endpoints': 0,
                'total_endpoints': 0,
                'critical_issues': [],
                'recommendations': [],
                'proxy_issues_detected': False
            }
        }
        
        # Expected microservice ports and their purposes
        self.expected_services = {
            8010: "Content Generation Service",
            8011: "Detection/Quality Analysis Service", 
            8013: "Configuration Management Service",
            8015: "Analytics Service"
        }
        
        # Expected API endpoints for each service
        self.service_endpoints = {
            8010: [
                "/health",
                "/api/v1/content/generate",
                "/api/v1/content/regenerate",
                "/api/v1/publishing/queue",
                "/api/v1/publishing/wordpress",
                "/api/v1/publishing/medium",
                "/api/v1/publishing/linkedin", 
                "/api/v1/publishing/twitter"
            ],
            8011: [
                "/health",
                "/api/v1/detection/analyze"
            ],
            8013: [
                "/health",
                "/api/v1/config/domains/finance",
                "/api/v1/config/domains/sports",
                "/api/v1/config/domains/technology"
            ],
            8015: [
                "/health",
                "/api/v1/analytics/events",
                "/api/v1/analytics/adversarial-learning",
                "/api/v1/analytics/optimization-complete",
                "/api/v1/analytics/publishing-success",
                "/api/v1/analytics/publishing-failure",
                "/api/v1/analytics/publishing-batch"
            ]
        }
        
    def extract_urls_from_workflow(self, workflow_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract all URLs from workflow nodes"""
        urls = []
        nodes = workflow_data.get('nodes', [])
        
        for node in nodes:
            node_name = node.get('name', 'Unknown')
            node_type = node.get('type', 'Unknown')
            parameters = node.get('parameters', {})
            
            # HTTP Request node URLs
            if 'url' in parameters:
                url = parameters['url']
                # Skip n8n template variables for now
                if not url.startswith('={{') and not url.startswith('{{ '):
                    urls.append({
                        'url': url,
                        'node_name': node_name,
                        'node_type': node_type,
                        'node_id': node.get('id', ''),
                        'purpose': 'HTTP Request'
                    })
            
            # RSS Feed URLs
            if 'feedUrl' in parameters:
                feed_url = parameters['feedUrl']
                if not feed_url.startswith('={{') and not feed_url.startswith('{{ '):
                    urls.append({
                        'url': feed_url,
                        'node_name': node_name,
                        'node_type': node_type,
                        'node_id': node.get('id', ''),
                        'purpose': 'RSS Feed'
                    })
            
            # Webhook endpoints
            if node_type == 'n8n-nodes-base.webhook' and 'path' in parameters:
                webhook_path = parameters['path']
                urls.append({
                    'url': f"webhook/{webhook_path}",
                    'node_name': node_name,
                    'node_type': node_type,
                    'node_id': node.get('id', ''),
                    'purpose': 'Webhook Endpoint'
                })
                
        return urls
    
    def test_url_connectivity(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Test URL connectivity and response"""
        result = {
            'url': url,
            'status': 'unknown',
            'status_code': None,
            'response_time': None,
            'error': None,
            'accessible': False,
            'proxy_bypassed': False
        }
        
        try:
            # Skip webhook URLs as they're internal n8n endpoints
            if url.startswith('webhook/'):
                result.update({
                    'status': 'webhook_endpoint',
                    'accessible': True,
                    'note': 'Internal n8n webhook endpoint - not externally testable'
                })
                return result
            
            start_time = time.time()
            
            # Use session without proxy for localhost URLs
            if 'localhost' in url or '127.0.0.1' in url:
                result['proxy_bypassed'] = True
                response = self.session.head(url, timeout=timeout, allow_redirects=True)
            else:
                response = requests.head(url, timeout=timeout, allow_redirects=True)
                
            response_time = time.time() - start_time
            
            result.update({
                'status': 'success',
                'status_code': response.status_code,
                'response_time': round(response_time, 3),
                'accessible': response.status_code < 400
            })
            
            if response.status_code >= 400:
                result['status'] = 'http_error'
                result['error'] = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            result.update({
                'status': 'timeout',
                'error': 'Request timed out',
                'accessible': False
            })
        except requests.exceptions.ConnectionError as e:
            if 'proxy' in str(e).lower():
                self.results['summary']['proxy_issues_detected'] = True
                result['error'] = f'Proxy connection error: {str(e)[:100]}...'
            else:
                result['error'] = f'Connection failed: {str(e)[:100]}...'
            result.update({
                'status': 'connection_error',
                'accessible': False
            })
        except Exception as e:
            result.update({
                'status': 'error',
                'error': str(e)[:100] + ('...' if len(str(e)) > 100 else ''),
                'accessible': False
            })
            
        return result
    
    def test_service_endpoint(self, host: str, port: int, endpoint: str) -> Dict[str, Any]:
        """Test specific service endpoint"""
        url = f"http://{host}:{port}{endpoint}"
        result = {
            'url': url,
            'endpoint': endpoint,
            'accessible': False,
            'status': 'unknown',
            'error': None,
            'response_data': None
        }
        
        try:
            response = self.session.get(url, timeout=5)
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result.update({
                    'accessible': True,
                    'status': 'success'
                })
                
                # Try to parse JSON response for health endpoints
                if endpoint == '/health':
                    try:
                        result['response_data'] = response.json()
                    except:
                        result['response_data'] = response.text[:200]
                        
            elif response.status_code == 404:
                result.update({
                    'status': 'endpoint_not_found',
                    'error': 'Endpoint not implemented'
                })
            elif response.status_code == 405:
                result.update({
                    'status': 'method_not_allowed',
                    'accessible': True,  # Endpoint exists but wrong method
                    'error': 'Method not allowed (endpoint exists)'
                })
            else:
                result.update({
                    'status': 'http_error',
                    'error': f'HTTP {response.status_code}'
                })
                
        except Exception as e:
            result.update({
                'status': 'connection_error',
                'error': str(e)[:100]
            })
            
        return result
    
    def test_service_connectivity(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Test service connectivity and validate endpoints"""
        result = {
            'host': host,
            'port': port,
            'service_name': self.expected_services.get(port, f"Service on port {port}"),
            'accessible': False,
            'status': 'unknown',
            'error': None,
            'response_time': None,
            'endpoints': {},
            'working_endpoints': 0,
            'total_endpoints': 0
        }
        
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            connection_result = sock.connect_ex((host, port))
            response_time = time.time() - start_time
            sock.close()
            
            if connection_result == 0:
                result.update({
                    'accessible': True,
                    'status': 'port_open',
                    'response_time': round(response_time, 3)
                })
                
                # Test specific endpoints for this service
                expected_endpoints = self.service_endpoints.get(port, [])
                result['total_endpoints'] = len(expected_endpoints)
                
                for endpoint in expected_endpoints:
                    endpoint_result = self.test_service_endpoint(host, port, endpoint)
                    result['endpoints'][endpoint] = endpoint_result
                    
                    if endpoint_result['accessible']:
                        result['working_endpoints'] += 1
                        
                # Update overall service status
                if result['working_endpoints'] > 0:
                    result['status'] = 'service_responsive'
                    if result['working_endpoints'] == result['total_endpoints']:
                        result['status'] = 'service_fully_functional'
                        
            else:
                result.update({
                    'status': 'port_closed',
                    'error': f'Connection failed (error code: {connection_result})'
                })
                
        except socket.timeout:
            result.update({
                'status': 'timeout',
                'error': 'Connection timeout'
            })
        except Exception as e:
            result.update({
                'status': 'error',
                'error': str(e)
            })
            
        return result
    
    def test_rss_feed(self, feed_url: str) -> Dict[str, Any]:
        """Specifically test RSS feed accessibility and validity"""
        result = {
            'url': feed_url,
            'accessible': False,
            'valid_rss': False,
            'status': 'unknown',
            'error': None,
            'feed_info': {}
        }
        
        try:
            # Use appropriate session based on URL
            if 'localhost' in feed_url or '127.0.0.1' in feed_url:
                response = self.session.get(feed_url, timeout=10)
            else:
                response = requests.get(feed_url, timeout=10)
                
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['accessible'] = True
                result['status'] = 'accessible'
                
                # Basic RSS validation
                content = response.text.lower()
                if any(tag in content for tag in ['<rss', '<feed', '<channel']):
                    result['valid_rss'] = True
                    result['status'] = 'valid_rss'
                    
                    # Extract feed info
                    if '<title>' in content:
                        title_match = re.search(r'<title[^>]*>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            title = title_match.group(1).strip()
                            # Clean up CDATA
                            title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title)
                            result['feed_info']['title'] = title[:100]
                            
                    # Count items
                    item_count = len(re.findall(r'<item[^>]*>', content))
                    if item_count == 0:
                        item_count = len(re.findall(r'<entry[^>]*>', content))  # Atom feeds
                    result['feed_info']['item_count'] = item_count
                else:
                    result['status'] = 'not_rss'
                    result['error'] = 'Response does not appear to be RSS/Atom feed'
            else:
                result['status'] = 'http_error'
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['status'] = 'error'
            if 'proxy' in str(e).lower():
                self.results['summary']['proxy_issues_detected'] = True
                result['error'] = f'Proxy error: {str(e)[:100]}...'
            else:
                result['error'] = str(e)[:100] + ('...' if len(str(e)) > 100 else '')
            
        return result
    
    def analyze_workflow_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a single workflow file"""
        workflow_result = {
            'filepath': filepath,
            'workflow_name': '',
            'workflow_type': self.classify_workflow_type(filepath),
            'urls_found': [],
            'url_test_results': {},
            'issues': [],
            'status': 'unknown'
        }
        
        try:
            with open(filepath, 'r') as f:
                workflow_data = json.load(f)
            
            workflow_result['workflow_name'] = workflow_data.get('name', 'Unknown')
            
            # Extract URLs
            urls = self.extract_urls_from_workflow(workflow_data)
            workflow_result['urls_found'] = urls
            
            working_urls = 0
            
            # Test each URL
            for url_info in urls:
                url = url_info['url']
                print(f"  Testing: {url}")
                
                if url_info['purpose'] == 'RSS Feed':
                    test_result = self.test_rss_feed(url)
                    self.results['rss_feed_tests'][url] = test_result
                else:
                    test_result = self.test_url_connectivity(url)
                    self.results['url_tests'][url] = test_result
                
                workflow_result['url_test_results'][url] = test_result
                
                if test_result.get('accessible', False):
                    working_urls += 1
                else:
                    # Track issues
                    issue = f"URL not accessible: {url} ({test_result.get('error', 'Unknown error')})"
                    workflow_result['issues'].append(issue)
                    
                    if url.startswith('http://localhost'):
                        self.results['summary']['critical_issues'].append(
                            f"Microservice endpoint unavailable: {url}"
                        )
                        
            # Determine workflow status
            total_urls = len(urls)
            if total_urls == 0:
                workflow_result['status'] = 'no_urls'
            elif working_urls == total_urls:
                workflow_result['status'] = 'fully_functional'
            elif working_urls > 0:
                workflow_result['status'] = 'partially_functional'
            else:
                workflow_result['status'] = 'non_functional'
                
        except Exception as e:
            workflow_result['issues'].append(f"Failed to analyze workflow: {str(e)}")
            workflow_result['status'] = 'analysis_failed'
            
        return workflow_result
    
    def classify_workflow_type(self, filepath: str) -> str:
        """Classify workflow based on filename"""
        filename = os.path.basename(filepath).lower()
        
        if 'fixed' in filename:
            return 'fixed_version'
        elif 'testing' in filename:
            return 'testing_version'
        elif 'content-generation' in filename or '01-' in filename:
            return 'content_generation'
        elif 'adversarial' in filename or '02-' in filename:
            return 'quality_optimization'
        elif 'publishing' in filename or '03-' in filename:
            return 'publishing'
        elif 'monitoring' in filename or '05-' in filename:
            return 'monitoring'
        elif 'rss' in filename:
            return 'rss_testing'
        else:
            return 'other'
    
    def test_microservices(self):
        """Test all expected microservice endpoints"""
        print("Testing microservice connectivity...")
        
        total_endpoints = 0
        working_endpoints = 0
        
        for port, service_name in self.expected_services.items():
            print(f"  Testing {service_name} on port {port}")
            result = self.test_service_connectivity('localhost', port)
            self.results['service_tests'][port] = result
            
            total_endpoints += result['total_endpoints']
            working_endpoints += result['working_endpoints']
            
            if result['accessible']:
                self.results['summary']['available_services'] += 1
            else:
                self.results['summary']['critical_issues'].append(
                    f"{service_name} (port {port}) is not accessible"
                )
                
        self.results['summary']['total_services'] = len(self.expected_services)
        self.results['summary']['total_endpoints'] = total_endpoints
        self.results['summary']['working_endpoints'] = working_endpoints
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis results"""
        recommendations = []
        
        # Proxy recommendations
        if self.results['summary']['proxy_issues_detected']:
            recommendations.append("Configure NO_PROXY environment variable: export NO_PROXY=localhost,127.0.0.1")
            recommendations.append("Consider updating proxy settings to allow localhost connections")
        
        # Service recommendations
        unavailable_services = []
        partial_services = []
        
        for port, result in self.results['service_tests'].items():
            if not result.get('accessible', False):
                unavailable_services.append(f"Port {port} ({result['service_name']})")
            elif result['working_endpoints'] < result['total_endpoints']:
                partial_services.append(f"Port {port} ({result['working_endpoints']}/{result['total_endpoints']} endpoints working)")
        
        if unavailable_services:
            recommendations.append(f"Start missing services: {', '.join(unavailable_services)}")
            recommendations.append("Run: cd backend && ./start-simple-services.sh")
        
        if partial_services:
            recommendations.append(f"Services with missing endpoints: {', '.join(partial_services)}")
            recommendations.append("Check service implementation for missing API endpoints")
        
        # RSS Feed recommendations
        failed_rss = [url for url, result in self.results['rss_feed_tests'].items() 
                     if not result.get('accessible', False)]
        if failed_rss:
            recommendations.append(f"Fix RSS feed connectivity: {', '.join(failed_rss[:2])}{'...' if len(failed_rss) > 2 else ''}")
        
        # Workflow recommendations
        workflow_status = {}
        for workflow in self.results['workflows_analyzed']:
            status = workflow['status']
            workflow_type = workflow['workflow_type']
            if status not in workflow_status:
                workflow_status[status] = []
            workflow_status[status].append(f"{workflow_type}")
        
        if 'non_functional' in workflow_status:
            recommendations.append(f"Fix non-functional workflows: {', '.join(workflow_status['non_functional'][:3])}")
        
        if 'fixed_version' in [w['workflow_type'] for w in self.results['workflows_analyzed']]:
            recommendations.append("Prioritize testing FIXED workflow versions as they contain the latest improvements")
        
        self.results['summary']['recommendations'] = recommendations
    
    def run_analysis(self):
        """Run complete connectivity analysis"""
        print("N8N Workflow Connectivity Analysis - Final Version")
        print("="*60)
        
        # Find all workflow files
        workflow_files = []
        for filename in os.listdir(self.workflow_dir):
            if filename.endswith('.json') and not filename.startswith('.'):
                workflow_files.append(os.path.join(self.workflow_dir, filename))
        
        print(f"Found {len(workflow_files)} workflow files to analyze")
        
        # Prioritize FIXED workflows
        fixed_files = [f for f in workflow_files if 'FIXED' in f]
        other_files = [f for f in workflow_files if 'FIXED' not in f]
        workflow_files = fixed_files + other_files
        
        # Test microservices first
        self.test_microservices()
        
        print(f"\nAnalyzing workflows (FIXED versions prioritized)...")
        # Analyze each workflow
        for filepath in workflow_files:
            filename = os.path.basename(filepath)
            print(f"\n🔍 Analyzing: {filename}")
            workflow_result = self.analyze_workflow_file(filepath)
            self.results['workflows_analyzed'].append(workflow_result)
        
        # Calculate summary statistics
        all_urls = set()
        accessible_urls = set()
        
        for workflow in self.results['workflows_analyzed']:
            for url, result in workflow['url_test_results'].items():
                all_urls.add(url)
                if result.get('accessible', False):
                    accessible_urls.add(url)
        
        self.results['summary']['total_urls'] = len(all_urls)
        self.results['summary']['available_urls'] = len(accessible_urls)
        
        # Generate recommendations
        self.generate_recommendations()
        
        return self.results
    
    def save_results(self, output_file: str):
        """Save analysis results to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📊 Detailed results saved to: {output_file}")
    
    def print_summary_report(self):
        """Print a comprehensive summary report"""
        summary = self.results['summary']
        
        print(f"\n{'='*70}")
        print("🔍 N8N WORKFLOW CONNECTIVITY ANALYSIS REPORT")
        print(f"{'='*70}")
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   • Workflows analyzed: {len(self.results['workflows_analyzed'])}")
        print(f"   • Total URLs tested: {summary['total_urls']}")
        print(f"   • Available URLs: {summary['available_urls']}")
        print(f"   • URL success rate: {(summary['available_urls']/summary['total_urls']*100) if summary['total_urls'] > 0 else 0:.1f}%")
        
        print(f"\n🔧 MICROSERVICE STATUS:")
        print(f"   • Total services: {summary['total_services']}")
        print(f"   • Available services: {summary['available_services']}")
        print(f"   • Service availability: {(summary['available_services']/summary['total_services']*100) if summary['total_services'] > 0 else 0:.1f}%")
        print(f"   • Working endpoints: {summary['working_endpoints']}/{summary['total_endpoints']}")
        print(f"   • Endpoint success rate: {(summary['working_endpoints']/summary['total_endpoints']*100) if summary['total_endpoints'] > 0 else 0:.1f}%")
        
        # Service details
        print(f"\n🚀 SERVICE DETAILS:")
        for port, result in self.results['service_tests'].items():
            status_icon = "✅" if result['accessible'] else "❌"
            service_name = result['service_name']
            endpoint_status = f"{result['working_endpoints']}/{result['total_endpoints']}"
            
            print(f"   {status_icon} {service_name} (:{port}) - {endpoint_status} endpoints")
            
            if result['accessible'] and result.get('endpoints'):
                for endpoint, ep_result in result['endpoints'].items():
                    ep_icon = "✅" if ep_result['accessible'] else "❌" if ep_result['status'] == 'endpoint_not_found' else "⚠️"
                    print(f"      {ep_icon} {endpoint}")
        
        # Workflow analysis by type
        print(f"\n📋 WORKFLOW STATUS BY TYPE:")
        workflow_types = {}
        for workflow in self.results['workflows_analyzed']:
            wf_type = workflow['workflow_type']
            wf_status = workflow['status']
            
            if wf_type not in workflow_types:
                workflow_types[wf_type] = {}
            if wf_status not in workflow_types[wf_type]:
                workflow_types[wf_type][wf_status] = 0
            workflow_types[wf_type][wf_status] += 1
        
        for wf_type, statuses in workflow_types.items():
            print(f"   📄 {wf_type.replace('_', ' ').title()}:")
            for status, count in statuses.items():
                status_icon = {"fully_functional": "✅", "partially_functional": "⚠️", "non_functional": "❌", "no_urls": "ℹ️"}.get(status, "❓")
                print(f"      {status_icon} {status.replace('_', ' ').title()}: {count}")
        
        # RSS Feed Analysis
        if self.results['rss_feed_tests']:
            print(f"\n📡 RSS FEED ANALYSIS:")
            for url, result in self.results['rss_feed_tests'].items():
                status_icon = "✅" if result.get('accessible', False) else "❌"
                feed_name = urlparse(url).netloc
                print(f"   {status_icon} {feed_name}")
                
                if result.get('accessible', False) and result.get('feed_info'):
                    info = result['feed_info']
                    title = info.get('title', 'Unknown')[:50] + ('...' if len(info.get('title', '')) > 50 else '')
                    items = info.get('item_count', 0)
                    print(f"      📰 {title}")
                    print(f"      📄 {items} items available")
                elif not result.get('accessible', False):
                    error = result.get('error', 'Unknown error')[:60]
                    print(f"      ❌ {error}")
        
        # Critical Issues
        if summary['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES ({len(summary['critical_issues'])}):")
            # Group issues by type
            service_issues = [issue for issue in summary['critical_issues'] if 'Service' in issue and 'not accessible' in issue]
            endpoint_issues = [issue for issue in summary['critical_issues'] if 'endpoint unavailable' in issue]
            
            if service_issues:
                print(f"   🔧 Service Availability Issues:")
                for issue in service_issues[:3]:
                    print(f"      • {issue}")
            
            if endpoint_issues:
                print(f"   🌐 Endpoint Connectivity Issues:")
                for issue in endpoint_issues[:5]:
                    print(f"      • {issue}")
                if len(endpoint_issues) > 5:
                    print(f"      • ... and {len(endpoint_issues) - 5} more endpoint issues")
        
        # Recommendations
        if summary['recommendations']:
            print(f"\n✅ RECOMMENDATIONS ({len(summary['recommendations'])}):")
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # Priority Actions
        print(f"\n🎯 PRIORITY ACTIONS:")
        
        if summary['available_services'] < summary['total_services']:
            print(f"   🚨 HIGH: Start missing microservices")
            print(f"       Command: cd backend && ./start-simple-services.sh")
        
        if summary['proxy_issues_detected']:
            print(f"   ⚠️  MEDIUM: Fix proxy configuration for localhost")
            print(f"       Command: export NO_PROXY=localhost,127.0.0.1")
        
        if summary['working_endpoints'] < summary['total_endpoints']:
            print(f"   ℹ️  LOW: Implement missing API endpoints in services")
        
        fixed_workflows = [w for w in self.results['workflows_analyzed'] if w['workflow_type'] == 'fixed_version']
        if fixed_workflows:
            functional_fixed = [w for w in fixed_workflows if w['status'] == 'fully_functional']
            print(f"   ✅ READY: {len(functional_fixed)}/{len(fixed_workflows)} FIXED workflows are fully functional")
        
        print(f"\n{'='*70}")
        print(f"📅 Analysis completed: {self.results['analysis_timestamp']}")
        print(f"{'='*70}")


def main():
    analyzer = N8NConnectivityAnalyzer()
    results = analyzer.run_analysis()
    
    # Print comprehensive summary
    analyzer.print_summary_report()
    
    # Save detailed results
    output_file = "/home/wyatt/dev-projects/Prism/n8n-connectivity-comprehensive-report.json"
    analyzer.save_results(output_file)

if __name__ == "__main__":
    main()
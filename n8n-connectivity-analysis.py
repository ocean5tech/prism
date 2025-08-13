#!/usr/bin/env python3
"""
N8N Workflow Connectivity Analysis Script
Analyzes all n8n workflow files for URL availability, service connections, and endpoint validation
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
        self.results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'workflows_analyzed': [],
            'url_tests': {},
            'service_tests': {},
            'rss_feed_tests': {},
            'summary': {
                'total_urls': 0,
                'available_urls': 0,
                'total_services': 0,
                'available_services': 0,
                'critical_issues': [],
                'recommendations': []
            }
        }
        
        # Expected microservice ports and their purposes
        self.expected_services = {
            8010: "Content Generation Service",
            8011: "Detection/Quality Analysis Service", 
            8013: "Configuration Management Service",
            8015: "Analytics Service"
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
            'accessible': False
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
        except requests.exceptions.ConnectionError:
            result.update({
                'status': 'connection_error',
                'error': 'Connection failed',
                'accessible': False
            })
        except Exception as e:
            result.update({
                'status': 'error',
                'error': str(e),
                'accessible': False
            })
            
        return result
    
    def test_service_connectivity(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Test service connectivity on specific port"""
        result = {
            'host': host,
            'port': port,
            'service_name': self.expected_services.get(port, f"Service on port {port}"),
            'accessible': False,
            'status': 'unknown',
            'error': None,
            'response_time': None
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
                
                # Try HTTP health check if it's a web service
                try:
                    health_url = f"http://{host}:{port}/health"
                    health_response = requests.get(health_url, timeout=3)
                    if health_response.status_code == 200:
                        result['status'] = 'service_healthy'
                        result['health_check'] = True
                except:
                    result['health_check'] = False
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
                            result['feed_info']['title'] = title_match.group(1).strip()
                            
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
            result['error'] = str(e)
            
        return result
    
    def analyze_workflow_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a single workflow file"""
        workflow_result = {
            'filepath': filepath,
            'workflow_name': '',
            'urls_found': [],
            'url_test_results': {},
            'issues': []
        }
        
        try:
            with open(filepath, 'r') as f:
                workflow_data = json.load(f)
            
            workflow_result['workflow_name'] = workflow_data.get('name', 'Unknown')
            
            # Extract URLs
            urls = self.extract_urls_from_workflow(workflow_data)
            workflow_result['urls_found'] = urls
            
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
                
                # Track issues
                if not test_result.get('accessible', False):
                    issue = f"URL not accessible: {url} ({test_result.get('error', 'Unknown error')})"
                    workflow_result['issues'].append(issue)
                    
                    if url.startswith('http://localhost'):
                        self.results['summary']['critical_issues'].append(
                            f"Microservice endpoint unavailable: {url}"
                        )
                
        except Exception as e:
            workflow_result['issues'].append(f"Failed to analyze workflow: {str(e)}")
            
        return workflow_result
    
    def test_microservices(self):
        """Test all expected microservice endpoints"""
        print("Testing microservice connectivity...")
        
        for port, service_name in self.expected_services.items():
            print(f"  Testing {service_name} on port {port}")
            result = self.test_service_connectivity('localhost', port)
            self.results['service_tests'][port] = result
            
            if result['accessible']:
                self.results['summary']['available_services'] += 1
            else:
                self.results['summary']['critical_issues'].append(
                    f"{service_name} (port {port}) is not accessible"
                )
                
        self.results['summary']['total_services'] = len(self.expected_services)
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis results"""
        recommendations = []
        
        # Check RSS feed issues
        for url, result in self.results['rss_feed_tests'].items():
            if not result.get('accessible', False):
                recommendations.append(f"RSS Feed Issue: {url} - {result.get('error', 'Not accessible')}")
        
        # Check microservice issues
        unavailable_services = []
        for port, result in self.results['service_tests'].items():
            if not result.get('accessible', False):
                unavailable_services.append(f"Port {port} ({result['service_name']})")
        
        if unavailable_services:
            recommendations.append(f"Start missing services: {', '.join(unavailable_services)}")
            recommendations.append("Run 'cd backend && ./start-simple-services.sh' or use Docker Compose")
        
        # Check URL accessibility
        failed_urls = [url for url, result in self.results['url_tests'].items() 
                      if not result.get('accessible', False) and not url.startswith('webhook/')]
        
        if failed_urls:
            recommendations.append(f"Fix URL connectivity issues for: {', '.join(failed_urls[:3])}{'...' if len(failed_urls) > 3 else ''}")
        
        self.results['summary']['recommendations'] = recommendations
    
    def run_analysis(self):
        """Run complete connectivity analysis"""
        print("N8N Workflow Connectivity Analysis")
        print("="*50)
        
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
        
        print(f"\nAnalyzing workflows...")
        # Analyze each workflow
        for filepath in workflow_files:
            filename = os.path.basename(filepath)
            print(f"\nAnalyzing: {filename}")
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
        print(f"\nDetailed results saved to: {output_file}")
    
    def print_summary_report(self):
        """Print a summary report to console"""
        summary = self.results['summary']
        
        print(f"\n{'='*60}")
        print("CONNECTIVITY ANALYSIS SUMMARY")
        print(f"{'='*60}")
        
        print(f"📊 URL Connectivity:")
        print(f"   • Total URLs tested: {summary['total_urls']}")
        print(f"   • Available URLs: {summary['available_urls']}")
        print(f"   • Success rate: {(summary['available_urls']/summary['total_urls']*100) if summary['total_urls'] > 0 else 0:.1f}%")
        
        print(f"\n🔧 Microservice Status:")
        print(f"   • Total services: {summary['total_services']}")
        print(f"   • Available services: {summary['available_services']}")
        print(f"   • Service availability: {(summary['available_services']/summary['total_services']*100) if summary['total_services'] > 0 else 0:.1f}%")
        
        if summary['critical_issues']:
            print(f"\n❌ Critical Issues ({len(summary['critical_issues'])}):")
            for i, issue in enumerate(summary['critical_issues'][:5], 1):
                print(f"   {i}. {issue}")
            if len(summary['critical_issues']) > 5:
                print(f"   ... and {len(summary['critical_issues']) - 5} more")
        
        if summary['recommendations']:
            print(f"\n✅ Recommendations:")
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # RSS Feed specific report
        rss_feeds = self.results['rss_feed_tests']
        if rss_feeds:
            print(f"\n📡 RSS Feed Analysis:")
            for url, result in rss_feeds.items():
                status = "✅" if result.get('accessible', False) else "❌"
                feed_info = result.get('feed_info', {})
                item_count = feed_info.get('item_count', 'Unknown')
                print(f"   {status} {url}")
                if result.get('accessible', False):
                    print(f"      Items: {item_count}, Valid RSS: {result.get('valid_rss', False)}")
                else:
                    print(f"      Error: {result.get('error', 'Not accessible')}")
        
        print(f"\n{'='*60}")
        
        # Priority recommendations based on workflow types
        priority_issues = []
        if summary['available_services'] < summary['total_services']:
            priority_issues.append("🚨 PRIORITY: Start missing microservices before testing workflows")
        
        failed_rss = len([r for r in rss_feeds.values() if not r.get('accessible', False)])
        if failed_rss > 0:
            priority_issues.append(f"⚠️  RSS Feed issues detected ({failed_rss} feeds failing)")
        
        if priority_issues:
            print("IMMEDIATE ACTION REQUIRED:")
            for issue in priority_issues:
                print(f"  {issue}")
            print()


def main():
    analyzer = N8NConnectivityAnalyzer()
    results = analyzer.run_analysis()
    
    # Print summary to console
    analyzer.print_summary_report()
    
    # Save detailed results
    output_file = "/home/wyatt/dev-projects/Prism/n8n-connectivity-report.json"
    analyzer.save_results(output_file)
    
    print(f"\nAnalysis completed at {results['analysis_timestamp']}")

if __name__ == "__main__":
    main()
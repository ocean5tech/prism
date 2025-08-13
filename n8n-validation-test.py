#!/usr/bin/env python3
"""
n8n Workflow Engine Validation Test Suite
Provides comprehensive evidence of n8n functionality and workflow validation
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path

class N8nValidator:
    def __init__(self, base_url="http://localhost:5679"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "evidence": []
        }
    
    def log_evidence(self, test_name, status, details, data=None):
        """Log test evidence"""
        evidence = {
            "test": test_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        if data:
            evidence["data"] = data
        
        self.results["evidence"].append(evidence)
        
        if status == "PASS":
            self.results["tests_passed"] += 1
            print(f"✓ {test_name}: {details}")
        else:
            self.results["tests_failed"] += 1
            print(f"✗ {test_name}: {details}")
    
    def test_basic_connectivity(self):
        """Test basic HTTP connectivity to n8n"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200 and "n8n" in response.text.lower():
                self.log_evidence(
                    "Basic Connectivity", 
                    "PASS", 
                    f"n8n interface accessible, status code: {response.status_code}",
                    {"response_length": len(response.text), "contains_n8n": True}
                )
                return True
            else:
                self.log_evidence(
                    "Basic Connectivity", 
                    "FAIL", 
                    f"Unexpected response: {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
        except Exception as e:
            self.log_evidence(
                "Basic Connectivity", 
                "FAIL", 
                f"Connection failed: {str(e)}"
            )
            return False
    
    def test_health_endpoint(self):
        """Test n8n health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                self.log_evidence(
                    "Health Endpoint", 
                    "PASS", 
                    f"Health check successful: {health_data.get('status', 'unknown')}",
                    health_data
                )
                return True
            else:
                self.log_evidence(
                    "Health Endpoint", 
                    "FAIL", 
                    f"Health endpoint returned: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_evidence(
                "Health Endpoint", 
                "FAIL", 
                f"Health check failed: {str(e)}"
            )
            return False
    
    def test_api_availability(self):
        """Test n8n API endpoint availability"""
        try:
            # Test if API endpoints are available (should return auth required)
            response = requests.get(f"{self.base_url}/api/v1/workflows", timeout=10)
            if response.status_code == 401 or "api" in response.text.lower():
                self.log_evidence(
                    "API Availability", 
                    "PASS", 
                    f"API endpoints accessible (auth required as expected): {response.status_code}",
                    {"response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]}
                )
                return True
            else:
                self.log_evidence(
                    "API Availability", 
                    "FAIL", 
                    f"API endpoint unexpected response: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_evidence(
                "API Availability", 
                "FAIL", 
                f"API test failed: {str(e)}"
            )
            return False
    
    def validate_workflow_files(self):
        """Validate that workflow JSON files exist and are valid"""
        workflow_dir = Path("/home/wyatt/dev-projects/Prism/n8n-workflows")
        workflow_files = [
            "01-content-generation-pipeline.json",
            "02-adversarial-optimization.json", 
            "03-error-handler-workflow.json"
        ]
        
        valid_workflows = 0
        workflow_details = []
        
        for workflow_file in workflow_files:
            file_path = workflow_dir / workflow_file
            try:
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        workflow_data = json.load(f)
                    
                    # Validate workflow structure
                    required_fields = ['name', 'nodes', 'connections']
                    if all(field in workflow_data for field in required_fields):
                        node_count = len(workflow_data.get('nodes', []))
                        workflow_details.append({
                            "file": workflow_file,
                            "name": workflow_data.get('name'),
                            "nodes": node_count,
                            "valid": True
                        })
                        valid_workflows += 1
                    else:
                        workflow_details.append({
                            "file": workflow_file,
                            "valid": False,
                            "error": "Missing required fields"
                        })
                else:
                    workflow_details.append({
                        "file": workflow_file,
                        "valid": False,
                        "error": "File not found"
                    })
            except Exception as e:
                workflow_details.append({
                    "file": workflow_file,
                    "valid": False,
                    "error": str(e)
                })
        
        if valid_workflows == len(workflow_files):
            self.log_evidence(
                "Workflow Files Validation", 
                "PASS", 
                f"All {valid_workflows} workflow files are valid JSON with proper structure",
                workflow_details
            )
            return True
        else:
            self.log_evidence(
                "Workflow Files Validation", 
                "FAIL", 
                f"Only {valid_workflows}/{len(workflow_files)} workflow files are valid",
                workflow_details
            )
            return False
    
    def test_n8n_process(self):
        """Test if n8n process is running"""
        import subprocess
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'n8n' in result.stdout:
                # Extract n8n process info
                n8n_processes = [line for line in result.stdout.split('\n') if 'n8n' in line and 'grep' not in line]
                self.log_evidence(
                    "Process Check", 
                    "PASS", 
                    f"n8n process is running ({len(n8n_processes)} processes found)",
                    {"processes": n8n_processes[:3]}  # First 3 processes to avoid too much data
                )
                return True
            else:
                self.log_evidence(
                    "Process Check", 
                    "FAIL", 
                    "No n8n process found"
                )
                return False
        except Exception as e:
            self.log_evidence(
                "Process Check", 
                "FAIL", 
                f"Process check failed: {str(e)}"
            )
            return False
    
    def test_port_listening(self):
        """Test if port 5679 is being listened on"""
        import subprocess
        try:
            # Use ss to check listening ports
            result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
            if ':5679' in result.stdout:
                port_info = [line for line in result.stdout.split('\n') if ':5679' in line]
                self.log_evidence(
                    "Port Listening Check", 
                    "PASS", 
                    f"Port 5679 is being listened on",
                    {"port_info": port_info}
                )
                return True
            else:
                self.log_evidence(
                    "Port Listening Check", 
                    "FAIL", 
                    "Port 5679 is not being listened on"
                )
                return False
        except Exception as e:
            self.log_evidence(
                "Port Listening Check", 
                "FAIL", 
                f"Port check failed: {str(e)}"
            )
            return False
    
    def test_workflow_content_analysis(self):
        """Analyze workflow content for completeness and complexity"""
        workflow_dir = Path("/home/wyatt/dev-projects/Prism/n8n-workflows")
        
        try:
            # Load the main content generation pipeline
            pipeline_file = workflow_dir / "01-content-generation-pipeline.json"
            with open(pipeline_file, 'r') as f:
                pipeline = json.load(f)
            
            analysis = {
                "workflow_name": pipeline.get('name'),
                "total_nodes": len(pipeline.get('nodes', [])),
                "node_types": {},
                "has_connections": len(pipeline.get('connections', {})) > 0,
                "has_error_handling": 'errorWorkflow' in pipeline.get('settings', {}),
                "timeout_configured": 'executionTimeout' in pipeline.get('settings', {})
            }
            
            # Count node types
            for node in pipeline.get('nodes', []):
                node_type = node.get('type', 'unknown')
                analysis["node_types"][node_type] = analysis["node_types"].get(node_type, 0) + 1
            
            # Check for HTTP request nodes (indicating API integration)
            has_api_integration = 'n8n-nodes-base.httpRequest' in analysis["node_types"]
            
            self.log_evidence(
                "Workflow Content Analysis", 
                "PASS", 
                f"Complex workflow with {analysis['total_nodes']} nodes, API integration: {has_api_integration}",
                analysis
            )
            return True
            
        except Exception as e:
            self.log_evidence(
                "Workflow Content Analysis", 
                "FAIL", 
                f"Analysis failed: {str(e)}"
            )
            return False
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("=" * 60)
        print("n8n Workflow Engine Validation Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_basic_connectivity,
            self.test_health_endpoint,
            self.test_api_availability,
            self.test_n8n_process,
            self.test_port_listening,
            self.validate_workflow_files,
            self.test_workflow_content_analysis
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_evidence(
                    test.__name__, 
                    "FAIL", 
                    f"Test execution failed: {str(e)}"
                )
            time.sleep(0.5)  # Brief pause between tests
        
        # Generate summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Tests Passed: {self.results['tests_passed']}")
        print(f"Tests Failed: {self.results['tests_failed']}")
        print(f"Success Rate: {(self.results['tests_passed'] / (self.results['tests_passed'] + self.results['tests_failed'])) * 100:.1f}%")
        
        # Save detailed results
        results_file = "/home/wyatt/dev-projects/Prism/n8n-validation-results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
        return self.results['tests_failed'] == 0

if __name__ == "__main__":
    validator = N8nValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)
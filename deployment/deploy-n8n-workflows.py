#!/usr/bin/env python3
"""
n8n Workflow Deployment Script
Automated deployment of n8n workflows to n8n.cloud or self-hosted instances
"""

import os
import json
import requests
import sys
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class N8NWorkflowDeployer:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-N8N-API-KEY': api_key,
            'Content-Type': 'application/json'
        })
        
    def get_existing_workflows(self) -> Dict[str, Dict]:
        """Fetch all existing workflows from n8n instance"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/workflows")
            response.raise_for_status()
            workflows = response.json().get('data', [])
            return {wf['name']: wf for wf in workflows}
        except requests.RequestException as e:
            logging.error(f"Failed to fetch existing workflows: {e}")
            return {}

    def validate_workflow(self, workflow_data: Dict) -> bool:
        """Validate workflow structure and required fields"""
        required_fields = ['name', 'nodes', 'connections']
        
        for field in required_fields:
            if field not in workflow_data:
                logging.error(f"Missing required field: {field}")
                return False
                
        # Validate nodes structure
        if not isinstance(workflow_data['nodes'], list):
            logging.error("Nodes must be a list")
            return False
            
        return True

    def backup_workflow(self, workflow: Dict) -> bool:
        """Create backup of existing workflow before update"""
        try:
            backup_dir = Path('backups/workflows')
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"{workflow['name']}_{timestamp}.json"
            
            with open(backup_file, 'w') as f:
                json.dump(workflow, f, indent=2)
                
            logging.info(f"Backup created: {backup_file}")
            return True
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            return False

    def deploy_workflow(self, workflow_file: Path) -> bool:
        """Deploy a single workflow file"""
        try:
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
                
            if not self.validate_workflow(workflow_data):
                return False
                
            workflow_name = workflow_data['name']
            existing_workflows = self.get_existing_workflows()
            
            if workflow_name in existing_workflows:
                # Update existing workflow
                existing_workflow = existing_workflows[workflow_name]
                
                # Create backup before update
                if not self.backup_workflow(existing_workflow):
                    logging.warning(f"Backup failed for {workflow_name}, continuing anyway...")
                
                workflow_id = existing_workflow['id']
                response = self.session.put(
                    f"{self.base_url}/api/v1/workflows/{workflow_id}",
                    json=workflow_data
                )
                action = "Updated"
            else:
                # Create new workflow
                response = self.session.post(
                    f"{self.base_url}/api/v1/workflows",
                    json=workflow_data
                )
                action = "Created"
                
            response.raise_for_status()
            logging.info(f"{action} workflow: {workflow_name}")
            return True
            
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {workflow_file}: {e}")
            return False
        except requests.RequestException as e:
            logging.error(f"API request failed for {workflow_file}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error deploying {workflow_file}: {e}")
            return False

    def activate_workflow(self, workflow_name: str) -> bool:
        """Activate a deployed workflow"""
        try:
            existing_workflows = self.get_existing_workflows()
            
            if workflow_name not in existing_workflows:
                logging.error(f"Workflow not found: {workflow_name}")
                return False
                
            workflow_id = existing_workflows[workflow_name]['id']
            
            response = self.session.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/activate"
            )
            response.raise_for_status()
            
            logging.info(f"Activated workflow: {workflow_name}")
            return True
            
        except requests.RequestException as e:
            logging.error(f"Failed to activate workflow {workflow_name}: {e}")
            return False

    def deploy_all_workflows(self, workflows_dir: Path) -> Dict[str, bool]:
        """Deploy all workflow files in the specified directory"""
        results = {}
        
        # Find all JSON files in workflows directory
        workflow_files = list(workflows_dir.glob('*.json'))
        
        if not workflow_files:
            logging.warning(f"No workflow files found in {workflows_dir}")
            return results
            
        logging.info(f"Found {len(workflow_files)} workflow files to deploy")
        
        # Deploy each workflow
        for workflow_file in workflow_files:
            logging.info(f"Deploying: {workflow_file.name}")
            success = self.deploy_workflow(workflow_file)
            results[workflow_file.name] = success
            
            if success:
                # Try to activate the workflow
                try:
                    with open(workflow_file, 'r') as f:
                        workflow_data = json.load(f)
                    workflow_name = workflow_data['name']
                    self.activate_workflow(workflow_name)
                except Exception as e:
                    logging.warning(f"Could not activate {workflow_file.name}: {e}")
                    
        return results

def main():
    """Main deployment function"""
    # Configuration from environment variables
    n8n_base_url = os.getenv('N8N_BASE_URL', 'https://api.n8n.cloud')
    n8n_api_key = os.getenv('N8N_API_KEY')
    
    if not n8n_api_key:
        logging.error("N8N_API_KEY environment variable is required")
        sys.exit(1)
        
    # Initialize deployer
    deployer = N8NWorkflowDeployer(n8n_base_url, n8n_api_key)
    
    # Deploy workflows
    workflows_dir = Path('n8n-workflows')
    
    if not workflows_dir.exists():
        logging.error(f"Workflows directory not found: {workflows_dir}")
        sys.exit(1)
        
    logging.info(f"Starting deployment to {n8n_base_url}")
    results = deployer.deploy_all_workflows(workflows_dir)
    
    # Report results
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    logging.info(f"Deployment complete: {successful}/{total} workflows deployed successfully")
    
    # List failed deployments
    failed = [name for name, success in results.items() if not success]
    if failed:
        logging.error(f"Failed deployments: {', '.join(failed)}")
        sys.exit(1)
    else:
        logging.info("All workflows deployed successfully!")

if __name__ == "__main__":
    main()
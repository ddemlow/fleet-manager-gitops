#!/usr/bin/env python3
"""
GitOps deployment script for Fleet Manager
Automatically deploys manifests from GitHub to Fleet Manager via MCP server
"""

import os
import sys
import yaml
import json
import requests
import glob
from pathlib import Path
from typing import Dict, List, Any

class FleetManagerGitOps:
    def __init__(self):
        self.fm_api_key = os.getenv('SC_FM_APIKEY')
        self.fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
        
        if not self.fm_api_key:
            raise ValueError("SC_FM_APIKEY environment variable is required")
            
        # Fleet Manager API headers (based on actual API usage)
        self.headers = {
            'authority': 'api.scalecomputing.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'api-key': self.fm_api_key,
            'origin': 'https://fleet.scalecomputing.com',
            'referer': 'https://fleet.scalecomputing.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'Content-Type': 'application/json'
        }

    def get_changed_files(self) -> List[str]:
        """Get list of changed manifest files"""
        changed_files = []
        
        # Check for changed files in the current commit
        try:
            import subprocess
            result = subprocess.run(['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'], 
                                 capture_output=True, text=True, check=True)
            changed_files = [f for f in result.stdout.strip().split('\n') 
                           if f.startswith(('manifests/', 'applications/')) and f.endswith(('.yaml', '.yml'))]
        except:
            # Fallback: process all manifest files
            changed_files = glob.glob('manifests/**/*.yaml', recursive=True) + \
                           glob.glob('manifests/**/*.yml', recursive=True) + \
                           glob.glob('applications/**/*.yaml', recursive=True) + \
                           glob.glob('applications/**/*.yml', recursive=True)
        
        return changed_files

    def load_manifest(self, file_path: str) -> Dict[str, Any]:
        """Load and parse a YAML manifest file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return None

    def find_deployment_application(self, app_name: str) -> str:
        """Find existing deployment application by name"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployment-applications?limit=200",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            for app in data.get('items', []):
                if app.get('name') == app_name:
                    return app.get('id')
            return None
        except Exception as e:
            print(f"❌ Error finding application {app_name}: {e}")
            return None

    def create_deployment_application(self, app_name: str, manifest: str) -> str:
        """Create a new deployment application using PUT"""
        try:
            payload = {
                "name": app_name,
                "sourceType": "editor",  # Use "editor" like in your example
                "sourceConfig": manifest
            }
            
            # Use PUT for deployment-applications (always PUT according to API)
            response = requests.put(
                f"{self.fm_api_url}/deployment-applications",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            app_id = data.get('id')
            print(f"✅ Created new application: {app_name} (ID: {app_id})")
            return app_id
            
        except Exception as e:
            print(f"❌ Error creating application {app_name}: {e}")
            return None

    def update_deployment_application(self, app_id: str, app_name: str, manifest: str) -> bool:
        """Update an existing deployment application"""
        try:
            payload = {
                "name": app_name,
                "sourceType": "editor",  # Use "editor" like in your example
                "sourceConfig": manifest
            }
            
            response = requests.put(
                f"{self.fm_api_url}/deployment-applications/{app_id}",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            print(f"✅ Updated application: {app_name} (ID: {app_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error updating application {app_name}: {e}")
            return False

    def deploy_application(self, app_id: str, app_name: str) -> bool:
        """Deploy the application to clusters"""
        try:
            # First, find the deployment for this application
            response = requests.get(
                f"{self.fm_api_url}/deployments?limit=200",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            deployments = response.json().get('items', [])
            deployment_id = None
            
            for deployment in deployments:
                if deployment.get('name') == app_name:
                    deployment_id = deployment.get('id')
                    break
            
            if not deployment_id:
                print(f"❌ No deployment found for application: {app_name}")
                return False
            
            # Trigger deployment using POST (as shown in your examples)
            response = requests.post(
                f"{self.fm_api_url}/deployments/{deployment_id}/deploy",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            print(f"✅ Triggered deployment for: {app_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error deploying application {app_name}: {e}")
            return False

    def process_manifest(self, file_path: str) -> bool:
        """Process a single manifest file"""
        print(f"\n📄 Processing: {file_path}")
        
        manifest = self.load_manifest(file_path)
        if not manifest:
            return False
        
        # Extract application name from manifest or filename
        app_name = manifest.get('metadata', {}).get('name')
        if not app_name:
            app_name = Path(file_path).stem
        
        # Convert manifest to YAML string
        manifest_yaml = yaml.dump(manifest, default_flow_style=False)
        
        # Check if application already exists
        app_id = self.find_deployment_application(app_name)
        
        if app_id:
            # Update existing application
            success = self.update_deployment_application(app_id, app_name, manifest_yaml)
        else:
            # Create new application
            app_id = self.create_deployment_application(app_name, manifest_yaml)
            success = app_id is not None
        
        if success and app_id:
            # Deploy the application
            return self.deploy_application(app_id, app_name)
        
        return False

    def run(self):
        """Main deployment process"""
        print("🚀 Starting GitOps deployment to Fleet Manager")
        print(f"📡 Fleet Manager API: {self.fm_api_url}")
        
        # Test connection to Fleet Manager API
        try:
            response = requests.get(
                f"{self.fm_api_url}/clusters",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Fleet Manager API connection successful")
            else:
                print(f"❌ Fleet Manager API connection failed (status: {response.status_code})")
                print(f"Response: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ Fleet Manager API connection error: {e}")
            return False
        
        # Get changed files
        changed_files = self.get_changed_files()
        if not changed_files:
            print("ℹ️  No manifest files changed")
            return True
        
        print(f"📋 Found {len(changed_files)} changed manifest files")
        
        # Process each changed file
        success_count = 0
        for file_path in changed_files:
            if self.process_manifest(file_path):
                success_count += 1
        
        print(f"\n📊 Deployment Summary:")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {len(changed_files) - success_count}")
        
        return success_count == len(changed_files)

if __name__ == "__main__":
    try:
        deployer = FleetManagerGitOps()
        success = deployer.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)

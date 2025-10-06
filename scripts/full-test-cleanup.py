#!/usr/bin/env python3
"""
Full test cleanup script that removes VMs and then cleans up deployments/applications
"""

import os
import sys
import time
import yaml
import requests
import tempfile
import subprocess
import argparse
from typing import List, Dict, Optional
from datetime import datetime

class FullTestCleanup:
    def __init__(self):
        self.fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
        self.api_key = os.getenv('SC_FM_APIKEY')
        
        if not self.api_key:
            print("❌ SC_FM_APIKEY environment variable not set")
            sys.exit(1)
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_test_applications(self) -> List[Dict]:
        """Get all test applications (those ending with -test)"""
        print("🔍 Finding test applications...")
        
        applications = []
        url = f"{self.fm_api_url}/deployment-applications"
        
        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"❌ Failed to fetch applications: {response.status_code}")
                return []
            
            data = response.json()
            for app in data.get('items', []):
                app_name = app.get('name', '')
                if app_name.endswith('-test'):
                    applications.append(app)
            
            url = data.get('next')
        
        print(f"📋 Found {len(applications)} test applications")
        return applications

    def get_test_deployments(self) -> List[Dict]:
        """Get all test deployments (those with -test- in name)"""
        print("🔍 Finding test deployments...")
        
        deployments = []
        url = f"{self.fm_api_url}/deployments"
        
        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"❌ Failed to fetch deployments: {response.status_code}")
                return []
            
            data = response.json()
            for dep in data.get('items', []):
                dep_name = dep.get('name', '')
                if '-test-' in dep_name:
                    deployments.append(dep)
            
            url = data.get('next')
        
        print(f"📋 Found {len(deployments)} test deployments")
        return deployments

    def create_cleanup_manifest(self, app_name: str, app_source_config: str) -> str:
        """Create a cleanup manifest that removes all VMs"""
        try:
            # Parse the original manifest
            original_manifest = yaml.safe_load(app_source_config)
            
            # Create cleanup version
            cleanup_manifest = original_manifest.copy()
            
            # Modify metadata
            if 'metadata' in cleanup_manifest:
                cleanup_manifest['metadata']['name'] = f"{app_name}-cleanup"
                cleanup_manifest['metadata']['description'] = f"[CLEANUP] Removing all VMs for {app_name}"
            
            # Remove all resources (VMs, virdomains, etc.)
            if 'spec' in cleanup_manifest:
                cleanup_manifest['spec']['resources'] = []
                # Keep assets but remove resources
                if 'assets' in cleanup_manifest['spec']:
                    cleanup_manifest['spec']['assets'] = []
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
            yaml.dump(cleanup_manifest, temp_file, default_flow_style=False)
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Error creating cleanup manifest for {app_name}: {e}")
            return None

    def deploy_cleanup_manifest(self, manifest_path: str, app_name: str, cluster_groups: List[str]) -> bool:
        """Deploy the cleanup manifest to remove VMs"""
        print(f"🧹 Deploying cleanup manifest for {app_name}...")
        
        try:
            # Set up environment for deployment
            env = os.environ.copy()
            env['TARGET_APPLICATIONS'] = f"{app_name}-cleanup"
            env['SKIP_DEPLOYMENT_TRIGGER'] = 'false'  # We want to trigger deployment
            
            # Run deployment
            result = subprocess.run([
                'python3', 'scripts/deploy.py'
            ], cwd=os.getcwd(), env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Cleanup deployment successful for {app_name}")
                return True
            else:
                print(f"❌ Cleanup deployment failed for {app_name}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error deploying cleanup manifest for {app_name}: {e}")
            return False

    def wait_for_vm_cleanup(self, app_name: str, timeout_minutes: int = 10) -> bool:
        """Wait for VM cleanup to complete"""
        print(f"⏳ Waiting for VM cleanup to complete for {app_name}...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            # Check deployment status
            try:
                url = f"{self.fm_api_url}/deployments"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    cleanup_deployments = []
                    
                    for dep in data.get('items', []):
                        dep_name = dep.get('name', '')
                        if f"{app_name}-cleanup" in dep_name:
                            cleanup_deployments.append(dep)
                    
                    if not cleanup_deployments:
                        print(f"✅ No cleanup deployments found - VMs likely cleaned up")
                        return True
                    
                    # Check if any cleanup deployments are still running
                    running_deployments = [dep for dep in cleanup_deployments 
                                         if dep.get('status') in ['Running', 'Pending', 'Created']]
                    
                    if not running_deployments:
                        print(f"✅ All cleanup deployments completed for {app_name}")
                        return True
                    
                    print(f"⏳ {len(running_deployments)} cleanup deployments still running...")
                    
            except Exception as e:
                print(f"⚠️  Error checking cleanup status: {e}")
            
            time.sleep(30)  # Check every 30 seconds
        
        print(f"⏰ Timeout waiting for VM cleanup for {app_name}")
        return False

    def delete_application(self, app_id: str, app_name: str) -> bool:
        """Delete an application"""
        url = f"{self.fm_api_url}/deployment-applications/{app_id}"
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 204:
            print(f"✅ Deleted application: {app_name}")
            return True
        else:
            print(f"❌ Failed to delete application {app_name}: {response.status_code}")
            if response.status_code == 409:
                print(f"   (Application may still have active deployments)")
            return False

    def delete_deployment(self, dep_id: str, dep_name: str) -> bool:
        """Delete a deployment"""
        url = f"{self.fm_api_url}/deployments/{dep_id}"
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 204:
            print(f"✅ Deleted deployment: {dep_name}")
            return True
        else:
            print(f"❌ Failed to delete deployment {dep_name}: {response.status_code}")
            return False

    def full_cleanup(self, dry_run: bool = True, vm_cleanup: bool = True, timeout_minutes: int = 10):
        """Perform full cleanup including VMs"""
        
        print("🧹 FULL TEST CLEANUP")
        print("=" * 50)
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual changes will be made")
        
        if vm_cleanup:
            print("🖥️  VM cleanup: ENABLED (will remove VMs before deleting deployments)")
        else:
            print("🖥️  VM cleanup: DISABLED (will only delete deployments/applications)")
        
        # Get test applications and deployments
        test_apps = self.get_test_applications()
        test_deployments = self.get_test_deployments()
        
        if not test_apps and not test_deployments:
            print("✅ No test applications or deployments found to clean up")
            return
        
        # Show what will be cleaned up
        print(f"\n📋 CLEANUP PLAN:")
        print(f"   📦 Test Applications: {len(test_apps)}")
        print(f"   🚀 Test Deployments: {len(test_deployments)}")
        
        if test_apps:
            print(f"\n   Applications to clean up:")
            for app in test_apps:
                app_name = app.get('name', 'unknown')
                print(f"     - {app_name}")
        
        if test_deployments:
            print(f"\n   Deployments to clean up:")
            for dep in test_deployments:
                dep_name = dep.get('name', 'unknown')
                status = dep.get('status', 'unknown')
                print(f"     - {dep_name} (Status: {status})")
        
        if dry_run:
            print(f"\n🧪 DRY RUN COMPLETE")
            print(f"Run with --execute to perform actual cleanup")
            return
        
        # Confirm cleanup
        total_items = len(test_apps) + len(test_deployments)
        if total_items == 0:
            print("✅ Nothing to clean up")
            return
        
        print(f"\n⚠️  Starting full cleanup of {total_items} test items...")
        
        cleanup_results = {
            'apps_processed': 0,
            'apps_vm_cleaned': 0,
            'apps_deleted': 0,
            'deployments_deleted': 0,
            'errors': []
        }
        
        # Step 1: VM Cleanup (if enabled)
        if vm_cleanup and test_apps:
            print(f"\n🖥️  STEP 1: VM CLEANUP")
            print("-" * 30)
            
            for app in test_apps:
                app_name = app.get('name', 'unknown')
                app_id = app.get('id', 'unknown')
                app_source_config = app.get('sourceConfig', '')
                
                print(f"\n🧹 Processing {app_name}...")
                cleanup_results['apps_processed'] += 1
                
                if not app_source_config:
                    print(f"⚠️  No source config found for {app_name}, skipping VM cleanup")
                    continue
                
                # Create cleanup manifest
                cleanup_manifest_path = self.create_cleanup_manifest(app_name, app_source_config)
                if not cleanup_manifest_path:
                    cleanup_results['errors'].append(f"Failed to create cleanup manifest for {app_name}")
                    continue
                
                try:
                    # Get cluster groups from original manifest
                    original_manifest = yaml.safe_load(app_source_config)
                    cluster_groups = original_manifest.get('metadata', {}).get('clusterGroups', [])
                    
                    # Deploy cleanup manifest
                    if self.deploy_cleanup_manifest(cleanup_manifest_path, app_name, cluster_groups):
                        cleanup_results['apps_vm_cleaned'] += 1
                        
                        # Wait for VM cleanup to complete
                        if self.wait_for_vm_cleanup(app_name, timeout_minutes):
                            print(f"✅ VM cleanup completed for {app_name}")
                        else:
                            print(f"⚠️  VM cleanup timed out for {app_name}, proceeding anyway")
                    else:
                        cleanup_results['errors'].append(f"VM cleanup deployment failed for {app_name}")
                
                finally:
                    # Clean up temporary manifest file
                    if cleanup_manifest_path and os.path.exists(cleanup_manifest_path):
                        os.unlink(cleanup_manifest_path)
        
        # Step 2: Delete deployments
        print(f"\n🚀 STEP 2: DEPLOYMENT CLEANUP")
        print("-" * 30)
        
        for dep in test_deployments:
            dep_name = dep.get('name', 'unknown')
            dep_id = dep.get('id', 'unknown')
            
            print(f"🗑️  Deleting deployment: {dep_name}")
            if self.delete_deployment(dep_id, dep_name):
                cleanup_results['deployments_deleted'] += 1
            else:
                cleanup_results['errors'].append(f"Failed to delete deployment {dep_name}")
        
        # Step 3: Delete applications
        print(f"\n📦 STEP 3: APPLICATION CLEANUP")
        print("-" * 30)
        
        for app in test_apps:
            app_name = app.get('name', 'unknown')
            app_id = app.get('id', 'unknown')
            
            print(f"🗑️  Deleting application: {app_name}")
            if self.delete_application(app_id, app_name):
                cleanup_results['apps_deleted'] += 1
            else:
                cleanup_results['errors'].append(f"Failed to delete application {app_name}")
        
        # Final summary
        print(f"\n📊 CLEANUP SUMMARY")
        print("=" * 50)
        print(f"✅ Applications processed: {cleanup_results['apps_processed']}")
        print(f"🖥️  VMs cleaned up: {cleanup_results['apps_vm_cleaned']}")
        print(f"📦 Applications deleted: {cleanup_results['apps_deleted']}")
        print(f"🚀 Deployments deleted: {cleanup_results['deployments_deleted']}")
        
        if cleanup_results['errors']:
            print(f"\n❌ ERRORS ({len(cleanup_results['errors'])}):")
            for error in cleanup_results['errors']:
                print(f"   - {error}")
        
        if cleanup_results['errors']:
            print(f"\n⚠️  Cleanup completed with {len(cleanup_results['errors'])} errors")
        else:
            print(f"\n🎉 Full cleanup completed successfully!")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Full test cleanup including VMs')
    parser.add_argument('--execute', action='store_true', help='Actually perform cleanup (default is dry run)')
    parser.add_argument('--no-vm-cleanup', action='store_true', help='Skip VM cleanup, only delete deployments/applications')
    parser.add_argument('--timeout', type=int, default=10, help='VM cleanup timeout in minutes (default: 10)')
    
    args = parser.parse_args()
    
    cleanup = FullTestCleanup()
    cleanup.full_cleanup(
        dry_run=not args.execute,
        vm_cleanup=not args.no_vm_cleanup,
        timeout_minutes=args.timeout
    )

if __name__ == "__main__":
    main()

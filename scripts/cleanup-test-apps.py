#!/usr/bin/env python3
"""
Cleanup script to remove test applications and deployments
"""

import os
import sys
import requests
import argparse
from typing import List, Dict

class TestAppCleanup:
    def __init__(self):
        self.fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
        self.api_key = os.getenv('SC_FM_APIKEY')
        
        if not self.api_key:
            print("❌ SC_FM_APIKEY environment variable not set")
            sys.exit(1)
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
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
        """Get all test deployments (those ending with -test)"""
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
    
    def delete_application(self, app_id: str, app_name: str) -> bool:
        """Delete an application"""
        url = f"{self.fm_api_url}/deployment-applications/{app_id}"
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 204:
            print(f"✅ Deleted application: {app_name}")
            return True
        else:
            print(f"❌ Failed to delete application {app_name}: {response.status_code}")
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
    
    def cleanup_test_apps(self, dry_run: bool = True):
        """Clean up test applications and deployments"""
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual deletions will be performed")
        
        # Get test applications
        test_apps = self.get_test_applications()
        
        if not test_apps:
            print("✅ No test applications found to clean up")
            return
        
        print(f"\n📋 Test Applications to {'delete' if not dry_run else 'review'}:")
        for app in test_apps:
            app_name = app.get('name', 'unknown')
            app_id = app.get('id', 'unknown')
            print(f"  - {app_name} (ID: {app_id})")
        
        # Get test deployments
        test_deployments = self.get_test_deployments()
        
        if test_deployments:
            print(f"\n📋 Test Deployments to {'delete' if not dry_run else 'review'}:")
            for dep in test_deployments:
                dep_name = dep.get('name', 'unknown')
                dep_id = dep.get('id', 'unknown')
                status = dep.get('status', 'unknown')
                print(f"  - {dep_name} (ID: {dep_id}, Status: {status})")
        
        if dry_run:
            print(f"\n🧪 DRY RUN COMPLETE")
            print(f"Found {len(test_apps)} test applications and {len(test_deployments)} test deployments")
            print(f"Run with --execute to actually delete them")
            return
        
        # Confirm deletion
        total_items = len(test_apps) + len(test_deployments)
        print(f"\n⚠️  About to delete {total_items} test items")
        
        if total_items == 0:
            print("✅ Nothing to delete")
            return
        
        # Delete deployments first (they depend on applications)
        deleted_deployments = 0
        for dep in test_deployments:
            dep_name = dep.get('name', 'unknown')
            dep_id = dep.get('id', 'unknown')
            if self.delete_deployment(dep_id, dep_name):
                deleted_deployments += 1
        
        # Delete applications
        deleted_apps = 0
        for app in test_apps:
            app_name = app.get('name', 'unknown')
            app_id = app.get('id', 'unknown')
            if self.delete_application(app_id, app_name):
                deleted_apps += 1
        
        print(f"\n📊 Cleanup Summary:")
        print(f"✅ Deleted {deleted_apps} test applications")
        print(f"✅ Deleted {deleted_deployments} test deployments")
        print(f"❌ Failed to delete {len(test_apps) - deleted_apps} applications")
        print(f"❌ Failed to delete {len(test_deployments) - deleted_deployments} deployments")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Clean up test applications and deployments')
    parser.add_argument('--execute', action='store_true', help='Actually delete items (default is dry run)')
    
    args = parser.parse_args()
    
    cleanup = TestAppCleanup()
    cleanup.cleanup_test_apps(dry_run=not args.execute)

if __name__ == "__main__":
    main()

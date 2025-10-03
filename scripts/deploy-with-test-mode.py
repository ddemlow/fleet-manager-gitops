#!/usr/bin/env python3
"""
Enhanced deployment script that handles test vs production deployments
by creating separate applications for testing.
"""

import os
import sys
import yaml
import json
import requests
import glob
from pathlib import Path
from typing import Dict, List, Any

# Import the main deployment class
sys.path.append(os.path.dirname(__file__))
from deploy import FleetManagerGitOps

class TestModeDeployer(FleetManagerGitOps):
    def __init__(self, test_mode=False, test_cluster_group="dd_szt15b"):
        super().__init__()
        self.test_mode = test_mode
        self.test_cluster_group = test_cluster_group
        
    def modify_manifest_for_test(self, manifest_path: str) -> str:
        """Create a test version of the manifest with modified cluster groups and app name"""
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
        
        # Create a copy for modification
        test_manifest = manifest.copy()
        
        # Modify metadata for testing
        if 'metadata' in test_manifest:
            # Change cluster groups to test cluster group
            test_manifest['metadata']['clusterGroups'] = [self.test_cluster_group]
            
            # Add test suffix to application name
            original_name = test_manifest['metadata'].get('name', '')
            test_manifest['metadata']['name'] = f"{original_name}-test"
            
            # Add test description
            original_desc = test_manifest['metadata'].get('description', '')
            test_manifest['metadata']['description'] = f"[TEST] {original_desc}"
        
        # Create test manifest file
        test_manifest_path = manifest_path.replace('.yaml', '-test.yaml')
        with open(test_manifest_path, 'w') as f:
            yaml.dump(test_manifest, f, default_flow_style=False)
        
        return test_manifest_path
    
    def deploy_manifest_with_test_mode(self, manifest_path: str):
        """Deploy manifest in test mode (separate app) or production mode"""
        if self.test_mode:
            print(f"🧪 TEST MODE: Creating test version of {manifest_path}")
            
            # Create test version of manifest
            test_manifest_path = self.modify_manifest_for_test(manifest_path)
            
            try:
                # Deploy test version
                print(f"📄 Deploying test manifest: {test_manifest_path}")
                success = self.process_manifest(test_manifest_path)
                
                if success:
                    print(f"✅ Test deployment successful!")
                    print(f"📋 Test application: {self.get_app_name_from_manifest(test_manifest_path)}")
                    print(f"🎯 Test cluster group: {self.test_cluster_group}")
                else:
                    print(f"❌ Test deployment failed!")
                
                return success
                
            finally:
                # Clean up test manifest file
                if os.path.exists(test_manifest_path):
                    os.remove(test_manifest_path)
                    print(f"🧹 Cleaned up test manifest: {test_manifest_path}")
        else:
            print(f"🚀 PRODUCTION MODE: Deploying original {manifest_path}")
            return self.process_manifest(manifest_path)
    
    def get_app_name_from_manifest(self, manifest_path: str) -> str:
        """Extract application name from manifest"""
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
        return manifest.get('metadata', {}).get('name', 'unknown')
    
    def run_with_test_mode(self):
        """Main deployment process with test mode support"""
        print("🚀 Starting Fleet Manager GitOps Deployment")
        if self.test_mode:
            print(f"🧪 TEST MODE: Deploying to {self.test_cluster_group} with separate test applications")
        else:
            print("🚀 PRODUCTION MODE: Deploying to production cluster groups")
        
        print(f"📡 Fleet Manager API: {self.fm_api_url}")
        
        # Test API connection
        try:
            response = requests.get(f"{self.fm_api_url}/deployments", headers=self.headers, timeout=10)
            if response.status_code != 200:
                print("❌ Fleet Manager API connection failed")
                return False
        except Exception as e:
            print(f"❌ Fleet Manager API connection failed: {e}")
            return False
        
        print("✅ Fleet Manager API connection successful")
        
        # Get changed manifest files
        changed_files = self.get_compiled_files_to_process()
        
        if not changed_files:
            print("📋 No changed manifest files found")
            return True
        
        print(f"📋 Found {len(changed_files)} changed manifest files")
        
        # Process each manifest
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for manifest_path in changed_files:
            try:
                print(f"\n📄 Processing: {manifest_path}")
                
                if self.should_process_manifest(manifest_path):
                    success = self.deploy_manifest_with_test_mode(manifest_path)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    print(f"⏭️  Skipping {manifest_path} (filtered out)")
                    skip_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing {manifest_path}: {e}")
                fail_count += 1
        
        # Print summary
        print(f"\n📊 Deployment Summary:")
        print(f"✅ Successful: {success_count}")
        print(f"⏭️  Skipped: {skip_count}")
        print(f"❌ Failed: {fail_count}")
        
        if self.test_mode and success_count > 0:
            print(f"\n🧪 TEST DEPLOYMENT COMPLETE!")
            print(f"📋 Test applications created in cluster group: {self.test_cluster_group}")
            print(f"🔗 Fleet Manager: https://fleet.scalecomputing.com/cluster-groups?org=63b8337ec6939fdfb0f716af")
            print(f"\n📝 Next steps:")
            print(f"1. ✅ Verify test deployments in Fleet Manager UI")
            print(f"2. ✅ Test the applications in {self.test_cluster_group}")
            print(f"3. ✅ If tests pass, approve for production deployment")
        
        return fail_count == 0

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy with test mode support')
    parser.add_argument('--test', action='store_true', help='Enable test mode')
    parser.add_argument('--test-cluster-group', default='dd_szt15b', help='Test cluster group name')
    parser.add_argument('--target-apps', help='Comma-separated list of target applications')
    
    args = parser.parse_args()
    
    # Set environment variables
    if args.test:
        os.environ['TEST_MODE'] = 'true'
        os.environ['CLUSTER_GROUP_NAME'] = args.test_cluster_group
    else:
        os.environ['TEST_MODE'] = 'false'
    
    if args.target_apps:
        os.environ['TARGET_APPLICATIONS'] = args.target_apps
    
    # Create deployer
    deployer = TestModeDeployer(
        test_mode=args.test,
        test_cluster_group=args.test_cluster_group
    )
    
    # Run deployment
    success = deployer.run_with_test_mode()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

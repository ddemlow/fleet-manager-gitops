#!/usr/bin/env python3
"""
Simple test deployment script that creates test versions of manifests
"""

import os
import sys
import yaml
import shutil
import subprocess

def create_test_manifest(manifest_path: str, test_cluster_group: str = "dd_szt15b") -> str:
    """Create a test version of the manifest"""
    
    # Read original manifest
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)
    
    # Create test version
    test_manifest = manifest.copy()
    
    # Modify for testing
    if 'metadata' in test_manifest:
        # Change cluster groups to test cluster group
        test_manifest['metadata']['clusterGroups'] = [test_cluster_group]
        
        # Add test suffix to application name - just use 'test' to make it unique
        original_name = test_manifest['metadata'].get('name', '')
        test_manifest['metadata']['name'] = f"{original_name}-test"
        
        # Add test description
        original_desc = test_manifest['metadata'].get('description', '')
        test_manifest['metadata']['description'] = f"[TEST] {original_desc} - {test_cluster_group}"
    
    # Create test manifest file
    test_manifest_path = manifest_path.replace('.yaml', '-test.yaml')
    with open(test_manifest_path, 'w') as f:
        yaml.dump(test_manifest, f, default_flow_style=False)
    
    return test_manifest_path

def deploy_test_manifest(manifest_path: str, test_cluster_group: str = "dd_szt15b"):
    """Deploy manifest in test mode"""
    
    print(f"🧪 Creating test deployment for: {manifest_path}")
    
    # Create test version
    test_manifest_path = create_test_manifest(manifest_path, test_cluster_group)
    
    try:
        print(f"📄 Test manifest created: {test_manifest_path}")
        
        # Get the application name from the test manifest
        with open(test_manifest_path, 'r') as f:
            test_manifest = yaml.safe_load(f)
        app_name = test_manifest.get('metadata', {}).get('name', 'unknown')
        
        # Set environment for test deployment
        env = os.environ.copy()
        env['CLUSTER_GROUP_NAME'] = test_cluster_group
        env['TARGET_APPLICATIONS'] = app_name
        
        # Run deployment
        print(f"🚀 Deploying to test cluster group: {test_cluster_group}")
        result = subprocess.run([
            'python3', 'scripts/deploy.py'
        ], cwd=os.getcwd(), env=env, capture_output=True, text=True)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ Test deployment successful!")
            print(f"📋 Test application: {env['TARGET_APPLICATIONS']}")
            print(f"🎯 Test cluster group: {test_cluster_group}")
            return True
        else:
            print(f"❌ Test deployment failed!")
            return False
            
    finally:
        # Clean up test manifest
        if os.path.exists(test_manifest_path):
            os.remove(test_manifest_path)
            print(f"🧹 Cleaned up test manifest: {test_manifest_path}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy manifest in test mode')
    parser.add_argument('manifest', help='Manifest file to deploy in test mode')
    parser.add_argument('--test-cluster-group', default='dd_szt15b', help='Test cluster group name')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.manifest):
        print(f"❌ Manifest file not found: {args.manifest}")
        sys.exit(1)
    
    success = deploy_test_manifest(args.manifest, args.test_cluster_group)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

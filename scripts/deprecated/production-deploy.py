#!/usr/bin/env python3
"""
Production deployment script that ensures only production applications are deployed
"""

import os
import sys
import yaml
import subprocess

def is_production_manifest(manifest_path: str) -> bool:
    """Check if a manifest is suitable for production deployment"""
    
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)
    
    # Check if it's a test manifest
    app_name = manifest.get('metadata', {}).get('name', '')
    description = manifest.get('metadata', {}).get('description', '')
    
    # Skip test applications
    if '-test' in app_name.lower():
        return False
    
    # Skip test descriptions
    if '[test]' in description.lower():
        return False
    
    return True

def deploy_production_manifest(manifest_path: str):
    """Deploy manifest in production mode"""
    
    if not is_production_manifest(manifest_path):
        print(f"⏭️  Skipping test manifest: {manifest_path}")
        return True
    
    print(f"🚀 Deploying to production: {manifest_path}")
    
    # Set environment for production deployment
    env = os.environ.copy()
    env['TEST_MODE'] = 'false'  # Ensure test mode is off
    
    # Run deployment
    result = subprocess.run([
        'python3', 'scripts/deploy.py'
    ], cwd=os.getcwd(), env=env, capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        print(f"✅ Production deployment successful!")
        return True
    else:
        print(f"❌ Production deployment failed!")
        return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy manifest in production mode')
    parser.add_argument('manifest', help='Manifest file to deploy in production mode')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.manifest):
        print(f"❌ Manifest file not found: {args.manifest}")
        sys.exit(1)
    
    success = deploy_production_manifest(args.manifest)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Find deployments where associated applications don't have valid manifest content
Now properly checks sourceConfig field and handles multiple applications per deployment
"""

import os
import sys
import requests
import yaml
from typing import Dict, List, Any, Set

def get_all_deployments() -> List[Dict[str, Any]]:
    """Get all deployments"""
    api_key = os.getenv('SC_FM_APIKEY')
    api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    
    headers = {
        'accept': 'application/json',
        'api-key': api_key
    }
    
    deployments = []
    url = f"{api_url}/deployments?limit=50"
    
    while url:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            deployments.extend(data.get('items', []))
            url = data.get('next')
        except Exception as e:
            print(f"❌ Error fetching deployments: {e}")
            break
    
    return deployments

def get_deployment_details(dep_id: str) -> Dict[str, Any]:
    """Get full details for a specific deployment"""
    api_key = os.getenv('SC_FM_APIKEY')
    api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    
    headers = {
        'accept': 'application/json',
        'api-key': api_key
    }
    
    try:
        response = requests.get(f"{api_url}/deployments/{dep_id}", headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {'error': f"Request error: {e}"}

def get_application_details(app_id: str) -> Dict[str, Any]:
    """Get full details for a specific application"""
    api_key = os.getenv('SC_FM_APIKEY')
    api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    
    headers = {
        'accept': 'application/json',
        'api-key': api_key
    }
    
    try:
        response = requests.get(f"{api_url}/deployment-applications/{app_id}", headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {'error': f"Request error: {e}"}

def analyze_application_content(app_details: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze application content to determine if it's valid, empty, or broken"""
    result = {
        'status': 'unknown',
        'reason': '',
        'has_resources': False,
        'resource_count': 0,
        'yaml_valid': False,
        'error': None
    }
    
    if 'error' in app_details:
        result['status'] = 'error'
        result['reason'] = f"HTTP Error: {app_details['error']}"
        result['error'] = app_details['error']
        return result
    
    # Check sourceConfig field (the actual manifest content)
    source_config = app_details.get('sourceConfig')
    if not source_config:
        result['status'] = 'empty'
        result['reason'] = 'No sourceConfig field'
        return result
    
    if not isinstance(source_config, str):
        result['status'] = 'invalid'
        result['reason'] = 'sourceConfig is not a string'
        return result
    
    # Check if content contains Fleet Manager templates
    import re
    has_templates = bool(re.search(r'\{\{[^}]+\}\}', source_config))
    
    if has_templates:
        # For content with templates, do a basic structure check instead of strict YAML parsing
        # Fleet Manager handles template processing, so we'll be more lenient
        
        # Check for basic YAML structure indicators
        if 'type:' in source_config and 'metadata:' in source_config and 'spec:' in source_config:
            result['yaml_valid'] = True
            result['status'] = 'valid'
            result['reason'] = 'Contains Fleet Manager templates (structure looks valid)'
            
            # Try to extract basic info without strict parsing
            if 'resources:' in source_config or 'assets:' in source_config:
                # Count rough indicators of content
                asset_count = len(re.findall(r'- name:', source_config))
                resource_count = len(re.findall(r'type:\s*["\']?virdomain', source_config))
                
                if resource_count > 0 or asset_count > 0:
                    result['has_resources'] = resource_count > 0
                    result['resource_count'] = resource_count
                    result['reason'] = f'Contains Fleet Manager templates with {resource_count} resource(s) and {asset_count} asset(s)'
                else:
                    result['reason'] = 'Contains Fleet Manager templates (basic structure valid)'
            else:
                result['status'] = 'empty'
                result['reason'] = 'Contains templates but no resources or assets detected'
        else:
            result['status'] = 'invalid'
            result['reason'] = 'Contains templates but missing basic YAML structure'
        return result
    
    # For content without templates, do strict YAML parsing
    try:
        manifest_data = yaml.safe_load(source_config)
        result['yaml_valid'] = True
        
        if not manifest_data:
            result['status'] = 'empty'
            result['reason'] = 'Empty YAML content'
            return result
        
        # Check for resources and assets in the parsed YAML
        spec = manifest_data.get('spec', {})
        resources = spec.get('resources', [])
        assets = spec.get('assets', [])
        
        if isinstance(resources, list):
            result['resource_count'] = len(resources)
            result['has_resources'] = len(resources) > 0
        else:
            result['status'] = 'invalid'
            result['reason'] = 'Resources field is not a list'
            return result
        
        # Check if application has any content (assets or resources)
        has_assets = isinstance(assets, list) and len(assets) > 0
        has_resources = len(resources) > 0
        
        if has_resources and has_assets:
            result['status'] = 'valid'
            result['reason'] = f'{len(resources)} resource(s) and {len(assets)} asset(s) defined'
        elif has_resources:
            result['status'] = 'valid'
            result['reason'] = f'{len(resources)} resource(s) defined'
        elif has_assets:
            result['status'] = 'valid'
            result['reason'] = f'{len(assets)} asset(s) defined (no VM resources)'
        else:
            result['status'] = 'empty'
            result['reason'] = 'No resources or assets defined in manifest'
            
    except yaml.YAMLError as e:
        result['status'] = 'invalid'
        result['reason'] = f'Invalid YAML: {str(e)}'
        result['error'] = str(e)
    except Exception as e:
        result['status'] = 'invalid'
        result['reason'] = f'Parsing error: {str(e)}'
        result['error'] = str(e)
    
    return result

def find_deployments_with_broken_apps():
    """Find deployments where associated applications don't have valid manifest content"""
    
    if not os.getenv('SC_FM_APIKEY'):
        print("❌ SC_FM_APIKEY environment variable is required")
        return
    
    print("🔍 Finding deployments with broken or empty applications...")
    print("   (Checking sourceConfig field for valid manifest content)")
    print()
    
    # Get all deployments
    print("📋 Fetching all deployments...")
    deployments = get_all_deployments()
    print(f"   Found {len(deployments)} deployments")
    print()
    
    # Analyze each deployment
    broken_deployments = []
    valid_deployments = []
    
    print("🔍 Analyzing deployment-application relationships...")
    
    for i, deployment in enumerate(deployments, 1):
        dep_name = deployment.get('name', 'Unknown')
        dep_id = deployment.get('id', 'Unknown')
        dep_status = deployment.get('status', 'Unknown')
        
        print(f"[{i:2d}/{len(deployments)}] {dep_name}")
        
        # Get full deployment details
        full_deployment = get_deployment_details(dep_id)
        
        if 'error' in full_deployment:
            print(f"    ❌ ERROR getting deployment details: {full_deployment['error']}")
            continue
        
        # Extract applications from the applications field
        applications = full_deployment.get('applications', [])
        if not applications:
            print(f"    ⚠️  No applications referenced")
            continue
        
        print(f"    📋 References {len(applications)} application(s)")
        
        # Check each application
        deployment_issues = []
        all_apps_valid = True
        
        for app_ref in applications:
            app_id = app_ref.get('id')
            app_name = app_ref.get('name', 'Unknown')
            
            if not app_id:
                continue
            
            print(f"      🔗 Checking app: {app_name}")
            
            # Get application details
            app_details = get_application_details(app_id)
            
            # Analyze application content
            analysis = analyze_application_content(app_details)
            
            print(f"        Status: {analysis['status'].upper()} - {analysis['reason']}")
            
            if analysis['status'] != 'valid':
                all_apps_valid = False
                deployment_issues.append({
                    'app_id': app_id,
                    'app_name': app_name,
                    'analysis': analysis
                })
        
        # Categorize deployment
        if all_apps_valid:
            valid_deployments.append({
                'deployment': full_deployment,
                'applications': applications
            })
            print(f"    ✅ All applications valid")
        else:
            broken_deployments.append({
                'deployment': full_deployment,
                'applications': applications,
                'issues': deployment_issues
            })
            print(f"    ❌ Has {len(deployment_issues)} problematic application(s)")
    
    print()
    print("=" * 80)
    print("📊 DEPLOYMENT APPLICATION HEALTH SUMMARY")
    print("=" * 80)
    
    print(f"✅ Deployments with valid applications: {len(valid_deployments)}")
    print(f"❌ Deployments with broken/empty applications: {len(broken_deployments)}")
    print()
    
    if broken_deployments:
        print("❌ DEPLOYMENTS WITH PROBLEMATIC APPLICATIONS:")
        print()
        
        for dep_info in broken_deployments:
            dep = dep_info['deployment']
            issues = dep_info['issues']
            
            print(f"   🚨 Deployment: {dep.get('name', 'Unknown')}")
            print(f"      ID: {dep.get('id')}")
            print(f"      Status: {dep.get('status', 'Unknown')}")
            print(f"      Problematic applications:")
            
            for issue in issues:
                analysis = issue['analysis']
                print(f"        - {issue['app_name']} ({issue['app_id']})")
                print(f"          Status: {analysis['status']} - {analysis['reason']}")
                if analysis.get('error'):
                    print(f"          Error: {analysis['error']}")
            
            print()
    
    # Summary by application status
    print("📊 SUMMARY BY APPLICATION STATUS:")
    status_counts = {}
    
    for dep_info in broken_deployments:
        for issue in dep_info['issues']:
            status = issue['analysis']['status']
            status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f"   {status.upper()}: {count} applications")
    
    print()
    print("💡 RECOMMENDATIONS:")
    if broken_deployments:
        print(f"   - {len(broken_deployments)} deployments have applications with issues")
        print("   - These applications need to be fixed or cleaned up")
        print("   - The UI shows 'nothing' for these applications because they lack valid content")
    
    if status_counts.get('error', 0) > 0:
        print(f"   - {status_counts['error']} applications return server errors and need immediate attention")
    
    if status_counts.get('invalid', 0) > 0:
        print(f"   - {status_counts['invalid']} applications have invalid YAML and need fixing")
    
    if status_counts.get('empty', 0) > 0:
        print(f"   - {status_counts['empty']} applications are truly empty (no assets or resources) and may be candidates for cleanup")
    
    print()
    print("=" * 80)
    print("📋 QUICK REFERENCE: DEPLOYMENTS TO CHECK")
    print("=" * 80)
    
    if broken_deployments:
        # Group by problem type
        error_deployments = []
        invalid_deployments = []
        empty_deployments = []
        
        for dep_info in broken_deployments:
            dep = dep_info['deployment']
            issues = dep_info['issues']
            dep_name = dep.get('name', 'Unknown')
            
            for issue in issues:
                app_name = issue['app_name']
                status = issue['analysis']['status']
                
                if status == 'error':
                    error_deployments.append(f"{dep_name} → {app_name}")
                elif status == 'invalid':
                    invalid_deployments.append(f"{dep_name} → {app_name}")
                elif status == 'empty':
                    empty_deployments.append(f"{dep_name} → {app_name}")
        
        # Print grouped results
        if error_deployments:
            print("🚨 BROKEN RUNNING DEPLOYMENTS (Server Errors):")
            for item in error_deployments:
                print(f"  {item}")
            print()
        
        if invalid_deployments:
            print("⚠️  INVALID YAML APPLICATIONS:")
            for item in invalid_deployments:
                print(f"  {item}")
            print()
        
        if empty_deployments:
            print("📭 EMPTY APPLICATIONS:")
            for item in empty_deployments:
                print(f"  {item}")
            print()
        
        print("-" * 50)
        print(f"Total deployments to check: {len(broken_deployments)}")
        print(f"  - Broken Running Deployments: {len(error_deployments)}")
        print(f"  - Invalid YAML Applications: {len(invalid_deployments)}")
        print(f"  - Empty Applications: {len(empty_deployments)}")
    else:
        print("✅ No problematic deployments found!")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python3 find-deployments-with-broken-apps.py")
        print()
        print("This script finds deployments where associated applications don't have")
        print("valid manifest content. It properly checks the sourceConfig field and")
        print("handles deployments that reference multiple applications.")
        return
    
    find_deployments_with_broken_apps()

if __name__ == "__main__":
    main()

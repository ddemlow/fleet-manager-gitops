#!/usr/bin/env python3
"""
Generate a comprehensive report of all applications and their deployment relationships
Shows which deployments use each application, including cluster group information
Also identifies applications not used in any deployment
"""

import os
import sys
import requests
from typing import Dict, List, Any, Set

def get_all_deployments() -> List[Dict[str, Any]]:
    """Get all deployments with full details"""
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

def get_all_applications() -> Dict[str, Dict[str, Any]]:
    """Get all applications and return as a dict keyed by ID"""
    api_key = os.getenv('SC_FM_APIKEY')
    api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    
    headers = {
        'accept': 'application/json',
        'api-key': api_key
    }
    
    applications = {}
    url = f"{api_url}/deployment-applications?limit=50"
    
    while url:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for app in data.get('items', []):
                app_id = app.get('id')
                if app_id:
                    applications[app_id] = app
            
            url = data.get('next')
        except Exception as e:
            print(f"❌ Error fetching applications: {e}")
            break
    
    return applications

def extract_cluster_group_from_deployment(deployment: Dict[str, Any]) -> str:
    """Extract cluster group information from deployment"""
    # Try to extract cluster group from deployment name or other fields
    dep_name = deployment.get('name', '')
    
    # Look for cluster group patterns in deployment name (e.g., nginx-DDvsns)
    if '-' in dep_name:
        parts = dep_name.split('-')
        if len(parts) > 1:
            # Last part might be cluster group
            potential_cluster = parts[-1]
            # Common cluster group patterns
            if potential_cluster in ['DDvsns', 'DDGroup', 'DDLab', 'DDTest'] or potential_cluster.startswith('DD'):
                return potential_cluster
    
    # Check if there's a targetGroup field
    target_group = deployment.get('targetGroup')
    if target_group:
        return target_group
    
    # Check if there's a cluster field
    cluster = deployment.get('cluster')
    if cluster:
        return cluster
    
    return 'Unknown'

def generate_application_deployment_report():
    """Generate comprehensive application-deployment relationship report"""
    
    if not os.getenv('SC_FM_APIKEY'):
        print("❌ SC_FM_APIKEY environment variable is required")
        return
    
    print("🔍 Generating Application-Deployment Relationship Report...")
    print("   (Analyzing all applications and their deployment usage)")
    print()
    
    # Get all data
    print("📋 Fetching all applications...")
    applications = get_all_applications()
    print(f"   Found {len(applications)} applications")
    
    print("📋 Fetching all deployments...")
    deployments = get_all_deployments()
    print(f"   Found {len(deployments)} deployments")
    print()
    
    # Build application usage map
    print("🔍 Analyzing application-deployment relationships...")
    app_usage = {}  # app_id -> list of deployment info
    used_app_ids = set()
    
    for i, deployment in enumerate(deployments, 1):
        dep_name = deployment.get('name', 'Unknown')
        dep_id = deployment.get('id', 'Unknown')
        dep_status = deployment.get('status', 'Unknown')
        
        print(f"[{i:2d}/{len(deployments)}] {dep_name}")
        
        # Get full deployment details
        full_deployment = get_deployment_details(dep_id)
        
        if 'error' in full_deployment:
            print(f"    ❌ ERROR: {full_deployment['error']}")
            continue
        
        # Extract cluster group
        cluster_group = extract_cluster_group_from_deployment(full_deployment)
        
        # Get applications referenced by this deployment
        applications_refs = full_deployment.get('applications', [])
        
        for app_ref in applications_refs:
            app_id = app_ref.get('id')
            app_name = app_ref.get('name', 'Unknown')
            
            if app_id:
                used_app_ids.add(app_id)
                
                if app_id not in app_usage:
                    app_usage[app_id] = []
                
                app_usage[app_id].append({
                    'deployment_name': dep_name,
                    'deployment_id': dep_id,
                    'deployment_status': dep_status,
                    'cluster_group': cluster_group
                })
        
        if applications_refs:
            app_names = [app.get('name', 'Unknown') for app in applications_refs]
            print(f"    📋 Uses {len(applications_refs)} application(s): {', '.join(app_names)}")
        else:
            print(f"    ⚠️  No applications referenced")
    
    print()
    print("=" * 100)
    print("📊 APPLICATION-DEPLOYMENT RELATIONSHIP REPORT")
    print("=" * 100)
    
    # Report applications used in deployments
    print(f"📋 APPLICATIONS USED IN DEPLOYMENTS ({len(app_usage)} applications)")
    print()
    
    for app_id, deployment_list in sorted(app_usage.items(), key=lambda x: applications.get(x[0], {}).get('name', 'Unknown')):
        app_name = applications.get(app_id, {}).get('name', 'Unknown')
        app_source_type = applications.get(app_id, {}).get('sourceType', 'Unknown')
        
        print(f"🔧 {app_name}")
        print(f"   ID: {app_id}")
        print(f"   Source Type: {app_source_type}")
        
        # Check if this is a GitOps-managed application
        app_description = applications.get(app_id, {}).get('description') or ''
        if app_source_type == 'gitops':
            print(f"   📍 GitOps Managed: {app_description}")
        elif app_description and ('gitops' in app_description.lower() or 'github' in app_description.lower()):
            print(f"   📍 GitOps Managed: {app_description}")
        elif app_source_type == 'editor':
            print(f"   📝 Manually Created (Editor)")
        else:
            print(f"   🔗 API Created ({app_source_type})")
            
        print(f"   Used in {len(deployment_list)} deployment(s):")
        
        for dep_info in deployment_list:
            print(f"     • {dep_info['deployment_name']} ({dep_info['cluster_group']}) - {dep_info['deployment_status']}")
        
        print()
    
    # Report orphaned applications (not used in any deployment)
    orphaned_app_ids = set(applications.keys()) - used_app_ids
    orphaned_applications = [applications[app_id] for app_id in orphaned_app_ids]
    
    print("=" * 100)
    print(f"📭 ORPHANED APPLICATIONS ({len(orphaned_applications)} applications)")
    print("   (Applications not used in any deployment)")
    print()
    
    if orphaned_applications:
        for app in sorted(orphaned_applications, key=lambda x: x.get('name', 'Unknown')):
            app_name = app.get('name', 'Unknown')
            app_id = app.get('id', 'Unknown')
            app_source_type = app.get('sourceType', 'Unknown')
            app_description = app.get('description', '')
            created_at = app.get('createdAt', 'Unknown')
            
            print(f"🔧 {app_name}")
            print(f"   ID: {app_id}")
            print(f"   Source Type: {app_source_type}")
            
            # Check if this is a GitOps-managed application
            if app_source_type == 'gitops':
                print(f"   📍 GitOps Managed: {app_description}")
            elif app_description and ('gitops' in app_description.lower() or 'github' in app_description.lower()):
                print(f"   📍 GitOps Managed: {app_description}")
            elif app_source_type == 'editor':
                print(f"   📝 Manually Created (Editor)")
            else:
                print(f"   🔗 API Created ({app_source_type})")
                
            print(f"   Created: {created_at}")
            print()
    else:
        print("✅ No orphaned applications found - all applications are in use!")
    
    print("=" * 100)
    print("📊 SUMMARY STATISTICS")
    print("=" * 100)
    print(f"Total Applications: {len(applications)}")
    print(f"Applications in Use: {len(app_usage)}")
    print(f"Orphaned Applications: {len(orphaned_applications)}")
    print(f"Total Deployments: {len(deployments)}")
    
    # Cluster group summary
    cluster_groups = set()
    for deployment_list in app_usage.values():
        for dep_info in deployment_list:
            cluster_groups.add(dep_info['cluster_group'])
    
    print(f"Cluster Groups in Use: {len(cluster_groups)}")
    if cluster_groups:
        print(f"Cluster Groups: {', '.join(sorted(cluster_groups))}")
    
    print()
    print("💡 INSIGHTS:")
    if orphaned_applications:
        print(f"   - {len(orphaned_applications)} applications are not used in any deployment")
        print("   - These may be candidates for cleanup or were created for testing")
    
    # Find most used applications
    most_used = sorted(app_usage.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    if most_used:
        print("   - Most used applications:")
        for app_id, deployment_list in most_used:
            app_name = applications.get(app_id, {}).get('name', 'Unknown')
            print(f"     • {app_name}: {len(deployment_list)} deployment(s)")
    
    # Find deployments using multiple applications
    multi_app_deployments = []
    for deployment in deployments:
        full_deployment = get_deployment_details(deployment.get('id'))
        if 'error' not in full_deployment:
            app_refs = full_deployment.get('applications', [])
            if len(app_refs) > 1:
                multi_app_deployments.append({
                    'name': deployment.get('name'),
                    'app_count': len(app_refs)
                })
    
    if multi_app_deployments:
        print(f"   - {len(multi_app_deployments)} deployment(s) use multiple applications")
        for dep in multi_app_deployments[:3]:  # Show top 3
            print(f"     • {dep['name']}: {dep['app_count']} application(s)")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python3 application-deployment-report.py")
        print()
        print("This script generates a comprehensive report showing:")
        print("  - All applications and which deployments use them")
        print("  - Cluster group information for each deployment")
        print("  - Applications not used in any deployment (orphaned)")
        print("  - Summary statistics and insights")
        print()
        print("Requirements:")
        print("  - SC_FM_APIKEY environment variable must be set")
        print("  - Network access to Fleet Manager API")
        return
    
    generate_application_deployment_report()

if __name__ == "__main__":
    main()

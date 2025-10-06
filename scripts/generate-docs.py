#!/usr/bin/env python3
"""
Generate documentation from manifests
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict

def generate_application_docs():
    """Generate documentation from application manifests"""
    
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    manifest_dir = Path("manifests")
    applications = []
    
    # Find all application manifests
    for manifest_file in manifest_dir.rglob("*.yaml"):
        if manifest_file.name.startswith('.') or '/_compiled/' in str(manifest_file):
            continue
            
        try:
            with open(manifest_file, 'r') as f:
                manifest = yaml.safe_load(f)
            
            if manifest.get('type') == 'Application':
                metadata = manifest.get('metadata', {})
                spec = manifest.get('spec', {})
                
                app_info = {
                    'name': metadata.get('name', manifest_file.stem),
                    'description': metadata.get('description', ''),
                    'lifecycle': metadata.get('lifecycle', 'production'),
                    'cluster_groups': metadata.get('clusterGroups', []),
                    'file': str(manifest_file),
                    'resources': len(spec.get('resources', [])),
                    'assets': len(spec.get('assets', []))
                }
                applications.append(app_info)
        except Exception as e:
            print(f"Error processing {manifest_file}: {e}")
    
    # Generate applications documentation
    with open(docs_dir / "applications.md", 'w') as f:
        f.write("# 📦 Application Catalog\n\n")
        f.write("This document lists all applications managed by this GitOps repository.\n\n")
        
        # Group by lifecycle
        lifecycle_groups = {
            'production': [],
            'testonly': [],
            'draft': [],
            'undeploy': []
        }
        
        for app in applications:
            lifecycle = app['lifecycle']
            if lifecycle in lifecycle_groups:
                lifecycle_groups[lifecycle].append(app)
            else:
                lifecycle_groups['production'].append(app)
        
        for lifecycle, apps in lifecycle_groups.items():
            if apps:
                lifecycle_emoji = {
                    'production': '🚀',
                    'testonly': '🧪',
                    'draft': '📝',
                    'undeploy': '🗑️'
                }.get(lifecycle, '❓')
                
                f.write(f"## {lifecycle_emoji} {lifecycle.title()} Applications ({len(apps)})\n\n")
                
                for app in sorted(apps, key=lambda x: x['name']):
                    f.write(f"### {app['name']}\n")
                    f.write(f"**Description**: {app['description']}\n\n")
                    f.write(f"**Cluster Groups**: {', '.join(app['cluster_groups'])}\n\n")
                    f.write(f"**Resources**: {app['resources']} resources, {app['assets']} assets\n\n")
                    f.write(f"**Manifest**: `{app['file']}`\n\n")
                    f.write("---\n\n")
        
        f.write("## 📊 Summary\n\n")
        f.write(f"- **Total Applications**: {len(applications)}\n")
        f.write(f"- **Production**: {len(lifecycle_groups['production'])}\n")
        f.write(f"- **Test Only**: {len(lifecycle_groups['testonly'])}\n")
        f.write(f"- **Draft**: {len(lifecycle_groups['draft'])}\n")
        f.write(f"- **Undeploy**: {len(lifecycle_groups['undeploy'])}\n")

def main():
    """Main entry point"""
    print("📚 Generating application documentation...")
    generate_application_docs()
    print("✅ Documentation generated in docs/applications.md")

if __name__ == "__main__":
    main()

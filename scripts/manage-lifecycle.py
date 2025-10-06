#!/usr/bin/env python3
"""
Manifest lifecycle management utility
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from typing import List, Dict

class LifecycleManager:
    def __init__(self):
        self.manifest_dir = "manifests"
        
    def find_manifests(self, pattern: str = None) -> List[Path]:
        """Find manifest files matching pattern"""
        manifest_files = []
        
        for file_path in Path(self.manifest_dir).rglob("*.yaml"):
            if file_path.name.startswith('.') or '/_compiled/' in str(file_path):
                continue
                
            if pattern and pattern not in file_path.name:
                continue
                
            manifest_files.append(file_path)
        
        return sorted(manifest_files)
    
    def get_manifest_info(self, file_path: Path) -> Dict:
        """Get manifest information including lifecycle state"""
        try:
            with open(file_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            metadata = manifest.get('metadata', {})
            app_name = metadata.get('name', file_path.stem)
            lifecycle = self.get_lifecycle_state(manifest)
            
            return {
                'file': file_path,
                'name': app_name,
                'lifecycle': lifecycle,
                'description': metadata.get('description', ''),
                'cluster_groups': metadata.get('clusterGroups', [])
            }
        except Exception as e:
            return {
                'file': file_path,
                'name': file_path.stem,
                'lifecycle': 'unknown',
                'description': f'Error reading manifest: {e}',
                'cluster_groups': []
            }
    
    def get_lifecycle_state(self, manifest: dict) -> str:
        """Get lifecycle state from manifest"""
        metadata = manifest.get('metadata', {})
        
        # Check for explicit lifecycle state
        lifecycle = metadata.get('lifecycle', '').lower()
        if lifecycle in ['draft', 'testonly', 'production', 'undeploy']:
            return lifecycle
        
        # Check for legacy draft flag
        if metadata.get('draft', False):
            return 'draft'
        
        # Default to production
        return 'production'
    
    def set_lifecycle_state(self, file_path: Path, new_state: str) -> bool:
        """Set lifecycle state in manifest"""
        if new_state not in ['draft', 'testonly', 'production', 'undeploy']:
            print(f"❌ Invalid lifecycle state: {new_state}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            if 'metadata' not in manifest:
                manifest['metadata'] = {}
            
            manifest['metadata']['lifecycle'] = new_state
            
            with open(file_path, 'w') as f:
                yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Set lifecycle to '{new_state}' for {file_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating manifest {file_path.name}: {e}")
            return False
    
    def list_manifests(self, pattern: str = None, lifecycle_filter: str = None):
        """List manifests with their lifecycle states"""
        manifests = self.find_manifests(pattern)
        
        if not manifests:
            print(f"ℹ️  No manifests found matching pattern: {pattern}")
            return
        
        print(f"📋 Found {len(manifests)} manifests:")
        print()
        
        for file_path in manifests:
            info = self.get_manifest_info(file_path)
            
            if lifecycle_filter and info['lifecycle'] != lifecycle_filter:
                continue
            
            lifecycle_emoji = {
                'draft': '📝',
                'testonly': '🧪',
                'production': '🚀',
                'undeploy': '🗑️',
                'unknown': '❓'
            }.get(info['lifecycle'], '❓')
            
            print(f"{lifecycle_emoji} {info['name']} ({info['lifecycle']})")
            print(f"   📄 {info['file']}")
            print(f"   📝 {info['description']}")
            if info['cluster_groups']:
                print(f"   🎯 Clusters: {', '.join(info['cluster_groups'])}")
            print()
    
    def bulk_set_lifecycle(self, pattern: str, new_state: str, dry_run: bool = False):
        """Set lifecycle state for multiple manifests"""
        manifests = self.find_manifests(pattern)
        
        if not manifests:
            print(f"ℹ️  No manifests found matching pattern: {pattern}")
            return
        
        print(f"🔍 Found {len(manifests)} manifests matching '{pattern}':")
        for manifest in manifests:
            print(f"   - {manifest.name}")
        print()
        
        if dry_run:
            print(f"🧪 DRY RUN: Would set lifecycle to '{new_state}' for {len(manifests)} manifests")
            return
        
        success_count = 0
        for file_path in manifests:
            if self.set_lifecycle_state(file_path, new_state):
                success_count += 1
        
        print(f"📊 Updated {success_count}/{len(manifests)} manifests")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Manage manifest lifecycle states')
    parser.add_argument('action', choices=['list', 'set', 'bulk-set'], 
                       help='Action to perform')
    parser.add_argument('--pattern', '-p', help='File pattern to match')
    parser.add_argument('--lifecycle', '-l', 
                       choices=['draft', 'testonly', 'production', 'undeploy'],
                       help='Lifecycle state to set or filter by')
    parser.add_argument('--file', '-f', help='Specific manifest file to modify')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    manager = LifecycleManager()
    
    if args.action == 'list':
        manager.list_manifests(args.pattern, args.lifecycle)
    
    elif args.action == 'set':
        if not args.file:
            print("❌ --file required for 'set' action")
            sys.exit(1)
        if not args.lifecycle:
            print("❌ --lifecycle required for 'set' action")
            sys.exit(1)
        
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        
        manager.set_lifecycle_state(file_path, args.lifecycle)
    
    elif args.action == 'bulk-set':
        if not args.pattern:
            print("❌ --pattern required for 'bulk-set' action")
            sys.exit(1)
        if not args.lifecycle:
            print("❌ --lifecycle required for 'bulk-set' action")
            sys.exit(1)
        
        manager.bulk_set_lifecycle(args.pattern, args.lifecycle, args.dry_run)

if __name__ == "__main__":
    main()

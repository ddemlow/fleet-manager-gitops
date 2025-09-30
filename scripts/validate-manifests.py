#!/usr/bin/env python3
"""
Manifest validation script for Fleet Manager GitOps
Validates YAML syntax and structure of deployment manifests
"""

import os
import sys
import yaml
import glob
from pathlib import Path
from typing import Dict, List, Any

class ManifestValidator:
    def __init__(self):
        self.required_fields = {
            'metadata': ['name'],
            'spec': ['assets']
        }
        
        self.valid_asset_types = [
            'virtual_disk',
            'virtual_machine',
            'network',
            'storage'
        ]

    def validate_yaml_syntax(self, file_path: str) -> bool:
        """Validate YAML syntax"""
        try:
            with open(file_path, 'r') as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            print(f"❌ YAML syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False

    def validate_manifest_structure(self, manifest: Dict[str, Any], file_path: str) -> bool:
        """Validate manifest structure"""
        errors = []
        
        # Check required top-level fields
        if 'metadata' not in manifest:
            errors.append("Missing 'metadata' section")
        else:
            if 'name' not in manifest['metadata']:
                errors.append("Missing 'name' in metadata")
        
        if 'spec' not in manifest:
            errors.append("Missing 'spec' section")
        else:
            if 'assets' not in manifest['spec']:
                errors.append("Missing 'assets' in spec")
            elif not isinstance(manifest['spec']['assets'], list):
                errors.append("'assets' must be a list")
            else:
                # Validate each asset
                for i, asset in enumerate(manifest['spec']['assets']):
                    if not isinstance(asset, dict):
                        errors.append(f"Asset {i} must be a dictionary")
                        continue
                    
                    if 'name' not in asset:
                        errors.append(f"Asset {i} missing 'name'")
                    if 'type' not in asset:
                        errors.append(f"Asset {i} missing 'type'")
                    elif asset.get('type') not in self.valid_asset_types:
                        errors.append(f"Asset {i} has invalid type '{asset.get('type')}'. Valid types: {self.valid_asset_types}")
        
        if errors:
            print(f"❌ Validation errors in {file_path}:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        return True

    def validate_manifest(self, file_path: str) -> bool:
        """Validate a single manifest file"""
        print(f"🔍 Validating: {file_path}")
        
        # Check YAML syntax
        if not self.validate_yaml_syntax(file_path):
            return False
        
        # Load and validate structure
        try:
            with open(file_path, 'r') as f:
                manifest = yaml.safe_load(f)
            # Skip non-Application manifests (e.g., ContainerDefinition, RuntimeConfiguration)
            mtype = str(manifest.get('type', '')).lower() if isinstance(manifest, dict) else ''
            if mtype != 'application':
                print(f"⏭️  Skipping non-Application manifest: {file_path} (type={manifest.get('type') if isinstance(manifest, dict) else 'unknown'})")
                return True
            
            if not self.validate_manifest_structure(manifest, file_path):
                return False
            
            print(f"✅ Valid: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error validating {file_path}: {e}")
            return False

    def validate_all_manifests(self) -> bool:
        """Validate all manifest files"""
        print("🔍 Validating all manifest files...")
        
        # Find all manifest files
        manifest_files = []
        for pattern in ['manifests/**/*.yaml', 'manifests/**/*.yml', 
                       'applications/**/*.yaml', 'applications/**/*.yml']:
            manifest_files.extend(glob.glob(pattern, recursive=True))
        
        if not manifest_files:
            print("ℹ️  No manifest files found")
            return True
        
        print(f"📋 Found {len(manifest_files)} manifest files")
        
        # Validate each file
        success_count = 0
        for file_path in manifest_files:
            # Hard-skip container/runtime definition files by path
            if '/containers/' in file_path:
                print(f"⏭️  Skipping non-Application manifest: {file_path} (by path)")
                success_count += 1
                continue
            if self.validate_manifest(file_path):
                success_count += 1
        
        print(f"\n📊 Validation Summary:")
        print(f"✅ Valid: {success_count}")
        print(f"❌ Invalid: {len(manifest_files) - success_count}")
        
        return success_count == len(manifest_files)

if __name__ == "__main__":
    validator = ManifestValidator()
    success = validator.validate_all_manifests()
    sys.exit(0 if success else 1)

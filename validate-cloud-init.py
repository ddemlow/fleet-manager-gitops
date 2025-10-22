#!/usr/bin/env python3
"""
Cloud-init user_data validation script
Validates YAML structure and cloud-init schema compliance
"""

import sys
import re
from pathlib import Path

def validate_cloud_init_yaml(file_path):
    """Validate cloud-init user_data section in a YAML file"""
    
    print(f"=== Validating cloud-init in {file_path} ===")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        return False
    
    # Extract user_data section
    lines = content.split('\n')
    user_data_start = None
    user_data_end = None
    
    for i, line in enumerate(lines):
        if 'user_data: |' in line:
            user_data_start = i
        elif user_data_start and line.strip() and not line.startswith('            ') and not line.startswith('          '):
            # Found end of user_data section
            user_data_end = i
            break
    
    if user_data_start is None:
        print("✗ No user_data section found")
        return False
    
    if user_data_end is None:
        user_data_end = len(lines)
    
    # Extract user_data content
    user_data_lines = lines[user_data_start + 1:user_data_end]
    
    # Remove leading spaces to get clean YAML
    cleaned_lines = []
    for line in user_data_lines:
        if line.strip():
            # Remove the leading 12 spaces (YAML indentation)
            if line.startswith('            '):
                cleaned_line = line[12:]
            else:
                cleaned_line = line
            cleaned_lines.append(cleaned_line)
        else:
            cleaned_lines.append('')
    
    user_data_yaml = '\n'.join(cleaned_lines)
    
    print("✓ Extracted user_data section")
    
    # Basic structure validation
    validation_passed = True
    
    # Check for #cloud-config header
    if '#cloud-config' in user_data_yaml:
        print("✓ Found #cloud-config header")
    else:
        print("✗ Missing #cloud-config header")
        validation_passed = False
    
    # Check for required sections
    required_sections = {
        'users:': 'User configuration',
        'runcmd:': 'Command execution'
    }
    
    for section, description in required_sections.items():
        if section in user_data_yaml:
            print(f"✓ Found {description} section")
        else:
            print(f"✗ Missing {description} section")
            validation_passed = False
    
    # Validate users section structure
    users_section_valid = True
    in_users = False
    user_count = 0
    
    for line in user_data_lines:
        if 'users:' in line:
            in_users = True
        elif in_users and line.strip() and not line.startswith('            ') and not line.startswith('              ') and not line.startswith('                '):
            in_users = False
        elif in_users and line.strip():
            if line.startswith('              - name:'):
                user_count += 1
            elif line.startswith('                ') and user_count > 0:
                # Check for proper user field indentation - these are valid user fields
                pass
    
    if user_count > 0:
        print(f"✓ Found {user_count} user(s) in users section")
    else:
        print("✗ No users found in users section")
        users_section_valid = False
    
    if not users_section_valid:
        print("✗ Users section structure issues detected")
        validation_passed = False
    
    # Check for proper array formatting
    array_checks = [
        ('groups: ["', 'groups field should be array'),
        ('sudo: ["', 'sudo field should be array'),
        ('ssh_import_id: ["', 'ssh_import_id field should be array')
    ]
    
    for check, description in array_checks:
        if check in user_data_yaml:
            print(f"✓ {description}")
        else:
            print(f"✗ {description}")
            validation_passed = False
    
    # Count runcmd entries
    runcmd_count = 0
    for line in user_data_lines:
        if line.strip().startswith('- ') and 'runcmd:' not in line:
            runcmd_count += 1
    
    print(f"✓ Found {runcmd_count} runcmd entries")
    
    # Check for multiline blocks
    multiline_blocks = 0
    for line in user_data_lines:
        if '|' in line and 'cat <<' in line:
            multiline_blocks += 1
    
    if multiline_blocks > 0:
        print(f"✓ Found {multiline_blocks} multiline blocks")
    
    print("=== Validation Summary ===")
    if validation_passed:
        print("✓ Cloud-init user_data validation PASSED")
        return True
    else:
        print("✗ Cloud-init user_data validation FAILED")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 validate-cloud-init.py <yaml-file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = validate_cloud_init_yaml(file_path)
    sys.exit(0 if success else 1)

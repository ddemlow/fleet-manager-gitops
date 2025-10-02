#!/usr/bin/env python3
"""
Restore a container application by compiling and deploying the container definition
"""

import os
import sys
import yaml
import subprocess
import tempfile
import shutil

def restore_container_application(app_name: str):
    """Restore a container application by compiling its definition"""
    
    container_file = f"manifests/containers/{app_name}.container.yaml"
    
    if not os.path.exists(container_file):
        print(f"❌ Container definition not found: {container_file}")
        return False
    
    print(f"🔍 Found container definition: {container_file}")
    
    # Create a temporary directory for compilation
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Copy the container file to temp directory
        temp_container = os.path.join(temp_dir, f"{app_name}.container.yaml")
        shutil.copy2(container_file, temp_container)
        
        # Try to compile using the compile script
        print(f"🔧 Compiling container definition...")
        
        # Change to temp directory and run compilation
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # Run the compile script
            result = subprocess.run([
                'python3', f'{original_dir}/scripts/compile_manifests.py'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"❌ Compilation failed:")
                print(result.stdout)
                print(result.stderr)
                return False
            
            # Find the compiled manifest
            compiled_dir = os.path.join(temp_dir, 'manifests', '_compiled')
            if os.path.exists(compiled_dir):
                compiled_files = [f for f in os.listdir(compiled_dir) if f.endswith('.yaml')]
                if compiled_files:
                    compiled_file = os.path.join(compiled_dir, compiled_files[0])
                    print(f"✅ Compiled manifest: {compiled_files[0]}")
                    
                    # Copy compiled manifest to the main manifests directory
                    target_compiled = f"{original_dir}/manifests/_compiled/{compiled_files[0]}"
                    os.makedirs(os.path.dirname(target_compiled), exist_ok=True)
                    shutil.copy2(compiled_file, target_compiled)
                    
                    print(f"📄 Copied to: {target_compiled}")
                    
                    # Now restore using the cleanup script
                    print(f"🔄 Restoring application definition...")
                    restore_result = subprocess.run([
                        f'{original_dir}/scripts/cleanup.sh', target_compiled, '0'
                    ], capture_output=True, text=True)
                    
                    if restore_result.returncode == 0:
                        print(f"✅ Application '{app_name}' restored successfully!")
                        return True
                    else:
                        print(f"❌ Restoration failed:")
                        print(restore_result.stdout)
                        print(restore_result.stderr)
                        return False
                else:
                    print(f"❌ No compiled files found in {compiled_dir}")
                    return False
            else:
                print(f"❌ Compiled directory not found: {compiled_dir}")
                return False
                
        finally:
            os.chdir(original_dir)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 restore-container-app.py <app-name>")
        print("Example: python3 restore-container-app.py nginx3")
        sys.exit(1)
    
    app_name = sys.argv[1]
    
    print(f"🧹 Restoring container application: {app_name}")
    
    success = restore_container_application(app_name)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

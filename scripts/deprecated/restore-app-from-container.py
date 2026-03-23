#!/usr/bin/env python3
"""
Restore application definition from container definition without full compilation
"""

import os
import sys
import yaml
import requests
import json

def restore_app_from_container(app_name: str):
    """Restore application definition using container definition as template"""
    
    container_file = f"manifests/containers/{app_name}.container.yaml"
    
    if not os.path.exists(container_file):
        print(f"❌ Container definition not found: {container_file}")
        return False
    
    print(f"🔍 Found container definition: {container_file}")
    
    fm_api_key = os.getenv('SC_FM_APIKEY')
    fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    
    if not fm_api_key:
        print("❌ SC_FM_APIKEY environment variable is required")
        return False
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'api-key': fm_api_key,
        'user-agent': 'fleet-manager-restore/1.0'
    }
    
    # Read the container definition
    with open(container_file, 'r') as f:
        container_data = yaml.safe_load(f)
    
    # Create a basic application manifest from the container
    # This is a simplified version that should work for most containers
    app_manifest = {
        'version': '1',
        'type': 'Application',
        'metadata': {
            'name': app_name,
            'clusterGroups': ['DDvsns'],
            'labels': ['container', 'restored']
        },
        'spec': {
            'assets': [
                {
                    'name': 'rootdisk',
                    'type': 'virtual_disk',
                    'format': 'raw',
                    'url': 'https://pm-westfield.s3.us-east-2.amazonaws.com/openSUSE-MicroOS.x86_64-ContainerHost-OpenStack-Cloud.raw'
                }
            ],
            'resources': [
                {
                    'type': 'virdomain',
                    'name': app_name,
                    'spec': {
                        'cpu': 2,
                        'memory': '2Gi',
                        'storage_devices': [
                            {
                                'name': 'bootdisk',
                                'type': 'virtio_disk',
                                'source': 'rootdisk',
                                'boot': 1,
                                'capacity': '40Gi'
                            }
                        ],
                        'network_devices': [
                            {
                                'name': 'eth0',
                                'type': 'virtio'
                            }
                        ],
                        'tags': ['container', 'restored'],
                        'state': 'running',
                        'cloud_init_data': {
                            'user_data': '''#cloud-config
ssh_pwauth: true
disable_root: false
users:
  - name: user
    groups: [wheel]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh-authorized-keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDihWWhjoPj8KVLtdLDwNJQ71zi9An0iUFjefRWu2Eju ddemlow@scalecomputing.com
      - github:davedemlow
chpasswd:
  list: |
    user:password
  expire: false
write_files: []
runcmd:
  - systemctl enable podman.socket
  - systemctl enable --now podman-auto-update.timer
  - mkdir -p /etc/containers/systemd
  - mkdir -p /var/edge/www
  - |
    cat <<'EOF' > /var/edge/www/index.html
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Welcome - {{clusterName}}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          :root { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial, sans-serif; }
          body { margin: 2rem; line-height: 1.5; }
          .wrap { max-width: 52rem; }
          h1 { margin-bottom: .25rem; }
          .meta { color: #555; margin-bottom: 1rem; }
          code { background: #f4f4f4; padding: .125rem .375rem; border-radius: .25rem; }
          .card { border: 1px solid #e6e6e6; border-radius: .5rem; padding: 1rem; }
        </style>
      </head>
      <body>
        <div class="wrap">
          <h1>Welcome to nginx on MicroOS - Scale Computing Runtime Demo</h1>
          <p class="meta">This node is serving a custom page from a bind-mounted volume.</p>
          <div class="card">
            <p><strong>Cluster:</strong> <code>{{clusterName}}</code></p>
            <p><strong>Cluster ID:</strong> <code>{{clusterId}}</code></p>
          </div>
          <p>Content path: <code>/var/edge/www/index.html</code> → mounted into <code>/usr/share/nginx/html</code>.</p>
        </div>
      </body>
    </html>
    EOF
    chmod 0644 /var/edge/www/index.html
  - |
    cat <<'EOF' > /etc/containers/systemd/nginx.container
    [Container]
    Image=docker.io/library/nginx:1.27-alpine
    PublishPort=80:80
    Volume=/var/edge/www:/usr/share/nginx/html:Z
    Environment=NGINX_ENTRYPOINT_QUIET_LOGS=1
    Label=io.containers.autoupdate=registry

    [Install]
    WantedBy=multi-user.target
    EOF
  - systemctl daemon-reload
  - systemctl restart nginx.service
  - transactional-update --non-interactive pkg install qemu-guest-agent || true
  - mkdir -p /etc/systemd/system
  - |
    cat <<'EOF' > /etc/systemd/system/enable-qemu-guest-agent.service
    [Unit]
    Description=Enable qemu-guest-agent post-reboot
    After=multi-user.target

    [Service]
    Type=oneshot
    ExecStart=/usr/bin/systemctl enable --now qemu-guest-agent.service
    RemainAfterExit=yes

    [Install]
    WantedBy=multi-user.target
    EOF
  - systemctl enable enable-qemu-guest-agent.service || true
  - mkdir -p /etc/systemd/system/qemu-guest-agent.service.d
  - |
    cat <<'EOF' > /etc/systemd/system/qemu-guest-agent.service.d/override.conf
    [Unit]
    Requires=
    After=
    EOF
  - reboot
''',
                            'meta_data': 'dsmode: local\nlocal-hostname: "nginx3"'
                        }
                    }
                }
            ]
        }
    }
    
    print(f"🔄 Restoring application definition for: {app_name}")
    
    # Find the application ID - handle pagination
    try:
        # Try to get all applications with pagination
        all_applications = []
        url = f"{fm_api_url}/deployment-applications?limit=50"
        
        while url:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"❌ Failed to get deployment applications: {response.status_code}")
                return False
            
            data = response.json()
            applications = data.get('items', [])
            all_applications.extend(applications)
            
            # Check for next page
            url = data.get('next')
        
        app_id = None
        for app in all_applications:
            if app.get('name') == app_name:
                app_id = app.get('id')
                break
        
        if not app_id:
            print(f"❌ Application '{app_name}' not found")
            return False
        
        print(f"🔍 Found application ID: {app_id}")
        
        # Update the application definition
        response = requests.put(
            f"{fm_api_url}/deployment-applications/{app_id}",
            headers=headers,
            data=json.dumps(app_manifest),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Application definition restored successfully")
            return True
        else:
            print(f"❌ Failed to restore application definition: {response.status_code}")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error restoring application definition: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 restore-app-from-container.py <app-name>")
        print("Example: python3 restore-app-from-container.py nginx3")
        sys.exit(1)
    
    app_name = sys.argv[1]
    
    print(f"🧹 Restoring application from container definition: {app_name}")
    
    success = restore_app_from_container(app_name)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
import yaml
import glob
from pathlib import Path


def load_yaml(path: str):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def to_application(container_def: dict, runtime_def: dict) -> dict:
    name = container_def.get('metadata', {}).get('name')
    md = container_def.get('metadata', {})
    runtime = runtime_def.get('spec', {}).get('runtime', {}) if runtime_def else {}
    network = runtime_def.get('spec', {}).get('network', []) if runtime_def else []
    containers = container_def.get('spec', {}).get('containers', [])
    content = container_def.get('spec', {}).get('content', [])

    vcpus = runtime.get('vcpus', 2)
    memory = runtime.get('memory', '2Gi')
    disk_cfg = runtime.get('disk', {})
    disk_name = disk_cfg.get('name', 'rootdisk')
    disk_capacity = disk_cfg.get('capacity', '40Gi')
    disk_image = disk_cfg.get('imageUrl') or disk_cfg.get('url')
    disk_format = disk_cfg.get('format', 'raw')

    # Map simplified to Application
    tags = list(md.get('labels') or [])

    # Merge cloudInit from runtime + container convenience fields
    merged_cloud_init = {}
    rc_cloud = (runtime_def.get('spec', {}).get('cloudInit') if runtime_def else {}) or {}
    ct_cloud = (container_def.get('spec', {}).get('cloudInit') if container_def else {}) or {}
    # Allow top-level users/chpasswd in container spec
    if container_def.get('spec', {}).get('users'):
        ct_cloud['users'] = container_def['spec']['users']
    if container_def.get('spec', {}).get('chpasswd'):
        ct_cloud['chpasswd'] = container_def['spec']['chpasswd']
    # Shallow-merge with runtime taking precedence for ssh settings
    merged_cloud_init.update(ct_cloud)
    merged_cloud_init.update(rc_cloud)

    app = {
        'version': '1',
        'type': 'Application',
        'metadata': {
            'name': name,
            'clusterGroups': md.get('clusterGroups') or [],
            'labels': md.get('labels') or [],
        },
        'spec': {
            'assets': [
                {
                    'name': disk_name,
                    'type': 'virtual_disk',
                    'format': disk_format,
                    'url': disk_image,
                }
            ],
            'resources': [
                {
                    'type': 'virdomain',
                    'name': f"{name}-domain",
                    'spec': {
                        'cpu': vcpus,
                        'memory': memory,
                        'storage_devices': [
                            {
                                'name': 'bootdisk',
                                'type': 'virtio_disk',
                                'source': disk_name,
                                'boot': 1,
                                'capacity': disk_capacity
                            }
                        ],
                        'network_devices': [
                            {'name': n.get('name', 'eth0'), 'type': n.get('type', 'virtio')}
                            for n in (network or [{'name': 'eth0', 'type': 'virtio'}])
                        ],
                        'tags': tags,
                        'state': 'running',
                        'cloud_init_data': {
                            'user_data': _container_quadlet_user_data(containers, content, merged_cloud_init),
                            'meta_data': _meta_data(name)
                        }
                    }
                }
            ]
        }
    }
    return app


def _container_quadlet_user_data(containers: list, content: list, cloud_init: dict | None = None) -> str:
    lines = [
        '#cloud-config',
    ]

    # Optional cloud-init basics (users, ssh)
    ci = cloud_init or {}
    ssh = ci.get('ssh') or {}
    if 'passwordAuth' in ssh:
        lines.append(f"ssh_pwauth: {'true' if ssh.get('passwordAuth') else 'false'}")
    if 'disableRoot' in ssh:
        lines.append(f"disable_root: {'true' if ssh.get('disableRoot') else 'false'}")

    # Support users either in cloudInit.users or top-level spec.users for convenience
    users = (ci.get('users') if isinstance(ci.get('users'), list) else [])
    if users:
        lines.append('users:')
        for u in users:
            lines.append(f"  - name: {u.get('name')}")
            if u.get('groups'):
                # render list inline
                groups = ", ".join([str(g) for g in u.get('groups')])
                lines.append(f"    groups: [{groups}]")
            if u.get('sudo'):
                lines.append(f"    sudo: {u.get('sudo')}")
            if u.get('shell'):
                lines.append(f"    shell: {u.get('shell')}")
            aks = u.get('sshAuthorizedKeys') or []
            if aks:
                lines.append('    ssh-authorized-keys:')
                for key in aks:
                    lines.append(f"      - {key}")

    # Also read top-level users from the container def (legacy convenience)
    # This function receives only the merged cloudInit dict; top-level users/chpasswd
    # are merged by caller into cloudInit before invoking this function.

    # chpasswd support
    chpwd = ci.get('chpasswd')
    if isinstance(chpwd, dict):
        lines.append('chpasswd:')
        if 'list' in chpwd:
            lines.append('  list: |')
            for ln in str(chpwd.get('list')).splitlines():
                lines.append(f"    {ln}")
        if 'expire' in chpwd:
            lines.append(f"  expire: {'true' if chpwd.get('expire') else 'false'}")

    # Files and commands
    lines += [
        'write_files: []',
        'runcmd:',
    ]

    # Base system prep
    lines.append('  - systemctl enable podman.socket')
    lines.append('  - systemctl enable --now podman-auto-update.timer')
    lines.append('  - mkdir -p /etc/containers/systemd')
    lines.append('  - mkdir -p /var/edge/www')

    for item in content or []:
        path = item.get('path')
        mode = item.get('mode', '0644')
        data = item.get('data', '')
        lines.append('  - |')
        lines.append(f"    cat <<'EOF' > {path}")
        lines.extend([f"    {ln}" for ln in data.splitlines()])
        lines.append('    EOF')
        lines.append(f"    chmod {mode} {path}")

    for c in containers or []:
        name = c.get('name', 'app')
        image = c.get('image')
        ports = c.get('ports', [])
        mounts = c.get('mounts', [])
        env = c.get('env', [])
        unit_path = f"/etc/containers/systemd/{name}.container"
        lines.append('  - |')
        lines.append(f"    cat <<'EOF' > {unit_path}")
        lines.append('    [Container]')
        lines.append(f"    Image={image}")
        for p in ports:
            lines.append(f"    PublishPort={p}")
        for m in mounts:
            hp = m.get('hostPath')
            mp = m.get('mountPath')
            sel = ':Z' if m.get('selinuxRelabel') else ''
            lines.append(f"    Volume={hp}:{mp}{sel}")
        for e in env:
            lines.append(f"    Environment={e.get('name')}={e.get('value')}")
        lines.append('    Label=io.containers.autoupdate=registry')
        lines.append('')
        lines.append('    [Install]')
        lines.append('    WantedBy=multi-user.target')
        lines.append('    EOF')

    lines.append('  - systemctl daemon-reload')
    for c in containers or []:
        lines.append(f"  - systemctl restart {c.get('name','app')}.service")

    # Optional: install qemu-guest-agent transactionally and enable next boot
    lines.append('  - transactional-update --non-interactive pkg install qemu-guest-agent || true')
    lines.append('  - mkdir -p /etc/systemd/system')
    lines.append('  - |')
    lines.append("    cat <<'EOF' > /etc/systemd/system/enable-qemu-guest-agent.service")
    lines.append('    [Unit]')
    lines.append('    Description=Enable qemu-guest-agent post-reboot')
    lines.append('    After=multi-user.target')
    lines.append('')
    lines.append('    [Service]')
    lines.append('    Type=oneshot')
    lines.append('    ExecStart=/usr/bin/systemctl enable --now qemu-guest-agent.service')
    lines.append('    RemainAfterExit=yes')
    lines.append('')
    lines.append('    [Install]')
    lines.append('    WantedBy=multi-user.target')
    lines.append('    EOF')
    lines.append('  - systemctl enable enable-qemu-guest-agent.service || true')
    # Match nginx-deployment: create override dir/file and reboot
    lines.append('  - mkdir -p /etc/systemd/system/qemu-guest-agent.service.d')
    lines.append('  - |')
    lines.append("    cat <<'EOF' > /etc/systemd/system/qemu-guest-agent.service.d/override.conf")
    lines.append('    [Unit]')
    lines.append('    Requires=')
    lines.append('    After=')
    lines.append('    EOF')
    lines.append('  - reboot')

    return "\n".join(lines) + "\n"


def _meta_data(name: str) -> str:
    hostname = name or 'vm'
    return f"dsmode: local\nlocal-hostname: \"{hostname}\"\n"


def main():
    compile_output_dir = Path(os.getenv('COMPILE_OUTPUT_DIR', 'manifests/_compiled'))
    ensure_dir(compile_output_dir)

    container_files = glob.glob('manifests/containers/*.container.yaml')
    if not container_files:
        print('ℹ️  No container definitions found to compile')
        return 0

    compiled = 0
    for cfile in container_files:
        name = Path(cfile).stem.replace('.container', '')
        # Prefer a generic runtime.yaml, fallback to per-app runtime file
        generic_runtime = 'manifests/containers/runtime_configuration/runtime.yaml'
        per_app_runtime = f'manifests/containers/runtime_configuration/{name}.runtime.yaml'
        rfile = generic_runtime if os.path.exists(generic_runtime) else per_app_runtime
        container_def = load_yaml(cfile)
        runtime_def = load_yaml(rfile) if os.path.exists(rfile) else {}
        app = to_application(container_def, runtime_def)
        out_path = compile_output_dir / f'{name}.yaml'
        with open(out_path, 'w') as f:
            yaml.safe_dump(app, f, sort_keys=False)
        print(f"🧩 Compiled {name} → {out_path}")
        compiled += 1

    print(f"📦 Compiled {compiled} manifest(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())



#!/usr/bin/env python3
"""
GitOps deployment script for Fleet Manager
Automatically deploys manifests from GitHub to Fleet Manager via MCP server
"""

import os
import sys
import yaml
import json
import requests
import glob
from pathlib import Path
from typing import Dict, List, Any

class FleetManagerGitOps:
    def __init__(self):
        self.fm_api_key = os.getenv('SC_FM_APIKEY')
        self.fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
        # Default cluster group name can be overridden by manifest content or env
        self.default_cluster_group_name = os.getenv('CLUSTER_GROUP_NAME', 'DDvsns')
        
        if not self.fm_api_key:
            raise ValueError("SC_FM_APIKEY environment variable is required")
            
        # Fleet Manager API headers
        # Use API key header appropriate for server-to-server requests
        self.headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': self.fm_api_key,
            'user-agent': 'fleet-manager-gitops/1.0 (+github-actions)'
        }

    def _debug_fail(self, resp: requests.Response, context: str) -> None:
        print(f"❌ {context} (status: {resp.status_code})")
        try:
            print(f"Response JSON: {resp.json()}")
        except Exception:
            print(f"Response Text: {resp.text[:500]}")

    @staticmethod
    def _normalize(obj: Any) -> str:
        """Return a stable JSON string for semantic equality checks."""
        try:
            return json.dumps(obj, sort_keys=True, separators=(",", ":"))
        except Exception:
            return str(obj)

    @staticmethod
    def _normalize_manifest_structure(manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize fields to match API expectations (e.g., labels list)."""
        if not isinstance(manifest, dict):
            return manifest
        md = manifest.get('metadata') or {}
        if isinstance(md, dict):
            labels = md.get('labels')
            # API expects a list for labels; accept dict in YAML and convert
            if isinstance(labels, dict):
                # Convert to list of key/value objects
                md['labels'] = [{ 'key': k, 'value': v } for k, v in labels.items()]
                manifest['metadata'] = md
        return manifest

    def get_changed_files(self) -> List[str]:
        """Get list of changed manifest files"""
        changed_files = []
        process_all = os.getenv('PROCESS_ALL_MANIFESTS', '').lower() in ('1', 'true', 'yes')
        
        # 0) Prefer GitHub Actions event payload when available (push events contain changed files)
        try:
            event_path = os.getenv('GITHUB_EVENT_PATH')
            if event_path and os.path.exists(event_path):
                with open(event_path, 'r') as f:
                    event = json.load(f)
                # Push event: aggregate added/modified files across commits
                if event.get('commits'):
                    gh_candidates: List[str] = []
                    for c in event.get('commits') or []:
                        gh_candidates.extend(c.get('added') or [])
                        gh_candidates.extend(c.get('modified') or [])
                    changed_files = [
                        f for f in gh_candidates if f and 
                        f.startswith(('manifests/', 'applications/')) and 
                        f.endswith(('.yaml', '.yml'))
                    ]
                    if changed_files:
                        return sorted(set(changed_files))
                # Some push events only populate head_commit
                head = event.get('head_commit') or {}
                if head:
                    gh_candidates = (head.get('added') or []) + (head.get('modified') or [])
                    changed_files = [
                        f for f in gh_candidates if f and 
                        f.startswith(('manifests/', 'applications/')) and 
                        f.endswith(('.yaml', '.yml'))
                    ]
                    if changed_files:
                        return sorted(set(changed_files))
        except Exception:
            pass

        # Prefer using git to detect changes
        try:
            import subprocess
            # Ensure we are in a git repo and HEAD exists
            in_repo = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True
            ).stdout.strip() == 'true'
            has_head = subprocess.run(
                ['git', 'rev-parse', '--verify', 'HEAD'], capture_output=True, text=True
            ).returncode == 0

            diff_last_commits = []
            diff_index_vs_head = []
            diff_worktree_vs_head = []

            if in_repo and has_head:
                # 1) Changes between last two commits (CI typical)
                diff_last_commits = subprocess.run(
                    ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
                    capture_output=True, text=True, check=True
                ).stdout.strip().split('\n')

                # 2) Staged changes vs HEAD (local dev)
                diff_index_vs_head = subprocess.run(
                    ['git', 'diff', '--cached', '--name-only', 'HEAD'],
                    capture_output=True, text=True, check=True
                ).stdout.strip().split('\n')

                # 3) Unstaged working tree changes vs HEAD (local dev)
                diff_worktree_vs_head = subprocess.run(
                    ['git', 'diff', '--name-only', 'HEAD'],
                    capture_output=True, text=True, check=True
                ).stdout.strip().split('\n')

            candidates = [
                *diff_last_commits,
                *diff_index_vs_head,
                *diff_worktree_vs_head,
            ]

            changed_files = [
                f for f in candidates if f and 
                f.startswith(('manifests/', 'applications/')) and 
                f.endswith(('.yaml', '.yml'))
            ]
        except Exception:
            # If git is unavailable or repo has no history, process all manifests
            pass

        # If still nothing, only scan all manifests if explicitly requested
        if not changed_files and process_all:
            changed_files = (
                glob.glob('manifests/**/*.yaml', recursive=True) +
                glob.glob('manifests/**/*.yml', recursive=True) +
                glob.glob('applications/**/*.yaml', recursive=True) +
                glob.glob('applications/**/*.yml', recursive=True)
            )
        
        return sorted(set(changed_files))

    def load_manifest(self, file_path: str) -> Dict[str, Any]:
        """Load and parse a YAML manifest file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return None

    def find_deployment_application(self, app_name: str) -> str:
        """Find existing deployment application ID by name"""
        app = self.get_deployment_application(app_name)
        return app.get('id') if app else None

    def get_deployment_application(self, app_name: str) -> Dict[str, Any]:
        """Return full deployment application object by name (or None)"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployment-applications?limit=200",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            for app in response.json().get('items', []):
                if app.get('name') == app_name:
                    return app
            return None
        except Exception as e:
            print(f"❌ Error getting application {app_name}: {e}")
            return None

    def create_deployment_application(self, app_name: str, manifest: str) -> str:
        """Create a new deployment application (use POST)."""
        try:
            payload = {
                "name": app_name,
                "sourceType": "editor",  # Use "editor" like in your example
                "sourceConfig": manifest
            }
            
            # Create without UUID uses POST; PUT with UUID is for updates
            response = requests.post(
                f"{self.fm_api_url}/deployment-applications",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, "Create application POST /deployment-applications")
                response.raise_for_status()
            
            data = response.json()
            app_id = data.get('id')
            print(f"✅ Created new application: {app_name} (ID: {app_id})")
            return app_id
            
        except Exception as e:
            print(f"❌ Error creating application {app_name}: {e}")
            return None

    def update_deployment_application(self, app_id: str, app_name: str, manifest: str) -> bool:
        """Update an existing deployment application"""
        try:
            payload = {
                "name": app_name,
                "sourceType": "editor",  # Use "editor" like in your example
                "sourceConfig": manifest
            }
            
            response = requests.put(
                f"{self.fm_api_url}/deployment-applications/{app_id}",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, f"Update application PUT /deployment-applications/{app_id}")
                response.raise_for_status()
            
            print(f"✅ Updated application: {app_name} (ID: {app_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error updating application {app_name}: {e}")
            return False

    def list_cluster_groups(self) -> Dict[str, str]:
        """Return a mapping of cluster group name -> id"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/cluster-groups?limit=200",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            name_to_id = {}
            for group in response.json().get('items', []):
                name = group.get('name')
                gid = group.get('id')
                if name and gid:
                    name_to_id[name] = gid
            return name_to_id
        except Exception as e:
            print(f"❌ Error listing cluster groups: {e}")
            return {}

    def find_deployment(self, name: str) -> str:
        """Find an existing deployment id by name"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployments?limit=200",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            for dep in response.json().get('items', []):
                if dep.get('name') == name:
                    return dep.get('id')
            return None
        except Exception as e:
            print(f"❌ Error finding deployment {name}: {e}")
            return None

    def create_deployment(self, app_id: str, name: str, cluster_group_id: str, app_name: str, app_version: str = "1") -> str:
        """Create a new deployment that binds an application to a single cluster group"""
        try:
            payload = {
                "name": name,
                "applicationId": app_id,
                # API expects a single targetGroup field, not an array of targets
                "targetGroup": cluster_group_id,
                # Applications array is required; include app id/name/version and strategy
                "applications": [
                    {
                        "id": app_id,
                        "name": app_name,
                        "version": app_version,
                        "strategy": "manual"
                    }
                ]
            }
            response = requests.post(
                f"{self.fm_api_url}/deployments",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, "Create deployment POST /deployments")
                response.raise_for_status()
            dep_id = response.json().get('id')
            print(f"✅ Created deployment: {name} (ID: {dep_id})")
            return dep_id
        except Exception as e:
            print(f"❌ Error creating deployment {name}: {e}")
            return None

    def update_deployment(self, dep_id: str, app_id: str, name: str, cluster_group_id: str, app_name: str, app_version: str = "1") -> bool:
        """Update an existing deployment with app and a single cluster group"""
        try:
            payload = {
                "name": name,
                "applicationId": app_id,
                "targetGroup": cluster_group_id,
                "applications": [
                    {
                        "id": app_id,
                        "name": app_name,
                        "version": app_version,
                        "strategy": "manual"
                    }
                ]
            }
            response = requests.put(
                f"{self.fm_api_url}/deployments/{dep_id}",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, f"Update deployment PUT /deployments/{dep_id}")
                response.raise_for_status()
            print(f"✅ Updated deployment: {name} (ID: {dep_id})")
            return True
        except Exception as e:
            print(f"❌ Error updating deployment {name}: {e}")
            return False

    def trigger_deployment_release(self, dep_id: str) -> bool:
        """Trigger a deployment release for the given deployment id"""
        try:
            response = requests.post(
                f"{self.fm_api_url}/deployments/{dep_id}/deploy",
                headers=self.headers,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, f"Trigger deploy POST /deployments/{dep_id}/deploy")
                response.raise_for_status()
            print(f"🚀 Triggered release for deployment ID: {dep_id}")
            return True
        except Exception as e:
            print(f"❌ Error triggering release for deployment {dep_id}: {e}")
            return False

    def deploy_application(self, app_id: str, app_name: str) -> bool:
        """Deploy the application to clusters"""
        try:
            # First, find the deployment for this application
            response = requests.get(
                f"{self.fm_api_url}/deployments?limit=200",
                headers=self.headers,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, "List deployments GET /deployments")
                response.raise_for_status()
            
            deployments = response.json().get('items', [])
            deployment_id = None
            
            for deployment in deployments:
                if deployment.get('name') == app_name:
                    deployment_id = deployment.get('id')
                    break
            
            if not deployment_id:
                print(f"❌ No deployment found for application: {app_name}")
                return False
            
            # Trigger deployment using POST (as shown in your examples)
            response = requests.post(
                f"{self.fm_api_url}/deployments/{deployment_id}/deploy",
                headers=self.headers,
                timeout=30
            )
            if response.status_code >= 400:
                self._debug_fail(response, f"Trigger deploy POST /deployments/{deployment_id}/deploy")
                response.raise_for_status()
            
            print(f"✅ Triggered deployment for: {app_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error deploying application {app_name}: {e}")
            return False

    def process_manifest(self, file_path: str) -> bool:
        """Process a single manifest file"""
        print(f"\n📄 Processing: {file_path}")
        
        manifest = self.load_manifest(file_path)
        if not manifest:
            return False
        
        # Extract application name from manifest or filename
        app_name = manifest.get('metadata', {}).get('name')
        if not app_name:
            app_name = Path(file_path).stem
        
        # Convert manifest to YAML string
        manifest = self._normalize_manifest_structure(manifest)
        manifest_yaml = yaml.dump(manifest, default_flow_style=False)

        # Determine target cluster group name(s) from manifest or defaults
        group_names: List[str] = []
        md = manifest.get('metadata', {}) or {}
        sp = manifest.get('spec', {}) or {}

        # Preferred in metadata: list or single
        if isinstance(md.get('clusterGroups'), list):
            group_names = [str(x) for x in md.get('clusterGroups') if x]
        elif md.get('clusterGroup'):
            group_names = [str(md.get('clusterGroup'))]

        # Fallback to spec
        if not group_names:
            if isinstance(sp.get('clusterGroups'), list):
                group_names = [str(x) for x in sp.get('clusterGroups') if x]
            elif sp.get('clusterGroup'):
                group_names = [str(sp.get('clusterGroup'))]

        # Annotations support (comma-separated or single)
        if not group_names:
            annotations = md.get('annotations', {}) or {}
            ann_multi = annotations.get('fleet.scalecomputing.com/cluster-groups')
            ann_single = annotations.get('fleet.scalecomputing.com/cluster-group')
            if ann_multi:
                group_names = [x.strip() for x in str(ann_multi).split(',') if x.strip()]
            elif ann_single:
                group_names = [str(ann_single)]

        # Env/default fallback
        if not group_names:
            group_names = [self.default_cluster_group_name]
        
        # Check if application already exists and whether content changed
        existing_app = self.get_deployment_application(app_name)
        app_id = existing_app.get('id') if existing_app else None

        content_changed = True
        if existing_app and existing_app.get('sourceConfig'):
            try:
                existing_yaml = yaml.safe_load(existing_app.get('sourceConfig'))
                existing_yaml = self._normalize_manifest_structure(existing_yaml)
                # Compare normalized structures to avoid formatting/ordering diffs
                content_changed = (
                    self._normalize(existing_yaml) != self._normalize(manifest)
                )
            except Exception:
                content_changed = True

        if app_id:
            if content_changed:
                success = self.update_deployment_application(app_id, app_name, manifest_yaml)
            else:
                print(f"ℹ️  No changes for application: {app_name}")
                success = True
        else:
            app_id = self.create_deployment_application(app_name, manifest_yaml)
            success = app_id is not None
        
        if not (success and app_id):
            return False

        # Ensure deployments exist/updated for the configured cluster group(s)
        name_to_id = self.list_cluster_groups()
        missing = [n for n in group_names if n not in name_to_id]
        if missing:
            print(f"❌ Cluster group(s) not found: {', '.join(missing)}")
            return False

        all_ok = True
        # Use manifest's top-level version if present; default "1"
        app_version = str(manifest.get('version', '1'))

        for group_name in group_names:
            group_id = name_to_id[group_name]
            deployment_name = f"{app_name}-{group_name}"
            dep_id = self.find_deployment(deployment_name)
            created = False
            if dep_id:
                # Only trigger release if app content changed
                ok = True
                if content_changed:
                    released = self.trigger_deployment_release(dep_id)
                    all_ok = all_ok and released
            else:
                dep_id = self.create_deployment(app_id, deployment_name, group_id, app_name, app_version)
                ok = dep_id is not None
                created = ok and dep_id is not None
            all_ok = all_ok and ok

            # For newly created deployment, trigger release immediately
            if created and dep_id:
                released = self.trigger_deployment_release(dep_id)
                all_ok = all_ok and released

        # Do not trigger release here; will be handled in the next step
        return all_ok
        
        return False

    def run(self):
        """Main deployment process"""
        print("🚀 Starting GitOps deployment to Fleet Manager")
        print(f"📡 Fleet Manager API: {self.fm_api_url}")
        
        # Test connection to Fleet Manager API
        try:
            response = requests.get(
                f"{self.fm_api_url}/clusters",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Fleet Manager API connection successful")
            else:
                self._debug_fail(response, "Connectivity check GET /clusters")
                return False
        except Exception as e:
            print(f"❌ Fleet Manager API connection error: {e}")
            return False
        
        # Get changed files
        changed_files = self.get_changed_files()
        if not changed_files:
            print("ℹ️  No manifest files changed")
            return True
        
        print(f"📋 Found {len(changed_files)} changed manifest files")
        
        # Process each changed file
        success_count = 0
        for file_path in changed_files:
            if self.process_manifest(file_path):
                success_count += 1
        
        print(f"\n📊 Deployment Summary:")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {len(changed_files) - success_count}")
        
        return success_count == len(changed_files)

if __name__ == "__main__":
    try:
        deployer = FleetManagerGitOps()
        success = deployer.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)

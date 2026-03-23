#!/usr/bin/env python3
"""
GitOps deployment script for Fleet Manager
Automatically deploys manifests from GitHub to Fleet Manager via direct API calls
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
        
        # New control flags for better deployment targeting
        self.only_compile = os.getenv('ONLY_COMPILE', '').lower() in ('1', 'true', 'yes')
        self.skip_deployment_trigger = os.getenv('SKIP_DEPLOYMENT_TRIGGER', '').lower() in ('1', 'true', 'yes')
        self.diagnostic_mode = os.getenv('DIAGNOSTIC_MODE', '').lower() in ('1', 'true', 'yes')
        self.test_mode = os.getenv('TEST_MODE', '').lower() in ('1', 'true', 'yes')
        self.monitor_deployments = os.getenv('MONITOR_DEPLOYMENTS', '').lower() in ('1', 'true', 'yes')
        self.target_applications = os.getenv('TARGET_APPLICATIONS', '').split(',') if os.getenv('TARGET_APPLICATIONS') else []
        # Filter out empty strings
        self.target_applications = [app.strip() for app in self.target_applications if app.strip()]
        
        # Test manifest creation settings
        self.create_test_manifests = os.getenv('CREATE_TEST_MANIFESTS', '').lower() in ('1', 'true', 'yes')
        self.test_cluster_group = os.getenv('TEST_CLUSTER_GROUP', 'dd_szt15b')

        # Optional: deploy a single manifest file (set via CLI positional arg)
        self.single_manifest = os.getenv('SINGLE_MANIFEST', '')

        # Track deployments for monitoring
        self.created_deployments = []
        # Track test manifests for cleanup
        self._test_manifest_paths = []
        
        if not self.fm_api_key:
            raise ValueError("SC_FM_APIKEY environment variable is required")
            
        # Fleet Manager API headers
        # Use API key header appropriate for server-to-server requests
        self.headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': self.fm_api_key,
            'user-agent': 'fleet-manager-gitops/2.0'
        }

    def _debug_fail(self, resp: requests.Response, context: str) -> None:
        print(f"❌ {context} (status: {resp.status_code})")
        try:
            print(f"Response JSON: {resp.json()}")
        except Exception:
            print(f"Response Text: {resp.text[:500]}")

    def _create_gitops_description(self, app_name: str, action: str = "managed") -> str:
        """Create comprehensive GitOps description for UI visibility"""
        from datetime import datetime
        
        # Base GitOps information
        description_parts = [
            "🤖 GitOps Managed Application",
            f"📦 Application: {app_name}",
            f"🔄 Action: {action.title()}",
            f"🕐 Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ]
        
        # Repository information
        try:
            import subprocess
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                repo_url = result.stdout.strip()
                description_parts.append(f"🔗 Repository: {repo_url}")
        except:
            description_parts.append("🔗 Repository: fleet-manager-gitops")
        
        # Git commit information
        try:
            import subprocess
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                commit_sha = result.stdout.strip()
                description_parts.append(f"📝 Commit: {commit_sha}")
        except:
            pass
        
        # Branch information
        try:
            import subprocess
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                branch = result.stdout.strip()
                if branch:
                    description_parts.append(f"🌿 Branch: {branch}")
        except:
            pass
        
        # Test mode indicator
        if self.test_mode:
            description_parts.append("🧪 TEST MODE DEPLOYMENT")
        
        # Join with newlines for better readability in UI
        return " | ".join(description_parts)

    def create_test_manifest(self, manifest_path: str) -> str:
        """Create a test version of a manifest with -test suffix and test cluster group.

        Returns the path to the temporary test manifest file.
        The caller is responsible for cleanup (or use self._test_manifest_paths tracking).
        """
        from datetime import datetime

        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        test_manifest = manifest.copy()

        if 'metadata' in test_manifest:
            # Allow manifest to override test cluster group
            test_group = test_manifest['metadata'].get('testClusterGroup', self.test_cluster_group)
            print(f"📋 Using test cluster group: {test_group}")

            test_manifest['metadata']['clusterGroups'] = [test_group]

            # Add -test suffix to application name
            original_name = test_manifest['metadata'].get('name', '')
            test_manifest['metadata']['name'] = f"{original_name}-test"

            # Build descriptive test description
            original_desc = test_manifest['metadata'].get('description', '')
            desc_parts = [
                "🧪 TEST DEPLOYMENT",
                f"📦 Original: {original_desc}",
                f"🎯 Test Cluster: {test_group}",
                f"🕐 Created: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                "🤖 GitOps Automated Test"
            ]

            try:
                import subprocess
                result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    desc_parts.append(f"📝 Commit: {result.stdout.strip()}")
            except Exception:
                pass

            test_manifest['metadata']['description'] = " | ".join(desc_parts)

        # Write test manifest alongside original
        test_manifest_path = manifest_path.replace('.yaml', '-test.yaml')
        with open(test_manifest_path, 'w') as f:
            yaml.dump(test_manifest, f, default_flow_style=False)

        self._test_manifest_paths.append(test_manifest_path)
        print(f"📄 Test manifest created: {test_manifest_path}")
        return test_manifest_path

    def _cleanup_test_manifests(self):
        """Remove temporary test manifest files."""
        for path in self._test_manifest_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🧹 Cleaned up test manifest: {path}")
            except OSError as e:
                print(f"⚠️  Could not remove {path}: {e}")
        self._test_manifest_paths.clear()

    def get_manifest_lifecycle_state(self, manifest: dict) -> str:
        """Get the lifecycle state of a manifest"""
        metadata = manifest.get('metadata', {})
        
        # Check for explicit lifecycle state
        lifecycle = metadata.get('lifecycle', '').lower()
        if lifecycle in ['draft', 'testonly', 'production', 'undeploy']:
            return lifecycle
        
        # Check for legacy draft flag
        if metadata.get('draft', False):
            return 'draft'
        
        # Default to production for backward compatibility
        return 'production'

    def should_skip_manifest(self, manifest: dict, lifecycle_state: str) -> tuple[bool, str]:
        """Determine if a manifest should be skipped based on lifecycle state and context"""
        if lifecycle_state == 'draft':
            return True, "Manifest is in draft state - skipping deployment"
        
        if lifecycle_state == 'testonly' and not self.test_mode:
            return True, "Manifest is test-only and not in test mode - skipping production deployment"
        
        if lifecycle_state == 'undeploy':
            return True, "Manifest is marked for undeployment - will be handled by cleanup process"
        
        return False, ""

    def detect_destructive_changes(self, app_name: str, new_manifest: dict, existing_manifest: dict = None) -> list[str]:
        """Detect potentially destructive changes that could cause deployment issues"""
        warnings = []
        
        if not existing_manifest:
            return warnings
        
        # Check for cloud-init changes
        new_cloud_init = new_manifest.get('spec', {}).get('resources', [])
        existing_cloud_init = existing_manifest.get('spec', {}).get('resources', [])
        
        for i, new_resource in enumerate(new_cloud_init):
            if new_resource.get('type') == 'virdomain':
                new_cloud_init_data = new_resource.get('spec', {}).get('cloud_init_data', {})
                
                # Find corresponding existing resource
                existing_resource = None
                for existing_res in existing_cloud_init:
                    if existing_res.get('type') == 'virdomain':
                        existing_resource = existing_res
                        break
                
                if existing_resource:
                    existing_cloud_init_data = existing_resource.get('spec', {}).get('cloud_init_data', {})
                    
                    # Compare cloud-init user_data
                    new_user_data = new_cloud_init_data.get('user_data', '')
                    existing_user_data = existing_cloud_init_data.get('user_data', '')
                    
                    if new_user_data != existing_user_data and existing_user_data:
                        warnings.append(f"Cloud-init user_data changed for resource '{new_resource.get('name', 'unknown')}' - this may cause deployment issues")
                    
                    # Check for VM name changes
                    new_vm_name = new_resource.get('name', '')
                    existing_vm_name = existing_resource.get('name', '')
                    
                    if new_vm_name != existing_vm_name and existing_vm_name:
                        warnings.append(f"VM name changed from '{existing_vm_name}' to '{new_vm_name}' - this may cause deployment issues")
        
        return warnings

    def handle_undeploy_manifest(self, app_name: str, manifest: dict) -> bool:
        """Handle undeployment of a manifest by triggering cleanup"""
        print(f"🗑️  Handling undeployment for application: {app_name}")
        
        # Get cluster groups from manifest
        cluster_groups = manifest.get('metadata', {}).get('clusterGroups', [])
        if not cluster_groups:
            cluster_groups = [self.default_cluster_group_name]
        
        # Find existing deployments
        deployments_deleted = 0
        for cluster_group in cluster_groups:
            deployment_name = f"{app_name}-{cluster_group}"
            dep_id = self.find_deployment(deployment_name)
            
            if dep_id:
                print(f"🗑️  Deleting deployment: {deployment_name}")
                
                # Delete deployment
                try:
                    url = f"{self.fm_api_url}/deployments/{dep_id}"
                    response = requests.delete(url, headers=self.headers)
                    
                    if response.status_code == 204:
                        print(f"✅ Deleted deployment: {deployment_name}")
                        deployments_deleted += 1
                    else:
                        print(f"❌ Failed to delete deployment {deployment_name}: {response.status_code}")
                        if response.status_code == 409:
                            print(f"   Deployment may still be running - check Fleet Manager UI")
                except Exception as e:
                    print(f"❌ Error deleting deployment {deployment_name}: {e}")
            else:
                print(f"ℹ️  No deployment found for: {deployment_name}")
        
        # Delete application if no deployments remain
        app_id = self.find_deployment_application(app_name)
        if app_id:
            print(f"🗑️  Deleting application: {app_name}")
            try:
                url = f"{self.fm_api_url}/deployment-applications/{app_id}"
                response = requests.delete(url, headers=self.headers)
                
                if response.status_code == 204:
                    print(f"✅ Deleted application: {app_name}")
                else:
                    print(f"❌ Failed to delete application {app_name}: {response.status_code}")
                    if response.status_code == 409:
                        print(f"   Application may still have active deployments")
            except Exception as e:
                print(f"❌ Error deleting application {app_name}: {e}")
        
        print(f"📊 Undeployment summary: {deployments_deleted} deployments deleted")
        return deployments_deleted > 0

    @staticmethod
    def _normalize(obj: Any) -> str:
        """Return a stable JSON string for semantic equality checks."""
        try:
            return json.dumps(obj, sort_keys=True, separators=(",", ":"))
        except Exception:
            return str(obj)

    def should_process_manifest(self, file_path: str, app_name: str) -> bool:
        """Determine if a manifest should be processed based on targeting rules"""
        
        # If specific applications are targeted, only process those
        if self.target_applications:
            if app_name not in self.target_applications:
                print(f"⏭️  Skipping {app_name} (not in target list: {self.target_applications})")
                return False
        
        return True

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
        # Normalize cloud-init user_data whitespace to reduce false positives
        spec = manifest.get('spec') or {}
        if isinstance(spec, dict):
            resources = spec.get('resources') or []
            if isinstance(resources, list):
                for res in resources:
                    if not isinstance(res, dict):
                        continue
                    if (res.get('type') == 'virdomain' and isinstance(res.get('spec'), dict)):
                        rspec = res['spec']
                        cid = rspec.get('cloud_init_data')
                        if isinstance(cid, dict) and isinstance(cid.get('user_data'), str):
                            cid['user_data'] = cid['user_data'].rstrip()
                            rspec['cloud_init_data'] = cid
                            res['spec'] = rspec
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
                        f.startswith('manifests/') and 
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
                        f.startswith('manifests/') and 
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
            untracked = []

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

                # 4) Untracked files (e.g., freshly compiled outputs not yet added)
                untracked = subprocess.run(
                    ['git', 'ls-files', '--others', '--exclude-standard'],
                    capture_output=True, text=True, check=True
                ).stdout.strip().split('\n')

            candidates = [
                *diff_last_commits,
                *diff_index_vs_head,
                *diff_worktree_vs_head,
                *untracked,
            ]

            changed_files = [
                f for f in candidates if f and 
                f.startswith('manifests/') and 
                f.endswith(('.yaml', '.yml'))
            ]
        except Exception:
            # If git is unavailable or repo has no history, process all manifests
            pass

        # If still nothing, only scan all manifests if explicitly requested
        if not changed_files and process_all:
            changed_files = (
                glob.glob('manifests/**/*.yaml', recursive=True) +
                glob.glob('manifests/**/*.yml', recursive=True)
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

    def load_manifest_raw(self, file_path: str) -> str:
        """Load raw YAML content (preserving comments) from a manifest file"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error loading raw content from {file_path}: {e}")
            return None

    def find_deployment_application(self, app_name: str) -> str:
        """Find existing deployment application ID by name"""
        app = self.get_deployment_application(app_name)
        return app.get('id') if app else None

    def get_deployment_application(self, app_name: str) -> Dict[str, Any]:
        """Return full deployment application object by name (or None)"""
        try:
            # Handle pagination to get all applications
            url = f"{self.fm_api_url}/deployment-applications?limit=50"
            
            while url:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for app in data.get('items', []):
                    if app.get('name') == app_name:
                        return app
                
                # Check for next page
                url = data.get('next')
            
            return None
        except Exception as e:
            print(f"❌ Error getting application {app_name}: {e}")
            return None

    def create_deployment_application(self, app_name: str, manifest: str) -> str:
        """Create a new deployment application (use POST)."""
        try:
            # Add comprehensive GitOps source information
            gitops_description = self._create_gitops_description(app_name, "created")
            
            payload = {
                "name": app_name,
                "sourceType": "gitops",  # Use "gitops" to distinguish from manual editor
                "sourceConfig": manifest,
                "description": gitops_description
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
            # Add comprehensive GitOps source information
            gitops_description = self._create_gitops_description(app_name, "updated")
            
            payload = {
                "name": app_name,
                "sourceType": "gitops",  # Use "gitops" to distinguish from manual editor
                "sourceConfig": manifest,
                "description": gitops_description
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
            # Handle pagination to get all deployments
            url = f"{self.fm_api_url}/deployments?limit=50"
            
            while url:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for dep in data.get('items', []):
                    if dep.get('name') == name:
                        return dep.get('id')
                
                # Check for next page
                url = data.get('next')
            
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

    def get_deployment_status(self, dep_id: str) -> Dict[str, Any]:
        """Get detailed deployment status and information"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployments/{dep_id}",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  Could not get deployment status for {dep_id}: {response.status_code}")
                return {}
        except Exception as e:
            print(f"⚠️  Error getting deployment status for {dep_id}: {e}")
            return {}

    def check_deployment_conflicts(self, app_name: str, cluster_groups: List[str]) -> List[Dict[str, Any]]:
        """Check for potential deployment conflicts"""
        conflicts = []
        try:
            # Get all deployments
            response = requests.get(
                f"{self.fm_api_url}/deployments?limit=200",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            deployments = response.json().get('items', [])
            
            # Check for naming conflicts
            for deployment in deployments:
                dep_name = deployment.get('name')
                dep_app_id = deployment.get('applicationId')
                dep_status = deployment.get('status')
                
                # Check if deployment name matches expected pattern
                for group_name in cluster_groups:
                    expected_name = f"{app_name}-{group_name}"
                    if dep_name == expected_name:
                        conflicts.append({
                            'type': 'naming_conflict',
                            'deployment_id': deployment.get('id'),
                            'deployment_name': dep_name,
                            'status': dep_status,
                            'application_id': dep_app_id,
                            'message': f"Deployment {expected_name} already exists with status: {dep_status}"
                        })
            
            return conflicts
        except Exception as e:
            print(f"⚠️  Error checking deployment conflicts: {e}")
            return []

    def trigger_deployment_release(self, dep_id: str, dep_name: str = None) -> bool:
        """Trigger a deployment release for the given deployment id with enhanced error checking"""
        try:
            # Get deployment status first
            dep_status = self.get_deployment_status(dep_id)
            if dep_status:
                current_status = dep_status.get('status', 'unknown')
                print(f"📊 Deployment {dep_name or dep_id} current status: {current_status}")
                
                # Check if deployment is in a problematic state
                if current_status in ['failed', 'error', 'cancelled']:
                    print(f"⚠️  Deployment is in {current_status} state - this may cause issues")
            
            # Attempt to trigger deployment
            response = requests.post(
                f"{self.fm_api_url}/deployments/{dep_id}/deploy",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print(f"🚀 Successfully triggered release for deployment: {dep_name or dep_id}")
                return True
            elif response.status_code == 409:
                print(f"⚠️  Deployment conflict (409) - deployment may already be running or in progress")
                print(f"   Deployment: {dep_name or dep_id}")
                return False
            elif response.status_code == 500:
                print(f"❌ Server error (500) - Fleet Manager API internal error")
                print(f"   Deployment: {dep_name or dep_id}")
                print(f"   This often indicates:")
                print(f"   - Deployment in problematic state")
                print(f"   - Resource conflicts")
                print(f"   - API processing issues")
                self._debug_fail(response, f"Trigger deploy POST /deployments/{dep_id}/deploy")
                return False
            else:
                self._debug_fail(response, f"Trigger deploy POST /deployments/{dep_id}/deploy")
                return False
                
        except Exception as e:
            print(f"❌ Error triggering release for deployment {dep_name or dep_id}: {e}")
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
        """Process a single manifest file with enhanced controls"""
        print(f"\n📄 Processing: {file_path}")
        
        manifest = self.load_manifest(file_path)
        if not manifest:
            return False
            
        # Only process full Application manifests; skip definitions/configs
        mtype = (manifest.get('type') or '').lower()
        if mtype != 'application':
            print(f"ℹ️  Skipping non-Application manifest: {file_path} (type={manifest.get('type')})")
            return True
        
        # Extract application name from manifest or filename
        app_name = manifest.get('metadata', {}).get('name')
        if not app_name:
            app_name = Path(file_path).stem
        
        # Check lifecycle state
        lifecycle_state = self.get_manifest_lifecycle_state(manifest)
        print(f"🔍 Lifecycle state: {lifecycle_state}")
        
        # Handle undeploy lifecycle
        if lifecycle_state == 'undeploy':
            return self.handle_undeploy_manifest(app_name, manifest)
        
        # Check if manifest should be skipped
        should_skip, skip_reason = self.should_skip_manifest(manifest, lifecycle_state)
        if should_skip:
            print(f"⏭️  {skip_reason}")
            return True  # Skip but don't fail
        
        # Check for destructive changes if application exists
        existing_app = self.get_deployment_application(app_name)
        if existing_app and existing_app.get('sourceConfig'):
            try:
                existing_manifest = yaml.safe_load(existing_app.get('sourceConfig'))
                warnings = self.detect_destructive_changes(app_name, manifest, existing_manifest)
                
                if warnings:
                    print(f"⚠️  DESTRUCTIVE CHANGES DETECTED for {app_name}:")
                    for warning in warnings:
                        print(f"   - {warning}")
                    
                    # Check if we should bail out on destructive changes
                    if os.getenv('BAIL_ON_DESTRUCTIVE_CHANGES', '').lower() in ('true', '1', 'yes'):
                        print(f"❌ Bailing out due to destructive changes (BAIL_ON_DESTRUCTIVE_CHANGES=true)")
                        return False
                    else:
                        print(f"⚠️  Continuing deployment despite destructive changes...")
                        print(f"   Set BAIL_ON_DESTRUCTIVE_CHANGES=true to stop on such changes")
            except Exception as e:
                print(f"⚠️  Could not check for destructive changes: {e}")
        
        # Check if we should process this manifest
        if not self.should_process_manifest(file_path, app_name):
            return True  # Skip but don't fail
        
        # Load raw YAML content to preserve comments
        manifest_yaml = self.load_manifest_raw(file_path)
        if not manifest_yaml:
            return False
            
        # Also normalize the parsed manifest for comparison purposes
        manifest_normalized = self._normalize_manifest_structure(manifest)

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
        
        # Get application ID (existing_app already retrieved earlier)
        app_id = existing_app.get('id') if existing_app else None

        content_changed = True
        if existing_app and existing_app.get('sourceConfig'):
            try:
                existing_yaml = yaml.safe_load(existing_app.get('sourceConfig'))
                existing_yaml = self._normalize_manifest_structure(existing_yaml)
                # Compare normalized structures to avoid formatting/ordering diffs
                content_changed = (
                    self._normalize(existing_yaml) != self._normalize(manifest_normalized)
                )
            except Exception:
                content_changed = True

        # Update or create application
        if app_id:
            if content_changed:
                success = self.update_deployment_application(app_id, app_name, manifest_yaml)
                print(f"🔄 Updated application: {app_name}")
            else:
                print(f"ℹ️  No changes for application: {app_name}")
                success = True
        else:
            app_id = self.create_deployment_application(app_name, manifest_yaml)
            success = app_id is not None
            if success:
                print(f"✨ Created new application: {app_name}")
        
        if not (success and app_id):
            return False

        # Handle deployments (only if not skipping deployment triggers)
        if self.skip_deployment_trigger:
            print(f"⏭️  Skipping deployment trigger for {app_name} (SKIP_DEPLOYMENT_TRIGGER=true)")
            return True

        # Check for deployment conflicts before proceeding
        print(f"🔍 Checking for deployment conflicts for {app_name}...")
        conflicts = self.check_deployment_conflicts(app_name, group_names)
        if conflicts:
            print(f"⚠️  Found {len(conflicts)} potential deployment conflicts:")
            for conflict in conflicts:
                print(f"   - {conflict['message']}")
            print(f"   💡 Consider using a different application name or cleaning up existing deployments")

        # Ensure deployments exist/updated for the configured cluster group(s)
        name_to_id = self.list_cluster_groups()
        missing = [n for n in group_names if n not in name_to_id]
        if missing:
            print(f"❌ Cluster group(s) not found: {', '.join(missing)}")
            print(f"   Available cluster groups: {', '.join(name_to_id.keys())}")
            return False

        all_ok = True
        # Use manifest's top-level version if present; default "1"
        app_version = str(manifest.get('version', '1'))

        for group_name in group_names:
            group_id = name_to_id[group_name]
            deployment_name = f"{app_name}-{group_name}"
            print(f"🔍 Processing deployment: {deployment_name}")
            
            dep_id = self.find_deployment(deployment_name)
            created = False
            if dep_id:
                print(f"📋 Found existing deployment: {deployment_name} (ID: {dep_id})")
                # Only trigger release if app content changed
                ok = True
                if content_changed:
                    print(f"🔄 Content changed, triggering deployment release...")
                    released = self.trigger_deployment_release(dep_id, deployment_name)
                    all_ok = all_ok and released
                else:
                    print(f"ℹ️  No content changes, skipping deployment trigger")
            else:
                print(f"✨ Creating new deployment: {deployment_name}")
                dep_id = self.create_deployment(app_id, deployment_name, group_id, app_name, app_version)
                ok = dep_id is not None
                created = ok and dep_id is not None
                
                # Track deployment for monitoring
                if created and self.monitor_deployments:
                    self.created_deployments.append({
                        'id': dep_id,
                        'name': deployment_name,
                        'app_name': app_name,
                        'cluster_group': group_name
                    })
            all_ok = all_ok and ok

            # For newly created deployment, trigger release immediately
            if created and dep_id:
                print(f"🚀 Triggering initial deployment release for new deployment...")
                released = self.trigger_deployment_release(dep_id, deployment_name)
                all_ok = all_ok and released

        return all_ok
        
        return False

    def run(self):
        """Main deployment process with enhanced controls"""
        print("🚀 Starting Fleet Manager GitOps Deployment")
        print(f"📡 Fleet Manager API: {self.fm_api_url}")
        
        # Print control flags
        if self.test_mode:
            print("🧪 TEST_MODE: Deploying to test cluster group only")
        if self.create_test_manifests:
            print(f"🧪 CREATE_TEST_MANIFESTS: Will create -test copies targeting cluster group '{self.test_cluster_group}'")
        if self.only_compile:
            print("🔧 ONLY_COMPILE mode: Will only compile manifests, not deploy")
        if self.skip_deployment_trigger:
            print("⏭️  SKIP_DEPLOYMENT_TRIGGER mode: Will update applications but not trigger deployments")
        if self.diagnostic_mode:
            print("🔍 DIAGNOSTIC_MODE: Enhanced error checking and conflict detection enabled")
        if self.target_applications:
            print(f"🎯 TARGET_APPLICATIONS mode: Will only process {self.target_applications}")
        if self.single_manifest:
            print(f"📄 SINGLE_MANIFEST mode: Will only process {self.single_manifest}")
        
        # If only compiling, skip Fleet Manager API connection
        if self.only_compile:
            print("🔧 ONLY_COMPILE mode enabled - skipping Fleet Manager operations")
            return True
        
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
        
        # Get changed files (or use single manifest if specified)
        if self.single_manifest:
            if not os.path.exists(self.single_manifest):
                print(f"❌ Manifest file not found: {self.single_manifest}")
                return False
            changed_files = [self.single_manifest]
        else:
            changed_files = self.get_changed_files()
        # Skip files that were deleted (can appear in event payload)
        existing_changed_files = [f for f in changed_files if os.path.exists(f)]
        missing_files = [f for f in changed_files if not os.path.exists(f)]
        if missing_files:
            print(f"ℹ️  Skipping deleted files: {', '.join(missing_files)}")
        changed_files = existing_changed_files
        if not changed_files:
            print("ℹ️  No manifest files changed")
            return True
        
        print(f"📋 Found {len(changed_files)} changed manifest files")

        # Map container/runtime sources → compiled outputs and include only those whose sources changed
        try:
            # Remove any compiled paths from the raw change list (we'll re-add selectively)
            changed_files = [f for f in changed_files if not f.startswith('manifests/_compiled/')]

            generic_runtime = 'manifests/containers/runtime_configuration/runtime.yaml'
            
            # Find container definition files by extension first
            container_files = glob.glob('manifests/containers/*.container.yaml')
            
            # Also find any YAML files that contain ContainerDefinition type
            all_yaml_files = glob.glob('manifests/containers/*.yaml')
            for yaml_file in all_yaml_files:
                try:
                    with open(yaml_file, 'r') as f:
                        content = yaml.safe_load(f)
                        if content and content.get('type') == 'ContainerDefinition':
                            if yaml_file not in container_files:
                                container_files.append(yaml_file)
                except Exception:
                    continue  # Skip files that can't be parsed
            
            compiled_to_add: List[str] = []
            container_sources_changed = False
            
            for cfile in container_files:
                name = Path(cfile).stem.replace('.container', '')
                per_app_runtime = f'manifests/containers/runtime_configuration/{name}.runtime.yaml'
                compiled_path = f'manifests/_compiled/{name}.yaml'
                
                # If any of the sources changed in this run, include its compiled output
                if any(src in changed_files for src in [cfile, per_app_runtime, generic_runtime]):
                    container_sources_changed = True
                    if os.path.exists(compiled_path):
                        compiled_to_add.append(compiled_path)
                        print(f"🔄 Container source changed, will process: {compiled_path}")

            # CRITICAL FIX: Only process compiled files if their sources actually changed
            # This prevents unwanted redeployment of container applications when editing unrelated manifests
            if not container_sources_changed:
                print("ℹ️  No container sources changed, skipping compiled container deployments")
                print("ℹ️  This prevents unwanted redeployment of container applications")
            else:
                print(f"📦 Will process {len(compiled_to_add)} compiled container applications")

            # Add compiled files to the change list
            for p in compiled_to_add:
                if p not in changed_files:
                    changed_files.append(p)
                    
        except Exception as e:
            print(f"⚠️  Error processing compiled files: {e}")
            # Don't fall back to adding all compiled files - this was the bug!

        # Only process Application manifests, track skipped
        application_files: List[str] = []
        skipped_count = 0
        for cf in changed_files:
            try:
                data = self.load_manifest(cf)
                if data and isinstance(data, dict) and str(data.get('type','')).lower() == 'application':
                    application_files.append(cf)
                else:
                    print(f"ℹ️  Skipping non-Application manifest: {cf} (type={data.get('type') if isinstance(data, dict) else 'unknown'})")
                    skipped_count += 1
            except Exception:
                application_files.append(cf)

        # If --create-test-manifests, transform each manifest into a -test copy
        if self.create_test_manifests:
            test_files = []
            for file_path in application_files:
                try:
                    test_path = self.create_test_manifest(file_path)
                    test_files.append(test_path)
                except Exception as e:
                    print(f"⚠️  Failed to create test manifest for {file_path}: {e}")
            application_files = test_files

        # Process each Application file
        success_count = 0
        try:
            for file_path in application_files:
                if self.process_manifest(file_path):
                    success_count += 1
        finally:
            # Always clean up test manifests even on failure
            if self.create_test_manifests:
                self._cleanup_test_manifests()

        print(f"\n📊 Deployment Summary:")
        print(f"✅ Successful: {success_count}")
        print(f"⏭️  Skipped: {skipped_count}")
        print(f"❌ Failed: {len(application_files) - success_count}")

        # Monitor deployments if requested
        if self.monitor_deployments and self.created_deployments:
            print(f"\n🔍 Monitoring {len(self.created_deployments)} deployments...")
            try:
                from monitor_deployment_releases import DeploymentReleaseMonitor
                monitor = DeploymentReleaseMonitor()
                deployment_ids = [dep['id'] for dep in self.created_deployments]
                results = monitor.report_deployment_results(deployment_ids, timeout_minutes=30)
                
                # Update success count based on monitoring results
                if results['summary']['failed'] > 0:
                    print(f"⚠️  Some deployments failed during monitoring")
                    return False
                    
            except ImportError:
                print(f"⚠️  Monitoring script not available, skipping deployment monitoring")
            except Exception as e:
                print(f"⚠️  Error during monitoring: {e}")
        
        return success_count == len(application_files)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fleet Manager GitOps deployment')
    parser.add_argument('manifest', nargs='?', default=None,
                        help='Optional: deploy a single manifest file instead of detecting changes')
    parser.add_argument('--target-apps', help='Comma-separated list of applications to target')
    parser.add_argument('--only-compile', action='store_true', help='Only compile manifests, do not deploy')
    parser.add_argument('--skip-deployment-trigger', action='store_true', help='Update applications but do not trigger deployments')
    parser.add_argument('--diagnostic', action='store_true', help='Enable enhanced error checking and conflict detection')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deployed without making changes')
    parser.add_argument('--test', action='store_true',
                        help='Enable test mode (deploy testonly manifests, add test mode indicators)')
    parser.add_argument('--test-cluster-group', default='dd_szt15b',
                        help='Cluster group for test deployments (default: dd_szt15b)')
    parser.add_argument('--create-test-manifests', action='store_true',
                        help='Create -test copies of manifests with modified names and cluster groups')

    args = parser.parse_args()

    # Set environment variables from command line args
    if args.manifest:
        os.environ['SINGLE_MANIFEST'] = args.manifest
    if args.target_apps:
        os.environ['TARGET_APPLICATIONS'] = args.target_apps
    if args.only_compile:
        os.environ['ONLY_COMPILE'] = 'true'
    if args.skip_deployment_trigger:
        os.environ['SKIP_DEPLOYMENT_TRIGGER'] = 'true'
    if args.diagnostic:
        os.environ['DIAGNOSTIC_MODE'] = 'true'
    if args.test:
        os.environ['TEST_MODE'] = 'true'
    if args.test_cluster_group:
        os.environ['TEST_CLUSTER_GROUP'] = args.test_cluster_group
    if args.create_test_manifests:
        os.environ['CREATE_TEST_MANIFESTS'] = 'true'

    try:
        deployer = FleetManagerGitOps()
        success = deployer.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)

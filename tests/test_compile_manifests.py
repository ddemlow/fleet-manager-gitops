"""Tests for manifest compilation (scripts/compile_manifests.py)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from compile_manifests import _meta_data, to_application


# ---------------------------------------------------------------------------
# _meta_data
# ---------------------------------------------------------------------------

class TestMetaData:
    def test_basic_hostname(self):
        result = _meta_data('my-host')
        assert 'local-hostname: "my-host"' in result
        assert 'dsmode: local' in result

    def test_empty_name_falls_back_to_vm(self):
        result = _meta_data('')
        assert 'local-hostname: "vm"' in result


# ---------------------------------------------------------------------------
# to_application
# ---------------------------------------------------------------------------

class TestToApplication:
    @staticmethod
    def _container_def():
        return {
            'type': 'ContainerDefinition',
            'metadata': {
                'name': 'test-app',
                'clusterGroups': ['TestGroup'],
            },
            'spec': {
                'containers': [
                    {
                        'name': 'nginx',
                        'image': 'docker.io/library/nginx:latest',
                        'ports': ['80:80'],
                    },
                ],
                'content': [],
            },
        }

    @staticmethod
    def _runtime_def():
        return {
            'version': '1',
            'type': 'RuntimeConfiguration',
            'metadata': {'name': 'default-runtime'},
            'spec': {
                'cloudInit': {
                    'ssh': {'passwordAuth': True, 'disableRoot': False},
                },
                'runtime': {
                    'vcpus': 2,
                    'memory': '2Gi',
                    'disk': {
                        'name': 'rootdisk',
                        'capacity': '40Gi',
                        'format': 'raw',
                        'url': 'https://example.com/disk.raw',
                    },
                },
                'network': [{'name': 'eth0', 'type': 'virtio'}],
                'vmState': 'running',
                'policies': {
                    'enablePodmanSocket': True,
                    'enableAutoUpdateTimer': True,
                    'setupQemuGuestAgent': False,
                    'rebootAfterQga': False,
                    'autoUpdateLabel': True,
                },
            },
        }

    def test_output_type_and_version(self):
        app = to_application(self._container_def(), self._runtime_def())
        assert app['type'] == 'Application'
        assert app['version'] == '1'

    def test_metadata_name(self):
        app = to_application(self._container_def(), self._runtime_def())
        assert app['metadata']['name'] == 'test-app'

    def test_assets_contains_virtual_disk(self):
        app = to_application(self._container_def(), self._runtime_def())
        assets = app['spec']['assets']
        assert any(a['type'] == 'virtual_disk' for a in assets)

    def test_resources_contains_virdomain(self):
        app = to_application(self._container_def(), self._runtime_def())
        resources = app['spec']['resources']
        assert any(r['type'] == 'virdomain' for r in resources)

    def test_cloud_init_data_populated(self):
        app = to_application(self._container_def(), self._runtime_def())
        virdomain = [r for r in app['spec']['resources'] if r['type'] == 'virdomain'][0]
        cloud_init = virdomain['spec']['cloud_init_data']
        assert 'user_data' in cloud_init
        assert 'meta_data' in cloud_init

    def test_rendered_user_data_key_present(self):
        """to_application attaches __rendered_user_data__ for later YAML emission."""
        app = to_application(self._container_def(), self._runtime_def())
        assert '__rendered_user_data__' in app
        assert '#cloud-config' in app['__rendered_user_data__']

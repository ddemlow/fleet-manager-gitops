"""Tests for destructive change detection."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv('SC_FM_APIKEY', 'dummy')


@pytest.fixture
def fm():
    from deploy import FleetManagerGitOps
    return FleetManagerGitOps()


def _make_manifest(vm_name='test-vm', user_data='#cloud-config\nruncmd: []'):
    """Helper to build a minimal manifest with a virdomain resource."""
    return {
        'spec': {
            'resources': [
                {
                    'type': 'virdomain',
                    'name': vm_name,
                    'spec': {
                        'cloud_init_data': {
                            'user_data': user_data,
                        }
                    }
                }
            ]
        }
    }


class TestDetectDestructiveChanges:
    def test_no_existing_manifest_returns_empty(self, fm):
        warnings = fm.detect_destructive_changes('app1', _make_manifest(), None)
        assert warnings == []

    def test_same_cloud_init_no_warning(self, fm):
        manifest = _make_manifest(user_data='#cloud-config\nfoo: bar')
        existing = _make_manifest(user_data='#cloud-config\nfoo: bar')
        warnings = fm.detect_destructive_changes('app1', manifest, existing)
        cloud_init_warnings = [w for w in warnings if 'cloud-init' in w.lower() or 'cloud_init' in w.lower() or 'user_data' in w.lower()]
        assert cloud_init_warnings == []

    def test_changed_cloud_init_user_data_warns(self, fm):
        new = _make_manifest(user_data='#cloud-config\nnew: data')
        existing = _make_manifest(user_data='#cloud-config\nold: data')
        warnings = fm.detect_destructive_changes('app1', new, existing)
        assert any('user_data' in w.lower() or 'cloud' in w.lower() for w in warnings)

    def test_changed_vm_name_warns(self, fm):
        new = _make_manifest(vm_name='new-vm')
        existing = _make_manifest(vm_name='old-vm')
        warnings = fm.detect_destructive_changes('app1', new, existing)
        assert any('name' in w.lower() for w in warnings)

    def test_no_changes_empty_warnings(self, fm):
        manifest = _make_manifest()
        existing = _make_manifest()
        warnings = fm.detect_destructive_changes('app1', manifest, existing)
        assert warnings == []

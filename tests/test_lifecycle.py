"""Tests for manifest lifecycle detection and skip logic."""

import os
import sys
import pytest

# Add scripts/ to path so we can import deploy module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    """Set required env var so FleetManagerGitOps can be instantiated."""
    monkeypatch.setenv('SC_FM_APIKEY', 'dummy')


@pytest.fixture
def fm():
    from deploy import FleetManagerGitOps
    return FleetManagerGitOps()


# ---------------------------------------------------------------------------
# get_manifest_lifecycle_state
# ---------------------------------------------------------------------------

class TestGetManifestLifecycleState:
    def test_draft(self, fm):
        manifest = {'metadata': {'lifecycle': 'draft'}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'draft'

    def test_testonly(self, fm):
        manifest = {'metadata': {'lifecycle': 'testonly'}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'testonly'

    def test_production(self, fm):
        manifest = {'metadata': {'lifecycle': 'production'}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'production'

    def test_undeploy(self, fm):
        manifest = {'metadata': {'lifecycle': 'undeploy'}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'undeploy'

    def test_legacy_draft_flag(self, fm):
        manifest = {'metadata': {'draft': True}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'draft'

    def test_no_lifecycle_field(self, fm):
        manifest = {'metadata': {'name': 'some-app'}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'production'

    def test_empty_metadata(self, fm):
        manifest = {'metadata': {}}
        assert fm.get_manifest_lifecycle_state(manifest) == 'production'


# ---------------------------------------------------------------------------
# should_skip_manifest
# ---------------------------------------------------------------------------

class TestShouldSkipManifest:
    def test_draft_skipped(self, fm):
        skip, reason = fm.should_skip_manifest({}, 'draft')
        assert skip is True
        assert 'draft' in reason.lower()

    def test_testonly_no_test_mode_skipped(self, fm):
        fm.test_mode = False
        skip, reason = fm.should_skip_manifest({}, 'testonly')
        assert skip is True
        assert 'test' in reason.lower()

    def test_testonly_with_test_mode_not_skipped(self, fm):
        fm.test_mode = True
        skip, reason = fm.should_skip_manifest({}, 'testonly')
        assert skip is False
        assert reason == ''

    def test_production_not_skipped(self, fm):
        skip, reason = fm.should_skip_manifest({}, 'production')
        assert skip is False
        assert reason == ''

    def test_undeploy_skipped(self, fm):
        skip, reason = fm.should_skip_manifest({}, 'undeploy')
        assert skip is True
        assert 'undeploy' in reason.lower()

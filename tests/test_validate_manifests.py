"""Tests for the manifest validator (scripts/validate-manifests.py)."""

import os
import sys
import importlib
import tempfile
import pytest
import yaml

# The file is named validate-manifests.py (hyphenated), so use importlib
_scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, _scripts_dir)

_spec = importlib.util.spec_from_file_location(
    'validate_manifests',
    os.path.join(_scripts_dir, 'validate-manifests.py'),
)
validate_manifests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_manifests)
ManifestValidator = validate_manifests.ManifestValidator


@pytest.fixture
def validator():
    return ManifestValidator()


# ---------------------------------------------------------------------------
# validate_manifest_structure
# ---------------------------------------------------------------------------

class TestValidateManifestStructure:
    def test_valid_application(self, validator):
        manifest = {
            'type': 'Application',
            'metadata': {'name': 'test-app'},
            'spec': {
                'assets': [
                    {'name': 'disk1', 'type': 'virtual_disk'},
                ],
            },
        }
        assert validator.validate_manifest_structure(manifest, 'test.yaml') is True

    def test_missing_metadata_name(self, validator):
        manifest = {
            'type': 'Application',
            'metadata': {},
            'spec': {
                'assets': [
                    {'name': 'disk1', 'type': 'virtual_disk'},
                ],
            },
        }
        assert validator.validate_manifest_structure(manifest, 'test.yaml') is False

    def test_missing_spec_assets_still_fails(self, validator):
        """Assets are required by the validator's current implementation."""
        manifest = {
            'type': 'Application',
            'metadata': {'name': 'test-app'},
            'spec': {},
        }
        assert validator.validate_manifest_structure(manifest, 'test.yaml') is False

    def test_asset_with_invalid_type(self, validator):
        manifest = {
            'type': 'Application',
            'metadata': {'name': 'test-app'},
            'spec': {
                'assets': [
                    {'name': 'disk1', 'type': 'invalid_type'},
                ],
            },
        }
        assert validator.validate_manifest_structure(manifest, 'test.yaml') is False

    def test_non_application_skipped_via_validate_manifest(self, validator, tmp_path):
        """Non-Application type manifests are skipped (returns True) via validate_manifest."""
        manifest = {
            'type': 'ContainerDefinition',
            'metadata': {'name': 'test-container'},
            'spec': {},
        }
        f = tmp_path / 'container.yaml'
        f.write_text(yaml.dump(manifest))
        # validate_manifest skips non-Application types and returns True
        assert validator.validate_manifest(str(f)) is True


# ---------------------------------------------------------------------------
# validate_yaml_syntax
# ---------------------------------------------------------------------------

class TestValidateYamlSyntax:
    def test_valid_yaml(self, validator, tmp_path):
        f = tmp_path / 'valid.yaml'
        f.write_text('key: value\nlist:\n  - item1\n')
        assert validator.validate_yaml_syntax(str(f)) is True

    def test_invalid_yaml(self, validator, tmp_path):
        f = tmp_path / 'invalid.yaml'
        # Tabs mixed with spaces and unquoted special chars produce a YAML error
        f.write_text('key: value\n\t bad: indent\n  nested:\n    - [unclosed\n')
        assert validator.validate_yaml_syntax(str(f)) is False

    def test_empty_file(self, validator, tmp_path):
        f = tmp_path / 'empty.yaml'
        f.write_text('')
        # yaml.safe_load returns None for empty files; no exception raised
        assert validator.validate_yaml_syntax(str(f)) is True

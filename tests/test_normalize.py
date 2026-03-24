"""Tests for manifest normalization."""

import os
import sys
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from deploy import FleetManagerGitOps


class TestNormalizeManifestStructure:
    """Test FleetManagerGitOps._normalize_manifest_structure (staticmethod)."""

    def test_labels_dict_converted_to_list(self):
        manifest = {
            'metadata': {
                'name': 'test',
                'labels': {'env': 'prod', 'team': 'ops'},
            },
            'spec': {},
        }
        result = FleetManagerGitOps._normalize_manifest_structure(manifest)
        labels = result['metadata']['labels']
        assert isinstance(labels, list)
        label_keys = {item['key'] for item in labels}
        assert label_keys == {'env', 'team'}
        for item in labels:
            if item['key'] == 'env':
                assert item['value'] == 'prod'
            elif item['key'] == 'team':
                assert item['value'] == 'ops'

    def test_labels_already_list_unchanged(self):
        original_labels = [{'key': 'env', 'value': 'prod'}]
        manifest = {
            'metadata': {
                'name': 'test',
                'labels': copy.deepcopy(original_labels),
            },
            'spec': {},
        }
        result = FleetManagerGitOps._normalize_manifest_structure(manifest)
        assert result['metadata']['labels'] == original_labels

    def test_cloud_init_user_data_trailing_whitespace_stripped(self):
        manifest = {
            'metadata': {'name': 'test'},
            'spec': {
                'resources': [
                    {
                        'type': 'virdomain',
                        'spec': {
                            'cloud_init_data': {
                                'user_data': '#cloud-config\nruncmd:\n  - echo hello\n   \n  '
                            }
                        }
                    }
                ]
            },
        }
        result = FleetManagerGitOps._normalize_manifest_structure(manifest)
        user_data = result['spec']['resources'][0]['spec']['cloud_init_data']['user_data']
        assert not user_data.endswith(' ')
        assert not user_data.endswith('\n   \n  ')

    def test_manifest_without_labels_or_cloud_init(self):
        manifest = {
            'metadata': {'name': 'test'},
            'spec': {'assets': []},
        }
        original = copy.deepcopy(manifest)
        result = FleetManagerGitOps._normalize_manifest_structure(manifest)
        assert result['metadata'] == original['metadata']
        assert result['spec'] == original['spec']

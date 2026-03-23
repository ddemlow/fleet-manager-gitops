#!/usr/bin/env python3
"""
Dry-run tests for deploy.py CLI flags and test manifest creation.
These tests do NOT require API access or SC_FM_APIKEY — they exercise
the argument parsing, manifest transformation, and flag handling logic only.

Requirements: pyyaml, requests (same as deploy.py itself)

Usage:
    python tests/test_deploy_flags.py
"""

import os
import sys
import tempfile
import shutil
import subprocess

# Track test results
passed = 0
failed = 0
errors = []

# Use the same Python interpreter for subprocesses
PYTHON = sys.executable
DEPLOY_SCRIPT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'deploy.py')
)

SAMPLE_MANIFEST_YAML = """\
version: "1"
type: Application
metadata:
  name: my-app
  description: Test application
  clusterGroups:
    - DDvsns
  lifecycle: production
spec:
  resources:
    - type: virdomain
      name: test-vm
"""

SAMPLE_MANIFEST_WITH_TEST_GROUP_YAML = """\
version: "1"
type: Application
metadata:
  name: my-app
  description: Test application
  clusterGroups:
    - DDvsns
  testClusterGroup: custom-test-group
  lifecycle: production
spec:
  resources:
    - type: virdomain
      name: test-vm
"""


def test(name):
    """Decorator to register and run a test."""
    def decorator(fn):
        global passed, failed
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            print(f"  ❌ {name}: unexpected error: {e}")
            failed += 1
            errors.append(f"{name}: {e}")
        return fn
    return decorator


def clean_env():
    """Return env dict with dummy API key and cleared deploy-specific vars."""
    env = os.environ.copy()
    env['SC_FM_APIKEY'] = 'test-dummy-key-not-real'
    for var in ['FLEET_MANAGER_API_URL', 'TEST_MODE', 'CREATE_TEST_MANIFESTS',
                'SINGLE_MANIFEST', 'PROCESS_ALL_MANIFESTS', 'TEST_CLUSTER_GROUP',
                'TARGET_APPLICATIONS', 'ONLY_COMPILE']:
        env.pop(var, None)
    return env


def run_deploy(*args, env_overrides=None):
    """Run deploy.py with args. Returns (returncode, stdout, stderr)."""
    env = clean_env()
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        [PYTHON, DEPLOY_SCRIPT, *args],
        capture_output=True, text=True, env=env, timeout=15
    )
    return result.returncode, result.stdout, result.stderr


def run_script(script_text, env_overrides=None):
    """Run an inline Python script. Returns (returncode, stdout, stderr)."""
    env = clean_env()
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        [PYTHON, '-c', script_text],
        capture_output=True, text=True, env=env, timeout=15
    )
    return result.returncode, result.stdout, result.stderr


def write_manifest(tmpdir, content=None, filename='test.yaml'):
    """Write manifest YAML string to a temp file and return the path."""
    content = content or SAMPLE_MANIFEST_YAML
    path = os.path.join(tmpdir, filename)
    with open(path, 'w') as f:
        f.write(content)
    return path


# ── Tests ────────────────────────────────────────────────────────────

print(f"\n🧪 deploy.py flag and manifest tests")
print(f"   Python: {PYTHON}")
print(f"   Script: {DEPLOY_SCRIPT}\n")

print("── Argument parsing ──")


@test("--help exits 0 and shows all flags")
def _():
    rc, out, err = run_deploy('--help')
    assert rc == 0, f"exit code {rc}, stderr: {err}"
    for flag in ['--test', '--test-cluster-group', '--create-test-manifests',
                 '--target-apps', '--only-compile', '--dry-run', '--diagnostic',
                 '--skip-deployment-trigger', 'manifest']:
        assert flag in out, f"missing flag '{flag}' in help output"


@test("--only-compile exits 0 without API access")
def _():
    rc, out, err = run_deploy('--only-compile')
    assert rc == 0, f"exit code {rc}, stderr: {err}"
    assert 'ONLY_COMPILE' in out


@test("--test flag sets TEST_MODE indicator in output")
def _():
    rc, out, err = run_deploy('--only-compile', '--test')
    assert rc == 0, f"exit code {rc}, stderr: {err}"
    assert 'TEST_MODE' in out


@test("--create-test-manifests shows indicator in output")
def _():
    rc, out, err = run_deploy('--only-compile', '--create-test-manifests')
    assert rc == 0, f"exit code {rc}, stderr: {err}"
    assert 'CREATE_TEST_MANIFESTS' in out


@test("unknown flag causes exit code 2")
def _():
    rc, _, err = run_deploy('--bogus-flag')
    assert rc == 2, f"expected exit 2, got {rc}"


@test("positional manifest arg activates SINGLE_MANIFEST in output")
def _():
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = write_manifest(tmpdir)
        rc, out, err = run_deploy('--only-compile', manifest_path)
        assert rc == 0, f"exit code {rc}, stderr: {err}"
        assert 'SINGLE_MANIFEST' in out, f"single manifest mode not shown in output: {out}"
    finally:
        shutil.rmtree(tmpdir)


print("\n── Test manifest creation ──")


@test("create_test_manifest produces -test name and correct cluster group")
def _():
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = write_manifest(tmpdir)
        script = f"""\
import sys, os, yaml
sys.path.insert(0, '{os.path.dirname(DEPLOY_SCRIPT)}')
os.environ['SC_FM_APIKEY'] = 'dummy'
os.environ['TEST_CLUSTER_GROUP'] = 'test-group-123'
from deploy import FleetManagerGitOps
deployer = FleetManagerGitOps()
test_path = deployer.create_test_manifest('{manifest_path}')
with open(test_path) as f:
    m = yaml.safe_load(f)
assert m['metadata']['name'] == 'my-app-test', f"name: {{m['metadata']['name']}}"
assert m['metadata']['clusterGroups'] == ['test-group-123'], f"groups: {{m['metadata']['clusterGroups']}}"
assert 'TEST DEPLOYMENT' in m['metadata']['description'], f"desc: {{m['metadata']['description']}}"
assert os.path.exists(test_path), "file not created"
print("PASS")
"""
        rc, out, err = run_script(script, {'TEST_CLUSTER_GROUP': 'test-group-123'})
        assert rc == 0, f"script failed (rc={rc}): {err}"
        assert 'PASS' in out
    finally:
        shutil.rmtree(tmpdir)


@test("create_test_manifest respects testClusterGroup from manifest metadata")
def _():
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = write_manifest(tmpdir, SAMPLE_MANIFEST_WITH_TEST_GROUP_YAML)
        script = f"""\
import sys, os, yaml
sys.path.insert(0, '{os.path.dirname(DEPLOY_SCRIPT)}')
os.environ['SC_FM_APIKEY'] = 'dummy'
os.environ['TEST_CLUSTER_GROUP'] = 'should-be-overridden'
from deploy import FleetManagerGitOps
deployer = FleetManagerGitOps()
test_path = deployer.create_test_manifest('{manifest_path}')
with open(test_path) as f:
    m = yaml.safe_load(f)
assert m['metadata']['clusterGroups'] == ['custom-test-group'], f"groups: {{m['metadata']['clusterGroups']}}"
print("PASS")
"""
        rc, out, err = run_script(script)
        assert rc == 0, f"script failed (rc={rc}): {err}"
        assert 'PASS' in out
    finally:
        shutil.rmtree(tmpdir)


@test("_cleanup_test_manifests removes temp files")
def _():
    tmpdir = tempfile.mkdtemp()
    try:
        manifest_path = write_manifest(tmpdir)
        script = f"""\
import sys, os, yaml
sys.path.insert(0, '{os.path.dirname(DEPLOY_SCRIPT)}')
os.environ['SC_FM_APIKEY'] = 'dummy'
from deploy import FleetManagerGitOps
deployer = FleetManagerGitOps()
test_path = deployer.create_test_manifest('{manifest_path}')
assert os.path.exists(test_path), "should exist before cleanup"
deployer._cleanup_test_manifests()
assert not os.path.exists(test_path), "should be gone after cleanup"
print("PASS")
"""
        rc, out, err = run_script(script)
        assert rc == 0, f"script failed (rc={rc}): {err}"
        assert 'PASS' in out
    finally:
        shutil.rmtree(tmpdir)


# ── Summary ──────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if errors:
    print(f"\nFailures:")
    for e in errors:
        print(f"  - {e}")
print()
sys.exit(1 if failed else 0)

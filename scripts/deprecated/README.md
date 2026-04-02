# Deprecated Scripts

These scripts have been superseded by consolidated flags in the main tools.

## Deploy variants → `deploy.py`

| Old Script | Replacement |
|-----------|-------------|
| `test-deploy.py` | `deploy.py --test --create-test-manifests [manifest]` |
| `production-deploy.py` | `deploy.py` (production is the default mode) |
| `deploy-with-test-mode.py` | `deploy.py --test --create-test-manifests --test-cluster-group <group>` |

## Cleanup variants → `cleanup-test-apps.py`

| Old Script | Replacement |
|-----------|-------------|
| `full-test-cleanup.py` | Use `cleanup-test-apps.py` (VM cleanup consolidation pending) |
| `delete-test-deployments.py` | Was a one-time hardcoded cleanup script |

## Restore variants → `restore-container-app.py`

| Old Script | Replacement |
|-----------|-------------|
| `restore-app-from-container.py` | Use `restore-container-app.py` |

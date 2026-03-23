# Project Kraken — Fleet Manager GitOps

## What This Is

A GitOps prototype (codename "Project Kraken") for managing Scale Computing Fleet Manager deployments. YAML manifests committed to this Git repo drive VM and container deployments across HC3 cluster groups via the Fleet Manager REST API, orchestrated by GitHub Actions CI/CD.

Built as a personal beta/prototype with cursor.ai (Sept–Nov 2025). Single contributor: Dave Demlow.

## Architecture

```
Git Push/PR → GitHub Actions → Python scripts → Fleet Manager API v2
                                    │
                          compile_manifests.py
                         (containers/ → _compiled/)
```

**Core components:**
- `scripts/deploy.py` — Main deployment engine (FleetManagerGitOps class). Reads manifests, calls FM API to create/update applications and deployments, triggers releases. ~1,100 lines.
- `scripts/compile_manifests.py` — Transforms `ContainerDefinition` + `RuntimeConfiguration` YAML into full `Application` manifests (from `manifests/containers/` to `manifests/_compiled/`).
- `scripts/validate-manifests.py` — YAML syntax and structure validation.
- `.github/workflows/production-deployment.yml` — Deploys on push to master.
- `.github/workflows/test-deployment.yml` — Deploys on PRs to test cluster group.
- `manifests/` — Application definitions (VMs, containers, examples, templates).

## Manifest Lifecycle States

Manifests use a `metadata.lifecycle` field to control deployment behavior:

| State | Behavior |
|-------|----------|
| `draft` | Skipped in all deployments (work in progress) |
| `testonly` | Deployed only in TEST_MODE (PR workflow) |
| `production` | Deployed to production cluster groups (default) |
| `undeploy` | Triggers cleanup and removal |

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SC_FM_APIKEY` | Yes | — | Fleet Manager API authentication key |
| `FLEET_MANAGER_API_URL` | No | `https://api.scalecomputing.com/api/v2` | FM API base URL |
| `CLUSTER_GROUP_NAME` | No | `DDvsns` | Default production cluster group |
| `TEST_MODE` | No | `false` | Enable test-only manifest deployment |
| `PROCESS_ALL_MANIFESTS` | No | `false` | Process all manifests, not just changed |
| `TARGET_APPLICATIONS` | No | — | Comma-separated app names to deploy |
| `ONLY_COMPILE` | No | `false` | Compile manifests without deploying |
| `SKIP_DEPLOYMENT_TRIGGER` | No | `false` | Update apps without triggering deployment |
| `DIAGNOSTIC_MODE` | No | `false` | Enhanced error checking |
| `MONITOR_DEPLOYMENTS` | No | `false` | Monitor deployment progress after triggering |
| `BAIL_ON_DESTRUCTIVE_CHANGES` | No | `false` | Fail on destructive changes (true in prod workflow) |

## Hardcoded Defaults

These values are embedded in scripts and manifests — be aware when working in different environments:

- **Production cluster group**: `DDvsns`
- **Test cluster group**: `dd_szt15b`
- **API URL**: `https://api.scalecomputing.com/api/v2`
- **Org ID**: `63b8337ec6939fdfb0f716af`
- **VM passwords**: Literal `"password"` in cloud-init configs (intentional for dev/test)
- **SSH keys**: Ed25519 public key for `ddemlow@scalecomputing.com` in several manifests

## Development Commands

```bash
# Validate all manifests
python scripts/validate-manifests.py

# Compile container definitions into full application manifests
python scripts/compile_manifests.py

# Test API connectivity (requires SC_FM_APIKEY)
python scripts/test-api-connection.py

# Deploy (requires SC_FM_APIKEY)
python scripts/deploy.py
python scripts/deploy.py --target-apps "my-app"
python scripts/deploy.py --only-compile
python scripts/deploy.py --diagnostic
python scripts/deploy.py --dry-run

# Monitor deployments
python scripts/monitor-deployment-releases.py

# Cleanup test deployments
python scripts/cleanup-test-apps.py
python scripts/full-test-cleanup.py
```

## Code Conventions

- **Python 3.9+** (target upgrade to 3.11+)
- **Dependencies**: `requests` + `PyYAML` only (see `requirements.txt`)
- **No test framework** currently — validation scripts and CI test deployments serve as testing
- **Console output** uses emoji prefixes for status (e.g., `✅`, `❌`, `⚠️`, `📋`)
- **API auth**: `api-key` header (NOT `Authorization: Bearer` — CHANGES.md has a documentation bug on this)
- **User-Agent**: `fleet-manager-gitops/2.0`

## Known Issues

See [GitHub Issues](https://github.com/ddemlow/fleet-manager-gitops/issues) for the full backlog. Key items:
- `deploy.py` is a 1,100-line monolith that should be refactored into modules
- Multiple duplicate deploy scripts (test-deploy.py, production-deploy.py, deploy-with-test-mode.py) that should be consolidated
- Python 3.9 is past EOL — needs upgrade to 3.11+
- Documentation has stale/overlapping files from cursor.ai generation
- `action.log` is committed to the repo and should be removed

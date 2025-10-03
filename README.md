# Fleet Manager GitOps Repository

This repository demonstrates a GitOps workflow for deploying applications to Scale Computing Fleet Manager using GitHub Actions and the Fleet Manager API directly.

## 🚀 **What is GitOps?**

GitOps is a methodology that uses Git as the single source of truth for declarative infrastructure and applications. This repository allows you to:

- **Store deployment manifests** in Git
- **Automatically deploy** when you push changes
- **Version control** your infrastructure
- **Collaborate** on deployments through pull requests

## 📁 **Repository Structure**

```
gitops/
├── .github/workflows/
│   └── deploy.yml                 # GitHub Actions workflow
├── manifests/                     # Application manifests
│   ├── example-vm.yaml
│   └── nginx-deployment.yaml
├── scripts/
│   ├── deploy.py                  # Main deployment script
│   └── validate-manifests.py      # Manifest validation
└── README.md                      # This file
```

## 🛠️ **Setup Instructions**

### **Step 1: Create GitHub Repository**

1. Create a new repository on GitHub
2. Clone this repository structure to your new repo
3. Push the initial commit

```bash
git clone <your-new-repo-url>
cd <your-repo-name>
# Copy the gitops/ contents to your repo
git add .
git commit -m "Initial GitOps setup"
git push origin main
```

### **Step 2: Configure GitHub Secrets**

Go to your repository settings → Secrets and variables → Actions, and add these secrets:

#### **Required Secrets:**
- `SC_FM_APIKEY`: Your Fleet Manager API key

#### **Optional Secrets:**
- `FLEET_MANAGER_API_URL`: Fleet Manager API URL (default: `https://api.scalecomputing.com/api/v2`)

### **Step 3: Test the Workflow**

1. **Make a small change** to a manifest file
2. **Commit and push** the change
3. **Check the Actions tab** to see the deployment in progress
4. **Verify deployment** in Fleet Manager

## 📝 **Manifest Format**

Your deployment manifests should follow this structure - standard Fleet Manager application manifest but can also include the additional metadata to automatially create one or more "Application Deployment" relationships

  clusterGroups:
    - DDvsns

```yaml
version: "1"
type: "Application"
metadata:
  name: "gitops-example-vm2"
  description: "Example virtual machine deployment"
  clusterGroups:
    - DDvsns
  labels:
    - development

spec:
  assets:
    - name: test-disk
      type: virtual_disk
      format: raw
      url: https://storage.googleapis.com/demo-bucket-lfm/netboot.xyz.img
  resources:
    - name: gitops-example-vm2
      type: virdomain
      spec:
        description: A simple VM for testing
        cpu: 1
        memory: "2147483648"
        machine_type: bios
        storage_devices:
          - name: cdrom1
            type: ide_cdrom
            boot: 1
          - name: disk1
            source: test-disk
            boot: 2
          - name: disk2
            type: virtio_disk
            capacity: 100000000000
        network_devices:
          - name: nic1
            type: virtio
        tags:
          - kraken
          - test
        state: running
```

## 🔄 **GitOps Workflow**

### **Automatic Deployment:**
1. **Edit manifest** files in `manifests/`
2. **Commit and push** changes
3. **GitHub Actions** automatically:
   - Validates YAML syntax
   - Validates manifest structure
   - Deploys to Fleet Manager
   - Notifies on success/failure

### **Manual Deployment:**
```bash
# Run deployment script locally (normal deployment)
python scripts/deploy.py

# Deploy only specific applications
python scripts/deploy.py --target-apps nginx,nginx2

# Update applications but don't trigger deployments (useful for testing)
python scripts/deploy.py --skip-deployment-trigger

# Only compile manifests without deploying
python scripts/deploy.py --only-compile

# Combine multiple controls
python scripts/deploy.py --target-apps nginx --skip-deployment-trigger
```

### **Environment Variable Controls:**
```bash
# Set target applications
export TARGET_APPLICATIONS=nginx,nginx2
python scripts/deploy.py

# Skip deployment triggers
export SKIP_DEPLOYMENT_TRIGGER=true
python scripts/deploy.py

# Only compile mode
export ONLY_COMPILE=true
python scripts/deploy.py
```

## 📊 **Monitoring Deployments**

### **GitHub Actions:**
- Go to the **Actions** tab in your repository
- View deployment logs and status
- See validation results

### **Fleet Manager:**
- Check the **Deployments** section
- View application status
- Monitor job progress

## 🛠️ **Development Workflow**

### **1. Create New Application:**
```bash
# Create new manifest
cp manifests/example-vm.yaml manifests/my-new-app.yaml
# Edit the manifest
vim manifests/my-new-app.yaml
# Commit and push
git add manifests/my-new-app.yaml
git commit -m "Add my-new-app deployment"
git push origin main
```

### **2. Update Existing Application:**
```bash
# Edit existing manifest
vim manifests/nginx-deployment.yaml
# Commit and push
git add manifests/nginx-deployment.yaml
git commit -m "Update nginx configuration"
git push origin main
```

### **3. Rollback Changes:**
```bash
# Revert to previous version
git revert <commit-hash>
git push origin main
```

## 🎯 **Deployment Controls**

### **Problem Solved:**
The enhanced deployment script now prevents unwanted redeployments when editing unrelated manifests. Previously, editing `boot_iso.yaml` would cause all container applications to redeploy unnecessarily.

### **New Controls:**

#### **Target Applications (`--target-apps`)**
Deploy only specific applications:
```bash
python scripts/deploy.py --target-apps nginx,nginx2
```

#### **Skip Deployment Trigger (`--skip-deployment-trigger`)**
Update applications in Fleet Manager but don't trigger actual deployments:
```bash
python scripts/deploy.py --skip-deployment-trigger
```

#### **Only Compile (`--only-compile`)**
Only compile manifests without any Fleet Manager operations:
```bash
python scripts/deploy.py --only-compile
```

### **GitHub Actions Integration:**
Use the enhanced workflow (`.github/workflows/enhanced-deploy.yml`) with manual dispatch options:
- Target specific applications
- Skip deployment triggers
- Only compile mode

### **Environment Variables:**
Set these in your GitHub Actions secrets or local environment:
- `TARGET_APPLICATIONS`: Comma-separated list of applications
- `SKIP_DEPLOYMENT_TRIGGER`: Set to `true` to skip deployment triggers
- `ONLY_COMPILE`: Set to `true` to only compile manifests

## 🔍 **Troubleshooting**

### **Common Issues:**

#### **Deployment Fails:**
- Check GitHub Actions logs
- Verify API keys are correct

#### **Manifest Validation Fails:**
- Check YAML syntax
- Verify required fields are present
- Use `python scripts/validate-manifests.py` locally

#### **Deleted Manifest Still Appears in CI:**
- Push payloads can include deleted files. The deploy script now skips missing files and logs `Skipping deleted files: ...`. Deleting a manifest does not currently delete its corresponding Deployment Application or Deployment in Fleet Manager. This may be added in the future.

#### **Application Not Found:**
- Check application name in manifest
- Verify it exists in Fleet Manager
- Check deployment status

### **Debug Commands:**
```bash
# Test Fleet Manager API connectivity
curl -H "Authorization: Bearer your-api-key" https://api.scalecomputing.com/api/v2/clusters

# Validate manifests locally
python scripts/validate-manifests.py

# Test deployment locally
export SC_FM_APIKEY="your-fleet-manager-api-key"
python scripts/deploy.py
```

## 📚 **Advanced Usage**

### **ContainerDefinition + runtime.yaml (Compiler Workflow)**

This repo supports a simplified authoring workflow using a compiler that turns a `ContainerDefinition` + shared `runtime.yaml` into a full Fleet Manager `Application` manifest.

Folders:
- `manifests/containers/*.container.yaml` → container apps
- `manifests/containers/runtime_configuration/runtime.yaml` → shared runtime defaults/policies (override per-app with `<name>.runtime.yaml` if needed)
- Compiled output: `manifests/_compiled/*.yaml` (ignored by Git)

ContainerDefinition (example):
```yaml
version: "1"
type: "ContainerDefinition"
metadata:
  name: "nginx"
  clusterGroups: [DDvsns]
  labels: [scruntime, nginx]
spec:
  runtime:                  # optional per-app overrides
    vcpus: 2
    memory: "2Gi"
    disk:
      capacity: "40Gi"
  containers:
    - name: "nginx"
      image: "docker.io/library/nginx:1.27-alpine"
      ports: ["80:80"]
      mounts:
        - hostPath: "/var/edge/www"
          mountPath: "/usr/share/nginx/html"
          selinuxRelabel: true
  content:
    - path: "/var/edge/www/index.html"
      mode: "0644"
      data: |
        <!doctype html>
        <html>...</html>
```

runtime.yaml (shared defaults and policies):
```yaml
version: "1"
type: "RuntimeConfiguration"
metadata:
  name: "default-runtime"
spec:
  cloudInit:
    ssh:
      passwordAuth: true
      disableRoot: false
  runtime:
    vcpus: 2
    memory: "2Gi"
    disk:
      name: "rootdisk"
      capacity: "40Gi"
      format: "raw"
      url: "https://.../OpenStack-Cloud.raw"
  network:
    - name: "eth0"
      type: "virtio"
  vmState: "running"
  policies:
    enablePodmanSocket: true
    enableAutoUpdateTimer: true
    setupQemuGuestAgent: true
    rebootAfterQga: true
    autoUpdateLabel: true
```

How compilation works:
- The compiler merges `ContainerDefinition` with `runtime.yaml`
- `spec.runtime` in the container overrides values from `runtime.yaml`
- Multi-line `cloud_init_data.user_data` is rendered as a readable YAML block
- Output is written to `manifests/_compiled/<name>.yaml`

Run locally:
```bash
python scripts/compile_manifests.py
python scripts/deploy.py
```

Notes:
- Place per-app runtime at `manifests/containers/runtime_configuration/<name>.runtime.yaml` to override shared defaults.
- Deleting source files does not delete resources in Fleet Manager yet (see Known limitations).

### **Environment-Specific Deployments:**
Create different branches for different environments:
- `main` → Production
- `develop` → Development
- `staging` → Staging

### **Conditional Deployments:**
Modify `.github/workflows/deploy.yml` to add conditions:
```yaml
if: github.ref == 'refs/heads/main'
```

### **Custom Validation:**
Add custom validation rules in `scripts/validate-manifests.py`

## 🧪 **Testing Workflow**

All production deployments must be tested first in the `dd_szt15b` cluster group before being approved for production.

### Process:
1. **Create Pull Request** → Changes automatically deployed to `dd_szt15b`
2. **Human Verification** → Reviewer tests deployment in Fleet Manager UI
3. **Approve PR** → Only after successful testing
4. **Production Deployment** → Automatic deployment to production cluster groups

See [TESTING_WORKFLOW.md](TESTING_WORKFLOW.md) for detailed documentation.

## 🧹 **Deployment Cleanup**

When Fleet Manager deployments get stuck or need to be reset, use the automated cleanup script:

```bash
# Clean up using compiled manifest
./scripts/cleanup.sh manifests/_compiled/nginx2.yaml

# Clean up using source container manifest
./scripts/cleanup.sh manifests/containers/nginx3.container.yaml

# Clean up using just the app name (for GitHub-compiled containers)
./scripts/cleanup.sh nginx3

# Clean up with custom wait time (5 minutes)
./scripts/cleanup.sh nginx2 5

# Clean up without waiting (verify manually)
./scripts/cleanup.sh nginx3 0
```

**What it does:**
1. Creates a temporary cleanup manifest with `resources: []`
2. Deploys it to trigger Fleet Manager cleanup (VM deletion)
3. **Immediately restores** the original application definition (while cleanup runs)
4. Waits for cleanup deployment to complete (optional)
5. Removes temporary files
6. Application is ready for normal deployment

**Key insight:** The application definition can be restored immediately after submitting the cleanup deployment, while the cleanup runs in the background.

**When to use:**
- Deployments are stuck or failed
- VMs need to be completely removed
- Starting fresh with a deployment
- Fleet Manager state is inconsistent

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** locally
5. **Submit** a pull request

## 📞 **Support**

- **GitHub Issues**: Report bugs and feature requests
- **Fleet Manager Docs**: [Scale Computing Documentation](https://docs.scalecomputing.com)

---

**Happy GitOps! 🚀**

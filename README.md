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
├── manifests/                      # Application definitions (YAML)
│   └── k3s-cluster.yaml
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

Your deployment manifests should follow this structure:

```yaml
version: "1"
type: "Application"
metadata:
  name: "my-app"
  description: "My application description"
  labels:
    environment: "production"
    team: "platform"
spec:
  assets:
    - name: "app-disk"
      type: "virtual_disk"
      format: "qcow2"
      size: "20Gi"
      url: "https://example.com/image.img"
    - name: "app-vm"
      type: "virtual_machine"
      vcpus: 2
      memory: "4Gi"
      disks:
        - name: "app-disk"
          size: "20Gi"
      networks:
        - name: "default"
          type: "bridge"
      userData: |
        #cloud-config
        users:
          - name: ubuntu
            sudo: ALL=(ALL) NOPASSWD:ALL
        packages:
          - docker.io
        runcmd:
          - systemctl enable docker
          - systemctl start docker
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
# Run deployment script locally
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

## 🔍 **Troubleshooting**

### **Common Issues:**

#### **Deployment Fails:**
- Check GitHub Actions logs
- Verify API keys are correct
- Ensure MCP server is running

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

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** locally
5. **Submit** a pull request

## 📞 **Support**

- **GitHub Issues**: Report bugs and feature requests
- **Fleet Manager Docs**: [Scale Computing Documentation](https://docs.scalecomputing.com)
- **MCP Server**: Check the MCP server logs for API issues

---

**Happy GitOps! 🚀**

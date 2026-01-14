# 🚀 Quick Start Guide

Get your Fleet Manager GitOps workflow running in 5 minutes!

## ⚡ **5-Minute Setup**

### **1. Create (or fork) a GitHub repository**
```bash
# Option A: use this repo as a template / fork it in GitHub, then clone
git clone https://github.com/yourusername/fleet-manager-gitops.git
cd fleet-manager-gitops
```

### **2. Set GitHub Secrets**
Go to **Settings** → **Secrets and variables** → **Actions** and add:

- **`SC_FM_APIKEY`**: Your Fleet Manager API key

### **3. Test a deployment**
```bash
# Make a small change to a manifest
echo "# Test comment" >> manifests/example-vm.yaml

# Commit and push
git add .
git commit -m "Test GitOps deployment"
git push origin <default-branch>  # usually master or main
```

### **4. Check Results**
- Go to **Actions** tab in GitHub
- Check Fleet Manager for new applications
- 🎉 **You're done!**

## 📁 **Repository Structure**

```
fleet-manager-gitops/
├── .github/workflows/
│   ├── validate-manifests.yml      # PR manifest validation
│   ├── test-deployment.yml         # PR test deployment
│   ├── production-deployment.yml   # Push-to-default-branch production deployment
│   └── security-scan.yml           # PR security scan (Trivy + Trufflehog)
├── manifests/                      # Application manifests
│   ├── example-vm.yaml
│   └── nginx-deployment.yaml
├── scripts/                        # Deployment scripts
│   ├── deploy.py
│   └── validate-manifests.py
└── README.md
```

## 🔧 **What Happens When You Push?**

1. **GitHub Actions** triggers
2. **Validates** your YAML manifests
3. **Deploys** to Fleet Manager via API
4. **Notifies** you of success/failure

## 📝 **Creating Your First Application**

1. **Create a new manifest**:
   ```yaml
   # manifests/my-app.yaml
   version: "1"
   type: "Application"
   metadata:
     name: "my-app"
     description: "My first GitOps application"
   spec:
     assets:
       - name: "app-disk"
         type: "virtual_disk"
         format: "qcow2"
         size: "20Gi"
         url: "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"
   ```

2. **Commit and push**:
   ```bash
   git add manifests/my-app.yaml
   git commit -m "Add my first application"
   git push origin <default-branch>  # usually master or main
   ```

3. **Watch it deploy** in GitHub Actions!

## 🛠️ **Common Commands**

```bash
# Validate manifests locally
python scripts/validate-manifests.py

# Test deployment locally
export SC_FM_APIKEY="your-fleet-manager-api-key"
python scripts/deploy.py

# Check GitHub Actions
# Go to Actions tab in your repository
```

## 🚨 **Troubleshooting**

### **Deployment Fails?**
- Check GitHub Actions logs
- Verify API keys are set
- Ensure Fleet Manager API is accessible

### **Manifest Invalid?**
- Check YAML syntax
- Verify required fields
- Use local validation

### **Need Help?**
- Check the full [SETUP.md](SETUP.md) guide
- Read the [README.md](README.md) for detailed documentation
- Look at example manifests in `manifests/`

---

**Happy GitOps! 🎉**

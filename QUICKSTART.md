# 🚀 Quick Start Guide

Get your Fleet Manager GitOps workflow running in 5 minutes!

## ⚡ **5-Minute Setup**

### **1. Create GitHub Repository**
```bash
# Create a new repository on GitHub
# Clone it locally
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

### **2. Copy GitOps Files**
```bash
# Copy all files from the gitops/ directory to your repo
# (You'll need to copy manually from this repository)
```

### **3. Set GitHub Secrets**
Go to **Settings** → **Secrets and variables** → **Actions** and add:

- **`SC_FM_APIKEY`**: Your Fleet Manager API key

### **4. Test Deployment**
```bash
# Make a small change to a manifest
echo "# Test comment" >> manifests/example-vm.yaml

# Commit and push
git add .
git commit -m "Test GitOps deployment"
git push origin main
```

### **5. Check Results**
- Go to **Actions** tab in GitHub
- Check Fleet Manager for new applications
- 🎉 **You're done!**

## 📁 **Repository Structure**

```
your-repo/
├── .github/workflows/deploy.yml    # GitHub Actions workflow
├── manifests/                      # Your application manifests
│   ├── example-vm.yaml
│   └── nginx-deployment.yaml
├── applications/                   # Complex applications
│   └── k3s-cluster.yaml
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
   git push origin main
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
- Look at example manifests in `manifests/` and `applications/`

---

**Happy GitOps! 🎉**

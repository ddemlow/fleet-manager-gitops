# GitOps Setup Guide

This guide walks you through setting up a complete GitOps workflow for Fleet Manager deployments.

## 🎯 **Prerequisites**

- GitHub account
- Fleet Manager API access
- MCP server running (or access to one)
- Basic knowledge of YAML and Git

## 📋 **Step-by-Step Setup**

### **Step 1: Create GitHub Repository**

1. **Go to GitHub** and create a new repository
2. **Name it** something like `fleet-manager-gitops`
3. **Make it public** or private (your choice)
4. **Initialize** with README (optional)

### **Step 2: Clone and Setup Repository**

```bash
# Clone your new repository
git clone https://github.com/yourusername/fleet-manager-gitops.git
cd fleet-manager-gitops

# Create the directory structure
mkdir -p .github/workflows
mkdir -p manifests
mkdir -p applications
mkdir -p scripts

# Copy the files from this gitops/ directory to your repo
# (You'll need to copy the files manually)
```

### **Step 3: Configure GitHub Secrets**

1. **Go to your repository** on GitHub
2. **Click Settings** → **Secrets and variables** → **Actions**
3. **Click "New repository secret"** and add:

#### **Required Secrets:**

**`SC_FM_APIKEY`**
- **Value**: Your Fleet Manager API key
- **Description**: API key for Fleet Manager API access

#### **Optional Secrets:**

**`FLEET_MANAGER_API_URL`**
- **Value**: `https://api.scalecomputing.com/api/v2` (default)
- **Description**: Fleet Manager API URL

### **Step 4: Test the Setup**

1. **Make a small change** to a manifest file:
   ```bash
   # Edit a manifest file
   vim manifests/example-vm.yaml
   # Change the name or description
   ```

2. **Commit and push**:
   ```bash
   git add .
   git commit -m "Test GitOps deployment"
   git push origin main
   ```

3. **Check GitHub Actions**:
   - Go to the **Actions** tab in your repository
   - You should see a workflow run
   - Check the logs for any errors

### **Step 5: Verify Deployment**

1. **Check Fleet Manager**:
   - Go to your Fleet Manager dashboard
   - Look for new applications in the Deployments section
   - Check if the deployment was successful

2. **Check MCP Server Logs**:
   - Look at your MCP server logs
   - Verify API calls were made
   - Check for any errors

## 🔧 **Configuration Options**

### **Custom MCP Server URL**

If you're running your own MCP server:

1. **Update the workflow** in `.github/workflows/deploy.yml`:
   ```yaml
   env:
     MCP_SERVER_URL: https://your-mcp-server.com/api/v2
   ```

2. **Or set it as a secret** in GitHub

### **Custom Deployment Triggers**

Modify `.github/workflows/deploy.yml` to change when deployments happen:

```yaml
on:
  push:
    branches: [ main, develop ]  # Deploy on these branches
    paths:
      - 'manifests/**'           # Only when manifests change
      # paths under manifests trigger the workflow
```

### **Environment-Specific Deployments**

Create different workflows for different environments:

```yaml
# .github/workflows/deploy-production.yml
on:
  push:
    branches: [ main ]
    paths: [ 'manifests/**' ]

# .github/workflows/deploy-staging.yml  
on:
  push:
    branches: [ develop ]
    paths: [ 'manifests/**' ]
```

## 🧪 **Testing Your Setup**

### **Test 1: Basic Deployment**

1. **Create a simple manifest**:
   ```yaml
   # manifests/test-app.yaml
   version: "1"
   type: "Application"
   metadata:
     name: "test-app"
     description: "Test application"
   spec:
     assets:
       - name: "test-disk"
         type: "virtual_disk"
         format: "qcow2"
         size: "10Gi"
         url: "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"
   ```

2. **Commit and push**:
   ```bash
   git add manifests/test-app.yaml
   git commit -m "Add test application"
   git push origin main
   ```

3. **Check the results**:
   - GitHub Actions should run
   - Fleet Manager should show the new application

### **Test 2: Update Existing Application**

1. **Edit an existing manifest**:
   ```bash
   vim manifests/test-app.yaml
   # Change the description or add labels
   ```

2. **Commit and push**:
   ```bash
   git add manifests/test-app.yaml
   git commit -m "Update test application"
   git push origin main
   ```

3. **Verify the update**:
   - Check Fleet Manager for the updated application
   - Look for a new version number

### **Test 3: Error Handling**

1. **Create an invalid manifest**:
   ```yaml
   # manifests/invalid-app.yaml
   version: "1"
   # Missing required fields
   ```

2. **Commit and push**:
   ```bash
   git add manifests/invalid-app.yaml
   git commit -m "Add invalid manifest"
   git push origin main
   ```

3. **Check the error handling**:
   - GitHub Actions should fail
   - You should see validation errors
   - No deployment should happen

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **"API key required" Error**
- **Check**: GitHub secrets are set correctly
- **Verify**: API keys are valid
- **Test**: MCP server is accessible

#### **"Deployment failed" Error**
- **Check**: Fleet Manager API is accessible
- **Verify**: Application name is unique
- **Look**: At MCP server logs for details

#### **"Manifest validation failed" Error**
- **Check**: YAML syntax is correct
- **Verify**: Required fields are present
- **Test**: Run validation locally

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

## 📚 **Next Steps**

Once your basic setup is working:

1. **Add more applications** to your manifests
2. **Set up environment-specific deployments**
3. **Configure monitoring and alerting**
4. **Add custom validation rules**
5. **Integrate with your CI/CD pipeline**

## 🤝 **Getting Help**

- **GitHub Issues**: Report bugs in your repository
- **Fleet Manager Docs**: [Scale Computing Documentation](https://docs.scalecomputing.com)
- **MCP Server**: Check the MCP server documentation

---

**Your GitOps workflow is now ready! 🎉**

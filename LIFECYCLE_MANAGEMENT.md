# 🔄 Manifest Lifecycle Management

This document describes the manifest lifecycle management system that allows you to control how applications are deployed, tested, and managed through different stages of their development.

## 🎯 **Overview**

The Fleet Manager GitOps system supports four lifecycle states that control how manifests are processed:

- **`draft`** - Skip deployment (work in progress)
- **`testonly`** - Deploy only during testing
- **`production`** - Deploy to production (default)
- **`undeploy`** - Trigger cleanup and removal

## 📋 **Lifecycle States**

### 🔧 **Draft State**
Manifests in draft state are skipped during deployment, allowing you to work on them without affecting any environments.

```yaml
metadata:
  name: my-app
  lifecycle: draft  # Will be skipped during deployment
```

**Behavior:**
- ✅ **Test Mode**: Skipped
- ✅ **Production Mode**: Skipped
- 💡 **Use Case**: Work in progress, incomplete features

### 🧪 **Test Only State**
Manifests in test-only state are deployed during testing but skipped during production deployment.

```yaml
metadata:
  name: my-test-app
  lifecycle: testonly  # Only deployed during testing
```

**Behavior:**
- ✅ **Test Mode**: Deployed to test cluster group
- ❌ **Production Mode**: Skipped
- 💡 **Use Case**: Experimental features, demos, temporary applications

### 🚀 **Production State**
Manifests in production state are deployed to production environments (default behavior).

```yaml
metadata:
  name: my-prod-app
  lifecycle: production  # Deployed to production
```

**Behavior:**
- ✅ **Test Mode**: Deployed to test cluster group
- ✅ **Production Mode**: Deployed to production cluster groups
- 💡 **Use Case**: Stable applications ready for production use

### 🗑️ **Undeploy State**
Manifests in undeploy state trigger cleanup and removal of existing deployments.

```yaml
metadata:
  name: my-old-app
  lifecycle: undeploy  # Will trigger cleanup
```

**Behavior:**
- 🗑️ **Test Mode**: Cleans up test deployments
- 🗑️ **Production Mode**: Cleans up production deployments
- 💡 **Use Case**: Removing old applications, resetting demos

## 🔄 **Lifecycle Workflow Examples**

### **Development Workflow**
1. **Start with draft**:
   ```yaml
   metadata:
     lifecycle: draft
   ```

2. **Move to testing**:
   ```yaml
   metadata:
     lifecycle: testonly
   ```

3. **Promote to production**:
   ```yaml
   metadata:
     lifecycle: production
   ```

### **Demo Reset Workflow**
1. **Mark for cleanup**:
   ```yaml
   metadata:
     lifecycle: undeploy
   ```

2. **Create new version**:
   ```yaml
   metadata:
     name: demo-v2
     lifecycle: production
   ```

## ⚠️ **Destructive Change Detection**

The system automatically detects potentially destructive changes that could cause deployment issues:

### **Cloud-init Changes**
Changes to cloud-init `user_data` after initial deployment can cause problems:

```yaml
# This change will trigger a warning
cloud_init_data:
  user_data: |
    #cloud-config
    # Changing this after deployment may cause issues
    users:
      - name: newuser  # ← This change triggers warning
```

### **VM Name Changes**
Changing VM names after deployment can cause resource conflicts:

```yaml
resources:
  - name: old-vm-name    # ← Changing this triggers warning
    type: virdomain
```

### **Warning Behavior**
- **Test Mode**: Warnings shown, deployment continues
- **Production Mode**: Warnings shown, deployment fails (configurable)

## 🛠️ **Configuration Options**

### **Environment Variables**

#### **`BAIL_ON_DESTRUCTIVE_CHANGES`**
Controls whether to stop deployment on destructive changes:

```bash
# Stop deployment on destructive changes (production default)
export BAIL_ON_DESTRUCTIVE_CHANGES=true

# Continue deployment with warnings (test default)
export BAIL_ON_DESTRUCTIVE_CHANGES=false
```

#### **`TEST_MODE`**
Enables test mode behavior:

```bash
# Test mode - deploys testonly manifests, continues on destructive changes
export TEST_MODE=true

# Production mode - skips testonly manifests, fails on destructive changes
export TEST_MODE=false
```

## 📊 **GitHub Actions Integration**

### **Test Deployment (PR)**
- **Draft**: Skipped
- **Testonly**: Deployed to test cluster group
- **Production**: Skipped
- **Undeploy**: Cleans up test deployments
- **Destructive Changes**: Warnings only

### **Production Deployment (Default Branch)**
- **Draft**: Skipped
- **Testonly**: Skipped
- **Production**: Deployed to production
- **Undeploy**: Cleans up production deployments
- **Destructive Changes**: Fails deployment

## 🎯 **Best Practices**

### **Development Process**
1. **Start with `draft`** for new applications
2. **Move to `testonly`** when ready for testing
3. **Promote to `production`** when stable
4. **Use `undeploy`** to clean up old versions

### **Demo Management**
1. **Create demo with `testonly`** lifecycle
2. **Use `undeploy`** to reset demo
3. **Recreate with `production`** lifecycle

### **Safe Changes**
- ✅ CPU/Memory changes
- ✅ Storage capacity changes
- ✅ Network configuration changes
- ✅ Tag/label changes

### **Destructive Changes** (Require Caution)
- ⚠️ Cloud-init user_data changes
- ⚠️ VM name changes
- ⚠️ Storage device type changes
- ⚠️ Network interface changes

## 🔍 **Monitoring and Debugging**

### **Check Lifecycle State**
```bash
# View lifecycle state in deployment logs
python scripts/deploy.py --target-apps my-app
```

### **Force Deployment** (Override Lifecycle)
```bash
# Deploy draft manifest by removing lifecycle temporarily
# (Not recommended for production)
```

### **Check for Destructive Changes**
```bash
# Set bail flag to see destructive changes without deploying
export BAIL_ON_DESTRUCTIVE_CHANGES=true
python scripts/deploy.py --target-apps my-app
```

## 📝 **Example Manifests**

### **Draft Application**
```yaml
type: Application
version: '1'
metadata:
  name: my-draft-app
  description: Work in progress application
  lifecycle: draft
  clusterGroups:
    - DDvsns
spec:
  # ... application spec
```

### **Test Only Application**
```yaml
type: Application
version: '1'
metadata:
  name: my-test-app
  description: Testing only application
  lifecycle: testonly
  clusterGroups:
    - DDvsns
spec:
  # ... application spec
```

### **Production Application**
```yaml
type: Application
version: '1'
metadata:
  name: my-prod-app
  description: Production ready application
  lifecycle: production
  clusterGroups:
    - DDvsns
spec:
  # ... application spec
```

### **Undeploy Application**
```yaml
type: Application
version: '1'
metadata:
  name: my-old-app
  description: Application to be removed
  lifecycle: undeploy
  clusterGroups:
    - DDvsns
spec:
  # ... application spec (will be ignored during cleanup)
```

## 🚨 **Troubleshooting**

### **Manifest Not Deploying**
1. Check lifecycle state: `grep lifecycle manifests/my-app.yaml`
2. Verify test mode setting: `echo $TEST_MODE`
3. Check for destructive changes in logs

### **Destructive Change Warnings**
1. Review the specific changes mentioned
2. Consider if changes are necessary
3. Use `BAIL_ON_DESTRUCTIVE_CHANGES=false` for testing
4. Plan deployment strategy for production

### **Undeploy Not Working**
1. Verify lifecycle is set to `undeploy`
2. Check that application exists in Fleet Manager
3. Review deployment deletion logs
4. Check for active deployments that prevent deletion

## 🎉 **Summary**

The manifest lifecycle management system provides:

- **🎯 Controlled deployment** based on development stage
- **🧪 Safe testing** with separate test-only applications
- **🗑️ Easy cleanup** for demo resets and application removal
- **⚠️ Destructive change detection** to prevent deployment issues
- **🔄 Flexible workflow** supporting various development patterns

This system makes Fleet Manager GitOps workflows safer, more predictable, and easier to manage across different environments and use cases.

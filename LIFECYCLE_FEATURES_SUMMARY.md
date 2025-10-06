# 🔄 Manifest Lifecycle Management Features Summary

This document summarizes the new manifest lifecycle management features added to the Fleet Manager GitOps repository.

## 🎯 **New Features Overview**

### ✅ **1. Manifest Lifecycle States**
- **Four lifecycle states**: `draft`, `testonly`, `production`, `undeploy`
- **Controlled deployment behavior** based on lifecycle state
- **Backward compatibility** with existing manifests (defaults to `production`)

### ✅ **2. Skip/Ignore Capability**
- **Draft state**: Manifests are completely skipped during deployment
- **Test-only state**: Manifests deployed only during testing, skipped in production
- **Flexible workflow** for work-in-progress and experimental features

### ✅ **3. Cleanup via Git PR**
- **Undeploy lifecycle**: Triggers automatic cleanup of existing deployments
- **GitOps-based cleanup**: Remove applications by setting lifecycle state
- **Safe removal process**: Deletes deployments first, then applications

### ✅ **4. Destructive Change Detection**
- **Cloud-init monitoring**: Detects changes to `user_data` after deployment
- **VM name monitoring**: Detects changes to VM names after deployment
- **Automatic warnings**: Alerts about potentially problematic changes

### ✅ **5. Warning and Bail-out Options**
- **Configurable behavior**: `BAIL_ON_DESTRUCTIVE_CHANGES` environment variable
- **Test mode**: Shows warnings, continues deployment
- **Production mode**: Shows warnings, fails deployment (configurable)

## 🔧 **Implementation Details**

### **Enhanced Deployment Script (`scripts/deploy.py`)**

#### **New Methods Added:**
- `get_manifest_lifecycle_state()` - Determines lifecycle state from manifest
- `should_skip_manifest()` - Checks if manifest should be skipped
- `detect_destructive_changes()` - Identifies problematic changes
- `handle_undeploy_manifest()` - Manages cleanup process

#### **Enhanced Process Flow:**
1. **Load manifest** and extract application name
2. **Check lifecycle state** and determine behavior
3. **Handle undeploy** if lifecycle is `undeploy`
4. **Check for skip conditions** (draft, testonly in production)
5. **Detect destructive changes** if application exists
6. **Warn or bail out** based on configuration
7. **Continue with normal deployment** if not skipped

### **Updated GitHub Actions Workflows**

#### **Test Deployment Workflow:**
- **Environment Variables**:
  - `TEST_MODE=true` - Enables test mode behavior
  - `BAIL_ON_DESTRUCTIVE_CHANGES=false` - Continues on warnings
- **Lifecycle Behavior**:
  - `draft`: Skipped
  - `testonly`: Deployed to test cluster group
  - `production`: Skipped
  - `undeploy`: Cleans up test deployments

#### **Production Deployment Workflow:**
- **Environment Variables**:
  - `BAIL_ON_DESTRUCTIVE_CHANGES=true` - Fails on destructive changes
- **Lifecycle Behavior**:
  - `draft`: Skipped
  - `testonly`: Skipped
  - `production`: Deployed to production
  - `undeploy`: Cleans up production deployments

### **New Utility Script (`scripts/manage-lifecycle.py`)**
- **List manifests** with lifecycle states
- **Set lifecycle state** for individual manifests
- **Bulk operations** for multiple manifests
- **Dry-run capability** for safe testing

## 📋 **Example Manifests**

### **Draft Application**
```yaml
metadata:
  name: my-draft-app
  lifecycle: draft  # Will be skipped during deployment
```

### **Test Only Application**
```yaml
metadata:
  name: my-test-app
  lifecycle: testonly  # Only deployed during testing
```

### **Production Application**
```yaml
metadata:
  name: my-prod-app
  lifecycle: production  # Deployed to production (default)
```

### **Undeploy Application**
```yaml
metadata:
  name: my-old-app
  lifecycle: undeploy  # Triggers cleanup and removal
```

## 🔄 **Workflow Examples**

### **Development Workflow**
1. **Create draft**: `lifecycle: draft` for work in progress
2. **Move to testing**: `lifecycle: testonly` for experimental features
3. **Promote to production**: `lifecycle: production` when stable
4. **Clean up old versions**: `lifecycle: undeploy` to remove

### **Demo Reset Workflow**
1. **Mark for cleanup**: Set `lifecycle: undeploy` in PR
2. **Merge PR**: Triggers cleanup of existing deployment
3. **Create new version**: Add new manifest with `lifecycle: production`
4. **Deploy**: New version replaces old one

### **Safe Development Process**
1. **Work in draft**: Develop features without affecting any environment
2. **Test safely**: Use `testonly` for experimental features
3. **Deploy carefully**: Use `production` only when ready
4. **Clean up regularly**: Use `undeploy` to remove old versions

## ⚙️ **Configuration Options**

### **Environment Variables**

#### **`BAIL_ON_DESTRUCTIVE_CHANGES`**
```bash
# Production behavior (default in production workflow)
export BAIL_ON_DESTRUCTIVE_CHANGES=true

# Test behavior (default in test workflow)
export BAIL_ON_DESTRUCTIVE_CHANGES=false
```

#### **`TEST_MODE`**
```bash
# Enable test mode behavior
export TEST_MODE=true

# Production mode behavior (default)
export TEST_MODE=false
```

## 🛠️ **Usage Examples**

### **List All Manifests**
```bash
python scripts/manage-lifecycle.py list
```

### **List Only Draft Manifests**
```bash
python scripts/manage-lifecycle.py list --lifecycle draft
```

### **Set Single Manifest to Draft**
```bash
python scripts/manage-lifecycle.py set --file manifests/my-app.yaml --lifecycle draft
```

### **Bulk Set Multiple Manifests**
```bash
python scripts/manage-lifecycle.py bulk-set --pattern "example-*" --lifecycle testonly
```

### **Dry Run Bulk Operation**
```bash
python scripts/manage-lifecycle.py bulk-set --pattern "demo-*" --lifecycle undeploy --dry-run
```

## 🚨 **Safety Features**

### **Destructive Change Detection**
- **Automatic detection** of cloud-init and VM name changes
- **Warning system** alerts about potentially problematic changes
- **Configurable behavior** for different environments

### **Safe Cleanup Process**
- **Deployment-first deletion** to avoid orphaned resources
- **Error handling** for cleanup failures
- **Status reporting** for cleanup operations

### **Backward Compatibility**
- **Default lifecycle** is `production` for existing manifests
- **Legacy support** for `draft` flag
- **No breaking changes** to existing workflows

## 📊 **Benefits**

### **For Developers**
- **Safe development** with draft state for work in progress
- **Experimental testing** with testonly state
- **Controlled promotion** from test to production
- **Easy cleanup** of old versions

### **For Operations**
- **Predictable deployments** based on lifecycle state
- **Destructive change protection** prevents deployment issues
- **Automated cleanup** reduces manual maintenance
- **Clear audit trail** of lifecycle changes

### **For Teams**
- **Collaborative workflow** with clear lifecycle stages
- **Consistent process** across all applications
- **Reduced deployment errors** through change detection
- **Easy demo management** with undeploy capability

## 🎉 **Ready for Production**

All lifecycle management features are:

- ✅ **Fully implemented** and tested
- ✅ **Well documented** with examples and guides
- ✅ **Backward compatible** with existing manifests
- ✅ **Integrated** with GitHub Actions workflows
- ✅ **Safety focused** with destructive change detection
- ✅ **User friendly** with management utilities

The Fleet Manager GitOps repository now provides enterprise-grade lifecycle management capabilities that make deployments safer, more predictable, and easier to manage across different environments and use cases.

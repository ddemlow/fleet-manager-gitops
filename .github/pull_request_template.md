# 🚀 GitOps Deployment PR

## 📋 **Pre-Deployment Checklist**

### **Manifest Validation**
- [ ] Manifest follows the [application template](manifests/templates/application-template.yaml)
- [ ] All required fields are present: `name`, `description`, `lifecycle`, `clusterGroups`
- [ ] Lifecycle state is appropriate for this change
- [ ] Application name is unique and descriptive

### **Lifecycle State**
- [ ] `draft` - Work in progress (will be skipped)
- [ ] `testonly` - Experimental/demo (test deployment only)
- [ ] `production` - Ready for production
- [ ] `undeploy` - Remove existing deployment

### **Destructive Changes**
- [ ] No changes to cloud-init `user_data` after initial deployment
- [ ] No changes to VM names after initial deployment
- [ ] No changes to storage device types
- [ ] No changes to network interface configurations

### **Testing**
- [ ] Tested locally with `python scripts/deploy.py --target-apps <app-name>`
- [ ] Verified test deployment works (if applicable)
- [ ] Checked for destructive change warnings

## 🔄 **Deployment Plan**

### **What will be deployed:**
- Application: `[app-name]`
- Cluster Groups: `[cluster-groups]`
- Lifecycle State: `[lifecycle]`

### **Expected behavior:**
- [ ] New application creation
- [ ] Existing application update
- [ ] Application cleanup (undeploy)
- [ ] Test deployment only
- [ ] Production deployment

## 🧪 **Testing Instructions**

### **For Reviewers:**
1. Review the manifest for correctness
2. Check that lifecycle state is appropriate
3. Verify no destructive changes are present
4. Test deployment (if applicable):
   ```bash
   python scripts/deploy.py --target-apps [app-name]
   ```

### **After Merge:**
1. Monitor deployment in Fleet Manager UI
2. Verify application status
3. Test application functionality (if applicable)

## 📊 **Deployment Monitoring**

- **Fleet Manager UI**: [Link to deployments](https://fleet.scalecomputing.com/deployments?org=63b8337ec6939fdfb0f716af)
- **Test Cluster Group**: `dd_szt15b` (if testonly)
- **Production Cluster Groups**: `DDvsns` (if production)

## 🚨 **Rollback Plan**

If deployment fails:
1. Set lifecycle to `undeploy` in a new PR
2. Merge to trigger cleanup
3. Fix issues in manifest
4. Set lifecycle back to `production`

## 📝 **Additional Notes**

<!-- Add any additional context, concerns, or notes here -->
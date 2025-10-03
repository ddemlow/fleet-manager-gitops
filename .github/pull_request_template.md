## 🧪 Test Deployment Checklist

### Pre-Deployment Testing
- [ ] Changes have been tested locally (if applicable)
- [ ] YAML syntax is valid
- [ ] All required fields are present

### Test Deployment Verification
- [ ] **Test deployment to `dd_szt15b` completed successfully**
- [ ] **Verified deployment in Fleet Manager UI**
- [ ] **Tested deployed applications in `dd_szt15b` cluster group**
- [ ] **Confirmed applications are working as expected**

### Production Readiness
- [ ] All tests passed in test environment
- [ ] No breaking changes detected
- [ ] Documentation updated (if needed)

### Deployment Details
**Files Changed:**
<!-- List the manifest files that were changed -->

**Cluster Groups Affected:**
<!-- List which cluster groups will be affected by this deployment -->

**Testing Notes:**
<!-- Describe what was tested and any specific test scenarios -->

---

## 📋 Test Deployment Process

1. **Automated Test Deployment**: This PR will automatically deploy changes to the `dd_szt15b` test cluster group
2. **Manual Verification**: A human reviewer must verify the deployment works correctly
3. **Approval**: Only after successful testing should this PR be approved for merge
4. **Production Deployment**: Once merged to master, changes will be deployed to production cluster groups

### 🔗 Fleet Manager Links
- [Test Cluster Group: dd_szt15b](https://fleet.scalecomputing.com/cluster-groups?org=63b8337ec6939fdfb0f716af)
- [All Deployments](https://fleet.scalecomputing.com/deployments?org=63b8337ec6939fdfb0f716af)
- [Applications](https://fleet.scalecomputing.com/deployment-applications?org=63b8337ec6939fdfb0f716af)

---

## ⚠️ Important Notes

- **Do not merge until test deployment is verified**
- **Test in `dd_szt15b` before production deployment**
- **If deployment fails, request changes to fix issues**

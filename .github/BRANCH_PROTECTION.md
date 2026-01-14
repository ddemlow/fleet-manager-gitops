# 🛡️ Branch Protection Rules

## **Recommended GitHub Repository Settings**

### **Default Branch Protection (master/main)**
1. Go to **Settings** → **Branches** → **Add rule**
2. **Branch name pattern**: `master` (or `main`, depending on your default branch)
3. **Protect matching branches**: ✅

#### **Required Settings:**
- [ ] **Require a pull request before merging**
  - [ ] **Required number of reviewers**: 1 (or more)
  - [ ] **Dismiss stale PR approvals when new commits are pushed**
  - [ ] **Require review from code owners**

- [ ] **Require status checks to pass before merging**
  - [ ] **Require branches to be up to date before merging**
  - [ ] **Required status checks**:
    - `validate-manifests` (Validation)
    - `security-scan` (Security Scan)
    - `test-deployment` (Test Deployment)

- [ ] **Require conversation resolution before merging**
- [ ] **Include administrators** (recommended)

#### **Optional Settings:**
- [ ] **Restrict pushes that create files** (prevent direct pushes)
- [ ] **Allow force pushes**: ❌
- [ ] **Allow deletions**: ❌

### **Feature Branch Protection**
1. Go to **Settings** → **Branches** → **Add rule**
2. **Branch name pattern**: `feature/*` or `*`
3. **Protect matching branches**: ✅

#### **Required Settings:**
- [ ] **Require status checks to pass before merging**
  - [ ] **Required status checks**:
    - `validate-manifests` (Validation)
    - `security-scan` (Security Scan)

## **Benefits of Branch Protection**

### **Safety**
- **Prevents direct pushes** to the default branch
- **Requires code review** before merging
- **Ensures tests pass** before deployment
- **Prevents force pushes** that could break history

### **Quality**
- **Mandatory validation** of manifests
- **Security scanning** for vulnerabilities
- **Test deployment verification**
- **Documentation requirements**

### **Compliance**
- **Audit trail** of all changes
- **Review process** for all deployments
- **Rollback capability** through Git history
- **Change tracking** and approval workflow

## **Setup Instructions**

1. **Navigate to repository settings**
2. **Go to Branches section**
3. **Add protection rules** as described above
4. **Test the protection** by trying to push directly to the default branch
5. **Verify PR workflow** requires checks to pass

## **Team Workflow**

### **Development Process:**
1. **Create feature branch**: `git checkout -b feature/my-app`
2. **Make changes** to manifests
3. **Create PR** with proper description
4. **Wait for checks** to pass
5. **Request review** from team members
6. **Merge after approval**

### **Emergency Process:**
1. **Create hotfix branch**: `git checkout -b hotfix/urgent-fix`
2. **Make minimal changes** needed
3. **Create PR** with emergency justification
4. **Fast-track review** process
5. **Merge after approval**

## **Monitoring**

### **Check Protection Status:**
- **Repository Settings** → **Branches**
- **View protection rules** and their status
- **Monitor failed checks** and resolve issues

### **Common Issues:**
- **Missing status checks**: Ensure workflows are running
- **Review requirements**: Add team members as reviewers
- **Status check failures**: Fix validation or security issues

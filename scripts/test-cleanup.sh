#!/bin/bash

# Test-specific cleanup script that respects test cluster groups
# Usage: ./scripts/test-cleanup.sh <app-name> [cluster-group]

set -e

APP_NAME="$1"
TEST_CLUSTER_GROUP="${2:-dd_szt15b}"

# If app name doesn't include cluster group, add it
if [[ "$APP_NAME" != *"-test-$TEST_CLUSTER_GROUP" ]]; then
    APP_NAME="${APP_NAME}-test-${TEST_CLUSTER_GROUP}"
fi

if [ -z "$APP_NAME" ]; then
    echo "❌ Usage: $0 <app-name> [cluster-group]"
    echo "   Example: $0 k0s-demo-test dd_szt15b"
    exit 1
fi

echo "🧹 TEST CLEANUP: $APP_NAME in cluster group $TEST_CLUSTER_GROUP"
echo ""

# Create a test-specific cleanup manifest
CLEANUP_MANIFEST="manifests/${APP_NAME}-test-cleanup.yaml"

echo "📝 Creating test cleanup manifest..."
cat > "$CLEANUP_MANIFEST" << EOF
type: Application
version: "1"
metadata:
  name: "$APP_NAME"
  description: "Test cleanup - temporary empty resources"
  clusterGroups:
    - $TEST_CLUSTER_GROUP
  labels:
    - test-cleanup
spec:
  assets: []
  resources: []
EOF

echo "✅ Created test cleanup manifest: $CLEANUP_MANIFEST"

# Deploy the cleanup manifest
echo ""
echo "🚀 Deploying test cleanup manifest..."
export CLUSTER_GROUP_NAME="$TEST_CLUSTER_GROUP"
export TARGET_APPLICATIONS="$APP_NAME"

python3 scripts/deploy.py

if [ $? -eq 0 ]; then
    echo "✅ Test cleanup deployment submitted successfully"
    echo "🧹 VMs in $TEST_CLUSTER_GROUP will be cleaned up"
    echo ""
    echo "⏳ Wait for cleanup to complete, then manually delete:"
    echo "   1. Deployment: ${APP_NAME}-${TEST_CLUSTER_GROUP}"
    echo "   2. Application: $APP_NAME"
    echo ""
    echo "🔗 Fleet Manager: https://fleet.scalecomputing.com/cluster-groups?org=63b8337ec6939fdfb0f716af"
else
    echo "❌ Test cleanup deployment failed"
    exit 1
fi

# Clean up the temporary manifest
echo ""
echo "🧹 Cleaning up temporary manifest..."
rm -f "$CLEANUP_MANIFEST"
echo "✅ Cleaned up: $CLEANUP_MANIFEST"

echo ""
echo "🎯 Test cleanup complete!"
echo "📋 Next: Manually delete the deployment and application in Fleet Manager UI"

#!/bin/bash
# Fleet Manager Deployment Cleanup - The RIGHT Way
# Uses empty resources approach with proper timing

MANIFEST_PATH="$1"
WAIT_MINUTES="${2:-10}"

if [ -z "$MANIFEST_PATH" ]; then
    echo "❌ Usage: $0 <manifest-path> [wait-minutes]"
    echo ""
    echo "🎯 Fleet Manager cleanup workflow:"
    echo "  1. Deploy cleanup manifest (resources: [])"
    echo "  2. Wait for cleanup deployment to complete"
    echo "  3. Restore application definition"
    echo "  4. Application is ready for deployment"
    echo ""
    echo "Examples:"
    echo "  $0 manifests/_compiled/nginx2.yaml"
    echo "  $0 manifests/_compiled/nginx2.yaml 5"
    exit 1
fi

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "❌ Manifest file not found: $MANIFEST_PATH"
    exit 1
fi

echo "🧹 Fleet Manager Deployment Cleanup"
echo "📄 Manifest: $MANIFEST_PATH"
echo "⏰ Wait time: ${WAIT_MINUTES} minutes"
echo ""

# Extract app name from manifest
APP_NAME=$(python3 -c "
import yaml
with open('$MANIFEST_PATH', 'r') as f:
    data = yaml.safe_load(f)
print(data['metadata']['name'])
")

echo "🔑 Application name: $APP_NAME"
echo ""

# Step 1: Create temporary cleanup manifest
echo "📝 Step 1: Creating cleanup manifest..."
CLEANUP_MANIFEST="manifests/${APP_NAME}-cleanup-temp.yaml"

# Create cleanup manifest with same app name but empty resources
python3 -c "
import yaml
with open('$MANIFEST_PATH', 'r') as f:
    original = yaml.safe_load(f)

cleanup = original.copy()
cleanup['metadata']['description'] = 'Cleanup deployment - temporary empty resources'
cleanup['spec']['resources'] = []

with open('$CLEANUP_MANIFEST', 'w') as f:
    yaml.dump(cleanup, f, default_flow_style=False, sort_keys=False)

print('✅ Created cleanup manifest: $CLEANUP_MANIFEST')
"

# Step 2: Deploy cleanup manifest
echo ""
echo "🚀 Step 2: Deploying cleanup manifest..."
python3 scripts/deploy.py --target-apps "$APP_NAME"

if [ $? -ne 0 ]; then
    echo "❌ Cleanup deployment failed"
    rm -f "$CLEANUP_MANIFEST"
    exit 1
fi

echo "✅ Cleanup deployment started"
echo ""

# Step 3: Wait for cleanup to complete
echo "⏳ Step 3: Waiting for cleanup to complete (${WAIT_MINUTES} minutes)..."
echo "💡 This is crucial - the deployment must finish before we restore the app definition"

if [ "$WAIT_MINUTES" != "0" ]; then
    echo "⏰ Waiting ${WAIT_MINUTES} minutes for cleanup to complete..."
    sleep $((WAIT_MINUTES * 60))
    echo "✅ Wait period completed"
else
    echo "⚠️  Skipping wait - you should manually verify cleanup is complete"
fi

# Step 4: Restore application definition
echo ""
echo "📝 Step 4: Restoring application definition..."
python3 scripts/deploy.py --target-apps "$APP_NAME" --skip-deployment-trigger

if [ $? -eq 0 ]; then
    echo "✅ Application definition restored successfully"
else
    echo "❌ Failed to restore application definition"
    rm -f "$CLEANUP_MANIFEST"
    exit 1
fi

# Step 5: Clean up temporary file
echo ""
echo "🗑️  Step 5: Cleaning up temporary manifest..."
rm -f "$CLEANUP_MANIFEST"
echo "✅ Temporary manifest removed"

echo ""
echo "🎉 Cleanup workflow completed!"
echo "🚀 Application '$APP_NAME' is ready for deployment:"
echo "   python3 scripts/deploy.py --target-apps $APP_NAME"

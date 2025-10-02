#!/bin/bash
# Fleet Manager Deployment Cleanup - The RIGHT Way
# Uses empty resources approach with proper timing

MANIFEST_PATH="$1"
WAIT_MINUTES="${2:-10}"

if [ -z "$MANIFEST_PATH" ]; then
    echo "❌ Usage: $0 <manifest-path-or-app-name> [wait-minutes]"
    echo ""
    echo "🎯 Fleet Manager cleanup workflow:"
    echo "  1. Deploy cleanup manifest (resources: [])"
    echo "  2. Wait for cleanup deployment to complete"
    echo "  3. Restore application definition"
    echo "  4. Application is ready for deployment"
    echo ""
    echo "Examples:"
    echo "  $0 manifests/_compiled/nginx2.yaml          # Use compiled manifest"
    echo "  $0 manifests/containers/nginx3.container.yaml # Use source container"
    echo "  $0 nginx3                                    # Use app name directly"
    echo "  $0 nginx2 5                                 # With custom wait time"
    exit 1
fi

# Check if it's a file or just an app name
if [ -f "$MANIFEST_PATH" ]; then
    # It's a file - use it directly
    echo "📄 Using manifest file: $MANIFEST_PATH"
elif [[ "$MANIFEST_PATH" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    # It's just an app name - create a temporary manifest
    APP_NAME="$MANIFEST_PATH"
    echo "📝 Creating temporary cleanup manifest for app: $APP_NAME"
    
    TEMP_MANIFEST="/tmp/${APP_NAME}-cleanup.yaml"
    cat > "$TEMP_MANIFEST" << EOF
version: '1'
type: Application
metadata:
  name: $APP_NAME
  clusterGroups: [DDvsns]
spec:
  assets: []
  resources: []
EOF
    
    MANIFEST_PATH="$TEMP_MANIFEST"
    echo "✅ Created temporary manifest: $MANIFEST_PATH"
else
    echo "❌ Invalid input: $MANIFEST_PATH"
    echo "   Use a manifest file path or just an application name"
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

echo "✅ Cleanup deployment submitted"
echo ""

# Step 3: IMMEDIATELY restore application definition
echo "⚡ Step 3: Immediately restoring application definition..."
echo "💡 Restoring now while cleanup deployment is queued/running"

# Check what type of restoration is needed
if [[ "$MANIFEST_PATH" == *"/tmp/"* ]]; then
    # This was created from app name - it's likely a compiled container
    echo "🔍 Detected compiled container application"
    echo "⚠️  For compiled containers, you need to restore from the compiled manifest"
    echo ""
    echo "💡 To restore this application:"
    echo "   1. If you have local compiled files:"
    echo "      ./scripts/cleanup.sh manifests/_compiled/${APP_NAME}.yaml"
    echo "   2. If compiled on GitHub Actions:"
    echo "      - Push changes to trigger compilation"
    echo "      - Or manually compile: python3 scripts/compile_manifests.py"
    echo "      - Then: python3 scripts/deploy.py --target-apps $APP_NAME --skip-deployment-trigger"
    echo ""
    echo "⚠️  Skipping automatic restoration - manual action required"
else
    # This is a regular manifest - restore immediately from the ORIGINAL manifest
    echo "🔄 Restoring from ORIGINAL manifest: $MANIFEST_PATH"
    
    # Temporarily move the cleanup manifest out of the way so deploy.py doesn't process it
    mv "$CLEANUP_MANIFEST" "${CLEANUP_MANIFEST}.bak"
    
    # Deploy from the original manifest using deploy script
    # First, let's copy the original manifest to a known location that deploy.py will process
    ORIGINAL_RESTORE_FILE="manifests/${APP_NAME}-restore.yaml"
    cp "$MANIFEST_PATH" "$ORIGINAL_RESTORE_FILE"
    
    # Now deploy using the copied file
    python3 scripts/deploy.py --target-apps "$APP_NAME" --skip-deployment-trigger
    
    if [ $? -eq 0 ]; then
        echo "✅ Application definition restored successfully from original manifest"
        # Clean up the temporary restore file
        rm -f "$ORIGINAL_RESTORE_FILE"
    else
        echo "❌ Failed to restore application definition"
        # Clean up the temporary restore file
        rm -f "$ORIGINAL_RESTORE_FILE"
        # Restore the cleanup manifest before exiting
        mv "${CLEANUP_MANIFEST}.bak" "$CLEANUP_MANIFEST"
        rm -f "$CLEANUP_MANIFEST"
        exit 1
    fi
    
    # Restore the cleanup manifest for later cleanup
    mv "${CLEANUP_MANIFEST}.bak" "$CLEANUP_MANIFEST"
fi

# Step 4: Wait for cleanup to complete (optional)
echo ""
echo "⏳ Step 4: Waiting for cleanup to complete (${WAIT_MINUTES} minutes)..."
echo "💡 Cleanup is running with empty resources while app definition is restored"

if [ "$WAIT_MINUTES" != "0" ]; then
    echo "⏰ Waiting ${WAIT_MINUTES} minutes for cleanup to complete..."
    sleep $((WAIT_MINUTES * 60))
    echo "✅ Wait period completed"
else
    echo "⚠️  Skipping wait - cleanup is running in background"
fi

# Step 5: Clean up temporary files
echo ""
echo "🗑️  Step 5: Cleaning up temporary manifests..."
rm -f "$CLEANUP_MANIFEST"
# Also clean up the temp manifest if we created one
if [[ "$TEMP_MANIFEST" != "" ]]; then
    rm -f "$TEMP_MANIFEST"
    echo "✅ Temporary manifests removed"
else
    echo "✅ Temporary cleanup manifest removed"
fi

echo ""
echo "🎉 Cleanup workflow completed!"
if [[ "$MANIFEST_PATH" == *"/tmp/"* ]]; then
    echo "⚠️  IMPORTANT: Application '$APP_NAME' has been cleaned up but NOT restored"
    echo "   You need to restore the application definition manually:"
    echo ""
    echo "   Option 1 - Use compiled manifest (if available):"
    echo "     ./scripts/cleanup.sh manifests/_compiled/${APP_NAME}.yaml"
    echo ""
    echo "   Option 2 - Compile and restore:"
    echo "     python3 scripts/compile_manifests.py"
    echo "     python3 scripts/deploy.py --target-apps $APP_NAME --skip-deployment-trigger"
    echo ""
    echo "   Option 3 - Trigger GitHub Actions compilation"
else
    echo "🚀 Application '$APP_NAME' is ready for deployment:"
    echo "   python3 scripts/deploy.py --target-apps $APP_NAME"
fi

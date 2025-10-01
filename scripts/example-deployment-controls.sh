#!/bin/bash
# Example usage of enhanced deployment controls

echo "🚀 Fleet Manager GitOps Deployment Controls Examples"
echo "=================================================="

# Set your API key
export SC_FM_APIKEY="your-api-key-here"
export FLEET_MANAGER_API_URL="https://api.scalecomputing.com/api/v2"

echo ""
echo "1. Deploy only specific applications:"
echo "   python scripts/deploy.py --target-apps nginx,nginx2"
echo ""

echo "2. Update applications but don't trigger deployments (useful for testing):"
echo "   python scripts/deploy.py --skip-deployment-trigger"
echo ""

echo "3. Only compile manifests without deploying:"
echo "   python scripts/deploy.py --only-compile"
echo ""

echo "4. Combine multiple controls:"
echo "   python scripts/deploy.py --target-apps nginx --skip-deployment-trigger"
echo ""

echo "5. Environment variable usage (for GitHub Actions):"
echo "   export TARGET_APPLICATIONS=nginx,nginx2"
echo "   export SKIP_DEPLOYMENT_TRIGGER=true"
echo "   python scripts/deploy.py"
echo ""

echo "6. Normal deployment (no controls):"
echo "   python scripts/deploy.py"
echo ""

echo "🔧 These controls prevent unwanted redeployments when editing unrelated manifests!"

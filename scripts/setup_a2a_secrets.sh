#!/bin/bash

# Setup script for A2A integration with dev-nexus
# Creates required secrets in Secret Manager and configures IAM permissions

set -e

# Configuration
PROJECT_ID="globalbiting-dev"
SERVICE_ACCOUNT_EMAIL="ai-ap-service@globalbiting-dev.iam.gserviceaccount.com"
CLOUD_RUN_SERVICE="agentic-log-attacker"
REGION="us-central1"

echo "=========================================="
echo "A2A Integration Setup Script"
echo "=========================================="
echo "Project ID: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "Cloud Run Service: $CLOUD_RUN_SERVICE"
echo "Region: $REGION"
echo ""

# Set project
echo "[1] Setting GCP project..."
gcloud config set project $PROJECT_ID || {
    echo "Failed to set project. Make sure you have gcloud installed and authenticated."
    exit 1
}

# Create ALLOWED_SERVICE_ACCOUNTS secret if it doesn't exist
echo "[2] Creating ALLOWED_SERVICE_ACCOUNTS secret..."
if gcloud secrets describe ALLOWED_SERVICE_ACCOUNTS > /dev/null 2>&1; then
    echo "    Secret already exists, updating version..."
    echo -n "$SERVICE_ACCOUNT_EMAIL" | gcloud secrets versions add ALLOWED_SERVICE_ACCOUNTS --data-file=-
else
    echo "    Creating new secret..."
    echo -n "$SERVICE_ACCOUNT_EMAIL" | \
      gcloud secrets create ALLOWED_SERVICE_ACCOUNTS \
      --data-file=- \
      --replication-policy="automatic"
fi
echo "    ✓ ALLOWED_SERVICE_ACCOUNTS secret configured"

# Grant Cloud Build permission to access the secret
echo "[3] Granting Cloud Build access to ALLOWED_SERVICE_ACCOUNTS secret..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud secrets add-iam-policy-binding ALLOWED_SERVICE_ACCOUNTS \
  --member="serviceAccount:$BUILD_SA" \
  --role="roles/secretmanager.secretAccessor" \
  > /dev/null 2>&1 || true  # Ignore if already has role
echo "    ✓ Cloud Build service account has access"

# Verify Cloud Run service exists
echo "[4] Verifying Cloud Run service exists..."
if gcloud run services describe $CLOUD_RUN_SERVICE --region=$REGION > /dev/null 2>&1; then
    echo "    ✓ Cloud Run service found"
else
    echo "    ✗ Cloud Run service not found: $CLOUD_RUN_SERVICE"
    echo "    Note: Deploy the service first using: gcloud builds submit --config cloudbuild.yaml ."
    echo "    Then run this script again to configure permissions."
fi

# Grant Cloud Run Invoker role to dev-nexus service account
echo "[5] Granting Cloud Run Invoker role..."
gcloud run services add-iam-policy-binding $CLOUD_RUN_SERVICE \
  --region=$REGION \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.invoker" \
  > /dev/null 2>&1
echo "    ✓ Service account can invoke Cloud Run service"

echo ""
echo "=========================================="
echo "✓ A2A Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Deploy the service:"
echo "   gcloud builds submit --config cloudbuild.yaml ."
echo ""
echo "2. After deployment, verify the integration:"
echo "   python scripts/test_a2a_endpoint.py"
echo ""
echo "3. Register this service with dev-nexus using:"
echo "   https://agentic-log-attacker-XXX.run.app/.well-known/agent.json"
echo ""

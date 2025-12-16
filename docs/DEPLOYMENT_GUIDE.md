# Complete A2A Deployment Guide

This guide provides comprehensive instructions for deploying agentic-log-attacker with A2A integration to production.

## Deployment Overview

Two deployment approaches are available:

1. **Cloud Build Only** - Simple, straightforward deployment via gcloud
2. **Terraform + Cloud Build** - Infrastructure-as-code approach (recommended)

## Prerequisites

### Common Requirements
- Google Cloud SDK (`gcloud`) installed and authenticated
- GCP Project: `globalbiting-dev`
- Required permissions:
  - Secret Manager admin
  - Cloud Build admin
  - Cloud Run admin
  - IAM admin

### For Terraform Deployment (Additional)
- Terraform >= 1.0 installed
- Google Terraform Provider

### Required Credentials
- Gemini API Key (from https://aistudio.google.com/apikey)
- GitHub Personal Access Token (from https://github.com/settings/tokens)

## Approach 1: Cloud Build Only (Simple)

### Step 1: Create Required Secrets

```bash
# Navigate to project root
cd agentic-log-attacker

# Create secrets in Secret Manager
echo -n "your-gemini-api-key" | \
  gcloud secrets create GEMINI_API_KEY --data-file=-

echo -n "your-github-token" | \
  gcloud secrets create GITHUB_TOKEN --data-file=-

echo -n "ai-ap-service@globalbiting-dev.iam.gserviceaccount.com" | \
  gcloud secrets create ALLOWED_SERVICE_ACCOUNTS --data-file=-
```

### Step 2: Grant Cloud Build Access to Secrets

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe globalbiting-dev --format='value(projectNumber)')
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant access to all three secrets
for secret in GEMINI_API_KEY GITHUB_TOKEN ALLOWED_SERVICE_ACCOUNTS; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Step 3: Deploy via Cloud Build

```bash
# Submit build (will automatically push image and deploy to Cloud Run)
gcloud builds submit --config cloudbuild.yaml .

# Wait for build to complete (~10-15 minutes)
# Check status:
gcloud builds list --limit=1

# Get build details:
gcloud builds log [BUILD_ID] --stream
```

### Step 4: Grant Dev-Nexus Invocation Permission

```bash
# Add dev-nexus service account as Cloud Run invoker
gcloud run services add-iam-policy-binding agentic-log-attacker \
  --region=us-central1 \
  --member="serviceAccount:ai-ap-service@globalbiting-dev.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Step 5: Verify Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe agentic-log-attacker \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl "$SERVICE_URL/health"

# Test metadata endpoint
curl "$SERVICE_URL/.well-known/agent.json"
```

## Approach 2: Terraform + Cloud Build (Recommended)

### Step 1: Initialize Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Verify initialization
ls -la .terraform
```

### Step 2: Configure Variables

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars (optional, defaults should work)
# Verify these values:
# - gcp_project_id = "globalbiting-dev"
# - gcp_region = "us-central1"
# - deploy_via_terraform = false  (we'll use Cloud Build)
```

### Step 3: Set Sensitive Variables

```bash
# Option A: Environment variables (recommended)
export TF_VAR_gemini_api_key="your-gemini-api-key"
export TF_VAR_github_token="your-github-token"

# Option B: Add to terraform.tfvars (less secure)
# Edit terraform.tfvars and add:
# gemini_api_key = "your-key"
# github_token = "your-token"
```

### Step 4: Plan and Apply Terraform

```bash
# Review what will be created
terraform plan

# Create secrets in Secret Manager
terraform apply

# Verify outputs
terraform output

# Example output:
# secrets_created = {
#   "allowed_service_accounts" = "ALLOWED_SERVICE_ACCOUNTS"
#   "gemini_api_key" = "GEMINI_API_KEY"
#   "github_token" = "GITHUB_TOKEN"
# }
```

### Step 5: Deploy Cloud Run Service

```bash
# Go back to repo root
cd ..

# Deploy via Cloud Build (uses secrets created by Terraform)
gcloud builds submit --config cloudbuild.yaml .

# Monitor the build
gcloud builds log --stream $(gcloud builds list --limit=1 --format='value(id)')
```

### Step 6: Configure IAM

```bash
# Add dev-nexus service account as Cloud Run invoker
gcloud run services add-iam-policy-binding agentic-log-attacker \
  --region=us-central1 \
  --member="serviceAccount:ai-ap-service@globalbiting-dev.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Step 7: Verify Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe agentic-log-attacker \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test endpoints
curl "$SERVICE_URL/health"
curl "$SERVICE_URL/.well-known/agent.json"
```

## Full Terraform Deployment (Alternative)

If you want Terraform to deploy the Cloud Run service directly (instead of Cloud Build):

### Step 1: Build Container Image First

```bash
# Build and push Docker image
gcloud builds submit --config cloudbuild.yaml . \
  --substitutions="_PUSH_IMAGE_ONLY=true"

# Get the image SHA
IMAGE_SHA=$(gcloud builds log [BUILD_ID] | grep "Digest:" | awk '{print $2}')
echo "Image: gcr.io/globalbiting-dev/agentic-log-attacker@$IMAGE_SHA"
```

### Step 2: Update Terraform Configuration

```bash
cd terraform

# Edit terraform.tfvars:
# 1. Set: deploy_via_terraform = true
# 2. Update: container_image = "gcr.io/globalbiting-dev/agentic-log-attacker:latest"

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with desired values
```

### Step 3: Deploy via Terraform

```bash
# Set sensitive variables
export TF_VAR_gemini_api_key="your-key"
export TF_VAR_github_token="your-token"

# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Get the service URL
terraform output cloud_run_url
```

### Step 4: Verify

```bash
SERVICE_URL=$(terraform output -raw cloud_run_url)
curl "$SERVICE_URL/health"
```

## Post-Deployment Steps

### 1. Register with Dev-Nexus

```bash
# Get the agent metadata URL
SERVICE_URL=$(gcloud run services describe agentic-log-attacker \
  --region=us-central1 \
  --format='value(status.url)')

echo "Register this URL with dev-nexus:"
echo "${SERVICE_URL}/.well-known/agent.json"

# The dev-nexus agent will discover your service and add it to its registry
```

### 2. Test A2A Integration

```bash
# Run the integration test script
python scripts/test_a2a_endpoint.py

# Expected output:
# [1] Testing /health endpoint...
#     Status: healthy
#     Version: 2.0.0-a2a
# [2] Testing /.well-known/agent.json endpoint...
#     Agent name: agentic-log-attacker
# [3] Testing /a2a/execute endpoint with authentication...
#     Response Status: 200
# [4] Testing unauthorized access rejection...
#     Correctly rejected unauthorized request (401)
# ✓ All tests passed!
```

### 3. Monitor Logs

```bash
# View service logs
gcloud run services logs read agentic-log-attacker --region=us-central1

# Or filter by recent entries
gcloud run services logs read agentic-log-attacker \
  --region=us-central1 \
  --limit=50 \
  --format=json | jq '.[] | select(.timestamp > "2024-01-01T00:00:00Z")'

# Monitor in real-time
gcloud run services logs read agentic-log-attacker \
  --region=us-central1 \
  --tail
```

### 4. Check Cloud Run Configuration

```bash
# Describe the deployed service
gcloud run services describe agentic-log-attacker \
  --region=us-central1 \
  --format=yaml

# Check IAM policy
gcloud run services get-iam-policy agentic-log-attacker \
  --region=us-central1
```

## Troubleshooting

### Secrets Not Found

```bash
# Verify secrets were created
gcloud secrets list

# Check a specific secret
gcloud secrets describe ALLOWED_SERVICE_ACCOUNTS

# View secret versions
gcloud secrets versions list ALLOWED_SERVICE_ACCOUNTS
```

### Cloud Build Fails

```bash
# Check build logs
gcloud builds log --stream [BUILD_ID]

# Common issues:
# - Missing secrets: Ensure all three secrets are created
# - Permission denied: Check Cloud Build SA has secret access
# - Image push failed: Verify Container Registry access
```

### Service Deployment Fails

```bash
# Check service status
gcloud run services describe agentic-log-attacker --region=us-central1

# View recent revisions
gcloud run revisions list --service=agentic-log-attacker --region=us-central1

# Check resource quotas
gcloud compute project-info describe --format="value(quotas[])"
```

### A2A Endpoint Issues

```bash
# Test health without auth
curl -i https://agentic-log-attacker-XXX.run.app/health

# Test with invalid token (should return 401)
curl -i -H "Authorization: Bearer invalid-token" \
  https://agentic-log-attacker-XXX.run.app/a2a/execute

# Test rate limiting
for i in {1..101}; do
  curl https://agentic-log-attacker-XXX.run.app/health
done
# Request 101+ should return 429 (Too Many Requests)
```

## Scaling and Performance Tuning

### Adjust Cloud Run Configuration

```bash
# Update memory allocation
gcloud run services update agentic-log-attacker \
  --region=us-central1 \
  --memory=2Gi  # Increase from 1Gi to 2Gi

# Adjust timeout
gcloud run services update agentic-log-attacker \
  --region=us-central1 \
  --timeout=600  # Increase from 300s to 600s

# Set minimum instances (reduces cold starts)
gcloud run services update agentic-log-attacker \
  --region=us-central1 \
  --min-instances=1
```

### Monitor Performance

```bash
# View metrics
gcloud monitoring timeseries list \
  --filter 'metric.type=run.googleapis.com/request_count'

# Check cloud trace
gcloud trace traces list --filter='is:failed' --limit=10
```

## Backup and Recovery

### Backup Terraform State

```bash
# If using local state
cp terraform/terraform.tfstate terraform/terraform.tfstate.backup

# Or migrate to remote state
gsutil mb gs://terraform-state-globalbiting-dev
gsutil versioning set on gs://terraform-state-globalbiting-dev

# Configure backend in terraform/main.tf
# Then run:
cd terraform
terraform init  # Select yes to migrate state
```

### Destroy Deployment

```bash
# To completely remove the deployment:

# Option 1: Via gcloud
gcloud run services delete agentic-log-attacker --region=us-central1

# Option 2: Via Terraform
cd terraform
terraform destroy

# Delete secrets manually if not using Terraform
for secret in GEMINI_API_KEY GITHUB_TOKEN ALLOWED_SERVICE_ACCOUNTS; do
  gcloud secrets delete $secret
done
```

## Security Best Practices

1. **Rotate Secrets Regularly**
   ```bash
   # Update secret version
   echo -n "new-api-key" | \
     gcloud secrets versions add GEMINI_API_KEY --data-file=-
   ```

2. **Audit Access**
   ```bash
   gcloud secrets get-iam-policy GEMINI_API_KEY
   ```

3. **Use Service Accounts**
   - Never use personal credentials
   - Grant minimal IAM roles

4. **Enable Cloud Audit Logs**
   ```bash
   gcloud logging read "resource.type=cloud_run_service" --limit=10
   ```

5. **Monitor Unauthorized Access**
   ```bash
   gcloud logging read "protoPayload.status.code=403" --limit=10
   ```

## Next Steps

1. **Register with dev-nexus**: Provide the AgentCard URL
2. **Test integration**: Run `python scripts/test_a2a_endpoint.py`
3. **Monitor performance**: Set up Cloud Monitoring dashboards
4. **Configure backups**: Migrate Terraform state to GCS
5. **Document endpoints**: Share service URL with team

## Reference Documentation

- [A2A Integration Guide](../README.md#a2a-integration-with-dev-nexus)
- [Terraform Deployment Details](TERRAFORM_DEPLOYMENT.md)
- [Development Commands](../CLAUDE.md#development-commands)
- [Architecture Overview](../CLAUDE.md#architecture)

## Support

For deployment issues:
1. Check logs: `gcloud run services logs read agentic-log-attacker`
2. Review this guide's troubleshooting section
3. See repository README for additional help

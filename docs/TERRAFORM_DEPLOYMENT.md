# Terraform Deployment Guide for A2A Integration

This guide provides step-by-step instructions for deploying the agentic-log-attacker service using Terraform.

## Quick Start (5 minutes)

### Prerequisites
- Terraform >= 1.0 installed
- Google Cloud SDK (`gcloud`) installed
- GCP Project ID: `globalbiting-dev`
- Authenticated to GCP: `gcloud auth login`

### Deployment Steps

```bash
# 1. Navigate to Terraform directory
cd terraform

# 2. Initialize Terraform
terraform init

# 3. Set your API keys as environment variables
export TF_VAR_gemini_api_key="your-gemini-api-key"
export TF_VAR_github_token="your-github-token"

# 4. Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# 5. Review the plan (no changes yet)
terraform plan

# 6. Create the secrets
terraform apply

# 7. Deploy Cloud Run service via Cloud Build
cd ..
gcloud builds submit --config cloudbuild.yaml .

# 8. Get the service URL
gcloud run services describe agentic-log-attacker \
  --region us-central1 \
  --format 'value(status.url)'
```

## Deployment Options

### Option 1: Terraform for Secrets Only (Recommended)

This approach uses Terraform to create and manage secrets, while Cloud Build deploys the service.

**Pros:**
- Familiar with existing Cloud Build workflow
- Easier to iterate on service code
- Terraform focuses on infrastructure (secrets, IAM)

**Cons:**
- Two deployment systems (Terraform + Cloud Build)

**Steps:**
```bash
cd terraform
export TF_VAR_gemini_api_key="your-key"
export TF_VAR_github_token="your-token"
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply

# Then deploy via Cloud Build
cd ..
gcloud builds submit --config cloudbuild.yaml .
```

### Option 2: Full Terraform Deployment

This approach uses Terraform to create secrets AND deploy the Cloud Run service.

**Pros:**
- Single infrastructure-as-code definition
- Reproducible deployments
- Version control entire infrastructure

**Cons:**
- More Terraform complexity
- Container image must be pre-built

**Steps:**
```bash
cd terraform

# Edit terraform.tfvars:
# - Set deploy_via_terraform = true
# - Ensure container_image is valid

export TF_VAR_gemini_api_key="your-key"
export TF_VAR_github_token="your-token"
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply

# Terraform will output the Cloud Run URL
terraform output cloud_run_url
```

## Environment Configuration

### Setting Sensitive Variables

**Option A: Environment Variables (Recommended)**
```bash
export TF_VAR_gemini_api_key="your-gemini-api-key"
export TF_VAR_github_token="your-github-token"
terraform plan
```

**Option B: Create terraform.tfvars (Less Secure)**
```bash
cat > terraform.tfvars <<EOF
gcp_project_id = "globalbiting-dev"
gcp_region     = "us-central1"
gemini_api_key = "your-key"
github_token   = "your-token"
EOF

# Add to .gitignore
echo "terraform.tfvars" >> ../.gitignore
```

**Option C: Use `-var` Flag**
```bash
terraform apply \
  -var gemini_api_key="your-key" \
  -var github_token="your-token"
```

## Terraform Workflow

### Initialize Terraform
```bash
cd terraform
terraform init

# This downloads the Google provider and sets up the working directory
```

### Plan Changes
```bash
# See what Terraform will create/modify/destroy
terraform plan

# Output to file for review
terraform plan -out=tfplan
```

### Apply Configuration
```bash
# Create/update resources (requires confirmation)
terraform apply

# Or apply a saved plan (no confirmation needed)
terraform apply tfplan

# Automatically approve (use with caution)
terraform apply -auto-approve
```

### Check Current State
```bash
# Show all resources
terraform show

# Show specific resource
terraform show google_secret_manager_secret.gemini_api_key

# View outputs
terraform output
```

### Update Resources
```bash
# Update allowed service accounts
terraform apply \
  -var allowed_service_accounts_email="new-email@example.com"

# Update secrets
export TF_VAR_gemini_api_key="new-key"
terraform apply
```

### Destroy Resources
```bash
# Remove all Terraform-managed resources
terraform destroy

# Destroy specific resource
terraform destroy -target=google_secret_manager_secret.gemini_api_key

# Destroy without confirmation
terraform destroy -auto-approve
```

## Complete Deployment Walkthrough

### 1. Prepare Secrets
```bash
# Have ready:
# - Gemini API key (get from https://aistudio.google.com/apikey)
# - GitHub Personal Access Token (from https://github.com/settings/tokens)
```

### 2. Initialize Terraform
```bash
cd terraform
terraform init

# Output should include:
# Terraform initialized in .../terraform
# The working directory now contains all necessary Terraform files.
```

### 3. Configure Variables
```bash
cp terraform.tfvars.example terraform.tfvars

# Review and keep defaults, or update if needed:
# - gcp_project_id: should be "globalbiting-dev"
# - gcp_region: should be "us-central1"
# - deploy_via_terraform: keep as "false" for Cloud Build workflow
```

### 4. Plan Deployment
```bash
export TF_VAR_gemini_api_key="your-gemini-key"
export TF_VAR_github_token="your-github-token"

terraform plan

# Review the output to see what will be created:
# + google_secret_manager_secret.allowed_service_accounts
# + google_secret_manager_secret.gemini_api_key
# + google_secret_manager_secret.github_token
# (etc.)
```

### 5. Apply Terraform Configuration
```bash
terraform apply

# Type "yes" to confirm

# Output shows:
# Apply complete! Resources: X added, 0 changed, 0 destroyed.
```

### 6. Deploy Cloud Run Service
```bash
# Go back to repo root
cd ..

# Build and deploy via Cloud Build
gcloud builds submit --config cloudbuild.yaml .

# Wait for build to complete (~5-10 minutes)
```

### 7. Verify Deployment
```bash
# Get the service URL
gcloud run services describe agentic-log-attacker \
  --region us-central1 \
  --format 'value(status.url)'

# Test the health endpoint (should work without auth)
curl <SERVICE_URL>/health

# Test the metadata endpoint
curl <SERVICE_URL>/.well-known/agent.json
```

### 8. Configure Dev-Nexus Integration
```bash
# Register with dev-nexus using:
<SERVICE_URL>/.well-known/agent.json

# Or test the A2A endpoint:
python scripts/test_a2a_endpoint.py
```

## Troubleshooting

### "Error: Secret already exists"
```bash
# This is okay - the secret exists from a previous run
# Terraform will update it if needed
terraform apply

# Or view existing secret
gcloud secrets describe ALLOWED_SERVICE_ACCOUNTS
```

### "Error: Permission denied"
```bash
# Check your GCP permissions
gcloud auth list  # Should show your account

# Check project access
gcloud config get-value project  # Should be "globalbiting-dev"

# If wrong project:
gcloud config set project globalbiting-dev

# Verify roles (need at least Editor for full deployment)
gcloud projects get-iam-policy globalbiting-dev
```

### "Error: resource already exists"
```bash
# Terraform state is out of sync
# Import existing resources:
terraform import google_secret_manager_secret.gemini_api_key GEMINI_API_KEY

# Or rebuild state:
terraform taint google_secret_manager_secret.gemini_api_key
terraform apply
```

### "Terraform plan shows unexpected changes"
```bash
# Refresh the state
terraform refresh

# Check for external changes
terraform plan

# If needed, update tfvars to match current state
```

## Managing Terraform State

### Local State (Default)
Suitable for single developer or testing:
```bash
# State stored locally in terraform.tfstate
# Keep this file safe and don't commit to git

# Back it up
cp terraform/terraform.tfstate terraform/terraform.tfstate.backup
```

### Remote State (Production Recommended)
Store state in Google Cloud Storage:

```bash
# Create GCS bucket
gsutil mb gs://terraform-state-globalbiting-dev

# Enable versioning
gsutil versioning set on gs://terraform-state-globalbiting-dev

# Configure backend (uncomment in main.tf):
# backend "gcs" {
#   bucket = "terraform-state-globalbiting-dev"
#   prefix = "agentic-log-attacker"
# }

# Reinitialize Terraform
terraform init
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Terraform Deploy

on:
  push:
    paths:
      - 'terraform/**'
      - '.github/workflows/terraform.yml'

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Terraform Init
        run: terraform init
        working-directory: terraform

      - name: Terraform Plan
        run: terraform plan
        working-directory: terraform
        env:
          TF_VAR_gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
          TF_VAR_github_token: ${{ secrets.GITHUB_TOKEN }}

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
        working-directory: terraform
        env:
          TF_VAR_gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
          TF_VAR_github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Best Practices

1. **Always plan before apply**
   ```bash
   terraform plan -out=tfplan
   # Review output
   terraform apply tfplan
   ```

2. **Use remote state for production**
   - Enables team collaboration
   - Automatic backups
   - State locking

3. **Keep secrets in environment variables**
   - Never commit `terraform.tfvars` with secrets
   - Use `.gitignore` for sensitive files

4. **Tag resources for tracking**
   ```bash
   # Add labels in terraform for GCP resources
   labels = {
     managed_by = "terraform"
     environment = "production"
   }
   ```

5. **Regularly backup state**
   ```bash
   gsutil cp gs://bucket/terraform.tfstate ./backup/
   ```

## Reference

- [Terraform Google Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Terraform Resource](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service)
- [Secret Manager Terraform Resource](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret)

## Support

For issues:
1. Check Terraform logs: `TF_LOG=DEBUG terraform apply`
2. Review GCP documentation
3. See main repository README for additional help

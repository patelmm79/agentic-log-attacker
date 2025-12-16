# Terraform Configuration for A2A Integration

This directory contains Terraform configuration for deploying the agentic-log-attacker service with A2A (Agent-to-Agent) protocol integration.

## What This Deployment Includes

- **Secret Manager Secrets**: Creates and manages secrets for:
  - `ALLOWED_SERVICE_ACCOUNTS` - dev-nexus service account whitelist
  - `GEMINI_API_KEY` - Gemini API key
  - `GITHUB_TOKEN` - GitHub personal access token

- **Cloud Run Service** (optional): Deploys the service to Cloud Run with:
  - Proper IAM configuration
  - Secret mounting
  - Service account with minimal permissions
  - Private access (no unauthenticated requests)

- **IAM Roles**: Sets up proper permissions for:
  - Cloud Build to access secrets
  - Cloud Run service account to access secrets and logs
  - dev-nexus service account to invoke the Cloud Run service

## Prerequisites

1. **Terraform >= 1.0** installed locally
2. **Google Cloud SDK** (`gcloud`) installed and authenticated
3. **Project Owner** or appropriate IAM roles to:
   - Create secrets in Secret Manager
   - Create/update Cloud Run services
   - Manage IAM bindings

## Setup Instructions

### Option 1: Secrets Only (Recommended with Cloud Build)

This option uses Terraform to create and manage secrets, while deploying the service via Cloud Build (cloudbuild.yaml).

```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars to set your values

# 3. Set sensitive variables via environment
export TF_VAR_gemini_api_key="your-gemini-key"
export TF_VAR_github_token="your-github-token"

# 4. Plan the deployment
terraform plan

# 5. Apply the configuration (creates secrets only)
terraform apply

# 6. Deploy via Cloud Build
cd ..
gcloud builds submit --config cloudbuild.yaml .
```

### Option 2: Full Terraform Deployment

This option uses Terraform to create secrets AND deploy the Cloud Run service.

```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Copy and configure variables
cp terraform.tfvars.example terraform.tfvars

# 3. Edit terraform.tfvars:
#    - Set deploy_via_terraform = true
#    - Update container_image after first Cloud Build deployment

# 4. Set sensitive variables via environment
export TF_VAR_gemini_api_key="your-gemini-key"
export TF_VAR_github_token="your-github-token"

# 5. Plan the deployment
terraform plan

# 6. Apply the configuration
terraform apply

# 7. Output the Cloud Run URL
terraform output
```

## File Structure

```
terraform/
├── main.tf                      # Main Terraform configuration
├── variables.tf                 # Variable definitions
├── terraform.tfvars.example     # Example configuration (copy to terraform.tfvars)
├── terraform.tffmt.rc          # Terraform formatter configuration
└── README.md                    # This file
```

## Terraform Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `gcp_project_id` | string | `globalbiting-dev` | GCP Project ID |
| `gcp_region` | string | `us-central1` | GCP region (must match dev-nexus) |
| `allowed_service_accounts_email` | string | `ai-ap-service@globalbiting-dev.iam.gserviceaccount.com` | Dev-nexus service account email |
| `dev_nexus_url` | string | `https://pattern-discovery-agent-665374072631.us-central1.run.app/` | Dev-nexus service URL |
| `gemini_api_key` | string (sensitive) | - | Gemini API key |
| `github_token` | string (sensitive) | - | GitHub personal access token |
| `container_image` | string | `gcr.io/globalbiting-dev/agentic-log-attacker:latest` | Container image URI |
| `deploy_via_terraform` | bool | `false` | Deploy Cloud Run service via Terraform |

## Managing Secrets Securely

### Option A: Environment Variables (Recommended)

```bash
# Set sensitive values via environment variables
export TF_VAR_gemini_api_key="your-key"
export TF_VAR_github_token="your-token"

# Then run terraform
terraform plan
terraform apply
```

### Option B: Using `tfvars` File (Less Secure)

```bash
# Create a .gitignored tfvars file with sensitive values
cat > terraform.tfvars.secret <<EOF
gemini_api_key = "your-gemini-key"
github_token   = "your-github-token"
EOF

# Add to .gitignore
echo "terraform.tfvars.secret" >> ../.gitignore

# Run terraform
terraform plan -var-file="terraform.tfvars.secret"
terraform apply -var-file="terraform.tfvars.secret"
```

### Option C: Google Cloud Secret Manager

```bash
# Store secrets in Secret Manager first
echo -n "your-gemini-key" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "your-github-token" | gcloud secrets create GITHUB_TOKEN --data-file=-

# Then use in Terraform
export TF_VAR_gemini_api_key=$(gcloud secrets versions access latest --secret="GEMINI_API_KEY")
export TF_VAR_github_token=$(gcloud secrets versions access latest --secret="GITHUB_TOKEN")

terraform apply
```

## Common Tasks

### View Current State

```bash
# Show all managed resources
terraform show

# Show specific resource
terraform show google_cloud_run_service.agentic_log_attacker

# Show outputs
terraform output
```

### Update Secrets

```bash
# Update ALLOWED_SERVICE_ACCOUNTS
terraform apply -var allowed_service_accounts_email="new-email@project.iam.gserviceaccount.com"

# Update API keys
export TF_VAR_gemini_api_key="new-key"
terraform apply
```

### Destroy Resources (Cleanup)

```bash
# Remove all Terraform-managed resources
terraform destroy

# Note: This will NOT delete the Cloud Run service if deploy_via_terraform=false
# To delete secrets and Cloud Build trigger only:
terraform destroy
```

### Backup State

```bash
# Copy local state file
cp terraform.tfstate terraform.tfstate.backup

# Or migrate to remote state (recommended for production)
# Edit main.tf and uncomment the backend configuration
```

## Troubleshooting

### Error: "Secret already exists"

If you get an error that the secret already exists:

```bash
# The secrets were created by a previous run or manually
# Terraform will update the secret versions automatically
# You can safely proceed
```

### Error: "Permission denied: Cloud Build"

Make sure Cloud Build service account has access to Secret Manager:

```bash
# This is automatically configured by Terraform
# If it fails, verify your IAM permissions
gcloud projects get-iam-policy globalbiting-dev
```

### Terraform State Issues

```bash
# Refresh the state
terraform refresh

# Check for drift (changes made outside Terraform)
terraform plan

# If needed, import existing resources
terraform import google_secret_manager_secret.allowed_service_accounts ALLOWED_SERVICE_ACCOUNTS
```

## Deployment Flow

### With Cloud Build (Recommended)

```
1. terraform init                    # Initialize Terraform
2. terraform plan                    # Review changes
3. terraform apply                   # Create secrets (only)
4. gcloud builds submit              # Deploy via Cloud Build
   (uses cloudbuild.yaml)            # Creates Cloud Run service
5. terraform output                  # View service URL
```

### With Terraform Only

```
1. terraform init                    # Initialize Terraform
2. terraform plan                    # Review changes
3. terraform apply                   # Create secrets + Cloud Run
4. terraform output                  # View service URL
```

## Integration with Dev-Nexus

After deployment, register the service with dev-nexus:

```bash
# Get the Cloud Run URL
SERVICE_URL=$(terraform output cloud_run_url)

# Verify the A2A endpoint
curl "${SERVICE_URL}/health"
curl "${SERVICE_URL}/.well-known/agent.json"

# Register with dev-nexus by providing the AgentCard URL
# https://your-cloud-run-url/.well-known/agent.json
```

## Security Best Practices

1. **Never commit secrets**: Use `.gitignore` for `terraform.tfvars`
2. **Use environment variables**: For sensitive values (recommended)
3. **Enable state locking**: For team environments
4. **Use remote state**: For production deployments
5. **Audit IAM roles**: Verify least privilege access
6. **Rotate secrets regularly**: Update API keys and tokens

## Support

For issues or questions:

1. Check Terraform logs: `TF_LOG=DEBUG terraform apply`
2. Review GCP Cloud Build logs: `gcloud builds log --stream`
3. Check Cloud Run service logs: `gcloud run services logs read agentic-log-attacker`
4. See main repository README for more information

## Additional Resources

- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run with Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service)
- [Secret Manager with Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret)

# Terraform Variables for A2A Integration Deployment

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "globalbiting-dev"
}

variable "gcp_region" {
  description = "GCP region for deployment (must match dev-nexus region)"
  type        = string
  default     = "us-central1"
}

variable "allowed_service_accounts_email" {
  description = "Email of the dev-nexus service account that can invoke this service"
  type        = string
  default     = "ai-ap-service@globalbiting-dev.iam.gserviceaccount.com"
}

variable "dev_nexus_url" {
  description = "URL of the dev-nexus service"
  type        = string
  default     = "https://pattern-discovery-agent-665374072631.us-central1.run.app/"
}

variable "gemini_api_key" {
  description = "Gemini API Key (from Secret Manager or environment)"
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub Personal Access Token (from Secret Manager or environment)"
  type        = string
  sensitive   = true
}

variable "container_image" {
  description = "Container image URI for Cloud Run deployment"
  type        = string
  default     = "gcr.io/globalbiting-dev/agentic-log-attacker:latest"
}

variable "deploy_via_terraform" {
  description = "Whether to deploy the Cloud Run service via Terraform (vs Cloud Build)"
  type        = bool
  default     = false
  # Set to true if deploying directly from Terraform
  # Set to false if deploying via Cloud Build, and Terraform only manages secrets
}

# Prefix to avoid secret id collisions across projects/apps
variable "secret_prefix" {
  description = "Prefix applied to Secret Manager secret IDs to avoid name collisions"
  type        = string
  default     = "agentic_log_attacker"
}

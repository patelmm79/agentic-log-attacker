# A2A Integration Deployment Configuration
# This Terraform configuration deploys agentic-log-attacker to Cloud Run
# with A2A (Agent-to-Agent) protocol compatibility

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Uncomment to use remote state (recommended for production)
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "agentic-log-attacker"
  # }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com"
  ])

  service            = each.value
  disable_on_destroy = false
}

# Create Secret Manager secret for ALLOWED_SERVICE_ACCOUNTS
resource "google_secret_manager_secret" "allowed_service_accounts" {
  secret_id = "ALLOWED_SERVICE_ACCOUNTS"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Set the secret version with the allowed service account
resource "google_secret_manager_secret_version" "allowed_service_accounts" {
  secret      = google_secret_manager_secret.allowed_service_accounts.id
  secret_data = var.allowed_service_accounts_email
}

# Create Secret Manager secret for GEMINI_API_KEY
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "GEMINI_API_KEY"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Set the secret version (value should be provided via terraform.tfvars)
resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

# Create Secret Manager secret for GITHUB_TOKEN
resource "google_secret_manager_secret" "github_token" {
  secret_id = "GITHUB_TOKEN"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Set the secret version (value should be provided via terraform.tfvars)
resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
}

# Get the Cloud Build service account
data "google_project" "project" {
}

# Grant Cloud Build access to secrets
resource "google_secret_manager_secret_iam_member" "cloud_build_allowed_sa" {
  secret_id = google_secret_manager_secret.allowed_service_accounts.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "cloud_build_gemini" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "cloud_build_github" {
  secret_id = google_secret_manager_secret.github_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Create Cloud Run service (if deploying directly from Terraform)
# Otherwise, this will be deployed via Cloud Build
resource "google_cloud_run_service" "agentic_log_attacker" {
  count    = var.deploy_via_terraform ? 1 : 0
  name     = "agentic-log-attacker"
  location = var.gcp_region
  project  = var.gcp_project_id

  template {
    spec {
      service_account_name = google_service_account.cloud_run_sa[0].email

      containers {
        image = var.container_image

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.gcp_project_id
        }

        env {
          name  = "CLOUD_RUN_REGION"
          value = var.gcp_region
        }

        env {
          name  = "GEMINI_MODEL_NAME"
          value = "gemini-2.5-flash"
        }

        env {
          name  = "DEV_NEXUS_URL"
          value = var.dev_nexus_url
        }

        # Secrets as environment variables
        env_from {
          source {
            secret_ref {
              name = google_secret_manager_secret.gemini_api_key.secret_id
            }
          }
        }

        env_from {
          source {
            secret_ref {
              name = google_secret_manager_secret.github_token.secret_id
            }
          }
        }

        env_from {
          source {
            secret_ref {
              name = google_secret_manager_secret.allowed_service_accounts.secret_id
            }
          }
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }
      }

      timeout_seconds = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "10"
        "autoscaling.knative.dev/minScale" = "1"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.gemini_api_key,
    google_secret_manager_secret_version.github_token,
    google_secret_manager_secret_version.allowed_service_accounts
  ]
}

# Make Cloud Run service private (no unauthenticated access)
resource "google_cloud_run_service_iam_member" "private" {
  count    = var.deploy_via_terraform ? 1 : 0
  service  = google_cloud_run_service.agentic_log_attacker[0].name
  location = google_cloud_run_service.agentic_log_attacker[0].location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.allowed_service_accounts_email}"
}

# Create service account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  count        = var.deploy_via_terraform ? 1 : 0
  account_id   = "agentic-log-attacker-sa"
  display_name = "Service account for agentic-log-attacker Cloud Run service"
}

# Grant Cloud Logging write permission to the service account
resource "google_project_iam_member" "cloud_logging" {
  count   = var.deploy_via_terraform ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa[0].email}"
}

# Grant Cloud Logging read permission (for log reading)
resource "google_project_iam_member" "logging_viewer" {
  count   = var.deploy_via_terraform ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.cloud_run_sa[0].email}"
}

# Grant Secret Manager access to Cloud Run service account
resource "google_secret_manager_secret_iam_member" "cloud_run_gemini" {
  count     = var.deploy_via_terraform ? 1 : 0
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa[0].email}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_github" {
  count     = var.deploy_via_terraform ? 1 : 0
  secret_id = google_secret_manager_secret.github_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa[0].email}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_allowed_sa" {
  count     = var.deploy_via_terraform ? 1 : 0
  secret_id = google_secret_manager_secret.allowed_service_accounts.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa[0].email}"
}

# Output the Cloud Run service URL
output "cloud_run_url" {
  value       = var.deploy_via_terraform ? google_cloud_run_service.agentic_log_attacker[0].status[0].url : null
  description = "URL of the deployed Cloud Run service"
}

output "secrets_created" {
  value = {
    allowed_service_accounts = google_secret_manager_secret.allowed_service_accounts.secret_id
    gemini_api_key           = google_secret_manager_secret.gemini_api_key.secret_id
    github_token             = google_secret_manager_secret.github_token.secret_id
  }
  description = "Secret Manager secrets created"
}

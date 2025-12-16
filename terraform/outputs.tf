# Terraform Outputs for A2A Integration Deployment

output "secrets_created" {
  value = {
    allowed_service_accounts = google_secret_manager_secret.allowed_service_accounts.secret_id
    gemini_api_key           = google_secret_manager_secret.gemini_api_key.secret_id
    github_token             = google_secret_manager_secret.github_token.secret_id
  }
  description = "Secret Manager secrets created"
}

output "service_account_email" {
  value       = var.deploy_via_terraform ? google_service_account.cloud_run_sa[0].email : null
  description = "Cloud Run service account email"
}

output "cloud_run_url" {
  value       = var.deploy_via_terraform ? google_cloud_run_service.agentic_log_attacker[0].status[0].url : null
  description = "URL of the deployed Cloud Run service"
}

output "cloud_run_service_name" {
  value       = var.deploy_via_terraform ? google_cloud_run_service.agentic_log_attacker[0].name : "agentic-log-attacker"
  description = "Cloud Run service name"
}

output "gcp_project_id" {
  value       = var.gcp_project_id
  description = "GCP Project ID"
}

output "gcp_region" {
  value       = var.gcp_region
  description = "GCP Region"
}

output "dev_nexus_service_account" {
  value       = var.allowed_service_accounts_email
  description = "Dev-nexus service account that can invoke this service"
}

output "next_steps" {
  value = var.deploy_via_terraform ? <<-EOT
    ✓ Terraform deployment complete!

    Cloud Run Service URL: ${google_cloud_run_service.agentic_log_attacker[0].status[0].url}

    Next steps:
    1. Test the service:
       curl ${google_cloud_run_service.agentic_log_attacker[0].status[0].url}/health

    2. Verify A2A integration:
       curl ${google_cloud_run_service.agentic_log_attacker[0].status[0].url}/.well-known/agent.json

    3. Register with dev-nexus:
       ${google_cloud_run_service.agentic_log_attacker[0].status[0].url}/.well-known/agent.json

    4. Run integration tests:
       python ../scripts/test_a2a_endpoint.py
  EOT : <<-EOT
    ✓ Terraform configuration applied!

    Secrets created:
    - ${google_secret_manager_secret.allowed_service_accounts.secret_id}
    - ${google_secret_manager_secret.gemini_api_key.secret_id}
    - ${google_secret_manager_secret.github_token.secret_id}

    Next steps:
    1. Deploy Cloud Run service:
       cd ..
       gcloud builds submit --config cloudbuild.yaml .

    2. Get the Cloud Run service URL:
       gcloud run services describe agentic-log-attacker --region ${var.gcp_region} --format 'value(status.url)'

    3. Test the service:
       curl <SERVICE_URL>/health

    4. Register with dev-nexus:
       <SERVICE_URL>/.well-known/agent.json
  EOT
  description = "Next steps after deployment"
}

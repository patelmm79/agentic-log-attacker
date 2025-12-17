**Terraform Coding Standards — Lessons Learned

Purpose
- **Scope:** Capture practical lessons from the recent Terraform work for agentic-log-attacker.
- **Audience:** Platform engineers and repository contributors who write or review Terraform.

**Key Lessons**
- **Namespace resources:** Use a `secret_prefix` (or similar) to avoid name collisions in shared projects; prefer names like `${var.secret_prefix}_GEMINI_API_KEY`.
- **Decide create vs import early:** If a resource already exists in the project, either import it into Terraform state or choose a new, namespaced resource name. Avoid trying to create an already-existing resource.
- **Provider/schema compatibility:** Terraform core and provider versions matter. Check `terraform version` and `terraform providers`. When schema errors surface, inspect the provider schema with `terraform providers schema -json` to choose the correct HCL shape.
- **Use provider pinning and init -upgrade carefully:** Declare `required_providers` and upgrade with `terraform init -upgrade` when you intentionally want newer provider features — test in a sandbox first.
- **Secret handling:** Never commit real secrets. Favor `TF_VAR_*` environment variables or secret stores. Add `terraform.tfvars` to .gitignore if used locally.
- **Secret Manager replication form:** Different provider versions expect different forms of the replication block. Consult provider schema — common acceptable forms include `replication { auto {} }` for automatic replication.
- **Cloud Run secrets:** Provider HCL shapes differ from platform YAML. Use `env { value_from { secret_key_ref { name = "..." key = "latest" } } }` rather than unsupported `env_from`/`source` blocks.

**Secret Manager Gotchas (explicit)**

- Provider/schema mismatch: different `google` provider versions expect different HCL shapes for Secret Manager resources (replication block shape, nested keys). When you see errors like "Unsupported block type" or "An argument named 'automatic' is not expected here", inspect the provider schema with:

  ```bash
  terraform providers schema -json > /tmp/schema.json
  jq '.provider_schemas["registry.terraform.io/hashicorp/google"].resource_schemas["google_secret_manager_secret"].block' /tmp/schema.json
  ```

- Replication block shape: use the schema to pick the correct syntax. Examples seen in this repo:
  - `replication { auto {} }`  (works with current `hashicorp/google` provider schema)
  - older/other forms may require different nesting — don't guess, inspect schema.

- Cloud Run env secret mapping: Cloud Run in Terraform expects `env.value_from.secret_key_ref` for per-variable secret references. Attempting to use `env_from { source { secret_ref { ... } } }` results in "unsupported block type" errors — prefer `env { value_from { secret_key_ref { name = "..." key = "latest" } } }`.

- Secret name collisions: creating common secret_ids like `GEMINI_API_KEY` will fail if another app/team already created them (`Error 409: Secret ... already exists`). Use a prefix or namespacing to avoid conflicts (see `secret_prefix` standard below).

**Secret Prefix — Required Standard**

- Standard: All new Secret Manager secret ids MUST be namespaced with a project/app prefix. Use the `secret_prefix` variable in Terraform and default to a repo-specific value (for this repo the example default is `agentic_log_attacker`). Example secret id: `${var.secret_prefix}_GEMINI_API_KEY`.
- Rationale: avoids collisions in shared GCP projects, makes it clear which application owns the secret, and simplifies migration.
- Implementation checklist when adding secrets:
  - Add or reuse `variable "secret_prefix"` in `variables.tf` with a meaningful default.
  - Use `${var.secret_prefix}_<SOMETHING>` for `secret_id` on `google_secret_manager_secret` resources.
  - Update `terraform.tfvars.example` with `secret_prefix` and document the naming convention.
  - If migrating from non-prefixed secrets, provide clear migration steps (create namespaced secrets, copy versions, update runtime to use new names, then remove old secrets).
- **IAM access:** Terraform can create secrets but you must ensure the Cloud Run runtime service account has `roles/secretmanager.secretAccessor`. Either let Terraform create the service account and IAM bindings (set `deploy_via_terraform=true`) or run `gcloud secrets add-iam-policy-binding` after apply.
- **Avoid inline sensitive values in examples:** Keep `terraform.tfvars.example` complete but use placeholder values only. For real runs, use environment variables, CI secrets, or provider-managed secret resources.
- **Naming conventions:** Use lowercase, underscore-separated prefixes for programmatic IDs (consistent with other infra naming conventions). Document naming rules in variables and examples.
- **Plan and review:** Always run `terraform plan -out=tfplan` then `terraform show -json tfplan` for machine-readable review in CI before `apply`.
- **State management:** Use remote state (GCS backend + locking) for team workflows. Document backend configuration and state locking in the repo.
- **Testing & validation:** Use `terraform validate`, `terraform fmt`, and optionally `tflint` in CI to catch formatting, lint, and provider issues quickly.
- **Importing resources:** When importing existing resources, import both resource and version where applicable (e.g., `google_secret_manager_secret` and `google_secret_manager_secret_version`). Record the exact import commands in docs.
- **Sensitive outputs:** Mark outputs as `sensitive = true` where appropriate and avoid printing secret contents in CI logs.
- **Rollback/Migration:** If switching existing resource names, provide migration steps: create new namespaced secrets, copy or add versions (via `gcloud secrets versions add`), update Cloud Run to reference new names, then remove old secrets once clients are migrated.

**Recommended Workflow**
- **Local dev:** Set `TF_VAR_*` for sensitive values, keep `deploy_via_terraform=false` until secrets and service accounts are tested.
- **Sandbox:** Run full `terraform init -upgrade`, `terraform plan`, `apply` in an isolated project to validate behavior.
- **CI gating:** Enforce `terraform fmt`, `terraform validate`, `tflint` and `plan` review for pull requests.
- **Production deploy:** Use remote state + locked apply, make sure provider versions are explicitly tested.

**Repository Conventions**
- **Files:** Keep examples in `terraform/terraform.tfvars.example`. Keep operational notes and migration steps in `docs/TERRAFORM_CODING_STANDARDS.md`.
- **Ignore:** Add `terraform.tfvars` and any local state to .gitignore. Do not commit environment-specific credentials.
- **Commits:** Use clear commit messages for infra changes, e.g., `feat(terraform): add secret_prefix` or `fix(terraform): secret replication schema`.

**Quick Commands (cheat-sheet)**
- Initialize and upgrade providers:
  - `terraform init -upgrade`
- Validate and plan:
  - `terraform validate`
  - `terraform plan -out=tfplan`
- Import an existing secret and its version:
  - `terraform import google_secret_manager_secret.gemini_api_key projects/PROJECT_ID/secrets/GEMINI_API_KEY`
  - `terraform import google_secret_manager_secret_version.gemini_api_key projects/PROJECT_ID/secrets/GEMINI_API_KEY/versions/latest`
- Grant secret access to a service account:
  - `gcloud secrets add-iam-policy-binding SECRET_NAME --member="serviceAccount:SA_EMAIL" --role="roles/secretmanager.secretAccessor" --project=PROJECT_ID`

**Appendix — Migration Example**
- Create new namespaced secrets via Terraform (set `TF_VAR_secret_prefix=agentic_log_attacker`) and `TF_VAR_deploy_via_terraform=false`.
- Copy existing secret payloads into the new secret versions using `gcloud secrets versions add`.
- Grant runtime SA access to new secrets.
- Point Cloud Run to the new secrets and test.
- Once verified, remove the old secrets (and optionally import them into Terraform state for safe deletion).

Contact
- **Owner:** Platform infra team
- **Location:** `docs/TERRAFORM_CODING_STANDARDS.md` in this repo

End of document

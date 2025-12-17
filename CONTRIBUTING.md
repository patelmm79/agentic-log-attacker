Thank you for contributing!

This repository follows infrastructure standards. Please follow the checklist below when opening PRs that touch Terraform code.

- [ ] Read the Terraform coding standards: [docs/TERRAFORM_CODING_STANDARDS.md](docs/TERRAFORM_CODING_STANDARDS.md)
- [ ] Run `terraform fmt` and `terraform validate` locally
- [ ] Ensure no real credentials are committed; use `TF_VAR_*` or CI secrets
- [ ] Run the repository CI checks (format, validate, tflint)
- [ ] Add or update `terraform.tfvars.example` when adding variables
- [ ] Provide migration steps when renaming or replacing existing infra resources

- [ ] Use `secret_prefix` for any new Secret Manager secrets and document the prefix in `terraform.tfvars.example`.

Notes:
- Avoid generic secret IDs (e.g., `GEMINI_API_KEY`) — prefer namespaced ids like `${secret_prefix}_GEMINI_API_KEY`.

If your change affects deployment, make sure to coordinate with the platform team and follow the remote state and apply procedures documented in the repo.

Thank you — the maintainers

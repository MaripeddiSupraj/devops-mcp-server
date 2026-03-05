# Security Policy

## Reporting a Vulnerability
Please do not open public GitHub issues for vulnerabilities.

Report privately to: `security@your-domain.com` (replace with your real security contact).

Include:
- affected endpoint/tool
- impact summary
- reproduction steps
- suggested fix (if available)

## Supported Versions
Only the latest release tag is considered fully supported for security fixes.

## Hardening Expectations
- Use least-privilege Kubernetes RBAC.
- Use restricted IAM roles.
- Keep `TERRAFORM_APPLY_REQUIRE_APPROVAL=true` in production.
- Store all auth and approval secrets in a secret manager (Kubernetes Secret, Vault, etc.).

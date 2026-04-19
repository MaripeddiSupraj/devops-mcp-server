# Security Policy

## Supported versions

Only the latest release on `main` receives security fixes.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: supraj.maripeddi@gmail.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

You will receive an acknowledgement within 48 hours and a resolution timeline within 7 days.

## Scope

This server has privileged access to real infrastructure (AWS, Kubernetes, Terraform, GitHub). The following classes of vulnerability are in scope:

- Authentication bypass on `/tools/execute` or `/audit`
- Path traversal in Terraform working directory validation
- Command injection via tool inputs
- API key leakage via logs or responses
- Privilege escalation via crafted tool inputs

## Security design decisions

- **API key auth**: All mutating endpoints require `MCP_API_KEY`. Timing-safe comparison via `hmac.compare_digest`.
- **Terraform path isolation**: All Terraform paths are resolved (symlinks dereferenced) and validated against `TERRAFORM_ALLOWED_BASE_DIR` before execution.
- **No shell=True**: All subprocess calls pass arguments as lists, never via shell interpolation.
- **Audit log**: Every tool invocation is recorded with a masked key hint, inputs, status, and duration.
- **Rate limiting**: Execute endpoints are rate-limited per IP (60/min sync, 20/min batch, 30/min async).
- **CORS**: Set `CORS_ORIGINS` to explicit origins in production — never use `*` with an API key.

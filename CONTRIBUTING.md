# Contributing

## Development Setup
1. Create virtual environment: `python3 -m venv .venv`
2. Activate: `source .venv/bin/activate`
3. Install deps: `pip install -r requirements.txt`
4. Run verification: `make verify`

## Pull Request Rules
- Open PRs against `main`.
- Keep PRs focused and small.
- Add or update tests for behavior changes.
- Do not include secrets in code, docs, or test fixtures.

## Commit Style
- Use imperative, concise commit messages.
- Example: `add approval token validation for terraform apply`

## Security-Sensitive Changes
For changes in auth, Terraform apply behavior, or deployment security controls:
- include threat/risk notes in the PR description
- include rollback plan

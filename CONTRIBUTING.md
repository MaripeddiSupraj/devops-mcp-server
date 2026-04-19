# Contributing to devops-mcp-server

## Getting started

```bash
git clone <repo-url>
cd devops-mcp-server
pip install -r requirements.txt
cp .env.example .env   # fill in credentials you want to test
```

## Running tests

```bash
pytest tests/ -q
```

All 152 tests must pass before opening a PR. No external services are required — integrations are mocked.

## Adding a new tool

1. Create `tools/<service>/<tool_name>.py` with `TOOL_NAME`, `TOOL_DESCRIPTION`, `TOOL_INPUT_SCHEMA`, and `handler()`.
2. Register it in `server/registry.py` inside `build_registry()`.
3. Add tests under `tests/test_tools_<service>.py`.
4. Update `tests/test_registry.py` — add the tool name to `expected_tools`.
5. Update `tests/test_api.py` — increment the hardcoded tool count.

Nothing outside these five files needs to change.

## Pull request checklist

- [ ] `pytest tests/ -q` passes with no failures
- [ ] New tool has at least one happy-path and one error-path test
- [ ] Destructive tools carry the `"destructive"` tag
- [ ] No credentials or secrets committed (check with `git diff --staged`)
- [ ] PR description explains *why*, not just *what*

## Code style

- Python 3.11+, typed with standard `typing` annotations
- `structlog` for all logging — never `print()`
- Tool handlers must be synchronous functions (the executor runs them in a thread pool)
- No shell=True anywhere — pass args as lists

## Reporting issues

Open a GitHub issue. For security vulnerabilities, see [SECURITY.md](SECURITY.md).

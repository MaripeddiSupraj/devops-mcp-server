"""
tests/test_tools_github.py
---------------------------
Unit tests for GitHub tool handlers using mocked PyGithub.

No real GitHub API calls are made.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from github import GithubException


def _mock_repo(
    name="my-repo",
    full_name="owner/my-repo",
    description="A test repo",
    html_url="https://github.com/owner/my-repo",
    default_branch="main",
    stargazers_count=42,
    forks_count=7,
    open_issues_count=3,
    private=False,
    language="Python",
):
    repo = MagicMock()
    repo.name = name
    repo.full_name = full_name
    repo.description = description
    repo.html_url = html_url
    repo.default_branch = default_branch
    repo.stargazers_count = stargazers_count
    repo.forks_count = forks_count
    repo.open_issues_count = open_issues_count
    repo.private = private
    repo.language = language
    return repo


def _mock_pr(number=42, html_url="https://github.com/owner/repo/pull/42",
             state="open", title="My PR"):
    pr = MagicMock()
    pr.number = number
    pr.html_url = html_url
    pr.state = state
    pr.title = title
    return pr


# ── get_repo_info ─────────────────────────────────────────────────────────────

class TestGetRepoInfo:
    @patch("integrations.github_client._get_client")
    def test_get_repo_info_returns_dict(self, mock_get_client):
        mock_gh = MagicMock()
        mock_get_client.return_value = mock_gh
        mock_gh.get_repo.return_value = _mock_repo()

        from integrations.github_client import GitHubClient
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            result = client.get_repo_info("owner/my-repo")

        assert result["name"] == "my-repo"
        assert result["full_name"] == "owner/my-repo"
        assert result["stars"] == 42
        assert result["forks"] == 7
        assert result["open_issues"] == 3
        assert result["language"] == "Python"
        assert result["private"] is False

    @patch("integrations.github_client._get_client")
    def test_unknown_repo_raises_github_client_error(self, mock_get_client):
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)

        from integrations.github_client import GitHubClient, GitHubClientError
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            with pytest.raises(GitHubClientError, match="Failed to fetch repository"):
                client.get_repo_info("owner/nonexistent")

    @patch("integrations.github_client._get_client")
    def test_private_repo_marked_correctly(self, mock_get_client):
        mock_gh = MagicMock()
        mock_gh.get_repo.return_value = _mock_repo(private=True)

        from integrations.github_client import GitHubClient
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            result = client.get_repo_info("owner/private-repo")

        assert result["private"] is True


# ── create_pull_request ───────────────────────────────────────────────────────

class TestCreatePullRequest:
    @patch("integrations.github_client._get_client")
    def test_create_pr_success(self, mock_get_client):
        mock_gh = MagicMock()
        mock_repo = _mock_repo()
        mock_repo.create_pull.return_value = _mock_pr()
        mock_gh.get_repo.return_value = mock_repo

        from integrations.github_client import GitHubClient
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            result = client.create_pull_request(
                repo_full_name="owner/my-repo",
                title="My PR",
                body="Description",
                head="feature/my-feature",
                base="main",
            )

        assert result["number"] == 42
        assert result["url"] == "https://github.com/owner/repo/pull/42"
        assert result["state"] == "open"
        assert result["head"] == "feature/my-feature"
        assert result["base"] == "main"

    @patch("integrations.github_client._get_client")
    def test_create_pr_passes_correct_params(self, mock_get_client):
        mock_gh = MagicMock()
        mock_repo = _mock_repo()
        mock_repo.create_pull.return_value = _mock_pr()
        mock_gh.get_repo.return_value = mock_repo

        from integrations.github_client import GitHubClient
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            client.create_pull_request(
                repo_full_name="owner/repo",
                title="feat: add auth",
                body="Adds API key auth",
                head="feature/auth",
                base="develop",
                draft=True,
            )

        mock_repo.create_pull.assert_called_once_with(
            title="feat: add auth",
            body="Adds API key auth",
            head="feature/auth",
            base="develop",
            draft=True,
        )

    @patch("integrations.github_client._get_client")
    def test_api_error_on_create_raises_client_error(self, mock_get_client):
        mock_gh = MagicMock()
        mock_repo = _mock_repo()
        mock_repo.create_pull.side_effect = GithubException(
            422, {"message": "Validation Failed"}, None
        )
        mock_gh.get_repo.return_value = mock_repo

        from integrations.github_client import GitHubClient, GitHubClientError
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            with pytest.raises(GitHubClientError, match="Failed to create PR"):
                client.create_pull_request(
                    repo_full_name="owner/repo",
                    title="Bad PR",
                    body="",
                    head="nonexistent-branch",
                    base="main",
                )

    @patch("integrations.github_client._get_client")
    def test_draft_pr_created_as_draft(self, mock_get_client):
        mock_gh = MagicMock()
        mock_repo = _mock_repo()
        mock_pr = _mock_pr()
        mock_repo.create_pull.return_value = mock_pr
        mock_gh.get_repo.return_value = mock_repo

        from integrations.github_client import GitHubClient
        from integrations.github_client import _get_client
        _get_client.cache_clear()

        with patch("integrations.github_client._get_client") as mgc:
            mgc.return_value = mock_gh
            client = GitHubClient()
            client.create_pull_request(
                repo_full_name="owner/repo",
                title="Draft",
                body="WIP",
                head="wip",
                base="main",
                draft=True,
            )

        call_kwargs = mock_repo.create_pull.call_args[1]
        assert call_kwargs["draft"] is True

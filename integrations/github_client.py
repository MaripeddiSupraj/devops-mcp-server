"""
integrations/github_client.py
------------------------------
Thin wrapper around PyGithub (github3 package).
Provides a lazily-created, token-authenticated GitHub client.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from github import Github, GithubException, Repository

from core.auth import get_github_token
from core.logger import get_logger

log = get_logger(__name__)


class GitHubClientError(RuntimeError):
    """Wraps PyGithub exceptions in a domain-specific error."""


@lru_cache(maxsize=1)
def _get_client() -> Github:
    """Return a cached, authenticated PyGithub client."""
    token = get_github_token()
    client = Github(token)
    log.info("github_client_initialised")
    return client


class GitHubClient:
    """
    High-level GitHub operations used by MCP tool handlers.

    Methods raise GitHubClientError on API failures so callers
    do not need to know about PyGithub internals.
    """

    def __init__(self) -> None:
        self._gh = _get_client()

    def get_repo(self, full_name: str) -> Repository.Repository:
        """
        Fetch a repository by its full name (``owner/repo``).

        Raises:
            GitHubClientError: if the repo cannot be found or accessed.
        """
        try:
            repo = self._gh.get_repo(full_name)
            log.debug("github_repo_fetched", repo=full_name)
            return repo
        except GithubException as exc:
            raise GitHubClientError(
                f"Failed to fetch repository '{full_name}': {exc.data}"
            ) from exc

    def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False,
    ) -> dict:
        """
        Open a pull request and return a summary dict.

        Args:
            repo_full_name: ``owner/repo`` string.
            title:          PR title.
            body:           PR description (Markdown supported).
            head:           Source branch name.
            base:           Target branch (default ``main``).
            draft:          Create as draft PR.

        Returns:
            Dict with ``number``, ``url``, ``state``, ``title``.
        """
        repo = self.get_repo(repo_full_name)
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft,
            )
            log.info(
                "github_pr_created",
                repo=repo_full_name,
                pr_number=pr.number,
                url=pr.html_url,
            )
            return {
                "number": pr.number,
                "url": pr.html_url,
                "state": pr.state,
                "title": pr.title,
                "head": head,
                "base": base,
            }
        except GithubException as exc:
            raise GitHubClientError(
                f"Failed to create PR in '{repo_full_name}': {exc.data}"
            ) from exc

    def get_repo_info(self, repo_full_name: str) -> dict:
        """
        Return a trimmed info dict for a repository.
        """
        repo = self.get_repo(repo_full_name)
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "url": repo.html_url,
            "default_branch": repo.default_branch,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "open_issues": repo.open_issues_count,
            "private": repo.private,
            "language": repo.language,
        }

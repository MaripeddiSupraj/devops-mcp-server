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
        """Return a trimmed info dict for a repository."""
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

    def list_issues(
        self,
        repo_full_name: str,
        state: str = "open",
        label: Optional[str] = None,
        limit: int = 30,
    ) -> list:
        """
        List issues in a repository.

        Args:
            repo_full_name: ``owner/repo`` string.
            state:          ``open``, ``closed``, or ``all``.
            label:          Filter by label name (optional).
            limit:          Maximum number of issues to return.
        """
        repo = self.get_repo(repo_full_name)
        try:
            kwargs: dict = {"state": state}
            if label:
                kwargs["labels"] = [label]
            issues_paged = repo.get_issues(**kwargs)
            issues = []
            for issue in issues_paged[:limit]:
                # Skip pull requests (GitHub API returns PRs as issues too)
                if issue.pull_request:
                    continue
                issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "url": issue.html_url,
                    "author": issue.user.login if issue.user else None,
                    "labels": [lb.name for lb in issue.labels],
                    "created_at": issue.created_at.isoformat() if issue.created_at else None,
                    "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                    "comments": issue.comments,
                })
            return issues
        except GithubException as exc:
            raise GitHubClientError(
                f"Failed to list issues in '{repo_full_name}': {exc.data}"
            ) from exc

    def trigger_workflow(
        self,
        repo_full_name: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[dict] = None,
    ) -> dict:
        """
        Trigger a GitHub Actions workflow dispatch event.

        Args:
            repo_full_name: ``owner/repo`` string.
            workflow_id:    Workflow file name (e.g. ``ci.yml``) or numeric ID.
            ref:            Branch or tag to run the workflow on.
            inputs:         Optional workflow_dispatch inputs dict.

        Returns:
            Dict confirming the dispatch was accepted.
        """
        repo = self.get_repo(repo_full_name)
        try:
            workflow = repo.get_workflow(workflow_id)
            success = workflow.create_dispatch(ref=ref, inputs=inputs or {})
            if not success:
                raise GitHubClientError(
                    f"Workflow dispatch returned false for '{workflow_id}' on '{ref}'"
                )
            log.info("github_workflow_triggered", repo=repo_full_name, workflow=workflow_id, ref=ref)
            return {
                "dispatched": True,
                "repo": repo_full_name,
                "workflow": workflow_id,
                "ref": ref,
                "inputs": inputs or {},
            }
        except GithubException as exc:
            raise GitHubClientError(
                f"Failed to trigger workflow '{workflow_id}': {exc.data}"
            ) from exc

    def create_release(
        self,
        repo_full_name: str,
        tag_name: str,
        name: str,
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
        target_commitish: str = "main",
    ) -> dict:
        """
        Create a GitHub release.

        Args:
            repo_full_name:    ``owner/repo`` string.
            tag_name:          Tag to create (e.g. ``v1.2.3``).
            name:              Release title.
            body:              Release notes (Markdown).
            draft:             Publish as draft.
            prerelease:        Mark as pre-release.
            target_commitish:  Branch or commit SHA for the tag.

        Returns:
            Dict with release ``id``, ``url``, ``tag``, ``name``.
        """
        repo = self.get_repo(repo_full_name)
        try:
            release = repo.create_git_release(
                tag=tag_name,
                name=name,
                message=body,
                draft=draft,
                prerelease=prerelease,
                target_commitish=target_commitish,
            )
            log.info("github_release_created", repo=repo_full_name, tag=tag_name, url=release.html_url)
            return {
                "id": release.id,
                "tag": tag_name,
                "name": release.title,
                "url": release.html_url,
                "draft": draft,
                "prerelease": prerelease,
            }
        except GithubException as exc:
            raise GitHubClientError(
                f"Failed to create release '{tag_name}' in '{repo_full_name}': {exc.data}"
            ) from exc

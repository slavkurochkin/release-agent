"""GitHub API client for fetching release context.

This module fetches PR data from GitHub's REST API to build the context
the agent needs for risk assessment. It gathers:
- PR metadata (title, description, author)
- File changes (paths, additions, deletions, patches)
- Commit messages

Design notes:
- Uses httpx for async HTTP requests
- Implements rate limit handling and pagination
- Uses a Protocol so the agent doesn't depend on the concrete implementation
  (makes testing with mocks easy)

GitHub API docs: https://docs.github.com/en/rest
"""

from __future__ import annotations

import os
from typing import Protocol

import httpx

from release_agent.schemas import FileChange, ReleaseInput


# ---------------------------------------------------------------------------
# Protocol (Interface)
# ---------------------------------------------------------------------------


class GitHubClientProtocol(Protocol):
    """Protocol defining the interface for GitHub data fetching.

    By coding against this protocol (not the concrete class), the agent
    and tests can use mock implementations without touching real GitHub.
    """

    async def get_pr_data(self, repo: str, pr_number: int) -> ReleaseInput:
        """Fetch all PR data and return it as a ReleaseInput.

        Args:
            repo: Repository in "owner/name" format
            pr_number: Pull request number

        Returns:
            A ReleaseInput populated with data from the PR
        """
        ...


# ---------------------------------------------------------------------------
# Concrete Implementation
# ---------------------------------------------------------------------------


class GitHubClient:
    """Real GitHub API client using httpx.

    Usage:
        client = GitHubClient(token="ghp_...")
        release_data = await client.get_pr_data("myorg/api", 123)
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None) -> None:
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token. Falls back to
                   GITHUB_TOKEN environment variable if not provided.
        """
        # TODO: Set up the httpx async client with auth headers.
        #
        # Steps:
        # 1. Resolve the token:
        #    self._token = token or os.environ.get("GITHUB_TOKEN", "")
        #
        # 2. Set up headers:
        #    self._headers = {
        #        "Authorization": f"Bearer {self._token}",
        #        "Accept": "application/vnd.github.v3+json",
        #        "X-GitHub-Api-Version": "2022-11-28",
        #    }
        #
        # Hint: You'll create the httpx.AsyncClient in each method
        # (or use a context manager) to avoid connection lifecycle issues.
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._headers: dict[str, str] = {}

    async def get_pr_data(self, repo: str, pr_number: int) -> ReleaseInput:
        """Fetch all PR data and assemble it into a ReleaseInput.

        This method makes multiple API calls:
        1. GET /repos/{repo}/pulls/{pr_number} - PR metadata
        2. GET /repos/{repo}/pulls/{pr_number}/files - Changed files
        3. GET /repos/{repo}/pulls/{pr_number}/commits - Commit messages

        Args:
            repo: Repository in "owner/name" format
            pr_number: Pull request number

        Returns:
            A ReleaseInput populated with PR data

        Raises:
            httpx.HTTPStatusError: If any GitHub API call fails
        """
        # TODO: Implement the full PR data fetch.
        #
        # Steps:
        # 1. Create an httpx.AsyncClient:
        #    async with httpx.AsyncClient(
        #        base_url=self.BASE_URL,
        #        headers=self._headers,
        #        timeout=30.0,
        #    ) as client:
        #
        # 2. Fetch PR metadata:
        #    pr_resp = await client.get(f"/repos/{repo}/pulls/{pr_number}")
        #    pr_resp.raise_for_status()
        #    pr_data = pr_resp.json()
        #
        # 3. Fetch changed files (handle pagination for PRs with many files):
        #    files_resp = await client.get(
        #        f"/repos/{repo}/pulls/{pr_number}/files",
        #        params={"per_page": 100},
        #    )
        #    files_data = files_resp.json()
        #
        # 4. Fetch commits:
        #    commits_resp = await client.get(
        #        f"/repos/{repo}/pulls/{pr_number}/commits",
        #        params={"per_page": 100},
        #    )
        #    commits_data = commits_resp.json()
        #
        # 5. Transform into schema objects:
        #    files_changed = [
        #        FileChange(
        #            path=f["filename"],
        #            additions=f["additions"],
        #            deletions=f["deletions"],
        #            patch=f.get("patch", ""),
        #        )
        #        for f in files_data
        #    ]
        #    commit_messages = [c["commit"]["message"] for c in commits_data]
        #
        # 6. Build and return ReleaseInput:
        #    return ReleaseInput(
        #        repo=repo,
        #        pr_number=pr_number,
        #        title=pr_data["title"],
        #        description=pr_data.get("body", ""),
        #        author=pr_data["user"]["login"],
        #        files_changed=files_changed,
        #        commit_messages=commit_messages,
        #    )
        raise NotImplementedError("TODO: Implement GitHub PR data fetch")

    async def _handle_pagination(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> list[dict]:
        """Handle GitHub API pagination for endpoints that return lists.

        GitHub returns a 'Link' header with next/prev/last URLs for
        paginated responses.

        Args:
            client: The httpx client to use
            url: The initial URL to fetch

        Returns:
            All items across all pages
        """
        # TODO: Implement pagination handling.
        #
        # Steps:
        # 1. Fetch the first page
        # 2. Check for 'Link' header with rel="next"
        # 3. If present, fetch the next page and append results
        # 4. Repeat until no more pages
        #
        # Hint: The Link header format is:
        #   <https://api.github.com/...?page=2>; rel="next",
        #   <https://api.github.com/...?page=5>; rel="last"
        raise NotImplementedError("TODO: Implement pagination")


# ---------------------------------------------------------------------------
# Mock Implementation (for testing)
# ---------------------------------------------------------------------------


class MockGitHubClient:
    """Mock GitHub client that returns predefined data.

    Use this in tests and local development when you don't want to hit
    the real GitHub API.

    Usage:
        client = MockGitHubClient(mock_data={"myorg/api": {123: some_data}})
        result = await client.get_pr_data("myorg/api", 123)
    """

    def __init__(self, mock_data: dict | None = None) -> None:
        """Initialize with optional predefined data.

        Args:
            mock_data: Nested dict of repo -> pr_number -> ReleaseInput data
        """
        self._mock_data = mock_data or {}

    async def get_pr_data(self, repo: str, pr_number: int) -> ReleaseInput:
        """Return mock PR data.

        Args:
            repo: Repository identifier
            pr_number: PR number

        Returns:
            A ReleaseInput with mock data

        Raises:
            KeyError: If no mock data exists for this repo/PR
        """
        # TODO: Implement mock data lookup.
        #
        # Steps:
        # 1. Look up the data in self._mock_data
        # 2. If found, return ReleaseInput.model_validate(data)
        # 3. If not found, return a default minimal ReleaseInput
        raise NotImplementedError("TODO: Implement mock GitHub client")

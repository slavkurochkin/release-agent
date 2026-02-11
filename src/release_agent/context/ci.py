"""CI results parser for fetching build and test outcomes.

This module provides an interface for fetching CI pipeline results
from various CI systems (GitHub Actions, CircleCI, etc.). For Phase 3,
it starts with a mock implementation and a GitHub Actions client.

The CI results tell the agent whether automated checks passed or failed,
which is a critical signal in risk assessment — a release with failing
tests is fundamentally different from one with all green checks.

Design notes:
- Uses Protocol for dependency inversion (swap real/mock easily)
- Parses CI-specific formats into our generic CIResult schema
- Handles the common case where CI status is available via GitHub's
  commit status API or check runs API
"""

from __future__ import annotations

import os
from typing import Protocol

import httpx

from release_agent.schemas import CIResult

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class CIClientProtocol(Protocol):
    """Protocol for CI result fetchers.

    Any CI integration (GitHub Actions, CircleCI, Jenkins) should
    implement this interface.
    """

    async def get_ci_results(self, repo: str, ref: str) -> list[CIResult]:
        """Fetch CI results for a given commit reference.

        Args:
            repo: Repository in "owner/name" format
            ref: Git reference (commit SHA, branch name, or PR head ref)

        Returns:
            List of CIResult objects representing each check
        """
        ...


# ---------------------------------------------------------------------------
# GitHub Actions Implementation
# ---------------------------------------------------------------------------


class GitHubActionsCIClient:
    """Fetches CI results from GitHub Actions via the Check Runs API.

    GitHub's check runs API provides status for all CI checks associated
    with a commit, regardless of which CI system produced them.

    API docs: https://docs.github.com/en/rest/checks/runs
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None) -> None:
        """Initialize the CI client.

        Args:
            token: GitHub token with repo access
        """
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self._token:
            self._headers["Authorization"] = f"Bearer {self._token}"

    async def get_ci_results(self, repo: str, ref: str) -> list[CIResult]:
        """Fetch check run results for a commit.

        Args:
            repo: Repository in "owner/name" format
            ref: Git commit SHA

        Returns:
            List of CIResult objects
        """
        # TODO: Implement GitHub Actions CI results fetch.
        #
        # Steps:
        # 1. Create httpx.AsyncClient with auth headers
        #
        # 2. Fetch check runs:
        #    resp = await client.get(
        #        f"/repos/{repo}/commits/{ref}/check-runs",
        #        params={"per_page": 100},
        #    )
        #    data = resp.json()
        #
        # 3. Transform into CIResult objects:
        #    results = []
        #    for run in data["check_runs"]:
        #        passed = run["conclusion"] == "success"
        #        results.append(CIResult(
        #            name=run["name"],
        #            passed=passed,
        #            details=run.get("output", {}).get("summary", ""),
        #        ))
        #
        # 4. Return results
        #
        # Hint: Check run conclusions can be: success, failure, neutral,
        # cancelled, skipped, timed_out, action_required.
        # For our purposes, only "success" counts as passed.
        # raise NotImplementedError("TODO: Implement GitHub Actions CI fetch")

        async with httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self._headers,
            timeout=30.0,
        ) as client:
            resp = await client.get(
                f"/repos/{repo}/commits/{ref}/check-runs",
                params={"per_page": 100},
            )
            data = resp.json()

            results = []
            for run in data["check_runs"]:
                passed = run["conclusion"] == "success"
                results.append(CIResult(
                    name=run["name"],
                    passed=passed,
                    details=run.get("output", {}).get("summary", ""),
                ))

            return results
# ---------------------------------------------------------------------------
# Mock Implementation
# ---------------------------------------------------------------------------


class MockCIClient:
    """Mock CI client for testing and local development.

    Returns predefined CI results without hitting any external API.
    """

    def __init__(self, results: list[CIResult] | None = None) -> None:
        """Initialize with optional predefined results.

        Args:
            results: CI results to return. If None, returns default passing results.
        """
        self._results = results

    async def get_ci_results(self, repo: str, ref: str) -> list[CIResult]:
        """Return mock CI results.

        Args:
            repo: Repository (ignored in mock)
            ref: Git ref (ignored in mock)

        Returns:
            Predefined or default CI results
        """
        # TODO: Return mock CI results.
        #
        # Steps:
        # 1. If self._results is set, return it
        # 2. Otherwise, return sensible defaults:
        #    return [
        #        CIResult(name="unit-tests", passed=True, details="All 142 tests passed"),
        #        CIResult(name="lint", passed=True, details="No issues found"),
        #        CIResult(name="build", passed=True, details="Build successful"),
        #        CIResult(name="type-check", passed=True, details="No type errors"),
        #    ]
        if self._results is not None:
            return self._results

        return [
            CIResult(name="unit-tests", passed=True, details="All 142 tests passed"),
            CIResult(name="lint", passed=True, details="No issues found"),
            CIResult(name="build", passed=True, details="Build successful"),
            CIResult(name="type-check", passed=True, details="No type errors"),
        ]

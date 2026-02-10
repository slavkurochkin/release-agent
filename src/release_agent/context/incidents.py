"""Incident history loader for recent production incidents.

This module provides context about recent production incidents, which is
a critical input for risk assessment. If the team is already dealing with
a P1 outage, deploying a risky change is much more dangerous.

The loader supports multiple backends:
- Local JSON file (for development and testing)
- (Future) Firestore or BigQuery for production incident databases
- (Future) PagerDuty or Opsgenie API integration

Design notes:
- Starts simple with JSON file, upgrades to real backends later
- Uses the same Protocol pattern as other context modules
- Returns plain strings (incident descriptions) since the agent
  needs natural language context, not structured incident data
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class IncidentLoaderProtocol(Protocol):
    """Protocol for loading recent incident history."""

    async def get_recent_incidents(
        self,
        repo: str,
        lookback_days: int = 7,
    ) -> list[str]:
        """Fetch recent incidents related to a repository.

        Args:
            repo: Repository identifier (may be used to filter incidents)
            lookback_days: How many days back to look for incidents

        Returns:
            List of incident description strings
        """
        ...


# ---------------------------------------------------------------------------
# JSON File Implementation
# ---------------------------------------------------------------------------


class JSONIncidentLoader:
    """Loads incident history from a local JSON file.

    This is the simplest implementation — good for development, testing,
    and demos. The JSON file format is:

    [
        {
            "id": "INC-001",
            "title": "Database connection pool exhausted",
            "severity": "P1",
            "timestamp": "2024-01-15T14:30:00Z",
            "repo": "myorg/backend-api",
            "description": "Connection pool hit max limit during peak traffic",
            "resolved": true
        },
        ...
    ]
    """

    def __init__(self, file_path: str | Path | None = None) -> None:
        """Initialize with path to the incidents JSON file.

        Args:
            file_path: Path to JSON file. Defaults to ./incidents.json
        """
        self._file_path = Path(file_path) if file_path else Path("incidents.json")

    async def get_recent_incidents(
        self,
        repo: str,
        lookback_days: int = 7,
    ) -> list[str]:
        """Load and filter incidents from the JSON file.

        Args:
            repo: Repository to filter incidents for
            lookback_days: How many days back to include

        Returns:
            List of formatted incident description strings
        """
        # TODO: Implement JSON-based incident loading.
        #
        # Steps:
        # 1. Check if the file exists:
        #    if not self._file_path.exists():
        #        return []
        #
        # 2. Load the JSON file:
        #    with open(self._file_path) as f:
        #        incidents = json.load(f)
        #
        # 3. Filter by repo (if the incident has a repo field):
        #    relevant = [
        #        inc for inc in incidents
        #        if inc.get("repo", "") == repo or inc.get("repo", "") == ""
        #    ]
        #
        # 4. Filter by time window:
        #    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        #    recent = [
        #        inc for inc in relevant
        #        if datetime.fromisoformat(
        #            inc["timestamp"].replace("Z", "+00:00")
        #        ).replace(tzinfo=None) > cutoff
        #    ]
        #
        # 5. Format as readable strings:
        #    return [
        #        f"[{inc['severity']}] {inc['title']}: {inc['description']}"
        #        for inc in recent
        #    ]
        raise NotImplementedError("TODO: Implement JSON incident loader")


# ---------------------------------------------------------------------------
# Mock Implementation
# ---------------------------------------------------------------------------


class MockIncidentLoader:
    """Mock incident loader for testing.

    Returns predefined incidents without reading from any source.
    """

    def __init__(self, incidents: list[str] | None = None) -> None:
        """Initialize with optional predefined incidents.

        Args:
            incidents: Incident descriptions to return. If None, returns empty list.
        """
        self._incidents = incidents or []

    async def get_recent_incidents(
        self,
        repo: str,
        lookback_days: int = 7,
    ) -> list[str]:
        """Return mock incidents.

        Args:
            repo: Repository (ignored in mock)
            lookback_days: Lookback period (ignored in mock)

        Returns:
            Predefined incident list
        """
        # TODO: Return self._incidents
        raise NotImplementedError("TODO: Implement mock incident loader")

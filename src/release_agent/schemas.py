"""Pydantic models defining the input/output contract for the release risk agent.

These schemas serve as the single source of truth for what data flows in and out
of the agent. They are used for:
- Request/response validation in the API layer (Phase 2)
- Structured output parsing from the LLM (Phase 1)
- Test fixture typing (Phase 5)
- OpenAPI documentation generation (Phase 2)

Key design decisions:
- All fields have explicit types and descriptions for self-documenting schemas
- Enums constrain categorical values to prevent drift
- The output schema mirrors what we ask the LLM to produce
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Risk classification for a release.

    LOW: Routine change, minimal blast radius
    MEDIUM: Some risk factors present, proceed with caution
    HIGH: Significant risk, requires careful review
    CRITICAL: Severe risk, strong recommendation against releasing
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Decision(str, Enum):
    """Binary release decision.

    GO: Safe to release (possibly with conditions)
    NO_GO: Do not release without addressing concerns
    """

    GO = "GO"
    NO_GO = "NO_GO"


# ---------------------------------------------------------------------------
# Input Schemas
# ---------------------------------------------------------------------------


class FileChange(BaseModel):
    """A single file changed in the release.

    Attributes:
        path: File path relative to repo root (e.g., "src/auth/login.py")
        additions: Number of lines added
        deletions: Number of lines deleted
        patch: The actual diff/patch content (may be truncated for large diffs)
    """

    path: str = Field(..., description="File path relative to repo root")
    additions: int = Field(0, ge=0, description="Lines added")
    deletions: int = Field(0, ge=0, description="Lines deleted")
    patch: str = Field("", description="Diff content for this file")


class CIResult(BaseModel):
    """Result from a CI pipeline check.

    Attributes:
        name: Name of the CI check (e.g., "unit-tests", "lint", "build")
        passed: Whether the check passed
        details: Additional details or error messages
    """

    name: str = Field(..., description="CI check name")
    passed: bool = Field(..., description="Whether the check passed")
    details: str = Field("", description="Additional details or error output")


class ReleaseInput(BaseModel):
    """Input data for a release risk assessment.

    This is the primary input schema. In Phase 1, this data is provided
    directly. In Phase 3+, the context builders populate this automatically
    from GitHub, CI systems, and incident history.

    Attributes:
        repo: Repository name (e.g., "myorg/backend-api")
        pr_number: Pull request number being assessed
        title: PR title or release title
        description: PR description / release notes
        author: Who authored the change
        files_changed: List of files modified in this release
        ci_results: Results from CI pipeline checks
        commit_messages: List of commit messages in this release
        recent_incidents: Descriptions of recent production incidents
        deployment_target: Target environment (e.g., "production", "staging")
    """

    # TODO: Add validators to ensure at least one of files_changed or
    # commit_messages is provided. Use Pydantic's @model_validator decorator.
    # Hint: A release with no file changes AND no commits is probably invalid.
    @model_validator(mode='after')
    def check_has_content(self) -> 'ReleaseInput':
        """Ensure the release has at least some content to assess."""
        if not self.files_changed and not self.commit_messages:
            raise ValueError("Release must have at least one of: " \
            "files_changed, commit_messages. "
                "Cannot assess risk with no information about what changed.")
        return self


    repo: str = Field(..., description="Repository identifier (e.g., 'myorg/api')")
    pr_number: int = Field(..., gt=0, description="Pull request number")
    title: str = Field(..., min_length=1, description="PR or release title")
    description: str = Field("", description="PR description or release notes")
    author: str = Field(..., description="Author of the change")
    files_changed: list[FileChange] = Field(
        default_factory=list, description="Files modified in this release"
    )
    ci_results: list[CIResult] = Field(
        default_factory=list, description="CI pipeline results"
    )
    commit_messages: list[str] = Field(
        default_factory=list, description="Commit messages in the release"
    )
    recent_incidents: list[str] = Field(
        default_factory=list,
        description="Recent production incidents (for context)",
    )
    deployment_target: str = Field(
        "production", description="Target environment for deployment"
    )


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------


class RiskFactor(BaseModel):
    """A single risk factor identified in the release.

    Attributes:
        category: Type of risk (e.g., "database", "authentication", "api_change")
        description: Human-readable explanation of the risk
        severity: How severe this risk factor is
    """

    category: str = Field(..., description="Risk category")
    description: str = Field(..., description="Explanation of the risk")
    severity: RiskLevel = Field(..., description="Severity of this factor")


class ReleaseOutput(BaseModel):
    """Structured output from the release risk agent.

    This schema defines exactly what the LLM must produce. It is used
    both as a Pydantic model for validation and (via .model_json_schema())
    to generate the JSON schema sent to OpenAI for structured output.

    Attributes:
        decision: GO or NO_GO recommendation
        risk_level: Overall risk classification
        risk_score: Numeric risk score from 0.0 (no risk) to 1.0 (maximum risk)
        risk_factors: List of identified risk factors
        summary: Brief human-readable summary of the assessment
        explanation: Detailed reasoning for the decision
        conditions: Conditions that must be met for a GO decision (if any)
        recommended_actions: Suggested actions before or during deployment
    """

    # TODO: Add a @model_validator that ensures consistency between fields:
    # - If decision is NO_GO, risk_level should be HIGH or CRITICAL
    # - If risk_score > 0.7, decision should be NO_GO
    # - If decision is GO with conditions, the conditions list should not be empty
    # Hint: Use @model_validator(mode='after') for cross-field validation.
    @model_validator(mode='after')
    def cehc_decision_consistency(self) -> 'ReleaseOutput':
        """Ensure the decision is consistent with the risk assessment."""
        # Rule 1: NO_GO decisions should have HIGH or CRITICAL risk level
        if self.decision == Decision.NO_GO and self.risk_level not in (
            RiskLevel.HIGH, RiskLevel.CRITICAL
        ):
            raise ValueError(
                f"Decision is NO_GO but risk_level is {self.risk_level}. "
                "NO_GO decisions should have HIGH or CRITICAL risk."
            )

        # Rule 2: If risk scores should result in NO_GO
        if self.risk_score > 0.7 and self.decision == Decision.GO:
            raise ValueError(
                f"Risk score is {self.risk_score} (> 0.7) but decision is GO."
                f"High-risk releases should be NO_GO."
            )
        
        # Rule 3: GO with conditions requires non-empty conditions list
        # (This one is a soft check -- uncomment if you want strict enforcement)
        # if self.decision == Decision.GO and self.risk_score > 0.3 and not self.conditions:
        #     raise ValueError(
        #         "GO decision with risk_score > 0.3 should include conditions."
        #     )

        return self
       

    decision: Decision = Field(..., description="GO or NO_GO recommendation")
    risk_level: RiskLevel = Field(..., description="Overall risk classification")
    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Numeric risk score (0.0 = safe, 1.0 = critical)"
    )
    risk_factors: list[RiskFactor] = Field(
        default_factory=list, description="Identified risk factors"
    )
    summary: str = Field(
        ...,
        min_length=10,
        description="Brief summary of the assessment (1-2 sentences)",
    )
    explanation: str = Field(
        ...,
        min_length=20,
        description="Detailed reasoning for the decision",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions for GO decision (empty if unconditional)",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended actions before/during deployment",
    )

"""Tests for the policy engine (Phase 4).

These tests verify that policy rules:
- Detect the conditions they're supposed to detect
- Return the correct violation types
- Don't trigger false positives
- Stack correctly when multiple rules apply

The policy engine is deterministic (no LLM involved), so these tests
are straightforward assertions without mocking.

Run with: pytest tests/test_policy.py -v
"""

from __future__ import annotations

import pytest

from release_agent.policy import (
    PolicyAction,
    PolicyViolation,
    apply_policies,
    rule_auth_changes,
    rule_ci_failures,
    rule_database_migration,
    rule_deploy_during_incident,
    rule_high_risk_threshold,
)
from release_agent.schemas import (
    CIResult,
    Decision,
    FileChange,
    ReleaseInput,
    ReleaseOutput,
    RiskFactor,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_input() -> ReleaseInput:
    """A minimal ReleaseInput for policy testing."""
    return ReleaseInput(
        repo="myorg/api",
        pr_number=1,
        title="Test PR",
        author="tester",
    )


@pytest.fixture
def base_output() -> ReleaseOutput:
    """A baseline GO output that policies may modify."""
    return ReleaseOutput(
        decision=Decision.GO,
        risk_level=RiskLevel.LOW,
        risk_score=0.2,
        risk_factors=[
            RiskFactor(
                category="scope",
                description="Small change",
                severity=RiskLevel.LOW,
            )
        ],
        summary="A simple low-risk change for testing policy rules.",
        explanation="This is a test output used as a baseline for policy engine tests. "
        "The policies may modify the decision, risk score, or add warnings.",
        conditions=[],
        recommended_actions=[],
    )


# ---------------------------------------------------------------------------
# CI Failure Rule Tests
# ---------------------------------------------------------------------------


class TestCIFailureRule:
    """Tests for rule_ci_failures."""

    def test_no_ci_results_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """No CI results means no violation (can't fail what doesn't exist)."""
        with pytest.raises(NotImplementedError):
            result = rule_ci_failures(base_output, base_input)
            # Once implemented: assert result is None

    def test_all_ci_passing_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """All passing CI checks should not trigger a violation."""
        base_input.ci_results = [
            CIResult(name="tests", passed=True),
            CIResult(name="lint", passed=True),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_ci_failures(base_output, base_input)
            # Once implemented: assert result is None

    def test_ci_failure_forces_nogo(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """A failing CI check should force NO_GO."""
        base_input.ci_results = [
            CIResult(name="tests", passed=False, details="3 tests failed"),
            CIResult(name="lint", passed=True),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_ci_failures(base_output, base_input)
            # Once implemented:
            # assert result is not None
            # assert result.action == PolicyAction.FORCE_NO_GO
            # assert "tests" in result.reason


# ---------------------------------------------------------------------------
# High Risk Threshold Rule Tests
# ---------------------------------------------------------------------------


class TestHighRiskThresholdRule:
    """Tests for rule_high_risk_threshold."""

    def test_low_risk_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score below 0.7 should not trigger."""
        base_output.risk_score = 0.5
        with pytest.raises(NotImplementedError):
            result = rule_high_risk_threshold(base_output, base_input)
            # Once implemented: assert result is None

    def test_high_risk_forces_nogo(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score above 0.7 should force NO_GO."""
        base_output.risk_score = 0.8
        with pytest.raises(NotImplementedError):
            result = rule_high_risk_threshold(base_output, base_input)
            # Once implemented:
            # assert result is not None
            # assert result.action == PolicyAction.FORCE_NO_GO

    def test_boundary_risk_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score at exactly 0.7 should not trigger (> not >=)."""
        base_output.risk_score = 0.7
        with pytest.raises(NotImplementedError):
            result = rule_high_risk_threshold(base_output, base_input)
            # Once implemented: assert result is None


# ---------------------------------------------------------------------------
# Database Migration Rule Tests
# ---------------------------------------------------------------------------


class TestDatabaseMigrationRule:
    """Tests for rule_database_migration."""

    def test_no_migration_files_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Regular files should not trigger migration rule."""
        base_input.files_changed = [
            FileChange(path="src/main.py", additions=10, deletions=5),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_database_migration(base_output, base_input)
            # Once implemented: assert result is None

    def test_migration_file_adjusts_risk(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Migration files should bump risk score."""
        base_input.files_changed = [
            FileChange(path="migrations/0001_initial.sql", additions=20, deletions=0),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_database_migration(base_output, base_input)
            # Once implemented:
            # assert result is not None
            # assert result.action == PolicyAction.ADJUST_RISK
            # assert result.risk_adjustment > 0

    def test_alembic_file_triggers_rule(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Alembic migration files should also trigger the rule."""
        base_input.files_changed = [
            FileChange(
                path="alembic/versions/abc123_add_column.py",
                additions=15,
                deletions=0,
            ),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_database_migration(base_output, base_input)
            # Once implemented:
            # assert result is not None


# ---------------------------------------------------------------------------
# Auth Changes Rule Tests
# ---------------------------------------------------------------------------


class TestAuthChangesRule:
    """Tests for rule_auth_changes."""

    def test_no_auth_files_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Non-auth files should not trigger."""
        base_input.files_changed = [
            FileChange(path="src/utils/helpers.py", additions=5, deletions=3),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_auth_changes(base_output, base_input)
            # Once implemented: assert result is None

    def test_auth_file_adjusts_risk(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Auth-related files should bump risk score."""
        base_input.files_changed = [
            FileChange(path="src/auth/login.py", additions=10, deletions=5),
        ]
        with pytest.raises(NotImplementedError):
            result = rule_auth_changes(base_output, base_input)
            # Once implemented:
            # assert result is not None
            # assert result.action == PolicyAction.ADJUST_RISK


# ---------------------------------------------------------------------------
# Deploy During Incident Rule Tests
# ---------------------------------------------------------------------------


class TestDeployDuringIncidentRule:
    """Tests for rule_deploy_during_incident."""

    def test_no_incidents_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """No incidents means no warning."""
        with pytest.raises(NotImplementedError):
            result = rule_deploy_during_incident(base_output, base_input)
            # Once implemented: assert result is None

    def test_active_incident_adds_warning(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Active incidents should add a warning."""
        base_input.recent_incidents = ["[P1] Database outage — ongoing"]
        with pytest.raises(NotImplementedError):
            result = rule_deploy_during_incident(base_output, base_input)
            # Once implemented:
            # assert result is not None
            # assert result.action == PolicyAction.ADD_WARNING


# ---------------------------------------------------------------------------
# Policy Engine Integration Tests
# ---------------------------------------------------------------------------


class TestApplyPolicies:
    """Tests for the apply_policies function."""

    def test_no_violations_returns_original(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """No policy violations should return the output unchanged."""
        # Empty rules list = no violations possible
        with pytest.raises(NotImplementedError):
            result = apply_policies(base_output, base_input, rules=[])
            # Once implemented:
            # assert result.decision == base_output.decision
            # assert result.risk_score == base_output.risk_score

    def test_ci_failure_overrides_go(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """CI failure should override a GO decision to NO_GO."""
        base_input.ci_results = [
            CIResult(name="tests", passed=False, details="Failed"),
        ]
        with pytest.raises(NotImplementedError):
            result = apply_policies(base_output, base_input)
            # Once implemented:
            # assert result.decision == Decision.NO_GO

    def test_multiple_rules_stack(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Multiple risk adjustments should stack."""
        base_input.files_changed = [
            FileChange(path="migrations/0001.sql", additions=10, deletions=0),
            FileChange(path="src/auth/login.py", additions=5, deletions=3),
        ]
        with pytest.raises(NotImplementedError):
            result = apply_policies(base_output, base_input)
            # Once implemented:
            # Both migration (+0.15) and auth (+0.1) adjustments applied
            # assert result.risk_score > base_output.risk_score

    def test_risk_score_capped_at_one(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score should never exceed 1.0 after adjustments."""
        base_output.risk_score = 0.9
        base_input.files_changed = [
            FileChange(path="migrations/0001.sql", additions=10, deletions=0),
            FileChange(path="src/auth/login.py", additions=5, deletions=3),
        ]
        with pytest.raises(NotImplementedError):
            result = apply_policies(base_output, base_input)
            # Once implemented:
            # assert result.risk_score <= 1.0

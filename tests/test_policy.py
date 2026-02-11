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

from pathlib import Path

import pytest

from release_agent.policy import (
    PolicyAction,
    PolicyConfig,
    RuleConfig,
    apply_policies,
    load_policy_config,
    rule_auth_changes,
    rule_ci_failures,
    rule_database_migration,
    rule_deploy_during_incident,
    rule_high_risk_threshold,
    rule_large_pr,
    rule_no_tests,
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
        commit_messages=["fix: test change"],
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
        result = rule_ci_failures(base_output, base_input)
        assert result is None

    def test_all_ci_passing_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """All passing CI checks should not trigger a violation."""
        base_input.ci_results = [
            CIResult(name="tests", passed=True),
            CIResult(name="lint", passed=True),
        ]
        result = rule_ci_failures(base_output, base_input)
        assert result is None

    def test_ci_failure_forces_nogo(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """A failing CI check should force NO_GO."""
        base_input.ci_results = [
            CIResult(name="tests", passed=False, details="3 tests failed"),
            CIResult(name="lint", passed=True),
        ]
        result = rule_ci_failures(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.FORCE_NO_GO
        assert "tests" in result.reason


# ---------------------------------------------------------------------------
# Large PR Rules Tests
# ---------------------------------------------------------------------------

class TestLargePRRule:
    def test_small_pr_no_violation(self, base_output, base_input):
        base_input.files_changed = [
            FileChange(path="src/main.py", additions=10, deletions=5),
        ]
        result = rule_large_pr(base_output, base_input)
        assert result is None

    def test_large_pr_adjusts_risk(self, base_output, base_input):
        base_input.files_changed = [
            FileChange(path="src/main.py", additions=300, deletions=250),
        ]
        result = rule_large_pr(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADJUST_RISK
        assert result.risk_adjustment == 0.1

    def test_boundary_500_no_violation(self, base_output, base_input):
        """Exactly 500 lines should NOT trigger (> not >=)."""
        base_input.files_changed = [
            FileChange(path="src/main.py", additions=300, deletions=200),
        ]
        result = rule_large_pr(base_output, base_input)
        assert result is None

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
        result = rule_high_risk_threshold(base_output, base_input)
        assert result is None

    def test_high_risk_forces_nogo(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score above 0.7 should force NO_GO."""
        base_output.risk_score = 0.8
        result = rule_high_risk_threshold(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.FORCE_NO_GO

    def test_boundary_risk_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score at exactly 0.7 should not trigger (> not >=)."""
        base_output.risk_score = 0.7
        result = rule_high_risk_threshold(base_output, base_input)
        assert result is None


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
        result = rule_database_migration(base_output, base_input)
        assert result is None

    def test_migration_file_adjusts_risk(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Migration files should bump risk score."""
        base_input.files_changed = [
            FileChange(path="migrations/0001_initial.sql", additions=20, deletions=0),
        ]
        result = rule_database_migration(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADJUST_RISK
        assert result.risk_adjustment > 0

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
        result = rule_database_migration(base_output, base_input)
        assert result is not None


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
        result = rule_auth_changes(base_output, base_input)
        assert result is None

    def test_auth_file_adjusts_risk(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Auth-related files should bump risk score."""
        base_input.files_changed = [
            FileChange(path="src/auth/login.py", additions=10, deletions=5),
        ]
        result = rule_auth_changes(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADJUST_RISK


# ---------------------------------------------------------------------------
# Deploy During Incident Rule Tests
# ---------------------------------------------------------------------------


class TestDeployDuringIncidentRule:
    """Tests for rule_deploy_during_incident."""

    def test_no_incidents_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """No incidents means no warning."""
        result = rule_deploy_during_incident(base_output, base_input)
        assert result is None

    def test_active_incident_adds_warning(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Active incidents should add a warning."""
        base_input.recent_incidents = ["[P1] Database outage — ongoing"]
        result = rule_deploy_during_incident(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADD_WARNING


# ---------------------------------------------------------------------------
# No Tests Rule Tests
# ---------------------------------------------------------------------------


class TestNoTestsRule:
    """Tests for rule_no_tests."""

    def test_no_files_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """No file changes means no violation."""
        base_input.files_changed = []
        result = rule_no_tests(base_output, base_input)
        assert result is None

    def test_source_with_tests_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Source changes accompanied by test changes should not trigger."""
        base_input.files_changed = [
            FileChange(path="src/auth/login.py", additions=10, deletions=5),
            FileChange(path="tests/test_login.py", additions=20, deletions=0),
        ]
        result = rule_no_tests(base_output, base_input)
        assert result is None

    def test_source_without_tests_triggers_warning(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Source changes without test changes should add a warning."""
        base_input.files_changed = [
            FileChange(path="src/auth/login.py", additions=10, deletions=5),
        ]
        result = rule_no_tests(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADD_WARNING
        assert "test" in result.reason.lower()

    def test_test_only_changes_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Only test file changes should not trigger."""
        base_input.files_changed = [
            FileChange(path="tests/test_login.py", additions=20, deletions=0),
        ]
        result = rule_no_tests(base_output, base_input)
        assert result is None

    def test_non_source_changes_no_violation(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Changes outside src/lib/app should not trigger."""
        base_input.files_changed = [
            FileChange(path="docs/README.md", additions=5, deletions=2),
            FileChange(path="config/settings.yaml", additions=1, deletions=1),
        ]
        result = rule_no_tests(base_output, base_input)
        assert result is None

    def test_lib_prefix_triggers(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Changes under lib/ without tests should trigger."""
        base_input.files_changed = [
            FileChange(path="lib/utils.py", additions=10, deletions=0),
        ]
        result = rule_no_tests(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADD_WARNING

    def test_app_prefix_triggers(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Changes under app/ without tests should trigger."""
        base_input.files_changed = [
            FileChange(path="app/models/user.py", additions=15, deletions=3),
        ]
        result = rule_no_tests(base_output, base_input)
        assert result is not None
        assert result.action == PolicyAction.ADD_WARNING


    def test_three_rules_stack(self, base_output, base_input):
        base_output.risk_score = 0.2
        base_input.files_changed = [
            FileChange(
                path="migrations/0001_add_users.sql",
                additions=20,
                deletions=0,
            ),
            FileChange(
                path="src/auth/oauth.py",
                additions=30,
                deletions=10,
            ),
        ]
        base_input.recent_incidents = ["[P2] Elevated error rate in payments"]

        result = apply_policies(base_output, base_input)

        # Risk adjustments stacked
        assert result.risk_score == pytest.approx(0.45)

        # Decision not overridden (no FORCE_NO_GO triggered)
        assert result.decision == Decision.GO

        # Warning added
        assert any("incident" in a.lower() for a in result.recommended_actions)

        # Two risk factors added (migration + auth)
        policy_factors = [f for f in result.risk_factors if f.category == "policy"]
        assert len(policy_factors) == 2



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
        result = apply_policies(base_output, base_input, rules=[])
        assert result.decision == base_output.decision
        assert result.risk_score == base_output.risk_score

    def test_ci_failure_overrides_go(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """CI failure should override a GO decision to NO_GO."""
        base_input.ci_results = [
            CIResult(name="tests", passed=False, details="Failed"),
        ]
        result = apply_policies(base_output, base_input)
        assert result.decision == Decision.NO_GO

    def test_multiple_rules_stack(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Multiple risk adjustments should stack."""
        base_input.files_changed = [
            FileChange(path="migrations/0001.sql", additions=10, deletions=0),
            FileChange(path="src/auth/login.py", additions=5, deletions=3),
        ]
        result = apply_policies(base_output, base_input)
        assert result.risk_score > base_output.risk_score

    def test_risk_score_capped_at_one(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Risk score should never exceed 1.0 after adjustments."""
        base_output.risk_score = 0.9
        base_input.files_changed = [
            FileChange(path="migrations/0001.sql", additions=10, deletions=0),
            FileChange(path="src/auth/login.py", additions=5, deletions=3),
        ]
        result = apply_policies(base_output, base_input)
        assert result.risk_score <= 1.0


# ---------------------------------------------------------------------------
# Policy Config Tests
# ---------------------------------------------------------------------------


class TestPolicyConfig:
    """Tests for YAML-based configurable policy rules."""

    def test_load_config_missing_file(self, tmp_path: Path) -> None:
        """Missing config file returns defaults."""
        cfg = load_policy_config(tmp_path / "nonexistent.yaml")
        assert cfg == PolicyConfig()
        assert cfg.rules == {}

    def test_load_config_valid_yaml(self, tmp_path: Path) -> None:
        """Valid YAML is loaded and validated."""
        config_file = tmp_path / "policy.yaml"
        config_file.write_text(
            "rules:\n"
            "  rule_high_risk_threshold:\n"
            "    threshold: 0.5\n"
        )
        cfg = load_policy_config(config_file)
        assert "rule_high_risk_threshold" in cfg.rules
        assert cfg.rules["rule_high_risk_threshold"].threshold == 0.5

    def test_load_config_invalid_yaml(self, tmp_path: Path) -> None:
        """Invalid YAML raises ValueError."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("rules:\n  - :\n  bad: [unbalanced")
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_policy_config(config_file)

    def test_load_config_invalid_schema(self, tmp_path: Path) -> None:
        """YAML that doesn't match the schema raises ValueError."""
        config_file = tmp_path / "bad_schema.yaml"
        config_file.write_text(
            "rules:\n"
            "  rule_ci_failures:\n"
            "    enabled: not_a_bool\n"
        )
        with pytest.raises(ValueError, match="Invalid policy config"):
            load_policy_config(config_file)

    def test_high_risk_threshold_respects_config(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Rule uses configured threshold instead of default 0.7."""
        base_output.risk_score = 0.6
        # Default threshold 0.7 would NOT trigger
        assert rule_high_risk_threshold(base_output, base_input) is None

        # Custom threshold 0.5 SHOULD trigger
        cfg = RuleConfig(threshold=0.5)
        result = rule_high_risk_threshold(base_output, base_input, config=cfg)
        assert result is not None
        assert result.action == PolicyAction.FORCE_NO_GO
        assert "0.5" in result.reason

    def test_database_migration_respects_config_patterns(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Rule uses configured patterns."""
        base_input.files_changed = [
            FileChange(path="db/changesets/001.sql", additions=10, deletions=0),
        ]
        # Default patterns won't match "changesets"
        assert rule_database_migration(base_output, base_input) is None

        # Custom patterns include "changesets"
        cfg = RuleConfig(patterns=["changesets"])
        result = rule_database_migration(base_output, base_input, config=cfg)
        assert result is not None
        assert result.action == PolicyAction.ADJUST_RISK

    def test_database_migration_respects_config_risk_adjustment(
        self, base_output: ReleaseOutput, base_input: ReleaseInput
    ) -> None:
        """Rule uses configured risk_adjustment."""
        base_input.files_changed = [
            FileChange(path="migrations/001.sql", additions=10, deletions=0),
        ]
        cfg = RuleConfig(risk_adjustment=0.3)
        result = rule_database_migration(base_output, base_input, config=cfg)
        assert result is not None
        assert result.risk_adjustment == 0.3

    def test_disabled_rule_is_skipped(
        self, base_output: ReleaseOutput, base_input: ReleaseInput, tmp_path: Path
    ) -> None:
        """Rules with enabled: false are skipped by apply_policies."""
        base_input.ci_results = [
            CIResult(name="tests", passed=False, details="Failed"),
        ]
        # Without config, CI failure forces NO_GO
        result = apply_policies(base_output, base_input)
        assert result.decision == Decision.NO_GO

        # With ci_failures disabled, decision stays GO
        config_file = tmp_path / "policy.yaml"
        config_file.write_text(
            "rules:\n"
            "  rule_ci_failures:\n"
            "    enabled: false\n"
        )
        result = apply_policies(base_output, base_input, config_path=config_file)
        assert result.decision == Decision.GO

    def test_config_falls_back_to_defaults(
        self, base_output: ReleaseOutput, base_input: ReleaseInput, tmp_path: Path
    ) -> None:
        """Rules not mentioned in config use default behavior."""
        base_output.risk_score = 0.8
        # Empty config file — all defaults apply
        config_file = tmp_path / "policy.yaml"
        config_file.write_text("rules: {}\n")
        result = apply_policies(base_output, base_input, config_path=config_file)
        assert result.decision == Decision.NO_GO

    def test_apply_policies_with_config_path(
        self, base_output: ReleaseOutput, base_input: ReleaseInput, tmp_path: Path
    ) -> None:
        """apply_policies integrates config_path end-to-end."""
        base_output.risk_score = 0.6
        base_input.files_changed = [
            FileChange(path="migrations/001.sql", additions=10, deletions=0),
        ]
        config_file = tmp_path / "policy.yaml"
        config_file.write_text(
            "rules:\n"
            "  rule_high_risk_threshold:\n"
            "    threshold: 0.5\n"
            "  rule_database_migration:\n"
            "    risk_adjustment: 0.05\n"
        )
        result = apply_policies(base_output, base_input, config_path=config_file)
        # high_risk_threshold with threshold=0.5 triggers on 0.6 → NO_GO
        assert result.decision == Decision.NO_GO
        # migration risk adjustment is 0.05 instead of default 0.15
        assert result.risk_score == pytest.approx(0.65)


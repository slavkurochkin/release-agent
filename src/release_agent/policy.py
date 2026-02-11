"""Deterministic policy engine for the release risk agent.

This module implements hard rules that override or augment the LLM's
probabilistic judgment. Some decisions should NEVER be left to an LLM:
- If CI tests failed → NO_GO (no exceptions)
- If risk score > 0.7 → NO_GO (deterministic threshold)
- If database migration without rollback plan → bump risk

Why a policy engine?
LLMs are probabilistic. They might say "GO" for a deploy with failing tests
because the prompt didn't emphasize it enough, or because the model got
confused. Policy rules provide a deterministic safety net.

Architecture:
- Each rule is a function that takes (ReleaseOutput, ReleaseInput) and
  returns an optional PolicyViolation
- Rules are registered in a list and executed in order
- Violations can adjust risk scores, force NO_GO, or add warnings
- The policy engine runs AFTER the LLM produces its assessment
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel

from release_agent.schemas import (
    Decision,
    ReleaseInput,
    ReleaseOutput,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Policy Types
# ---------------------------------------------------------------------------


class PolicyAction(StrEnum):
    """What action to take when a policy rule is violated.

    FORCE_NO_GO: Override decision to NO_GO regardless of LLM output
    ADJUST_RISK: Bump the risk score by a specified amount
    ADD_WARNING: Add a warning to recommended_actions but don't change decision
    """

    FORCE_NO_GO = "FORCE_NO_GO"
    ADJUST_RISK = "ADJUST_RISK"
    ADD_WARNING = "ADD_WARNING"


@dataclass
class PolicyViolation:
    """Result of a policy rule check that found a violation.

    Attributes:
        rule_name: Human-readable name of the rule that was violated
        action: What action to take
        reason: Why this rule was triggered
        risk_adjustment: How much to add to risk_score (for ADJUST_RISK)
    """

    rule_name: str
    action: PolicyAction
    reason: str
    risk_adjustment: float = 0.0


# ---------------------------------------------------------------------------
# Configurable Policy (YAML)
# ---------------------------------------------------------------------------


class RuleConfig(BaseModel):
    """Configuration for a single policy rule."""

    enabled: bool = True
    action: PolicyAction | None = None
    threshold: float | None = None
    risk_adjustment: float | None = None
    patterns: list[str] | None = None


class PolicyConfig(BaseModel):
    """Top-level configuration loaded from YAML."""

    rules: dict[str, RuleConfig] = {}


def load_policy_config(path: str | Path) -> PolicyConfig:
    """Load and validate a YAML policy config file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A validated PolicyConfig. Returns defaults if the file doesn't exist.

    Raises:
        ValueError: If the YAML content is invalid or fails validation.
    """
    config_path = Path(path)
    if not config_path.exists():
        return PolicyConfig()

    try:
        raw = yaml.safe_load(config_path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    try:
        return PolicyConfig.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"Invalid policy config in {path}: {exc}") from exc


# Type alias for policy rule functions
PolicyRule = Callable[[ReleaseOutput, ReleaseInput, RuleConfig | None], PolicyViolation | None]


# ---------------------------------------------------------------------------
# Policy Rules
# ---------------------------------------------------------------------------


def rule_ci_failures(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Any failed CI check forces NO_GO.

    Rationale: If automated tests fail, the release should not proceed.
    This is non-negotiable — the LLM should never override failing tests.
    """
    # TODO: Implement the CI failure rule.
    #
    # Steps:
    # 1. Check if any CI results have passed=False:
    #    failed_checks = [ci for ci in input_data.ci_results if not ci.passed]
    #
    # 2. If there are failures, return a PolicyViolation:
    #    if failed_checks:
    #        names = ", ".join(ci.name for ci in failed_checks)
    #        return PolicyViolation(
    #            rule_name="ci_failures",
    #            action=PolicyAction.FORCE_NO_GO,
    #            reason=f"CI checks failed: {names}",
    #        )
    #
    # 3. If all passed, return None (no violation)
    #    return None
    failed_checks = [ci for ci in input_data.ci_results if not ci.passed]

    if failed_checks:
            names = ", ".join(ci.name for ci in failed_checks)
            return PolicyViolation(
                rule_name="ci_failures",
                action=PolicyAction.FORCE_NO_GO,
                reason=f"CI checks failed: {names}",
            )

    return None


def rule_high_risk_threshold(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Risk score above threshold forces NO_GO.

    Rationale: Even if the LLM says "GO" with a high risk score, we enforce
    a deterministic threshold. This catches cases where the LLM is
    inconsistent between its score and its decision.
    """
    threshold = config.threshold if config and config.threshold is not None else 0.7
    if output.risk_score > threshold:
        return PolicyViolation(
            rule_name="high_risk_threshold",
            action=PolicyAction.FORCE_NO_GO,
            reason=f"Risk score {output.risk_score} exceeds threshold of {threshold}",
        )

    return None


def rule_database_migration(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Database migration files bump risk score.

    Rationale: Database migrations are inherently risky because they're
    hard to roll back. If we detect migration files, we increase the
    risk score to ensure the LLM (and humans) pay attention.
    """
    default_patterns = ["migration", "alembic", "flyway", "liquibase"]
    patterns = config.patterns if config and config.patterns is not None else default_patterns
    risk_adj = config.risk_adjustment if config and config.risk_adjustment is not None else 0.15

    migration_files = [
        f for f in input_data.files_changed
        if any(pattern in f.path.lower() for pattern in patterns)
    ]

    if migration_files:
        paths = ", ".join(f.path for f in migration_files)
        return PolicyViolation(
            rule_name="database_migration",
            action=PolicyAction.ADJUST_RISK,
            reason=f"Database migration files detected: {paths}",
            risk_adjustment=risk_adj,
        )
    return None


def rule_auth_changes(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Changes to authentication/authorization code bump risk.

    Rationale: Auth code is security-critical. Changes here have outsized
    blast radius because they affect every user and every request.
    """
    default_patterns = ["auth", "login", "session", "token", "oauth",
                        "permission", "rbac", "acl"]
    patterns = config.patterns if config and config.patterns is not None else default_patterns
    risk_adj = config.risk_adjustment if config and config.risk_adjustment is not None else 0.1

    auth_files = [
        f for f in input_data.files_changed
        if any(pattern in f.path.lower() for pattern in patterns)
    ]

    if auth_files:
        paths = ", ".join(f.path for f in auth_files)
        return PolicyViolation(
            rule_name="auth_changes",
            action=PolicyAction.ADJUST_RISK,
            reason=f"Auth changes detected: {paths}",
            risk_adjustment=risk_adj,
        )

    return None


def rule_deploy_during_incident(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Deploying during active incidents adds a warning.

    Rationale: If the team is dealing with a production incident, adding
    more changes to production increases cognitive load and risk. We don't
    force NO_GO (the incident might be unrelated), but we flag it.
    """
    # TODO: Implement the incident-aware deploy rule.
    #
    # Steps:
    # 1. Check if there are recent incidents:
    #    if input_data.recent_incidents:
    #        return PolicyViolation(
    #            rule_name="deploy_during_incident",
    #            action=PolicyAction.ADD_WARNING,
    #            reason=f"There are {len(input_data.recent_incidents)} recent "
    #                   f"incidents. Consider delaying this deploy.",
    #        )
    #
    # 2. Return None if no incidents
    if input_data.recent_incidents:
        return PolicyViolation(
            rule_name="deploy_during_incident",
            action=PolicyAction.ADD_WARNING,
            reason=f"There are {len(input_data.recent_incidents)} recent "
                    f"incidents. Consider delaying this deploy.",
        )

    return None


def rule_large_pr(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Large PRs (>threshold lines changed) bump risk score.

    Rationale: Large changes are harder to review thoroughly and have
    more surface area for bugs. Studies show defect density increases
    with change size.
    """
    threshold = config.threshold if config and config.threshold is not None else 500
    risk_adj = config.risk_adjustment if config and config.risk_adjustment is not None else 0.1

    total_lines = sum(
        f.additions + f.deletions for f in input_data.files_changed
    )
    if total_lines > threshold:
        return PolicyViolation(
            rule_name="large_pr",
            action=PolicyAction.ADJUST_RISK,
            reason=f"PR changes {total_lines} lines (threshold: {int(threshold)})",
            risk_adjustment=risk_adj,
        )
    return None

def rule_no_tests(
    output: ReleaseOutput, input_data: ReleaseInput, config: RuleConfig | None = None
) -> PolicyViolation | None:
    """RULE: Source changes without test changes trigger a warning.

    Rationale: If you change source code but not tests, either the
    existing tests already cover the change (great) or you forgot to
    add tests (not great). Either way, a human should verify.
    """
    paths = [f.path for f in input_data.files_changed]
    has_source_changes = any(
        p.startswith("src/") or p.startswith("lib/") or p.startswith("app/")
        for p in paths
    )
    has_test_changes = any(
        "test" in p.lower() for p in paths
    )
    if has_source_changes and not has_test_changes:
        return PolicyViolation(
            rule_name="no_tests",
            action=PolicyAction.ADD_WARNING,
            reason="Source files were changed but no test files were modified. "
                   "Verify that existing tests cover the changes.",
        )
    return None


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

# Default rules applied in order
DEFAULT_RULES: list[PolicyRule] = [
    rule_ci_failures,
    rule_high_risk_threshold,
    rule_database_migration,
    rule_auth_changes,
    rule_deploy_during_incident,
    rule_large_pr,
]


def apply_policies(
    output: ReleaseOutput,
    input_data: ReleaseInput,
    rules: list[PolicyRule] | None = None,
    config_path: str | Path | None = None,
) -> ReleaseOutput:
    """Apply all policy rules to the LLM's output and return the adjusted result.

    This is the main entry point for the policy engine. It:
    1. Runs each rule against the output and input
    2. Collects violations
    3. Adjusts the output based on violations (risk score, decision, warnings)
    4. Returns the modified output

    The output is modified in place (well, a copy is made). The original
    ReleaseOutput from the LLM is never mutated.

    Args:
        output: The LLM's risk assessment output
        input_data: The original release input (for context in rules)
        rules: List of policy rules to apply. Uses DEFAULT_RULES if None.
        config_path: Optional path to a YAML config file for rule overrides.

    Returns:
        A potentially modified ReleaseOutput with policy adjustments applied
    """

    # 1. Use the default rules if none provided:
    rules = rules or DEFAULT_RULES

    # Load config if a path was provided
    policy_config = load_policy_config(config_path) if config_path else PolicyConfig()

    # 2. Make a mutable copy of the output:
    data = output.model_dump()

    # 3. Collect all violations:
    violations = []
    for rule in rules:
        rule_name = rule.__name__
        rule_cfg = policy_config.rules.get(rule_name)

        # Skip disabled rules
        if rule_cfg and not rule_cfg.enabled:
            continue

        violation = rule(output, input_data, rule_cfg)
        if violation is not None:
            violations.append(violation)

    # 4. Apply each violation:
    for v in violations:
        if v.action == PolicyAction.FORCE_NO_GO:
            data["decision"] = Decision.NO_GO
            data["risk_factors"].append({
                "category": "policy",
                "description": f"[POLICY: {v.rule_name}] {v.reason}",
                "severity": RiskLevel.CRITICAL,
            })

        elif v.action == PolicyAction.ADJUST_RISK:
            data["risk_score"] = min(1.0, data["risk_score"] + v.risk_adjustment)
            data["risk_factors"].append({
                "category": "policy",
                "description": f"[POLICY: {v.rule_name}] {v.reason}",
                "severity": RiskLevel.HIGH,
            })

        elif v.action == PolicyAction.ADD_WARNING:
            data["recommended_actions"].append(
                f"[POLICY: {v.rule_name}] {v.reason}"
            )

    # 5. Recalculate risk_level based on adjusted risk_score:
    score = data["risk_score"]
    if score <= 0.3:
        data["risk_level"] = RiskLevel.LOW
    elif score <= 0.5:
        data["risk_level"] = RiskLevel.MEDIUM
    elif score <= 0.7:
        data["risk_level"] = RiskLevel.HIGH
    else:
        data["risk_level"] = RiskLevel.CRITICAL

    # Ensure NO_GO decisions have at least HIGH risk_level
    if data["decision"] == Decision.NO_GO and data["risk_level"] not in (
        RiskLevel.HIGH, RiskLevel.CRITICAL
    ):
        data["risk_level"] = RiskLevel.HIGH

    # 6. Return the adjusted output:
    return ReleaseOutput.model_validate(data)

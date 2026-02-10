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

from release_agent.schemas import (
    ReleaseInput,
    ReleaseOutput,
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


# Type alias for policy rule functions
PolicyRule = Callable[[ReleaseOutput, ReleaseInput], PolicyViolation | None]


# ---------------------------------------------------------------------------
# Policy Rules
# ---------------------------------------------------------------------------


def rule_ci_failures(output: ReleaseOutput, input_data: ReleaseInput) -> PolicyViolation | None:
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
    raise NotImplementedError("TODO: Implement CI failure rule")


def rule_high_risk_threshold(
    output: ReleaseOutput, input_data: ReleaseInput
) -> PolicyViolation | None:
    """RULE: Risk score above 0.7 forces NO_GO.

    Rationale: Even if the LLM says "GO" with a high risk score, we enforce
    a deterministic threshold. This catches cases where the LLM is
    inconsistent between its score and its decision.
    """
    # TODO: Implement the high risk threshold rule.
    #
    # Steps:
    # 1. Check if risk_score > 0.7:
    #    if output.risk_score > 0.7:
    #        return PolicyViolation(
    #            rule_name="high_risk_threshold",
    #            action=PolicyAction.FORCE_NO_GO,
    #            reason=f"Risk score {output.risk_score} exceeds threshold of 0.7",
    #        )
    #
    # 2. Return None if within threshold
    raise NotImplementedError("TODO: Implement high risk threshold rule")


def rule_database_migration(
    output: ReleaseOutput, input_data: ReleaseInput
) -> PolicyViolation | None:
    """RULE: Database migration files bump risk score.

    Rationale: Database migrations are inherently risky because they're
    hard to roll back. If we detect migration files, we increase the
    risk score to ensure the LLM (and humans) pay attention.
    """
    # TODO: Implement the database migration rule.
    #
    # Steps:
    # 1. Define migration file patterns to look for:
    #    migration_patterns = ["migration", "alembic", "flyway", "liquibase"]
    #
    # 2. Check if any changed files match:
    #    migration_files = [
    #        f for f in input_data.files_changed
    #        if any(pattern in f.path.lower() for pattern in migration_patterns)
    #    ]
    #
    # 3. If found, return a risk adjustment:
    #    if migration_files:
    #        paths = ", ".join(f.path for f in migration_files)
    #        return PolicyViolation(
    #            rule_name="database_migration",
    #            action=PolicyAction.ADJUST_RISK,
    #            reason=f"Database migration files detected: {paths}",
    #            risk_adjustment=0.15,
    #        )
    #
    # 4. Return None if no migrations found
    raise NotImplementedError("TODO: Implement database migration rule")


def rule_auth_changes(
    output: ReleaseOutput, input_data: ReleaseInput
) -> PolicyViolation | None:
    """RULE: Changes to authentication/authorization code bump risk.

    Rationale: Auth code is security-critical. Changes here have outsized
    blast radius because they affect every user and every request.
    """
    # TODO: Implement the auth changes rule.
    #
    # Steps:
    # 1. Define auth-related file patterns:
    #    auth_patterns = ["auth", "login", "session", "token", "oauth",
    #                     "permission", "rbac", "acl"]
    #
    # 2. Check if any changed files match
    # 3. If found, return ADJUST_RISK with +0.1
    # 4. Return None if no auth files changed
    raise NotImplementedError("TODO: Implement auth changes rule")


def rule_deploy_during_incident(
    output: ReleaseOutput, input_data: ReleaseInput
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
    raise NotImplementedError("TODO: Implement incident-aware deploy rule")


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
]


def apply_policies(
    output: ReleaseOutput,
    input_data: ReleaseInput,
    rules: list[PolicyRule] | None = None,
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

    Returns:
        A potentially modified ReleaseOutput with policy adjustments applied
    """
    # TODO: Implement the policy engine.
    #
    # Steps:
    # 1. Use the default rules if none provided:
    #    rules = rules or DEFAULT_RULES
    #
    # 2. Make a mutable copy of the output:
    #    data = output.model_dump()
    #
    # 3. Collect all violations:
    #    violations = []
    #    for rule in rules:
    #        violation = rule(output, input_data)
    #        if violation is not None:
    #            violations.append(violation)
    #
    # 4. Apply each violation:
    #    for v in violations:
    #        if v.action == PolicyAction.FORCE_NO_GO:
    #            data["decision"] = Decision.NO_GO
    #            data["risk_factors"].append({
    #                "category": "policy",
    #                "description": f"[POLICY: {v.rule_name}] {v.reason}",
    #                "severity": RiskLevel.CRITICAL,
    #            })
    #
    #        elif v.action == PolicyAction.ADJUST_RISK:
    #            data["risk_score"] = min(1.0, data["risk_score"] + v.risk_adjustment)
    #            data["risk_factors"].append({
    #                "category": "policy",
    #                "description": f"[POLICY: {v.rule_name}] {v.reason}",
    #                "severity": RiskLevel.HIGH,
    #            })
    #
    #        elif v.action == PolicyAction.ADD_WARNING:
    #            data["recommended_actions"].append(
    #                f"[POLICY: {v.rule_name}] {v.reason}"
    #            )
    #
    # 5. Recalculate risk_level based on adjusted risk_score:
    #    score = data["risk_score"]
    #    if score <= 0.3:
    #        data["risk_level"] = RiskLevel.LOW
    #    elif score <= 0.5:
    #        data["risk_level"] = RiskLevel.MEDIUM
    #    elif score <= 0.7:
    #        data["risk_level"] = RiskLevel.HIGH
    #    else:
    #        data["risk_level"] = RiskLevel.CRITICAL
    #
    # 6. Return the adjusted output:
    #    return ReleaseOutput.model_validate(data)
    raise NotImplementedError("TODO: Implement policy engine")

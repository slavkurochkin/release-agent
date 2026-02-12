"""Functional evaluations — deterministic checks on agent output.

Functional evals verify that the agent's output meets hard requirements:
- Schema compliance (all required fields present, correct types)
- Field constraints (risk_score in [0, 1], decision is GO/NO_GO)
- Logical consistency (NO_GO should have HIGH/CRITICAL risk level)
- Decision agreement (does agent's decision match the gold example)

These are the simplest and most reliable evals. If functional evals fail,
there's a clear bug — no judgment call needed.

Think of these as "unit tests for agent output."
"""

from __future__ import annotations

from release_agent.evals.runner import EvalResult
from release_agent.schemas import Decision, ReleaseOutput, RiskLevel


def run_functional_evals(
    actual: ReleaseOutput,
    expected: ReleaseOutput,
    example_id: str,
) -> list[EvalResult]:
    """Run all functional evals on an agent output.

    Args:
        actual: The agent's actual output
        expected: The expected (gold) output
        example_id: Identifier for the gold example

    Returns:
        List of EvalResult objects, one per check
    """

    results = []
    results.append(check_schema_compliance(actual, example_id))
    results.append(check_decision_match(actual, expected, example_id))
    results.append(check_risk_score_range(actual, example_id))
    results.append(check_risk_level_consistency(actual, example_id))
    results.append(check_explanation_present(actual, example_id))
    return results


def check_schema_compliance(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that the output has all required fields with correct types.

    Since we use Pydantic, if we got a ReleaseOutput object it already
    passed basic validation. This check verifies semantic constraints
    beyond what Pydantic checks (e.g., explanation length, non-empty factors).
    """
    failures: list[str] = []

    if len(actual.summary) < 10:
        failures.append(f"summary too short ({len(actual.summary)} chars, need >= 10)")

    if len(actual.explanation) < 20:
        failures.append(f"explanation too short ({len(actual.explanation)} chars, need >= 20)")

    if not actual.risk_factors:
        failures.append("risk_factors is empty")

    if actual.decision == Decision.NO_GO and not actual.recommended_actions:
        failures.append("NO_GO decision but recommended_actions is empty")

    passed = len(failures) == 0
    details = "All schema checks passed" if passed else "; ".join(failures)

    return EvalResult(
        eval_type="functional",
        eval_name="schema_compliance",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
        example_id=example_id,
    )


def check_decision_match(
    actual: ReleaseOutput, expected: ReleaseOutput, example_id: str
) -> EvalResult:
    """Check that the agent's GO/NO_GO decision matches the expected one.

    This is the most important functional eval. A wrong decision means
    either a dangerous release was approved or a safe release was blocked.
    """
    passed = actual.decision == expected.decision

    if passed:
        details = f"Decision matches: {actual.decision}"
    else:
        details = (
            f"Decision mismatch: got {actual.decision}, expected {expected.decision}"
        )

    return EvalResult(
        eval_type="functional",
        eval_name="decision_match",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
        example_id=example_id,
    )


def check_risk_score_range(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that risk_score is within [0.0, 1.0].

    Pydantic enforces this via Field(ge=0.0, le=1.0), but this eval
    serves as documentation and catches edge cases.
    """
    passed = 0.0 <= actual.risk_score <= 1.0

    if passed:
        details = f"risk_score {actual.risk_score} is within [0.0, 1.0]"
    else:
        details = f"risk_score {actual.risk_score} is out of range [0.0, 1.0]"

    return EvalResult(
        eval_type="functional",
        eval_name="risk_score_range",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
        example_id=example_id,
    )


def check_risk_level_consistency(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that risk_level is consistent with risk_score.

    Expected mapping:
    - 0.0-0.3 → LOW
    - 0.3-0.5 → MEDIUM
    - 0.5-0.7 → HIGH
    - 0.7-1.0 → CRITICAL

    We allow some flexibility (±0.05) since the boundaries aren't strict.
    """
    tolerance = 0.05
    score = actual.risk_score

    # Determine which risk levels are acceptable at this score (with tolerance)
    acceptable: set[RiskLevel] = set()
    if score <= 0.3 + tolerance:
        acceptable.add(RiskLevel.LOW)
    if 0.3 - tolerance <= score <= 0.5 + tolerance:
        acceptable.add(RiskLevel.MEDIUM)
    if 0.5 - tolerance <= score <= 0.7 + tolerance:
        acceptable.add(RiskLevel.HIGH)
    if score >= 0.7 - tolerance:
        acceptable.add(RiskLevel.CRITICAL)

    passed = actual.risk_level in acceptable

    if passed:
        details = f"risk_level {actual.risk_level} is consistent with risk_score {score}"
    else:
        details = (
            f"risk_level {actual.risk_level} is inconsistent with risk_score {score} "
            f"(expected one of: {', '.join(sorted(acceptable))})"
        )

    return EvalResult(
        eval_type="functional",
        eval_name="risk_level_consistency",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
        example_id=example_id,
    )


def check_explanation_present(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that the explanation is substantive, not just filler text.

    A good explanation should:
    - Be at least 50 characters
    - Reference specific aspects of the release
    - Not be generic boilerplate
    """
    failures: list[str] = []

    if len(actual.explanation) < 50:
        failures.append(
            f"explanation too short ({len(actual.explanation)} chars, need >= 50)"
        )

    words = actual.explanation.split()
    unique_words = set(w.lower() for w in words)
    if len(words) >= 5 and len(unique_words) <= 2:
        failures.append("explanation appears to be repeated filler text")

    has_specifics = any(c.isdigit() for c in actual.explanation) or any(
        marker in actual.explanation for marker in ["/", ".", "_", "#"]
    )
    if not has_specifics:
        failures.append(
            "explanation lacks specific details (no numbers, file paths, or references)"
        )

    passed = len(failures) == 0
    details = "Explanation is substantive" if passed else "; ".join(failures)

    return EvalResult(
        eval_type="functional",
        eval_name="explanation_present",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
        example_id=example_id,
    )

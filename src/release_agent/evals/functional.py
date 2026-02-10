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
from release_agent.schemas import ReleaseOutput


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
    # TODO: Implement by calling each functional eval and collecting results.
    #
    # results = []
    # results.append(check_schema_compliance(actual, example_id))
    # results.append(check_decision_match(actual, expected, example_id))
    # results.append(check_risk_score_range(actual, example_id))
    # results.append(check_risk_level_consistency(actual, example_id))
    # results.append(check_explanation_present(actual, example_id))
    # return results
    raise NotImplementedError("TODO: Implement functional eval runner")


def check_schema_compliance(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that the output has all required fields with correct types.

    Since we use Pydantic, if we got a ReleaseOutput object it already
    passed basic validation. This check verifies semantic constraints
    beyond what Pydantic checks (e.g., explanation length, non-empty factors).
    """
    # TODO: Implement schema compliance check.
    #
    # Things to verify:
    # 1. summary is at least 10 characters
    # 2. explanation is at least 20 characters
    # 3. risk_factors is not empty
    # 4. If decision is NO_GO, recommended_actions should not be empty
    #
    # Return EvalResult(
    #     eval_type="functional",
    #     eval_name="schema_compliance",
    #     passed=all_checks_pass,
    #     details="...",
    #     example_id=example_id,
    # )
    raise NotImplementedError("TODO: Implement schema compliance check")


def check_decision_match(
    actual: ReleaseOutput, expected: ReleaseOutput, example_id: str
) -> EvalResult:
    """Check that the agent's GO/NO_GO decision matches the expected one.

    This is the most important functional eval. A wrong decision means
    either a dangerous release was approved or a safe release was blocked.
    """
    # TODO: Implement decision match check.
    #
    # passed = actual.decision == expected.decision
    # Return EvalResult with pass/fail and details about the mismatch
    raise NotImplementedError("TODO: Implement decision match check")


def check_risk_score_range(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that risk_score is within [0.0, 1.0].

    Pydantic enforces this via Field(ge=0.0, le=1.0), but this eval
    serves as documentation and catches edge cases.
    """
    # TODO: Implement risk score range check.
    #
    # passed = 0.0 <= actual.risk_score <= 1.0
    raise NotImplementedError("TODO: Implement risk score range check")


def check_risk_level_consistency(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that risk_level is consistent with risk_score.

    Expected mapping:
    - 0.0-0.3 → LOW
    - 0.3-0.5 → MEDIUM
    - 0.5-0.7 → HIGH
    - 0.7-1.0 → CRITICAL

    We allow some flexibility (±0.05) since the boundaries aren't strict.
    """
    # TODO: Implement risk level consistency check.
    #
    # Steps:
    # 1. Determine expected risk_level from risk_score
    # 2. Check if actual.risk_level matches (with tolerance)
    # 3. Return EvalResult
    raise NotImplementedError("TODO: Implement risk level consistency check")


def check_explanation_present(actual: ReleaseOutput, example_id: str) -> EvalResult:
    """Check that the explanation is substantive, not just filler text.

    A good explanation should:
    - Be at least 50 characters
    - Reference specific aspects of the release
    - Not be generic boilerplate
    """
    # TODO: Implement explanation quality check.
    #
    # Basic checks:
    # 1. len(actual.explanation) >= 50
    # 2. Not all the same word repeated
    # 3. Contains at least some specific details (numbers, file paths, etc.)
    raise NotImplementedError("TODO: Implement explanation check")

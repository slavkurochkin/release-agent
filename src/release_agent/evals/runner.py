"""Eval runner — orchestrates all evaluation types and reports results.

This module is the entry point for running evaluations. It:
- Loads gold examples from fixtures
- Runs the agent against each example
- Executes all eval types (functional, semantic, judge, adversarial)
- Collects results and computes aggregate metrics
- Outputs a structured report

Metrics tracked:
- pass@k: What fraction of examples pass all evals after k runs
- false_go_rate: How often the agent says GO when the gold answer is NO_GO
- false_nogo_rate: How often the agent says NO_GO when the gold answer is GO
- schema_compliance: What fraction of outputs have valid schema
- explanation_quality: Average semantic similarity score for explanations

Usage:
    python -m release_agent.evals.runner --examples tests/fixtures/gold_examples.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from release_agent.agent import ReleaseRiskAgent
from release_agent.schemas import Decision, ReleaseInput, ReleaseOutput

# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Result of a single eval check on a single example.

    Attributes:
        eval_type: Category of eval (functional, semantic, judge, adversarial)
        eval_name: Specific eval check name
        passed: Whether the check passed
        score: Numeric score (0.0-1.0) if applicable
        details: Human-readable details about what was checked
        example_id: Which gold example this was run against
    """

    eval_type: str
    eval_name: str
    passed: bool
    score: float = 0.0
    details: str = ""
    example_id: str = ""


@dataclass
class EvalReport:
    """Aggregate results from an eval run.

    Attributes:
        timestamp: When the eval was run
        total_examples: Number of gold examples tested
        total_checks: Total number of individual eval checks
        passed_checks: Number of checks that passed
        failed_checks: Number of checks that failed
        pass_rate: Overall pass rate (passed/total)
        false_go_rate: Rate of incorrect GO decisions
        false_nogo_rate: Rate of incorrect NO_GO decisions
        avg_explanation_quality: Average explanation quality score
        results: All individual eval results
        metadata: Additional context (model version, etc.)
    """

    timestamp: str = ""
    total_examples: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    pass_rate: float = 0.0
    pass_at_k: float = 0.0
    k: int = 1
    false_go_rate: float = 0.0
    false_nogo_rate: float = 0.0
    avg_explanation_quality: float = 0.0
    results: list[EvalResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Gold Example Loader
# ---------------------------------------------------------------------------


def load_gold_examples(path: str | Path) -> list[dict[str, Any]]:
    """Load gold examples from a JSON file.

    Each gold example has:
    - "input": ReleaseInput data
    - "expected_output": Expected ReleaseOutput data
    - "id": Unique identifier
    - "description": What this example tests

    Args:
        path: Path to the gold examples JSON file

    Returns:
        List of gold example dicts
    """
    with open(path) as f:
        examples = json.load(f)

    for i, ex in enumerate(examples):
        if "input" not in ex:
            raise ValueError(f"Example {i} missing 'input'")
        if "expected_output" not in ex:
            raise ValueError(f"Example {i} missing 'expected_output'")
        if "id" not in ex:
            ex["id"] = f"example_{i}"

    return examples


# ---------------------------------------------------------------------------
# Eval Runner
# ---------------------------------------------------------------------------


class EvalRunner:
    """Orchestrates running all evaluations.

    Usage:
        runner = EvalRunner(agent=ReleaseRiskAgent())
        report = await runner.run_all(examples_path="tests/fixtures/gold_examples.json")
        runner.save_report(report, "eval_results/report.json")
    """

    def __init__(self, agent: ReleaseRiskAgent | None = None) -> None:
        """Initialize the eval runner.

        Args:
            agent: The agent to evaluate. Creates a default one if None.
        """
        self.agent = agent or ReleaseRiskAgent()

    async def run_all(
        self,
        examples_path: str | Path = "tests/fixtures/gold_examples.json",
        k: int = 1,
    ) -> EvalReport:
        """Run all evaluations against all gold examples.

        This is the main method. It:
        1. Loads gold examples
        2. Runs the agent against each example (up to k times for pass@k)
        3. Runs all eval types against each (input, output, expected) triple
        4. Computes aggregate metrics
        5. Returns the report

        Args:
            examples_path: Path to gold examples JSON file
            k: Number of attempts per example for pass@k. An example
               passes if ALL checks pass in at least one of the k runs.

        Returns:
            An EvalReport with all results and aggregate metrics
        """
        from release_agent.evals.adversarial import run_adversarial_evals
        from release_agent.evals.functional import run_functional_evals
        from release_agent.evals.semantic import run_semantic_evals

        examples = load_gold_examples(examples_path)

        all_results: list[EvalResult] = []
        false_go = 0
        false_nogo = 0
        total_decisions = 0
        examples_passed = 0

        for example in examples:
            example_id = example["id"]
            input_data = ReleaseInput.model_validate(example["input"])
            expected = ReleaseOutput.model_validate(example["expected_output"])

            example_passed = False

            for run_idx in range(k):
                try:
                    actual = await self.agent.assess(input_data)
                except Exception as e:
                    all_results.append(
                        EvalResult(
                            eval_type="runtime",
                            eval_name="agent_execution",
                            passed=False,
                            details=f"Agent raised (run {run_idx + 1}/{k}): {e}",
                            example_id=example_id,
                        )
                    )
                    continue

                # Track decision accuracy (only on the first run)
                if run_idx == 0:
                    total_decisions += 1
                    if (
                        actual.decision == Decision.GO
                        and expected.decision == Decision.NO_GO
                    ):
                        false_go += 1
                    elif (
                        actual.decision == Decision.NO_GO
                        and expected.decision == Decision.GO
                    ):
                        false_nogo += 1

                # Functional evals
                run_results = list(
                    run_functional_evals(actual, expected, example_id)
                )

                # Semantic evals
                try:
                    sem_results = await run_semantic_evals(
                        actual, expected, example_id
                    )
                    run_results.extend(sem_results)
                except Exception as e:
                    run_results.append(
                        EvalResult(
                            eval_type="semantic",
                            eval_name="semantic_eval_error",
                            passed=False,
                            details=f"Semantic evals failed: {e}",
                            example_id=example_id,
                        )
                    )

                all_results.extend(run_results)

                if all(r.passed for r in run_results):
                    example_passed = True
                    break  # No need to run more times

            examples_passed += int(example_passed)

        # Adversarial evals
        try:
            adv_results = await run_adversarial_evals(self.agent)
            all_results.extend(adv_results)
        except Exception as e:
            all_results.append(
                EvalResult(
                    eval_type="adversarial",
                    eval_name="adversarial_eval_error",
                    passed=False,
                    details=f"Adversarial evals failed: {e}",
                )
            )

        # Compute aggregate metrics
        passed_checks = sum(1 for r in all_results if r.passed)
        failed_checks = sum(1 for r in all_results if not r.passed)
        total_checks = len(all_results)
        pass_rate = passed_checks / total_checks if total_checks > 0 else 0.0

        pass_at_k = examples_passed / len(examples) if examples else 0.0

        false_go_rate = false_go / total_decisions if total_decisions > 0 else 0.0
        false_nogo_rate = false_nogo / total_decisions if total_decisions > 0 else 0.0

        semantic_scores = [
            r.score for r in all_results if r.eval_type == "semantic" and r.score > 0
        ]
        avg_explanation_quality = (
            sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0
        )

        return EvalReport(
            timestamp=datetime.now(UTC).isoformat(),
            total_examples=len(examples),
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            pass_rate=pass_rate,
            pass_at_k=pass_at_k,
            k=k,
            false_go_rate=false_go_rate,
            false_nogo_rate=false_nogo_rate,
            avg_explanation_quality=avg_explanation_quality,
            results=all_results,
            metadata={"examples_path": str(examples_path), "k": k},
        )

    def save_report(self, report: EvalReport, path: str | Path) -> None:
        """Save an eval report to a JSON file.

        Args:
            report: The eval report to save
            path: Output file path
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(report)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for running evals.

    Usage:
        python -m release_agent.evals.runner \\
            --examples tests/fixtures/gold_examples.json \\
            --output eval_results/report.json
    """
    parser = argparse.ArgumentParser(description="Run release agent evaluations")
    parser.add_argument(
        "--examples",
        default="tests/fixtures/gold_examples.json",
        help="Path to gold examples JSON file",
    )
    parser.add_argument(
        "--output",
        default="eval_results/report.json",
        help="Path to save the eval report",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "-k",
        type=int,
        default=1,
        help="Number of attempts per example for pass@k (default: 1)",
    )
    args = parser.parse_args()

    import os

    from dotenv import load_dotenv

    load_dotenv()

    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OpenAI API key required.")
        print("  Set OPENAI_API_KEY environment variable:")
        print("    export OPENAI_API_KEY=sk-...")
        print("  Or pass --api-key:")
        print("    python -m release_agent.evals.runner --api-key sk-...")
        raise SystemExit(1)

    runner = EvalRunner()
    report = asyncio.run(runner.run_all(examples_path=args.examples, k=args.k))
    runner.save_report(report, args.output)

    print(f"Eval Report — {report.timestamp}")
    print(f"  Examples:  {report.total_examples}")
    print(f"  Checks:    {report.total_checks}")
    print(f"  Passed:    {report.passed_checks}")
    print(f"  Failed:    {report.failed_checks}")
    print(f"  Pass rate: {report.pass_rate:.1%}")
    print(f"  Pass@{report.k}:   {report.pass_at_k:.1%}")
    print(f"  False GO:  {report.false_go_rate:.1%}")
    print(f"  False NO_GO: {report.false_nogo_rate:.1%}")
    print(f"  Avg explanation quality: {report.avg_explanation_quality:.3f}")
    print(f"  Report saved to: {args.output}")


if __name__ == "__main__":
    main()

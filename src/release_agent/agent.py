"""Core agent orchestrator for the release risk assessment.

This module ties together all the components:
- Prompt building (prompts/assess_risk.py)
- LLM interaction (llm.py)
- Policy enforcement (policy.py, Phase 4)
- Context building (context/, Phase 3)

The agent follows this flow:
1. Receive release data (ReleaseInput)
2. Build prompts from the data
3. Call the LLM for risk assessment
4. Apply policy rules to adjust/override the LLM output
5. Return the final assessment (ReleaseOutput)

This is the main entry point for the agent, whether called from the API
(Phase 2), CLI (Phase 1), or evaluation framework (Phase 5).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from release_agent.llm import LLMClient, LLMConfig
from release_agent.logging_config import get_logger
from release_agent.policy import apply_policies
from release_agent.prompts.assess_risk import build_system_prompt, build_user_prompt
from release_agent.schemas import ReleaseInput, ReleaseOutput

logger = get_logger(__name__)


class ReleaseRiskAgent:
    """Orchestrates the release risk assessment pipeline.

    This is the central class that coordinates all components. It is
    designed to be stateless — each call to assess() is independent.

    Usage:
        agent = ReleaseRiskAgent()
        result = await agent.assess(release_input)
    """

    def __init__(
        self,
        llm_config: LLMConfig | None = None,
    ) -> None:
        """Initialize the agent with its dependencies.

        Args:
            llm_config: Configuration for the LLM client. Uses defaults if None.
        """
        # TODO: Initialize the agent's dependencies.
        #
        # Steps:
        # 1. Create an LLMClient instance with the provided config:
        #    self.llm = LLMClient(config=llm_config)
        #
        # 2. Store any other dependencies you might need.
        #    For now, just the LLM client. In Phase 4, you'll add
        #    the policy engine here too.
        self.llm = LLMClient(config=llm_config)

    async def assess(self, release: ReleaseInput) -> ReleaseOutput:
        """Run a full risk assessment on a release.

        This is the main method. It:
        1. Builds the prompts from the release data
        2. Calls the LLM
        3. (Phase 4) Applies policy rules
        4. Returns the validated result

        Args:
            release: The release data to assess

        Returns:
            A validated ReleaseOutput with the risk assessment

        Raises:
            ValueError: If the LLM returns invalid output after retries
        """
        logger.info(
            "assessment_started",
            repo=release.repo,
            pr_number=release.pr_number,
            author=release.author,
            files_count=len(release.files_changed),
        )
        try:
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(release)
            result = await self.llm.assess_risk(system_prompt, user_prompt)

            logger.info(
                "assessment_complete",
                repo=release.repo,
                pr_number=release.pr_number,
                decision=result.decision.value,
                risk_score=result.risk_score,
                risk_level=result.risk_level.value,
                risk_factors_count=len(result.risk_factors),
            )

            result = apply_policies(result, release)
            return result
        except Exception as e:
            logger.error(
                "assessment_failed",
                repo=release.repo,
                pr_number=release.pr_number,
                error=str(e),
                exc_info=True,
            )
            raise


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for running the agent from the command line.

    Usage:
        release-agent --input release_data.json
        cat release_data.json | release-agent

    This lets you test the agent locally without running the API server.
    """
    # TODO: Implement the CLI entry point.
    #
    # Steps:
    # 1. Set up argument parsing:
    parser = argparse.ArgumentParser(description="Release Risk Assessment Agent")
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Path to JSON file with release data (reads stdin if omitted)",
    )
    args = parser.parse_args()
    # 2. Read input data:
    if not args.input and sys.stdin.isatty():
      parser.print_usage()
      print("Provide --input FILE or pipe JSON via stdin.")
      return

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # 3. Parse into ReleaseInput:
    release = ReleaseInput.model_validate(data)
    #
    # 4. Create agent and run assessment:
    agent = ReleaseRiskAgent()
    result = asyncio.run(agent.assess(release))
    #
    # 5. Print the result as formatted JSON:
    print(result.model_dump_json(indent=2))



if __name__ == "__main__":
    main()

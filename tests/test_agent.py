"""Tests for the agent orchestrator (Phase 1).

These tests verify that the agent:
- Initializes correctly with dependencies
- Calls the LLM with properly formatted prompts
- Returns validated output
- Handles errors gracefully

Since the agent depends on the LLM (which costs money and is non-deterministic),
these tests use mocking to isolate the agent logic from the LLM.

Run with: pytest tests/test_agent.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from release_agent.agent import ReleaseRiskAgent, main
from release_agent.llm import LLMClient, LLMConfig
from release_agent.schemas import (
    Decision,
    ReleaseInput,
    ReleaseOutput,
    RiskFactor,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_input() -> ReleaseInput:
    """A sample ReleaseInput for testing."""
    return ReleaseInput(
        repo="myorg/api",
        pr_number=42,
        title="Add health check endpoint",
        description="Simple health check endpoint for load balancers",
        author="testuser",
        files_changed=[],
        ci_results=[],
        commit_messages=["Add /health endpoint"],
    )


@pytest.fixture
def sample_output() -> ReleaseOutput:
    """A sample ReleaseOutput that the mock LLM will return."""
    return ReleaseOutput(
        decision=Decision.GO,
        risk_level=RiskLevel.LOW,
        risk_score=0.1,
        risk_factors=[
            RiskFactor(
                category="scope",
                description="Small change with limited blast radius",
                severity=RiskLevel.LOW,
            )
        ],
        summary="Low-risk health check endpoint addition.",
        explanation="This PR adds a simple health check endpoint with no dependencies "
        "on business logic. The change is minimal and well-isolated.",
        conditions=[],
        recommended_actions=[],
    )


# ---------------------------------------------------------------------------
# Agent Initialization Tests
# ---------------------------------------------------------------------------


class TestAgentInit:
    """Tests for ReleaseRiskAgent initialization."""

    def test_agent_creates_with_defaults(self) -> None:
        """Agent should initialize with default config."""
        agent = ReleaseRiskAgent()
        # After TODO is implemented, this should have a real LLM client
        # For now, we just check it doesn't crash
        assert agent is not None

    def test_agent_creates_with_custom_config(self) -> None:
        """Agent should accept custom LLM config."""
        config = LLMConfig(model="gpt-4o-mini", temperature=0.0)
        agent = ReleaseRiskAgent(llm_config=config)
        assert agent is not None


# ---------------------------------------------------------------------------
# Agent Assessment Tests (with mocked LLM)
# ---------------------------------------------------------------------------


class TestAgentAssess:
    """Tests for the agent's assess() method.

    These tests mock the LLM client to test the agent's orchestration
    logic without making real API calls.
    """

    @pytest.mark.asyncio
    async def test_assess_returns_release_output(
        self, sample_input: ReleaseInput, sample_output: ReleaseOutput
    ) -> None:
        """assess() should return a ReleaseOutput instance.

        This test will pass once the agent TODO is implemented.
        It mocks the LLM to return a known good output.
        """
        agent = ReleaseRiskAgent()

        # Mock the LLM client
        mock_llm = AsyncMock(spec=LLMClient)
        mock_llm.assess_risk.return_value = sample_output
        agent.llm = mock_llm

        # This will raise NotImplementedError until the TODO is done
        with pytest.raises(NotImplementedError):
            result = await agent.assess(sample_input)
            # Once implemented, these assertions should hold:
            # assert isinstance(result, ReleaseOutput)
            # assert result.decision == Decision.GO
            # assert result.risk_score == 0.1

    @pytest.mark.asyncio
    async def test_assess_calls_llm_with_prompts(
        self, sample_input: ReleaseInput, sample_output: ReleaseOutput
    ) -> None:
        """assess() should call the LLM with system and user prompts.

        This test verifies the agent builds and passes prompts correctly.
        """
        agent = ReleaseRiskAgent()

        mock_llm = AsyncMock(spec=LLMClient)
        mock_llm.assess_risk.return_value = sample_output
        agent.llm = mock_llm

        with pytest.raises(NotImplementedError):
            await agent.assess(sample_input)
            # Once implemented:
            # mock_llm.assess_risk.assert_called_once()
            # args = mock_llm.assess_risk.call_args
            # assert "system" prompt contains risk assessment instructions
            # assert "user" prompt contains the release data


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the CLI entry point."""

    def test_main_prints_usage(self, capsys) -> None:
        """main() should print usage info when called without args."""
        main()
        captured = capsys.readouterr()
        assert "TODO" in captured.out or "Usage" in captured.out

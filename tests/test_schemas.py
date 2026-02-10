"""Tests for Pydantic schemas (Phase 1).

These tests verify that the input/output schemas:
- Accept valid data
- Reject invalid data
- Serialize/deserialize correctly
- Generate valid JSON schemas

Run with: pytest tests/test_schemas.py -v
"""

from __future__ import annotations

import json

import pytest

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
def sample_file_change() -> dict:
    """A valid FileChange dict."""
    return {
        "path": "src/main.py",
        "additions": 10,
        "deletions": 5,
        "patch": "@@ -1,5 +1,10 @@\n+new line",
    }


@pytest.fixture
def sample_ci_result() -> dict:
    """A valid CIResult dict."""
    return {
        "name": "unit-tests",
        "passed": True,
        "details": "All 42 tests passed",
    }


@pytest.fixture
def sample_release_input(sample_file_change: dict, sample_ci_result: dict) -> dict:
    """A valid ReleaseInput dict."""
    return {
        "repo": "myorg/backend-api",
        "pr_number": 123,
        "title": "Add user endpoint",
        "description": "Adds a new endpoint for user management",
        "author": "testuser",
        "files_changed": [sample_file_change],
        "ci_results": [sample_ci_result],
        "commit_messages": ["feat: add user endpoint"],
        "recent_incidents": [],
        "deployment_target": "production",
    }


@pytest.fixture
def sample_release_output() -> dict:
    """A valid ReleaseOutput dict."""
    return {
        "decision": "GO",
        "risk_level": "LOW",
        "risk_score": 0.2,
        "risk_factors": [
            {
                "category": "scope",
                "description": "Small change with good test coverage",
                "severity": "LOW",
            }
        ],
        "summary": "Low-risk change with good test coverage and all CI passing.",
        "explanation": "This is a small, well-tested change that adds a new endpoint. "
        "All CI checks pass and the blast radius is limited to the new endpoint.",
        "conditions": [],
        "recommended_actions": [],
    }


# ---------------------------------------------------------------------------
# FileChange Tests
# ---------------------------------------------------------------------------


class TestFileChange:
    """Tests for the FileChange model."""

    def test_valid_file_change(self, sample_file_change: dict) -> None:
        """FileChange accepts valid data."""
        fc = FileChange(**sample_file_change)
        assert fc.path == "src/main.py"
        assert fc.additions == 10
        assert fc.deletions == 5

    def test_file_change_defaults(self) -> None:
        """FileChange has sensible defaults for optional fields."""
        fc = FileChange(path="README.md")
        assert fc.additions == 0
        assert fc.deletions == 0
        assert fc.patch == ""

    def test_file_change_negative_additions_rejected(self) -> None:
        """FileChange rejects negative line counts."""
        with pytest.raises(Exception):
            FileChange(path="test.py", additions=-1)


# ---------------------------------------------------------------------------
# CIResult Tests
# ---------------------------------------------------------------------------


class TestCIResult:
    """Tests for the CIResult model."""

    def test_valid_ci_result(self, sample_ci_result: dict) -> None:
        """CIResult accepts valid data."""
        ci = CIResult(**sample_ci_result)
        assert ci.name == "unit-tests"
        assert ci.passed is True

    def test_ci_result_details_default(self) -> None:
        """CIResult defaults details to empty string."""
        ci = CIResult(name="lint", passed=True)
        assert ci.details == ""


# ---------------------------------------------------------------------------
# ReleaseInput Tests
# ---------------------------------------------------------------------------


class TestReleaseInput:
    """Tests for the ReleaseInput model."""

    def test_valid_release_input(self, sample_release_input: dict) -> None:
        """ReleaseInput accepts valid data."""
        ri = ReleaseInput(**sample_release_input)
        assert ri.repo == "myorg/backend-api"
        assert ri.pr_number == 123
        assert len(ri.files_changed) == 1
        assert len(ri.ci_results) == 1

    def test_release_input_requires_repo(self) -> None:
        """ReleaseInput requires repo field."""
        with pytest.raises(Exception):
            ReleaseInput(pr_number=1, title="test", author="user")

    def test_release_input_requires_positive_pr_number(self) -> None:
        """ReleaseInput requires pr_number > 0."""
        with pytest.raises(Exception):
            ReleaseInput(repo="org/repo", pr_number=0, title="test", author="user")

    def test_release_input_requires_title(self) -> None:
        """ReleaseInput requires non-empty title."""
        with pytest.raises(Exception):
            ReleaseInput(repo="org/repo", pr_number=1, title="", author="user")

    def test_release_input_empty_lists_default(self) -> None:
        """ReleaseInput defaults list fields to empty lists."""
        ri = ReleaseInput(
            repo="org/repo", pr_number=1, title="test", author="user"
        )
        assert ri.files_changed == []
        assert ri.ci_results == []
        assert ri.commit_messages == []
        assert ri.recent_incidents == []

    def test_release_input_deployment_target_default(self) -> None:
        """ReleaseInput defaults deployment_target to 'production'."""
        ri = ReleaseInput(
            repo="org/repo", pr_number=1, title="test", author="user"
        )
        assert ri.deployment_target == "production"

    def test_release_input_serialization_roundtrip(
        self, sample_release_input: dict
    ) -> None:
        """ReleaseInput serializes to JSON and back without data loss."""
        ri = ReleaseInput(**sample_release_input)
        json_str = ri.model_dump_json()
        ri2 = ReleaseInput.model_validate_json(json_str)
        assert ri == ri2

    def test_release_input_json_schema_generation(self) -> None:
        """ReleaseInput can generate a JSON schema."""
        schema = ReleaseInput.model_json_schema()
        assert "properties" in schema
        assert "repo" in schema["properties"]
        assert "pr_number" in schema["properties"]


# ---------------------------------------------------------------------------
# ReleaseOutput Tests
# ---------------------------------------------------------------------------


class TestReleaseOutput:
    """Tests for the ReleaseOutput model."""

    def test_valid_release_output(self, sample_release_output: dict) -> None:
        """ReleaseOutput accepts valid data."""
        ro = ReleaseOutput(**sample_release_output)
        assert ro.decision == Decision.GO
        assert ro.risk_level == RiskLevel.LOW
        assert ro.risk_score == 0.2

    def test_release_output_risk_score_bounds(self) -> None:
        """ReleaseOutput rejects risk_score outside [0, 1]."""
        base = {
            "decision": "GO",
            "risk_level": "LOW",
            "risk_factors": [],
            "summary": "Test summary for validation purposes.",
            "explanation": "This is a test explanation that is long enough to pass.",
        }
        with pytest.raises(Exception):
            ReleaseOutput(**{**base, "risk_score": 1.5})
        with pytest.raises(Exception):
            ReleaseOutput(**{**base, "risk_score": -0.1})

    def test_release_output_valid_enums(self) -> None:
        """ReleaseOutput only accepts valid enum values."""
        base = {
            "risk_score": 0.5,
            "risk_factors": [],
            "summary": "Test summary for validation purposes.",
            "explanation": "This is a test explanation that is long enough to pass.",
        }
        with pytest.raises(Exception):
            ReleaseOutput(**{**base, "decision": "MAYBE", "risk_level": "LOW"})
        with pytest.raises(Exception):
            ReleaseOutput(**{**base, "decision": "GO", "risk_level": "EXTREME"})

    def test_release_output_minimum_summary_length(self) -> None:
        """ReleaseOutput requires summary of at least 10 characters."""
        with pytest.raises(Exception):
            ReleaseOutput(
                decision="GO",
                risk_level="LOW",
                risk_score=0.1,
                summary="Short",
                explanation="This explanation is definitely long enough to pass validation.",
            )

    def test_release_output_serialization_roundtrip(
        self, sample_release_output: dict
    ) -> None:
        """ReleaseOutput serializes to JSON and back."""
        ro = ReleaseOutput(**sample_release_output)
        json_str = ro.model_dump_json()
        ro2 = ReleaseOutput.model_validate_json(json_str)
        assert ro == ro2

    def test_release_output_json_schema_generation(self) -> None:
        """ReleaseOutput can generate a JSON schema for LLM structured output."""
        schema = ReleaseOutput.model_json_schema()
        assert "properties" in schema
        assert "decision" in schema["properties"]
        assert "risk_score" in schema["properties"]


# ---------------------------------------------------------------------------
# Risk Factor Tests
# ---------------------------------------------------------------------------


class TestRiskFactor:
    """Tests for the RiskFactor model."""

    def test_valid_risk_factor(self) -> None:
        """RiskFactor accepts valid data."""
        rf = RiskFactor(
            category="database",
            description="Migration detected",
            severity=RiskLevel.HIGH,
        )
        assert rf.category == "database"
        assert rf.severity == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Gold Example Tests
# ---------------------------------------------------------------------------


class TestGoldExamples:
    """Tests that gold examples are valid and parseable."""

    def test_gold_examples_parse(self) -> None:
        """All gold examples should parse as valid ReleaseInput/ReleaseOutput."""
        with open("tests/fixtures/gold_examples.json") as f:
            examples = json.load(f)

        assert len(examples) >= 5, "Expected at least 5 gold examples"

        for example in examples:
            assert "id" in example, "Each example must have an id"
            assert "input" in example, f"Example {example['id']} missing input"
            assert "expected_output" in example, f"Example {example['id']} missing expected_output"

            # Validate input parses
            input_data = ReleaseInput.model_validate(example["input"])
            assert input_data.repo, f"Example {example['id']} has empty repo"

            # Validate output parses
            output_data = ReleaseOutput.model_validate(example["expected_output"])
            assert output_data.decision in (Decision.GO, Decision.NO_GO)

    def test_gold_examples_have_both_decisions(self) -> None:
        """Gold examples should include both GO and NO_GO cases."""
        with open("tests/fixtures/gold_examples.json") as f:
            examples = json.load(f)

        decisions = {
            ReleaseOutput.model_validate(ex["expected_output"]).decision
            for ex in examples
        }
        assert Decision.GO in decisions, "Need at least one GO example"
        assert Decision.NO_GO in decisions, "Need at least one NO_GO example"

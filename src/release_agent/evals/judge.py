"""LLM-as-judge evaluations — use a second model to grade the agent's output.

The LLM-as-judge pattern uses one LLM to evaluate another LLM's output.
This is powerful because:
- It can assess qualities that are hard to measure mechanically
  (reasoning quality, specificity, actionability)
- It scales better than human evaluation
- It catches subtle issues that functional evals miss

Risks and mitigations:
- **Bias**: The judge might favor certain styles. Mitigation: use a
  different model than the agent, randomize option order.
- **Consistency**: Same input might get different scores. Mitigation:
  use low temperature (0.0), run multiple times and average.
- **Sycophancy**: The judge might be too lenient. Mitigation: include
  explicit rubric with examples of each score level.

In this implementation, we use GPT-4 as the judge to grade our agent's
risk assessments on multiple dimensions.
"""

from __future__ import annotations

import json

from release_agent.evals.runner import EvalResult
from release_agent.llm import LLMClient, LLMConfig
from release_agent.schemas import ReleaseInput, ReleaseOutput


# ---------------------------------------------------------------------------
# Judge Prompt
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of release risk assessments.
You will be given:
1. A release's input data (what was being released)
2. An agent's risk assessment output
3. A gold-standard expected output

Your job is to grade the agent's output on these dimensions:

## Grading Rubric

### Reasoning Quality (1-5)
1: No reasoning, just states a conclusion
2: Vague reasoning, doesn't reference specific data
3: Adequate reasoning, references some specific data
4: Strong reasoning, references specific files/changes/risks
5: Excellent reasoning, considers combinations of risks and their interactions

### Specificity (1-5)
1: Completely generic, could apply to any release
2: Mentions the general area of changes
3: References specific files or types of changes
4: References specific files AND explains why they matter
5: Detailed file-level analysis with risk-specific recommendations

### Decision Accuracy (1-5)
1: Decision is clearly wrong (GO for a dangerous release, NO_GO for safe one)
2: Decision is questionable, doesn't match the evidence
3: Decision is reasonable but could go either way
4: Decision is correct and well-justified
5: Decision is correct, well-justified, and includes appropriate conditions

### Actionability (1-5)
1: No useful recommendations
2: Generic recommendations ("be careful", "monitor")
3: Some specific recommendations but missing key ones
4: Specific, actionable recommendations covering main risks
5: Comprehensive action plan with specific steps, monitoring, and rollback guidance

Respond with a JSON object:
{
    "reasoning_quality": <1-5>,
    "specificity": <1-5>,
    "decision_accuracy": <1-5>,
    "actionability": <1-5>,
    "overall_score": <1-5>,
    "explanation": "<why you gave these scores>"
}
"""

JUDGE_USER_TEMPLATE = """## Release Input
{input_data}

## Agent's Assessment
{agent_output}

## Expected Assessment (Gold Standard)
{expected_output}

Grade the agent's assessment using the rubric provided."""


# ---------------------------------------------------------------------------
# Judge Evaluator
# ---------------------------------------------------------------------------


async def run_judge_eval(
    input_data: ReleaseInput,
    actual: ReleaseOutput,
    expected: ReleaseOutput,
    example_id: str,
    llm_client: LLMClient | None = None,
) -> list[EvalResult]:
    """Run LLM-as-judge evaluation on an agent's output.

    Args:
        input_data: The original release input
        actual: The agent's actual output
        expected: The expected (gold) output
        example_id: Identifier for the gold example
        llm_client: LLM client for the judge model

    Returns:
        List of EvalResult objects, one per grading dimension
    """
    # TODO: Implement LLM-as-judge evaluation.
    #
    # Steps:
    # 1. Create a judge LLM client (use a different model or same model):
    #    judge_config = LLMConfig(
    #        model="gpt-4o",
    #        temperature=0.0,  # Deterministic for consistency
    #        max_tokens=1024,
    #    )
    #    client = llm_client or LLMClient(config=judge_config)
    #
    # 2. Build the judge prompt:
    #    user_prompt = JUDGE_USER_TEMPLATE.format(
    #        input_data=input_data.model_dump_json(indent=2),
    #        agent_output=actual.model_dump_json(indent=2),
    #        expected_output=expected.model_dump_json(indent=2),
    #    )
    #
    # 3. Call the judge (using raw chat completion, not assess_risk):
    #    Note: You'll need a generic "chat" method on LLMClient,
    #    or call the OpenAI API directly here.
    #
    # 4. Parse the judge's JSON response:
    #    scores = json.loads(judge_response)
    #
    # 5. Convert to EvalResults:
    #    results = []
    #    for dimension in ["reasoning_quality", "specificity",
    #                       "decision_accuracy", "actionability"]:
    #        score = scores[dimension]
    #        results.append(EvalResult(
    #            eval_type="judge",
    #            eval_name=f"judge_{dimension}",
    #            passed=score >= 3,  # 3/5 is the passing threshold
    #            score=score / 5.0,  # Normalize to 0-1
    #            details=scores.get("explanation", ""),
    #            example_id=example_id,
    #        ))
    #    return results
    raise NotImplementedError("TODO: Implement LLM-as-judge evaluation")

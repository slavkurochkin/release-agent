"""Semantic evaluations — measure meaning similarity using embeddings.

Semantic evals go beyond exact matching to check whether the agent's
explanations and reasoning are *semantically close* to the gold examples.
Two explanations can use completely different words but convey the same
risk assessment — semantic evals catch this.

How it works:
1. Get embeddings for the agent's explanation and the gold explanation
2. Compute cosine similarity between the two vectors
3. If similarity is above a threshold, the eval passes

This is important because:
- Exact string matching is too brittle for natural language
- The agent might phrase risks differently but still be correct
- We want to measure *meaning*, not *wording*

Uses OpenAI's text-embedding-3-small model for embeddings.
"""

from __future__ import annotations

from release_agent.evals.runner import EvalResult
from release_agent.llm import LLMClient
from release_agent.schemas import ReleaseOutput

# ---------------------------------------------------------------------------
# Cosine Similarity
# ---------------------------------------------------------------------------


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Cosine similarity measures the angle between two vectors:
    - 1.0 = identical direction (same meaning)
    - 0.0 = orthogonal (unrelated)
    - -1.0 = opposite direction (opposite meaning)

    Args:
        vec_a: First embedding vector
        vec_b: Second embedding vector

    Returns:
        Cosine similarity score between -1.0 and 1.0
    """
    # TODO: Implement cosine similarity.
    #
    # Steps:
    # 1. Convert to numpy arrays:
    #    a = np.array(vec_a)
    #    b = np.array(vec_b)
    #
    # 2. Compute cosine similarity:
    #    dot_product = np.dot(a, b)
    #    norm_a = np.linalg.norm(a)
    #    norm_b = np.linalg.norm(b)
    #
    # 3. Handle edge case (zero vectors):
    #    if norm_a == 0 or norm_b == 0:
    #        return 0.0
    #
    # 4. Return the similarity:
    #    return float(dot_product / (norm_a * norm_b))
    raise NotImplementedError("TODO: Implement cosine similarity")


# ---------------------------------------------------------------------------
# Semantic Evals
# ---------------------------------------------------------------------------


async def run_semantic_evals(
    actual: ReleaseOutput,
    expected: ReleaseOutput,
    example_id: str,
    llm_client: LLMClient | None = None,
    similarity_threshold: float = 0.75,
) -> list[EvalResult]:
    """Run semantic evaluations comparing actual vs expected output.

    Args:
        actual: The agent's actual output
        expected: The expected (gold) output
        example_id: Identifier for the gold example
        llm_client: LLM client for generating embeddings
        similarity_threshold: Minimum similarity score to pass

    Returns:
        List of EvalResult objects
    """
    # TODO: Implement semantic evaluations.
    #
    # Steps:
    # 1. Create LLM client if not provided:
    #    client = llm_client or LLMClient()
    #
    # 2. Run individual semantic checks:
    #    results = []
    #    results.append(
    #        await check_explanation_similarity(
    #            actual, expected, example_id, client, similarity_threshold
    #        )
    #    )
    #    results.append(
    #        await check_summary_similarity(
    #            actual, expected, example_id, client, similarity_threshold
    #        )
    #    )
    #    return results
    raise NotImplementedError("TODO: Implement semantic evals")


async def check_explanation_similarity(
    actual: ReleaseOutput,
    expected: ReleaseOutput,
    example_id: str,
    client: LLMClient,
    threshold: float = 0.75,
) -> EvalResult:
    """Check if the agent's explanation is semantically similar to the expected one.

    Args:
        actual: Agent's output
        expected: Gold example output
        example_id: Example identifier
        client: LLM client for embeddings
        threshold: Minimum similarity score

    Returns:
        EvalResult with similarity score
    """
    # TODO: Implement explanation similarity check.
    #
    # Steps:
    # 1. Get embeddings for both explanations:
    #    actual_emb = await client.get_embedding(actual.explanation)
    #    expected_emb = await client.get_embedding(expected.explanation)
    #
    # 2. Compute cosine similarity:
    #    similarity = cosine_similarity(actual_emb, expected_emb)
    #
    # 3. Return EvalResult:
    #    return EvalResult(
    #        eval_type="semantic",
    #        eval_name="explanation_similarity",
    #        passed=similarity >= threshold,
    #        score=similarity,
    #        details=f"Cosine similarity: {similarity:.3f} (threshold: {threshold})",
    #        example_id=example_id,
    #    )
    raise NotImplementedError("TODO: Implement explanation similarity check")


async def check_summary_similarity(
    actual: ReleaseOutput,
    expected: ReleaseOutput,
    example_id: str,
    client: LLMClient,
    threshold: float = 0.70,
) -> EvalResult:
    """Check if the agent's summary is semantically similar to the expected one.

    Summaries are shorter than explanations, so we use a slightly lower
    threshold since there's less text to match on.

    Args:
        actual: Agent's output
        expected: Gold example output
        example_id: Example identifier
        client: LLM client for embeddings
        threshold: Minimum similarity score

    Returns:
        EvalResult with similarity score
    """
    # TODO: Implement summary similarity check.
    #
    # Same approach as check_explanation_similarity but for the summary field.
    raise NotImplementedError("TODO: Implement summary similarity check")

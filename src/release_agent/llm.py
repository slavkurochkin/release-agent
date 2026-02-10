"""OpenAI LLM client wrapper for the release risk agent.

This module encapsulates all interaction with the OpenAI API. It handles:
- Client initialization and configuration
- Chat completion requests with structured output
- Token counting and budget management
- Retry logic for transient failures
- Response parsing and validation

Design notes:
- Uses OpenAI's response_format for structured JSON output
- Wraps the OpenAI client to keep LLM concerns isolated from business logic
- All LLM calls go through this module so we can swap providers later
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from release_agent.schemas import ReleaseOutput


class LLMConfig(BaseModel):
    """Configuration for the LLM client.

    Attributes:
        model: OpenAI model identifier (e.g., "gpt-4o", "gpt-4o-mini")
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum tokens in the response
        api_key: OpenAI API key (loaded from env if not provided)
    """

    model: str = "gpt-4o"
    temperature: float = 0.2
    max_tokens: int = 4096
    api_key: str | None = None


class LLMClient:
    """Async wrapper around the OpenAI API for structured output generation.

    Usage:
        client = LLMClient(config=LLMConfig())
        result = await client.assess_risk(system_prompt, user_prompt)

    The client uses OpenAI's JSON mode to ensure the response conforms to
    the ReleaseOutput schema. If the response fails validation, it raises
    a ValueError with details about what went wrong.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        """Initialize the LLM client.

        Args:
            config: LLM configuration. Uses defaults if not provided.
        """
        self.config = config or LLMConfig()

        # TODO: Initialize the AsyncOpenAI client.
        # - Use self.config.api_key if provided, otherwise fall back to
        #   the OPENAI_API_KEY environment variable.
        # - Store it as self._client
        # Hint: AsyncOpenAI(api_key=...) — if api_key is None, the SDK
        #   automatically reads from the OPENAI_API_KEY env var.
        self._client: AsyncOpenAI | None = None  # Replace with real init

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def assess_risk(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ReleaseOutput:
        """Send a risk assessment request to the LLM and parse the response.

        This method:
        1. Sends the system + user prompts to OpenAI
        2. Requests JSON output conforming to the ReleaseOutput schema
        3. Parses and validates the response
        4. Returns a typed ReleaseOutput object

        Args:
            system_prompt: The system message (instructions, persona, rules)
            user_prompt: The user message (release data to assess)

        Returns:
            A validated ReleaseOutput instance

        Raises:
            ValueError: If the LLM response doesn't conform to the schema
            openai.APIError: If the OpenAI API call fails after retries
        """
        # TODO: Implement the OpenAI API call with structured output.
        #
        # Steps:
        # 1. Build the messages list:
        #    messages = [
        #        {"role": "system", "content": system_prompt},
        #        {"role": "user", "content": user_prompt},
        #    ]
        #
        # 2. Call self._client.chat.completions.create() with:
        #    - model=self.config.model
        #    - messages=messages
        #    - temperature=self.config.temperature
        #    - max_tokens=self.config.max_tokens
        #    - response_format={"type": "json_object"}
        #
        # 3. Extract the response content:
        #    content = response.choices[0].message.content
        #
        # 4. Parse the JSON string into a dict:
        #    data = json.loads(content)
        #
        # 5. Validate using Pydantic:
        #    return ReleaseOutput.model_validate(data)
        #
        # 6. If json.loads() or model_validate() fails, raise ValueError
        #    with a helpful message including the raw content.
        #
        # Hint: Wrap the parse/validate in try/except to give clear errors.
        raise NotImplementedError("TODO: Implement LLM API call")

    async def get_embedding(self, text: str) -> list[float]:
        """Get an embedding vector for the given text.

        Used in Phase 5 for semantic similarity evals.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        # TODO: Implement embedding generation.
        #
        # Steps:
        # 1. Call self._client.embeddings.create() with:
        #    - model="text-embedding-3-small"
        #    - input=text
        #
        # 2. Extract the embedding:
        #    return response.data[0].embedding
        raise NotImplementedError("TODO: Implement embedding generation")

    def _get_schema_for_response_format(self) -> dict[str, Any]:
        """Generate the JSON schema to send to OpenAI for structured output.

        Returns:
            The JSON schema dict derived from ReleaseOutput
        """
        # TODO: Generate and return the JSON schema from ReleaseOutput.
        # Hint: Use ReleaseOutput.model_json_schema()
        # This is useful for including in the system prompt so the LLM
        # knows exactly what format to produce.
        raise NotImplementedError("TODO: Generate JSON schema")

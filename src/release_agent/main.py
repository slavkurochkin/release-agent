"""FastAPI application for the release risk agent.

This module sets up the web API layer that wraps the agent. It provides:
- POST /assess - Submit a release for risk assessment
- GET /health - Health check for load balancers and monitoring
- Automatic OpenAPI/Swagger documentation at /docs

Architecture notes:
- FastAPI handles HTTP concerns (routing, validation, serialization)
- The agent handles business logic (prompts, LLM calls, policy)
- Pydantic schemas are shared between both layers for consistency
- Error handling middleware catches and formats exceptions

To run locally:
    uvicorn release_agent.main:app --reload --port 8000

Then visit http://localhost:8000/docs for the interactive API docs.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from release_agent.schemas import ReleaseInput, ReleaseOutput

# ---------------------------------------------------------------------------
# Application Lifespan (startup/shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    This is where you initialize expensive resources (like the agent)
    once at startup, rather than on every request.
    """
    # TODO: Initialize the ReleaseRiskAgent at startup.
    #
    # Steps:
    # 1. Create the agent instance:
    #    app.state.agent = ReleaseRiskAgent()
    #
    # 2. yield to let the app run
    #
    # 3. Clean up resources on shutdown (if any)
    #
    # Hint: The agent is stateless, so cleanup is minimal.
    # In Phase 7, you'll add logging setup and DB connections here.
    yield


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Release Risk Agent",
    description="AI-powered release risk assessment service",
    version="0.1.0",
    lifespan=lifespan,
)

# TODO: Configure CORS middleware.
#
# Steps:
# 1. Add CORSMiddleware to the app:
#    app.add_middleware(
#        CORSMiddleware,
#        allow_origins=["*"],       # Restrict in production
#        allow_credentials=True,
#        allow_methods=["*"],
#        allow_headers=["*"],
#    )
#
# Hint: In production (Phase 7), you'll restrict allow_origins
# to your actual frontend domain.


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions (e.g., invalid LLM output).

    Returns a 422 Unprocessable Entity with error details.
    """
    # TODO: Return a proper JSON error response.
    #
    # return JSONResponse(
    #     status_code=422,
    #     content={"error": "validation_error", "detail": str(exc)},
    # )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "Not implemented"},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all error handler for unexpected exceptions.

    In development, includes error details. In production (Phase 7),
    you'll want to log the full traceback but return a generic message.
    """
    # TODO: Implement proper error handling.
    #
    # return JSONResponse(
    #     status_code=500,
    #     content={
    #         "error": "internal_error",
    #         "detail": str(exc),  # Remove in production
    #     },
    # )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "Not implemented"},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring.

    Returns:
        A simple status dict indicating the service is running.
    """
    # TODO: Implement health check.
    #
    # For now, just return {"status": "healthy"}.
    # In Phase 7, you might also check:
    # - LLM API connectivity
    # - Database connectivity
    # - Memory/CPU usage
    return {"status": "not_implemented"}


@app.post("/assess", response_model=ReleaseOutput)
async def assess_release(release: ReleaseInput, request: Request) -> ReleaseOutput:
    """Assess the risk of a release.

    This is the main endpoint. It:
    1. Validates the input (FastAPI does this automatically via Pydantic)
    2. Passes the data to the agent
    3. Returns the structured risk assessment

    Args:
        release: The release data to assess (validated by FastAPI)
        request: The incoming HTTP request (for accessing app state)

    Returns:
        A ReleaseOutput with the risk assessment

    Raises:
        HTTPException: If the agent fails to produce a valid assessment
    """
    # TODO: Call the agent and return the result.
    #
    # Steps:
    # 1. Get the agent from app state:
    #    agent: ReleaseRiskAgent = request.app.state.agent
    #
    # 2. Call the agent:
    #    try:
    #        result = await agent.assess(release)
    #    except ValueError as e:
    #        raise HTTPException(status_code=422, detail=str(e))
    #    except Exception as e:
    #        raise HTTPException(status_code=500, detail=f"Assessment failed: {e}")
    #
    # 3. Return the result (FastAPI serializes it automatically):
    #    return result
    raise HTTPException(status_code=501, detail="Not implemented")

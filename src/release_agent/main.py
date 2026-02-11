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
from fastapi.middleware.cors import CORSMiddleware

from release_agent.schemas import ReleaseInput, ReleaseOutput
from release_agent.agent import ReleaseRiskAgent
import time
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict


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
    # Startup: create the agent once
    app.state.agent = ReleaseRiskAgent()
    yield
    # Shutdown: nothing to clean up for now


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        print(
            f"{request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.2f}s)"
        )
        return response

app.add_middleware(LoggingMiddleware)

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # Remove old entries
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if now - t < self.window
        ]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True
    
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        response.headers["X-Process-Time"] = f"{duration:.2f}s"
        return response    

# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": str(exc)},
    )


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
    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": str(exc),
        },
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
    return {"status": "healthy"}


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
    agent: ReleaseRiskAgent = request.app.state.agent
    try:
        result = await agent.assess(release)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {e}")
    return result

@app.post("/assess/batch", response_model=list[ReleaseOutput])
async def assess_batch(
    releases: list[ReleaseInput],
    request: Request,
) -> list[ReleaseOutput]:
    """Assess multiple releases concurrently.

    Accepts a JSON array of ReleaseInput objects and returns a
    corresponding array of ReleaseOutput objects. Assessments run
    concurrently using asyncio.gather for efficiency.
    """
    agent: ReleaseRiskAgent = request.app.state.agent

    # Run all assessments concurrently
    import asyncio
    tasks = [agent.assess(release) for release in releases]

    try:
        results = await asyncio.gather(*tasks)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch assessment failed: {e}")

    return list(results) 

@app.post("/assess/dry-run")
async def dry_run(release: ReleaseInput) -> dict:
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(release)
    return {
        "valid": True,
        "system_prompt_length": len(system_prompt),
        "user_prompt_length": len(user_prompt),
        "system_prompt_preview": system_prompt[:500],
        "user_prompt_preview": user_prompt[:500],
    }   
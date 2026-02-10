# =============================================================================
# Multi-stage Dockerfile for the Release Risk Agent
# =============================================================================
#
# This Dockerfile uses a multi-stage build to create a small, secure image:
#   Stage 1 (builder): Install dependencies and build the package
#   Stage 2 (runtime): Copy only what's needed to run
#
# Why multi-stage?
# - Build tools (gcc, pip cache) aren't needed at runtime
# - Smaller image = faster deploys, less attack surface
# - Final image is ~150MB instead of ~800MB
#
# Usage:
#   docker build -t release-agent .
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... release-agent
#
# For Cloud Run:
#   gcloud builds submit --tag gcr.io/PROJECT_ID/release-agent
#   gcloud run deploy release-agent --image gcr.io/PROJECT_ID/release-agent
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# TODO: Set up the build environment.
#
# Steps:
# 1. Set working directory:
WORKDIR /app

# 2. Install build dependencies (if any native packages need compiling):
#    RUN apt-get update && apt-get install -y --no-install-recommends \
#        gcc \
#        && rm -rf /var/lib/apt/lists/*

# 3. Copy dependency files first (for Docker layer caching):
#    When dependencies don't change, Docker reuses this layer.
COPY pyproject.toml ./

# 4. Install dependencies into a virtual environment:
#    Using a venv makes it easy to copy just the installed packages
#    to the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# TODO: Install the project dependencies.
# RUN pip install --no-cache-dir .
# For now, just install dependencies without the package itself:
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir .

# 5. Copy the rest of the source code:
COPY src/ src/

# 6. Install the package itself:
RUN pip install --no-cache-dir .


# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# TODO: Set up the runtime environment.
#
# Security best practices:
# - Run as non-root user
# - No build tools in the final image
# - Minimal OS packages

# 1. Create a non-root user:
RUN groupadd --gid 1000 agent && \
    useradd --uid 1000 --gid agent --shell /bin/bash --create-home agent

# 2. Copy the virtual environment from the builder:
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Set working directory:
WORKDIR /app

# 4. Copy source code (needed for prompts and any file-based config):
COPY --from=builder /app/src /app/src

# 5. Switch to non-root user:
USER agent

# 6. Set environment variables:
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# 7. Health check (for Docker and Cloud Run):
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# 8. Expose the port:
EXPOSE ${PORT}

# 9. Start the application:
#    Cloud Run sets PORT env var, uvicorn reads it.
# TODO: Configure the CMD to start the FastAPI app.
CMD ["uvicorn", "release_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Release Risk Agent

An AI-powered agent that analyzes release metadata (PR diffs, CI results, commit history, incident context) and produces structured risk assessments with GO/NO_GO decisions.

---

## Architecture Overview

```
                         Release Risk Agent Pipeline
 ============================================================================

  ReleaseInput            Context              Prompt              OpenAI
  (PR, commits,          Building             Building             GPT-4
   CI results)      (GitHub, CI, Incidents)  (System + User)      (LLM Call)
       |                    |                    |                    |
       v                    v                    v                    v
  +---------+        +------------+        +------------+       +--------+
  |  Input  | -----> |  Context   | -----> |  Prompt    | ----> |  LLM   |
  |  Schema |        |  Builders  |        |  Templates |       | Client |
  +---------+        +------------+        +------------+       +--------+
                                                                     |
                                                                     v
                                                               +----------+
                       ReleaseOutput         Policy Engine      |  Parsed  |
                       (decision,       <--- (hard rules,  <--- |  JSON    |
                        risk score,          thresholds,        | Response |
                        factors,             overrides)         +----------+
                        actions)
```

The agent receives release data, enriches it with context from external sources, builds tailored prompts, sends them to GPT-4 for risk analysis, then passes the LLM output through a deterministic policy engine that enforces hard rules (e.g., failing CI always forces NO_GO, risk score above 0.7 forces NO_GO). The final output is a validated `ReleaseOutput` with a decision, risk score, risk factors, and recommended actions.

---

## Quick Start

### Prerequisites

- Python 3.12+
- An OpenAI API key

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd release-agent

# Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# Install the package and dependencies
pip install -e ".[dev]"
```

### Environment Setup

```bash
# Copy the example env file and fill in your keys
cp .env.example .env
```

Edit `.env` and set at minimum:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

### Run the CLI

```bash
# Assess a release from a JSON file
release-agent --input release_data.json

# Or pipe JSON via stdin
cat release_data.json | release-agent
```

### Run the API Server

```bash
uvicorn release_agent.main:app --reload --port 8000
```

Then open http://localhost:8000/docs for the interactive Swagger UI.

### Run with Docker

```bash
docker build -t release-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... release-agent
```

---

## Project Structure

```
release-agent/
|-- src/release_agent/
|   |-- agent.py              # Core agent orchestrator (assess pipeline)
|   |-- main.py               # FastAPI application (API layer)
|   |-- schemas.py            # Pydantic input/output models
|   |-- llm.py                # OpenAI client wrapper (structured output)
|   |-- policy.py             # Deterministic policy engine (hard rules)
|   |-- logging_config.py     # Structured logging setup (structlog)
|   |-- prompts/
|   |   |-- assess_risk.py    # System and user prompt templates
|   |-- context/
|   |   |-- github.py         # GitHub API client for PR data
|   |   |-- ci.py             # CI pipeline results fetcher
|   |   |-- incidents.py      # Incident history context builder
|   |-- evals/
|       |-- runner.py         # Eval orchestrator and CLI
|       |-- functional.py     # Schema and constraint checks
|       |-- semantic.py       # Embedding-based similarity evals
|       |-- judge.py          # LLM-as-a-judge evals
|       |-- adversarial.py    # Robustness and edge case evals
|       |-- storage.py        # Eval result persistence
|-- tests/
|   |-- test_agent.py         # Agent orchestration tests
|   |-- test_policy.py        # Policy engine rule tests
|   |-- test_schemas.py       # Schema validation tests
|   |-- fixtures/
|       |-- gold_examples.json # Gold reference examples for evals
|-- dashboard/
|   |-- app.py                # Streamlit eval results dashboard
|-- docs/
|   |-- phase-1-core-agent/
|   |-- phase-2-api-layer/
|   |-- phase-3-context-building/
|   |-- phase-4-policy-engine/
|   |-- phase-5-evals/
|   |-- phase-6-deployment/
|   |-- phase-7-production/
|-- Dockerfile                # Multi-stage build for Cloud Run
|-- pyproject.toml            # Project config, dependencies, tooling
|-- .env.example              # Environment variable template
|-- .github/workflows/
    |-- deploy.yml            # CI/CD pipeline for GCP deployment
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_agent.py -v

# Skip slow and integration tests
pytest -m "not slow and not integration"

# Run with coverage (requires pytest-cov)
pytest --cov=release_agent --cov-report=term-missing
```

### Linting and Type Checking

```bash
# Lint with ruff
ruff check src/ tests/

# Type check with mypy
mypy src/
```

### Running Evals

```bash
python -m release_agent.evals.runner \
    --examples tests/fixtures/gold_examples.json \
    --output eval_results/report.json
```

---

## Deployment

The agent is designed to run on GCP Cloud Run as a stateless container.

```bash
# Build and push the container image
gcloud builds submit --tag gcr.io/PROJECT_ID/release-agent

# Deploy to Cloud Run
gcloud run deploy release-agent \
    --image gcr.io/PROJECT_ID/release-agent \
    --platform managed \
    --region us-central1 \
    --set-env-vars OPENAI_API_KEY=sk-...,ENVIRONMENT=production
```

For full deployment instructions, infrastructure setup (BigQuery, Cloud Logging, Cloud Trace), and CI/CD configuration, see `docs/phase-6-deployment/`.

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from release_agent.main import app
from release_agent.schemas import Decision, ReleaseOutput, RiskFactor, RiskLevel

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_assess_invalid_input():
    response = client.post("/assess", json={"bad": "data"})
    assert response.status_code == 422

def test_assess_valid_input():
    # Mock the agent to avoid real LLM calls
    mock_output = ReleaseOutput(
        decision=Decision.GO,
        risk_level=RiskLevel.LOW,
        risk_score=0.1,
        summary="Test summary for the mock response.",
        explanation="Test explanation that is long enough to pass validation checks.",
        risk_factors=[],
        conditions=[],
        recommended_actions=[],
    )

    with patch.object(
        app.state, "agent", create=True
    ) as mock_agent:
        mock_agent.assess = AsyncMock(return_value=mock_output)
        response = client.post("/assess", json={
            "repo": "org/repo",
            "pr_number": 1,
            "title": "Test PR",
            "author": "user",
            "commit_messages": ["fix: test"],
        })
        assert response.status_code == 200
        assert response.json()["decision"] == "GO"
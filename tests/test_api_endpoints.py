"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app import app


@pytest.mark.asyncio
async def test_api_benchmarks_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert "gold_standard_a" not in data[0]  # Ensure gold standard is kept hidden!


@pytest.mark.asyncio
async def test_api_history_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_evaluate_endpoint():
    payload = {
        "prompt": "Evaluate this test case",
        "model_a_name": "llama3:latest",
        "model_a_response": "Output A",
        "model_b_name": "gemini-1.5-flash",
        "model_b_response": "Output B",
        "assessment_a": {
            "factual_accuracy": {"score": 5},
            "adherence": {"score": 5},
            "completeness": {"score": 5},
            "tone": {"score": 5},
            "structure": {"score": 5}
        },
        "assessment_b": {
            "factual_accuracy": {"score": 3},
            "adherence": {"score": 4},
            "completeness": {"score": 4},
            "tone": {"score": 4},
            "structure": {"score": 4}
        },
        "winner": "model_a",
        "tags": ["integration-test"]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["comparison"]["score_a"] == 100.0
    assert data["comparison"]["recommended_winner"] == "model_a"


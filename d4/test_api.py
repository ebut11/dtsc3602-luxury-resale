"""Local API tests: 200 on valid input, 422 on invalid input, 503 when the artifact is missing.

Run from the repository root:  uv run python -m pytest d4 -q
The 503 test points MODEL_PATH at a missing file locally; the live app is never touched.
"""
import pytest
from fastapi.testclient import TestClient

from d4 import api

VALID = {"brand": "Gucci", "item_type": "Handbag", "condition": "Very Good",
         "age_band": None, "estimated_retail_price": 2000}


@pytest.fixture
def client():
    with TestClient(api.app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["model_loaded"] is True


def test_pipeline_info(client):
    r = client.get("/pipeline/info")
    assert r.status_code == 200
    body = r.json()
    assert body["steps"] == ["prepare", "encode", "model"]
    assert body["sklearn_version"] == body["server_sklearn_version"]


def test_valid_prediction(client):
    r = client.post("/predict", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["predicted_percentage"] <= 83.3
    assert body["predicted_asking_price"] == round(2000 * body["predicted_percentage"] / 100, 2)


def test_extreme_inputs_are_capped(client):
    best = {"brand": "Chanel", "item_type": "Handbag", "condition": "Pristine",
            "age_band": "5 or less", "estimated_retail_price": 2000}
    assert client.post("/predict", json=best).json()["predicted_percentage"] <= 83.3
    pricey = client.post("/predict", json={**VALID, "estimated_retail_price": 500_000}).json()
    assert 0 <= pricey["predicted_percentage"] <= 83.3


@pytest.mark.parametrize("bad", [
    {**VALID, "brand": "Prada"},
    {**VALID, "brand": "gucci"},
    {**VALID, "condition": "Mint"},
    {**VALID, "item_type": "Car"},
    {**VALID, "age_band": "banana"},
    {**VALID, "estimated_retail_price": -5},
    {**VALID, "estimated_retail_price": 5_000_000},
    {k: v for k, v in VALID.items() if k != "estimated_retail_price"},
    {**VALID, "color": "red"},
])
def test_invalid_input_returns_422(client, bad):
    assert client.post("/predict", json=bad).status_code == 422


def test_missing_artifact_returns_503(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "missing.joblib"))
    with TestClient(api.app) as c:
        assert c.get("/health").json()["model_loaded"] is False
        assert c.post("/predict", json=VALID).status_code == 503
        assert c.get("/pipeline/info").status_code == 503

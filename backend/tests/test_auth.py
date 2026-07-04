from fastapi.testclient import TestClient

from app.api.api_v1.dependencies import get_classifier, verify_api_key  # noqa: F401
from app.main import app


class StubRuleManager:
    def get_all_rules(self):
        return []


class StubClassifier:
    rule_manager = StubRuleManager()


app.dependency_overrides[get_classifier] = lambda: StubClassifier()

client = TestClient(app)


def test_missing_api_key_rejected():
    response = client.get("/api/v1/rules")
    assert response.status_code == 401


def test_wrong_api_key_rejected():
    response = client.get("/api/v1/rules", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_correct_api_key_accepted():
    response = client.get("/api/v1/rules", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200
    assert response.json() == {"rules": []}


def test_openapi_stays_open():
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200


def test_cors_allows_frontend_origin():
    response = client.options(
        "/api/v1/transactions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_blocks_unknown_origin():
    response = client.options(
        "/api/v1/transactions",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "CRAM API",
        "status": "running",
        "version": "0.1.0",
    }


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "cram-api",
        "version": "0.1.0",
    }


def test_version_endpoint() -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json()["service"] == "cram-api"
    assert response.json()["version"] == "0.1.0"
    assert response.json()["environment"] == "development"

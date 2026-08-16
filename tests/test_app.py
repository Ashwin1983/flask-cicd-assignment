import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_home_success(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "running"


def test_health_success(client):
    response = client.get("/health")

    assert response.status_code == 500

    data = response.get_json()

    assert data["status"] == "healthy"


def test_status_success(client):
    response = client.get("/api/status")

    assert response.status_code == 200


def test_invalid_route_failure(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
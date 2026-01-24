from fastapi.testclient import TestClient

from furu.dashboard.main import create_app


def test_dashboard_spa_rejects_path_traversal() -> None:
    app = create_app(serve_frontend=True)
    client = TestClient(app)

    response = client.get("/%2e%2e/pyproject.toml")

    assert response.status_code == 404

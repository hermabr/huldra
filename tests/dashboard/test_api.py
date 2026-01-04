"""Tests for Dashboard API routes."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_experiments_empty(client: TestClient, temp_huldra_root: Path) -> None:
    """Test listing experiments when none exist."""
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert data["experiments"] == []
    assert data["total"] == 0


def test_list_experiments(client: TestClient, populated_huldra_root: Path) -> None:
    """Test listing all experiments."""
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["experiments"]) == 5

    # Check structure of returned experiments
    exp = data["experiments"][0]
    assert "namespace" in exp
    assert "huldra_hash" in exp
    assert "class_name" in exp
    assert "result_status" in exp


def test_list_experiments_filter_by_result_status(
    client: TestClient, populated_huldra_root: Path
) -> None:
    """Test filtering experiments by result status."""
    response = client.get("/api/experiments?result_status=success")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for exp in data["experiments"]:
        assert exp["result_status"] == "success"


def test_list_experiments_filter_by_attempt_status(
    client: TestClient, populated_huldra_root: Path
) -> None:
    """Test filtering experiments by attempt status."""
    response = client.get("/api/experiments?attempt_status=running")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["experiments"][0]["attempt_status"] == "running"


def test_list_experiments_filter_by_namespace(
    client: TestClient, populated_huldra_root: Path
) -> None:
    """Test filtering experiments by namespace prefix."""
    response = client.get("/api/experiments?namespace=my_project.pipelines")
    assert response.status_code == 200
    data = response.json()
    # 4 experiments: TrainModel x2, EvalModel, PrepareData
    assert data["total"] == 4
    for exp in data["experiments"]:
        assert exp["namespace"].startswith("my_project.pipelines")


def test_list_experiments_pagination(
    client: TestClient, populated_huldra_root: Path
) -> None:
    """Test pagination of experiments."""
    response = client.get("/api/experiments?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["experiments"]) == 2

    response = client.get("/api/experiments?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["experiments"]) == 2


def test_get_experiment_detail(client: TestClient, populated_huldra_root: Path) -> None:
    """Test getting detailed experiment information."""
    response = client.get(
        "/api/experiments/my_project.pipelines.TrainModel/abc123def456"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["namespace"] == "my_project.pipelines.TrainModel"
    assert data["huldra_hash"] == "abc123def456"
    assert data["class_name"] == "TrainModel"
    assert data["result_status"] == "success"
    assert data["attempt_status"] == "success"
    assert "directory" in data
    assert "state" in data
    assert "metadata" in data


def test_get_experiment_detail_with_attempt(
    client: TestClient, populated_huldra_root: Path
) -> None:
    """Test that experiment detail includes attempt information."""
    response = client.get(
        "/api/experiments/my_project.pipelines.TrainModel/xyz789ghi012"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["attempt_status"] == "running"
    assert data["attempt"] is not None
    assert data["attempt"]["status"] == "running"
    assert data["attempt"]["owner"]["host"] == "test-host"


def test_get_experiment_not_found(
    client: TestClient, populated_huldra_root: Path
) -> None:
    """Test getting a non-existent experiment."""
    response = client.get("/api/experiments/nonexistent.Namespace/fake123hash")
    assert response.status_code == 404
    assert response.json()["detail"] == "Experiment not found"


def test_dashboard_stats_empty(client: TestClient, temp_huldra_root: Path) -> None:
    """Test stats endpoint with no experiments."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["running_count"] == 0
    assert data["queued_count"] == 0
    assert data["failed_count"] == 0
    assert data["success_count"] == 0


def test_dashboard_stats(client: TestClient, populated_huldra_root: Path) -> None:
    """Test aggregate statistics endpoint."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 5
    assert data["success_count"] == 2
    assert data["failed_count"] == 1
    assert data["running_count"] == 1

    # Check by_result_status
    result_statuses = {s["status"]: s["count"] for s in data["by_result_status"]}
    assert result_statuses.get("success", 0) == 2
    assert result_statuses.get("failed", 0) == 1
    assert result_statuses.get("incomplete", 0) == 1
    assert result_statuses.get("absent", 0) == 1


def test_combined_filters(client: TestClient, populated_huldra_root: Path) -> None:
    """Test combining multiple filters."""
    response = client.get("/api/experiments?result_status=success&namespace=my_project")
    assert response.status_code == 200
    data = response.json()
    # Only my_project.pipelines.TrainModel/abc123def456 matches both
    assert data["total"] == 1
    assert data["experiments"][0]["result_status"] == "success"
    assert data["experiments"][0]["namespace"].startswith("my_project")

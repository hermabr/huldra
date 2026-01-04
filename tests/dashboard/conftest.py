"""Pytest fixtures for dashboard tests."""

import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from huldra.config import HULDRA_CONFIG
from huldra.dashboard.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_huldra_root(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary Huldra root directory and configure it."""
    original_root = HULDRA_CONFIG.base_root
    HULDRA_CONFIG.base_root = tmp_path

    yield tmp_path

    HULDRA_CONFIG.base_root = original_root


def create_experiment(
    root: Path,
    namespace: str,
    huldra_hash: str,
    result_status: str = "success",
    attempt_status: str | None = None,
    version_controlled: bool = False,
) -> Path:
    """
    Helper to create a mock experiment directory with state.

    Args:
        root: Huldra base root directory
        namespace: Dot-separated namespace (e.g., "my_project.pipelines.Train")
        huldra_hash: Hash identifier
        result_status: One of: absent, incomplete, success, failed
        attempt_status: Optional attempt status (queued, running, success, failed, etc.)
        version_controlled: Whether to put in git/ or data/ subdirectory

    Returns:
        Path to the created experiment directory
    """
    subdir = "git" if version_controlled else "data"
    namespace_path = Path(*namespace.split("."))
    experiment_dir = root / subdir / namespace_path / huldra_hash
    huldra_dir = experiment_dir / ".huldra"
    huldra_dir.mkdir(parents=True, exist_ok=True)

    # Build state based on result_status
    if result_status == "absent":
        result = {"status": "absent"}
    elif result_status == "incomplete":
        result = {"status": "incomplete"}
    elif result_status == "success":
        result = {"status": "success", "created_at": "2025-01-01T12:00:00+00:00"}
    else:  # failed
        result = {"status": "failed"}

    # Build attempt if status provided
    attempt = None
    if attempt_status:
        attempt = {
            "id": f"attempt-{huldra_hash[:8]}",
            "number": 1,
            "backend": "local",
            "status": attempt_status,
            "started_at": "2025-01-01T11:00:00+00:00",
            "heartbeat_at": "2025-01-01T11:30:00+00:00",
            "lease_duration_sec": 120.0,
            "lease_expires_at": "2025-01-01T13:00:00+00:00",
            "owner": {
                "pid": 12345,
                "host": "test-host",
                "user": "testuser",
            },
            "scheduler": {},
        }
        if attempt_status in ("success", "failed", "crashed", "cancelled", "preempted"):
            attempt["ended_at"] = "2025-01-01T12:00:00+00:00"
        if attempt_status == "failed":
            attempt["error"] = {
                "type": "RuntimeError",
                "message": "Test error",
            }

    state = {
        "schema_version": 1,
        "result": result,
        "attempt": attempt,
        "updated_at": "2025-01-01T12:00:00+00:00",
    }

    state_path = huldra_dir / "state.json"
    state_path.write_text(json.dumps(state, indent=2))

    # Create metadata
    metadata = {
        "huldra_python_def": f"{namespace}()",
        "huldra_obj": {"__class__": namespace},
        "huldra_hash": huldra_hash,
        "huldra_path": str(experiment_dir),
        "git_commit": "abc123",
        "git_branch": "main",
        "timestamp": "2025-01-01T11:00:00+00:00",
        "hostname": "test-host",
        "user": "testuser",
    }
    metadata_path = huldra_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return experiment_dir


@pytest.fixture
def populated_huldra_root(temp_huldra_root: Path) -> Path:
    """Create a temporary Huldra root with sample experiments."""
    # Create various experiments with different states
    create_experiment(
        temp_huldra_root,
        "my_project.pipelines.TrainModel",
        "abc123def456",
        result_status="success",
        attempt_status="success",
    )
    create_experiment(
        temp_huldra_root,
        "my_project.pipelines.TrainModel",
        "xyz789ghi012",
        result_status="incomplete",
        attempt_status="running",
    )
    create_experiment(
        temp_huldra_root,
        "my_project.pipelines.EvalModel",
        "eval123abc",
        result_status="failed",
        attempt_status="failed",
    )
    create_experiment(
        temp_huldra_root,
        "other_project.DataLoader",
        "data456def",
        result_status="success",
        attempt_status="success",
    )
    create_experiment(
        temp_huldra_root,
        "my_project.pipelines.PrepareData",
        "prep789xyz",
        result_status="absent",
        attempt_status=None,
    )

    return temp_huldra_root

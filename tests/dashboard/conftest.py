"""Pytest fixtures for dashboard tests.

FIXTURE SELECTION GUIDE
=======================

Use `populated_huldra_root` (module-scoped, fast) when:
- Test only reads/queries existing experiments
- Test doesn't need specific isolated data
- Test can work with the shared fixture data (see _create_populated_experiments)

Use `temp_huldra_root` (function-scoped, slow) when:
- Test needs an empty directory (e.g., testing empty state)
- Test needs to create experiments with specific attributes not in the shared fixture
- Test mutates experiment state
- Test needs isolated data to verify "no match" scenarios

The populated fixture creates experiments once per test module and reuses them,
which is significantly faster than creating experiments for each test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from huldra.config import HULDRA_CONFIG
from huldra.dashboard.main import app
from huldra.serialization import HuldraSerializer
from huldra.storage import MetadataManager, StateManager

from .pipelines import (
    DataLoader,
    EvalModel,
    MultiDependencyPipeline,
    PrepareDataset,
    TrainModel,
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_huldra_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    """Create a temporary Huldra root directory and configure it.

    Use this fixture when tests need isolated/empty state or must create
    specific experiments. For read-only tests, prefer `populated_huldra_root`.
    """
    monkeypatch.setattr(HULDRA_CONFIG, "base_root", tmp_path)
    monkeypatch.setattr(HULDRA_CONFIG, "ignore_git_diff", True)
    monkeypatch.setattr(HULDRA_CONFIG, "poll_interval", 0.01)
    monkeypatch.setattr(HULDRA_CONFIG, "stale_timeout", 0.1)
    monkeypatch.setattr(HULDRA_CONFIG, "lease_duration_sec", 0.05)
    monkeypatch.setattr(HULDRA_CONFIG, "heartbeat_interval_sec", 0.01)

    yield tmp_path


# Module-scoped fixtures for read-only tests (much faster)
@pytest.fixture(scope="module")
def module_huldra_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a module-scoped temporary Huldra root directory."""
    return tmp_path_factory.mktemp("huldra_root")


@pytest.fixture(scope="module")
def _configure_huldra_for_module(
    module_huldra_root: Path,
) -> Generator[Path, None, None]:
    """Configure HULDRA_CONFIG for module-scoped tests."""
    # Save original values
    orig_base_root = HULDRA_CONFIG.base_root
    orig_ignore_git_diff = HULDRA_CONFIG.ignore_git_diff
    orig_poll_interval = HULDRA_CONFIG.poll_interval
    orig_stale_timeout = HULDRA_CONFIG.stale_timeout
    orig_lease_duration = HULDRA_CONFIG.lease_duration_sec
    orig_heartbeat = HULDRA_CONFIG.heartbeat_interval_sec

    # Set test values
    HULDRA_CONFIG.base_root = module_huldra_root
    HULDRA_CONFIG.ignore_git_diff = True
    HULDRA_CONFIG.poll_interval = 0.01
    HULDRA_CONFIG.stale_timeout = 0.1
    HULDRA_CONFIG.lease_duration_sec = 0.05
    HULDRA_CONFIG.heartbeat_interval_sec = 0.01

    yield module_huldra_root

    # Restore original values
    HULDRA_CONFIG.base_root = orig_base_root
    HULDRA_CONFIG.ignore_git_diff = orig_ignore_git_diff
    HULDRA_CONFIG.poll_interval = orig_poll_interval
    HULDRA_CONFIG.stale_timeout = orig_stale_timeout
    HULDRA_CONFIG.lease_duration_sec = orig_lease_duration
    HULDRA_CONFIG.heartbeat_interval_sec = orig_heartbeat


def create_experiment_from_huldra(
    huldra_obj: object,
    result_status: str = "success",
    attempt_status: str | None = None,
    backend: str = "local",
    hostname: str = "test-host",
    user: str = "testuser",
    started_at: str = "2025-01-01T11:00:00+00:00",
    updated_at: str = "2025-01-01T12:00:00+00:00",
) -> Path:
    """
    Create an experiment directory from an actual Huldra object.

    This creates realistic metadata and state by using the actual Huldra
    serialization and metadata systems.

    Args:
        huldra_obj: A Huldra subclass instance
        result_status: One of: absent, incomplete, success, failed
        attempt_status: Optional attempt status (queued, running, success, failed, etc.)
        backend: Backend type (local, submitit)
        hostname: Hostname where the experiment ran
        user: User who ran the experiment
        started_at: ISO timestamp for when the experiment started
        updated_at: ISO timestamp for when the experiment was last updated

    Returns:
        Path to the created experiment directory
    """
    # Get the huldra_dir from the object (uses real path computation)
    directory = huldra_obj.huldra_dir  # type: ignore[attr-defined]
    directory.mkdir(parents=True, exist_ok=True)

    # Create metadata using the actual metadata system
    metadata = MetadataManager.create_metadata(
        huldra_obj,  # type: ignore[arg-type]
        directory,
        ignore_diff=True,
    )
    MetadataManager.write_metadata(metadata, directory)

    # Build state based on result_status
    if result_status == "absent":
        result: dict[str, str] = {"status": "absent"}
    elif result_status == "incomplete":
        result = {"status": "incomplete"}
    elif result_status == "success":
        result = {"status": "success", "created_at": updated_at}
    else:  # failed
        result = {"status": "failed"}

    # Build attempt if status provided
    attempt: dict[str, str | int | float | dict[str, str | int] | None] | None = None
    if attempt_status:
        attempt = {
            "id": f"attempt-{HuldraSerializer.compute_hash(huldra_obj)[:8]}",
            "number": 1,
            "backend": backend,
            "status": attempt_status,
            "started_at": started_at,
            "heartbeat_at": started_at,
            "lease_duration_sec": 120.0,
            "lease_expires_at": "2025-01-01T13:00:00+00:00",
            "owner": {
                "pid": 12345,
                "host": hostname,
                "hostname": hostname,
                "user": user,
            },
            "scheduler": {},
        }
        if attempt_status in ("success", "failed", "crashed", "cancelled", "preempted"):
            attempt["ended_at"] = updated_at
        if attempt_status == "failed":
            attempt["error"] = {
                "type": "RuntimeError",
                "message": "Test error",
            }

    state = {
        "schema_version": 1,
        "result": result,
        "attempt": attempt,
        "updated_at": updated_at,
    }

    state_path = StateManager.get_state_path(directory)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2))

    # Write success marker if successful
    if result_status == "success":
        success_marker = StateManager.get_success_marker_path(directory)
        success_marker.write_text(
            json.dumps(
                {
                    "attempt_id": attempt["id"] if attempt else "unknown",
                    "created_at": updated_at,
                }
            )
        )

    return directory


def _create_populated_experiments(root: Path) -> None:
    """Create sample experiments in the given root directory.

    Creates experiments with realistic dependencies and varied attributes
    for comprehensive filter testing:
    - PrepareDataset (success, local, gpu-01, alice, 2025-01-01)
    - TrainModel with dependency on PrepareDataset (success, local, gpu-01, alice, 2025-01-02)
    - TrainModel with different params (running, submitit, gpu-02, bob, 2025-01-03)
    - EvalModel that depends on TrainModel (failed, local, gpu-02, alice, 2025-01-04)
    - DataLoader in different namespace (success, submitit, gpu-01, bob, 2024-06-01)
    - PrepareDataset with different params (absent, no attempt)
    """
    # Create a base dataset (successful, local, gpu-01, alice, early 2025)
    dataset1 = PrepareDataset(name="mnist", version="v1")
    create_experiment_from_huldra(
        dataset1,
        result_status="success",
        attempt_status="success",
        backend="local",
        hostname="gpu-01",
        user="alice",
        started_at="2025-01-01T10:00:00+00:00",
        updated_at="2025-01-01T11:00:00+00:00",
    )

    # Create a training run that depends on the dataset (successful, local, gpu-01, alice)
    train1 = TrainModel(lr=0.001, steps=1000, dataset=dataset1)
    create_experiment_from_huldra(
        train1,
        result_status="success",
        attempt_status="success",
        backend="local",
        hostname="gpu-01",
        user="alice",
        started_at="2025-01-02T10:00:00+00:00",
        updated_at="2025-01-02T11:00:00+00:00",
    )

    # Create another training run with different params (running, submitit, gpu-02, bob)
    train2 = TrainModel(lr=0.0001, steps=2000, dataset=dataset1)
    create_experiment_from_huldra(
        train2,
        result_status="incomplete",
        attempt_status="running",
        backend="submitit",
        hostname="gpu-02",
        user="bob",
        started_at="2025-01-03T10:00:00+00:00",
        updated_at="2025-01-03T11:00:00+00:00",
    )

    # Create an evaluation that depends on training (failed, local, gpu-02, alice)
    eval1 = EvalModel(model=train1, eval_split="test")
    create_experiment_from_huldra(
        eval1,
        result_status="failed",
        attempt_status="failed",
        backend="local",
        hostname="gpu-02",
        user="alice",
        started_at="2025-01-04T10:00:00+00:00",
        updated_at="2025-01-04T11:00:00+00:00",
    )

    # Create a data loader in a different namespace (successful, submitit, gpu-01, bob, 2024)
    loader = DataLoader(source="s3", format="parquet")
    create_experiment_from_huldra(
        loader,
        result_status="success",
        attempt_status="success",
        backend="submitit",
        hostname="gpu-01",
        user="bob",
        started_at="2024-06-01T10:00:00+00:00",
        updated_at="2024-06-01T11:00:00+00:00",
    )

    # Create another dataset with absent status (no attempt)
    dataset2 = PrepareDataset(name="cifar", version="v2")
    create_experiment_from_huldra(dataset2, result_status="absent", attempt_status=None)


@pytest.fixture(scope="module")
def populated_huldra_root(_configure_huldra_for_module: Path) -> Path:
    """Create a module-scoped Huldra root with sample experiments.

    PREFER THIS FIXTURE for read-only tests. Experiments are created once per
    module and reused, which is much faster than creating them per-test.

    See _create_populated_experiments() for the exact data created.
    """
    root = _configure_huldra_for_module
    _create_populated_experiments(root)
    return root


@pytest.fixture
def populated_with_dependencies(temp_huldra_root: Path) -> Path:
    """Create experiments with a full dependency chain.

    This fixture actually runs load_or_create() to create real experiments,
    so it must be function-scoped.

    This creates a realistic DAG:
    - dataset1 (PrepareDataset)
    - dataset2 (PrepareDataset)
    - train (TrainModel) depends on dataset1
    - eval (EvalModel) depends on train
    - multi (MultiDependencyPipeline) depends on dataset1 and dataset2
    """
    # Base datasets
    dataset1 = PrepareDataset(name="train_data", version="v1")
    dataset1.load_or_create()

    dataset2 = PrepareDataset(name="val_data", version="v1")
    dataset2.load_or_create()

    # Training depends on dataset1
    train = TrainModel(lr=0.001, steps=500, dataset=dataset1)
    train.load_or_create()

    # Evaluation depends on training
    eval_model = EvalModel(model=train, eval_split="validation")
    eval_model.load_or_create()

    # Multi-dependency pipeline
    multi = MultiDependencyPipeline(
        dataset1=dataset1, dataset2=dataset2, output_name="merged"
    )
    multi.load_or_create()

    return temp_huldra_root

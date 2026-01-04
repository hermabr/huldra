"""Tests for the Huldra experiment scanner."""

from pathlib import Path

from huldra.dashboard.scanner import (
    get_experiment_detail,
    get_stats,
    scan_experiments,
)

from .conftest import create_experiment


def test_scan_experiments_empty(temp_huldra_root: Path) -> None:
    """Test scanning when no experiments exist."""
    experiments = scan_experiments()
    assert experiments == []


def test_scan_experiments_finds_all(populated_huldra_root: Path) -> None:
    """Test that scanner finds all experiments."""
    experiments = scan_experiments()
    assert len(experiments) == 5


def test_scan_experiments_filter_result_status(populated_huldra_root: Path) -> None:
    """Test filtering by result status."""
    experiments = scan_experiments(result_status="success")
    assert len(experiments) == 2
    for exp in experiments:
        assert exp.result_status == "success"


def test_scan_experiments_filter_attempt_status(populated_huldra_root: Path) -> None:
    """Test filtering by attempt status."""
    experiments = scan_experiments(attempt_status="failed")
    assert len(experiments) == 1
    assert experiments[0].attempt_status == "failed"


def test_scan_experiments_filter_namespace(populated_huldra_root: Path) -> None:
    """Test filtering by namespace prefix."""
    experiments = scan_experiments(namespace_prefix="my_project")
    assert len(experiments) == 4
    for exp in experiments:
        assert exp.namespace.startswith("my_project")


def test_scan_experiments_sorted_by_updated_at(temp_huldra_root: Path) -> None:
    """Test that experiments are sorted by updated_at (newest first)."""
    # Create experiments with different timestamps
    create_experiment(
        temp_huldra_root,
        "test.Experiment",
        "older",
        result_status="success",
        attempt_status="success",
    )
    # Modify the state file to have an older timestamp
    older_state = (
        temp_huldra_root
        / "data"
        / "test"
        / "Experiment"
        / "older"
        / ".huldra"
        / "state.json"
    )
    import json

    state_data = json.loads(older_state.read_text())
    state_data["updated_at"] = "2024-01-01T00:00:00+00:00"
    older_state.write_text(json.dumps(state_data))

    create_experiment(
        temp_huldra_root,
        "test.Experiment",
        "newer",
        result_status="success",
        attempt_status="success",
    )
    newer_state = (
        temp_huldra_root
        / "data"
        / "test"
        / "Experiment"
        / "newer"
        / ".huldra"
        / "state.json"
    )
    state_data = json.loads(newer_state.read_text())
    state_data["updated_at"] = "2025-06-01T00:00:00+00:00"
    newer_state.write_text(json.dumps(state_data))

    experiments = scan_experiments()
    assert len(experiments) == 2
    # Newer should come first
    assert experiments[0].huldra_hash == "newer"
    assert experiments[1].huldra_hash == "older"


def test_get_experiment_detail_found(populated_huldra_root: Path) -> None:
    """Test getting detail for an existing experiment."""
    detail = get_experiment_detail("my_project.pipelines.TrainModel", "abc123def456")
    assert detail is not None
    assert detail.namespace == "my_project.pipelines.TrainModel"
    assert detail.huldra_hash == "abc123def456"
    assert detail.result_status == "success"
    assert detail.metadata is not None
    assert "state" in detail.model_dump()


def test_get_experiment_detail_not_found(populated_huldra_root: Path) -> None:
    """Test getting detail for a non-existent experiment."""
    detail = get_experiment_detail("nonexistent.Namespace", "fakehash")
    assert detail is None


def test_get_experiment_detail_includes_attempt(populated_huldra_root: Path) -> None:
    """Test that detail includes attempt information."""
    detail = get_experiment_detail("my_project.pipelines.TrainModel", "xyz789ghi012")
    assert detail is not None
    assert detail.attempt is not None
    assert detail.attempt.status == "running"
    assert detail.attempt.owner.host == "test-host"


def test_get_stats_empty(temp_huldra_root: Path) -> None:
    """Test stats with no experiments."""
    stats = get_stats()
    assert stats.total == 0
    assert stats.running_count == 0
    assert stats.success_count == 0


def test_get_stats_counts(populated_huldra_root: Path) -> None:
    """Test that stats correctly count experiments."""
    stats = get_stats()
    assert stats.total == 5
    assert stats.success_count == 2
    assert stats.failed_count == 1
    assert stats.running_count == 1

    # Check by_result_status
    result_map = {s.status: s.count for s in stats.by_result_status}
    assert result_map["success"] == 2
    assert result_map["failed"] == 1
    assert result_map["incomplete"] == 1
    assert result_map["absent"] == 1


def test_scan_experiments_version_controlled(temp_huldra_root: Path) -> None:
    """Test that scanner finds experiments in git/ subdirectory."""
    create_experiment(
        temp_huldra_root,
        "versioned.Model",
        "vchash123",
        result_status="success",
        version_controlled=True,
    )
    create_experiment(
        temp_huldra_root,
        "unversioned.Model",
        "uvhash456",
        result_status="success",
        version_controlled=False,
    )

    experiments = scan_experiments()
    assert len(experiments) == 2
    namespaces = {exp.namespace for exp in experiments}
    assert "versioned.Model" in namespaces
    assert "unversioned.Model" in namespaces


def test_experiment_summary_class_name(temp_huldra_root: Path) -> None:
    """Test that class_name is correctly extracted from namespace."""
    create_experiment(
        temp_huldra_root,
        "deep.nested.namespace.MyModel",
        "hash123",
        result_status="success",
    )

    experiments = scan_experiments()
    assert len(experiments) == 1
    assert experiments[0].class_name == "MyModel"

"""Pydantic models for the Dashboard API."""

from typing import Any # TODO: Remove the Any

from pydantic import BaseModel


class HealthCheck(BaseModel):
    """Health check response."""

    status: str
    version: str


class ExperimentOwner(BaseModel): # TODO: Is it possible to share this with the actual huldra library rather than defining the experiment owner both in huldra and in huldra/dashboard?
    """Owner information for an experiment attempt."""

    pid: int | None = None
    host: str | None = None
    hostname: str | None = None
    user: str | None = None
    command: str | None = None
    timestamp: str | None = None


class ExperimentAttempt(BaseModel):
    """Attempt information for an experiment."""

    id: str
    number: int
    backend: str
    status: str
    started_at: str
    heartbeat_at: str
    lease_expires_at: str
    owner: ExperimentOwner
    ended_at: str | None = None
    reason: str | None = None


class ExperimentSummary(BaseModel):
    """Summary of an experiment for list views."""

    namespace: str
    hexdigest: str
    class_name: str
    result_status: str
    attempt_status: str | None = None
    attempt_number: int | None = None
    updated_at: str | None = None
    started_at: str | None = None


class ExperimentDetail(ExperimentSummary):
    """Detailed experiment information."""

    directory: str
    state: dict[str, Any]
    metadata: dict[str, Any] | None = None
    attempt: ExperimentAttempt | None = None


class ExperimentList(BaseModel):
    """List of experiments with total count."""

    experiments: list[ExperimentSummary]
    total: int


class StatusCount(BaseModel):
    """Count of experiments by status."""

    status: str
    count: int


class DashboardStats(BaseModel):
    """Aggregate dashboard statistics."""

    total: int
    by_result_status: list[StatusCount]
    by_attempt_status: list[StatusCount]
    running_count: int
    queued_count: int
    failed_count: int
    success_count: int



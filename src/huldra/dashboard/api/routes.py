"""API route definitions for the Huldra Dashboard."""

from fastapi import APIRouter, HTTPException, Query

from .. import __version__
from ..scanner import scan_experiments, get_experiment_detail, get_stats
from .models import (
    DashboardStats,
    ExperimentDetail,
    ExperimentList,
    HealthCheck,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    return HealthCheck(status="healthy", version=__version__)


@router.get("/experiments", response_model=ExperimentList)
async def list_experiments(
    result_status: str | None = Query(None, description="Filter by result status"),
    attempt_status: str | None = Query(None, description="Filter by attempt status"),
    namespace: str | None = Query(None, description="Filter by namespace prefix"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ExperimentList:
    """List all experiments with optional filtering."""
    experiments = scan_experiments(
        result_status=result_status,
        attempt_status=attempt_status,
        namespace_prefix=namespace,
    )

    # Apply pagination
    total = len(experiments)
    experiments = experiments[offset : offset + limit]

    return ExperimentList(experiments=experiments, total=total)


@router.get("/experiments/{namespace:path}/{hexdigest}", response_model=ExperimentDetail)
async def get_experiment(namespace: str, hexdigest: str) -> ExperimentDetail:
    """Get detailed information about a specific experiment."""
    experiment = get_experiment_detail(namespace, hexdigest)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats() -> DashboardStats:
    """Get aggregate statistics for the dashboard."""
    return get_stats()



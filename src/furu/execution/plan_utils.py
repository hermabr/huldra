from __future__ import annotations

from .plan import DependencyPlan, reconcile_in_progress


def reconcile_or_timeout_in_progress(
    plan: DependencyPlan,
    *,
    stale_timeout_sec: float,
) -> bool:
    if not any(node.status == "IN_PROGRESS" for node in plan.nodes.values()):
        return False
    return reconcile_in_progress(plan, stale_timeout_sec=stale_timeout_sec)

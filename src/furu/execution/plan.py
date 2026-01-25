from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..config import FURU_CONFIG
from ..core import Furu
from ..runtime.logging import get_logger
from ..storage.state import (
    StateManager,
    _StateAttemptFailed,
    _StateAttemptQueued,
    _StateAttemptRunning,
    _StateResultFailed,
)

Status = Literal["DONE", "IN_PROGRESS", "TODO", "FAILED"]

_MISSING_TIMESTAMP_SEEN: dict[str, float] = {}


@dataclass
class PlanNode:
    obj: Furu
    status: Status
    spec_key: str
    deps_all: set[str]
    deps_pending: set[str]
    dependents: set[str]


@dataclass
class DependencyPlan:
    roots: list[Furu]
    nodes: dict[str, PlanNode]


def _classify(obj: Furu, completed_hashes: set[str] | None) -> Status:
    if completed_hashes is not None and obj.furu_hash in completed_hashes:
        return "DONE"
    if obj._exists_quiet() and not obj._always_rerun():
        return "DONE"

    state = obj.get_state()
    attempt = state.attempt
    if isinstance(attempt, (_StateAttemptQueued, _StateAttemptRunning)):
        return "IN_PROGRESS"
    if isinstance(state.result, _StateResultFailed) or isinstance(
        attempt, _StateAttemptFailed
    ):
        if FURU_CONFIG.retry_failed:
            return "TODO"
        return "FAILED"
    return "TODO"


def build_plan(
    roots: list[Furu],
    *,
    completed_hashes: set[str] | None = None,
) -> DependencyPlan:
    nodes: dict[str, PlanNode] = {}
    stack = list(roots)
    seen: set[str] = set()

    while stack:
        obj = stack.pop()
        digest = obj.furu_hash
        if digest in seen:
            continue
        seen.add(digest)

        status = _classify(obj, completed_hashes)
        node = PlanNode(
            obj=obj,
            status=status,
            spec_key=obj._executor_spec_key(),
            deps_all=set(),
            deps_pending=set(),
            dependents=set(),
        )
        nodes[digest] = node

        if status != "TODO":
            continue

        deps = obj._get_dependencies(recursive=False)
        node.deps_all = {dep.furu_hash for dep in deps}
        for dep in deps:
            stack.append(dep)

    for digest, node in nodes.items():
        if node.status != "TODO":
            continue
        node.deps_pending = {
            dep for dep in node.deps_all if dep in nodes and nodes[dep].status != "DONE"
        }

    for digest, node in nodes.items():
        for dep in node.deps_pending:
            nodes[dep].dependents.add(digest)

    return DependencyPlan(roots=roots, nodes=nodes)


def topo_order_todo(plan: DependencyPlan) -> list[str]:
    todo = {digest for digest, node in plan.nodes.items() if node.status == "TODO"}
    indeg = {digest: 0 for digest in todo}

    for digest in todo:
        node = plan.nodes[digest]
        for dep in node.deps_pending:
            if dep in todo:
                indeg[digest] += 1

    ready = sorted([digest for digest, deg in indeg.items() if deg == 0])
    out: list[str] = []

    while ready:
        digest = ready.pop(0)
        out.append(digest)
        for dep in plan.nodes[digest].dependents:
            if dep not in todo:
                continue
            indeg[dep] -= 1
            if indeg[dep] == 0:
                ready.append(dep)
                ready.sort()

    if len(out) != len(todo):
        raise ValueError("Cycle detected in TODO dependency graph")
    return out


def ready_todo(plan: DependencyPlan) -> list[str]:
    return sorted(
        [
            digest
            for digest, node in plan.nodes.items()
            if node.status == "TODO"
            and all(plan.nodes[dep].status == "DONE" for dep in node.deps_pending)
        ]
    )


def _attempt_age_sec(
    attempt: _StateAttemptQueued | _StateAttemptRunning,
    *,
    updated_at: str | None,
    stale_timeout_sec: float,
    digest: str,
    name: str,
) -> float | None:
    timestamp = attempt.heartbeat_at
    if attempt.status == "queued":
        timestamp = attempt.started_at
    parsed = StateManager._parse_time(timestamp)
    if parsed is None:
        parsed = StateManager._parse_time(updated_at)
    if parsed is not None:
        _MISSING_TIMESTAMP_SEEN.pop(digest, None)
        return (StateManager._utcnow() - parsed).total_seconds()
    if stale_timeout_sec <= 0:
        return None
    now = StateManager._utcnow().timestamp()
    first_seen = _MISSING_TIMESTAMP_SEEN.get(digest)
    if first_seen is None:
        _MISSING_TIMESTAMP_SEEN[digest] = now
        logger = get_logger()
        logger.warning(
            "IN_PROGRESS attempt missing heartbeat/started timestamps for %s; "
            "deferring stale timeout check.",
            name,
        )
        return None
    return now - first_seen


def reconcile_in_progress(
    plan: DependencyPlan,
    *,
    stale_timeout_sec: float,
) -> bool:
    stale_attempts: list[
        tuple[PlanNode, _StateAttemptQueued | _StateAttemptRunning]
    ] = []
    for node in plan.nodes.values():
        if node.status != "IN_PROGRESS":
            _MISSING_TIMESTAMP_SEEN.pop(node.obj.furu_hash, None)
            continue
        state = StateManager.reconcile(node.obj._base_furu_dir())
        attempt = state.attempt
        if not isinstance(attempt, (_StateAttemptQueued, _StateAttemptRunning)):
            _MISSING_TIMESTAMP_SEEN.pop(node.obj.furu_hash, None)
            continue
        if stale_timeout_sec <= 0:
            continue
        name = f"{node.obj.__class__.__name__}({node.obj.furu_hash})"
        age = _attempt_age_sec(
            attempt,
            updated_at=state.updated_at,
            stale_timeout_sec=stale_timeout_sec,
            digest=node.obj.furu_hash,
            name=name,
        )
        if age is None or age < stale_timeout_sec:
            continue
        stale_attempts.append((node, attempt))

    if not stale_attempts:
        return False

    names = ", ".join(
        f"{node.obj.__class__.__name__}({node.obj.furu_hash})"
        for node, _attempt in stale_attempts
    )
    if not FURU_CONFIG.retry_failed:
        raise RuntimeError(
            "Stale IN_PROGRESS dependencies detected: "
            f"{names} exceeded {stale_timeout_sec:.1f}s without heartbeat."
        )

    stale_detected = False
    for node, attempt in stale_attempts:
        stale_detected = True
        StateManager.finish_attempt_preempted(
            node.obj._base_furu_dir(),
            attempt_id=attempt.id,
            error={
                "type": "StaleHeartbeat",
                "message": (
                    f"Attempt stale after {stale_timeout_sec:.1f}s without heartbeat."
                ),
            },
            reason="stale_timeout",
        )
        _MISSING_TIMESTAMP_SEEN.pop(node.obj.furu_hash, None)
    return stale_detected

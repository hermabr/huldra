# Executor Planning Notes

## Context and Problem Statement
Furu is a cached computation framework where `Furu` objects represent reproducible
artifacts. Dependencies are derived from config fields plus an optional
`_dependencies()` hook. We want to build a dependency execution plan for a root
`Furu` object that:

- Walks fields and `_dependencies()` to discover dependencies.
- Distinguishes **completed** nodes (`exists() == True`) from **pending** nodes.
- Skips traversal into completed nodes (their dependencies are irrelevant).
- Enables parallel execution without rigid layer barriers.
- Supports both local execution (threads/processes) and Slurm/submitit execution.
- Optionally supports batching multiple small tasks into a single Slurm job.

The design should be flexible enough for a senior engineer to choose exact
structures and optimizations. The snippets below are **sketches only**; if better
structures exist, we should strongly consider them.

## Current State
- Dependency discovery is private: `_get_dependencies(recursive=True)` exists.
- Direct dependencies are included in the Furu hash via `_dependency_hashes()`
  (non-recursive, de-duplicated by `_furu_hash`).
- Dependencies are not recorded in metadata.
- `load_or_create()` supports local and submitit execution.

## Stage 1: Dependency Overview (Suggested Shape)

Goal: produce a compact graph-like overview that captures both dependencies and
dependents for pending nodes, plus the completed nodes.

```python
@dataclass
class DependencyNode:
    obj: Furu
    dependencies: set[str]   # direct deps (pending + completed)
    dependents: set[str]     # pending dependents only

@dataclass
class DependencyOverview:
    root: Furu
    pending: dict[str, DependencyNode]   # hash -> node (needs work)
    completed: dict[str, Furu]           # hash -> obj (exists() == True)
```

Behavioral rules:
- Traverse only direct deps (fields + `_dependencies()`).
- If `exists()` is True: add to `completed`, do not traverse further.
- If pending: add to `pending`, record its direct dependency hashes.
- Build `dependents` only among pending nodes.

This structure avoids layer barriers and gives Stage 2 full flexibility.

## Stage 2: Execution Sketches

These are **sketches/ideas only**; a senior engineer should refine them.

### Local executor (dynamic ready queue)
```python
ready = deque(
    node.obj for node in overview.pending.values()
    if all(dep not in overview.pending for dep in node.dependencies)
)

running: dict[Future, str] = {}

with ThreadPoolExecutor(max_workers=max_workers) as pool:
    while ready or running:
        while ready and len(running) < max_workers:
            obj = ready.popleft()
            fut = pool.submit(obj.load_or_create)
            running[fut] = obj._furu_hash

        done, _ = wait(running, return_when=FIRST_COMPLETED)
        for fut in done:
            hash_ = running.pop(fut)
            fut.result()
            for dep_hash in overview.pending[hash_].dependents:
                dep_node = overview.pending[dep_hash]
                if all(d not in overview.pending or d == hash_ for d in dep_node.dependencies):
                    ready.append(dep_node.obj)
```

### Slurm/submitit executor (submit everything immediately)
```python
jobs: dict[str, submitit.Job] = {}

for hash_ in topo_order(overview.pending):
    node = overview.pending[hash_]
    dep_job_ids = [jobs[d].job_id for d in node.dependencies if d in jobs]

    # executor.update_parameters(dependency=f"afterok:{':'.join(dep_job_ids)}")
    job = node.obj.load_or_create(executor)
    jobs[hash_] = job
```

This uses Slurm dependencies to enforce ordering and avoids a runtime scheduler
loop, while still preserving correctness.

## Optional: Slurm batching

Two batching modes are desired:

1. **Batch by exact type**: group only same class (safe for resource profiles).
2. **Chain compression**: merge strict A -> B chains into single batches.

Batch plan sketch (idea only):
```python
@dataclass
class Batch:
    id: str
    members: list[Furu]          # topo order within batch
    dependencies: set[str]       # batch dependencies

@dataclass
class BatchPlan:
    batches: dict[str, Batch]
```

Execution: submit each batch as one Slurm job, with dependencies between batches.
Inside the job, run `load_or_create()` sequentially (or optionally with a small
local pool).

## Open Decisions for Senior Engineer
- Exact Stage 1 API shape (split `pending/completed` vs unified `nodes` map).
- Whether to expose helper methods (e.g., `ready()/mark_done()`), or keep Stage 2
  scheduling logic external.
- Whether batching should be opt-in and how it should be configured.
- Whether to add resource/batch hints on `Furu` (e.g., `_batch_key()` or
  `_slurm_profile()`).
- Whether completed nodes should include root when `exists() == True` (recommended).

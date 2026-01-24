# plans/executor.md — Furu Executors v1 (overview)

> **Read this first.** This file is the high-level overview of the executor work.
> Implementation details and checklists live in `plans/executor-plan/*.md`.

## What we’re building

We are adding an execution system that supports:

- A single public API: **`Furu.get()`** (remove `load_or_create` entirely).
- A dependency planner that can present **pending/completed/blocked/in-progress/failed** DAG state.
- A **local parallel executor** (threads) that runs a DAG locally.
- A **Slurm executor** with two modes:
  1. **Per-node DAG submission** (one Slurm job per node) wired via Slurm `afterok` dependencies.
  2. **Worker-pool (“mass-parallel”)** mode (workers pull tasks from a filesystem queue and run many nodes sequentially).

The design enforces a critical invariant:

- In **interactive** usage, `obj.get()` computes missing nodes (and may recursively compute dependencies).
- In **executor contexts** (local-parallel workers and Slurm workers/jobs), `obj.get()` is **strict load-only**:
  - exists → load
  - missing → raise `FuruMissingArtifact`
  - escape hatch: `obj.get(force=True)` is allowed **only** if the object’s **spec key** exactly matches the current worker’s spec key (v1 exact match).

This guarantees mixed resource requirements are scheduled correctly: a GPU task cannot accidentally compute a CPU dependency inside a GPU job.

## Spec keys and “default”

Each node declares a **spec key** string via `Furu._executor_spec_key()`.

- Default spec key is **`"default"`** (not `"cpu"`).
- Executors accept a `specs: dict[str, SlurmSpec]` mapping and interpret `"default"` at runtime:
  - `specs["default"]` defines what `"default"` means on the cluster.

Example:

```py
specs = {
    "default": SlurmSpec(partition="cpu", cpus=8, mem_gb=32, time_min=120),
    "gpu":     SlurmSpec(partition="gpu", gpus=1, cpus=8, mem_gb=64, time_min=720),
}
```

## Submitit log placement

Default logs root:

- `<FURU_PATH>/submitit` (sibling of `<FURU_PATH>/data`)

Override via env var:

- `FURU_SUBMITIT_PATH=/path/to/submitit`

Layout:

- per-node jobs: `<submitit_root>/nodes/<spec_key>/...`
- pool workers: `<submitit_root>/workers/<spec_key>/...`

## File map (what to read next)

Implementation is split into subplans:

- `plans/executor-plan/00-index.md` — global tracking + recommended order
- `plans/executor-plan/01-core-get.md` — remove `load_or_create`, implement `get`
- `plans/executor-plan/02-exec-context.md` — executor context via `contextvars`
- `plans/executor-plan/03-specs-and-slurmspec.md` — spec keys `"default"` and executor-provided `specs` mapping
- `plans/executor-plan/04-submitit-paths.md` — submitit root config + folder layout
- `plans/executor-plan/05-submitit-jobid-race.md` — fix job-id watcher race
- `plans/executor-plan/06-planner.md` — dependency plan DAG + statuses + topo/ready helpers
- `plans/executor-plan/07-local-executor.md` — `run_local(...)`
- `plans/executor-plan/08-slurm-dag.md` — `submit_slurm_dag(...)` per-node `afterok`
- `plans/executor-plan/09-slurm-pool.md` — `run_slurm_pool(...)` filesystem queue
- `plans/executor-plan/10-logging.md` — rename logging prefix to `"get"`
- `plans/executor-plan/11-repo-migration.md` — mechanical renames + docs/examples
- `plans/executor-plan/12-tests.md` — test plan (structure + what to add)

## How to update plans as you implement

This repo uses the plan files as living tracking docs.

- In each subplan, tick checkboxes `[ ] → [x]` as work is completed.
- If partially complete, use `[~]` and add a short note.
- Append short entries to each subplan’s **Progress Log** with date `YYYY-MM-DD` format.
- Record any deviations in the subplan’s **Plan Changes** table.

## Acceptance criteria (v1)

- `load_or_create` is removed; all code uses `.get()`.
- In executor contexts, dependencies cannot compute accidentally; missing dep `.get()` raises.
- Mixed specs across dependencies work:
  - CPU-like deps under `"default"`, GPU tasks under `"gpu"`, etc.
  - GPU tasks do not compute `"default"` deps inside GPU worker.
- Submitit logs root default is `<FURU_PATH>/submitit` and override works.
- Slurm per-node DAG uses `afterok` dependencies with correct job_id recording.
- Worker-pool mode can run many nodes per worker and respects global worker cap.

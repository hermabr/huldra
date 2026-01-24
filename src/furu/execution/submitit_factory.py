from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .paths import submitit_logs_dir
from .slurm_spec import SlurmSpec, SlurmSpecExtraValue

if TYPE_CHECKING:
    import submitit



def make_executor_for_spec(
    spec_key: str,
    spec: SlurmSpec,
    *,
    kind: str,
    submitit_root: Path | None,
    run_id: str | None = None,
) -> submitit.AutoExecutor:
    import submitit

    folder = submitit_logs_dir(
        kind,
        spec_key,
        override=submitit_root,
        run_id=run_id,
    )
    folder.mkdir(parents=True, exist_ok=True)

    executor = submitit.AutoExecutor(folder=str(folder))
    params: dict[str, SlurmSpecExtraValue | None] = {
        "timeout_min": spec.time_min,
        "slurm_partition": spec.partition,
        "cpus_per_task": spec.cpus,
        "mem_gb": spec.mem_gb,
    }
    if spec.gpus:
        params["gpus_per_node"] = spec.gpus
    if spec.extra:
        params.update(spec.extra)

    executor.update_parameters(
        **{key: value for key, value in params.items() if value is not None}
    )
    return executor

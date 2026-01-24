from pathlib import Path

from furu.config import FURU_CONFIG


def submitit_root_dir(override: Path | None = None) -> Path:
    return (override or FURU_CONFIG.get_submitit_root()).resolve()


def submitit_logs_dir(
    kind: str,
    spec_key: str,
    override: Path | None = None,
    run_id: str | None = None,
) -> Path:
    root = submitit_root_dir(override)
    path = root / kind / spec_key
    if run_id:
        path = path / run_id
    return path

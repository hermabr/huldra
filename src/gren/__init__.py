"""
Gren: cacheable, nested pipelines as config objects.

This package uses a src-layout. Import the package as `gren`.
"""

from importlib.metadata import version

import chz
import submitit

__version__ = version("gren")

from .config import GREN_CONFIG, GrenConfig, get_gren_root, set_gren_root
from .adapters import SubmititAdapter
from .core import Gren, GrenList
from .errors import (
    GrenComputeError,
    GrenError,
    GrenLockNotAcquired,
    GrenMigrationRequired,
    GrenWaitTimeout,
    MISSING,
)
from .runtime import (
    configure_logging,
    current_holder,
    current_log_dir,
    enter_holder,
    get_logger,
    load_env,
    log,
    write_separator,
)
from .migrate import migrate
from .serialization import GrenSerializer
from .storage import MetadataManager, StateManager

__all__ = [
    "__version__",
    "GREN_CONFIG",
    "Gren",
    "GrenComputeError",
    "GrenConfig",
    "GrenError",
    "GrenList",
    "GrenLockNotAcquired",
    "GrenMigrationRequired",
    "GrenSerializer",
    "GrenWaitTimeout",
    "MISSING",
    "migrate",
    "MetadataManager",
    "StateManager",
    "SubmititAdapter",
    "chz",
    "configure_logging",
    "current_holder",
    "current_log_dir",
    "enter_holder",
    "get_gren_root",
    "get_logger",
    "load_env",
    "log",
    "write_separator",
    "set_gren_root",
    "submitit",
]

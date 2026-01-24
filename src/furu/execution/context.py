from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal

Backend = Literal["local", "submitit"]


@dataclass(frozen=True)
class ExecContext:
    mode: Literal["interactive", "executor"]
    spec_key: str | None = None
    backend: Backend | None = None
    current_node_hash: str | None = None


EXEC_CONTEXT: ContextVar[ExecContext] = ContextVar(
    "FURU_EXEC_CONTEXT",
    default=ExecContext(
        mode="interactive",
        spec_key=None,
        backend=None,
        current_node_hash=None,
    ),
)


def in_executor() -> bool:
    return EXEC_CONTEXT.get().mode == "executor"

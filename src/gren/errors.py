import traceback
from pathlib import Path


class _GrenMissing:
    """Sentinel value for missing fields."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "Gren.MISSING"


MISSING = _GrenMissing()


class GrenError(Exception):
    """Base exception for Gren errors."""

    pass


class GrenWaitTimeout(GrenError):
    """Raised when waiting for a result exceeds _max_wait_time_sec."""

    pass


class GrenLockNotAcquired(GrenError):
    """Raised when a compute lock cannot be acquired (someone else holds it)."""

    pass


class GrenComputeError(GrenError):
    """Raised when computation fails."""

    def __init__(
        self,
        message: str,
        state_path: Path,
        original_error: Exception | None = None,
    ):
        self.state_path = state_path
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        msg = super().__str__()  # ty: ignore[invalid-super-argument]
        if self.original_error:
            msg += f"\n\nOriginal error: {self.original_error}"
            if hasattr(self.original_error, "__traceback__"):
                tb = "".join(
                    traceback.format_exception(
                        type(self.original_error),
                        self.original_error,
                        self.original_error.__traceback__,
                    )
                )
                msg += f"\n\nTraceback:\n{tb}"
        msg += f"\n\nState file: {self.state_path}"
        return msg


class GrenMigrationRequired(GrenError):
    """Raised when a migrated object requires explicit migration."""

    def __init__(self, message: str, *, state_path: Path | None = None):
        self.state_path = state_path
        super().__init__(message)

    def __str__(self) -> str:
        msg = super().__str__()  # ty: ignore[invalid-super-argument]
        if self.state_path is not None:
            msg += f"\n\nState file: {self.state_path}"
        return msg

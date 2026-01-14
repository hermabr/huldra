import contextlib
import contextvars
import datetime
import logging
import os
import threading
from pathlib import Path
from typing import Generator, Protocol

from rich.text import Text

from ..config import GREN_CONFIG


class _HolderProtocol(Protocol):
    """Protocol for objects that can be used as logging context holders."""

    @property
    def gren_dir(self) -> Path: ...


# A holder is either a Path directly or an object with a gren_dir attribute
HolderType = Path | _HolderProtocol

_GREN_HOLDER_STACK: contextvars.ContextVar[tuple[HolderType, ...]] = (
    contextvars.ContextVar("gren_holder_stack", default=())
)
_GREN_LOG_LOCK = threading.Lock()
_GREN_CONSOLE_LOCK = threading.Lock()

_LOAD_OR_CREATE_PREFIX = "load_or_create"


def _strip_load_or_create_decision_suffix(message: str) -> str:
    """
    Strip a trailing `(<decision>)` suffix from `load_or_create ...` console lines.

    This keeps detailed decision info in file logs, but makes console output cleaner.
    """
    if not message.startswith(_LOAD_OR_CREATE_PREFIX):
        return message
    if not message.endswith(")"):
        return message
    idx = message.rfind(" (")
    if idx == -1:
        return message

    decision = message[idx + 2 : -1]
    if decision == "create" or "->" in decision:
        return message[:idx]
    return message


def _holder_to_log_dir(holder: HolderType) -> Path:
    if isinstance(holder, Path):
        base_dir = holder
    else:
        directory = getattr(holder, "gren_dir", None)
        if not isinstance(directory, Path):
            raise TypeError(
                "holder must be a pathlib.Path or have a .gren_dir: pathlib.Path attribute"
            )
        base_dir = directory
    return base_dir / ".gren"


@contextlib.contextmanager
def enter_holder(holder: HolderType) -> Generator[None, None, None]:
    """
    Push a holder object onto the logging stack for this context.

    Gren calls this automatically during `load_or_create()`, so nested
    dependencies will log to the active dependency's folder and then revert.
    """
    configure_logging()
    stack = _GREN_HOLDER_STACK.get()
    token = _GREN_HOLDER_STACK.set((*stack, holder))
    try:
        yield
    finally:
        _GREN_HOLDER_STACK.reset(token)


def current_holder() -> HolderType | None:
    """Return the current holder object for logging, if any."""
    stack = _GREN_HOLDER_STACK.get()
    return stack[-1] if stack else None


def current_log_dir() -> Path:
    """Return the directory logs should be written to for this context."""
    holder = current_holder()
    if holder is None:
        return GREN_CONFIG.base_root
    return _holder_to_log_dir(holder)


class _GrenLogFormatter(logging.Formatter):
    def formatTime(  # noqa: N802 - keep logging.Formatter API
        self, record: logging.LogRecord, datefmt: str | None = None
    ) -> str:
        dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
        return dt.isoformat(timespec="seconds")


class _GrenContextFileHandler(logging.Handler):
    """
    A logging handler that writes to `current_log_dir() / "gren.log"` at emit-time.
    """

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)

        directory = current_log_dir()
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / "gren.log"
        with _GREN_LOG_LOCK:
            with log_path.open("a", encoding="utf-8") as fp:
                fp.write(f"{message}\n")


class _GrenScopeFilter(logging.Filter):
    """
    Capture all logs while inside a holder context.

    Outside a holder context, only capture logs from the `gren` logger namespace.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if current_holder() is not None:
            return True
        return record.name == "gren" or record.name.startswith("gren.")


class _GrenFileFilter(logging.Filter):
    """Filter out records intended for console only."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not bool(getattr(record, "gren_console_only", False))


class _GrenConsoleFilter(logging.Filter):
    """Only show gren namespace logs on console."""

    def filter(self, record: logging.LogRecord) -> bool:
        if bool(getattr(record, "gren_file_only", False)):
            return False
        return record.name == "gren" or record.name.startswith("gren.")


def _console_level() -> int:
    level = os.getenv("GREN_LOG_LEVEL", "INFO").upper()
    return logging.getLevelNamesMapping().get(level, logging.INFO)


class _GrenRichConsoleHandler(logging.Handler):
    def __init__(self, *, level: int) -> None:
        super().__init__(level=level)
        from rich.console import Console  # type: ignore

        self._console = Console(stderr=True)

    @staticmethod
    def _format_location(record: logging.LogRecord) -> str:
        # Use caller location if available (for load_or_create messages)
        caller_file = getattr(record, "gren_caller_file", None)
        caller_line = getattr(record, "gren_caller_line", None)
        if caller_file is not None and caller_line is not None:
            filename = Path(caller_file).name
            return f"[{filename}:{caller_line}]"
        filename = Path(record.pathname).name if record.pathname else "<unknown>"
        return f"[{filename}:{record.lineno}]"

    @staticmethod
    def _format_message_text(record: logging.LogRecord) -> Text:
        message = _strip_load_or_create_decision_suffix(record.getMessage())
        action_color = getattr(record, "gren_action_color", None)
        if isinstance(action_color, str) and message.startswith(_LOAD_OR_CREATE_PREFIX):
            prefix = _LOAD_OR_CREATE_PREFIX
            rest = message[len(prefix) :]
            text = Text()
            text.append(prefix, style=action_color)
            text.append(rest)
            return text
        return Text(message)

    def emit(self, record: logging.LogRecord) -> None:
        level_style = self._level_style(record.levelno)
        timestamp = datetime.datetime.fromtimestamp(
            record.created, tz=datetime.timezone.utc
        ).strftime("%H:%M:%S")

        location = self._format_location(record)

        line = Text()
        line.append(timestamp, style="dim")
        line.append(" ")
        line.append(location, style=level_style)
        line.append(" ")
        line.append_text(self._format_message_text(record))

        with _GREN_CONSOLE_LOCK:
            self._console.print(line)

        if record.exc_info:
            from rich.traceback import Traceback  # type: ignore

            exc_type, exc_value, tb = record.exc_info
            if exc_type is not None and exc_value is not None and tb is not None:
                with _GREN_CONSOLE_LOCK:
                    self._console.print(
                        Traceback.from_exception(
                            exc_type, exc_value, tb, show_locals=False
                        )
                    )

    @staticmethod
    def _level_style(levelno: int) -> str:
        if levelno >= logging.ERROR:
            return "red"
        if levelno >= logging.WARNING:
            return "yellow"
        if levelno >= logging.INFO:
            return "blue"
        return "magenta"


def configure_logging() -> None:
    """
    Install context-aware file logging + rich console logging (idempotent).

    With this installed, any stdlib logger (e.g. `logging.getLogger(__name__)`)
    that propagates to the root logger will be written to the current holder's
    `gren.log` while a holder is active.
    """
    root = logging.getLogger()
    if not any(isinstance(h, _GrenContextFileHandler) for h in root.handlers):
        handler = _GrenContextFileHandler(level=logging.DEBUG)
        handler.addFilter(_GrenScopeFilter())
        handler.addFilter(_GrenFileFilter())
        handler.setFormatter(
            _GrenLogFormatter(
                "%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d %(message)s"
            )
        )
        root.addHandler(handler)

    if not any(isinstance(h, _GrenRichConsoleHandler) for h in root.handlers):
        console = _GrenRichConsoleHandler(level=_console_level())
        console.addFilter(_GrenConsoleFilter())
        root.addHandler(console)


def get_logger() -> logging.Logger:
    """
    Return the default gren logger.

    It is configured with a context-aware file handler that routes log records to
    the current holder's directory (see `enter_holder()`).
    """
    configure_logging()
    logger = logging.getLogger("gren")
    logger.setLevel(logging.DEBUG)
    return logger


def log(message: str, *, level: str = "INFO") -> Path:
    """
    Log a message to the current holder's `gren.log` via stdlib `logging`.

    If no holder is active, logs to `GREN_CONFIG.base_root / "gren.log"`.
    Returns the path written to.
    """
    directory = current_log_dir()
    log_path = directory / "gren.log"

    level_no = logging.getLevelNamesMapping().get(level.upper())
    if level_no is None:
        raise ValueError(f"Unknown log level: {level!r}")

    configure_logging()
    get_logger().log(level_no, message)
    return log_path


def write_separator(line: str = "------------------") -> Path:
    """
    Write a raw separator line to the current holder's `gren.log`.

    This bypasses standard formatting so repeated `load_or_create()` calls are easy to spot.
    """
    directory = current_log_dir()
    log_path = directory / "gren.log"

    directory.mkdir(parents=True, exist_ok=True)

    with _GREN_LOG_LOCK:
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(f"{line}\n")
    return log_path

import json
import logging

import pytest

import gren
from gren.runtime.logging import _GrenRichConsoleHandler


class InternetContent(gren.Gren[int]):
    def _create(self) -> int:
        logging.getLogger("internet").info("internet:download")
        (self.gren_dir / "value.json").write_text(json.dumps(1))
        return 1

    def _load(self) -> int:
        return json.loads((self.gren_dir / "value.json").read_text())


class Video(gren.Gren[int]):
    content: InternetContent = gren.chz.field(default_factory=InternetContent)

    def _create(self) -> int:
        logging.getLogger("video").info("video:before")
        self.content.load_or_create()
        logging.getLogger("video").info("video:after")
        (self.gren_dir / "value.json").write_text(json.dumps(2))
        return 2

    def _load(self) -> int:
        return json.loads((self.gren_dir / "value.json").read_text())


class SeparatorItem(gren.Gren[int]):
    def _create(self) -> int:
        (self.gren_dir / "value.json").write_text(json.dumps(1))
        return 1

    def _load(self) -> int:
        return json.loads((self.gren_dir / "value.json").read_text())


def test_log_routes_to_current_holder_dir(gren_tmp_root) -> None:
    logging.getLogger("video").setLevel(logging.INFO)
    logging.getLogger("internet").setLevel(logging.INFO)

    obj = Video()
    obj.load_or_create()

    video_log = (obj.gren_dir / ".gren" / "gren.log").read_text()
    assert "[DEBUG]" in video_log
    assert "video:before" in video_log
    assert "video:after" in video_log
    assert "internet:download" not in video_log
    assert (
        f"dep: begin {obj.content.__class__.__name__} {obj.content._gren_hash}"
        in video_log
    )
    assert (
        f"dep: end {obj.content.__class__.__name__} {obj.content._gren_hash} (ok)"
        in video_log
    )
    assert video_log.index("video:before") < video_log.index("video:after")

    content_log = (obj.content.gren_dir / ".gren" / "gren.log").read_text()
    assert "[DEBUG]" in content_log
    assert "internet:download" in content_log
    assert "video:before" not in content_log
    assert "video:after" not in content_log


def test_log_without_holder_defaults_to_base_root(gren_tmp_root) -> None:
    log_path = gren.log("no-holder")
    assert log_path == gren.GREN_CONFIG.base_root / "gren.log"
    assert "no-holder" in log_path.read_text()


def test_configure_logging_rich_handler_is_idempotent(gren_tmp_root) -> None:
    root = logging.getLogger()
    before = sum(isinstance(h, _GrenRichConsoleHandler) for h in root.handlers)

    gren.configure_logging()
    after = sum(isinstance(h, _GrenRichConsoleHandler) for h in root.handlers)
    gren.configure_logging()
    after2 = sum(isinstance(h, _GrenRichConsoleHandler) for h in root.handlers)

    assert after >= before
    assert after2 == after


def test_load_or_create_does_not_log_on_cache_hit(
    gren_tmp_root,
) -> None:
    obj = SeparatorItem()
    obj.load_or_create()
    obj.load_or_create()

    text = (obj.gren_dir / ".gren" / "gren.log").read_text()
    assert text.count("------------------") == 1
    assert text.count("load_or_create ") == 1
    assert f"load_or_create {obj.__class__.__name__} {obj._gren_hash}" in text
    assert str(obj.gren_dir) in text
    assert text.count("_create: ok ") == 1


def test_rich_console_colors_only_load_or_create_token() -> None:
    pytest.importorskip("rich")

    record = logging.LogRecord(
        name="gren",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="load_or_create Foo 123 /tmp (success->load)",
        args=(),
        exc_info=None,
    )
    record.gren_action_color = "green"  # type: ignore[attr-defined]

    text = _GrenRichConsoleHandler._format_message_text(record)
    assert text.plain == "load_or_create Foo 123 /tmp"
    assert len(text.spans) == 1
    span = text.spans[0]
    assert span.start == 0
    assert span.end == len("load_or_create")
    assert str(span.style) == "green"


def test_rich_console_wraps_location_in_brackets() -> None:
    pytest.importorskip("rich")

    record = logging.LogRecord(
        name="gren",
        level=logging.INFO,
        pathname=__file__,
        lineno=123,
        msg="hello",
        args=(),
        exc_info=None,
    )
    assert _GrenRichConsoleHandler._format_location(record) == "[test_logger.py:123]"

import json

import pytest

import gren
from gren.storage.state import _StateResultFailed, _StateResultSuccess


class Fails(gren.Gren[int]):
    def _create(self) -> int:
        raise RuntimeError("boom")

    def _load(self) -> int:
        return json.loads((self.gren_dir / "never.json").read_text())


def test_failed_create_raises_compute_error_and_records_state(gren_tmp_root) -> None:
    obj = Fails()
    with pytest.raises(RuntimeError, match="boom"):
        obj.load_or_create()

    log_text = (obj.gren_dir / ".gren" / "gren.log").read_text()
    assert "[ERROR]" in log_text
    assert "_create failed" in log_text
    assert "Traceback (most recent call last)" in log_text
    assert "RuntimeError: boom" in log_text

    state = gren.StateManager.read_state(obj.gren_dir)
    assert isinstance(state.result, _StateResultFailed)
    attempt = state.attempt
    assert attempt is not None
    assert attempt.status == "failed"
    error = getattr(attempt, "error", None)
    assert error is not None
    assert "boom" in error.message
    assert error.traceback is not None


class InvalidValidate(gren.Gren[int]):
    def _create(self) -> int:
        (self.gren_dir / "value.json").write_text(json.dumps(1))
        return 1

    def _load(self) -> int:
        return 1

    def _validate(self) -> bool:
        raise RuntimeError("validate error")


def test_exists_raises_if_validate_throws(gren_tmp_root) -> None:
    obj = InvalidValidate()
    obj.load_or_create()
    with pytest.raises(RuntimeError, match="validate error"):
        obj.exists()


class ValidateReturnsFalse(gren.Gren[int]):
    def _create(self) -> int:
        (self.gren_dir / "value.json").write_text(json.dumps(1))
        return 1

    def _load(self) -> int:
        raise AssertionError("_load should not be called when _validate returns False")

    def _validate(self) -> bool:
        (self.gren_dir / "validated.txt").write_text("1")
        return False


def test_load_or_create_recomputes_if_validate_returns_false(gren_tmp_root) -> None:
    obj = ValidateReturnsFalse()
    obj.gren_dir.mkdir(parents=True, exist_ok=True)

    def mutate(state) -> None:
        state.result = _StateResultSuccess(status="success", created_at="x")
        state.attempt = None

    gren.StateManager.update_state(obj.gren_dir, mutate)
    gren.StateManager.write_success_marker(obj.gren_dir, attempt_id="test")

    assert obj.load_or_create() == 1
    assert (obj.gren_dir / "validated.txt").exists()

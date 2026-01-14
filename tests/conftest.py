import sys
from pathlib import Path

import pytest


# Make `import gren` work in a src-layout checkout without requiring an install.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture()
def gren_tmp_root(tmp_path, monkeypatch):
    import gren

    monkeypatch.setattr(gren.GREN_CONFIG, "base_root", tmp_path)
    monkeypatch.setattr(gren.GREN_CONFIG, "ignore_git_diff", True)
    monkeypatch.setattr(gren.GREN_CONFIG, "poll_interval", 0.01)
    monkeypatch.setattr(gren.GREN_CONFIG, "stale_timeout", 0.1)
    monkeypatch.setattr(gren.GREN_CONFIG, "lease_duration_sec", 0.05)
    monkeypatch.setattr(gren.GREN_CONFIG, "heartbeat_interval_sec", 0.01)
    monkeypatch.setattr(gren.GREN_CONFIG, "cancelled_is_preempted", True)
    return tmp_path

import furu


def test_classify_scheduler_state_cancelled(furu_tmp_root, monkeypatch) -> None:
    adapter = furu.SubmititAdapter(executor=None)
    monkeypatch.setattr(furu.FURU_CONFIG, "cancelled_is_preempted", True)
    assert adapter.classify_scheduler_state("CANCELLED") == "preempted"
    monkeypatch.setattr(furu.FURU_CONFIG, "cancelled_is_preempted", False)
    assert adapter.classify_scheduler_state("CANCELLED") == "failed"

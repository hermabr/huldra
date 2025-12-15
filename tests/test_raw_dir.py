import huldra


class Dummy(huldra.Huldra[int]):
    def _create(self) -> int:
        return 1

    def _load(self) -> int:
        return 1


def test_raw_dir_is_scoped_to_object(huldra_tmp_root) -> None:
    obj = Dummy()
    assert obj.raw_dir == huldra.HULDRA_CONFIG.raw_dir
    assert obj.raw_dir == huldra_tmp_root / "raw"

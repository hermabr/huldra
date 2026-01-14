import gren


class Dummy(gren.Gren[int]):
    def _create(self) -> int:
        return 1

    def _load(self) -> int:
        return 1


def test_raw_dir_is_scoped_to_object(gren_tmp_root) -> None:
    obj = Dummy()
    assert obj.raw_dir == gren.GREN_CONFIG.raw_dir
    assert obj.raw_dir == gren_tmp_root / "raw"

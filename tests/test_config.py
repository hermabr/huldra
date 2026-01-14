import gren


def test_get_and_set_gren_root(gren_tmp_root, tmp_path) -> None:
    assert gren.get_gren_root(version_controlled=False) == gren_tmp_root / "data"
    assert gren.get_gren_root(version_controlled=True) == gren_tmp_root / "git"
    assert gren.GREN_CONFIG.raw_dir == gren_tmp_root / "raw"

    gren.set_gren_root(tmp_path)
    assert gren.GREN_CONFIG.base_root == tmp_path.resolve()

import json

import gren


class Exp(gren.Gren[int]):
    value: int = gren.chz.field()

    def _create(self) -> int:
        (self.gren_dir / "value.json").write_text(json.dumps(self.value))
        return self.value

    def _load(self) -> int:
        return json.loads((self.gren_dir / "value.json").read_text())


class Experiments(gren.GrenList[Exp]):
    a = Exp(value=1)
    b = Exp(value=1)  # duplicate digest
    nested = {"x": Exp(value=2)}
    also_nested = [Exp(value=2)]  # duplicate digest


def test_collection_dedup_and_lookup(gren_tmp_root) -> None:
    all_exps = Experiments.all()
    assert sorted(e.value for e in all_exps) == [1, 2]

    assert Experiments.by_name("a").value == 1
    assert Experiments.by_name("x").value == 2
    assert Experiments.by_name("missing", strict=False) is None

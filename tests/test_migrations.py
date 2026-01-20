import json
import sys
import textwrap
from typing import cast

import pytest

import gren
from gren.storage import MigrationManager, StateManager
from gren.storage.state import _StateResultMigrated, _StateResultSuccess


class MigrationDummy(gren.Gren[int]):
    value: int = gren.chz.field(default=0)

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.value))
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


class RenamedSource(gren.Gren[int]):
    value: int = gren.chz.field(default=0)

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.value))
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


class RenamedTarget(gren.Gren[int]):
    value: int = gren.chz.field(default=0)

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.value))
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


class AddedFieldV1(gren.Gren[int]):
    value: int = gren.chz.field(default=0)

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.value))
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


class AddedFieldV2(gren.Gren[int]):
    value: int = gren.chz.field(default=0)
    extra: str = gren.chz.field(default="default")

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.value))
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


def _define_same_class(source: str) -> type:
    namespace: dict[str, object] = {"gren": gren, "__name__": __name__}
    exec(textwrap.dedent(source), namespace)
    cls = namespace.get("SameClass")
    if not isinstance(cls, type):
        raise AssertionError("SameClass definition failed")
    if not issubclass(cls, gren.Gren):
        raise AssertionError("SameClass must be a Gren")
    cls.__module__ = __name__
    cls.__qualname__ = "SameClass"
    module = sys.modules[__name__]
    setattr(module, "SameClass", cls)
    return cls


def _same_class_v1() -> type:
    return _define_same_class(
        """
        class SameClass(gren.Gren[int]):
            name: str = gren.chz.field(default="")

            def _create(self) -> int:
                (self.gren_dir / "value.txt").write_text(self.name)
                return len(self.name)

            def _load(self) -> int:
                return len((self.gren_dir / "value.txt").read_text())
        """
    )


def _same_class_v2_required() -> type:
    return _define_same_class(
        """
        class SameClass(gren.Gren[int]):
            name: str = gren.chz.field(default="")
            language: str = gren.chz.field()

            def _create(self) -> int:
                (self.gren_dir / "value.txt").write_text(f"{self.name}:{self.language}")
                return len(self.name)

            def _load(self) -> int:
                return len((self.gren_dir / "value.txt").read_text().split(\":\")[0])
        """
    )


def _same_class_v2_optional() -> type:
    return _define_same_class(
        """
        class SameClass(gren.Gren[int]):
            name: str = gren.chz.field(default="")
            language: str = gren.chz.field(default="spanish")

            def _create(self) -> int:
                (self.gren_dir / "value.txt").write_text(f"{self.name}:{self.language}")
                return len(self.name)

            def _load(self) -> int:
                return len((self.gren_dir / "value.txt").read_text().split(\":\")[0])
        """
    )


class DataBase(gren.Gren[int]):
    value: int = gren.chz.field(default=0)

    def _create(self) -> int:
        raise NotImplementedError("DataBase does not implement _create")

    def _load(self) -> int:
        raise NotImplementedError("DataBase does not implement _load")


class DataV1(DataBase):
    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.value))
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


class DataV2(DataBase):
    language: str = gren.chz.field(default="english")

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(f"{self.value}:{self.language}")
        return self.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text().split(":")[0])


class ExperimentV1(gren.Gren[int]):
    data: DataBase = gren.chz.field()

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.data.value))
        return self.data.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


class ExperimentV2(gren.Gren[int]):
    data: DataBase = gren.chz.field()

    def _create(self) -> int:
        (self.gren_dir / "value.txt").write_text(str(self.data.value))
        return self.data.value

    def _load(self) -> int:
        return int((self.gren_dir / "value.txt").read_text())


def _events_for(directory) -> list[dict[str, str | int]]:
    path = StateManager.get_events_path(directory)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_migrate_move_transfers_payload(gren_tmp_root) -> None:
    from_obj = RenamedSource(value=1)
    to_obj = RenamedTarget(value=1)

    assert from_obj.load_or_create() == 1

    gren.migrate(from_obj, to_obj, policy="move", origin="tests")

    from_dir = from_obj._base_gren_dir()
    to_dir = to_obj._base_gren_dir()

    assert not (from_dir / "value.txt").exists()
    assert (to_dir / "value.txt").read_text() == "1"
    assert to_obj.load_or_create() == 1

    to_record = MigrationManager.read_migration(to_dir)
    assert to_record is not None
    assert to_record.kind == "moved"
    assert to_record.policy == "move"

    from_record = MigrationManager.read_migration(from_dir)
    assert from_record is not None
    assert from_record.kind == "migrated"
    assert from_record.policy == "move"

    from_state = StateManager.read_state(from_dir)
    assert isinstance(from_state.result, _StateResultMigrated)


def test_migrate_alias_force_recompute_detaches(gren_tmp_root, monkeypatch) -> None:
    from_obj = RenamedSource(value=1)
    to_obj = RenamedTarget(value=1)

    assert from_obj.load_or_create() == 1

    gren.migrate(from_obj, to_obj, policy="alias", origin="tests")

    alias_dir = to_obj._base_gren_dir()
    state = StateManager.read_state(alias_dir)
    assert isinstance(state.result, _StateResultMigrated)

    qualname = f"{to_obj.__class__.__module__}.{to_obj.__class__.__qualname__}"
    monkeypatch.setattr(gren.GREN_CONFIG, "force_recompute", {qualname})

    assert to_obj.load_or_create() == 1

    state_after = StateManager.read_state(alias_dir)
    assert isinstance(state_after.result, _StateResultSuccess)
    assert (alias_dir / "value.txt").read_text() == "1"

    alias_record = MigrationManager.read_migration(alias_dir)
    assert alias_record is not None
    assert alias_record.overwritten_at is not None

    original_record = MigrationManager.read_migration(from_obj._base_gren_dir())
    assert original_record is not None
    assert original_record.overwritten_at is not None

    alias_events = [
        event
        for event in _events_for(alias_dir)
        if event.get("type") == "migration_overwrite"
    ]
    original_events = [
        event
        for event in _events_for(from_obj._base_gren_dir())
        if event.get("type") == "migration_overwrite"
    ]
    assert len(alias_events) == 1
    assert len(original_events) == 1
    assert alias_events[0].get("reason") == "force_recompute"
    assert original_events[0].get("reason") == "force_recompute"


def test_migrate_alias_of_alias_is_skipped(gren_tmp_root) -> None:
    from_obj = RenamedSource(value=2)
    to_obj = RenamedTarget(value=2)

    assert from_obj.load_or_create() == 2

    gren.migrate(from_obj, to_obj, policy="alias", origin="tests")

    candidates = gren.find_migration_candidates(
        namespace=gren.NamespacePair(
            from_namespace="test_migrations.RenamedSource",
            to_namespace="test_migrations.RenamedTarget",
        ),
    )
    assert len(candidates) == 1

    results = gren.apply_migration(
        candidates[0],
        policy="alias",
        origin="tests",
        note="alias-of-alias",
        conflict="skip",
    )
    assert len(results) == 1
    assert isinstance(results[0], gren.MigrationSkip)


def test_migrate_alias_for_rename(gren_tmp_root) -> None:
    from_obj = RenamedSource(value=10)
    to_obj = RenamedTarget(value=10)

    assert from_obj.load_or_create() == 10

    gren.migrate(from_obj, to_obj, policy="alias", origin="tests", note="rename")

    alias_state = StateManager.read_state(to_obj._base_gren_dir())
    assert isinstance(alias_state.result, _StateResultMigrated)

    alias_record = MigrationManager.read_migration(to_obj._base_gren_dir())
    assert alias_record is not None
    assert alias_record.kind == "alias"
    assert alias_record.from_namespace.endswith("RenamedSource")
    assert alias_record.to_namespace.endswith("RenamedTarget")

    assert to_obj.load_or_create() == 10


def test_migrate_alias_with_added_field_default(gren_tmp_root) -> None:
    from_obj = AddedFieldV1(value=5)
    to_obj = AddedFieldV2(value=5)

    assert from_obj.load_or_create() == 5

    candidates = gren.find_migration_candidates(
        namespace=gren.NamespacePair(
            from_namespace="test_migrations.AddedFieldV1",
            to_namespace="test_migrations.AddedFieldV2",
        ),
        default_values={"extra": "default"},
    )
    assert len(candidates) == 1

    gren.apply_migration(
        candidates[0],
        policy="alias",
        origin="tests",
        note="added-field",
    )

    alias_record = MigrationManager.read_migration(to_obj._base_gren_dir())
    assert alias_record is not None
    assert alias_record.kind == "alias"
    assert alias_record.default_values == {"extra": "default"}

    alias_state = StateManager.read_state(to_obj._base_gren_dir())
    assert isinstance(alias_state.result, _StateResultMigrated)

    assert to_obj.load_or_create() == 5


def test_migrate_same_class_add_required_field(gren_tmp_root) -> None:
    same_class_v1 = _same_class_v1()
    from_obj = same_class_v1(name="mnist")

    assert from_obj.load_or_create() == 5

    same_class_v2 = _same_class_v2_required()
    candidates = gren.find_migration_candidates(
        namespace="test_migrations.SameClass",
        to_obj=cast(type[gren.Gren], same_class_v2),
        drop_fields=["name"],
        default_values={"name": "mnist", "language": "english"},
    )
    assert len(candidates) == 1

    gren.apply_migration(
        candidates[0],
        policy="alias",
        origin="tests",
        note="add-language",
    )

    to_obj = same_class_v2(name="mnist", language="english")
    alias_record = MigrationManager.read_migration(to_obj._base_gren_dir())
    assert alias_record is not None
    assert alias_record.default_values == {"name": "mnist", "language": "english"}

    alias_state = StateManager.read_state(to_obj._base_gren_dir())
    assert isinstance(alias_state.result, _StateResultMigrated)

    assert to_obj.load_or_create() == 5


def test_migrate_same_class_drop_fields_and_defaults(gren_tmp_root) -> None:
    same_class_v1 = _same_class_v1()
    from_obj = same_class_v1(name="dummy")

    assert from_obj.load_or_create() == 5

    same_class_v2 = _same_class_v2_optional()
    candidates = gren.find_migration_candidates(
        namespace="test_migrations.SameClass",
        to_obj=cast(type[gren.Gren], same_class_v2),
        drop_fields=["name"],
        default_values={"name": "dummy", "language": "english"},
    )
    assert len(candidates) == 1

    gren.apply_migration(
        candidates[0],
        policy="alias",
        origin="tests",
        note="drop-and-default",
    )

    to_obj = same_class_v2(name="dummy", language="english")
    alias_record = MigrationManager.read_migration(to_obj._base_gren_dir())
    assert alias_record is not None
    assert alias_record.default_values == {"name": "dummy", "language": "english"}

    alias_state = StateManager.read_state(to_obj._base_gren_dir())
    assert isinstance(alias_state.result, _StateResultMigrated)

    assert to_obj.load_or_create() == 5


def test_migrate_default_fields_conflict(gren_tmp_root) -> None:
    same_class_v1 = _same_class_v1()
    from_obj = same_class_v1(name="dummy")

    assert from_obj.load_or_create() == 5

    same_class_v2 = _same_class_v2_optional()
    with pytest.raises(ValueError, match="default_fields and default_values overlap"):
        gren.find_migration_candidates(
            namespace="test_migrations.SameClass",
            to_obj=cast(type[gren.Gren], same_class_v2),
            default_fields=["language"],
            default_values={"language": "english"},
        )


def test_migrate_default_values_wrong_type(gren_tmp_root) -> None:
    same_class_v1 = _same_class_v1()
    from_obj = same_class_v1(name="dummy")

    assert from_obj.load_or_create() == 5

    same_class_v2 = _same_class_v2_required()
    with pytest.raises(Exception):
        gren.find_migration_candidates(
            namespace="test_migrations.SameClass",
            to_obj=cast(type[gren.Gren], same_class_v2),
            default_values={"language": 123},
        )


def test_migrate_drop_fields_unknown(gren_tmp_root) -> None:
    same_class_v1 = _same_class_v1()
    from_obj = same_class_v1(name="dummy")

    assert from_obj.load_or_create() == 5

    same_class_v2 = _same_class_v2_optional()
    with pytest.raises(ValueError, match="drop_fields contains unknown fields"):
        gren.find_migration_candidates(
            namespace="test_migrations.SameClass",
            to_obj=cast(type[gren.Gren], same_class_v2),
            drop_fields=["language"],
        )


def test_migrate_drop_fields_and_default_overlap(gren_tmp_root) -> None:
    same_class_v1 = _same_class_v1()
    from_obj = same_class_v1(name="dummy")

    assert from_obj.load_or_create() == 5

    same_class_v2 = _same_class_v2_optional()
    with pytest.raises(ValueError, match="default_values provided for existing fields"):
        gren.find_migration_candidates(
            namespace="test_migrations.SameClass",
            to_obj=cast(type[gren.Gren], same_class_v2),
            default_values={"name": "dummy"},
        )


def test_migrate_no_candidates_for_namespace(gren_tmp_root) -> None:
    same_class_v2 = _same_class_v2_required()
    candidates = gren.find_migration_candidates(
        namespace="test_migrations.MissingSource",
        to_obj=cast(type[gren.Gren], same_class_v2),
    )
    assert candidates == []


def test_migrate_cascade_updates_dependents(gren_tmp_root) -> None:
    data_obj = DataV1(value=3)
    exp_obj = ExperimentV1(data=data_obj)

    assert data_obj.load_or_create() == 3
    assert exp_obj.load_or_create() == 3

    data_candidates = gren.find_migration_candidates(
        namespace=gren.NamespacePair(
            from_namespace="test_migrations.DataV1",
            to_namespace="test_migrations.DataV2",
        ),
        drop_fields=["value"],
        default_values={"value": 3, "language": "english"},
    )
    assert len(data_candidates) == 1

    gren.apply_migration(
        data_candidates[0],
        policy="alias",
        cascade=True,
        origin="tests",
        note="cascade-data",
    )

    data_alias = DataV2(value=3, language="english")
    exp_alias = ExperimentV1(data=data_alias)

    assert data_alias.exists() is True
    assert exp_alias.exists() is True

    exp_record = MigrationManager.read_migration(exp_alias._base_gren_dir())
    assert exp_record is not None
    assert exp_record.kind == "alias"

    exp_candidates = gren.find_migration_candidates(
        namespace=gren.NamespacePair(
            from_namespace="test_migrations.ExperimentV1",
            to_namespace="test_migrations.ExperimentV2",
        ),
        drop_fields=["data"],
        default_values={"data": data_alias},
    )
    assert len(exp_candidates) == 2


def test_migrate_cascade_after_parent_migration(gren_tmp_root) -> None:
    data_obj = DataV1(value=7)
    exp_obj = ExperimentV1(data=data_obj)

    assert data_obj.load_or_create() == 7
    assert exp_obj.load_or_create() == 7

    exp_candidates = gren.find_migration_candidates(
        namespace=gren.NamespacePair(
            from_namespace="test_migrations.ExperimentV1",
            to_namespace="test_migrations.ExperimentV2",
        ),
        drop_fields=["data"],
        default_values={"data": DataV2(value=7, language="english")},
    )
    assert len(exp_candidates) == 1

    gren.apply_migration(
        exp_candidates[0],
        policy="alias",
        cascade=False,
        origin="tests",
        note="parent-only",
    )

    data_candidates = gren.find_migration_candidates(
        namespace=gren.NamespacePair(
            from_namespace="test_migrations.DataV1",
            to_namespace="test_migrations.DataV2",
        ),
        drop_fields=["value"],
        default_values={"value": 7, "language": "english"},
    )
    assert len(data_candidates) == 1

    gren.apply_migration(
        data_candidates[0],
        policy="alias",
        cascade=True,
        origin="tests",
        note="cascade-data",
    )

    data_alias = DataV2(value=7, language="english")
    exp_alias = ExperimentV2(data=data_alias)

    assert data_alias.exists() is True
    assert exp_alias.exists() is True

    exp_record = MigrationManager.read_migration(exp_alias._base_gren_dir())
    assert exp_record is not None
    assert exp_record.kind == "alias"

# Dependency Discovery Plan

## Goal
Add dependency discovery for `Furu` objects so callers can retrieve direct or transitive
dependencies from config fields plus an optional `_dependencies()` hook. The default
behavior should be recursive with stable ordering and de-duplication by `_furu_hash`.

## Proposed API

### Core Methods
```python
class Furu[T](ABC):
    def _dependencies(self) -> DependencySpec | None:
        return None

    def _get_dependencies(self, *, recursive: bool = True) -> list["Furu"]:
        ...
```

### DependencySpec
```python
from typing import TypeAlias
from furu import DependencyChzSpec

DependencySpec: TypeAlias = (
    Furu
    | list[Furu]
    | tuple[Furu, ...]
    | set[Furu]
    | frozenset[Furu]
    | dict[str, Furu]
    | DependencyChzSpec  # Any @chz object with only Furu or Furu collections as fields.
)
```

## Behavior Rules
- `_get_dependencies(recursive=True)` returns a stable, pre-order traversal of all
  dependencies from:
  1) `Furu` instances in `@chz` fields and nested containers
  2) the optional `_dependencies()` hook
- De-duplicate by `_furu_hash` across all sources (fields and `_dependencies()`).
- `_dependencies()` strict validation:
  - If it returns a `@chz` object, every field must be a `Furu` or a collection of
    `Furu` (list/tuple/set/frozenset/dict values).
  - If it returns a collection or dict directly, every contained value must be a `Furu`.
  - Non-`Furu` entries raise `TypeError` with a clear path to the invalid field/value.
- The strict validation applies only to the `_dependencies()` spec. It does not
  restrict the fields of the returned `Furu` objects.

## API Example
```python
from pathlib import Path
from chz import chz
from furu import Furu


class Task(Furu[int]):
    value: int

    @property
    def _data_path(self) -> Path:
        return self.furu_dir / "data.txt"

    def _create(self) -> int:
        new_value = self.value * 2
        self._data_path.write_text(str(new_value))
        return new_value

    def _load(self) -> int:
        return int(self._data_path.read_text())


@chz
class CollectionDeps:
    tasks: list[Task]


class Collection(Furu[int]):
    n_tasks: int
    base_task: Task

    def _dependencies(self) -> CollectionDeps:
        return CollectionDeps(tasks=[Task(value=i) for i in range(self.n_tasks)])

    @property
    def _data_path(self) -> Path:
        return self.furu_dir / "collection.txt"

    def _create(self) -> int:
        result = self.base_task.load_or_create()
        for task in self._dependencies().tasks:
            result += task.load_or_create()
        self._data_path.write_text(str(result))
        return result

    def _load(self) -> int:
        return int(self._data_path.read_text())


collection = Collection(n_tasks=3, base_task=Task(value=10))
deps = collection._get_dependencies()
# deps -> [Task(value=10), Task(value=0), Task(value=1), Task(value=2)]
```

## Test Examples
```python
def test_dependencies_dedup_and_order(furu_tmp_root) -> None:
    class Task(furu.Furu[int]):
        value: int
        def _create(self) -> int:
            (self.furu_dir / "v.txt").write_text(str(self.value))
            return self.value
        def _load(self) -> int:
            return int((self.furu_dir / "v.txt").read_text())

    @chz
    class Deps:
        tasks: list[Task]

    class Collection(furu.Furu[int]):
        base_task: Task
        n_tasks: int
        def _dependencies(self) -> Deps:
            return Deps(tasks=[Task(value=i) for i in range(self.n_tasks)])
        def _create(self) -> int:
            return 0
        def _load(self) -> int:
            return 0

    base = Task(value=0)
    obj = Collection(base_task=base, n_tasks=2)
    deps = obj._get_dependencies(recursive=False)
    assert [dep.value for dep in deps] == [0, 1]


def test_dependencies_spec_rejects_non_furu(furu_tmp_root) -> None:
    class Task(furu.Furu[int]):
        value: int
        def _create(self) -> int:
            return self.value
        def _load(self) -> int:
            return self.value

    @chz
    class BadDeps:
        tasks: list[Task]
        label: str

    class Collection(furu.Furu[int]):
        def _dependencies(self) -> BadDeps:
            return BadDeps(tasks=[Task(value=1)], label="oops")
        def _create(self) -> int:
            return 0
        def _load(self) -> int:
            return 0

    with pytest.raises(TypeError, match="label"):
        Collection()._get_dependencies()


def test_dependencies_recursive(furu_tmp_root) -> None:
    class Leaf(furu.Furu[int]):
        value: int
        def _create(self) -> int:
            return self.value
        def _load(self) -> int:
            return self.value

    class Mid(furu.Furu[int]):
        leaf: Leaf
        def _create(self) -> int:
            return 0
        def _load(self) -> int:
            return 0

    class Root(furu.Furu[int]):
        mid: Mid
        def _create(self) -> int:
            return 0
        def _load(self) -> int:
            return 0

    root = Root(mid=Mid(leaf=Leaf(value=1)))
    deps = root._get_dependencies()
    assert [d.__class__.__name__ for d in deps] == ["Mid", "Leaf"]
```

## Implementation Steps
1. Add `DependencySpec` type alias and `_dependencies()` default method in
   `src/furu/core/furu.py`.
2. Implement dependency walkers (lenient for config fields, strict for `_dependencies()`).
3. Add `_get_dependencies(recursive=True)` with stable pre-order traversal and de-dup.
4. Add tests to `tests/test_furu_dependencies.py` based on the examples above.
5. Update `CHANGELOG.md` with a `## Unreleased` section documenting the new API and typing helpers.

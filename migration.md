# Migration Workflow Design (migration.md)

## Overview
This document defines the high-level migration workflows for Gren, including:
- candidate discovery
- strict schema validation
- explicit defaulting and field drops
- cascading migrations
- application/overwrite safety checks

The design supports both:
1) Uninitialized targets (class or namespace) using schema-driven defaults
2) Initialized targets (instance) using concrete serialized values

No interactive prompts are part of the core API. The workflow is:
1) list candidates
2) select exactly one
3) apply that migration (with cascade by default)

## Goals / Invariants
- All fields possible to set on the target Gren object must be present.
- No extra fields are allowed unless explicitly dropped.
- Defaults are only applied explicitly (never implicitly).
- Default conflicts always throw.
- Cascading (dependent migrations) is enabled by default.
- When target dir exists with success/running state, require force or skip with warning.

## Types

### Primitive / JSON types
```
Primitive = str | int | float | bool | None
JsonValue = (
  Primitive |
  list[JsonValue] |
  dict[str, JsonValue]
)
MigrationValue = (
  Primitive |
  Gren |
  tuple[MigrationValue, ...] |
  dict[str, MigrationValue]
)
```

MigrationValue is resolved to JsonValue before hashing.
- Gren objects are serialized via GrenSerializer.to_dict(...)["gren_obj"].
- Tuples are normalized to JSON arrays during serialization.
- Non-serializable objects are not allowed; convert them to dict/tuple/primitive.

### NamespacePair
Used for specifying different from/to namespaces in a single argument.
```
@dataclass(frozen=True)
class NamespacePair:
    from_namespace: str
    to_namespace: str
```

### GrenRef
```
@dataclass(frozen=True)
class GrenRef:
    namespace: str
    gren_hash: str
    root: Literal["data", "git"]
    directory: Path
```

### MigrationCandidate
```
@dataclass(frozen=True)
class MigrationCandidate:
    from_ref: GrenRef
    to_ref: GrenRef
    to_namespace: str
    to_config: dict[str, JsonValue]      # final serialized config used for hash
    defaults_applied: dict[str, Primitive]
    fields_dropped: list[str]
    missing_fields: list[str]
    extra_fields: list[str]
```

### MigrationSkip
```
@dataclass(frozen=True)
class MigrationSkip:
    candidate: MigrationCandidate
    reason: str
```

## Public API

### 1) find_migration_candidates
Schema-driven candidate discovery (uninitialized target).

```
@overload
def find_migration_candidates(
    *,
    namespace: str,
    to_obj: type[Gren],
    default_values: Mapping[str, Primitive] | None = None,
    default_fields: Iterable[str] | None = None,
    drop_fields: Iterable[str] | None = None,
) -> list[MigrationCandidate]:
    ...

@overload
def find_migration_candidates(
    *,
    namespace: NamespacePair,
    to_obj: None = None,
    default_values: Mapping[str, Primitive] | None = None,
    default_fields: Iterable[str] | None = None,
    drop_fields: Iterable[str] | None = None,
) -> list[MigrationCandidate]:
    ...

def find_migration_candidates(
    *,
    namespace: str | NamespacePair,
    to_obj: type[Gren] | None = None,
    default_values: Mapping[str, Primitive] | None = None,
    default_fields: Iterable[str] | None = None,
    drop_fields: Iterable[str] | None = None,
) -> list[MigrationCandidate]:
    ...
```

Rules:
- `namespace` must be provided.
- `namespace` can be:
  - `str`: shared namespace (requires `to_obj`)
  - `NamespacePair`: explicit from/to namespaces
- If `namespace` is `NamespacePair`, `to_obj` must be `None`.
- If `namespace` is `str`, `to_obj` must be provided.
- `to_obj` must be a class (uninitialized); passing an instance throws.
- Defaults are applied only if the field appears in `default_fields`.
- When defaults are used, they come from:
  - `to_obj` class defaults if `to_obj` provided
  - target class defaults if `NamespacePair` is used
- If a requested default field has no class default, throw.
- `default_values` always takes precedence over class defaults when present.

### 2) find_migration_candidates_initialized_target
Instance-driven candidate discovery.

```
def find_migration_candidates_initialized_target(
    *,
    to_obj: Gren,
    from_namespace: str | None = None,
    default_fields: Iterable[str] | None = None,
    drop_fields: Iterable[str] | None = None,
) -> list[MigrationCandidate]:
    ...
```

Rules:
- `to_obj` must be an instance; passing a class (uninitialized) throws.
- Compare candidates against the concrete serialized config of `to_obj`.
- `default_fields` (if provided) fill missing fields using `to_obj` values.
- No class defaults are used here.

### 3) apply_migration
Apply a single candidate.

```
@overload
def apply_migration(
    candidate: MigrationCandidate,
    *,
    policy: Literal["alias", "move", "copy"] = "alias",
    cascade: bool = True,
    origin: str | None = None,
    note: str | None = None,
    force_overwrite: bool = False,
    on_conflict: Literal["throw"] = "throw",
) -> list[MigrationRecord]:
    ...

@overload
def apply_migration(
    candidate: MigrationCandidate,
    *,
    policy: Literal["alias", "move", "copy"] = "alias",
    cascade: bool = True,
    origin: str | None = None,
    note: str | None = None,
    force_overwrite: bool = False,
    on_conflict: Literal["skip"],
) -> list[MigrationRecord | MigrationSkip]:
    ...

def apply_migration(
    candidate: MigrationCandidate,
    *,
    policy: Literal["alias", "move", "copy"] = "alias",
    cascade: bool = True,
    origin: str | None = None,
    note: str | None = None,
    force_overwrite: bool = False,
    on_conflict: Literal["throw", "skip"] = "throw",
) -> list[MigrationRecord | MigrationSkip]:
    ...
```

Behavior:
- `cascade=True` by default. If False, emit warning.
- Target dir safety check:
  - Use `Gren.get_state()` (alias-aware) for the target dir.
  - If target state is `success` or `running`:
    - `force_overwrite=False` and `on_conflict="throw"` -> error
    - `force_overwrite=False` and `on_conflict="skip"` -> warn + skip
    - `force_overwrite=True` -> proceed + log overwrite event
- When `on_conflict="throw"`, return only `MigrationRecord` entries.
- When `on_conflict="skip"`, return a mixed list containing `MigrationRecord` and `MigrationSkip` entries.

## Validation Rules (Strict)

When building candidates:

1) Start from old metadata `gren_obj`.
2) Drop fields from `drop_fields`.
   - If drop target missing -> error.
3) Defaults:
   - If `default_fields` includes field already present -> error.
   - If `default_values` includes field already present -> error.
   - If field has no default in target class -> error.
4) Validate field set:
   - Missing fields -> error
   - Extra fields -> error
5) Set `__class__` to target namespace.
6) Type-check the candidate config by reconstructing the target object and running chz type checks:
   - `obj = GrenSerializer.from_dict(to_config)`
   - `validators.for_all_fields(validators.typecheck)(obj)`
7) Compute new hash from `to_config`.

## Error Messages (exact strings)

### Input validation
- `migration: namespace must be str or NamespacePair`
- `migration: to_obj must be a class (use find_migration_candidates_initialized_target for instances)`
- `migration: to_obj must be an instance (use find_migration_candidates for classes)`
- `migration: to_obj cannot be used with NamespacePair`
- `migration: namespace is required`

### Target class resolution
- `migration: unable to resolve target class: {namespace}`

### Defaults / drops
- `migration: default_values provided for existing fields: {fields}`
- `migration: default_fields provided for existing fields: {fields}`
- `migration: default_fields missing defaults for fields: {fields}`
- `migration: default_values contains fields not in target schema: {fields}`
- `migration: default_fields contains fields not in target schema: {fields}`
- `migration: drop_fields contains unknown fields: {fields}`

### Schema strictness
- `migration: missing required fields for target class: {fields}`
- `migration: extra fields present; use drop_fields to remove: {fields}`

### Apply conflict
- `migration: target exists with status {status}; pass force_overwrite=True or on_conflict='skip'`

Warnings:
- `migration: cascade disabled; dependents will not be migrated`
- `migration: skipping candidate due to target status {status}`

## State Safety Check
- Implement `Gren.get_state()` as a general alias-aware method.
- Use this in `apply_migration` to check target state.
- Alias awareness must not be hard-coded in migration functions.

## Logging
- For all migrations, append `migrated` events in both dirs.
- If `force_overwrite=True`, append `migration_overwrite` event to both dirs:
  - `reason = "force_overwrite"`
- Record `default_values` in `MigrationRecord` and migration events.

## Cascading (Default)
- When applying migration, find dependents by scanning metadata for nested `gren_obj`.
- For each dependent:
  - Replace embedded dependency config (`__class__`, hash, config)
  - Validate strict schema for the dependent
  - Create alias migration (by default policy)

## Implementation Notes / Constraints
- Follow repo rules: no Optional, no Any, no untyped dict.
- Prefer `Mapping[str, Primitive]`, `dict[str, JsonValue]`.
- Use chz validators for type checking (see Validation Rules).
- No try/except for control flow.
- Always update `CHANGELOG.md` for user-visible change.
- Use `make lint` / `make test` / `make dashboard-test` / `make dashboard-test-e2e`.

## Test Plan
Add tests for:
1) Default conflicts throw
2) Missing defaults throw
3) Extra fields require drop_fields
4) Initialized target candidate search uses to_obj values
5) Cascading data -> subclass migration updates dependent hashes
6) apply_migration conflict behavior (throw / skip / force_overwrite)
7) get_state is alias-aware for target dir

## Examples

### Add field with defaults (uninitialized)
```
find_migration_candidates(
  namespace="my_app.Data",
  to_obj=TextData,                   # class only
  default_fields=["language"],
)
```

### Rename class (namespace change)
```
find_migration_candidates(
  namespace=NamespacePair(
    from_namespace="old.Data",
    to_namespace="new.Data",
  )
)
```

### Initialized target
```
to_obj = TextData(name="dataset", language="spanish")
candidates = find_migration_candidates_initialized_target(
  to_obj=to_obj,
  from_namespace="my_app.Data",
)
apply_migration(candidates[0], policy="alias")
```

Progress for Migration Feature

Context
- Goal: add explicit migration/alias support for Gren objects (rename/move/field changes), add gren_version default 1.0, block _create for migrated objects unless force recompute, log migrations/overwrites, and show migration state in dashboard.
- Explicit migrations only: no implicit legacy lookup. Alias directories must be created via gren.migrate or dashboard-triggered migration.
- Alias dir should have metadata + state.json with result.status="migrated". SUCCESS.json should NOT exist in alias dir.
- migration.json should be written in both old and new dirs for alias/move; copy policy leaves old dir unchanged except for event log.
- exists() should return True if alias target is success.
- dashboard default view should show resolved (migrated) object with a tag; detail view should show original version if migrated; radio to switch view.
- migrated_at should live in migration.json (not state.json). However state.json still uses result.status="migrated". We debated adding migrated_at to state.json but decision is to keep migrated_at in migration.json.

Key decisions from user
- Always alias by default; move/copy optional.
- No implicit resolution; alias directory must be created with migration.json.
- _create must not run for migrated objects unless force recompute.
- Migrated objects should log migration and overwrites with timestamps in events.jsonl for both old and new dirs.
- gren_version is the only version field (no separate current version field). Default 1.0 and stored in metadata always; omit from to_python if default.
- Dashboard should show migrated tag in resolved view; original view should show original object unchanged (copy policy only adds event log).

Completed work
- [x] Added migration registry and helpers
  - New file: src/gren/serialization/migrations.py
    - MigrationContext, FieldRename, FieldAdd (with default_factory), Transform, MigrationSpec, MigrationRegistry, MIGRATION_REGISTRY.
    - Registry supports chaining and logs a warning if chain length > 1.
  - Updated: src/gren/serialization/__init__.py exports MigrationSpec/FieldAdd/FieldRename/Transform/MIGRATION_REGISTRY and DEFAULT_GREN_VERSION.
- [x] Serializer changes
  - src/gren/serialization/serializer.py
    - Added DEFAULT_GREN_VERSION = 1.0.
    - Added _is_default_value() that checks chz defaults/default_factory for a field.
    - to_python() omits gren_version if it matches default.
- [x] Migration metadata
  - New file: src/gren/storage/migration.py
    - MigrationRecord includes kind (alias/migrated), policy (alias/move/copy), from/to namespace+hash+version+root, migrated_at, origin, note.
    - MigrationManager handles read/write of migration.json and resolving directories.
  - src/gren/storage/__init__.py exports MigrationManager, MigrationRecord.
- [x] Errors
  - src/gren/errors.py: Added GrenMigrationRequired (inherits GrenError).
  - src/gren/__init__.py updated to export GrenMigrationRequired and migrate function.
- [x] Core changes (partial)
  - src/gren/core/gren.py
    - Added gren_version: float = chz.field(default=1.0) to Gren class.
    - Added helper methods: _is_migrated_state(), _migration_target_dir().
    - exists() now resolves alias target and returns True if target is success.
    - load_or_create() blocks when migrated unless force recompute (check is in place after reconcile).
    - gren_dir now resolves alias if migration.json kind=alias.
    - Added StateOwner usage for submitit queued attempt creation (some typing ignores still present).
- [x] Migration API (partial)
  - New file: src/gren/migrate.py
    - migrate(from_obj, to_obj, policy=alias|move|copy, origin, note).
    - Writes migration.json in new dir; and old dir for alias/move (not for copy).
    - Writes events in both old and new dirs.
    - For alias: writes state.result="migrated" in new dir.
    - For move/copy: copies payload and state, then writes metadata for new object.
    - uses DEFAULT_GREN_VERSION for target version check.

Current issues / blockers
- [ ] src/gren/storage/state.py is unstable due to toggling migrated_at on _StateResultMigrated.
  - Desired final: _StateResultMigrated should NOT include migrated_at in state.json.
  - But _coerce_result currently expects migrated_at and returns _StateResultMigrated with migrated_at. This must be reverted.
  - The state file should only store result.status="migrated". migrated_at should live only in migration.json.
- [ ] LSP/typing noise in core/gren.py around start_attempt_queued owner payload. Ignore or fix by defining proper Owner dict.
- [ ] In migrate.py, _write_migrated_state still sets migrated_at in state (should be removed once state model is fixed).
- [ ] Additional migration logging for overwrite (force recompute) still needs to be added.

Next steps
- [ ] Fix state migration handling (remove migrated_at from state.json; update coerce_result and migrate.py).
- [ ] Add overwrite logging in load_or_create when force recompute against migrated alias.
- [ ] Add migration-aware dashboard API and frontend UI.
- [ ] Add tests and update CHANGELOG.md.

Notes about chz defaults
- chz supports default comparison via Field._default and Field._default_factory.
- Similar logic appears in chz.data_model.pretty_format and beta_to_blueprint_values(skip_defaults=True).
- Use that logic to detect default gren_version in to_python.

Files modified/added so far
- [x] Added: src/gren/serialization/migrations.py
- [x] Added: src/gren/storage/migration.py
- [x] Added: src/gren/migrate.py
- [x] Modified: src/gren/serialization/serializer.py
- [x] Modified: src/gren/serialization/__init__.py
- [x] Modified: src/gren/storage/metadata.py
- [x] Modified: src/gren/errors.py
- [x] Modified: src/gren/core/gren.py
- [ ] Modified: src/gren/storage/state.py (needs cleanup)
- [x] Modified: src/gren/__init__.py

Original plan (agreed)
- [ ] Migration schema + registry: MigrationContext, FieldRename, FieldAdd (default or default_factory), Transform, MigrationSpec, MigrationRegistry; support code-defined + external (dashboard/API) migrations and chain with warning when >1 hop.
- [ ] gren_version: single field on Gren default 1.0; always stored in metadata; omit from to_python when default; adding it changes hashes and requires explicit migration.
- [ ] Explicit alias-only resolution: no implicit legacy lookup; alias directory must be created with migration.json; gren_dir resolves alias targets when migration.json kind=alias.
- [ ] Alias dirs + markers: alias dir contains metadata.json for new object and state.json with result.status="migrated"; no SUCCESS.json; migration.json written in both old/new for alias/move; copy leaves old unchanged except event log; migrated_at stored in migration.json only.
- [ ] Migrate API: gren.migrate(from_obj, to_obj, policy=alias|move|copy, origin, note) never calls _create; move/copy move or copy non-.gren payload; always log events in both dirs with timestamps.
- [ ] Force recompute rules: if current object is migrated, _create is blocked unless force recompute; on force recompute log overwritten events in both old/new dirs.
- [ ] exists() returns true when alias target is success; alias state only is not success.
- [ ] Dashboard: default resolved view with migrated tag; detail view shows original version if migrated; radio for resolved/original/both; allow simple migrations from dashboard.
- [ ] Tests + changelog: add migration tests (alias/move/copy, default_factory, chain warning, exists/force recompute) and update CHANGELOG.md; run make lint/test (and dashboard-test if dashboard changes).

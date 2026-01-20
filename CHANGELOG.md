# Changelog

## v1.0.0
- Add migration records for alias/move/copy with migrated state tracking, overwrite handling, and warnings on non-success migrations.
- Expand migration candidate logic (defaults, drop fields, initialized targets) and regression tests for rename/field-add cases.
- Make Gren runtime alias-aware for exists() and expose alias links/original status in experiment detail.
- Update dashboard views/filters to surface migration tags, alias/original navigation, and original-view deduping.
- Refresh dashboard fixtures/e2e coverage for migration navigation and counts.
- Ignore private fields when hashing migration configs and experiment objects.

## v0.2.0
- Add `GREN_CACHE_METADATA` for time-based git info caching. Accepts `never`, `forever`, or duration like `5m`, `1h`. Default: `5m`.
- Add `clear_metadata_cache()` to manually invalidate cached metadata.

## v0.1.2
- Add `GREN_FORCE_RECOMPUTE` to force recomputation for selected Gren classes.
- Update release automation to create PRs with version bumps and auto-release on main.
- Improve CI to build frontend assets and install e2e dependencies.

## v0.1.1
- Add `GREN_REQUIRE_GIT` and `GREN_REQUIRE_GIT_REMOTE` flags for git metadata collection.

## v0.1.0
- First public release of gren.

# Examples

These examples are meant to be run from the repo root.

They set `GREN_PATH` programmatically to `examples/.gren/` so you don’t clutter your working directory.
They also disable embedding the git diff in metadata (equivalent to `GREN_IGNORE_DIFF=1`), so the examples work even if your working tree is large.

## Run

```bash
uv run python examples/run_train.py
uv run python examples/run_nested.py
uv run python examples/run_logging.py
```

## Outputs

Artifacts will be written under:

- `examples/.gren/data/...`
- logs under each artifact directory: `.../.gren/gren.log`

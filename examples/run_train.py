from __future__ import annotations

from pathlib import Path

from my_project.pipelines import PrepareDataset, TrainModel

import gren


def main() -> None:
    try:
        examples_root = Path(__file__).resolve().parent
    except Exception:
        examples_root = Path(".").resolve().parent
    gren.set_gren_root(examples_root / ".gren")
    # gren.GREN_CONFIG.ignore_git_diff = True

    obj = TrainModel(lr=3e-4, steps=2_000, dataset=PrepareDataset(name="mydata"))
    artifact = obj.load_or_create()
    print("artifact:", artifact)
    print("artifact dir:", obj.gren_dir)
    print("log:", obj.gren_dir / ".gren" / "gren.log")


if __name__ == "__main__":
    main()

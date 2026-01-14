from __future__ import annotations

from pathlib import Path

import gren

from my_project.pipelines import PrepareDataset, TrainTextModel


def main() -> None:
    examples_root = Path(__file__).resolve().parent
    gren.set_gren_root(examples_root / ".gren")
    gren.GREN_CONFIG.ignore_git_diff = True

    model = TrainTextModel(dataset=PrepareDataset(name="toy"))
    out = model.load_or_create()

    print("model output:", out)
    print("model dir:", model.gren_dir)
    print("model log:", model.gren_dir / ".gren" / "gren.log")
    print("dataset dir:", model.dataset.gren_dir)
    print("dataset log:", model.dataset.gren_dir / ".gren" / "gren.log")


if __name__ == "__main__":
    main()

from __future__ import annotations

import logging
from pathlib import Path

import gren

from my_project.pipelines import TrainTextModel


def main() -> None:
    examples_root = Path(__file__).resolve().parent
    gren.set_gren_root(examples_root / ".gren")
    gren.GREN_CONFIG.ignore_git_diff = True

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

    obj = TrainTextModel()
    log.info("about to run: %s", obj.to_python(multiline=False))
    obj.load_or_create()
    log.info("wrote logs to: %s", obj.gren_dir / ".gren" / "gren.log")


if __name__ == "__main__":
    main()

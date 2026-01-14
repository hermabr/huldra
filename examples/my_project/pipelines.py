from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import gren

log = logging.getLogger(__name__)


class TrainModel(gren.Gren[Path]):
    lr: float = gren.chz.field(default=3e-4)
    steps: int = gren.chz.field(default=2_000)
    dataset: PrepareDataset
    sleep_sec: float = gren.chz.field(default=0.0)

    def _create(self) -> Path:
        log.info("training model lr=%s steps=%s", self.lr, self.steps)
        (self.gren_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "lr": self.lr,
                    "steps": self.steps,
                    "dataset": str(self.dataset.load_or_create()),
                },
                indent=2,
            )
        )
        ckpt = self.gren_dir / "checkpoint.bin"
        if self.sleep_sec > 0:
            time.sleep(self.sleep_sec)
        ckpt.write_bytes(b"fake-checkpoint-bytes")
        return ckpt

    def _load(self) -> Path:
        return self.gren_dir / "checkpoint.bin"


class PrepareDataset(gren.Gren[Path]):
    name: str = gren.chz.field(default="toy")

    def _create(self) -> Path:
        log.info("preparing dataset name=%s", self.name)
        path = self.gren_dir / "data.txt"
        path.write_text("hello\nworld\n")
        return path

    def _load(self) -> Path:
        return self.gren_dir / "data.txt"


class TrainTextModel(gren.Gren[Path]):
    dataset: PrepareDataset = gren.chz.field(default_factory=PrepareDataset)

    def _create(self) -> Path:
        log.info("training text model")
        dataset_path = self.dataset.load_or_create()
        model_path = self.gren_dir / "model.txt"
        model_path.write_text(f"trained on:\n{dataset_path.read_text()}")
        return model_path

    def _load(self) -> Path:
        return self.gren_dir / "model.txt"

"""Test pipelines with realistic Huldra subclasses for dashboard tests.

These classes create actual Huldra experiments with proper dependencies,
instead of using mock JSON data.
"""

from __future__ import annotations

import json
from pathlib import Path

import huldra


class PrepareDataset(huldra.Huldra[Path]):
    """Dataset preparation pipeline."""

    name: str = huldra.chz.field(default="default")
    version: str = huldra.chz.field(default="v1")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.txt"
        path.write_text(f"dataset: {self.name}\nversion: {self.version}\n")
        return path

    def _load(self) -> Path:
        return self.huldra_dir / "data.txt"


class TrainModel(huldra.Huldra[Path]):
    """Model training pipeline with dataset dependency."""

    lr: float = huldra.chz.field(default=3e-4)
    steps: int = huldra.chz.field(default=1000)
    dataset: PrepareDataset

    def _create(self) -> Path:
        # Trigger dependency
        dataset_path = self.dataset.load_or_create()

        # Write training metrics
        metrics_path = self.huldra_dir / "metrics.json"
        metrics_path.write_text(
            json.dumps(
                {"lr": self.lr, "steps": self.steps, "dataset": str(dataset_path)}
            )
        )

        # Create checkpoint
        ckpt = self.huldra_dir / "checkpoint.bin"
        ckpt.write_bytes(b"fake-checkpoint")
        return ckpt

    def _load(self) -> Path:
        return self.huldra_dir / "checkpoint.bin"


class EvalModel(huldra.Huldra[Path]):
    """Model evaluation pipeline with model dependency."""

    model: TrainModel
    eval_split: str = huldra.chz.field(default="test")

    def _create(self) -> Path:
        # Trigger dependency
        _ = self.model.load_or_create()

        # Fake evaluation results
        results = {"accuracy": 0.95, "loss": 0.05, "split": self.eval_split}
        results_path = self.huldra_dir / "results.json"
        results_path.write_text(json.dumps(results))
        return results_path

    def _load(self) -> Path:
        return self.huldra_dir / "results.json"


class FailingPipeline(huldra.Huldra[None]):
    """Pipeline that always fails (for testing failed states)."""

    reason: str = huldra.chz.field(default="intentional failure")

    def _create(self) -> None:
        raise RuntimeError(self.reason)

    def _load(self) -> None:
        return None


class DataLoader(huldra.Huldra[Path]):
    """Simple data loader in a different namespace."""

    source: str = huldra.chz.field(default="local")
    format: str = huldra.chz.field(default="csv")

    def _create(self) -> Path:
        path = self.huldra_dir / f"data.{self.format}"
        path.write_text(f"source: {self.source}\nformat: {self.format}\n")
        return path

    def _load(self) -> Path:
        return self.huldra_dir / f"data.{self.format}"


class MultiDependencyPipeline(huldra.Huldra[Path]):
    """Pipeline with multiple dependencies."""

    dataset1: PrepareDataset
    dataset2: PrepareDataset
    output_name: str = huldra.chz.field(default="combined")

    def _create(self) -> Path:
        # Trigger both dependencies
        path1 = self.dataset1.load_or_create()
        path2 = self.dataset2.load_or_create()

        # Combine outputs
        output = self.huldra_dir / f"{self.output_name}.txt"
        output.write_text(f"combined from:\n- {path1}\n- {path2}\n")
        return output

    def _load(self) -> Path:
        return self.huldra_dir / f"{self.output_name}.txt"


# --- Inheritance pattern: abstract Data base class with concrete subclasses ---


class Data(huldra.Huldra[Path]):
    """Abstract base class for data sources."""

    name: str = huldra.chz.field(default="unnamed")

    def _create(self) -> Path:
        raise NotImplementedError("Subclasses must implement _create")

    def _load(self) -> Path:
        return self.huldra_dir / "data.json"


class DataA(Data):
    """Concrete data source A."""

    source_url: str = huldra.chz.field(default="http://example.com/a")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.json"
        path.write_text(
            json.dumps({"type": "A", "name": self.name, "url": self.source_url})
        )
        return path


class DataB(Data):
    """Concrete data source B."""

    local_path: str = huldra.chz.field(default="/data/b")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.json"
        path.write_text(
            json.dumps({"type": "B", "name": self.name, "path": self.local_path})
        )
        return path


class Train(huldra.Huldra[Path]):
    """Training pipeline that accepts any Data subclass."""

    data: Data
    epochs: int = huldra.chz.field(default=10)

    def _create(self) -> Path:
        # Load the data dependency (works with any Data subclass)
        data_path = self.data.load_or_create()
        data_content = json.loads(data_path.read_text())

        # Create training output
        output = self.huldra_dir / "model.json"
        output.write_text(
            json.dumps(
                {
                    "epochs": self.epochs,
                    "data_type": data_content.get("type"),
                    "data_name": data_content.get("name"),
                }
            )
        )
        return output

    def _load(self) -> Path:
        return self.huldra_dir / "model.json"

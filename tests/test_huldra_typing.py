"""Tests that verify the type checker catches incorrect Huldra subclass definitions.

These tests run `ty` on code snippets and assert that the expected type errors are produced.
This ensures our type annotations correctly enforce the Huldra contract.
"""

import subprocess
import tempfile
from pathlib import Path


def run_ty_check(code: str) -> subprocess.CompletedProcess[str]:
    """Run ty check on a code snippet and return the result."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        result = subprocess.run(
            ["uv", "run", "ty", "check", str(temp_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,  # Run from project root
        )
        return result
    finally:
        temp_path.unlink()


def test_correct_huldra_subclass_passes_type_check() -> None:
    """A correctly typed Huldra subclass should pass type checking."""
    code = """
from pathlib import Path
import huldra

class CorrectData(huldra.Huldra[Path]):
    name: str = huldra.chz.field(default="correct")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.txt"
        path.write_text(self.name)
        return path

    def _load(self) -> Path:
        return self.huldra_dir / "data.txt"
"""
    result = run_ty_check(code)
    assert result.returncode == 0, f"Expected no errors, got:\n{result.stdout}"


def test_subclass_changing_return_type_fails_type_check() -> None:
    """A subclass that changes the return type should fail type checking."""
    code = """
from pathlib import Path
import huldra

class BaseData(huldra.Huldra[Path]):
    def _create(self) -> Path:
        return self.huldra_dir / "data.txt"

    def _load(self) -> Path:
        return self.huldra_dir / "data.txt"

class WrongSubclass(BaseData):
    def _create(self) -> str:  # Wrong: should be Path
        return "wrong"

    def _load(self) -> str:  # Wrong: should be Path
        return "wrong"
"""
    result = run_ty_check(code)
    assert result.returncode != 0, "Expected type errors"
    assert "invalid-method-override" in result.stdout
    assert "_create" in result.stdout
    assert "_load" in result.stdout


def test_huldra_subclass_with_mismatched_create_type_fails() -> None:
    """Declaring Huldra[Path] but returning str from _create should fail."""
    code = """
from pathlib import Path
import huldra

class MismatchedCreate(huldra.Huldra[Path]):
    def _create(self) -> str:  # Wrong: declared Huldra[Path]
        return "should be Path"

    def _load(self) -> Path:
        return self.huldra_dir / "data.txt"
"""
    result = run_ty_check(code)
    assert result.returncode != 0, "Expected type error"
    assert "invalid-method-override" in result.stdout
    assert "_create" in result.stdout


def test_huldra_subclass_with_mismatched_load_type_fails() -> None:
    """Declaring Huldra[Path] but returning str from _load should fail."""
    code = """
from pathlib import Path
import huldra

class MismatchedLoad(huldra.Huldra[Path]):
    def _create(self) -> Path:
        return self.huldra_dir / "data.txt"

    def _load(self) -> str:  # Wrong: declared Huldra[Path]
        return "should be Path"
"""
    result = run_ty_check(code)
    assert result.returncode != 0, "Expected type error"
    assert "invalid-method-override" in result.stdout
    assert "_load" in result.stdout


def test_correct_inheritance_chain_passes() -> None:
    """A correct inheritance chain (Base -> Subclass) should pass."""
    code = """
from pathlib import Path
import huldra

class Data(huldra.Huldra[Path]):
    name: str = huldra.chz.field(default="base")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.txt"
        path.write_text(self.name)
        return path

    def _load(self) -> Path:
        return self.huldra_dir / "data.txt"

class DataA(Data):
    extra: str = huldra.chz.field(default="a")

    def _create(self) -> Path:  # Correct: same return type as parent
        path = self.huldra_dir / "data.txt"
        path.write_text(f"{self.name} {self.extra}")
        return path
    # _load inherited - correct
"""
    result = run_ty_check(code)
    assert result.returncode == 0, f"Expected no errors, got:\n{result.stdout}"


def test_polymorphic_dependency_with_base_type_passes() -> None:
    """Using a base type annotation for polymorphic dependencies should pass."""
    code = """
from pathlib import Path
import json
import huldra

class Data(huldra.Huldra[Path]):
    name: str = huldra.chz.field(default="base")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.json"
        path.write_text(json.dumps({"name": self.name}))
        return path

    def _load(self) -> Path:
        return self.huldra_dir / "data.json"

class DataA(Data):
    url: str = huldra.chz.field(default="http://example.com")

    def _create(self) -> Path:
        path = self.huldra_dir / "data.json"
        path.write_text(json.dumps({"name": self.name, "url": self.url}))
        return path

class Train(huldra.Huldra[Path]):
    data: Data  # Accepts any Data subclass

    def _create(self) -> Path:
        data_path = self.data.load_or_create()  # Works with any Data
        return self.huldra_dir / "model.bin"

    def _load(self) -> Path:
        return self.huldra_dir / "model.bin"

# Usage should type check correctly
data_a = DataA(name="test")
train = Train(data=data_a)  # DataA is a valid Data
"""
    result = run_ty_check(code)
    assert result.returncode == 0, f"Expected no errors, got:\n{result.stdout}"

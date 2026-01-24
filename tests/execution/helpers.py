import json

import furu


class SimpleTask(furu.Furu[int]):
    value: int = furu.chz.field(default=1)

    def _create(self) -> int:
        (self.furu_dir / "value.json").write_text(json.dumps(self.value))
        return self.value

    def _load(self) -> int:
        return json.loads((self.furu_dir / "value.json").read_text())

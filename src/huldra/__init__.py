from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import reveal_type

from ty_extensions import TypeOf


@dataclass(frozen=True)
class Huldra(ABC):
    @property
    @abstractmethod
    def _slug(self) -> str:
        raise NotImplementedError("Slug not set - use @huldra decorator")

    @abstractmethod
    def _create(self):
        assert False

    @abstractmethod
    def _load(self):
        assert False

    def load_or_create(self):
        assert False, "TODO"

    def exists(self):
        assert False, "TODO"


def huldra(slug: str) -> TypeOf[Huldra]:  # TODO: make this nice
    @property
    def _slug(self) -> str:
        return slug

    huldra_obj = deepcopy(Huldra)
    huldra_obj._slug = _slug
    return huldra_obj


def main():
    huldra("clip") == Huldra

    # class Clip(Huldra):
    class Clip(huldra("clip")):
        name: str

        def _create(self):
            print("creating clip")

        def _load(self):
            print("loading clip")

    huldra("clip") == Huldra
    clip = Clip()
    reveal_type(clip._slug)
    assert (
        __import__("dataclasses").is_dataclass(clip)
        and getattr(clip, "__dataclass_params__").frozen
    )
    assert type(clip).__dataclass_params__.frozen
    clip.exists()

    # class SpanishClip(Clip):
    #     pass


if __name__ == "__main__":
    main()

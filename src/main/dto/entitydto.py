import dataclasses as dc
from abc import ABC
from typing import Iterator


@dc.dataclass
class EntityDto(ABC):
    """
    Basic implementation of Entity DTOs that store entities from relations in the smr world
    """

    def __iter__(self) -> Iterator:
        return iter(dc.astuple(self))

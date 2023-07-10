# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import Enum

from faebryk.core.core import ModuleTrait


class layer_type(Enum):
    NONE = 1
    TOP_LAYER = 2
    BOTTOM_LAYER = 3


Point = tuple[float, float]


class has_pcb_position(ModuleTrait):
    @abstractmethod
    def get_position(self) -> Point:
        ...


class has_pcb_position_defined(has_pcb_position.impl()):
    def __init__(self, position: Point) -> None:
        super().__init__()
        self.position = position

    def get_position(self) -> Point:
        return self.position

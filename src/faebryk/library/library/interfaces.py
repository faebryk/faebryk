# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from typing_extensions import Self

logger = logging.getLogger(__name__)

from faebryk.library.core import GraphInterface, ModuleInterface

# TODO: move file (interface component)----------------------------------------


class Electrical(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class GIFS(ModuleInterface.GIFS()):
            electrical = GraphInterface()

        self.GIFs = GIFS(self)

    def connect(self, other: Self) -> Self:
        self.GIFs.electrical.connect(other.GIFs.electrical)

        return super().connect(other)


class Bus(ModuleInterface):
    @classmethod
    def GIFS(cls):
        class GIFS(ModuleInterface.GIFS()):
            bus = GraphInterface()

        return GIFS

    def __init__(self) -> None:
        super().__init__()
        self.GIFs = Bus.GIFS()(self)

    # TODO: make trait
    def connect(self, other: Self) -> Self:
        self.GIFs.bus.connect(other.GIFs.bus)

        return super().connect(other)


class ElectricPower(Bus):
    def __init__(self) -> None:
        super().__init__()

        class _NODES(Bus.NODES()):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = _NODES(self)

    def connect(self, other: Self) -> Self:
        self.NODEs.hv.connect(other.NODEs.hv)
        self.NODEs.lv.connect(other.NODEs.lv)

        return super().connect(other)

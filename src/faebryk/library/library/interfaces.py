# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from typing_extensions import Self

logger = logging.getLogger("library")

from faebryk.library.core import Interface, Node

# TODO: move file (interface component)----------------------------------------


class InterfaceNode(Node):
    class LLIFS(super().LLIFS):
        parent = Interface()

    def __init__(self) -> None:
        super().__init__()
        self.LLIFs = InterfaceNode.LLIFS(self)

    def connect(self, other: Self) -> Self:
        assert type(other) is type(self), "can't connect to non-compatible type"
        return self


class Electrical(InterfaceNode):
    def __init__(self) -> None:
        super().__init__()

        class LLIFS(super().LLIFS):
            electrical = Interface()

        self.LLIFs = LLIFS(self)

    def connect(self, other: Self) -> Self:
        self.LLIFs.electrical.connect(other.LLIFs.electrical)

        return super().connect(other)


class Bus(InterfaceNode):
    class LLIFS(super().LLIFS):
        bus = Interface()

    def __init__(self) -> None:
        super().__init__()
        self.LLIFs = Bus.LLIFS(self)

    # TODO: make trait
    def connect(self, other: Self) -> Self:
        self.LLIFs.bus.connect(other.LLIFs.bus)

        return super().connect(other)


class ElectricPower(Bus):
    def __init__(self) -> None:
        super().__init__()

        class _NODES(super().NODES):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = _NODES(self)

    def connect(self, other: Self) -> Self:
        self.NODEs.hv.connect(other.NODEs.hv)
        self.NODEs.lv.connect(other.NODEs.lv)

        return super().connect(other)

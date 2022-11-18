# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterator, Self

logger = logging.getLogger("library")

from faebryk.library.core import Component, Interface
from faebryk.library.traits.interface import contructable_from_interface_list


class Electrical(Interface):
    def __init__(self) -> None:
        super().__init__()

        class _contructable_from_interface_list(
            contructable_from_interface_list.impl()
        ):
            @staticmethod
            def from_interfaces(interfaces: Iterator[Electrical]) -> Electrical:
                return next(interfaces)

        self.add_trait(_contructable_from_interface_list())


# TODO: move file -------------------------------------------------------------
class Bus(Component):
    class IFS(Component.InterfacesCls()):
        bus = Interface()

    def __init__(self) -> None:
        super().__init__()
        self.IFs = Bus.IFS(self)

    # TODO: make trait
    def connect(self, other: Self) -> Self:
        self.IFs.bus.connect(other.IFs.bus)


class Power(Bus):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Bus.IFS):
            hv = Electrical()
            lv = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Self) -> Self:
        assert type(other) is Power, "can't connect to non power"

        self.IFs.hv.connect(other.IFs.hv)
        self.IFs.lv.connect(other.IFs.lv)

        return super().connect(other)

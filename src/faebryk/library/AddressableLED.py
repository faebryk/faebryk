# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import IntEnum, auto

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.TBD import TBD


class AddressableLED(Module):
    class Protocol(IntEnum):
        WS2812 = auto()
        SPI = auto()

    def __init__(self) -> None:
        super().__init__()

        class _PARAMs(super().PARAMS()):
            protocol = TBD[self.Protocol]()

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            data_in = ElectricLogic()
            data_out = ElectricLogic()
            if self.PARAMs.protocol == self.Protocol.SPI:
                clk_in = ElectricLogic()
                clk_out = ElectricLogic()

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(self.IFs.power.IFs.hv, self.IFs.power.IFs.lv))
        self.add_trait(has_designator_prefix_defined("U"))

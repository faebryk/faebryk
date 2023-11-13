# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.LED import LED
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD
from faebryk.library.can_bridge_defined import can_bridge_defined


class PoweredLED(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        class _NODEs(Module.NODES()):
            current_limiting_resistor = Resistor(TBD())
            led = LED()

        self.NODEs = _NODEs(self)

        self.IFs.power.NODEs.hv.connect(self.NODEs.led.IFs.anode)
        self.IFs.power.NODEs.lv.connect_via(
            self.NODEs.current_limiting_resistor, self.NODEs.led.IFs.cathode
        )

        self.add_trait(
            can_bridge_defined(self.IFs.power.NODEs.hv, self.IFs.power.NODEs.lv)
        )
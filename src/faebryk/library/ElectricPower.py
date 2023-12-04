# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Electrical import Electrical
from faebryk.library.Power import Power
from faebryk.library.TBD import TBD


class ElectricPower(Power):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Power.NODES()):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = NODES(self)

        class PARAMS(Power.PARAMS()):
            voltage = TBD()

        self.PARAMs = PARAMS(self)

        # self.PARAMs.voltage.merge(
        #    self.NODEs.hv.PARAMs.potential - self.NODEs.lv.PARAMs.potential
        # )

    def _on_connect(self, other: ModuleInterface) -> None:
        super()._on_connect(other)

        if not isinstance(other, ElectricPower):
            return

        self.PARAMs.voltage.merge(other.PARAMs.voltage)

    def decouple(self, capacitor: Capacitor):
        self.NODEs.hv.connect_via(capacitor, self.NODEs.lv)

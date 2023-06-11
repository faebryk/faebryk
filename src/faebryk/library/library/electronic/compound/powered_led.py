import logging

from faebryk.library.core import Component
from faebryk.library.library.electronic.base.led import LED
from faebryk.library.library.electronic.base.resisistor import Resistor
from faebryk.library.library.interfaces import Power
from faebryk.library.library.parameters import TBD

logger = logging.getLogger("Powered LED")


class PoweredLED(Component):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Component.InterfacesCls()):
            power = Power()

        self.IFs = _IFs(self)

        class _CMPs(Component.ComponentsCls()):
            current_limiting_resistor = Resistor(TBD())
            led = LED()

        self.CMPs = _CMPs(self)

        self.IFs.power.IFs.hv.connect(self.CMPs.led.IFs.anode)
        self.IFs.power.IFs.lv.connect_via(
            self.CMPs.current_limiting_resistor, self.CMPs.led.IFs.cathode
        )

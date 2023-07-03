import logging

from faebryk.library.core import Component, Parameter
from faebryk.library.library.electronic.base.resisistor import Resistor
from faebryk.library.library.interfaces import Electrical
from faebryk.library.util import times

logger = logging.getLogger(__name__)


class Potentiometer(Component):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter) -> None:
        super().__init__()
        self._setup_interfaces(resistance)

    def _setup_traits(self):
        pass

    def _setup_interfaces(self, resistance):
        class _IFs(Component.InterfacesCls()):
            resistors = times(2, Electrical)
            wiper = Electrical()

        class _CMPs(Component.ComponentsCls()):
            resistors = [Resistor(resistance) for _ in range(2)]

        self.IFs = _IFs(self)
        self.CMPs = _CMPs(self)

        self.IFs.wiper.connect_all(
            [
                self.CMPs.resistors[0].IFs.unnamed[1],
                self.CMPs.resistors[1].IFs.unnamed[1],
            ]
        )

        for i, resistor in enumerate(self.CMPs.resistors):
            self.IFs.resistors[i].connect(resistor.IFs.unnamed[0])

    def connect_as_voltage_divider(self, high, low, out):
        self.IFs.resistors[0].connect(high)
        self.IFs.resistors[1].connect(low)
        self.IFs.wiper.connect(out)

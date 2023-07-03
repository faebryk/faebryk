# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger(__name__)

from faebryk.library.core import ModuleInterface

# TODO: move file (interface component)----------------------------------------


class Electrical(ModuleInterface):
    ...


class Power(ModuleInterface):
    ...


class ElectricPower(Power):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Power.NODES()):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = NODES(self)

    def _connect(self, other: ModuleInterface) -> ModuleInterface:
        if isinstance(other, type(self)):
            self.NODEs.hv.connect(other.NODEs.hv)
            self.NODEs.lv.connect(other.NODEs.lv)

        return super()._connect(other)


class Logic(ModuleInterface):
    ...


class ElectricLogic(Logic):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Logic.NODES()):
            reference = ElectricPower()
            signal = Electrical()

        self.NODEs = NODES(self)

    def _connect(self, other: ModuleInterface) -> ModuleInterface:
        if isinstance(other, type(self)):
            self.NODEs.reference.connect(other.NODEs.reference)
            self.NODEs.signal.connect(other.NODEs.signal)

        return super()._connect(other)

    def connect_to_electric(self, signal: Electrical, reference: ElectricPower):
        self.NODEs.reference.connect(reference)
        self.NODEs.signal.connect(signal)
        return self

    def pull_down(self, resistor):
        from faebryk.library.library.modules import Resistor

        assert isinstance(resistor, Resistor)

        self.NODEs.signal.connect_via(resistor, self.NODEs.reference.NODEs.lv)

    def pull_up(self, resistor):
        from faebryk.library.library.modules import Resistor

        assert isinstance(resistor, Resistor)

        self.NODEs.signal.connect_via(resistor, self.NODEs.reference.NODEs.hv)

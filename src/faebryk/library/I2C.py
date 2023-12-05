# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from enum import IntEnum

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD
from faebryk.libs.units import M, k

logger = logging.getLogger(__name__)


class I2C(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class NODES(ModuleInterface.NODES()):
            scl = ElectricLogic()
            sda = ElectricLogic()

        self.NODEs = NODES(self)

        class PARAMS(ModuleInterface.PARAMS()):
            frequency = TBD()

        self.PARAMs = PARAMS(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

    def terminate(self, resistors: tuple[Resistor, Resistor]):
        # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

        self.NODEs.sda.pull_up(resistors[0])
        self.NODEs.scl.pull_up(resistors[1])

    def _on_connect(self, other: "I2C"):
        super()._on_connect(other)

        self.PARAMs.frequency.merge(other.PARAMs.frequency)

    class SpeedMode(IntEnum):
        low_speed = 10 * k
        standard_speed = 100 * k
        fast_speed = 400 * k
        high_speed = 3.4 * M

    @staticmethod
    def define_max_frequency_capability(mode: SpeedMode):
        return Range(I2C.SpeedMode.low_speed, mode)

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from enum import IntEnum

from faebryk.core.core import ModuleInterface, Parameter
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

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

        self.frequency = TBD()

    def set_frequency(self, frequency: Parameter):
        self.frequency = frequency

    def terminate(self, resistors: tuple[Resistor, Resistor]):
        # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

        self.NODEs.sda.pull_up(resistors[0])
        self.NODEs.scl.pull_up(resistors[1])

    def _on_connect(self, other: "I2C"):
        super()._on_connect(other)

        if self.frequency == other.frequency:
            return

        try:
            frequency = self.frequency.resolve(other.frequency)
        except Parameter.ResolutionException:
            raise Parameter.ResolutionException(
                "Cannot resolve frequencies of\n"
                + f"\t {self}({self.frequency}) and\n"
                + f"\t {other}({other.frequency})"
            )
        other.set_frequency(frequency)
        self.set_frequency(frequency)

    class SpeedMode(IntEnum):
        low_speed = 10 * k
        standard_speed = 100 * k
        fast_speed = 400 * k
        high_speed = 3.4 * M

    @staticmethod
    def define_max_frequency_capability(mode: SpeedMode):
        return Range(I2C.SpeedMode.low_speed, mode)

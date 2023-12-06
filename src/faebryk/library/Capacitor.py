# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto

from faebryk.core.core import Module, Parameter
from faebryk.core.util import unit_map
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_simple_value_representation_based_on_param import (
    has_simple_value_representation_based_on_param,
)
from faebryk.library.TBD import TBD
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Capacitor(Module):
    class TemperatureCoefficient(IntEnum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    def __init__(
        self,
        capacitance: Parameter,
        rated_voltage: Parameter,
        temperature_coefficient: Parameter,
    ):
        super().__init__()

        class _IFs(Module.IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            capacitance = TBD()
            rated_voltage = TBD()
            temperature_coefficient = TBD()

        self.PARAMs = _PARAMs(self)

        self.PARAMs.capacitance.merge(capacitance)
        self.PARAMs.rated_voltage.merge(rated_voltage)
        self.PARAMs.temperature_coefficient.merge(temperature_coefficient)

        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

        self.add_trait(
            has_simple_value_representation_based_on_param(
                self.PARAMs.capacitance,
                lambda p: unit_map(p, ["µF", "mF", "F", "KF", "MF", "GF"], start="F"),
            )
        )
        self.add_trait(can_attach_to_footprint_symmetrically())
        self.add_trait(has_designator_prefix_defined("C"))

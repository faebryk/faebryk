# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, Parameter
from faebryk.core.util import unit_map
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_simple_value_representation_based_on_param import (
    has_simple_value_representation_based_on_param,
)
from faebryk.library.TBD import TBD


class Diode(Module):
    def __init__(self, forward_voltage: Parameter):
        super().__init__()

        class _PARAMs(Diode.PARAMS()):
            forward_voltage = TBD()

        self.PARAMs = _PARAMs(self)

        self.PARAMs.forward_voltage.merge(forward_voltage)

        class _IFs(super().IFS()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(self.IFs.anode, self.IFs.cathode))
        self.add_trait(
            has_simple_value_representation_based_on_param(
                self.PARAMs.forward_voltage,
                lambda p: unit_map(
                    p.value,
                    ["µV", "mV", "V", "kV", "MV", "GV"],
                    start="V",
                ),
            )
        )
        self.add_trait(has_designator_prefix_defined("D"))

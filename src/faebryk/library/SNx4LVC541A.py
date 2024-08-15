# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.libs.units import P
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Range import Range
from faebryk.libs.util import times


class SNx4LVC541A(Module):
    """
    The SN54LVC541A octal buffer/driver is designed for
    3.3-V VCC) 2.7-V to 3.6-V VCC operation, and the SN74LVC541A
    octal buffer/driver is designed for 1.65-V to 3.6-V VCC operation.
    """

    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            A = times(8, ElectricLogic)
            Y = times(8, ElectricLogic)

            vcc = ElectricPower()

            OE = times(2, ElectricLogic)

        self.IFs = _IFs(self)

        # ----------------------------------------
        #                traits
        # ----------------------------------------
        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            has_datasheet_defined(
                "https://www.ti.com/lit/ds/symlink/sn74lvc541a.pdf?ts=1718881644774&ref_url=https%253A%252F%252Fwww.mouser.ie%252F"
            )
        )
        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

        # ----------------------------------------
        #                parameters
        # ----------------------------------------
        self.IFs.vcc.PARAMs.voltage.merge(Range.upper_bound(3.6 * P.V))

        # ----------------------------------------
        #                aliases
        # ----------------------------------------

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.IFs.vcc.get_trait(can_be_decoupled).decouple()

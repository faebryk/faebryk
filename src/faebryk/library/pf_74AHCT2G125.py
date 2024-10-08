# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class pf_74AHCT2G125(Module):
    """
    The 74AHC1G/AHCT1G125 is a high-speed Si-gate CMOS device.
    The 74AHC1G/AHCT1G125 provides one non-inverting buffer/line
    driver with 3-state output. The 3-state output is controlled
    by the output enable input (OE). A HIGH at OE causes the
    output to assume a high-impedance OFF-state.
    """

    # interfaces

    power: F.ElectricPower
    a: F.ElectricLogic  # IN
    y: F.ElectricLogic  # OUT
    oe: F.ElectricLogic  # enable, active low

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.oe.signal,
                "2": x.a.signal,
                "3": x.power.lv,
                "4": x.y.signal,
                "5": x.power.hv,
            }
        )

    def __preinit__(self):
        self.power.voltage.merge(F.Range(4.5 * P.V, 5.5 * P.V))
        self.power.decoupled.decouple()

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.a, self.y)

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheet.lcsc.com/lcsc/2304140030_Nexperia-74AHCT1G125GV-125_C12494.pdf"
    )

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.can_be_surge_protected_defined import (
    can_be_surge_protected_defined,
)
from faebryk.library.DifferentialPair import DifferentialPair
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Range import Range
from faebryk.library.USB3 import USB3


class can_be_surge_protected_defined_usb(can_be_surge_protected_defined):
    def protect(self):
        return (
            super()
            .protect()
            .builder(
                lambda tvs: tvs.PARAMs.reverse_working_voltage.merge(
                    Range.lower_bound(5.0)
                )
            )
        )


class USB_C(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _NODEs(ModuleInterface.NODES()):
            usb3 = USB3()
            cc1 = Electrical()
            cc2 = Electrical()
            sbu1 = Electrical()
            sbu2 = Electrical()
            rx = DifferentialPair()
            tx = DifferentialPair()

        self.NODEs = _NODEs(self)


class USB_C_PowerOnly(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(ModuleInterface.NODES()):
            power = ElectricPower()
            cc1 = Electrical()
            cc2 = Electrical()

        self.NODEs = _NODEs(self)

        self.add_trait(
            can_be_surge_protected_defined(
                self.NODEs.power.NODEs.lv,
                self.NODEs.power.NODEs.hv,
                self.NODEs.cc1,
                self.NODEs.cc2,
            )
        )

    def connect_to_full_usb_c(self, usb_c: USB_C):
        self.NODEs.power.connect(usb_c.NODEs.usb3.NODEs.usb2.NODEs.buspower)
        self.NODEs.cc1.connect(usb_c.NODEs.cc1)
        self.NODEs.cc2.connect(usb_c.NODEs.cc2)
        return self

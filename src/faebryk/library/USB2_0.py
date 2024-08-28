# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Range import Range
from faebryk.library.USB2_0_IF import USB2_0_IF
from faebryk.libs.units import P


class USB2_0(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            usb_if = USB2_0_IF()

        self.IFs = IFS(self)

        self.IFs.usb_if.IFs.buspower.PARAMs.voltage.merge(
            Range.from_center(5 * P.V, 0.25 * P.V)
        )

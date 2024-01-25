# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.DifferentialPair import DifferentialPair
from faebryk.library.Electrical import Electrical
from faebryk.library.USB2_0 import USB2_0


class USB3(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            usb2 = USB2_0()
            rx = DifferentialPair()
            tx = DifferentialPair()
            gnd_drain = Electrical()

        self.IFs = IFS(self)

        self.IFs.gnd_drain.connect(self.IFs.usb2.IFs.buspower.IFs.lv)

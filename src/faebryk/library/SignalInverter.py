# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricLogic import ElectricLogic


class SignalInverter(Module):
    """
    Inverts a logic signal
    """

    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            logic_out = ElectricLogic()

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(self.IFs.logic_in, self.IFs.logic_out))

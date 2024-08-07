# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)


class SWD(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            clk = ElectricLogic()
            dio = ElectricLogic()
            swo = ElectricLogic()
            reset = ElectricLogic()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()): ...

        self.PARAMs = PARAMS(self)

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface, Parameter
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.TBD import TBD


class UART_Base(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class NODES(ModuleInterface.NODES()):
            rx = ElectricLogic()
            tx = ElectricLogic()

        self.NODEs = NODES(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

        self.baud = TBD()

    def set_baud(self, baud: Parameter):
        assert not isinstance(self.baud, Constant)
        self.baud = baud

    def _on_connect(self, other: "UART_Base"):
        super()._on_connect(other)

        if self.baud == other.baud:
            return

        # TODO parameter specialization
        if isinstance(self.baud, Constant):
            other.set_baud(self.baud)
        elif isinstance(other.baud, Constant):
            self.set_baud(other.baud)
